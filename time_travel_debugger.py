import sys
from debugger import Debugger


class TimeTravelDebugger(Debugger):

    def __init__(self, file=sys.stdout):
        self.diffs = []
        self.code = None
        self.last_state = None

        super().__init__(file)

    def _traceit(self, frame, event, arg):
        if self.code is None:
            self.code = frame.f_code
        self.traceit(frame, event, arg)
        return self._traceit

    def __enter__(self, *args, **kwargs):
        sys.settrace(self._traceit)
        return self

    def __exit__(self, *args, **kwargs):
        self.code = None
        sys.settrace(None)
        for line, diff in self.diffs:
            print(line, diff)

    def traceit(self, frame, event, arg):
        # Calculate and store diffs of the current scope/frame
        diff = self.changed_vars(frame.f_locals)
        self.diffs.append((frame.f_lineno, diff))
        return self.traceit
