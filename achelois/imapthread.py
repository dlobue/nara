#!/usr/bin/python
import subprocess
from threading import Thread


def _subthread(parentmethod):
    subpipe = subprocess.Popen('python -u /usr/bin/offlineimap -u Noninteractive.Basic', shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while 1:
        if subpipe.poll() is not None: break
        line = subpipe.stdout.readline()
        if not line: continue
        parentmethod(line.rstrip())

'''
def _thread_init(parentmethod):
        __current = threading.Thread(target=_subthread, args=(parentmethod,))
        __current.start()
        return __current
'''

def _restarter(initfunc, *args, **kwargs):
        while 1:
                __current = Thread(target=initfunc, args=(*args, **kwargs))
                __current.start()
                __current.join()
        
def thread_restarter(initfunc, *args, **kwargs):
        __current = Thread(target=_restarter, args=(initfunc, *args, **kwargs))
        __current.start()
        return __current
