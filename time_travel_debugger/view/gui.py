import functools
from pygments import highlight, lexers, formatters, styles
from ipywidgets import Output, Button, GridspecLayout, VBox, HBox, HTML
from IPython.core.display import display, HTML, clear_output

from ..domain.debugger import TimeTravelDebugger
from ..domain.tracer import TimeTravelTracer


class GUI(object):

    _SYMBOLS = {
        "step": {"symbol": "\u2BC8", "button": None},
        "next": {"symbol": "\u23ED", "button": None},
        "backstep": {"symbol": "\u2BC7", "button": None},
        "previous": {"symbol": "\u23EE", "button": None},
        "finish": {
            "symbol": "finish",
        },
        "start": {"symbol": "start", "button": None},
    }

    def __init__(self):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        self._debugger = None

        self._lexer = lexers.get_lexer_by_name("Python")
        self._code_output = Output(layout={"border": "1px solid black"})
        self._var_output = Output(layout={"border": "1px solid black"})

        for key, item in self._SYMBOLS.items():
            self.register_button(key, item["symbol"])

        buttons = VBox(
            [
                HBox(
                    [
                        self._SYMBOLS["backstep"]["button"],
                        self._SYMBOLS["step"]["button"],
                    ]
                ),
                HBox(
                    [
                        self._SYMBOLS["previous"]["button"],
                        self._SYMBOLS["next"]["button"],
                    ]
                ),
                HBox(
                    [
                        self._SYMBOLS["start"]["button"],
                        self._SYMBOLS["finish"]["button"],
                    ]
                ),
            ]
        )

        display(HBox([self._code_output, self._var_output, buttons]))

    def __enter__(self, *args, **kwargs):
        self._tracer.set_trace()

    def __exit__(self, *args, **kwargs):
        diffs, source_map = self._tracer.get_trace()
        self._debugger = TimeTravelDebugger(diffs, source_map, self.update)
        self._debugger.start_debugger()

    def register_button(self, key, description):
        button = Button(description=description)
        func = getattr(self, key + "_command")
        button.on_click(func)
        self._SYMBOLS[key]["button"] = button

    def update(self, state):
        self._current_state = state

        self._SYMBOLS["previous"]["button"].disabled = self._debugger.at_start
        self._SYMBOLS["start"]["button"].disabled = self._debugger.at_start
        self._SYMBOLS["backstep"]["button"].disabled = self._debugger.at_start

        self._SYMBOLS["next"]["button"].disabled = self._debugger.at_end
        self._SYMBOLS["finish"]["button"].disabled = self._debugger.at_end
        self._SYMBOLS["step"]["button"].disabled = self._debugger.at_end

        with self._code_output:
            clear_output(wait=True)
            self.list_command()

        with self._var_output:
            clear_output(wait=True)
            self.print_command()

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
        print(*objects, sep=sep, end=end, flush=True)

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
                self.log(f"Unknown command {repr(command)}. Possible commands are:")
                possible_cmds = self.commands()
            elif len(possible_cmds) > 1 and command not in possible_cmds:
                self.log(f"Ambiguous command {repr(command)}. Possible expansions are:")
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
        # Shorthand such that the following code is not as lengthy
        curr_vars = self._current_state

        if not arg:
            self.log(
                "\n".join([f"{var} = {repr(curr_vars[var])}" for var in curr_vars])
            )
        else:
            try:
                self.log(f"{arg} = {repr(eval(arg, globals(), curr_vars))}")
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
        if arg:
            try:
                code = self._debugger._source_map[arg]
                source_lines = code["code"]
                line_number = code["start"]
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")
                return
            display_current_line = -1
        else:
            code = self._debugger._source_map[self._debugger.curr_diff.func_name]
            source_lines = code["code"]
            line_number = code["start"]

        block = "".join(source_lines)

        coloured = highlight(
            block,
            lexer=self._lexer,
            formatter=formatters.get_formatter_by_name("16m"),
        )

        for line in coloured.strip().split("\n"):
            spacer = " "
            if line_number == display_current_line:
                spacer = ">"
            elif self._debugger.is_line_breakpoint(line_number):
                spacer = "#"
            print(f"{line_number:4}{spacer} {line}")
            line_number += 1

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
        if not arg:
            return {}
        elif arg.isnumeric():
            # Line
            return {"line_no": int(arg)}
        elif ":" not in arg:
            # Function name
            try:
                line_no = int(source_map[arg]["start"])
            except KeyError:
                return "No such function!"
            return {"line_no": line_no}
        else:
            # we have either <filename>:<line_number>
            # or <filename>:<function_name>
            file_name, line_or_func = arg.split(":")
            if line_or_func.isnumeric():
                line_no = int(line_or_func)
            else:
                #  parse func name to its starting line
                try:
                    line_no = int(source_map[line_or_func]["start"])
                except KeyError:
                    return "No such function!"
                #  parse func name to its starting line
                line_no = int(source_map[line_or_func]["start"])
            return {"file_name": file_name, "line_no": line_no}

    def until_command(self, arg=""):
        """ Execute forward until a given point """
        # Find out which type of breakpoint we want to insert
        args = self._parse_until_args(arg, self._debugger.source_map)
        if isinstance(args, dict):
            self._debugger.until(**args)
        elif isinstance(args, str):
            print(args)

    def backuntil_command(self, arg=""):
        """ Execute backward until a given point """
        args = self._parse_until_args(arg, self._debugger.source_map)
        if isinstance(args, dict):
            self._debugger.backuntil(**args)
        elif isinstance(args, str):
            print(args)

    def continue_command(self, arg=""):
        """ Continue execution forward until a breakpoint is hit """
        self._debugger.continue_()

    def reverse_command(self, arg=""):
        """ Continue execution backward until a breakpoint is hit """
        self._debugger.reverse()

    def where_command(self, arg=""):
        """ Print the call stack """
        pass

    def up_command(self, arg=""):
        """ Move up the call stack """
        pass

    def down_command(self, arg=""):
        """ Move down the call stack """
        pass

    def watch_command(self, arg=""):
        """ Insert a watchpoint """
        if not arg:
            table_template = "{:^15}|{:^6}"
            header = table_template.format("id", "watched variable")

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
        res = None
        # Find out which type of breakpoint we want to insert
        if arg.isnumeric():
            # Line breakpoint
            res = self._debugger.add_breakpoint(arg, "line")
        elif ":" not in arg:
            # Function breakpoint for different file
            res = self._debugger.add_breakpoint(arg, "func")
        else:
            filename, function_name = arg.split(":")
            res = self._debugger.add_breakpoint(
                function_name, "func", filename=filename
            )

        if res is not None:
            print(f"Breakpoint {res.id} added.")
        else:
            print("Could not add breakpoint.")

    def breakpoints_command(self, arg=""):
        """ List all breakpoints """
        table_template = "{:^15}|{:^6}|{:^20}|{:^15}|{:^20}"
        header = table_template.format("id", "type", "location", "active", "condition")

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
        location, condition = arg.split(" ", 1)
        self._debugger.add_breakpoint(location, "cond", cond=condition)
