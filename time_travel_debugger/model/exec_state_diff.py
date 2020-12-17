from typing import List, Dict, Any
import os
import inspect
import collections
from enum import Enum
from copy import deepcopy

# named tuple for a variable change
VarUpdate = collections.namedtuple('VarUpdate', 'before after')


class Action(Enum):
    CALL = 1
    RET = 2
    UPDATE = 3
    EXCEPTION = 4


class ExecStateDiff(object):
    ''' Model for saving differences between states of executions '''

    def __init__(self,root_func_name):
        self._function_states = []
        self._action = None
        self._root_func_name = root_func_name

    def call(self, frame):
        self._function_states.append(FunctionStateDiff(frame))
        self._action = Action.CALL
        return self

    def update(self, frame, prev_vars, new_vars):
        self._function_states[-1].update(frame, prev_vars, new_vars)
        self._action = Action.UPDATE
        return self

    def ret(self):
        assert len(self._function_states) > 0
        self._function_states.pop()
        self._action = Action.RET
        return self

    def exception(self, tb):
        self._action = Action.EXCEPTION
        #  self._exception = exception
        #  self._value = value
        self._tb = tb
        return self

    def __contains__(self, key):
        return key in self.added or key in self.updated

    def __getitem__(self, key):
        if key in self.added:
            return self.added[key]
        elif key in self.updated:
            return self.updated[key].after
        else:
            return None

    def __str__(self):
        return f"{self._action} \t- {self._function_states}\n"

    __repr__ = __str__

    def get_function_states(self):
        return self._function_states

    @property
    def action(self):
        return self._action

    @property
    def func_name(self):
        if (len(self._function_states) > 0):
            return self._function_states[-1].func_name
        else:
            return self._root_func_name

    @property
    def lineno(self):
        if (len(self._function_states) > 0):
            return self._function_states[-1].lineno
        else:
            return -1

    @property
    def added(self):
        if (len(self._function_states) > 0):
            return self._function_states[-1].added
        else:
            return {}
    @property
    def updated(self):
        if (len(self._function_states) > 0):
            return self._function_states[-1].updated
        else:
            return {}

    @property
    def changed(self):
        # TODO: this can be done more efficiently i think
        return {**self.added, **{k: v.after for (k, v) in self.updated.items()}}

    @property
    def file_name(self):
        if (len(self._function_states) > 0):
            return self._function_states[-1].file_name
        else:
            return ""

    # the number of nested function calls
    @property
    def depth(self):
        if (len(self._function_states) > 0):
            return len(self._function_states) - 1
        else:
            return -1


class FunctionStateDiff(object):
    ''' Model for saving differences between states of executions for one function scope '''

    def __init__(self, frame):
        # Hash of the frame this diff belongs to
        self._frame = hash(frame)
        self._file_name = os.path.basename(inspect.getfile(frame))
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
