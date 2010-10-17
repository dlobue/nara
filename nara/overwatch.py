from settings import get_settings, settings, xapidx
settings = get_settings()

from urwid.signals import MetaSignals, emit_signal, register_signal, connect_signal, disconnect_signal

import xappy

#from urwid.util import MetaSignals, Signals

class _eband(object):
    __metaclass__ = MetaSignals
    signals = ['emergency', 'log', 'frame_connect', 'redisplay']
    pass

eband = _eband()

#from offlinemaildir import mail_sources
from offlinemaildir import Maildir

mail_grab = Maildir()
#mail_grab = mail_sources()

if __name__ == '__main__':
    print str(settings)
