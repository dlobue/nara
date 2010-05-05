from overwatch import eband, emit_signal

import time

import os.path
import mailbox
from threading import Thread

from settings import get_settings
settings = get_settings()


class mail_sources(list):
    """
    This object is a hacky way to not have to remember the source or path to an email.
    It condenses all maildir sources into one place. Given a a maildir id, it tries every maildir
    it has been told about until it finally finds a source that has an email with the maildir id we're
    asking after, or runs out of sources.

    This will need to be reworked eventually as two emails with the same maildir id will cause the second
    email to never be accessible.
    """
    def __init__(self):
        maildirinc_list = [os.path.join(settings['rdir'], x) for x in settings['maildirinc']]
        maild_list = [mailbox.Maildir(x, factory=mailbox.MaildirMessage, create=False) for x in maildirinc_list]
        self._pthread = Thread

        self.extend(maild_list)
        self.refresh()

    def refresh(self):
        '''
        refresh all sources to look for new emails.
        And do every source in a separate thread so we aren't kept waiting.
        '''
        map(self._thread, self)

    def _thread(self, x, y='_refresh', z=None):
        if z is None: z = ()
        __current = self._pthread(target=getattr(x, y), args=z)
        #__current = self._pthread(target=x._refresh, args=y)
        #__current = self._pthread(target=x._refresh, args=())
        __current.start()

    def get(self, key):
        '''
        try every source until we find one that has the message id we're looking for.
        return the message when found.
        '''
        for source in self:
            try: value = source.get_message(key)
            except: pass
            else:
                if value: return value

    def update(self, muuid, msg):
        '''
        push updated message back to source.
        '''
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
        '''
        search every source until we find a source that has the id we're looking for.
        return the source found
        '''
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
