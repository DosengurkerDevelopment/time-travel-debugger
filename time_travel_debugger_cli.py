import inspect
import sys

from tracer import TimeTravelTracer
from debugger_context import DebuggerContext


# TODO: We could actually just inherit from Tracer instead since we end up
# overriding all the methods from Debugger anyway.
class TimeTravelDebugger(object):
    ''' Command line debugger that supports stepping backwards in time. '''

    def __init__(self, file=sys.stdout):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        self._context = None
        self._file = file

        #  super().__init__(file)

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

    def commands(self):
        cmds = sorted([method.replace('_command', '')
                       for method in dir(self.__class__)
                       if method.endswith('_command')])
        return cmds

    def command_method(self, command):
        if command.startswith('#'):
            return None  # Comment

        possible_cmds = [possible_cmd for possible_cmd in self.commands()
                         if possible_cmd.startswith(command)]
        if len(possible_cmds) != 1:
            self.help_command(command)
            return None

        cmd = possible_cmds[0]
        return getattr(self, cmd + '_command')

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
        # Find out which type of breakpoint we want to insert
        if arg.isnumeric():
            # Line breakpoint
            self._context.add_breakpoint(arg, "line")
        elif ':' not in arg:
            # Function breakpoint for different file
            self._context.add_breakpoint(arg, "func")
        else:
            filename, function_name = arg.split(':')
            self._context.add_breakpoint(function_name, filename, "func")

    def breakpoints_command(self):
        ''' List all breakpoints '''
        table_template = "{:^15}|{:^6}|{:^20}|{:^15}|{:^20}"
        header = table_template.format('id', 'type',
                                       'location', 'active', 'condition')

        print(header)
        print('-'*len(header))
        for bp in self._context.breakpoints:
            print(table_template.format(*bp))

    def delete_command(self, arg=""):
        ''' Remove the given breakpoint '''
        self._context.remove_breakpoint(int(arg))

    def disable_command(self, arg=""):
        self._context.disable_breakpoint(int(arg))

    def enable_command(self, arg=""):
        self._context.enable_breakpoint(int(arg))

    def cond_command(self, arg=""):
        ''' Set a conditional breakpoint at the given location '''
        location, condition = arg.split()
        self._context.add_breakpoint(location, "cond", cond=condition)
