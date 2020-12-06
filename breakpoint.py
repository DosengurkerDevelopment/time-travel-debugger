import sys


class Breakpoint(object):

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

    def __str__(self):
        return f"{self._id}\
\t{self._bp_type}\
\t{self._filename}:{self._location}\
\t{'active' if self._active else 'not active'} \
\t({self._condition})"

    def __repr__(self):
        return f"Breakpoint<_id: {self._id}, _filename: {self._filename}, \
_location: {self._location}, _condition: ({self._condition}), \
_active: {self._active}, _bp_type: {self._bp_type}>"
