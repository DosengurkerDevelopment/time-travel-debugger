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
        self._context = None

        super().__init__(file)

    def __enter__(self, *args, **kwargs):
        print("start tracing")
        self._tracer.set_trace()

    def __exit__(self, *args, **kwargs):
        print("stop tracing")
        diffs, source_map = self._tracer.get_trace()
        print(diffs, source_map)
        self._context = DebuggerContext(diffs, source_map)
        self._context.start(
            lambda: input("(debugger) "), self.execute)

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
        curr_vars = self._current_state.frames[-1]

        if not arg:
            self.log(
                "\n".join([f"{var} = {repr(curr_vars[var])}" for var in curr_vars]))
        else:
            try:
                self.log(f"{arg} = {repr(eval(arg, globals(), curr_vars))}")
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")

    def step_command(self, arg=""):
        ''' Step to the next instruction '''
        self._context.step_forward()

    def backstep_command(self, arg=""):
        ''' Step to the previous instruction '''
        self._context.step_backward()

    def list_command(self, arg=""):
        """Show current function. If arg is given, show its source code."""
        display_current_line = self._context.curr_line
        if arg:
            try:
                obj = eval(arg)
                source_lines, line_number = inspect.getsourcelines(obj)
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")
                return
            display_current_line = -1
        else:
            # TODO: replace self.code with the correct code object from the
            # source map
            source_lines, line_number = inspect.getsourcelines(self.code)

        for line in source_lines:
            spacer = ' '
            if line_number == display_current_line:
                spacer = '>'
            elif self._context.is_breakpoint(line_number):
                spacer = '#'
            self.log(f'{line_number:4}{spacer} {line}', end='')
            line_number += 1

    def next_command(self, arg=""):
        ''' Step to the next source line '''
        target = self._context.curr_line + 1
        while not(self._context.is_at_line(target) or self._context.at_end):
            self._context.step_forward()
        self.stepping = True

    def previous_command(self, arg=""):
        ''' Step to the previous source line '''
        target = self._context.curr_line - 1
        while not (self._context.is_at_line(target) or self._context.at_start):
            self._context.step_backward()
        self.stepping = True

    def finish_commmand(self):
        ''' Finsh the current function execution '''
        pass

    def until_command(self, arg=""):
        ''' Execute forward until a given point '''
        pass

    def backuntil_command(self, arg=""):
        ''' Execute backward until a given point '''
        pass

    def continue_command(self, arg=""):
        ''' Continue execution forward until a breakpoint is hit '''
        while not (self._context.break_at_current() or self._context.at_end):
            self._context.step_forward()

    def reverse_command(self, arg=""):
        ''' Continue execution backward until a breakpoint is hit '''
        while not (self._context.break_at_current() or self._context.at_start):
            self._context.step_backward()

    def where_command(self, arg=""):
        ''' Print the call stack '''
        pass

    def up_command(self):
        ''' Move up the call stack '''
        pass

    def down_command(self):
        ''' Move down the call stack '''
        pass

    def watch_command(self, arg=""):
        ''' Insert a watchpoint '''
        pass

    def unwatch_command(self, arg=""):
        ''' Remove a watchpoint '''
        pass

    def break_command(self, arg=""):
        ''' Insert a breakpoint at the given location '''
        pass

    def breakpoints_command(self):
        ''' List all breakpoints '''
        pass

    def delete_command(self, arg=""):
        ''' Remove the given breakpoint '''
        pass

    def disable_commad(self, arg=""):
        ''' Disable the given breakpoint '''
        pass

    def enable_command(self, arg=""):
        ''' Enable the given breakpoint '''
        pass

    def cond_command(self, arg=""):
        ''' Set a conditional breakpoint at the given location '''
        pass
