import inspect
import os
from pprint import pprint

import colorama
from IPython.core.display import Javascript, Markdown, clear_output, display
from ipywidgets import (HTML, AppLayout, Button, GridspecLayout, HBox,
                        IntSlider, Label, Layout, Output, Text, VBox)
from lxml import html
from pygments import formatters, highlight, lexers

from ..domain.debugger import TimeTravelDebugger
from ..domain.tracer import TimeTravelTracer
from ..model.breakpoint import BPType


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

        self._layout = GridspecLayout(4, 4)

        self._lexer = lexers.get_lexer_by_name("Python")
        self._code_output = HTML()

        self._var_output = Output(layout=Layout(overflow_y="scroll"))
        self._diff_slider = IntSlider(readout=False, layout=Layout(width="200px"))
        self._diff_slider.observe(self.slider_command, names="value")

        self._watchpoint_input = Text(layout=Layout(width="200px"))
        self._add_watchpoint = Button(description="Watch expression")
        self._add_watchpoint.on_click(self.watch_command)

        # Need this to disable the default scrolling behaviour in the output widget
        style = """
            <style>
               .jupyter-widgets-output-area .output_scroll {
                    border-radius: unset !important;
                    -webkit-box-shadow: unset !important;
                    box-shadow: unset !important;
                }
            </style>
            """
        display(HTML(style))

        for key, item in self._BUTTONS.items():
            self.register_button(key, item["symbol"])

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

        self._layout[:, 3:4] = buttons
        self._layout[:, 0:3] = HBox(
            [self._code_output], layout=Layout(height="500px", overflow_y="scroll")
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

        self.list_command()

        with self._var_output:
            clear_output(wait=True)
            self.print_command()

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
        template = "|{}|{}|{!r}|"
        header = "| Variable | Type | Value |"
        split = "| --- | --- | --- |"

        variable_table = header + "\n" + split + "\n"
        variable_table += "\n".join(
            template.format(var, type(curr_vars[var]), curr_vars[var])
            for var in curr_vars
        )

        display(Markdown(variable_table))

    def step_command(self, arg=""):
        """ Step to the next instruction """
        self._debugger.step_forward()

    def backstep_command(self, arg=""):
        """ Step to the previous instruction """
        self._debugger.step_backward()

    def list_command(self, arg=""):
        """Show current function. If arg is given, show its source code."""
        display_current_line = self._debugger.curr_line

        code = self._debugger.get_source_for_func()

        source_lines = open(code["filename"]).read()

        css = """
        <style>
        code > span:hover {
            background-color: lightgrey
        }

        .breakpoint {
            background-color: red
        }

        .currentline {
            background-color: green
        }
        </style>
        """

        lexer = lexers.get_lexer_by_name("python")
        formatter = formatters.HtmlFormatter(
            linenos=True,
            anchorlinenos=True,
            full=True,
            linespans=True,
            wrapcode=True,
        )
        coloured = highlight(source_lines, lexer=lexer, formatter=formatter)

        doc = html.fromstring(coloured)

        self._debugger.add_breakpoint(lineno=78)

        for bp in self._debugger.breakpoints:
            if bp.active and bp.breakpoint_type != BPType.FUNC:
                elem = doc.get_element_by_id(f"True-{bp.lineno}", None)
                if elem is not None:
                    elem.set("class", "breakpoint")

        elem = doc.get_element_by_id(f"True-{display_current_line}", None)
        if elem is not None:
            elem.set("class", "currentline")

        for elem in doc.cssselect("code > span"):
            elem.set("onclick", 'alert("hallooo")')

        coloured = html.tostring(doc).decode("utf-8")

        self._code_output.value = css + coloured

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
