class Watchpoint(object):

    def __init__(self, id, var_name, initial):
        self._id = id
        self._var = var_name
        self._last_value = initial
        self._current_value = initial

    def update(self, value):
        self._last_value = self._current_value
        self._current_value = value

    def has_changed(self):
        return self._current_value != self._last_value

    @property
    def id(self):
        return self._id

    @property
    def last_value(self):
        return self._last_value

    @property
    def current_value(self):
        return self._current_value

    @property
    def var_name(self):
        return self._var

    def __repr__(self):
        return f"Watchpoint<_id: {self.id}, _last_value: {self.last_value}, _current_value: {self.current_value}, _var: {self.var_name}>"

    def __str__(self):
        return f"Changed {self.var_name}: {self.last_value} -> {self.current_value}"

    def __iter__(self):
        return iter((self.id, self.var_name))


