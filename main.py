import sys
from time_travel_debugger.view.cli import TimeTravelCLI


def list_comprehension_test(max):
    a = [x for x in range(1, max)]
    return a


def test1(a):
    x = 100
    while a > 5:
        id(a)
        a -= 1
        x -= 1
    return


def id(a):
    b = 1234
    c = 12


def recursive_test(a):
    b = 111
    if a > 0:
        recursive_test(a - 1)
    else:
        return a


def dict_test(a):
    b = {"test": "test"}
    return


class Test(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b


def class_test(a, b):
    a -= 1
    test = Test(a, b)
    print(a)


def remove_html_markup(s):
    tag = False
    quote = False
    out = ""

    test1(14)

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


def watch_test():
    a = 0
    b = 0
    for i in range(10):
        if i % 2:
            a += 1
        else:
            b += 1
    return a + b


if __name__ == "__main__":
    with TimeTravelCLI():
        watch_test()
        #  id(12)
        # test1(7)
        #  recursive_test(2)
        #  dict_test(123)
        # list_comprehension_test(5) #  not working
        #  class_test(1, 2)  #  not working
        # remove_html_markup("<tag>hello</tag>")
