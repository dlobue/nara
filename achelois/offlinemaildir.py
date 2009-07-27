import os.path
import mailbox
from threading import Thread

from settings import settings


class mail_sources(list):
    def __init__(self):
        maildirinc_list = [os.path.join(settings['rdir'], x) for x in settings['maildirinc']]
        maild_list = [mailbox.Maildir(x, factory=mailbox.MaildirMessage, create=False) for x in maildirinc_list]
        self._pthread = Thread
        def _thread(x):
            __current = self._pthread(target=x._refresh, args=())
            __current.start()
            #return __current

        [_thread(x) for x in maild_list]
        #__tojoin = [_thread(x) for x in maild_list]
        #[x.join() for x in __tojoin]
        self.extend(maild_list)

    def get(self, key):
        for source in self:
            try: value = source.get_message(key)
            except: pass
            else:
                if value: return value

    def iteritems(self):
        return ((__i, __x.get_message(__i)) for __x in self for __i in __x.iterkeys())
    def itervalues(self):
        return (__x.get_message(__i) for __x in self for __i in __x.iterkeys())
    def iterkeys(self):
        return (__i for __x in self for __i in __x.iterkeys())
