import sys
from time_travel_debugger_cli import TimeTravelDebugger

def id(a):
    b = 1234
    c = 12
    return a

def call_id(a):
    x = 100
    while a > 5:
        id(a)
        a -= 1
    return

def remove_html_markup(s):
    tag = False
    quote = False
    out = ""

    for c in s:
        if c == '<' and not quote:
            tag = True
        elif c == '>' and not quote:
            tag = False
        elif c == '"' or c == "'" and tag:
            quote = not quote
        elif not tag:
            out = out + c

    return out


if __name__ == '__main__':
    with TimeTravelDebugger():
        call_id(100)
