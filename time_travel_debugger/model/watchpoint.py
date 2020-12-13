class Watchpoint(object):

    def __init__(self, id, var_name, initial):
        self._id = id
        self._var = var_name
        self._last_value = initial

    def has_changed(self, state):
        if self._var not in state:
            return self._last_value is not None
        return self._last_value != state[self._var]

    @property
    def last_value(self):
        return self._last_value

    @property
    def var_name(self):
        return self._var

    @property
    def id(self):
        return self._id

    def update(self, state):
        lastlast = self._last_value
        if self._var not in state:
            self._last_value = None
        else:
            self._last_value = state[self._var]

        return lastlast, self._last_value
