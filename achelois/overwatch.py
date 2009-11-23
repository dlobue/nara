from settings import get_settings, settings
settings = get_settings()

from urwid.signals import MetaSignals, emit_signal, register_signal, connect_signal, disconnect_signal
#from urwid.util import MetaSignals, Signals

class _eband(object):
    __slots__ = ('__weakref__', '_urwid_signals')
    __metaclass__ = MetaSignals
    signals = ['emergency', 'log', 'frame_connect', 'redisplay']
    pass

eband = _eband()

from offlinemaildir import mail_sources

mail_grab = mail_sources()
