#from overwatch import eband, emit_signal

import time

import os.path
from os.path import join
import mailbox
from mailbox import Maildir as _Maildir
from mailbox import MaildirMessage
from threading import Thread
from contextlib import closing
from mmap import mmap, ACCESS_READ

from sqlobject import connectionForURI, sqlhub

from models.fs import Directory, File

from lib import threadmap

from settings import get_settings, settingsdir
settings = get_settings()






db_filename = join(settingsdir, 'fs_scan.cache')

conn_str = 'sqlite:%s' % db_filename
conn = connectionForURI(conn_str)
sqlhub.processConnection = conn



class Maildir(_Maildir):
    def __init__(self, MaildirRecords=Directory, MailRecords=File,
                 factory=None):
        self._factory = factory
        self._path = None
        self._maildir_records = MaildirRecords
        self._mail_records = MailRecords
        self._root_records = MaildirRecords.selectBy(parent_dir=None)
        self._toc = {}


    def iteritems(self):
        records = iter(self._mail_records.select())
        while 1:
            try:
                record = records.next()
            except StopIteration:
                break
            yield record.uuid, self._get_message_for_index(
                self.__lookup(record.full_path))

    def iterkeys(self):
        records = iter(self._mail_records.select().lazyColumns())
        while 1:
            try:
                record = records.next()
            except StopIteration:
                break
            yield record.uuid

    def _lookup(self, key):
        if type(key) is int:
            fp = self._mail_records.get(key).full_path
        else:
            fp = self._mail_records.by_uuid(key).full_path
        return self.__lookup(fp)

    def __lookup(self, fp):
        fp = fp.split('/')
        fname = fp.pop()
        subdir = fp.pop()
        self._path = fp = '/'.join(fp)
        subpath = '/'.join([subdir, fname])
        return subpath

    def get_message_for_index(self, key):
        """Return a Message representation or raise a KeyError."""
        subpath = self._lookup(key)
        return self._get_message_for_index(subpath)

    def _get_message_for_index(self, subpath):
        with open(os.path.join(self._path, subpath), 'r') as f:
            with closing(mmap(f.fileno(), 0, access=ACCESS_READ)) as m:
                if self._factory:
                    msg = self._factory(m)
                else:
                    msg = MaildirMessage(m)
        subdir, name = os.path.split(subpath)
        msg.set_subdir(subdir)
        if self.colon in name:
            msg.set_info(name.split(self.colon)[-1])
        msg.set_date(os.path.getmtime(os.path.join(self._path, subpath)))
        return msg






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
        threadmap.map(lambda x: x._refresh(), self)
        #map(self._thread, self)

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
        if no message is found, refresh all sources and try again.
        '''
        try: return self._get(key)
        except KeyError:
            self.refresh()
            return self._get(key)

    def _get(self, key):
        for source in self:
            if key in source._toc:
                return source.get_message(key)

        e = 'No message with key: %s' % key
        raise KeyError(e)

    def update(self, muuid, msg):
        '''
        push updated message back to source.
        '''
        t = time.time()
        source = self.get_folder(muuid)
        t = time.time() - t
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
