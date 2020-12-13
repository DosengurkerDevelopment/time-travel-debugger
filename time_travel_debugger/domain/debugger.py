from typing import List
from ..model.watchpoint import Watchpoint
from ..model.breakpoint import Breakpoint
from ..model.exec_state_diff import ExecStateDiff, Action
from copy import deepcopy


class StateMachine(object):
    ''' Contains the absolute state of all defined variables of all currently
    active functions '''

    def __init__(self, diffs):
        self._exec_state_diffs = diffs
        self._curr_states = [{}]
        self._curr_state_ptr = 0
        #  start at -1 and step into first diff in start_debugger
        self._exec_point = -1
        # True if we are at the start of the current frame
        self._at_start = True
        # True if we are the end of the current frame
        self._at_end = False

    def get_source_for_function(self, func_name):
        try:
            return self._source_map[func_name]
        except KeyError:
            return None

    def get_source_for_current_frame(self):
        return self._source_map[self.curr_diff.func_name]

    def get_source_for_line(self, line):
        pass

    def get_source_for_current_line(self):
        code = self.get_source_for_current_frame()
        return code["code"][self.curr_line - code["start"]]

    def forward(self):
        ''' steps one step forward if possible and computes the current state
        '''

        if self._exec_point < len(self._exec_state_diffs) - 1:
            prev_depth = self.curr_diff.depth
            self._exec_point += 1
            diff = deepcopy(self.curr_diff)
            if diff.depth > prev_depth:
                # called new function, so create new absolute state with added
                # variables (parameters)
                self._curr_states.append(diff.added.copy())
                self._curr_state_ptr += 1
            elif diff.depth < prev_depth:
                # returned from function, so return to previous absolute state
                # and step one further, since return statements dont do
                # anything
                self._curr_state_ptr -= 1
                self._exec_point += 1
                diff = deepcopy(self.curr_diff)
            else:
                # depth stayed the same, so just update the state
                self.curr_state.update(diff.changed)

            self._at_end = False
        else:
            if self._exec_point < len(self._exec_state_diffs):
                self._at_end = True
        self._at_start = False
        assert self.curr_depth >= 0

    def backward(self):
        ''' steps one step backwards if possible and computes the current state
        '''

        # Check whether we reached the start of the program
        if self._exec_point > 0:
            diff = deepcopy(self._exec_state_diffs[self._exec_point])
            self._exec_point -= 1
            depth_after = self.curr_diff.depth
            if diff.depth > depth_after:
                # called new function previously, so rewind by deleting current
                # context (which is safe, since when going forward we will
                # recreate it)
                self._curr_state_ptr -= 1
                self._curr_states.pop()
            elif diff.depth < depth_after:
                # returned from function previously, so go to absolute state
                # one scope higher (which exists, since we rewind in history,
                # so we have created this scope in a previous execution)
                self._curr_state_ptr += 1
            else:
                # if previous action was return then step to return statement
                # ,since we dont want to step back to the point after
                # the function execution
                if self.curr_diff.action == Action.RET:
                    self._exec_point -= 1
                    self._curr_state_ptr += 1
                    diff = deepcopy(self.curr_diff)
                # depth stayed the same, so rewind updated vars
                self.curr_state.update(diff.changed)
                # and delete added vars
                for k in diff.added:
                    self.curr_state.pop(k)
            self._at_start = False
        else:
            if self._exec_point == 0:
                self._at_start = True
        self._at_end = False
        assert self.curr_depth >= 0

    @property
    def at_start(self):
        return self._at_start

    @property
    def at_end(self):
        return self._at_end

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

    def __init__(self, exec_state_diffs: List[ExecStateDiff], source_map):
        # Dictionary that contains source code objects for each frame
        self._source_map = source_map
        # The current state of variables:
        self._state_machine = StateMachine(exec_state_diffs)

        self._breakpoints = []
        self._watchpoints = []

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
        return self.curr_diff.func_name == func \
            and self.curr_diff.file_name == file

    def is_at_breakpoint(self, bp: Breakpoint):
        if bp.breakpoint_type == Breakpoint.FUNC:
            return self.is_in_function(bp.location, bp.filename)
        else:
            return self.is_at_line(bp.location)

    def start_debugger(self, exec_command, update):
        ''' Interaction loop that is run after the execution of the code inside
        the with block is finished '''
        # since we start at exec_point we have to step once to start at the
        # correct point and update the UI
        self._state_machine.forward()
        update(self._state_machine.curr_state, False)

        while True:
            #  Assemble the vars of the current state of the program
            performed_nav_command = exec_command()

            state = self._state_machine.curr_state

            if performed_nav_command:
                for wp in self.watchpoints:
                    wp.update(state.get(wp.var_name, None))

            update(state, performed_nav_command)

    def step_forward(self):
        ''' Step forward one instruction at a time '''
        self._state_machine.forward()

    def step_backward(self):
        ''' Step backward one step at a time '''
        self._state_machine.backward()

    def next(self):
        # TODO: check if next line is executable at all
        target = self._state_machine.curr_line + 1
        while not self._state_machine.curr_line == target\
                and not self._state_machine.at_end:
            self._state_machine.forward()

    def previous(self):
        # TODO: check if previous line is executable at all
        target = self._state_machine.curr_line - 1
        while not self._state_machine.curr_line == target\
                and not self._state_machine.at_start:
            self._state_machine.backward()

    def finish(self):
        curr_depth = self._state_machine.curr_depth
        # only take in account return actions that happened in the same
        # function scope (in the same depth)
        while not(curr_depth == self._state_machine.curr_depth
                  and self._state_machine.next_action == Action.RET)\
                and not self._state_machine.at_end:
            self._state_machine.forward()

    def start(self):
        curr_depth = self._state_machine.curr_depth
        # only take in account call actions that happened in one function
        # scope lower
        while not(curr_depth == self._state_machine.curr_depth
                  and self._state_machine.curr_diff.action == Action.CALL)\
                and not self._state_machine.at_start:
            self._state_machine.backward()

    def continue_(self):
        self._state_machine.forward()
        while not (self.break_at_current() or self._state_machine.at_end):
            self._state_machine.forward()

    def reverse(self):
        self._state_machine.backward()
        while not (self.break_at_current() or self._state_machine.at_start):
            self._state_machine.backward()

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
                if source['filename'] == filename:
                    # TODO: Encapsulate this in get_source_for_line
                    starting_line = source['start']
                    code = source['code']

                    if starting_line > location:
                        continue

                    if location > starting_line + len(code):
                        continue

                    line = code[starting_line - location + 1]
                    while line.startswith('\n') or line.startswith('#'):
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
