from enum import Enum
import os


class EventType(Enum):
    VAR_CHANGE = "var"
    FUNC_CALL = "call"
    BREAK_HIT = "hit"


class Event(object):
    """class for storing information about events happening during program
    execution"""

    def __init__(self, type: EventType, id, line, func, file, exec_point):
        self.id = id
        self.type = type
        self.line = line
        self.func = func
        self.file = file
        self.exec_point = exec_point

    def __str__(self):
        return f"{os.path.basename(self.file)}:{self.func}:{self.line} -- {self.type}"

    __repr__ = __str__
