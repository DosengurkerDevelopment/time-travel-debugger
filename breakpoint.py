class Breakpoint(object):

    LINE = 'line'
    FUNC = 'func'
    COND = 'cond'

    def __init__(self, id, location, filename, bp_type, condition=""):
        # TODO: Do we need the id here ?
        self._id = id
        self._filename = filename
        self._location = location
        self._condition = condition
        self._active = True
        self._bp_type = bp_type

    def eval_condition(self, context):
        if self._active:
            return eval(self._condition, context)

    def get_location(self):
        pass

    def toggle(self):
        self._active = not self._active

    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False

    @property
    def id(self):
        return self._id

    @property
    def status(self):
        return "active" if self._active else "not active"

    @property
    def complete_location(self):
        return self._filename + ":" + self._location

    @property
    def breakpoint_type(self):
        return self._bp_type

    @property
    def condition(self):
        return self._condition

    def __str__(self):
        s = f"{self._id}\
 {self._bp_type}\
 {self._filename}:{self._location}"

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
