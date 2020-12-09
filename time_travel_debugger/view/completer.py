import readline
import functools
import sys

from os import environ


class CLICompleter(object):

    def __init__(self, options):
        self._options = options

    def levenshtein(self, seq1, seq2):
        size_x = len(seq1) + 1
        size_y = len(seq2) + 1
        matrix = [[0 for y in range(size_y)] for x in range(size_x)]
        for x in range(size_x):
            matrix[x][0] = x
        for y in range(size_y):
            matrix[0][y] = y

        for x in range(1, size_x):
            for y in range(1, size_y):
                if seq1[x-1] == seq2[y-1]:
                    matrix[x][y] = min(
                        matrix[x-1][y] + 1,
                        matrix[x-1][y-1],
                        matrix[x][y-1] + 1
                    )
                else:
                    matrix[x][y] = min(
                        matrix[x-1][y] + 1,
                        matrix[x-1][y-1] + 1,
                        matrix[x][y-1] + 1
                    )
        return (matrix[size_x - 1][size_y - 1])

    def complete(self, text, state):
        if state == 0:
            if not text:
                self._matches = self._options[:]

            else:
                self._matches = [
                    s for s in self._options if s and s.startswith(text)]

        try:
            return self._matches[state]
        except IndexError:
            return None

        # self._options.sort(key=functools.partial(self.levenshtein, instr))
        # return self._options[0]
