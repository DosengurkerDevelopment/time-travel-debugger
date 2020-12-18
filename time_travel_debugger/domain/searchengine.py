from ..model.exec_state_diff import Action
from ..domain.debugger import TimeTravelDebugger, StateMachine
from copy import deepcopy
from enum import Enum


class EventType(Enum):
    VAR_CHANGE = "var_change"
    FUNC_CALL = "func_call"
    BREAK_HIT = "break_hit"

class Event(object):
    """ class for storing information about events happening during program
    execution """ 

    def __init__(self, type:EventType, id, line, func, file):
        self.id = id
        self.type = type
        self.line = line
        self.func = func
        self.file = file
    
    def __str__(self):
        return f"<type: {self.type}, id:{self.id}, line:{self.line}, func:{self.func}, file:{self.file}\n"

    __repr__ = __str__

class SearchEngine(TimeTravelDebugger):
    """ Search Enginge for events happening during debugging """

    def __init__(self):

        # lists of events
        self._var_change_events: List[Event]= []
        self._func_call_events:  List[Event]= []
        self._break_hit_events:  List[Event]= []

        # Dictionary that contains source code objects for each frame
        self._call_stack_depth = 0
        # que of lines in callstack, after moving down the callstack
        self._call_stack_return_lines = []

        # update shouldnt do anything
        self._update = lambda : None


    def _parse_search_query(self, query):
        """ parses the search criteria for a query """
        ids = []
        func_names = []
        line_nums = []
        
        query = query.replace('"','')
        query = query.replace("'",'')
        phrases = query.split(',')
        for phrase in phrases:
            if phrase.startswith('#'):
                id = phrase.replace('#','')
                ids.append(id)
            elif phrase.startswith("line "):
                line_nums.append(phrase.replace("line ",''))
            else:
                func_names.append(phrase)
        print ( ids, func_names, line_nums )
        return ids, func_names, line_nums

    def search_events(self, event_type:EventType, query):
        """ search for events of a specific type in the programm execution """
        ids, func_names, line_nums = self._parse_search_query(query)
        results = []
        if event_type == EventType.VAR_CHANGE:
            search_list = self._var_change_events
        elif event_type == EventType.BREAK_HIT:
            search_list = self._break_hit_events
        elif event_type == EventType.FUNC_CALL:
            search_list = self._func_call_events
        for event in search_list:
            if event.id in ids:
                results.append(event)
            if event.line in line_nums:
                results.append(event)
            if event.func in func_names:
                results.append(event)
            #  not supported yet
            #  if event.file in ids:
                #  results.append(event)
        #  print(f"results:{results}")
        return results


    def init(self, diffs, breakpoints, watchpoints):
        """ reset the state of the program, run it once and record all events """
        # initialize an own state machine
        self._state_machine = StateMachine(diffs)
        self._breakpoints = deepcopy(breakpoints)
        self._watchpoints = deepcopy(watchpoints)

        while not self.at_end:
            line = self.curr_line
            file = self.curr_diff.file_name
            func = self.curr_diff.func_name
            if ids := self._check_breakpoint_hit() :
                for id in ids:
                    event = Event(EventType.BREAK_HIT,id,line,func,file)
                    self._break_hit_events.append(event)
            if var_names := self._check_var_changes():
                for var_name in var_names:
                    event = Event(EventType.VAR_CHANGE,var_name,line,func,file)
                    self._var_change_events.append(event)
            if func_name := self._check_func_call():
                event = Event(EventType.FUNC_CALL,func_name,line,func,file)
                self._func_call_events.append(event)


            self._state_machine.forward()
        #  print(f"var_change_events: {self._var_change_events}")
        #  print(f"func_call_events: {self._func_call_events}")
        print(f"break_hit_event: {self._break_hit_events}")


    def _check_breakpoint_hit(self):
        """ check if breakpoint got hit and if return its id """
        return self.get_ids_of_current_breaks()

    def _check_var_changes(self):
        """ check if a variable changed """
        return self.curr_diff.changed.keys()

    def _check_func_call(self):
        """ check if a function got called """
        if self.curr_diff.action == Action.CALL:
            return self.curr_diff.func_name 
        else:
            return None
