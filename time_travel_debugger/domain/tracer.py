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

    def get_trace(self):
        sys.settrace(None)
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
        #  print(f"previous: {prev_vars}")
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
    def _current_diff(self):
        if len(self._diffs) > 0:
            return deepcopy(self._diffs[-1])
        else:
            return ExecStateDiff()

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
        if frame.f_code.co_name not in self._source_map:
            self._source_map[frame.f_code.co_name] = {
                "start": startline, "code": code, "filename": filename}
        if frame.f_lineno == startline:
            # first call of traceit in current frame should be ignored
            return self._traceit
        line_code = code[frame.f_lineno - startline]
        #  print(f"current_function: { frame.f_code.co_name }")
        #  print(f"{frame.f_lineno}: {line_code.rstrip()}")
        #  print(f"locals :{frame.f_locals}")
        if "return " in line_code and self._should_return:
            # we executed the statement before return, so we can return
            #  print("return")
            self._should_return = False
            new_state = self._do_return()
        # check if last action was a return statement
        # in that case don't do call, since we step back in to previous frame
        elif self._last_action != Action.RET\
                and frame.f_code.co_name != self._last_frame:
            #  print(f"CALL {frame.f_code.co_name}")
            if "return " in line_code:
                # this is the state where we first see return, but didnt execute the
                # previous line yet
                # so perform call and next round we can perform return
                self._should_return = True
            new_state = self._do_call(frame)
        else:
            #  print("UPDATE")
            if "return " in line_code:
                # this is the state where we first see return, but didnt execute the
                # previous line yet
                # so perform update and next round we can perform return
                self._should_return = True
            #  if self._last_action == Action.RET:
                #  return self._traceit
            new_state = self._do_update(frame)

        #  print(f"last_vars {self._last_vars[-1]}")
        #  print(f"locals {frame.f_locals}")
        self._diffs.append(new_state)
        return self._traceit
