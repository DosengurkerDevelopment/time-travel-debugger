import inspect
import sys

from debugger import Debugger
from tracer import TimeTravelTracer
from debugger_context import DebuggerContext


# TODO: We could actually just inherit from Tracer instead since we end up
# overriding all the methods from Debugger anyway.
class TimeTravelDebugger(Debugger):
    ''' Command line debugger that supports stepping backwards in time. '''

    def __init__(self, file=sys.stdout):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        super().__init__(file)

    def __enter__(self, *args, **kwargs):
        self._tracer.set_trace()

    def __exit__(self, *args, **kwargs):
        diffs, source_map = self._tracer.get_trace()
        debugger_context = DebuggerContext(diffs, source_map)
        debugger_context.start(lambda: input("(debugger) "), self.execute)

    def execute(self, command, current_state):
        self._current_state = current_state
        sep = command.find(' ')
        if sep > 0:
            cmd = command[:sep].strip()
            arg = command[sep + 1:].strip()
        else:
            cmd = command.strip()
            arg = ""

        method = self.command_method(cmd)
        if method:
            method(arg)

    ### COMMANDS ###

    def print_command(self, arg=""):
        ''' Print all variables or pass an expression to evaluate in the
        current context '''
        # Shorthand such that the following code is not as lengthy
        #  vars = self._current_state[-1]

        #  print(
            #  f"{self.diffs[self.exec_point]} - {self.exec_point+1}/{len(self.diffs)}")

        if not arg:
            self.log("\n".join([f"{var} = {repr(vars[var])}" for var in vars]))
        else:
            try:
                self.log(f"{arg} = {repr(eval(arg, globals(), vars))}")
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")

    def step_command(self, arg=""):
        ''' Step to the next instruction '''
        self.step_forward()
        self.stepping = True

    def backstep_command(self, arg=""):
        ''' Step to the previous instruction '''
        self.step_backward()
        self.stepping = True

    def next_command(self, arg=""):
        ''' Step to the next source line '''
        next_line = self.curr_line + 1
        while (self.curr_line != next_line and not self.at_end):
            self.step_forward()
        self.stepping = True

    def previous_command(self, arg=""):
        ''' Step to the previous source line '''
        next_line = self.curr_line - 1
        while (self.curr_line != next_line and not self.at_start):
            self.step_backward()
        self.stepping = True

    def list_command(self, arg=""):
        """Show current function. If arg is given, show its source code."""
        display_current_line = self.curr_line
        if arg:
            try:
                obj = eval(arg)
                source_lines, line_number = inspect.getsourcelines(obj)
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")
                return
            display_current_line = -1
        else:
            source_lines, line_number = inspect.getsourcelines(self.code)

        for line in source_lines:
            spacer = ' '
            if line_number == display_current_line:
                spacer = '>'
            elif line_number in self.breakpoints:
                spacer = '#'
            self.log(f'{line_number:4}{spacer} {line}', end='')
            line_number += 1
