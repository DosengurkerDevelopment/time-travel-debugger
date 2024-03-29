import inspect
import os
import traceback
from pprint import pprint

# DO NOT REMOVE THIS
import readline
import sys

import colorama
from pygments import formatters, highlight, lexers, styles

from ..domain.debugger import TimeTravelDebugger, Direction
from ..domain.tracer import TimeTravelTracer
from ..domain.searchengine import SearchEngine, EventType
from ..model.exec_state_diff import Action
from .completer import CLICompleter

_next_inputs = list()


def next_inputs(*args):
    global _next_inputs
    _next_inputs.extend(reversed(args))


class TimeTravelCLI(object):
    """ Command line debugger that supports stepping backwards in time. """

    NAV_COMMANDS = [
        "backstep",
        "continue",
        "finish",
        "next",
        "previous",
        "reverse",
        "until",
        "backuntil",
        "step",
        "start",
        "up",
        "down",
    ]

    BOLD = "\033[1m"
    END = "\033[0m"

    def __init__(self, file=sys.stdout):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        self._debugger = None
        self._file = file
        self._last_command = ""
        self._draw_update = True
        self._lexer = lexers.get_lexer_by_name("Python")
        self._quit = False

    def __enter__(self, *args, **kwargs):
        self._tracer.set_trace()

    def __exit__(self, *args, **kwargs):
        diffs, source_map = self._tracer.get_trace()
        self._completer = CLICompleter(self.commands())
        readline.set_completer(self._completer.complete)
        readline.parse_and_bind("tab: complete")
        search_engine = SearchEngine()
        self._debugger = TimeTravelDebugger(diffs, source_map, self.update,
            search_engine)
        self._debugger.step_forward()
        self.execute()

    def get_input(self):
        global _next_inputs
        if len(_next_inputs) > 0:
            cmd = _next_inputs.pop()
            print("(debugger) " + cmd)
        else:
            try:
                cmd = input("(debugger) ")
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt", end="")
                return
            except EOFError:
                print("quit")
                return "quit"

        if not cmd:
            return self._last_command
        else:
            self._last_command = cmd
            return cmd

    def is_nav_command(self, cmd):
        return cmd.__name__.split("_")[0] in self.NAV_COMMANDS

    def execute(self):
        command = self.get_input()

        if not command:
            print("\r")
            self.execute()

        sep = command.find(" ")
        if sep > 0:
            cmd = command[:sep].strip()
            arg = command[sep + 1 :].strip()
        else:
            cmd = command.strip()
            arg = ""

        method = self.command_method(cmd)
        if method:
            self._draw_update = self.is_nav_command(method)
            method(arg)
        else:
            self._draw_update = False

        if self._quit:
            return
        else:
            self.execute()

    def update(self, state):
        self._current_state = state

        if self._draw_update:
            # os.system("clear")
            self.list_command()

            for wp in self._debugger.watchpoints:
                if wp.has_changed():
                    print(wp)

            if self._debugger.break_at_current():
                print("Breakpoint hit!")

            if self._debugger.at_end:
                print("Hit end of program")

            diff = self._debugger.curr_diff
            if diff.action == Action.EXCEPTION:
                print("Exception:")
                pprint(diff._tb)

            if self._debugger.at_start:
                print("Hit start of program")

    def commands(self):
        cmds = sorted(
            [
                method.replace("_command", "")
                for method in dir(self.__class__)
                if method.endswith("_command")
            ]
        )
        return cmds

    def command_method(self, command):
        if command.startswith("#"):
            return None  # Comment

        possible_cmds = [
            possible_cmd
            for possible_cmd in self.commands()
            if possible_cmd.startswith(command)
        ]

        if len(possible_cmds) != 1 and command not in possible_cmds:
            self.help_command(command)
            return None

        cmd = possible_cmds[0]
        return getattr(self, cmd + "_command")

    def log(self, *objects, sep=" ", end="\n", flush=False):
        """Like print(), but always sending to file given at initialization,
        and always flushing"""
        print(*objects, sep=sep, end=end, file=self._file, flush=True)

    ### COMMANDS ###
    def help_command(self, command=""):
        """Give help on given command. If no command is given, give help on all"""

        if command:
            possible_cmds = [
                possible_cmd
                for possible_cmd in self.commands()
                if possible_cmd.startswith(command)
            ]

            if len(possible_cmds) == 0:
                self.log(
                    f"Unknown command {repr(command)}. Possible commands are:"
                )
                possible_cmds = self.commands()
            elif len(possible_cmds) > 1 and command not in possible_cmds:
                self.log(
                    f"Ambiguous command {repr(command)}. Possible expansions are:"
                )
        else:
            possible_cmds = self.commands()

        for cmd in possible_cmds:
            method = self.command_method(cmd)
            if method.__doc__ is not None:
                desc = " ".join(method.__doc__.split())
            else:
                desc = ""
            self.log(f"{cmd:15} -- {desc}")

    def print_command(self, arg=""):
        """Print all variables or pass an expression to evaluate in the
        current context"""

        def prettify_classes(obj):
            if hasattr(obj, "__dict__"):
                return vars(obj)
            else:
                return repr(obj)

        # Shorthand such that the following code is not as lengthy
        curr_vars = self._current_state
        if curr_vars:
            if not arg:
                self.log(
                    "\n".join(
                        [
                            f"{var} = {prettify_classes(curr_vars[var])}"
                            for var in curr_vars
                            if not var.startswith("__")
                        ]
                    )
                )
            else:
                try:
                    self.log(
                        f"{arg} = {prettify_classes(eval(arg, globals(), curr_vars))}"
                    )
                except Exception as err:
                    self.log(f"{err.__class__.__name__}: {err}")

    def step_command(self, arg=""):
        """ Step to the next instruction """
        self._debugger.step_forward()

    def backstep_command(self, arg=""):
        """ Step to the previous instruction """
        self._debugger.step_backward()

    def list_command(self, arg=""):
        """Show current function. If arg is given, show its source code."""
        display_current_line = self._debugger.curr_line
        above, below = 0, 0

        args = arg.strip().split()
        use_current = all(x.isnumeric() for x in args)

        if len(args) == 1 and args[0].isnumeric():
            above = below = int(arg)
        elif len(args) == 2 and all(x.isnumeric() for x in args):
            above, below = [int(a) for a in arg.split()]

        if use_current:
            code = self._debugger._source_map[
                self._debugger.curr_diff.func_name
            ]
            source_lines = code["code"]
            line_number = code["start"]
        else:
            # List the given function
            try:
                code = self._debugger._source_map[arg]
                source_lines = code["code"]
                line_number = code["start"]
            except Exception as err:
                self.log(f"No function named {arg}!")
                return
            display_current_line = -1

        coloured = highlight(
            "".join(source_lines),
            lexer=self._lexer,
            formatter=formatters.get_formatter_by_name(
                "16m", style=styles.get_style_by_name("solarized-dark")
            ),
        )

        lines = coloured.strip().split("\n")

        top = 0
        bot = len(lines)

        def clamp(x):
            if x > bot:
                return bot
            if x < top:
                return top
            return x

        if use_current and (above > 0 or below > 0):
            curr_line = self._debugger.curr_line - line_number
            top = clamp(curr_line - above)
            bot = clamp(curr_line + below + 1)

        lines = lines[top:bot]

        for ln, line in enumerate(lines, start=line_number + top):
            spacer = " "
            color = ""
            if ln == display_current_line:
                spacer = ">"
                color = colorama.Back.YELLOW
            elif self._debugger.is_line_breakpoint(ln):
                spacer = "#"
                color = colorama.Back.RED
            print(color + f"{ln:4}{spacer} {line}" + colorama.Style.RESET_ALL)

    def next_command(self, arg=""):
        """ Step to the next source line """
        self._debugger.next()

    def previous_command(self, arg=""):
        """ Step to the previous source line """
        self._debugger.previous()

    def finish_command(self, arg=""):
        """ Finish the current function execution """
        self._debugger.finish()

    def start_command(self, arg=""):
        """ Go to start of the current function call """
        self._debugger.start()

    def _parse_until_args(self, arg, source_map):
        """
        parses the arguments of the until command
        """
        # TODO: this should be outsourced to some util class or whatever, so we
        # can reuse it for the GUI
        func = False
        if not arg:
            return {}
        elif arg.isnumeric():
            # Line
            return {"line_no": int(arg)}
        elif ":" not in arg:
            # Function name
            func = True
            try:
                line_no = int(source_map[arg]["start"]) + 1
            except KeyError:
                return "No such function!"
            return {"line_no": line_no, "func": func}
        else:
            # we have either <filename>:<line_number>
            # or <filename>:<function_name>
            file_name, line_or_func = arg.split(":")
            if line_or_func.isnumeric():
                line_no = int(line_or_func)
            else:
                #  parse func name to its starting line
                func = True
                try:
                    line_no = int(source_map[line_or_func]["start"]) + 1
                except KeyError:
                    return "No such function!"
                #  parse func name to its starting line
                line_no = int(source_map[line_or_func]["start"])
            # Find abs filename:
            for key, value in source_map.items():
                if os.path.basename(value["filename"]) == file_name:
                    file_name = value["filename"]
            return {"file_name": file_name, "line_no": line_no, "func": func}

    def until_command(self, arg=""):
        """ Execute forward until a given point """
        args = self._parse_until_args(arg, self._debugger.source_map)
        if isinstance(args, dict):
            self._debugger.until(**args)
        elif isinstance(args, str):
            print(args)

    def backuntil_command(self, arg=""):
        """ Execute backward until a given point """
        args = self._parse_until_args(arg, self._debugger.source_map)
        if isinstance(args, dict):
            self._debugger.until(**args, direction=Direction.BACKWARD)
        elif isinstance(args, str):
            print(args)

    def continue_command(self, arg=""):
        """ Continue execution forward until a breakpoint is hit """
        self._debugger.continue_()

    def reverse_command(self, arg=""):
        """ Continue execution backward until a breakpoint is hit """
        self._debugger.reverse()

    def search_command(self, arg=""):
        """ {event_type query} - Search for specific events, like variable changes and breakpoint hits """
        if arg:
            try:
                event_type, query = arg.split(" ",1)
                try:
                    results = self._debugger.search(event_type,query)
                    if results == None:
                        print("Wrong search criteria")
                    pprint(results)
                except Exception as err:
                    print(err)

            except ValueError:
                print("Wrong number of arguments!")


    def _print_callstack(self, stack):
        for (frame, (func, file)) in reversed(list(enumerate(stack, start=1))):
            print(f"#{frame}: {self.BOLD}{func}{self.END} at {file}")

    def where_command(self, arg=""):
        """ Print the call stack """
        params = {}
        if arg:
            params["bound"] = int(arg)
        call_stack = self._debugger.where(**params)
        self._print_callstack(call_stack)

    def up_command(self, arg=""):
        """ Move up the call stack """
        call_stack = self._debugger.up()

    def down_command(self, arg=""):
        """ Move down the call stack """
        call_stack = self._debugger.down()

    def watch_command(self, arg=""):
        """ Insert a watchpoint """
        if not arg:
            table_template = "{:^15}|{:^20}|{:^15}"
            header = table_template.format("id", "watched expression", "value")

            print(header)
            print("-" * len(header))
            for wp in self._debugger.watchpoints:
                print(table_template.format(*wp))
        else:
            res = self._debugger.add_watchpoint(arg)
            if not res:
                print("Could not add watchpoint.")
            else:
                print(f"Added watchpoint with id {res.id}.")

    def unwatch_command(self, arg=""):
        """ Remove a watchpoint """
        if not self._debugger.remove_watchpoint(int(arg)):
            print(f"Watchpoint with id {arg} does not exist.")
        else:
            print(f"Successfully removed watchpoint {arg}.")

    def break_command(self, arg=""):
        """ Insert a breakpoint at the given location """
        # Find out which type of breakpoint we want to insert
        if not arg or arg.isnumeric():
            # Line breakpoint
            res = self._debugger.add_breakpoint(lineno=arg)
        elif ":" not in arg:
            # Function breakpoint for current file
            res = self._debugger.add_breakpoint(funcname=arg)
        else:
            filename, funcname = arg.split(":")
            res = self._debugger.add_breakpoint(
                filename=filename, funcname=funcname
            )

        if res is not None:
            print(f"Breakpoint {res.id} added.")
        else:
            print("Could not add breakpoint.")

    def breakpoints_command(self, arg=""):
        """ List all breakpoints """
        table_template = "{:^15}|{:^6}|{:^25}|{:^15}|{:^20}"
        header = table_template.format(
            "id", "type", "location", "active", "condition"
        )

        print(header)
        print("-" * len(header))
        for bp in self._debugger.breakpoints:
            print(table_template.format(*bp))

    def delete_command(self, arg=""):
        """ Remove the given breakpoint """
        self._debugger.remove_breakpoint(int(arg))

    def disable_command(self, arg=""):
        """ Disable the given breakpoint """
        self._debugger.disable_breakpoint(int(arg))

    def enable_command(self, arg=""):
        """ Enable the given breakpoint """
        self._debugger.enable_breakpoint(int(arg))

    def cond_command(self, arg=""):
        """ Set a conditional breakpoint at the given location """
        try:
            lineno, condition = arg.split(" ", 1)
        except ValueError:
            self.log("Cond needs a line number and a condition")
            return
        self._debugger.add_breakpoint(lineno=lineno, cond=condition)

    def quit_command(self, arg=""):
        self._quit = True
