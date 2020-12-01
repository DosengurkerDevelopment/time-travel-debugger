import inspect
import sys
import readline

from debugger import Debugger


# TODO: We could actually just inherit from Tracer instead since we end up
# overriding all the methods from Debugger anyway.
class TimeTravelDebugger(Debugger):
    ''' Command line debugger that supports stepping backwards in time. '''

    def __init__(self, file=sys.stdout):
        # Stores the respective line number and variable changes for each
        # exection step
        self.diffs = list()
        self.curr_line = None

        self.exec_point = 0
        self.vars = dict()

        self.code = dict()
        self.running = False

        self.at_start = True
        self.at_end = False

        super().__init__(file)

    def _traceit(self, frame, event, arg):
        ''' Internal tracing method '''
        if self.code is None:
            self.code = frame.f_code
        if frame.f_code.co_name != '__exit__':
            self.traceit(frame, event, arg)
        return self._traceit

    def stop_here(self):
        ''' Method to determine whether we need to stop at the current step
        Add all conditions here '''
        line = self.curr_line
        if self.stepping or line in self.breakpoints:
            # TODO: check condition of breakpoint
            # After stopping we want to be interactive again
            self.interact = True
            return True
        else:
            return False

    def debugging_loop(self):
        ''' Interaction loop that is run after the execution of the code inside
        the with block is finished '''
        while self.exec_point < len(self.diffs):
            # The diff of the current execution point
            line, args = self.diffs[self.exec_point]
            self.curr_line = line
            #  Assemble the vars of the current state of the program
            if self.stop_here():
                # Get a command
                command = input("(debugger) ")
                self.execute(command)

    def __enter__(self, *args, **kwargs):
        sys.settrace(self._traceit)

    def __exit__(self, *args, **kwargs):
        sys.settrace(None)
        self.debugging_loop()

    def traceit(self, frame, event, arg):
        ''' Record the execution inside the with block.
        We do not store the complete state for each execution point, instead
        we calculate the difference and store a 'diff' which contains the old
        and the new value such that we can easily restore the state without
        having to backtrack to the beginning.
        '''

        if frame.f_code.co_name not in self.code:
            self.code[frame.f_code.co_name] = frame.f_code
        # Store the state of the previous execution point
        prev = self.last_vars.items()
        # Compute diff
        diff = self.changed_vars(frame.f_locals)
        # Only store previous values that got changed by the current step
        prev = {x: y for x, y in prev if x in diff}
        self.diffs.append((frame.f_lineno, (prev, diff)))
        return self.traceit

    def command_method(self, command):
        if command.startswith('#'):
            return None  # Comment

        possible_cmds = [possible_cmd for possible_cmd in self.commands()
                         if possible_cmd.startswith(command)]
        if len(possible_cmds) != 1 and command not in possible_cmds:
            self.help_command(command)
            return None

        cmd = possible_cmds[0]

        return getattr(self, cmd + '_command')

    def print_command(self, arg=""):
        ''' Print all variables or pass an expression to evaluate in the
        current context '''
        # Shorthand such that the following code is not as lengthy
        vars = self.vars

        print(
            f"{self.diffs[self.exec_point]} - {self.exec_point+1}/{len(self.diffs)}")

        if not arg:
            self.log("\n".join([f"{var} = {repr(vars[var])}" for var in vars]))
        else:
            try:
                self.log(f"{arg} = {repr(eval(arg, globals(), vars))}")
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")

    def step_forward(self):
        ''' Step forward one instruction at a time '''
        # Check whether we reached the end of the program
        if self.exec_point < len(self.diffs) - 1:
            self.exec_point += 1
            new_line, (_, var_diff) = self.diffs[self.exec_point]
            self.vars.update(var_diff)
            self.curr_line = new_line
            self.at_end = False
        else:
            self.at_end = True

        self.at_start = False
        return self.at_end

    def step_backward(self):
        ''' Step backward one step at a time '''
        # Check whether we reached the start of the program
        if self.exec_point > 0:
            new_line, (var_old, var_diff) = self.diffs[self.exec_point]
            self.exec_point -= 1
            # Filter out variables, that did not exist in the scope from the
            # previous
            for d in var_diff:
                if d in self.vars and d not in var_old:
                    self.vars.pop(d)
            self.curr_line = new_line
            self.at_start = False
        else:
            self.at_start = True

        self.at_end = False
        return self.at_start

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

    def help_command(self, command=""):
        """Give help on given command. If no command is given, give help on all"""
        if command:
            possible_cmds = [possible_cmd for possible_cmd in self.commands()
                             if possible_cmd.startswith(command)]

            if len(possible_cmds) == 0:
                self.log(
                    f"Unknown command {repr(command)}. Possible commands are:")
                possible_cmds = self.commands()
            elif len(possible_cmds) > 1:
                self.log(
                    f"Ambiguous command {repr(command)}. Possible expansions are:")
        else:
            possible_cmds = self.commands()

        for cmd in possible_cmds:
            method = self.command_method(cmd)
            # Get rid of any unnecessary whitespace that may occur in a
            # docstring (such as newline or tab)
            doc = ' '.join(method.__doc__.strip().split())
            self.log(f"{cmd:15}-- {doc}")


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
        pass

    def reverse_command(self, arg=""):
        ''' Continue execution backward until a breakpoint is hit '''
        pass

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
