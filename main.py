import sys
from time_travel_debugger.view.cli import TimeTravelCLI

from test_module import module


def list_comprehension_test(max):
    a = [x for x in range(1, max)]
    b = a
    return a


def test1(a):
    x = 100
    while a > 5:
        b = id(a)
        # comment
        a -= 1
        x -= 1
    return


def id(a):
    b = 1234
    c = 12
    return c


def recursive_test(a):
    b = 111
    if a > 0:
        recursive_test(a - 1)
    else:
        return a


def dict_test(a):
    b = {"test": "test"}
    return


class Test:
    def __init__(self, a, b):
        self.x = a + b
        self.y = b - b
        return


class TestTest:
    def __init__(self, a, b):
        self.x = a + b
        self.test = Test(a, b)
        return


def class_test(a, b):
    test = Test(a, b)
    return test


def nested_classes_test(a, b):
    testtest = TestTest(a, b)
    return testtest


def more_calls(a):
    a = id(a) + id(a)


def remove_html_markup(s):
    tag = False
    quote = False
    out = ""

    module(1, 4)

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

    print(out)
    return out


def lambda_test(a):
    square = lambda x: x ** a
    # sub = lambda x: x - a
    b = square(a)
    # b = sub(a) # breaks sourcemap, since lambda functions are always called
    # <lambda> in the source map
    return b


def watch_test():
    a = 0
    b = 0
    for i in range(10):
        if i % 2:
            a += 1
        else:
            b += 1
    d = a + b


def nested_functions_test():
    def f1():
        f2()

    def f2():
        f3()

    def f3():
        f4()

    def f4():
        return

    f1()

def throw_exception_test():
    a=10
    a=10
    a=10
    raise Exception("Uncaught")
    b=10
    return


if __name__ == "__main__":
    with TimeTravelCLI():
        #  watch_test()
        #  id(12) # works
        test1(7)  # works
        #  recursive_test(9) # works
        #  nested_functions_test()
        #  dict_test(123) #  works
        #  list_comprehension_test(5)  #  works
        #  class_test(1, 2)  #  works
        # lambda_test(2)
        #  nested_classes_test(1,2) #  not working yet
        #  more_calls(1) #  works
        #  remove_html_markup("<tag>hello</tag>")
        #  throw_exception_test()
