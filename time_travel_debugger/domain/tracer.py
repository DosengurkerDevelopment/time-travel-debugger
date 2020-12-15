import inspect
import sys
import os
from copy import deepcopy
from typing import List

from ..model.exec_state_diff import ExecStateDiff, Action


class TimeTravelTracer(object):

    NO_TRACE = ['__exit__', 'get_trace']

    def __init__(self):
        self._diffs: List[ExecStateDiff] = []
        self._source_map = {}
        self._last_vars = []
        self._last_frame = None
        self._should_return = False
        self._root_func_name = ""

    def get_trace(self):
        sys.settrace(None)
        #  self._diffs.insert(0,ExecStateDiff())
        self._diffs.pop()
        last_state = self._current_diff.finish()
        self._diffs.append(last_state)
        return self._diffs, self._source_map

    def set_trace(self):
        sys.settrace(self._traceit)

    def _traceit(self, frame, event, arg):
        ''' Internal tracing method '''
        # Don't trace __exit__ function and get_trace
        if frame.f_code.co_name not in self.NO_TRACE:
            self.traceit(frame, event, arg)
        return self._traceit

    def _changed_vars(self, locals):
        changed = {}
        for var_name in locals:
            # detect if a variable changed and push it into changed dict
            if (var_name not in self._last_vars[-1] or
                    self._last_vars[-1][var_name] != locals[var_name]):
                changed[var_name] = locals[var_name]
        # update last _last_vars
        self._last_vars[-1] = locals.copy()
        return changed

    def _do_return(self):
        assert len(self._last_vars) > 0
        self._last_vars.pop()
        new_state = self._current_diff.ret()
        self._last_frame = new_state.func_name
        return new_state

    def _do_call(self, frame):
        # we called a new function, so setup a new scope of variables
        self._last_vars.append(frame.f_locals.copy())
        # set last_frame manually since we don't compute _changed_vars
        self._last_frame = frame.f_code.co_name
        # create new function frame in current _exec_state_diff
        new_state = self._current_diff.call(frame)
        return new_state

    def _do_update(self, frame):
        assert len(
            self._last_vars) > 0, f"all actions:{[x.action for x in self._diffs]}"
        # save old scope for the update on _exec_state_diff
        prev_vars = self._last_vars[-1]
        changed = self._changed_vars(frame.f_locals.copy())
        #  added = self._added_vars(frame.f_locals.copy())
        # new function, invoke in exec_state_diff accordingly
        new_state = self._current_diff.update(frame, prev_vars, changed)
        return new_state

    @property
    def _last_action(self):
        if len(self._diffs) > 0:
            return self._diffs[-1].action
        else:
            return None

    @property
    def root_func_name(self):
        return self._root_func_name

    @root_func_name.setter
    def root_func_name(self,x):
        if not self._root_func_name:
            self._root_func_name = x

    @property
    def _current_diff(self):
        if len(self._diffs) > 0:
            return deepcopy(self._diffs[-1])
        else:
            return ExecStateDiff(self._root_func_name)

    def traceit(self, frame, event, arg):
        ''' Record the execution inside the with block.
        We do not store the complete state for each execution point, instead
        we calculate the difference and store a 'diff' which contains the old
        and the new value such that we can easily restore the state without
        having to backtrack to the beginning.
        '''

        # collect the code in a source_map, so we can print it later in the
        # debugger
        filename = os.path.basename(inspect.getsourcefile(frame.f_code))
        code, startline = inspect.getsourcelines(frame.f_code)
        self.root_func_name = frame.f_code.co_name
        #  if frame.f_code.co_name not in self._source_map:
        self._source_map[frame.f_code.co_name] = {
            "start": startline, "code": code, "filename": filename}
        relative_line_no = frame.f_lineno - startline
        line_code = code[relative_line_no]
        at_last_line_of_func = relative_line_no == (len(code)-1)
        if frame.f_lineno == startline:
            # first call of traceit in current frame should be ignored,
            # since its the function definition
            return self._traceit
        # print(f"line {relative_line_no}/{len(code)-1} : { line_code }")
        # check if last action was a return statement
        # in that case don't do call, since we step back in to previous frame
        if self._last_action != Action.RET\
                and frame.f_code.co_name != self._last_frame:
            new_state = self._do_call(frame)
            # print(f"CALL")
        else:
            new_state = self._do_update(frame)
            # print(f"UPDATE")

        if at_last_line_of_func:
            if self._should_return:
                # we executed the statement before return, so we can return
                self._should_return = False
                new_state = self._do_return()
                # print(f"RETURN")
            else:
                self._should_return = True

        self._diffs.append(new_state)
        # print(f"vars:{self._diffs[-1]}")
        return self._traceit
