import sys
from enum import Enum
from typing import List
from functools import wraps
from ..model.watchpoint import Watchpoint
from ..model.breakpoint import Breakpoint, FunctionBreakpoint, BPType
from ..model.exec_state_diff import ExecStateDiff, Action
from copy import deepcopy


class Direction(Enum):

    FORWARD = 1
    BACKWARD = -1


class FunctionStates(object):
    """Helper class for manaing the absolut states of functions"""

    def __init__(self):
        # maps functions to list of stored scopes
        self._func_scopes = {}
        #  maps the function name to the current number
        #  of 'open' iterations for that function
        self._func_pointers = {}

    def __str__(self):
        res = ""
        for k, v in self._func_scopes.items():
            res += f"\t{k}: {v} \n"
        return res

    __repr__ = __str__

    def __getitem__(self, func_name):
        func_pointer = self._func_pointers[func_name]
        #  print(f"func_pointer:{func_pointer}")
        res = self._func_scopes[func_name][func_pointer]
        #  print(f"found item:{res}")
        return res

    def call(self, func_name, params):
        """Stores a new scope with its parameters after the call for a function"""
        #  print(f"CALL: {func_name} - params:{params}")
        try:
            #  check if functions scope already exists in map
            self._func_scopes[func_name]
        except KeyError:
            # if not create it
            self._func_scopes[func_name] = [{}]
        # then append the parameters to it as a new scope
        self._func_scopes[func_name].append(params.copy())
        try:
            self._func_pointers[func_name] += 1
        except KeyError:
            self._func_pointers[func_name] = 1

    def ret(self, func_name):
        """ this function does nothing """
        #  print(f"RETURN: {func_name}")
        pass

    def update(self, func_name, changes):
        """update variables of the current scope for a function"""
        #  print(f"UPDATE {func_name} - changes:{changes}")
        self._func_scopes[func_name][-1].update(changes.copy())

    def revert_call(self, func_name):
        """revert a call by deleting the most recent scope of the function"""
        #  print(f"REVERT_CALL: {func_name}")
        self._func_pointers[func_name] -= 1
        self._func_scopes[func_name].pop()

    def revert_ret(self, func_name):
        """ this function does nothing """
        #  print(f"REVERT_RETURN: {func_name}")
        # returned from function previously, so go to absolute state
        # one scope higher (which exists, since we rewind in history,
        # so we have created this scope in a previous execution)
        #  self._func_pointers[func_name] += 1
        pass

    def revert_update(self, func_name, added, updated):
        """ revert added and updated variables from previous line in function """
        #  print(f"REVERT_UPDATE: {func_name} - added:{added} - updated:{updated}")
        # if previous action was return then step to return statement
        # ,since we dont want to step back to the point after
        # the function execution

        #  if self.curr_diff.action == Action.RET:
        #  self._exec_point -= 1
        #  self._curr_state_ptr += 1
        #  prev_diff = deepcopy(self.curr_diff)
        current_scope = self._func_pointers[func_name]
        #  print(f"current_scope of {func_name}:{current_scope}")
        before_update = {key: value.before for (key, value) in updated.items()}
        # revert updates
        self._func_scopes[func_name][-1].update(before_update)
        # and delete added vars
        for k in added:
            try:
                self._func_scopes[func_name][current_scope].pop(k)
            except:
                pass


class StateMachine(object):
    """Contains the absolute state of all defined variables of all currently
    active functions"""

    def __init__(self, diffs):
        # the diffs we computed in the tracer
        self._exec_state_diffs = diffs
        # the function state manager
        self._func_states = FunctionStates()
        #  start at -1 and step into first diff in start_debugger
        self._exec_point = 0
        # True if we are at the start of the current frame
        self._at_start = True
        # True if we are the end of the current frame
        self._at_end = False
        self._direction = Direction.FORWARD

    def forward(self):
        """steps one step forward if possible and computes the current state"""
        self._direction = Direction.FORWARD
        if not self.at_end:
            # step one step forward
            prev_diff = deepcopy(self.curr_diff)
            self._exec_point += 1
            new_diff = deepcopy(self.curr_diff)
            # compute state of function scopes
            if new_diff.action == Action.CALL:
                params = new_diff.changed
                self._func_states.call(new_diff.func_name, params)
            elif new_diff.action == Action.RET:
                self._func_states.ret(new_diff.func_name)
            elif new_diff.action == Action.UPDATE:
                self._func_states.update(new_diff.func_name, new_diff.changed.copy())
            else:
                raise Exception(f"Invalid Action: '{new_diff.action}'")
            if self.next_action == Action.RET:
                # skip the implicit return statement
                self._exec_point += 1
            #  print(self._func_states)

    def backward(self):
        """steps one step backwards if possible and computes the current state"""

        self._direction = Direction.BACKWARD
        # Check whether we reached the start of the program
        if not self.at_start:

            prev_diff = deepcopy(self.curr_diff)
            # step one step backwards
            self._exec_point -= 1
            new_diff = deepcopy(self.curr_diff)
            # compute state of function scopes
            if prev_diff.action == Action.CALL:
                self._func_states.revert_call(prev_diff.func_name)
            elif prev_diff.action == Action.RET:
                self._func_states.revert_ret(new_diff.func_name)
            elif prev_diff.action == Action.UPDATE:
                self._func_states.revert_update(
                    new_diff.func_name, prev_diff.added.copy(), prev_diff.updated.copy()
                )
            else:
                raise Exception(f"Invalid Action: '{new_diff.action}'")

            if prev_diff.action == Action.RET:
                # skip the implicit return statement and the line of callee
                self._exec_point -= 1

            #  print(self._func_states)

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
    def prev_diff(self):
        return self._exec_state_diffs[self._exec_point - 1]

    @property
    def next_diff(self):
        return self._exec_state_diffs[self._exec_point + 1]

    @property
    def direction(self):
        return self._direction

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
        return self._func_states[self.curr_diff.func_name]

    @property
    def curr_depth(self):
        func_states = self.curr_diff.get_function_states()
        return len(func_states) - 1


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

            state = self.curr_state

            for wp in self.watchpoints:
                wp.update(state)

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
    def prev_diff(self):
        return self._state_machine.prev_diff

    @property
    def next_diff(self):
        return self._state_machine.next_diff

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
            if self.is_at_breakpoint(bp) and bp.active:
                return True
        return False

    def is_line_breakpoint(self, line, filename=None):
        filename = filename or self.curr_diff.file_name
        source = self.find_source_for_location(filename, line)

        if source is None:
            return False

        file = source["filename"]
        for bp in self.breakpoints:
            if bp.filename != file:
                continue
            if bp.breakpoint_type == BPType.FUNC:
                continue
            else:
                if bp.lineno == line:
                    return True
        return False

    def is_at_line(self, line):
        return self.curr_line == line

    def is_at_breakpoint(self, bp):
        if self.curr_diff.file_name != bp.abs_filename:
            return False
        if bp.breakpoint_type == BPType.FUNC:
            if self._state_machine.direction == Direction.FORWARD:
                return self.is_at_line(bp.startline)
            if self._state_machine.direction == Direction.BACKWARD:
                return self.is_at_line(bp.endline)
        else:
            return self.is_at_line(bp.lineno) and bp.eval_condition(self.curr_state)

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
        curr_diff = self.curr_diff
        curr_line = self._state_machine.curr_line
        # find next executable line. may be undefined if not found
        target = self.find_next_executable_line(
            curr_line + 1, funcname=curr_diff.func_name
        )
        # continue to next line stepping over execution
        while not self._state_machine.curr_line == target and not self.at_end:
            # when we did not find the next valid line that is executable and
            # the current line was after return we stay there
            if not target and self.curr_diff.action == Action.RET:
                break
            # otherwise continue until we found a target or we hit end
            self._state_machine.forward()

    @trigger_update
    def previous(self):
        curr_diff = self.curr_diff
        curr_line = self._state_machine.curr_line
        # find next executable line. may be undefined if not found
        target = self.find_prev_executable_line(
            curr_line - 1, funcname=curr_diff.func_name
        )
        print(f"curr_line:{curr_line}")
        print(f"target:{target}")
        # continue to next line stepping over execution
        while not self._state_machine.curr_line == target and not self.at_start:
            # when we did not find the previous valid line that is executable and
            # the current line was before call we stay there
            if not target and self._state_machine.prev_action == Action.CALL:
                break
            # otherwise continue until we found a target or we hit end
            self._state_machine.backward()

    @trigger_update
    def finish(self):
        curr_depth = self._state_machine.curr_depth
        # only take in account return actions that happened in the same
        # function scope (in the same depth)
        print(curr_depth)
        while (
            not (
                curr_depth == self._state_machine.curr_depth + 1
                and self._state_machine.curr_diff.action == Action.RET
            )
            and not self._state_machine.at_end
        ):
            self._state_machine.forward()
            print(curr_depth)

        if not self._state_machine.at_end:
            self._state_machine.backward()

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

    def get_callstack_safe_bounds(self, _min, _max):
        """ get callstack with safe min and max bounds """
        func_states = self._state_machine.curr_diff.get_function_states()
        call_stack = []
        for state in func_states:
            call_stack = call_stack + [(state.func_name)]
        lower_bound = max(0, _min)
        upper_bound = min(len(call_stack), _max)
        # print(f"lower:{lower_bound}, upper:{upper_bound}")
        if _min == _max:
            return [call_stack[_min]]
        else:
            return call_stack[lower_bound:upper_bound]

    def where(self, bound=sys.maxsize):
        _min = self._call_stack_depth - bound
        _max = self._call_stack_depth + bound
        return self.get_callstack_safe_bounds(_min, _max)

    def up(self):
        func_states = self._state_machine.curr_diff.get_function_states()
        if self._call_stack_depth < len(func_states):
            self._call_stack_depth += 1
        _min = 0
        _max = self._call_stack_depth + 1
        return self.get_callstack_safe_bounds(_min, _max)

    def down(self):
        if self._call_stack_depth > 0:
            self._call_stack_depth -= 1
        _min = 0
        _max = self._call_stack_depth
        return self.get_callstack_safe_bounds(_min, _max)

    def get_breakpoint(self, id):
        for b in self.breakpoints:
            if b.id == id:
                return b
        return None

    def add_breakpoint(self, lineno=None, filename="", funcname="", cond=""):
        # Find next breakpoint id
        if not self.breakpoints:
            id = 1
        else:
            id = max([b.id for b in self.breakpoints]) + 1

        if not filename:
            filename = self.curr_diff.file_name

        if not lineno and funcname:
            if funcname not in self._source_map:
                return None
            # TODO: Need filename here as well
            source = self.get_source_for_func(funcname)
            start = source["start"]
            code = source["code"]
            startline = start + 1
            endline = start + len(code) - 1
            breakpoint = FunctionBreakpoint(id, funcname, filename, startline, endline)
        else:
            try:
                lineno = int(lineno)
            except (ValueError, TypeError):
                lineno = self.curr_line

            # Find the code object corresponding to this line number and
            # filename
            source = self.find_source_for_location(filename, lineno)
            lineno = self.find_next_executable_line(lineno, source)

            breakpoint = Breakpoint(id, lineno, filename, cond)

        self.breakpoints.append(breakpoint)
        return breakpoint

    def get_source_for_func(self, funcname=None):
        source = self._source_map[funcname or self.curr_diff.func_name]
        return source

    def find_source_for_location(self, filename, line_number):
        for func_name, source in self._source_map.items():
            if source["filename"] == filename:
                starting_line = source["start"]
                code = source["code"]
                end_line = starting_line + len(code)

                if not (starting_line <= line_number < end_line):
                    continue

                return source
        else:
            return None

    def is_executable(self, line):
        line = line.strip()
        return bool(line) and not line.startswith("#")

    def is_current_line_executable(self, line_number):
        source = self.get_source_for_func()
        start = source["start"]
        code = source["code"]

        try:
            return self.is_executable(code[line_number - start])
        except IndexError:
            return False

    def find_next_executable_line(
        self, line_number, source=None, filename=None, funcname=None
    ):
        if source:
            starting_line, source_code = source["start"], source["code"]
        else:
            source = self.get_source_for_func(funcname)
            starting_line = source["start"]
            source_code = source["code"]

        try:
            while not self.is_executable(source_code[line_number - starting_line]):
                line_number += 1
            # function definition is not executable
            if line_number == starting_line:
                return None
            else:
                return line_number
        except IndexError:
            return None

    def find_prev_executable_line(
        self, line_number, source=None, filename=None, funcname=None
    ):
        if source:
            starting_line, source_code = source["start"], source["code"]
        else:
            source = self.get_source_for_func(funcname)
            starting_line = source["start"]
            source_code = source["code"]

        try:
            while not self.is_executable(source_code[line_number - starting_line]):
                line_number -= 1
            # function definition is not executable
            if line_number == starting_line:
                return None
            else:
                return line_number
        except IndexError:
            return None

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

    def add_watchpoint(self, expression):
        # Find next breakpoint id
        if not self.watchpoints:
            next_wp_id = 1
        else:
            next_wp_id = max([b.id for b in self.watchpoints]) + 1

        new_wp = Watchpoint(next_wp_id, expression)
        new_wp.init(self.curr_state)
        self.watchpoints.append(new_wp)
        return new_wp

    def remove_watchpoint(self, id):
        b = self.get_watchpoint(id)
        if b is not None:
            self.watchpoints.remove(b)
            return True
        return False
