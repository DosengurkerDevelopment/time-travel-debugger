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
    """Helper class for managing the absolut states of functions"""

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
                self._func_states.update(
                    new_diff.func_name, new_diff.changed.copy()
                )
            elif new_diff.action == Action.EXCEPTION:
                pass
            else:
                raise ValueError(f"Invalid Action: '{new_diff.action}'")

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
                    new_diff.func_name,
                    prev_diff.added.copy(),
                    prev_diff.updated.copy(),
                )
            elif prev_diff.action == Action.EXCEPTION:
                pass
            else:
                raise Exception(f"Invalid Action: '{prev_diff.action}'")

            if prev_diff.action == Action.RET:
                # skip the implicit return statement and the line of callee
                self._exec_point -= 1

            #  print(self._func_states)

    @property
    def at_start(self):
        return self._exec_point < 2

    @property
    def at_end(self):
        # if the current diff is the last, or if we reached an Exception
        return (
            self._exec_point == len(self._exec_state_diffs) - 1
            or self.curr_diff.action == Action.EXCEPTION
        )

    @property
    def curr_line(self):
        return self.curr_diff.lineno

    @property
    def curr_diff(self):
        return self._exec_state_diffs[self._exec_point]

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
    def __init__(
        self, exec_state_diffs: List[ExecStateDiff], source_map, update
    ):
        # Dictionary that contains source code objects for each frame
        self._source_map = source_map
        # The current state of variables:
        self._state_machine = StateMachine(exec_state_diffs)

        self._breakpoints = []
        self._watchpoints = []
        self._call_stack_depth = 0
        # que of lines in callstack, after moving down the callstack
        self._call_stack_return_lines = []

        self._update = update

    def trigger_update(func):
        """triggers a UI update by calling the corresponding method for the
        currently used UI"""

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
            # Break at the first line if we're going forward
            if self._state_machine.direction == Direction.FORWARD:
                return self.is_at_line(bp.startline)
            # Otherwise we want to break at the last line of the function
            # a.k.a the first line from behind
            if self._state_machine.direction == Direction.BACKWARD:
                return self.is_at_line(bp.endline)
        else:
            return self.is_at_line(bp.lineno) and bp.eval_condition(
                self.curr_state
            )

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
    def step_to_index(self, index, ignore_breakpoints=False):
        def break_():
            return self.break_at_current() and not ignore_breakpoints

        while index < self._state_machine._exec_point and not break_():
            self._state_machine.backward()

        while index > self._state_machine._exec_point and not break_():
            self._state_machine.forward()

        return self.break_at_current()

    def next(self):
        self.until()

    def previous(self):
        self.until(direction=Direction.BACKWARD)

    @trigger_update
    def finish(self):
        curr_depth = self._state_machine.curr_depth
        # only take in account return actions that happened in the same
        # function scope (in the same depth)
        # print(curr_depth)
        while (
            not (
                curr_depth == self._state_machine.curr_depth + 1
                and self._state_machine.curr_diff.action == Action.RET
            )
            and not self._state_machine.at_end
        ):
            self._state_machine.forward()
            # print(curr_depth)

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
    def until(self, line_no=0, file_name="", direction=Direction.FORWARD):
        func_name = self.curr_diff.func_name
        if line_no:
            target = line_no
        else:
            if direction == Direction.FORWARD:
                target = self.curr_line + 1
            else:
                target = self.curr_line - 1

        # depending on the move dir define action and limits of the until
        # command
        if direction == Direction.FORWARD:
            move = self._state_machine.forward
            at_limit = lambda: self.at_end
            stepped_out_of_function =\
                    lambda: self.curr_diff.action == Action.RET

            # find next executable line for target
            # if there is no executable line in the current function run till end
            target = self.find_next_executable_line(target)
            # make sure we dont stay at the same line
            self._state_machine.forward()
        else:
            move = self._state_machine.backward
            at_limit = lambda: self.at_start
            stepped_out_of_function =\
                    lambda: self._state_machine.next_action == Action.CALL

            # find prev executable line for target
            # if there is no executable line in the current function run till end
            target = self.find_prev_executable_line(target)
            # make sure we dont stay at the same line
            self._state_machine.backward()

        #  print(f"target: {target}")

        while not at_limit():
            # when stepping out of function act as next or previous (stay at
            # point after return or before call)
            if not target and stepped_out_of_function():
                break
            if self.curr_line == target:
                # if filename was given, check if current filename matches
                if file_name:
                    if file_name == self.curr_diff.file_name:
                        break
                # otherwise dont check for filename
                else:
                    break
            move()

    def get_callstack_safe_bounds(self, _min, _max):
        """ get callstack with safe min and max bounds """
        func_states = self._state_machine.curr_diff.get_function_states()
        call_stack = []
        for state in func_states:
            call_stack = call_stack + [(state.func_name, state.file_name)]
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

    @trigger_update
    def up(self):
        # restore the target line from the call_stack queue.
        try:
            target = self._call_stack_return_lines.pop()
            self.until(line_no=target)
        except:
            pass
        return self.get_callstack_safe_bounds(0, self._call_stack_depth)


    @trigger_update
    def down(self):
        if not self._state_machine.curr_depth == 0:
            # store the current line, for later, when we want to move up again.
            self._call_stack_return_lines.append(self.curr_line)
            # move backwards out of the function (-1 will be invalid target and thus
            # just run backwards till call)
            self.until(line_no= -1, direction = Direction.BACKWARD)
        return self.get_callstack_safe_bounds(0, self._call_stack_depth)

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

        if not lineno and funcname:
            if funcname not in self._source_map:
                return None
            # TODO: Need filename here as well
            source = self.get_source_for_func(funcname)
            start = source["start"]
            code = source["code"]
            filename = filename or source["filename"]
            startline = start + 1
            endline = start + len(code) - 1
            breakpoint = FunctionBreakpoint(
                id, funcname, filename, startline, endline
            )
        else:
            try:
                lineno = int(lineno)
            except (ValueError, TypeError):
                lineno = self.curr_line

            # Find the code object corresponding to this line number and
            # filename
            filename = self.curr_diff.file_name
            source = self.find_source_for_location(filename, lineno)
            lineno = self.find_next_executable_line(lineno, source)

            breakpoint = Breakpoint(id, lineno, filename, cond)

        self.breakpoints.append(breakpoint)
        return breakpoint

    def get_source_for_func(self, funcname=None):
        source = self._source_map[funcname or self.curr_diff.func_name]
        return source

    def get_func_name_for_line(self, line_no):
        for name, src in self.source_map.items():
            start_line = src["start"]
            last_line = start_line + len(src["code"]) -1
            code_lines = list(range(start_line, last_line))
            if line_no in code_lines:
                return name
        # no such line in the sourcemap, so return None
        return None

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
        # find funcname, if not given:
        if not funcname:
            funcname = self.get_func_name_for_line(line_number)
            #  print(funcname)
        # if not found return None
        if not funcname:
            return None
        if source:
            starting_line, source_code = source["start"], source["code"]
        else:
            source = self.get_source_for_func(funcname)
            starting_line = source["start"]
            source_code = source["code"]

        try:
            while not self.is_executable(
                source_code[line_number - starting_line]
            ):
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
        # find funcname, if not given:
        if not funcname:
            funcname = self.get_func_name_for_line(line_number)
        # if not found return None
        if not funcname:
            return None
        if source:
            starting_line, source_code = source["start"], source["code"]
        else:
            source = self.get_source_for_func(funcname)
            starting_line = source["start"]
            source_code = source["code"]

        try:
            while not self.is_executable(
                source_code[line_number - starting_line]
            ):
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
