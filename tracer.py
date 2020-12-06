import inspect
import sys
import inspect
from exec_state_diff import ExecStateDiff
from copy import deepcopy



class Tracer(object):

    def __init__(self, file=sys.stdout):
        """Trace a block of code, sending logs to file (default: stdout)"""
        self.original_trace_function = None
        self.file = file
        self.last_vars = {}

    def log(self, *objects, sep=' ', end='\n', flush=False):
        """Like print(), but always sending to file given at initialization,
           and always flushing"""
        print(*objects, sep=sep, end=end, file=self.file, flush=True)

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
        """Called at end of `with` block. Turn tracing off."""
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

        return self.traceit


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




class TimeTravelTracer(Tracer):

    def __init__(self):
        self._diffs:List[ExecStateDiff] = []
        self._source_map = {}
        self._last_vars = []
        self._last_frame = None
        self._exec_state_diff = ExecStateDiff()

    def get_trace(self):
        sys.settrace(None)
        return self._diffs, self._source_map

    def set_trace(self):
        sys.settrace(self._traceit)

    def _traceit(self, frame, event, arg):
        ''' Internal tracing method '''
        #  if self.code is None:
            #  self.code = frame.f_code
        # don't trace __exit__ function and get_trace
        if ( frame.f_code.co_name != '__exit__' )and( frame.f_code.co_name != 'get_trace' ):
            self.traceit(frame, event, arg)
        return self._traceit

    def traceit(self, frame, event, arg):
        ''' Record the execution inside the with block.
        We do not store the complete state for each execution point, instead
        we calculate the difference and store a 'diff' which contains the old
        and the new value such that we can easily restore the state without
        having to backtrack to the beginning.
        '''

        # collect the code in a source_map, so we can print it later in the debugger
        if frame.f_code.co_name not in self._source_map:
            self._source_map[frame.f_code.co_name] = inspect.getsourcelines(frame.f_code)
        # TODO: check whether the current executed line contains a return statement and
        # then call self._exec_state_diff.return()
        frame.f_lineno
        # TODO: building exec_state_diff doesnt quite work yet!
        if(frame.f_code.co_name != self._last_frame):
            print(f"call {frame.f_code.co_name}")
            # we called a new function, so setup a new scope of variables
            self._last_vars.append(frame.f_locals)
            self._last_frame = frame.f_code.co_name
            # create new function frame in exec_state_diff
            new_state = self._exec_state_diff.call(frame)
            # store the resulting diff
            self._diffs.append(deepcopy(new_state))
        else:
            # save old scope for the update on _exec_state_diff
            prev_vars = self._last_vars[-1]
            changed = self.changed_vars(frame.f_locals.copy())
            print("update")
            # new function, invoke in exec_state_diff accordingly
            new_state = self._exec_state_diff.update(frame,prev_vars, changed)
            # store the resulting diff
            self._diffs.append(deepcopy(new_state))

        #  print(f"last_vars {self._last_vars[-1]}")
        #  print(f"changed {changed}")
        #  print(f"locals {frame.f_locals}")
        return self._traceit

    def changed_vars(self, locals):
        changed = {}
        for var_name in locals:
            # detect if a variable changed and push it into changed dict
            if (var_name not in self._last_vars[-1] or
                    self._last_vars[-1][var_name] != locals[var_name]):
                changed[var_name] = locals[var_name]
        # the new state in the current frame of tracing becomes the state of _last_vars
        # for the current scope
        self._last_vars[-1] = locals.copy()
        return changed
