import sys
from typing import List
from functools import wraps
from ..model.watchpoint import Watchpoint
from ..model.breakpoint import Breakpoint
from ..model.exec_state_diff import ExecStateDiff, Action
from copy import deepcopy


class StateMachine(object):
    """Contains the absolute state of all defined variables of all currently
    active functions"""

    def __init__(self, diffs):
        self._exec_state_diffs = diffs
        self._curr_states = [{}]
        self._curr_state_ptr = 0
        #  start at -1 and step into first diff in start_debugger
        self._exec_point = 0
        # True if we are at the start of the current frame
        self._at_start = True
        # True if we are the end of the current frame
        self._at_end = False

    def forward(self):
        """steps one step forward if possible and computes the current state"""

        if not self.at_end:
            self._exec_point += 1
            new_diff = self.curr_diff
            print(new_diff)
            if new_diff.action == Action.CALL:
                # called new function, so create new absolute state with added
                # variables (parameters)
                self._curr_states.append(new_diff.changed)
                self._curr_state_ptr += 1
            elif new_diff.action == Action.RET:
                # returned from function, so step down to previous scope
                # dont delete old scope though, since we might need it, when
                # going back in time
                self._curr_state_ptr -= 1
                #  self._exec_point += 1
                #  diff = deepcopy(self.curr_diff)
            elif new_diff.action == Action.UPDATE:
                # depth stayed the same, so just update the state
                self.curr_state.update(new_diff.changed.copy())
            else:
                raise Exception(f"Invalid Action: '{new_diff.action}'")

    def backward(self):
        """steps one step backwards if possible and computes the current state"""

        # Check whether we reached the start of the program
        if not self.at_start:
            prev_diff = deepcopy(self.curr_diff)
            self._exec_point -= 1
            if prev_diff.action == Action.CALL:
                # called new function previously, so rewind by deleting current
                # context (which is safe, since when going forward we will
                # recreate it)
                self._curr_state_ptr -= 1
                self._curr_states.pop()
            elif prev_diff.action == Action.RET:
                # returned from function previously, so go to absolute state
                # one scope higher (which exists, since we rewind in history,
                # so we have created this scope in a previous execution)
                self._curr_state_ptr += 1
            elif prev_diff.action == Action.UPDATE:
                # if previous action was return then step to return statement
                # ,since we dont want to step back to the point after
                # the function execution
                if self.curr_diff.action == Action.RET:
                    self._exec_point -= 1
                    self._curr_state_ptr += 1
                    prev_diff = deepcopy(self.curr_diff)
                # depth stayed the same, so rewind updated vars
                self.curr_state.update(prev_diff.changed)
                # and delete added vars
                for k in prev_diff.added:
                    self.curr_state.pop(k)
            else:
                raise Exception(f"Invalid Action: '{prev_diff.action}'")


    @property
    def at_start(self):
        #  return self._at_start
        return self._exec_point < 2

    @property
    def at_end(self):
        #  return self._at_end
        return self._exec_point == len(self._exec_state_diffs) - 1

    @property
    def curr_line(self):
        return self.curr_diff.lineno

    @property
    def curr_diff(self):
        diff = self._exec_state_diffs[self._exec_point]
        return diff

    @property
    def next_action(self):
        try:
            diff = self._exec_state_diffs[self._exec_point + 1]
            return diff.action
        except IndexError:
            return None

    @property
    def prev_action(self):
        try:
            diff = self._exec_state_diffs[self._exec_point - 1]
            return diff.action
        except IndexError:
            return None

    @property
    def curr_state(self):
        return self._curr_states[self._curr_state_ptr]

    @property
    def curr_depth(self):
        return self._curr_state_ptr


class TimeTravelDebugger(object):
    def __init__(self, exec_state_diffs: List[ExecStateDiff], source_map, update):
        # Dictionary that contains source code objects for each frame
        self._source_map = source_map
        # The current state of variables:
        self._state_machine = StateMachine(exec_state_diffs)

        self._breakpoints = []
        self._watchpoints = []
        self._call_stack_depth = 0

        self._update = update

    def trigger_update(func):
        @wraps(func)
        def nfunc(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)

            state = self._state_machine.curr_state

            for wp in self.watchpoints:
                wp.update(state.get(wp.var_name, None))

            self._update(state)
            self._call_stack_depth = self._state_machine.curr_diff.depth
            return ret

        return nfunc

    @property
    def source_map(self):
        return self._source_map

    @property
    def curr_line(self):
        return self._state_machine.curr_line

    @property
    def curr_diff(self):
        return self._state_machine.curr_diff

    @property
    def breakpoints(self):
        return self._breakpoints

    @property
    def watchpoints(self):
        return self._watchpoints

    @property
    def at_start(self):
        return self._state_machine.at_start

    @property
    def at_end(self):
        return self._state_machine.at_end

    @property
    def curr_state(self):
        return self._state_machine.curr_state

    def break_at_current(self):
        for bp in self.breakpoints:
            if self.is_at_breakpoint(bp) and bp.eval_condition(self.curr_state):
                return True
        return False

    def is_line_breakpoint(self, line):
        for bp in self.breakpoints:
            if bp.breakpoint_type == Breakpoint.FUNC:
                continue
            if bp.location == line:
                return True
        return False

    def is_at_line(self, line):
        return self.curr_line == line

    def is_in_function(self, func, file):
        return self.curr_diff.func_name == func and self.curr_diff.file_name == file

    def is_at_breakpoint(self, bp: Breakpoint):
        if bp.breakpoint_type == Breakpoint.FUNC:
            return self.is_in_function(bp.location, bp.filename)
        else:
            return self.is_at_line(bp.location)

    def start_debugger(self):
        """Interaction loop that is run after the execution of the code inside
        the with block is finished"""
        # since we start at exec_point we have to step once to start at the
        # correct point and update the UI
        self._state_machine.forward()
        self._update(self._state_machine.curr_state)

    @trigger_update
    def step_forward(self):
        """ Step forward one instruction at a time """
        self._state_machine.forward()

    @trigger_update
    def step_backward(self):
        """ Step backward one step at a time """
        self._state_machine.backward()

    @trigger_update
    def step_to_index(self, index):
        if index < self._state_machine._exec_point:
            while index < self._state_machine._exec_point:
                self._state_machine.backward()
        if index > self._state_machine._exec_point:
            while index > self._state_machine._exec_point:
                self._state_machine.forward()

    @trigger_update
    def next(self):
        # TODO: check if next line is executable at all
        curr_diff = self.curr_diff
        code_lines = self._source_map[curr_diff.func_name]["code"]
        start_line = self._source_map[curr_diff.func_name]["start"]
        target = self._state_machine.curr_line + 1
        relative_lineno = target - start_line
        # check if at end of function
        if relative_lineno < len(code_lines):
            # continue to next line stepping over execution
            while (
                not self._state_machine.curr_line == target
                and not self._state_machine.at_end
            ):
                self._state_machine.forward()
        else:
            # step out of function to caller
            self._state_machine.forward()

    @trigger_update
    def previous(self):
        # TODO: check if previous line is executable at all
        target = self._state_machine.curr_line - 1
        curr_diff = self.curr_diff

        start_line = self._source_map[curr_diff.func_name]["start"]
        relative_lineno = target - start_line
        # check if at the beginning of function call
        if relative_lineno > 0:
            # step one line back stepping over execution
            while (
                not self._state_machine.curr_line == target
                and not self._state_machine.at_start
            ):
                self._state_machine.backward()
        else:
            # step back out of function
            self._state_machine.backward()

    @trigger_update
    def finish(self):
        curr_depth = self._state_machine.curr_depth
        # only take in account return actions that happened in the same
        # function scope (in the same depth)
        while (
            not (
                curr_depth == self._state_machine.curr_depth
                and self._state_machine.next_action == Action.RET
            )
            and not self._state_machine.at_end
        ):
            self._state_machine.forward()

    @trigger_update
    def start(self):
        curr_depth = self._state_machine.curr_depth
        # only take in account call actions that happened in one function
        # scope lower
        while (
            not (
                curr_depth == self._state_machine.curr_depth
                and self._state_machine.curr_diff.action == Action.CALL
            )
            and not self._state_machine.at_start
        ):
            self._state_machine.backward()

    @trigger_update
    def continue_(self):
        self._state_machine.forward()
        while not (self.break_at_current() or self._state_machine.at_end):
            self._state_machine.forward()

    @trigger_update
    def reverse(self):
        self._state_machine.backward()
        while not (self.break_at_current() or self._state_machine.at_start):
            self._state_machine.backward()

    @trigger_update
    def until(self, line_no=0, file_name=""):
        if line_no:
            # line number given, so stop at lines larger than that
            target = line_no
        else:
            # otherwise stop at lines bigger than next line
            target = self.curr_line
        # if we are at target line already, step one further to make sure, that
        # we dont get stuck
        if target == self.curr_line:
            self._state_machine.forward()
        while not self.at_end:
            if self.curr_line > target:
                # if filename was given, check if current filename matches
                if file_name:
                    if file_name == self.curr_diff.file_name:
                        break
                # otherwise dont check for filename
                else:
                    break
            self._state_machine.forward()

    @trigger_update
    def backuntil(self, line_no=0, file_name=""):
        if line_no:
            # line number given, so stop at lines larger than that
            target = line_no
        else:
            # otherwise stop at lines bigger than next line
            target = self.curr_line
        # if we are at target line already, step one back to make sure, that
        # we dont get stuck
        if target == self.curr_line:
            self._state_machine.backward()
        while not self.at_start:
            if self.curr_line < target:
                # if filename was given, check if current filename matches
                if file_name:
                    if file_name == self.curr_diff.file_name:
                        break
                # otherwise dont check for filename
                else:
                    break
            self._state_machine.backward()

    def where(self, bound=sys.maxsize):
        print(self.curr_diff)
        func_states = self._state_machine.curr_diff.get_function_states()
        print(func_states)
        call_stack = []
        for state in func_states:
            #  fun_code = self._source_map[state.fun_name]
            call_stack = call_stack + [state.func_name]
        print(f"full call stack: {call_stack}")

        print(bound)
        lower_bound = max(0, self._call_stack_depth - bound)
        upper_bound = min(len(call_stack), self._call_stack_depth + bound)
        print(f"lower:{lower_bound}, upper:{upper_bound}")
        return call_stack[lower_bound:upper_bound]

    def get_breakpoint(self, id):
        for b in self.breakpoints:
            if b.id == id:
                return b
        return None

    def add_breakpoint(self, location, bp_type, filename="", cond=""):
        # Find next breakpoint id
        if not self.breakpoints:
            next_bp_id = 1
        else:
            next_bp_id = max([b.id for b in self.breakpoints]) + 1

        if not filename:
            filename = self.curr_diff.file_name

        if bp_type != Breakpoint.FUNC:
            location = int(location)

            # Find the code object corresponding to this line number and
            # filename
            for source in self._source_map.values():
                if source["filename"] == filename:
                    # TODO: Encapsulate this in get_source_for_line
                    starting_line = source["start"]
                    code = source["code"]

                    if starting_line > location:
                        continue

                    if location > starting_line + len(code):
                        continue

                    line = code[starting_line - location + 1]
                    while line.startswith("\n") or line.startswith("#"):
                        location += 1
                        line = code[starting_line - location + 1]

                    break
            else:
                return None

        new_bp = Breakpoint(next_bp_id, location, filename, bp_type, cond)
        self.breakpoints.append(new_bp)
        return new_bp

    def remove_breakpoint(self, id):
        b = self.get_breakpoint(id)
        if b is not None:
            self.breakpoints.remove(b)
            return True
        return False

    def disable_breakpoint(self, id):
        breakpoint = self.get_breakpoint(id)
        if breakpoint is not None:
            breakpoint.disable()
            return True
        return False

    def enable_breakpoint(self, id):
        breakpoint = self.get_breakpoint(id)
        if breakpoint is not None:
            breakpoint.enable()
            return True
        return False

    def get_watchpoint(self, id):
        for b in self.watchpoints:
            if b.id == id:
                return b
        return None

    def add_watchpoint(self, var_name):
        # Find next breakpoint id
        if not self.watchpoints:
            next_wp_id = 1
        else:
            next_wp_id = max([b.id for b in self.watchpoints]) + 1

        if var_name in self.curr_state:
            initial_value = self.curr_state[var_name]
        else:
            initial_value = None

        new_wp = Watchpoint(next_wp_id, var_name, initial_value)
        self.watchpoints.append(new_wp)
        return new_wp

    def remove_watchpoint(self, id):
        b = self.get_watchpoint(id)
        if b is not None:
            self.watchpoints.remove(b)
            return True
        return False
