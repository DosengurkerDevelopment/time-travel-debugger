import sys
from typing import List
from functools import wraps
from ..model.watchpoint import Watchpoint
from ..model.breakpoint import Breakpoint
from ..model.exec_state_diff import ExecStateDiff, Action
from copy import deepcopy


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
        for k,v in self._func_scopes.items():
            res += f"\t{k}: {v} \n"
        return res

    __repr__ = __str__

    def __getitem__(self, func_name):
        func_pointer = self._func_pointers[func_name]
        #  print(f"func_pointer:{func_pointer}")
        res = self._func_scopes[func_name][func_pointer]
        #  print(f"found item:{res}")
        return res

    def call(self,func_name, params):
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

    def update(self,func_name, changes):
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
        before_update = {key:value.before for (key,value) in updated.items()}
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

    def forward(self):
        """steps one step forward if possible and computes the current state"""

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
                self._func_states.update(new_diff.func_name,new_diff.changed.copy())
            else:
                raise Exception(f"Invalid Action: '{new_diff.action}'")
            if self.next_action == Action.RET:
                # skip the implicit return statement and the line of callee
                self._exec_point +=2
            #  print(self._func_states)

    def backward(self):
        """steps one step backwards if possible and computes the current state"""

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
                self._func_states.revert_update(new_diff.func_name,\
                        prev_diff.added.copy(), prev_diff.updated.copy())
            else:
                raise Exception(f"Invalid Action: '{new_diff.action}'")

            if new_diff.action == Action.RET:
                # skip the implicit return statement and the line of callee
                self._exec_point -=2

            #  print(self._func_states)


    @property
    def at_start(self):
        #  return self._at_start
        return self._exec_point < 2

    @property
    def at_end(self):
        #  return self._at_end
        return self._exec_point== len(self._exec_state_diffs) -1


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
        return self._func_states[self.curr_diff.func_name]

    @property
    def curr_depth(self):
        return self._curr_state_ptr


class TimeTravelDebugger(object):
    def __init__(self, exec_state_diffs: List[ExecStateDiff],
            source_map, update):
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
            call_stack = call_stack+[ state.func_name ]
        print(f"full call stack: {call_stack}")

        print(bound)
        lower_bound = max(0,self._call_stack_depth - bound)
        upper_bound = min(len(call_stack),self._call_stack_depth + bound)
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
