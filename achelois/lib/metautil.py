from urwid import MetaSuper, MetaSignals, Signals

class Singleton(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance

class BindError(Exception): pass
class NotImplemented(Exception): pass
class MetaSupSig(MetaSuper, MetaSignals): pass

class MetaSuperSignals(object):
    __slots__ = ()
    __metaclass__ = MetaSupSig
    def _connect(self, signal, child, method):
        Signals.connect(child, signal, method)

    def _emit(self, signal, *args, **kwargs):
        Signals.emit(self, signal, *args, **kwargs)

class MetaBind(object):
    __slots__ = ()
    def keypress(self, (maxcol,), key):
        try:
            __method = getattr(self, 'do_%s' % kbm[self.context, key])
            __method((maxcol,),)
        except AttributeError:
            self._keybind_failover((maxcol,), key)

    def _keybind_failover(self, (maxcol,), key):
        raise NotImplemented("Not set by default! Don't forget to set this method!")

    def do_nomap(self, (maxcol,),):
        raise BindError("Omg! What do I do!?")

class MetaMelt(MetaBind, MetaSuperSignals):
    __slots__ = ()
    signals = ['keypress', 'modified']
    def all_connect(self, child):
        def quack_filter(mthd):
            if mthd.startswith('_') and mthd.endswith('connect'):
                return True
            return False
        __cntrs = filter(quack_filter, dir(self))
        [getattr(self, __x)(child) for __x in __cntrs]

    def _kconnect(self, child):
        self._connect('keypress', child, self.keypress)
    def _kemit(self, (maxcol,), key):
        self._emit('keypress', (maxcol,), key)
    def _keybind_failover(self, (maxcol,), key):
        self._kemit((maxcol,), key)

    def _mconnect(self, child):
        self._connect('modified', child, self._modified)
    def _memit(self):
        self._emit('modified')
    def _modified(self):
        self._memit()
