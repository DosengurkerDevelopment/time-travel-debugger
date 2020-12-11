import readline
import functools
import sys

from os import environ


class CLICompleter(object):

    def __init__(self, options):
        self._options = options

    def complete(self, text, state):
        if state == 0:
            if not text:
                self._matches = self._options[:]

            else:
                self._matches = [
                    s for s in self._options if s.startswith(text)]
        try:
            return self._matches[state]
        except IndexError:
            return None
