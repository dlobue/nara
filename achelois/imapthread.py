#import urwid
import subprocess
import threading


def _subthread(parentmethod):
    #subpipe = subprocess.Popen('offlineimap -u Noninteractive.Basic', shell=True,
    subpipe = subprocess.Popen('/root/projects/achelois/achelois/doubler.py', shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while 1:
            if subpipe.poll() is not None: break
            line = subpipe.stdout.next()
            if not line: continue
            parentmethod(line.rstrip())

def _thread_init(parentmethod):
        __current = threading.Thread(target=_subthread, args=(parentmethod,))
        #self._threadlist.append(__current)
        __current.start()
        return __current
