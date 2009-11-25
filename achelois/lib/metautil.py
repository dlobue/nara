from overwatch import eband, emit_signal
from urwid import MetaSuper, MetaSignals, connect_signal

from achelois.keymap import kbm
#kbm = key_bind_manager

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
    __slots__ = ('_urwid_signals')
    __metaclass__ = MetaSupSig
    def _connect(self, signal, child, method):
        connect_signal(child, signal, method)
        #Signals.connect(child, signal, method)

    def _emit(self, signal, *args, **kwargs):
        emit_signal(self, signal, *args, **kwargs)

class MetaBind(object):
    __slots__ = ()
    def keypress(self, (maxcol,), key):
        emit_signal(eband, 'log', 'in keypress trying key %s from class %s' % (key, self.__class__.__name__))
        try:
            __method = getattr(self, 'do_%s' % kbm[self.context, key])
            emit_signal(eband, 'log', 'was directed to method %s' % __method)
            return __method((maxcol,), key)
        except AttributeError:
            emit_signal(eband, 'log', 'got attrerror')
            return self._keybind_failover((maxcol,), key)

    def _keybind_failover(self, (maxcol,), key):
        raise NotImplemented("Not set by default! Don't forget to set this method!")

    def do_global(self, (maxcol,), key):
        emit_signal(eband, 'log', 'in global trying key %s from class %s' % (key, self.__class__.__name__))
        try:
            __method = getattr(self, 'do_%s' % kbm['global', key])
            emit_signal(eband, 'log', 'was directed to method %s' % __method)
            return __method((maxcol,), key)
        except AttributeError:
            emit_signal(eband, 'log', 'got attrerror')
            return self._keybind_failover((maxcol,), key)

    def do_nomap(self, (maxcol,), key):
        raise BindError("Omg! What do I do!?")

#class MetaMelt(MetaBind, MetaSuperSignals):

class ScrollMixin(object):
    def do_cursor_up(self, (maxcol,), key):
        return 'up'
    def do_cursor_down(self, (maxcol,), key):
        return 'down'
    def do_cursor_page_up(self, (maxcol,), key):
        return 'page up'
    def do_cursor_page_down(self, (maxcol,), key):
        return 'page down'

class MetaMixin(MetaBind):
    __slots__ = ()
    signals = ['keypress', 'modified']
    def _connect(self, signal, child, method):
        connect_signal(child, signal, method)
        #Signals.connect(child, signal, method)

    def _emit(self, signal, *args, **kwargs):
        emit_signal(self, signal, *args, **kwargs)

    def all_connect(self, child):
        def do_connect(x):
            try: getattr(self, x)(child)
            except: pass
        def quack_filter(mthd):
            if mthd.startswith('_') and mthd.endswith('connect') and len(mthd) > 8:
                return True
            return False
        __cntrs = filter(quack_filter, dir(self))
        map(do_connect, __cntrs)
        #[getattr(self, __x)(child) for __x in __cntrs]

    def _kconnect(self, child):
        self._connect('keypress', child, self.keypress)
    def _kemit(self, (maxcol,), key):
        self._emit('keypress', (maxcol,), key)
    def _keybind_failover(self, (maxcol,), key):
        emit_signal(eband, 'log', 'in keybind failover trying key %s from class %s' % (key, self.__class__.__name__))
        self._kemit((maxcol,), key)
        return key

    def _mconnect(self, child):
        self._connect('modified', child, self._modified)
    def _memit(self):
        self._emit('modified')
    def _modified(self):
        try: self._invalidate()
        except: pass
        self._memit()
