#!/usr/bin/python -u

import time
def godouble(count=100):
    a = 1
    c = 0
    while 1:
        a *= 2
        c += 1
        print a
        time.sleep(1)
        if c > count: break

if __name__ == '__main__':
    print 'line!'
    print 'another line!'
    print 'omfg ANOTHER line!'

    godouble()
