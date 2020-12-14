import traitlets
from ipywidgets import DOMWidget, register

from ..domain.debugger import TimeTravelDebugger
from ..domain.tracer import TimeTravelTracer


@register
class GUI(DOMWidget):
    # Widget specific
    _view_name = traitlets.Unicode("TimeTravelDebugger").tag(sync=True)
    _view_module = traitlets.Unicode("time_travel_debugger").tag(sync=True)
    _view_module_version = traitlets.Unicode("0.1.0").tag(sync=True)

    def __init__(self):
        # Stores the respective line number and variable changes for each
        # exection step
        self._tracer = TimeTravelTracer()
        self._current_state = None
        self._debugger = None

    def __enter__(self, *args, **kwargs):
        self._tracer.set_trace()

    def __exit__(self, *args, **kwargs):
        diffs, source_map = self._tracer.get_trace()
        self._debugger = TimeTravelDebugger(diffs, source_map)
        self._debugger.start_debugger(self.execute, self.update)

    def execute(self):
        pass

    def update(self, state, draw_update):
        pass
