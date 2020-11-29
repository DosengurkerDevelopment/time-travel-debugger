import inspect
import math
import sys

class Tracer(object):
    def __init__(self, file=sys.stdout):
        """Trace a block of code, sending logs to file (default: stdout)"""
        self.original_trace_function = None
        self.file = file
        pass

    def log(self, *objects, sep=' ', end='\n', flush=False):
        """Like print(), but always sending to file given at initialization,
           and always flushing"""
        print(*objects, sep=sep, end=end, file=self.file, flush=True)

    def traceit(self, frame, event, arg):
        """Tracing function. To be overridden in subclasses."""
        self.log(event, frame.f_lineno, frame.f_code.co_name, frame.f_locals)

    def _traceit(self, frame, event, arg):
        """Internal tracing function."""
        if frame.f_code.co_name == '__exit__':
            # Do not trace our own __exit__() method
            pass
        else:
            self.traceit(frame, event, arg)
        return self._traceit

    def __enter__(self):
        """Called at begin of `with` block. Turn tracing on."""
        self.original_trace_function = sys.gettrace()
        sys.settrace(self._traceit)

    def __exit__(self, tp, value, traceback):
        """Called at begin of `with` block. Turn tracing off."""
        sys.settrace(self.original_trace_function)

    def print_debugger_status(self, frame, event, arg):
        changes = self.changed_vars(frame.f_locals)
        changes_s = ", ".join([var + " = " + repr(changes[var])
                               for var in changes])

        if event == 'call':
            self.log("Calling " + frame.f_code.co_name + '(' + changes_s + ')')
        elif changes:
            self.log(' ' * 40, '#', changes_s)

        if event == 'line':
            module = inspect.getmodule(frame.f_code)
            if module is None:
                source = inspect.getsource(frame.f_code)
            else:
                source = inspect.getsource(module)
            current_line = source.split('\n')[frame.f_lineno - 1]
            self.log(repr(frame.f_lineno) + ' ' + current_line)

        if event == 'return':
            self.log(frame.f_code.co_name + '()' + " returns " + repr(arg))
            self.last_vars = {}  # Delete 'last' variables

    def changed_vars(self, new_vars):
        changed = {}
        for var_name in new_vars:
            if (var_name not in self.last_vars or
                    self.last_vars[var_name] != new_vars[var_name]):
                changed[var_name] = new_vars[var_name]
        self.last_vars = new_vars.copy()
        return changed


class Tracer(Tracer):
    def traceit(self, frame, event, arg):
        if event == 'line':
            module = inspect.getmodule(frame.f_code)
            if module is None:
                source = inspect.getsource(frame.f_code)
            else:
                source = inspect.getsource(module)
            current_line = source.split('\n')[frame.f_lineno - 1]
            self.log(frame.f_lineno, current_line)

        return traceit


class Tracer(Tracer):
    def traceit(self, frame, event, arg):
        if event == 'call':
            self.log(f"Calling {frame.f_code.co_name}()")

        if event == 'line':
            module = inspect.getmodule(frame.f_code)
            source = inspect.getsource(module)
            current_line = source.split('\n')[frame.f_lineno - 1]
            self.log(frame.f_lineno, current_line)

        if event == 'return':
            self.log(f"{frame.f_code.co_name}() returns {repr(arg)}")

        return traceit


class Tracer(Tracer):
    def __init__(self, file=sys.stdout):
        self.last_vars = {}
        super().__init__(file=file)



class ConditionalTracer(Tracer):
    def __init__(self, file=sys.stdout, condition=None):
        if condition is None:
            condition = "False"
        self.condition = condition
        self.last_report = None
        super().__init__(file=file)

    def eval_in_context(self, expr, frame):
        frame.f_locals['function'] = frame.f_code.co_name
        frame.f_locals['line'] = frame.f_lineno

        try:
            cond = eval(expr, None, frame.f_locals)
        except NameError:  # (yet) undefined variable
            cond = None
        return cond

    def do_report(self, frame, event, arg):
        return self.eval_in_context(self.condition, frame)

    def traceit(self, frame, event, arg):
        report = self.do_report(frame, event, arg)
        if report != self.last_report:
            if report:
                self.log("...")
            self.last_report = report

        if report:
            self.print_debugger_status(frame, event, arg)
