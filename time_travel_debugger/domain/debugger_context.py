from typing import List
from ..model.breakpoint import Breakpoint
from ..model.exec_state_diff import ExecStateDiff
from copy import deepcopy

# Contains the absolute state of all defined variables of all currently active
# functions


class StateMachine(object):
    def __init__(self, diffs):
        self._exec_state_diffs = diffs
        self._curr_state = {}
        self._exec_point = 0
        # True if we are at the start of the current frame
        self._at_start = True
        # True if we are the end of the current frame
        self._at_end = False

    def forward(self):
        '''
        steps one step forward if possible and computes the current state
        '''

        if self._exec_point < len(self._exec_state_diffs) - 1:
            self._exec_point += 1
            diff = deepcopy(self.curr_diff)
            print(diff)
            self._curr_state.update(diff.changed)
            self._at_end = False
        else:
            self._at_end = True
        self._at_start = False
        print(self._curr_state)

    def backward(self):
        '''
        steps one step backwards if possible and computes the current state
        '''

        # Check whether we reached the start of the program
        if self._exec_point > 0:
            diff = deepcopy(self._exec_state_diffs[self._exec_point])
            self._exec_point -= 1
            # rewind updated vars
            self._curr_state.update(diff.changed)
            # delete added vars
            for k in diff.added:
                try:
                    self._curr_state.pop(k)
                except KeyError:
                    pass
            self._at_start = False
        else:
            self._at_start = True

        self._at_end = False
        print(self._curr_state)

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
    def curr_state(self):
        return self._curr_state


class DebuggerContext(object):

    def __init__(self, exec_state_diffs: List[ExecStateDiff], source_map):
        # Dictionary that contains source code objects for each frame
        self._source_map = source_map
        # The current state of variables:
        self._state_machine = StateMachine(exec_state_diffs)

        self._running = False
        self._stepping = True

        self._breakpoints = []

    def stop_here(self):
        ''' Method to determine whether we need to stop at the current step
        Add all conditions here '''
        if self._stepping or self.break_here():
            # After stopping we want to be interactive again
            self.interact = True
            return True
        else:
            # TODO: Don't we have to set self.interact = false ?
            return False

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

    def is_at_line(self, line):
        return self.curr_line == line

    def is_in_function(self, func, file):
        return self.curr_diff.func_name == func \
            and self.curr_diff.file_name == file

    def is_at_breakpoint(self, bp):
        if bp.breakpoint_type == Breakpoint.FUNC:
            return self.is_in_function(bp.location, bp.filename)
        else:
            return self.is_at_line(bp.location)

    def start(self, get_command, exec_command):
        ''' Interaction loop that is run after the execution of the code inside
        the with block is finished '''
        while not self._state_machine.at_end:
            #  Assemble the vars of the current state of the program
            if self.stop_here():
                # Get a command
                exec_command(get_command(), self._state_machine.curr_state)

    def step_forward(self):
        ''' Step forward one instruction at a time '''
        self._state_machine.forward()

    def step_backward(self):
        ''' Step backward one step at a time '''
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

            # Find the code object corresponding to this line number and filename
            for source in self._source_map.values():
                if source['filename'] == filename:
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
                # TODO: What to do if we can't find a matching code object ?
                return False

        new_bp = Breakpoint(next_bp_id, location, filename, bp_type, cond)
        self.breakpoints.append(new_bp)
        return True

    def remove_breakpoint(self, id):
        b = self.get_breakpoint(id)
        if b is not None:
            self.breakpoints.remove(b)

    def disable_breakpoint(self, id):
        breakpoint = self.get_breakpoint(id)
        breakpoint.disable()

    def enable_breakpoint(self, id):
        breakpoint = self.get_breakpoint(id)
        breakpoint.enable()
