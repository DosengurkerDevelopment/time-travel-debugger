import inspect
import sys
import os
import traceback 

from copy import deepcopy
from typing import List

from ..model.exec_state_diff import ExecStateDiff, Action


class TimeTravelTracer(object):

    NO_TRACE = ["__exit__", "get_trace"]

    def __init__(self):
        self._diffs: List[ExecStateDiff] = []
        self._source_map = {}
        self._last_vars = []
        self._should_call = False
        self._root_func_name = ""

    def get_trace(self):
        sys.settrace(None)
        # insert empty state at the beginning to mark the start
        self._diffs.insert(0,ExecStateDiff(self.root_func_name))
        # remove implicit return statement
        self._diffs.pop()
        return self._diffs, self._source_map

    def set_trace(self):
        sys.settrace(self._traceit)

    def _traceit(self, frame, event, arg):
        """ Internal tracing method """
        # Don't trace __exit__ function and get_trace
        if frame.f_code.co_name not in self.NO_TRACE:
            self.traceit(frame, event, arg)
        return self._traceit

    def _exception(self,tb):
        new_state = self._current_diff.exception(tb)
        self._diffs.append(new_state)


    def _do_return(self, frame):
        # return statements also could update variables:
        self._do_update(frame)
        new_state = self._current_diff.ret()
        self._diffs.append(new_state)
        self._last_vars.pop()
        #  print(f"RETURN")

    def _do_call(self, frame):
        #  self._diffs.pop()
        # we called a new function, so setup a new scope of variables
        # set last_frame manually since we don't compute _changed_vars
        # create new function frame in current _exec_state_diff
        new_state = self._current_diff.call(frame)
        self._diffs.append(new_state)
        locals = frame.f_locals.copy()
        self._last_vars.append(locals)
        #  print(f"CALL")

    def _do_update(self, frame):
        # save old scope for the update on _exec_state_diff
        #  prev_vars = self._last_vars[-1]
        #  changed = self._changed_vars(frame.f_locals.copy())
        #  added = self._added_vars(frame.f_locals.copy())
        # new function, invoke in exec_state_diff accordingly
        new_state = self._current_diff.update(
            frame, deepcopy(self._last_vars[-1]), frame.f_locals.copy()
        )
        self._diffs.append(new_state)
        locals = frame.f_locals.copy()
        self._last_vars[-1] = locals
        #  print(f"UPDATE")

    @property
    def root_func_name(self):
        return self._root_func_name

    @root_func_name.setter
    def root_func_name(self, x):
        if not self._root_func_name:
            self._root_func_name = x

    @property
    def _current_diff(self):
        if len(self._diffs) > 0:
            return deepcopy(self._diffs[-1])
        else:
            return ExecStateDiff(self._root_func_name)

    def traceit(self, frame, event, arg):
        """Record the execution inside the with block.
        We do not store the complete state for each execution point, instead
        we calculate the difference and store a 'diff' which contains the old
        and the new value such that we can easily restore the state without
        having to backtrack to the beginning.
        """

        # collect the code in a source_map, so we can print it later in the
        # debugger
        filename = inspect.getsourcefile(frame.f_code)
        code, startline = inspect.getsourcelines(frame.f_code)
        self.root_func_name = frame.f_code.co_name
        #  if frame.f_code.co_name not in self._source_map:
        self._source_map[frame.f_code.co_name] = {
            "start": startline,
            "code": code,
            "filename": filename,
        }
        #  print(f"{frame.f_lineno}: {code[frame.f_lineno - startline]}")
        #  print(f"EVENT:{event}")
        #  print(f"last_vars:{self._last_vars}")
        #  print(f"locals:{frame.f_locals}")
        # in case we returned from functin last line, we want to skip the
        # line of caller
        if event == "call":
            # we dont want to directly do_call, since we want to skip the
            # function definition
            # In order to get rid of this, we always ignore the line where a
            # call happens and postpone this call to one line later
            self._should_call = True
        elif self._should_call:
            self._do_call(frame)
            self._should_call = False
        elif event == "line":
            self._do_update(frame)
            #  print(f"UPDATE")
        elif event == "return":
            #  self._do_update(frame)
            self._do_return(frame)
            #  print(f"RETURN")
        elif event == "exception" :
            print("exception")
            exception, value, tb = arg
            #  print(arg)
            tb = traceback.format_exception(exception, value, tb)
            #  print(tb_formatted)
            self._exception(tb)
            #  return

        # print(f"vars:{self._diffs[-1]}")
        return self._traceit
