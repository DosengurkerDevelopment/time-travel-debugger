from typing import List, Dict, Any


class ExecStateDiff(object):

    def __init__(self, frame, prev_vars, new_vars):
        # Hash of the frame this diff belongs to
        self._frame = hash(frame)
        # Line number of the diff
        self._lineno = frame.f_lineno

        # Variables that were added to the state in this step
        self._added_vars = {}
        # Variables that were updated in this step
        self._updated_vars = {}

        for key, value in new_vars.items():
            if key in prev_vars:
                self._updated_vars[key] = value
            else:
                self._added_vars[key] = value

    @property
    def frame(self):
        return self._frame

    @property
    def lineno(self):
        return self._lineno

    @property
    def added(self):
        return self._added_vars

    @property
    def updated(self):
        return self._updated_vars

    @property
    def changed(self):
        return self._added_vars + self._updated_vars
