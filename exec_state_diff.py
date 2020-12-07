from typing import List, Dict, Any
import collections


# named tuple for a variable change
VarUpdate = collections.namedtuple('VarUpdate', 'before after')


class ExecStateDiff(object):

    def __init__(self):
        self._function_states = []

    def call(self, frame):
        self._function_states.append(FunctionStateDiff(frame))
        return self

    def update(self, frame, prev_vars, new_vars):
        self._function_states[-1].update(frame, prev_vars, new_vars)
        return self

    def ret(self, frame):
        self._function_states.pop()
        return self

    def __str__(self):
        return f"{self._function_states}\n"

    def __repr__(self):
        return str(self)

    #  @property
    #  def frame(self):
        #  return self._function_states[-1].frame

    @property
    def func_name(self):
        return self._function_states[-1].func_name

    @property
    def lineno(self):
        return self._function_states[-1].lineno

    @property
    def added(self):
        return self.function_states[-1].added

    @property
    def updated(self):
        return self.function_states[-1].updated

    @property
    def before(self):
        return self.function_states[-1].before

    @property
    def after(self):
        return self.function_states[-1].after

    # the number of nested function calls
    @property
    def depth(self):
        return len(self._function_states)


class FunctionStateDiff(object):

    def __init__(self, frame):
        # Hash of the frame this diff belongs to
        self._frame = hash(frame)
        self._func_name = frame.f_code.co_name
        # Line number of the diff
        self._lineno = frame.f_lineno

        # Variables that were added to the state in this step
        self._added_vars = frame.f_locals
        # Variables that were updated in this step
        self._updated_vars = {}

    def update(self, frame, prev_vars, new_vars):
        self._lineno = frame.f_lineno
        for key, value in new_vars.items():
            #  print(f"prev:{prev_vars}, new:{new_vars}")
            if key in prev_vars:
                # only push change, if we really changed something
                if value != prev_vars[key]:
                    update = VarUpdate(before=prev_vars[key], after=value)
                    #  if(update.before != update.after):
                    self._updated_vars[key] = update
            else:
                self._added_vars[key] = value


    def __str__(self):
        return f"<added:{self.added}, updated:{self.updated}>"

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
    def before(self):
        return [x.before for x in self._updated_vars]

    @property
    def after(self):
        return self._added_vars + [x.after for x in self._updated_vars]

    @property
    def func_name(self):
        return self.func_name
