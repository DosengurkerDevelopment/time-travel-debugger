class Breakpoint(object):
    ''' Container class that holds one breakpoint and all its properties '''

    LINE = 'line'
    FUNC = 'func'
    COND = 'cond'

    def __init__(self, id, location, filename, bp_type, condition=""):
        ''' Init method for the breakpoint class.  
            Args:
                - id: id of the breakpoint
                - location: location of the breapoint, either a line number or
                      function name
                - filename: name of the source file the line or function is
                      located in
                - bp_type: type of the breakpoint, one of LINE, FUNC, COND

            Keyword Args:
                - condition: a python expression passed as a string that is
                    evaluated whenever we pass this breakpoint
        '''

        self._id = id
        self._filename = filename
        self._location = location
        self._condition = condition
        self._active = True
        self._bp_type = bp_type

    def __iter__(self):
        return iter((self.id, self.breakpoint_type, self.abs_location,
                     self.status, self.condition))

    def eval_condition(self, context):
        ''' Evaluate the condition given in the constructor in the given
        context.  Always returns True if no condition was given.  '''
        if self._active:
            if not self._condition:
                # We do not have a condition, so we always break
                return True
            return eval(self._condition, context)

    def toggle(self):
        self._active = not self._active

    def enable(self):
        self._active = True

    def disable(self):
        self._active = False

    @property
    def is_active(self):
        return self._active

    @property
    def id(self):
        return self._id

    @property
    def status(self):
        return "active" if self.is_active else "not active"

    @property
    def location(self):
        return self._location

    @property
    def abs_location(self):
        return self._filename + ":" + str(self._location)

    @property
    def breakpoint_type(self):
        return self._bp_type

    @property
    def condition(self):
        return self._condition

    def __str__(self):
        s = f"{self._id}\
 {self._bp_type}\
 {self._filename}:{str(self._location)}"

        if self._active:
            s += " active"
        else:
            s += " not active"

        if self._condition:
            s += f" ({self._condition})"

        return s

    def __repr__(self):
        return f"Breakpoint<_id: {self._id}, _filename: {self._filename}, \
_location: {self._location}, _condition: ({self._condition}), \
_active: {self._active}, _bp_type: {self._bp_type}>"
