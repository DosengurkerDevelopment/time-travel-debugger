import sys
from time_travel_debugger_cli import TimeTravelDebugger

def id(a):
    b = 1234
    c = 12
    return a

def call_id(a):
    test = "test"
    while a > 5:
        a -= 1
        test += "t"
    res = id(a)
    print(test)
    return res

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
        #  wo_html = remove_html_markup("<a='insert <name> here'>this is a name holder</a>")
        #  print(wo_html)
        a = call_id(10)
        print(a)
