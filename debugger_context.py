from typing import List, Dict, Any


class DebuggerContext(object):

    def __init__(self):
        # Contains diffs between states
        self._diffs: List[ExecStateDiff] = list()
        # Current state that is built incrementally from diffs recorded during
        # execution of the tracer
        self._current_state: Dict[str, Any] = dict()
        # Dictionary that contains source code objects for each
        self._source_dict = dict()

        # True if we are at the start of the current frame
        self._at_start = False
        # True if we are the end of the current frame
        self._at_end = False

        # Current execution point
        self._exec_point = 0
        self._running = False

    def step_forward(self):
        ''' Step forward one instruction at a time '''
        if self._exec_point < len(self._diffs) - 1:
            self._exec_point += 1
            diff = self._diffs[self._exec_point]
            self._current_state.update(diff.changed)
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
            # Filter out variables, that did not exist in the scope from the
            # previous
            for d in diff.added:
                self.vars.pop(d)
            self._at_start = False
        else:
            self._at_start = True

        self._at_end = False
