from ..model.exec_state_diff import Action
from ..model.event import EventType, Event
from ..domain.debugger import TimeTravelDebugger, StateMachine
from copy import deepcopy
from enum import Enum


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
        
        # remove any string delimiters
        query = query.replace('"','')
        query = query.replace("'",'')

        phrases = query.split('-')
        for phrase in phrases:
            phrase = phrase.strip()
            if phrase.startswith("line"):
                line_no = phrase.split("line")[-1]
                line_nums.append(line_no.strip())
            elif phrase.startswith("func"):
                func_name = phrase.split("func")[-1]
                func_names.append(func_name.strip())
            elif phrase:
                id = phrase
                ids.append(id)

        #  print ( ids, func_names, line_nums )
        return ids, func_names, line_nums

    def search_events(self, event_type:EventType, query):
        """ search for events of a specific type in the programm execution """
        ids, func_names, line_nums = self._parse_search_query(query)
        #  print(ids, func_names, line_nums)
        results = []
        search_list = []
        if event_type == EventType.VAR_CHANGE:
            search_list = self._var_change_events
        elif event_type == EventType.BREAK_HIT:
            search_list = self._break_hit_events
        elif event_type == EventType.FUNC_CALL:
            search_list = self._func_call_events
        for event in search_list:
            id_crit = event.id in ids if ids else True
            line_crit = event.line in line_nums if line_nums else True
            func_crit = event.func in func_names if func_names else True
            if id_crit and line_crit and func_crit:
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
            ids = self._check_breakpoint_hit()
            if ids:
                for id in ids:
                    event = Event(EventType.BREAK_HIT\
                            ,id,str(line),func,file,self._state_machine._exec_point)
                    self._break_hit_events.append(event)
            var_names = self._check_var_changes()
            if var_names :
                for var_name in var_names:
                    event = Event(EventType.VAR_CHANGE\
                            ,var_name,str(line),func,file,self._state_machine._exec_point)
                    self._var_change_events.append(event)
            func_name = self._check_func_call()
            if func_name:
                event = Event(EventType.FUNC_CALL\
                        ,func_name,str(line),func,file,self._state_machine._exec_point)
                self._func_call_events.append(event)


            self._state_machine.forward()
        #  print(f"var_change_events: {self._var_change_events}")
        #  print(f"func_call_events: {self._func_call_events}")
        #  print(f"break_hit_event: {self._break_hit_events}")


    def _check_breakpoint_hit(self):
        """ return breakpoint ids that got hit at the current diff """
        return self.get_ids_of_current_breaks()

    def _check_var_changes(self):
        """ return variables that changed for the current diff """
        return [ str(x) for x in self.next_diff.changed.keys() ]

    def _check_func_call(self):
        """ check if a function got called at the current exec point and return
        the functions name if so """
        if self.curr_diff.action == Action.CALL:
            return self.next_diff.func_name 
        else:
            return None
