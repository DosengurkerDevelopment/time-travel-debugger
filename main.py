import sys
from tracer import Tracer
from debugger import Debugger
from time_travel_debugger import TimeTravelDebugger


def blub():
    a = 5
    b = 6
    c = 1
    while b > 0:
        c *= a
        b -= 1

    print(c)


if __name__ == '__main__':
    with TimeTravelDebugger():
        blub()
