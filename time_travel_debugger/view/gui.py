from IPython.core.display import clear_output, display, Markdown
from ipywidgets import (
    AppLayout,
    Button,
    HBox,
    IntSlider,
    Layout,
    Output,
    VBox,
    Label,
    HTML,
    Text,
)
from pygments import formatters, highlight, lexers

from ..domain.debugger import TimeTravelDebugger
from ..domain.tracer import TimeTravelTracer


class GUI(object):

    _BUTTONS = {
        "step": {"symbol": "\u2BC8", "button": None},
        "next": {"symbol": "\u23ED", "button": None},
        "backstep": {"symbol": "\u2BC7", "button": None},
        "previous": {"symbol": "\u23EE", "button": None},
        "finish": {"symbol": "Finish", "button": None},
        "start": {"symbol": "Start", "button": None},
        "continue": {"symbol": "Continue", "button": None},
        "reverse": {"symbol": "Reverse", "button": None},
    }

    def __init__(self):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        self._debugger = None

        self._lexer = lexers.get_lexer_by_name("Python")
        self._code_output = Output(layout=Layout(width="700px"))
        self._var_output = Output(layout=Layout(width="400px"))
        self._diff_slider = IntSlider(readout=False, layout=Layout(width="200px"))
        self._diff_slider.observe(self.slider_command, names="value")

        self._watchpoint_input = Text(layout=Layout(width="200px"))
        self._add_watchpoint = Button(description="Watch expression")
        self._add_watchpoint.on_click(self.watch_command)

        for key, item in self._BUTTONS.items():
            self.register_button(key, item["symbol"])

        self._code_pane = HBox([self._code_output, self._var_output])
        buttons = VBox(
            [
                HBox(self.get_buttons("backstep", "step")),
                HBox(self.get_buttons("previous", "next")),
                HBox(self.get_buttons("start", "finish")),
                HBox(self.get_buttons("continue", "reverse")),
                self._diff_slider,
                HBox([self._add_watchpoint, self._watchpoint_input]),
            ]
        )

        self._layout = AppLayout(
            header=HTML(value="<h1>Time Travel Debugger by DosengurkerDevelopment"),
            left_sidebar=None,
            center=self._code_pane,
            right_sidebar=buttons,
            footer=None,
        )

        display(self._layout)

    def __enter__(self, *args, **kwargs):
        self._tracer.set_trace()

    def __exit__(self, *args, **kwargs):
        diffs, source_map = self._tracer.get_trace()
        self._debugger = TimeTravelDebugger(diffs, source_map, self.update)
        self._debugger.start_debugger()
        self._diff_slider.max = len(diffs)

    def get_button(self, key):
        return self._BUTTONS[key]["button"]

    def get_buttons(self, *keys):
        return [self._BUTTONS[key]["button"] for key in keys]

    def register_button(self, key, description):
        button = Button(description=description)
        func = getattr(self, key + "_command")
        button.on_click(func)
        self._BUTTONS[key]["button"] = button

    def update(self, state):
        self._current_state = state

        self._diff_slider.value = self._debugger._state_machine._exec_point

        self._BUTTONS["previous"]["button"].disabled = self._debugger.at_start
        self._BUTTONS["start"]["button"].disabled = self._debugger.at_start
        self._BUTTONS["backstep"]["button"].disabled = self._debugger.at_start

        self._BUTTONS["next"]["button"].disabled = self._debugger.at_end
        self._BUTTONS["finish"]["button"].disabled = self._debugger.at_end
        self._BUTTONS["step"]["button"].disabled = self._debugger.at_end

        with self._code_output:
            clear_output(wait=True)
            self.list_command()

        with self._var_output:
            clear_output(wait=True)
            self.print_command()
            self.list_watch_command()

    def log(self, *objects, sep=" ", end="\n", flush=False):
        """Like print(), but always sending to file given at initialization,
        and always flushing"""
        print(*objects, sep=sep, end=end, flush=True)

    ### COMMANDS ###

    def print_command(self, arg=""):
        """Print all variables or pass an expression to evaluate in the
        current context"""
        # Shorthand such that the following code is not as lengthy
        curr_vars = self._current_state

        if not arg:
            self.log(
                "\n".join(
                    [
                        f"{var} = {repr(curr_vars[var])}"
                        for var in curr_vars
                        if not var.startswith("__")
                    ]
                )
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
            block, lexer=self._lexer, formatter=formatters.get_formatter_by_name("16m")
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

    def continue_command(self, arg=""):
        """ Continue execution forward until a breakpoint is hit """
        self._debugger.continue_()

    def reverse_command(self, arg=""):
        """ Continue execution backward until a breakpoint is hit """
        self._debugger.reverse()

    def watch_command(self, change):
        """ Insert a watchpoint """
        arg = self._watchpoint_input.value
        res = self._debugger.add_watchpoint(arg)
        if not res:
            print("Could not add watchpoint.")
        else:
            print(f"Added watchpoint with id {res.id}.")

    def list_watch_command(self):
        table_template = "{:^6}|{:^20}|{:^20}"
        header = table_template.format("id", "watched expression", "value")

        print(header)
        print("-" * len(header))
        for wp in self._debugger.watchpoints:
            print(table_template.format(*wp))

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

    def slider_command(self, change):
        self._debugger.step_to_index(change["new"])
