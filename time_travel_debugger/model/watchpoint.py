class Watchpoint(object):
    def __init__(self, id, expression, initial=None):
        self._id = id
        self._last_value = initial
        self._current_value = initial
        self._expression = expression

    def init(self, state):
        self._current_value = self._last_value = self._eval(state)

    def _eval(self, state):
        try:
            return eval(self._expression, state)
        except:
            return None

    def update(self, state):
        value = self._eval(state)
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
    def expression(self):
        return self._expression

    def __iter__(self):
        return iter(
            (str(self._id), self._expression, repr(self._current_value))
        )

    def __str__(self):
        return f"{repr(self.expression)}: {repr(self._last_value)} -> {repr(self._current_value)}"
