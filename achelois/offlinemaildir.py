from overwatch import eband, emit_signal

import time

import os.path
import mailbox
from threading import Thread

from settings import get_settings
settings = get_settings()


class mail_sources(list):
    def __init__(self):
        maildirinc_list = [os.path.join(settings['rdir'], x) for x in settings['maildirinc']]
        maild_list = [mailbox.Maildir(x, factory=mailbox.MaildirMessage, create=False) for x in maildirinc_list]
        self._pthread = Thread
        #def _thread(x):
            #__current = self._pthread(target=x._refresh, args=())
            #__current.start()
            #return __current

        #[_thread(x) for x in maild_list]
        #__tojoin = [_thread(x) for x in maild_list]
        #[x.join() for x in __tojoin]
        self.extend(maild_list)
        self.refresh()

    def refresh(self):
        map(self._thread, self)

    def _thread(self, x, y='_refresh', z=None):
        if z is None: z = ()
        __current = self._pthread(target=getattr(x, y), args=z)
        #__current = self._pthread(target=x._refresh, args=y)
        #__current = self._pthread(target=x._refresh, args=())
        __current.start()

    def get(self, key):
        for source in self:
            try: value = source.get_message(key)
            except: pass
            else:
                if value: return value

    def update(self, muuid, msg):
        t = time.time()
        source = self.get_folder(muuid)
        t = time.time() - t
        emit_signal(eband, 'log', 'in update, getting source took %s seconds' % t)
        #__current = self._pthread(target=source.update, args=({muuid:msg},))
        #__current.start()
        #self._thread(source, 'update', ([(muuid,msg)]))
        self._thread(source, 'update', ({muuid:msg},))

        #source.update

    def get_folder(self, muuid):
        for source in self:
            if source.has_key(muuid):
                return source

    def iteritems(self):
        return ((__i, __x.get_message(__i)) for __x in self for __i in __x.iterkeys())
    def itervalues(self):
        return (__x.get_message(__i) for __x in self for __i in __x.iterkeys())
    def iterkeys(self):
        return (__i for __x in self for __i in __x.iterkeys())


if __name__ == '__main__':
    m = mail_sources()
    for i in m.iteritems(): print i
