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
        self._should_call = False
        self._root_func_name = ""

    def get_trace(self):
        sys.settrace(None)
        self._diffs.insert(0,deepcopy(self._diffs[0]))
        self._diffs.pop()
        #  last_state = self._current_diff.finish()
        #  self._diffs.append(last_state)
        return self._diffs, self._source_map

    def set_trace(self):
        sys.settrace(self._traceit)

    def _traceit(self, frame, event, arg):
        ''' Internal tracing method '''
        # Don't trace __exit__ function and get_trace
        if frame.f_code.co_name not in self.NO_TRACE:
            self.traceit(frame, event, arg)
        return self._traceit

    def _do_return(self):
        assert len(self._last_vars) > 0
        new_state = self._current_diff.ret()
        self._diffs.append(new_state)
        self._last_vars.pop()

    def _do_call(self, frame):
        #  self._diffs.pop()
        # we called a new function, so setup a new scope of variables
        # set last_frame manually since we don't compute _changed_vars
        # create new function frame in current _exec_state_diff
        new_state = self._current_diff.call(frame)
        self._diffs.append(new_state)
        locals = frame.f_locals.copy()
        self._last_vars.append(locals)

    def _do_update(self, frame):
        assert len(
            self._last_vars) > 0, f"all actions:{[x.action for x in self._diffs]}"
        # save old scope for the update on _exec_state_diff
        #  prev_vars = self._last_vars[-1]
        #  changed = self._changed_vars(frame.f_locals.copy())
        #  added = self._added_vars(frame.f_locals.copy())
        # new function, invoke in exec_state_diff accordingly
        new_state = self._current_diff.update(frame,
                deepcopy(self._last_vars[-1]),frame.f_locals.copy())
        self._diffs.append(new_state)
        locals = frame.f_locals.copy()
        self._last_vars[-1] = locals

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
        print(f"{frame.f_lineno}: {code[frame.f_lineno - startline]}")
        print(f"EVENT:{event}")
        print(f"last_vars:{self._last_vars}")
        print(f"locals:{frame.f_locals}")
        if event == "call":
            # we dont want to directly do_call, since we always have one line,
            # that does nothing after call
            # In order to get rid of this, we always ignore the line where a
            # call happens and postpone this call to one trace stop later
            self._should_call = True
        elif self._should_call:
            self._do_call(frame)
            self._should_call = False
        elif event == "line":
            self._do_update(frame)
            #  print(f"UPDATE")
        elif event == "return":
            #  self._do_update(frame)
            self._do_return()
            #  print(f"RETURN")

        # print(f"vars:{self._diffs[-1]}")
        return self._traceit
