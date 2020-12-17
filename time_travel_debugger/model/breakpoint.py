import os

from enum import Enum


class BPType(Enum):

    COND = "cond"
    FUNC = "func"
    LINE = "line"


class BaseBreakpoint(object):
    def __init__(self, id, filename, type_):
        self._id = id
        self._filename = filename
        self._active = True
        self._type = type_

    def toggle(self):
        self._active = not self._active

    def enable(self):
        self._active = True

    def disable(self):
        self._active = False

    @property
    def id(self):
        return self._id

    @property
    def filename(self):
        return os.path.basename(self._filename)

    @property
    def abs_filename(self):
        return self._filename

    @property
    def active(self):
        return self._active

    @property
    def status(self):
        return "active" if self._active else "inactive"

    @property
    def breakpoint_type(self):
        return self._type


class Breakpoint(BaseBreakpoint):
    """ Container class that holds one breakpoint and all its properties """

    def __init__(self, id, lineno, filename, condition=""):
        super().__init__(
            id, filename, BPType.COND if condition else BPType.LINE
        )
        self._lineno = lineno
        self._condition = condition

    def __iter__(self):
        return iter(
            (
                str(self.id),
                self.breakpoint_type.value,
                self.abs_location,
                self.status,
                self.condition,
            )
        )

    def eval_condition(self, context):
        """Evaluate the condition given in the constructor in the given
        context.  Always returns True if no condition was given."""
        if self.active:
            if not self.condition:
                # We do not have a condition, so we always break
                return True
            try:
                return eval(self.condition, context)
            except:
                return False

    @property
    def lineno(self):
        return self._lineno

    @property
    def abs_location(self):
        return self.filename + ":" + str(self.lineno)

    @property
    def condition(self):
        return self._condition

    def __repr__(self):
        return f"Breakpoint<id: {self.id}, filename: {self.filename}, \
lineno: {self.lineno} active: {self.active}, \
breakpoint_type: {self.breakpoint_type}, condition: {self.condition}>"

    __str__ = __repr__


class FunctionBreakpoint(BaseBreakpoint):
    def __init__(self, id, funcname, filename, startline, endline):
        super().__init__(id, filename, BPType.FUNC)
        self._funcname = funcname
        self._endline = endline
        self._startline = startline

    def __iter__(self):
        return iter(
            (
                str(self.id),
                self.breakpoint_type.value,
                self.abs_location,
                self.status,
                "",
            )
        )

    @property
    def funcname(self):
        return self._funcname

    @property
    def endline(self):
        return self._endline

    @property
    def startline(self):
        return self._startline

    @property
    def abs_location(self):
        return self.filename + ":" + self.funcname

    def __repr__(self):
        return f"FunctionBreakpoint<id: {self.id}, filename: {self.filename}, \
funcname: {self.funcname}, \
active: {self.active}, breakpoint_type: {self.breakpoint_type}>"

    __str__ = __repr__
