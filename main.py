import sys
from time_travel_debugger.view.cli import TimeTravelCLI
from test_module import module


class Test:
    def __init__(self, a, b):
        self.x = a + b
        self.y = b - b

def remove_html_markup(s):
    tag = False
    quote = False
    out = ""
    f = module(1,42)
    d = "test"
    test = Test(4,5)
    # Help
    # blub

    for c in s:
        if c == "<" and not quote:
            tag = True
        elif c == ">" and not quote:
            tag = False
        elif c == '"' or c == "'" and tag:
            quote = not quote
        elif not tag:
            out = out + c
    return out

if __name__ == "__main__":
    with TimeTravelCLI():
        remove_html_markup("<tag>hello</tag>")
