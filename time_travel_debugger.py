import sys
from debugger import Debugger


class TimeTravelDebugger(Debugger):

    def __init__(self, file=sys.stdout):
        self.snaps = []

        super().__init__(file)

    def traceit(self, frame, event, arg):
        """Tracing function; called at every line"""
        self.frame = frame
        self.event = event
        self.arg = arg

        if self.stop_here():
            self.interaction_loop()

        return self.traceit
