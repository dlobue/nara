
"""
threadmap -- Threaded map(), uses all processors by default.

Connelly Barnes 2008, public domain.
"""

import os
import ctypes, ctypes.util
import time, thread, traceback, Queue

builtin_map = map

def nprocessors():
  try:
    try:
      try:
        # Mac OS
        libc=ctypes.cdll.LoadLibrary(ctypes.util.find_library('libc'))
        v=ctypes.c_int(0)
        size=ctypes.c_size_t(ctypes.sizeof(v))
        libc.sysctlbyname('hw.ncpu', ctypes.c_voidp(ctypes.addressof(v)), ctypes.addressof(size), None, 0)
        return v.value
      except:
        # Cygwin (Windows) and Linuxes
        # Could try sysconf(_SC_NPROCESSORS_ONLN) (LSB) next.  Instead, count processors in cpuinfo.
        s = open('/proc/cpuinfo', 'r').read()
        return s.replace(' ', '').replace('\t', '').count('processor:')
    except:
      # Native (Windows)
      return int(os.environ.get('NUMBER_OF_PROCESSORS'))
  except:
    return 1

nproc = nprocessors()

def map(f, *a, **kw):
  """
  threadmap.map(..., n=nprocessors), same as map(...).

  n must be a keyword arg; default n is number of physical processors.
  """
  n = kw.get('n', nproc)
  if n == 1:
    return builtin_map(f, *a)

  if len(a) == 1:
    L = a[0]
  else:
    L = zip(*a)
  try:
    len(L)
  except TypeError:
    L = list(L)
  n = min(n, len(L))

  ans = [None] * len(L)
  q = Queue.Queue()
  def handle(start, end):
    try:
      if len(a) == 1:
        ans[start:end] = builtin_map(f, L[start:end])
      else:
        ans[start:end] = [f(*x) for x in L[start:end]]
    except Exception, e:
      q.put(e)
    else:
      q.put(None)

  [thread.start_new_thread(handle, (i*len(L)//n, (i+1)*len(L)//n)) for i in range(n)]
  for i in range(n):
    x = q.get()
    if x is not None:
      raise x
  return ans

def bench():
  print 'Benchmark:\n'
  def timefunc(F):
    start = time.time()
    F()
    return time.time() - start
  def f1():
    return builtin_map(lambda x: pow(x,10**1000,10**9), range(10**3))
  def g1():
    return map(lambda x: pow(x,10**1000,10**9), range(10**3))
  def f2():
    return builtin_map(lambda x: os.system(syscall), range(10**2))
  def g2():
    return map(lambda x: os.system(syscall), range(10**2))
  import timeit
  print 'Python operation, 10**3 items:'
  print 'map           (1 processor): ', timefunc(f1), 's'
  print 'threadmap.map (%d processors):' % nproc, timefunc(g1), 's'
  print
  print 'Syscall, 10**2 items:'
  syscall = 'ls > /dev/null'
  for i in range(10):
    if os.system(syscall) != 0:
      syscall = 'dir > NUL:'
      os.system(syscall)
  print 'map           (1 processor): ', timefunc(f2), 's'
  print 'threadmap.map (%d processors):' % nproc, timefunc(g2), 's'

def test():
  print 'Testing:'
  assert [x**2 for x in range(10**4)] == map(lambda x: x**2, range(10**4))
  assert [x**2 for x in range(10**4)] == map(lambda x: x**2, range(10**4), n=10)
  assert [x**2 for x in range(10**4)] == map(lambda x: x**2, range(10**4), n=1)
  assert [(x**2,) for x in range(10**3,10**4)] == map(lambda x: (x**2,), range(10**3,10**4))
  assert [(x**2,) for x in range(10**3,10**4)] == map(lambda x: (x**2,), range(10**3,10**4), n=10)
  assert [(x**2,) for x in range(10**3,10**4)] == map(lambda x: (x**2,), range(10**3,10**4), n=1)
  assert builtin_map(lambda x,y:x+2*y, range(100),range(0,200,2)) == map(lambda x,y:x+2*y, range(100),range(0,200,2))
  assert builtin_map(lambda x,y:x+2*y, range(100),range(0,200,2)) == map(lambda x,y:x+2*y, range(100),range(0,200,2), n=10)
  assert builtin_map(lambda x,y:x+2*y, range(100),range(0,200,2)) == map(lambda x,y:x+2*y, range(100),range(0,200,2), n=2)
  # Some Windows (Cygwin) boxes can't fork more than about 15 times, so only test to n=15
  for n in range(1, 15):
    assert [x**3 for x in range(200)] == map(lambda x: x**3, range(200), n=n)
  def f(n):
    if n == 1:
      raise KeyError
  def check_raises(func, exc):
    e = None
    try:
      func()
    except Exception, e:
      pass
    if not isinstance(e, exc):
      raise ValueError('function did not raise specified error')

  check_raises(lambda: map(f, [1, 0], n=2), KeyError)
  check_raises(lambda: map(f, [0, 1], n=2), KeyError)
  check_raises(lambda: map(f, [1, 0, 0], n=3), KeyError)
  check_raises(lambda: map(f, [0, 1, 0], n=3), KeyError)
  check_raises(lambda: map(f, [0, 0, 1], n=3), KeyError)
  print 'threadmap.map: OK'

if __name__ == '__main__':
  test()
  bench()
