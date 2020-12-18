import os

from IPython.core.display import Markdown, clear_output, display, Javascript
from ipywidgets import (
    ToggleButtons,
    Valid,
    Dropdown,
    HTML,
    Button,
    GridspecLayout,
    HBox,
    IntSlider,
    Layout,
    Output,
    Play,
    Text,
    ToggleButton,
    VBox,
    jsdlink,
)
from lxml import html
from pygments import formatters, highlight, lexers

from ..domain.debugger import TimeTravelDebugger
from ..domain.tracer import TimeTravelTracer
from ..domain.searchengine import SearchEngine
from ..model.breakpoint import BPType

here = os.path.dirname(__file__)
root = os.path.abspath(os.path.join(here, "../../"))
cssfile = open(os.path.join(root, "codestyle.css")).read()
javascript = open(os.path.join(root, "scrollIntoView.js")).read()


class GUI(object):

    _BUTTONS = {
        "step": {
            "description": "",
            "icon": "step-forward",
            "tooltip": "Step to the next instruction",
        },
        "next": {
            "description": "",
            "icon": "fast-forward",
            "tooltip": "Go to the next sourceline",
        },
        "backstep": {
            "description": "",
            "icon": "step-backward",
            "tooltip": "Step to the previous instruction",
        },
        "previous": {
            "description": "",
            "icon": "fast-backward",
            "tooltip": "Go to th previous sourceline",
        },
        "finish": {
            "description": "Finish",
            "tooltip": "Go to the end of the program",
        },
        "start": {
            "description": "Start",
            "tooltip": "Go to the start of the program",
        },
        "continue": {
            "description": "Continue",
            "tooltip": "Continue execution until breakpoint is hit",
        },
        "reverse": {
            "description": "Reverse",
            "tooltip": "Continue execution backwards until breakpoint is hit",
        },
    }

    def __init__(self):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        self._debugger = None

        self._layout = GridspecLayout(7, 4)

        self._code_output = HTML()
        self._var_output = Output()
        self._watchpoint_output = Output()
        self._breakpoint_output = Output()

        display(self._breakpoint_output)

        self._diff_slider = IntSlider(
            min=1,
            readout=False,
            layout=Layout(width="100%"),
            tooltip="Execution timeline",
        )
        self._diff_slider.observe(self._handle_diff_slider, names="value")

        self._autoplay = Play(tooltip="Automatic playback of the execution")
        self._auto_link = jsdlink(
            (self._autoplay, "value"), (self._diff_slider, "value")
        )

        self._speed_slider = IntSlider(
            description="Delay (ms)", min=100, max=1000, step=100, value=500
        )
        self._speed_link = jsdlink(
            (self._speed_slider, "value"), (self._autoplay, "interval")
        )

        self._reverse_autoplay = ToggleButton(
            value=False, icon="history", tooltip="Reverse autoplay"
        )
        self._reverse_autoplay.observe(self._handle_reverse_button)

        self._watchpoint_input = Text(
            layout=Layout(width="200px"),
            placeholder="Enter expression to watch",
        )
        self._add_watchpoint = Button(
            description="Add watchpoint",
            icon="plus",
            tooltip="Add an expression or variable to watch",
        )
        self._add_watchpoint.on_click(self.watch_command)

        self._add_breakpoint = Button(
            icon="plus",
            description="Add breakpoint",
            tooltip="Add a breakpoint",
            name="breakpoint_button",
        )
        self._add_breakpoint.on_click(self._handle_breakpoint)

        self._disable_breakpoint_button = Button(
            icon="eye-slash", tooltip="Disable breakpoint"
        )

        self._breakpoint_dropdown = Dropdown()

        self._function_dropdown = Dropdown()
        self._function_dropdown.disabled = True
        self._breakpoint_type = ToggleButtons(
            options=["Line", "Function", "Conditional"], value="Line"
        )
        self._breakpoint_type.observe(
            self._handle_breakpoint_type, names="value"
        )
        self._condition_input = Text(placeholder="Enter condition")
        self._condition_input.disabled = True
        self._line_input = Text(
            placeholder="Enter line to break at", name="line_input"
        )

        self._search_query_type_dropdown = Dropdown(
            options=["var_change", "func_call", "break_hit"],
            description="Search query type",
        )
        self._search_input = Text(placeholder="Search...")
        self._search_input.observe(self._handle_search_input, names="value")

        self._search_results = Output()
        display(
            self._search_input,
            self._search_results,
            self._search_query_type_dropdown,
        )

        # Remove shadows from scrolling
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
            self.register_button(key, **item)

        self._buttons = HBox(
            [
                VBox(self.get_buttons("backstep", "step")),
                VBox(self.get_buttons("previous", "next")),
                VBox(self.get_buttons("start", "finish")),
                VBox(self.get_buttons("continue", "reverse")),
            ]
        )

        self._layout[0:4, 0:3] = HBox(
            [self._code_output],
            layout=Layout(
                height="500px", overflow_y="scroll", border="2px solid black"
            ),
        )
        self._layout[0:2, 3] = self._var_output
        self._layout[6, :] = self._diff_slider
        self._layout[2:4, 3] = self._watchpoint_output
        self._layout[5, :3] = self._buttons
        self._layout[4, :3] = HBox(
            [self._autoplay, self._speed_slider, self._reverse_autoplay]
        )
        self._layout[4:5, 3] = VBox(
            [self._watchpoint_input, self._add_watchpoint]
        )
        self._layout[6, :] = HBox(
            [
                self._add_breakpoint,
                self._breakpoint_type,
                self._function_dropdown,
                self._line_input,
                self._condition_input,
            ]
        )

        display(self._layout)

    def __enter__(self, *args, **kwargs):
        self._tracer.set_trace()

    def __exit__(self, *args, **kwargs):
        diffs, source_map = self._tracer.get_trace()
        search_engine = SearchEngine()
        self._debugger = TimeTravelDebugger(
            diffs, source_map, self.update, search_engine
        )
        self._debugger.start_debugger()
        self._diff_slider.max = len(diffs) - 1
        self._function_dropdown.options = self._debugger.source_map.keys()

    def get_buttons(self, *keys):
        return [self._BUTTONS[key]["button"] for key in keys]

    def register_button(self, key, **kwargs):
        button = Button(**kwargs)
        func = getattr(self, key + "_command")
        button.on_click(func)
        self._BUTTONS[key]["button"] = button

    def update(self, state=None):
        if state is not None:
            self._current_state = state

        self._diff_slider.value = self._debugger._state_machine._exec_point

        self._BUTTONS["previous"]["button"].disabled = self._debugger.at_start
        self._BUTTONS["start"]["button"].disabled = self._debugger.at_start
        self._BUTTONS["backstep"]["button"].disabled = self._debugger.at_start
        self._BUTTONS["next"]["button"].disabled = self._debugger.at_end
        self._BUTTONS["finish"]["button"].disabled = self._debugger.at_end
        self._BUTTONS["step"]["button"].disabled = self._debugger.at_end

        self._breakpoint_dropdown.options = [
            b.id for b in self._debugger.breakpoints
        ]

        self.list_command()

        with self._var_output:
            clear_output(wait=True)
            self.print_command()

        with self._breakpoint_output:
            clear_output(wait=True)
            self.breakpoints_command()

        with self._watchpoint_output:
            clear_output(wait=True)
            self.list_watch_command()

        display(
            Javascript(
                javascript
                + f'\nscrollToView("True-{self._debugger.curr_line - 10}")'
                + f'\nscrollToView("True-{self._debugger.curr_line + 10}")'
            )
        )

    def log(self, *objects, sep=" ", end="\n", flush=False):
        """Like print(), but always sending to file given at initialization,
        and always flushing"""
        print(*objects, sep=sep, end=end, flush=True)

    # COMMANDS
    def print_command(self, arg=""):
        """Print all variables or pass an expression to evaluate in the
        current context"""
        # Shorthand such that the following code is not as lengthy
        curr_vars = self._current_state
        template = "|`{}`|{}|`{!r}`|"
        header = "| Variable | Type | Value |"
        split = "| --- | --- | --- |"

        variable_table = header + "\n" + split + "\n"
        variable_table += "\n".join(
            template.format(var, type(curr_vars[var]), curr_vars[var])
            for var in curr_vars
            if not var.startswith("__")
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

        css = f"""
        <style>
        {cssfile}
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

        current_line_breakpoint = False

        # Highlight all breakpoints on the current file
        for bp in self._debugger.breakpoints:
            if self._debugger.curr_diff.file_name != bp.abs_filename:
                continue
            if bp.breakpoint_type != BPType.FUNC:
                elem = doc.get_element_by_id(f"True-{bp.lineno}", None)
                if bp.lineno == display_current_line:
                    current_line_breakpoint = True
                if elem is not None:
                    elem.set("class", "breakpoint")
                    if not bp.active:
                        elem.set("class", "inactive")

        elem = doc.get_element_by_id(f"True-{display_current_line}", None)
        if elem is not None:
            if not current_line_breakpoint:
                elem.set("class", "currentline")
            else:
                elem.set("class", "hit")

        coloured = html.tostring(doc).decode("utf-8").strip()

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
        self._debugger.add_watchpoint(expression=arg)
        self.update()

    def list_watch_command(self):
        header = "| ID | Expression | Value |\n"
        split = "|---|---|---|\n"
        template = "|{}|`{}`|`{!r}`|"
        wpstr = header + split

        for wp in self._debugger.watchpoints:
            wpstr += template.format(*wp)

        display(Markdown(wpstr))

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
        header = "| ID | Type | Location | Status | Condition |\n"
        split = "|---|---|---|---|---|\n"

        bpstr = header + split

        for bp in self._debugger.breakpoints:
            bpstr += "|" + "|".join(bp) + "|\n"

        display(Markdown(bpstr))

    def delete_command(self, arg=""):
        """ Remove the given breakpoint """
        self._debugger.remove_breakpoint(int(arg))

    def disable_command(self, arg=""):
        """ Disable the given breakpoint """
        self._debugger.disable_breakpoint(int(arg))

    def enable_command(self, arg=""):
        """ Enable the given breakpoint """
        self._debugger.enable_breakpoint(int(arg))

    def _handle_diff_slider(self, change):
        braked = self._debugger.step_to_index(
            change["new"], ignore_breakpoints=self._autoplay._playing
        )
        if braked:
            self._autoplay._playing = False

    def _handle_reverse_button(self, change):
        self._autoplay.step = -self._autoplay.step

    def _handle_breakpoint(self, change):
        type = self._breakpoint_type.value
        function = self._function_dropdown.value
        line = self._line_input.value
        condition = self._condition_input.value

        if type != "Function":
            if not line.isnumeric():
                self._line_input.value = ""
                self._line_input.placeholder = "Please enter a valid number!"
        if type == "Conditional":
            try:
                eval(condition)
            except SyntaxError:
                if not self._condition_input.value:
                    self._condition_input.placeholder = "Invalid expression!"
                self._condition_input.value = ""

            except NameError:
                pass

        if type == "Function":
            self._debugger.add_breakpoint(funcname=function)
        if type == "Line":
            self._debugger.add_breakpoint(lineno=line)
        if type == "Conditional":
            self._debugger.add_breakpoint(lineno=line, cond=condition)

        self.update()

    def _handle_breakpoint_type(self, change):
        self._function_dropdown.disabled = change["new"] != "Function"
        self._condition_input.disabled = change["new"] != "Conditional"
        self._line_input.disabled = change["new"] == "Function"

    def _handle_search_input(self, change):
        events = self._debugger.search(
            self._search_query_type_dropdown.value, change["new"]
        )
        with self._search_results:
            clear_output()
            print(self._search_query_type_dropdown.value)
            print(change["new"])
            print(events)
