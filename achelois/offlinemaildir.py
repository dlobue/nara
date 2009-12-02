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
    '''
    doram = True
    if doram:
        from guppy import hpy
        hp = hpy()
    sample_ids = [
    '1243857186_2.31259.dominiclinux.corp,U=91211,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857379_3.31259.dominiclinux.corp,U=78486,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857662_0.2371.dominiclinux.corp,U=89091,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857615_9.2371.dominiclinux.corp,U=80199,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857184_3.31259.dominiclinux.corp,U=90619,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857582_1.2371.dominiclinux.corp,U=87966,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857317_0.31259.dominiclinux.corp,U=86132,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857660_0.2371.dominiclinux.corp,U=89040,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857351_4.31259.dominiclinux.corp,U=86418,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857256_3.31259.dominiclinux.corp,U=85851,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857208_2.31259.dominiclinux.corp,U=85014,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857627_6.2371.dominiclinux.corp,U=80312,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857289_3.31259.dominiclinux.corp,U=86116,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857579_5.2371.dominiclinux.corp,U=86671,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857591_2.2371.dominiclinux.corp,U=88098,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857566_11.2371.dominiclinux.corp,U=91349,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    '1243857682_5.2371.dominiclinux.corp,U=89592,FMD5=7e33429f656f1e6e9d79b29c3f82c57e',
    ]
    if doram: hp.setrelheap()
    m = mail_sources()
    c = 0
    g = m.iterkeys()
    while c < 500:
        print g.next()
        c+=1
    print len(m)
    del g
    h1 = hp.heap()
    for i in sample_ids: print m.get(i)
    h2 = hp.heap()
    print h1
    print h2
    '''
