import sys
from tracer import ConditionalTracer

class Debugger(Tracer):
    """Interactive Debugger"""

    def __init__(self, file=sys.stdout):
        """Create a new interactive debugger."""
        self.stepping = True
        self.breakpoints = set()
        self.interact = True

        self.frame = None
        self.event = None
        self.arg = None

        super().__init__(file)

class Debugger(Debugger):
    def traceit(self, frame, event, arg):
        """Tracing function; called at every line"""
        self.frame = frame
        self.event = event
        self.arg = arg

        if self.stop_here():
            self.interaction_loop()

        return self.traceit

class Debugger(Debugger):
    def stop_here(self):
        """Return true if we should stop"""
        return self.stepping or self.frame.f_lineno in self.breakpoints

class Debugger(Debugger):
    def interaction_loop(self):
        """Interact with the user"""
        self.print_debugger_status(self.frame, self.event, self.arg)

        self.interact = True
        while self.interact:
            command = input("(debugger) ")
            self.execute(command)

class Debugger(Debugger):
    def step_command(self, arg=""):
        """Execute up to the next line"""
        self.stepping = True
        self.interact = False

class Debugger(Debugger):
    def continue_command(self, arg=""):
        """Resume execution"""
        self.stepping = False
        self.interact = False

class Debugger(Debugger):
    def execute(self, command):
        if command.startswith('s'):
            self.step_command()
        elif command.startswith('c'):
            self.continue_command()


class Debugger(Debugger):
    def commands(self):
        cmds = [method.replace('_command', '')
                for method in dir(self.__class__)
                if method.endswith('_command')]
        cmds.sort()
        return cmds


class Debugger(Debugger):
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


class Debugger(Debugger):
    def execute(self, command):
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

class Debugger(Debugger):
    def help_command(self, command=""):
        """Give help on given command. If no command is given, give help on all"""

        if command:
            possible_cmds = [possible_cmd for possible_cmd in self.commands()
                             if possible_cmd.startswith(command)]

            if len(possible_cmds) == 0:
                self.log(f"Unknown command {repr(command)}. Possible commands are:")
                possible_cmds = self.commands()
            elif len(possible_cmds) > 1:
                self.log(f"Ambiguous command {repr(command)}. Possible expansions are:")
        else:
            possible_cmds = self.commands()

        for cmd in possible_cmds:
            method = self.command_method(cmd)
            self.log(f"{cmd:10} -- {method.__doc__}")



class Debugger(Debugger):
    def print_command(self, arg=""):
        """Print an expression. If no expression is given, print all variables"""
        vars = self.frame.f_locals
        self.log("\n".join([f"{var} = {repr(vars[var])}" for var in vars]))

class Debugger(Debugger):
    def print_command(self, arg=""):
        """Print an expression. If no expression is given, print all variables"""
        vars = self.frame.f_locals

        if not arg:
            self.log("\n".join([f"{var} = {repr(vars[var])}" for var in vars]))
        else:
            try:
                self.log(f"{arg} = {repr(eval(arg, globals(), vars))}")
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")


import inspect

class Debugger(Debugger):
    def list_command(self, arg=""):
        """Show current function."""
        source_lines, line_number = inspect.getsourcelines(self.frame.f_code)

        for line in source_lines:
            self.log(f'{line_number:4} {line}', end='')
            line_number += 1


class Debugger(Debugger):
    def break_command(self, arg=""):
        """Set a breakoint in given line. If no line is given, list all breakpoints"""
        if arg:
            self.breakpoints.add(int(arg))
        self.log("Breakpoints:", self.breakpoints)

class Debugger(Debugger):
    def delete_command(self, arg=""):
        """Delete breakoint in given line. Without given line, clear all breakpoints"""
        if arg:
            try:
                self.breakpoints.remove(int(arg))
            except KeyError:
                self.log(f"No such breakpoint: {arg}")
        else:
            self.breakpoints = set()
        self.log("Breakpoints:", self.breakpoints)


class Debugger(Debugger):
    def list_command(self, arg=""):
        """Show current function. If arg is given, show its source code."""
        if arg:
            try:
                obj = eval(arg)
                source_lines, line_number = inspect.getsourcelines(obj)
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")
                return
            current_line = -1
        else:
            source_lines, line_number = \
                inspect.getsourcelines(self.frame.f_code)
            current_line = self.frame.f_lineno

        for line in source_lines:
            spacer = ' '
            if line_number == current_line:
                spacer = '>'
            elif line_number in self.breakpoints:
                spacer = '#'
            self.log(f'{line_number:4}{spacer} {line}', end='')
            line_number += 1

class Debugger(Debugger):
    def quit_command(self, arg=""):
        """Finish execution"""
        self.breakpoints = []
        self.stepping = False
        self.interact = False

class Debugger(Debugger):
    def assign_command(self, arg):
        """Use as 'assign VAR=VALUE'. Assign VALUE to local variable VAR."""
        sep = arg.find('=')
        if sep > 0:
            var = arg[:sep].strip()
            value = arg[sep + 1:].strip()
        else:
            self.help_command("assign")
            return

        try:
            self.frame.f_locals[var] = eval(value, globals(),
                                            self.frame.f_locals)
        except Exception as err:
            self.log(f"{err.__class__.__name__}: {err}")


def slider(rec):
    lines_over_time = [line for (line, var) in rec]
    vars_over_time = []
    for (line, vars) in rec:
        vars_over_time.append(", ".join(f"{var} = {repr(vars[var])}"
                                        for var in vars))

    # print(lines_over_time)
    # print(vars_over_time)

    template = f'''
    <div class="time_travel_debugger">
      <input type="range" min="0" max="{len(lines_over_time) - 1}"
      value="0" class="slider" id="time_slider">
      Line <span id="line">{lines_over_time[0]}</span>:
      <span id="vars">{vars_over_time[0]}</span>
    </div>
    <script>
       var lines_over_time = {lines_over_time};
       var vars_over_time = {vars_over_time};

       var time_slider = document.getElementById("time_slider");
       var line = document.getElementById("line");
       var vars = document.getElementById("vars");

       time_slider.oninput = function() {{
          line.innerHTML = lines_over_time[this.value];
          vars.innerHTML = vars_over_time[this.value];
       }}
    </script>
    '''
    # print(template)
    return HTML(template)
