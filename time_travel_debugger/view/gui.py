import os

from IPython.core.display import Markdown, clear_output, display, Javascript
from ipywidgets import (
    GridBox,
    Label,
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
    Tab,
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


class GUI(object):

    _BUTTONS = {
        "backstep": {
            "icon": "step-backward",
            "tooltip": "Step to the previous instruction",
        },
        "step": {
            "icon": "step-forward",
            "tooltip": "Step to the next instruction",
        },
        "previous": {
            "icon": "reply",
            "tooltip": "Go to th previous sourceline",
        },
        "next": {
            "icon": "share",
            "tooltip": "Go to the next sourceline",
        },
        "start": {
            "icon": "arrow-up",
            "tooltip": "Go to the start of the program",
        },
        "finish": {
            "icon": "arrow-down",
            "tooltip": "Go to the end of the program",
        },
        "reverse": {
            "icon": "fast-backward",
            "tooltip": "Continue execution backwards until breakpoint is hit",
        },
        "continue": {
            "icon": "fast-forward",
            "tooltip": "Continue execution until breakpoint is hit",
        },
    }

    def __init__(self):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        self._debugger = None

        self._code_output = HTML()
        self._var_output = Output()
        self._watchpoint_output = Output()
        self._breakpoint_output = Output()

        self._diff_slider = IntSlider(
            min=1,
            readout=False,
            layout=Layout(width="99%"),
            tooltip="Execution timeline",
        )
        self._diff_slider.observe(self._handle_diff_slider, names="value")

        self._autoplay = Play(
            tooltip="Automatic playback of the execution",
            layout=Layout(height="30px"),
        )
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
            value=False,
            icon="history",
            tooltip="Reverse autoplay",
            layout=Layout(width="40px"),
        )
        self._reverse_autoplay.observe(self._handle_reverse_button)

        self._watchpoint_input = Text(
            layout=Layout(width="150px"),
            placeholder="Watch expression",
        )
        self._add_watchpoint = Button(
            icon="plus",
            tooltip="Add an expression or variable to watch",
            layout=Layout(width="50px"),
        )
        self._add_watchpoint.on_click(self.watch_command)

        self._watchpoint_dropdown = Dropdown(
            layout=Layout(width="150px"),
        )
        self._remove_watchpoint = Button(
            icon="trash",
            tooltip="Remove a watchpoint",
            layout=Layout(width="50px"),
        )
        self._remove_watchpoint.on_click(self.unwatch_command)

        self._breakpoint_layout = GridspecLayout(3, 1)

        self._add_breakpoint = Button(
            icon="plus",
            tooltip="Add a breakpoint",
            name="breakpoint_button",
            layout=Layout(width="40px"),
        )
        self._add_breakpoint.on_click(self._handle_breakpoint)

        self._disable_breakpoint_button = Button(
            icon="eye-slash",
            tooltip="Disable breakpoint",
            layout=Layout(width="50px"),
        )
        self._disable_breakpoint_button.on_click(self.disable_command)

        self._remove_breakpoint_button = Button(
            icon="trash",
            tooltip="Remove breakpoint",
            layout=Layout(width="50px"),
        )
        self._remove_breakpoint_button.on_click(self.delete_command)

        self._breakpoint_dropdown = Dropdown(layout=Layout(width="70px"))

        self._function_dropdown = Dropdown(layout=Layout(width="200px"))
        self._function_dropdown.disabled = True
        self._breakpoint_type = Dropdown(
            options=["Line", "Function", "Conditional"],
            value="Line",
            layout=Layout(width="100px"),
        )

        self._breakpoint_type.observe(
            self._handle_breakpoint_type, names="value"
        )

        self._condition_input = Text(
            placeholder="Enter condition", layout=Layout(width="200px")
        )
        self._condition_input.disabled = True

        self._line_input = Text(
            placeholder="Line Number",
            name="line_input",
            layout=Layout(width="100px"),
        )

        self._breakpoint_layout = VBox(
            [
                HBox(
                    [
                        self._add_breakpoint,
                        self._breakpoint_type,
                        self._function_dropdown,
                        self._line_input,
                        self._condition_input,
                        self._breakpoint_dropdown,
                        self._remove_breakpoint_button,
                        self._disable_breakpoint_button,
                    ]
                ),
                self._breakpoint_output,
            ]
        )

        self._search_input = Text(placeholder="Search...")
        self._search_input.observe(self._handle_search_input, names="value")

        self._search_results = Output()
        self._search_layout = VBox(
            [
                self._search_input,
                self._search_results,
            ]
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

        self._code_layout = GridspecLayout(4, 4, grid_gap="20px")

        self._code_layout[0:4, 0:3] = HBox(
            [self._code_output],
            layout=Layout(
                height="500px", overflow_y="scroll", border="2px solid black"
            ),
        )
        self._code_layout[0:2, 3] = self._var_output
        self._code_layout[2:4, 3] = VBox(
            [
                HBox([self._add_watchpoint, self._watchpoint_input]),
                HBox([self._remove_watchpoint, self._watchpoint_dropdown]),
                self._watchpoint_output,
            ]
        )

        self._code_nav_layout = VBox(
            [
                HBox(
                    [
                        *self.get_buttons(),
                        self._autoplay,
                        self._reverse_autoplay,
                        self._speed_slider,
                    ]
                ),
                self._diff_slider,
                self._code_layout,
            ]
        )

        self._main_layout = Tab(
            [
                self._code_nav_layout,
                self._breakpoint_layout,
                self._search_layout,
            ],
            layout=Layout(height="650px"),
        )

        self._main_layout.set_title(0, "Code")
        self._main_layout.set_title(1, "Breakpoints")
        self._main_layout.set_title(2, "Search")

        display(self._main_layout)

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
        if not keys:
            return [
                self._BUTTONS[key]["button"] for key in self._BUTTONS.keys()
            ]
        return [self._BUTTONS[key]["button"] for key in keys]

    def register_button(self, key, **kwargs):
        button = Button(description="", layout=Layout(width="40px"), **kwargs)
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
        self._watchpoint_dropdown.options = [
            b.id for b in self._debugger.watchpoints
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
            if not current_line_breakpoint and not self._autoplay._playing:
                elem.set("class", "currentline")
            elif self._autoplay._playing:
                elem.set("class", "currentline-running")
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
        self._watchpoint_input.value = ""
        self.update()

    def list_watch_command(self):
        header = "| ID | Expression | Value |\n"
        split = "|---|---|---|\n"
        template = "|{}|`{}`|`{!r}`|\n"
        wpstr = header + split

        for wp in self._debugger.watchpoints:
            wpstr += template.format(*wp)

        display(Markdown(wpstr))

    def unwatch_command(self, change):
        """ Remove a watchpoint """
        arg = self._watchpoint_dropdown.value
        if not arg:
            return
        if not self._debugger.remove_watchpoint(int(arg)):
            print(f"Watchpoint with id {arg} does not exist.")
        else:
            print(f"Successfully removed watchpoint {arg}.")
            self.update()

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

    def delete_command(self, change):
        """ Remove the given breakpoint """
        arg = self._breakpoint_dropdown.value
        if not arg:
            return
        self._debugger.remove_breakpoint(int(arg))
        self.update()

    def disable_command(self, arg=""):
        """ Disable the given breakpoint """
        arg = self._breakpoint_dropdown.value
        if not arg:
            return
        self._debugger.disable_breakpoint(int(arg))
        self.update()

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
            if not line.isnumeric() or line is None:
                self._line_input.value = ""
                self._line_input.placeholder = "Please enter a valid number!"
                return

        if type == "Conditional":
            try:
                eval(condition)
            except SyntaxError:
                if self._condition_input.value:
                    self._condition_input.placeholder = "Invalid expression!"
                self._condition_input.value = ""
                return

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
        try:
            input = change["new"]
            event_type, query = input.split(" ", 1)
            events = self._debugger.search(event_type, query)
        except:
            return

        with self._search_results:
            clear_output()
            for event in events:
                goto = Button(
                    icon="angle-right",
                    layout=Layout(width="30px", height="30px"),
                )
                goto.on_click(
                    lambda change: self._debugger.step_to_index(
                        event.exec_point, ignore_breakpoints=True
                    )
                )
                display(HBox([goto, Label(value=str(event))]))
