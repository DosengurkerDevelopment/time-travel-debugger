from typing import List, Dict, Any
from exec_state_diff import ExecStateDiff

# contains the absolute state of all defined variables of all currently active functions
class CurrentState(object):
    def __init__(self):
        self._states = []

    def update(diff:ExecStateDiff):
        depth = diff.depth
        self._states[depth].update(diff.after)

    def revert(diff:ExecStateDiff):
        depth = diff.depth
        if depth < len(self._states):
            # function return got called in diff, so go to the last functions state
            self._states.pop()
        else:
            # revert the addition and changes of variables in current function scope from
            # diff
            for d in diff.added:
                    self._states[depth].pop(d.after)
            for d in diff.updated:
                self._states[depth].update(d.before)


class DebuggerContext(object):

    def __init__(self, exec_state_diffs: List[ExecStateDiff], source_map):
        # Contains diffs between states
        self._exec_state_diffs = exec_state_diffs
        # Dictionary that contains source code objects for each frame
        self._source_map = source_map
        # The current state of variables:
        self._current_state = CurrentState()

        # True if we are at the start of the current frame
        self._at_start = True
        # True if we are the end of the current frame
        self._at_end = False

        # Current execution point
        self._exec_point = 0
        self._running = False
        self._stepping = True

        self._breakpoints = []

    def step_forward(self):
        ''' Step forward one instruction at a time '''
        if self._exec_point < len(self._diffs) - 1:
            self._exec_point += 1
            diff = self._diffs[self._exec_point]
            self._current_state.update(diff)
            self._at_end = False
        else:
            self._at_end = True

        self._at_start = False

    def step_backward(self):
        ''' Step backward one step at a time '''
        # Check whether we reached the start of the program
        if self._exec_point > 0:
            diff = self._diffs[self._exec_point]
            self._exec_point -= 1
            self._current_state.revert(diff)
            self._at_start = False
        else:
            self._at_start = True

        self._at_end = False

    def stop_here(self):
        ''' Method to determine whether we need to stop at the current step
        Add all conditions here '''
        if self._stepping or line in self._breakpoints:
            # TODO: check condition of breakpoint
            # After stopping we want to be interactive again
            self.interact = True
            return True
        else:
            return False


    def start(self, get_input, execute):
        ''' Interaction loop that is run after the execution of the code inside
        the with block is finished '''
        while self._exec_point < len(self._exec_state_diffs):
            # The diff of the current execution point
            line, args = self._exec_state_diffs[self._exec_point]
            #  self.curr_line = line
            #  Assemble the vars of the current state of the program
            if self.stop_here():
                # Get a command
                command = get_input()
                execute(command, self._current_state)
