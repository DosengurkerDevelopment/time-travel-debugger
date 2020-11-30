import sys
import pdb
from debugger import Debugger


class TimeTravelDebugger(Debugger):

    def __init__(self, file=sys.stdout):
        #  stores the respective line number and variable changes for each exection step
        self.diffs = []
        self.curr_line = None
        self.exec_point = 0
        self.vars = {}
        self.code = None
        self.running = False
        self.at_start = True
        self.at_end = False

        super().__init__(file)

    def _traceit(self, frame, event, arg):
        if self.code is None:
            self.code = frame.f_code
        if frame.f_code.co_name != '__exit__':
            self.traceit(frame, event, arg)
        return self._traceit

    def stop_here(self):
        line = self.curr_line
        #  vars = self.vars
        if(self.stepping or line in self.breakpoints):
            # TODO: check condition of breakpoint
            # after stopping we want to be interactive again
            self.interact = True
            return True
        else:
            return False

    def debugging_loop(self):
        while self.exec_point < len(self.diffs):
            #  the diff of the current execution point
            (line, args) = self.diffs[self.exec_point]
            self.curr_line = line
            #  assemble the vars of the current state of the program
            if self.stop_here():
                #  self.exec_point = self.interaction_loop()
                # get a command
                command = input("(debugger) ")
                self.execute(command)

    def __enter__(self, *args, **kwargs):
        sys.settrace(self._traceit)

    def __exit__(self, *args, **kwargs):
        self.code = None
        sys.settrace(None)
        self.debugging_loop()
        #  for diff in self.diffs:
        #  print(diff)

    def traceit(self, frame, event, arg):
        # store the state of the previous execution point
        prev = self.last_vars.items()
        # compute diff
        diff = self.changed_vars(frame.f_locals)
        # only store previous values, that got changed by the current step
        prev = {x: y for x, y in prev if x in diff}
        self.diffs.append((frame.f_lineno, (prev, diff)))
        return self.traceit

    def print_command(self, arg=""):
        print(f"{self.diffs[self.exec_point]} - {self.exec_point+1}/{len(self.diffs)}")
        """Print an expression. If no expression is given, print all variables"""
        vars = self.vars

        if not arg:
            self.log("\n".join([f"{var} = {repr(vars[var])}" for var in vars]))
        else:
            try:
                self.log(f"{arg} = {repr(eval(arg, globals(), vars))}")
            except Exception as err:
                self.log(f"{err.__class__.__name__}: {err}")

    #  def interaction_loop(self):
        #  """Interact with the user"""
        #  #  self.print_debugger_status(self.frame, self.event, self.arg)

        #  self.interact = True
        #  while self.interact:
            #  command = input("(debugger) ")
            #  self.execute(command)

    def step_forward(self):
        # check wheter we reached the end of the program
        if self.exec_point < len(self.diffs)-1:
            self.exec_point += 1
            (new_line, (var_old,var_diff)) = self.diffs[self.exec_point]
            self.vars.update(var_diff)
            self.curr_line = new_line
            self.at_start = False
            return True
        else:
            self.at_start = False
            self.at_end = True
            return False

    def step_backward(self):
        # check wheter we reached the start of the program
        if self.exec_point > 0:
            (new_line, (var_old,var_diff)) = self.diffs[self.exec_point]
            self.exec_point -= 1
            # filter out variables, that did not exist in the scope from the previous
            # execution point
            #  pdb.set_trace()
            for d in var_diff:
                if d in self.vars and d not in var_old:
                    self.vars.pop(d)
            self.curr_line = new_line
            self.at_end = False
            return True
        else:
            self.at_start = True
            self.at_end = False
            return False

    def step_command(self, arg=""):
        self.step_forward()
        self.stepping = True

    def backstep_command(self, arg=""):
        self.step_backward()
        self.stepping = True

    def next_command(self, arg=""):
        next_line=self.curr_line + 1
        while (self.curr_line != next_line and not self.at_end):
            self.step_forward()
        self.stepping = True

    def previous_command(self, arg=""):
        next_line=self.curr_line - 1
        while (self.curr_line  != next_line and not self.at_start):
            self.step_backward()
        self.stepping = True
