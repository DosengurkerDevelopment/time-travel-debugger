from typing import List, Dict, Any
import inspect
import collections
from enum import Enum

# named tuple for a variable change
VarUpdate = collections.namedtuple('VarUpdate', 'before after')

class Action(Enum):
    CALL = 1
    RET = 2
    UPDATE = 3


'''
Model for saving differences between states of executions
'''
class ExecStateDiff(object):

    def __init__(self):
        self._function_states = []
        self._action = None

    def call(self, frame):
        self._function_states.append(FunctionStateDiff(frame))
        self._action = Action.CALL
        return self

    def update(self, frame, prev_vars, new_vars):
        self._function_states[-1].update(frame, prev_vars, new_vars)
        self._action = Action.UPDATE
        return self

    def ret(self):
        assert len(self._function_states ) > 0
        self._function_states.pop()
        self._action = Action.RET
        return self

    def __str__(self):
        return f"\t{self._action} \t- {self._function_states}\n"

    def __repr__(self):
        return str(self)

    @property
    def action(self):
        return self._action

    @property
    def func_name(self):
        return self._function_states[-1].func_name

    @property
    def lineno(self):
        return self._function_states[-1].lineno

    @property
    def added(self):
        return self._function_states[-1].added

    @property
    def updated(self):
        return self._function_states[-1].updated

    @property
    def changed(self):
        return { **self.added , **self.updated }
    @property
    def file_name(self):
        return self._function_states[-1].file_name

    # the number of nested function calls
    @property
    def depth(self):
        return len(self._function_states) -1


'''
Model for saving differences between states of executions for one function scope
'''
class FunctionStateDiff(object):

    def __init__(self, frame):
        # Hash of the frame this diff belongs to
        self._frame = hash(frame)
        self._file_name = inspect.getfile(frame)
        self._func_name = frame.f_code.co_name
        # Line number of the diff
        self._lineno = frame.f_lineno

        # Variables that were added to the state in this step
        self._added_vars = frame.f_locals.copy()
        # Variables that were updated in this step
        self._updated_vars = {}

    def update(self, frame, prev_vars, changed):
        self._added_vars = {}
        self._updated_vars = {}
        self._lineno = frame.f_lineno
        for key, value in changed.items():
            if key in prev_vars:
                # only push change, if we really changed something
                if value != prev_vars[key]:
                    update = VarUpdate(before=prev_vars[key], after=value)
                    #  if(update.before != update.after):
                    self._updated_vars[key] = update
            else:
                self._added_vars[key] = value


    def __str__(self):
        return f"<lineno: {self.lineno}, added:{self.added}, updated:{self.updated}>"

    def __repr__(self):
        return str(self)

    @property
    def frame(self):
        return self._frame

    @property
    def lineno(self):
        return self._lineno

    @property
    def added(self):
        return self._added_vars

    @property
    def updated(self):
        return self._updated_vars

    @property
    def file_name(self):
        return self._file_name

    @property
    def func_name(self):
        return self._func_name
