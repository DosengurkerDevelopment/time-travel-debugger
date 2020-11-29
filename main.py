import TimeTravelDebugger

if __name__ == '__main__':
    with TimeTravelDebugger():
        a = 1
        b = 2
        print(a+b)
