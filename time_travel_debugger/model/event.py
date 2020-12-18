from  enum import Enum 

class EventType(Enum):
    VAR_CHANGE = "var_change"
    FUNC_CALL = "func_call"
    BREAK_HIT = "break_hit"

class Event(object):
    """ class for storing information about events happening during program
    execution """ 

    def __init__(self, type:EventType, id, line, func, file, exec_point):
        self.id = id
        self.type = type
        self.line = line
        self.func = func
        self.file = file
        self.exec_point = exec_point
    
    def __str__(self):
        return f"<type: {self.type}>: id:{self.id}, line:{self.line}, func:{self.func}, file:{self.file}\n"

    __repr__ = __str__
