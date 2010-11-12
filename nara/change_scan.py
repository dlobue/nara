
from os.path import join, isdir, getmtime
from os import listdir
from datetime import datetime
from functools import partial
import logging

from sqlobject import connectionForURI, sqlhub, SQLObjectNotFound
from sqlobject.sresults import SelectResults

from models.fs import Directory, File
from settings import settingsdir, get_sources
sources = get_sources()

from tools import null_handler
from lib.util import memoize


nh = null_handler()
logger = logging.getLogger("nara.changescan")
logger.addHandler(nh)


db_filename = join(settingsdir, 'fs_scan.cache')

conn_str = 'sqlite:%s' % db_filename
conn = connectionForURI(conn_str)
sqlhub.processConnection = conn
#sqlhub.processConnection = trans = conn.transaction()


class isChildNode(Exception): pass
class logicError(Exception): pass

def _find_mdir_source(mdir, fail=False):
    _end = -1
    while 1:
        try:
            _end = mdir.rindex('/', 0, _end)
        except ValueError:
            break
        _path_part = mdir[:_end]
        if _path_part in sources:
            # not a root maildir
            if fail:
                raise isChildNode
            else:
                return sources[_path_part]

def scan_mail(getmtime=getmtime):
    Directory.createTable(ifNotExists=True)
    Directory.createIndexes(ifNotExists=True)
    File.createTable(ifNotExists=True)
    File.createIndexes(ifNotExists=True)

    root_maildirs = []
    known_root_maildirs = Directory.selectBy(parent_dir=None)

    for mdir in sorted(sources):
        mdir = mdir.rstrip('/')
        mdir_record = known_root_maildirs.filter(Directory.q.name == mdir)
        if mdir_record.count():
            root_maildirs.append(mdir_record.getOne())
            continue
        _last_modified = getmtime(mdir)-1
        if root_maildirs:
            try:
                _find_mdir_source(mdir, fail=True)
            except isChildNode:
                continue

        root_maildirs.append(Directory(name=mdir,
                                       last_modified=_last_modified,
                                       parent_dir=None))
    for mdir in (m for m in known_root_maildirs if m not in root_maildirs):
        mdir.destroySelf()
    
    print('done getting maildirs')
    #trans.commit()
    return root_maildirs


#def update_maildir_cache(maildirs, colon=':', trans=trans):
def update_maildir_cache(maildirs, colon=':'):
    """
    Scans maildirs looking for new and removed mail.
    """
    started_at = datetime.now()
    imaildirs = iter(maildirs)
    stash = []
    substash = []
    mdirmsg_separator = '%s2,' % colon

    while 1:
        try:
            mdir = imaildirs.next()
            if type(mdir) is SelectResults:
                stash.append(imaildirs)
                imaildirs = iter(mdir)
                continue
        except StopIteration:
            try:
                imaildirs = iter(stash.pop())
                continue
            except IndexError:
                break
        if mdir.has_changed:
            mdir_contents = mdir.listdir()
            seen_state = None
            while 1:
                try:
                    item = mdir_contents.next()
                    itemfp = join(mdir.full_path, item)
                except StopIteration:
                    if substash:
                        mdir_contents = substash.pop()
                        continue
                    if seen_state is None:
                        if not mdir.files.count():
                            break
                        missing_mail = mdir.files
                    else:
                        missing_mail = mdir.files.filter(File.q.was_seen == \
                                                         (not seen_state))
                    for mail in missing_mail:
                        mail.destroySelf()
                        #trans.commit()
                    break

                if isdir(itemfp):
                    if substash:
                        # if there's something in substash, that means we're in
                        # a cur or new folder, and there shouldn't be any
                        # folders under them. skip it
                        continue
                    if item in ('cur', 'new'):
                        # these aren't maildirs, so don't store them as Directory
                        # records. they are a component of a maildir though, and
                        # are where the files we want are located.
                        substash.append(mdir_contents)
                        mdir_contents = iter(listdir(itemfp))
                        continue

                    if item == 'tmp':
                        #files in the tmp folder shouldn't be there long
                        #don't bother
                        continue
                    try:
                        #item = Directory.selectBy(name=item,
                        #                          parent_dir=mdir).getOne()
                        item = mdir.directories.filter(Directory.q.name == item).getOne()
                    except SQLObjectNotFound:
                        item = Directory(name=item, parent_dir=mdir,
                                         last_modified=getmtime(itemfp)-1)
                    maildirs.append(item)
                elif substash:
                    if mdirmsg_separator not in item:
                        # not a properly formatted Maildir message filename.
                        # skip it.
                        continue
                    item = item.split(mdirmsg_separator)[0]
                    try:
                        item = mdir.files.filter(File.q.name == item).getOne()
                        seen_state = item.update_seen()
                    except SQLObjectNotFound:
                        if seen_state is None:
                            if mdir.files.count():
                                seen_state = not mdir.files.limit(1).getOne().was_seen
                            else:
                                seen_state = True
                        item = File(name=item, parent_dir=mdir,
                                    was_seen=seen_state)
                        #add to xapian

    #trans.commit(close=True)



def find_missing_and_new(maildirs):
    """
    Scans maildirs looking for new and removed mail.
    """
    started_at = datetime.now()
    imaildirs = iter(maildirs)
    stash = []

    while 1:
        try:
            mdir = imaildirs.next()
            if type(mdir) is SelectResults:
                stash.append(imaildirs)
                #maildirs.insert(0, imaildirs)
                imaildirs = iter(mdir)
                continue
        except StopIteration:
            try:
                imaildirs = iter(stash.pop())
                continue
            except IndexError:
                break
        if mdir.has_changed:
            mdir_contents = mdir.listdir()
            while 1:
                try:
                    item = mdir_contents.next()
                    itemfp = join(mdir.full_path, item)
                except StopIteration:
                    missing_mail = mdir.files.filter(File.q.last_seen < \
                                                          started_at)
                    for mail in missing_mail:
                        #pub.sendMessage('nara.xindex.delete', docid=mail.uuid)
                        mail.destroySelf()
                    break

                if isdir(itemfp):
                    try:
                        #item = Directory.selectBy(name=item,
                        #                          parent_dir=mdir).getOne()
                        item = mdir.directories.filter(Directory.q.name == item).getOne()
                    except SQLObjectNotFound:
                        item = Directory(name=item, parent_dir=mdir,
                                         last_modified=getmtime(itemfp)-1)
                    maildirs.append(item)
                else:
                    try:
                        item = mdir.files.filter(File.q.name == item).getOne()
                        item.update_seen()
                    except SQLObjectNotFound:
                        item = File(name=item, parent_dir=mdir)
                        #print('add to xapian - %r' % item)
                        #add to xapian
                    yield item


from pprint import pprint

@memoize
def _find_default_labels(mdir_path):
    s = sources.get(mdir_path, None)
    if s is None:
        s = _find_mdir_source(mdir_path)

    lbls = []
    if s['labels']:
        lbls.extend(s['labels'])
    if not s['archived']:
        lbls.append('index')
    return lbls

class indexer_listener(object):
    def __init__(self, que):
        self.queue = que

    def queue_msg(self, msginst):
        labels = _find_default_labels(msginst.parent_dir.full_path)
        self.queue.put(('index', msginst.id, labels))

    def created_listener(self, kwargs, post_funcs):
        print('new msg found. kwargs: %r' % kwargs)
        post_funcs.append(self.queue_msg)

def queue_msg(msginst, msg_indexer_queue):
    labels = _find_default_labels(msginst)
    msg_indexer_queue.put(('index', msginst.id, labels))


def _created_listener(kwargs, post_funcs, msg_indexer_queue):
    post_funcs.append(partial(queue_msg, msg_indexer_queue=msg_indexer_queue))

def created_listener(kwargs, post_funcs, msg_indexer_queue):
    post_funcs.append(partial(queue_msg, msg_indexer_queue=msg_indexer_queue))

def destroy_listener(inst, post_funcs):
    print('destroy_listener run')
    pprint(inst)
    print('')

if __name__ == '__main__':
    #from sqlobject.events import listen, RowDestroySignal, RowCreatedSignal
    #listen(created_listener, File, RowCreatedSignal)
    #listen(destroy_listener, File, RowDestroySignal)
    from time import time
    t = time()
    update_maildir_cache(scan_mail())
    t = time() - t
    print('took %r seconds' % t)

