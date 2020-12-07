import inspect
import sys
from copy import deepcopy
from typing import List

from exec_state_diff import ExecStateDiff


class TimeTravelTracer(object):

    NO_TRACE = ['__exit__', 'get_trace']

    def __init__(self):
        self._diffs: List[ExecStateDiff] = []
        self._source_map = {}
        self._last_vars = []
        self._last_frame = None
        self._exec_state_diff = ExecStateDiff()

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

    def traceit(self, frame, event, arg):
        ''' Record the execution inside the with block.
        We do not store the complete state for each execution point, instead
        we calculate the difference and store a 'diff' which contains the old
        and the new value such that we can easily restore the state without
        having to backtrack to the beginning.
        '''

        # collect the code in a source_map, so we can print it later in the
        # debugger
        if frame.f_code.co_name not in self._source_map:
            self._source_map[frame.f_code.co_name] = inspect.getsourcelines(
                frame.f_code)
        # TODO: check whether the current executed line contains a return
        # statement and then call self._exec_state_diff.return()
        frame.f_lineno
        # TODO: building exec_state_diff doesnt quite work yet!
        if frame.f_code.co_name != self._last_frame:
            print(f"call {frame.f_code.co_name}")
            # we called a new function, so setup a new scope of variables
            self._last_vars.append(frame.f_locals)
            self._last_frame = frame.f_code.co_name
            # create new function frame in exec_state_diff
            new_state = self._exec_state_diff.call(frame)
            # store the resulting diff
            self._diffs.append(deepcopy(new_state))
        else:
            # save old scope for the update on _exec_state_diff
            prev_vars = self._last_vars[-1]
            changed = self.changed_vars(frame.f_locals.copy())
            print("update")
            # new function, invoke in exec_state_diff accordingly
            new_state = self._exec_state_diff.update(frame, prev_vars, changed)
            # store the resulting diff
            self._diffs.append(deepcopy(new_state))

        #  print(f"last_vars {self._last_vars[-1]}")
        #  print(f"changed {changed}")
        #  print(f"locals {frame.f_locals}")
        return self._traceit

    def changed_vars(self, locals):
        changed = {}
        for var_name in locals:
            # detect if a variable changed and push it into changed dict
            if (var_name not in self._last_vars[-1] or
                    self._last_vars[-1][var_name] != locals[var_name]):
                changed[var_name] = locals[var_name]
        # the new state in the current frame of tracing becomes the state of
        # _last_vars for the current scope
        self._last_vars[-1] = locals.copy()
        return changed
