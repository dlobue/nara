import os.path
import mailbox
#import email

from settings import settings


class mail_sources(list):
    def __init__(self):
        maildirinc_list = [os.path.join(settings['rdir'], x) for x in settings['maildirinc']]
        maild_list = [mailbox.Maildir(x, factory=mailbox.MaildirMessage, create=False) for x in maildirinc_list]
        [x._refresh() for x in maild_list]
        self.extend(maild_list)

    def get(self, key):
        for source in self:
            try: value = source.get_message(key)
            except: pass
            else: return value
