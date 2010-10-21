
from os.path import join, isdir, getmtime
from os import listdir
from datetime import datetime
import logging

from sqlobject import connectionForURI, sqlhub, SQLObjectNotFound
from sqlobject.sresults import SelectResults
from pubsub import pub

from models.fs import Directory, SubDirectory, File
from settings import settingsdir
from overwatch import settings

from tools import null_handler


nh = null_handler()
logger = logging.getLogger("imaplibii.transports")
logger.addHandler(nh)


db_filename = join(settingsdir, 'fs_scan.cache')

conn_str = 'sqlite:%s' % db_filename
conn = connectionForURI(conn_str)
sqlhub.processConnection = conn



def scan_mail():
    Directory.createTable(ifNotExists=True)
    File.createTable(ifNotExists=True)

    root_maildirs = Directory.selectBy(parent_dir=None)
    if not root_maildirs.count():
        _rdir = settings['rdir']
        assert isdir(_rdir)
        _last_modified = getmtime(_rdir)
    
        root_maildirs = Directory(name=_rdir, last_modified=_last_modified-1,
                                   parent_dir=None)
    
    return find_missing_and_new([root_maildirs])


#TODO: only emails are valid "files"
#TODO: don't bother recording 'new', 'cur', or 'tmp' maildir subpaths.
def update_maildir_cache(maildirs, colon=':'):
    """
    Scans maildirs looking for new and removed mail.
    """
    started_at = datetime.now()
    imaildirs = iter(maildirs)
    stash = []
    substash = []

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
            while 1:
                try:
                    item = mdir_contents.next()
                    itemfp = join(mdir.full_path, item)
                except StopIteration:
                    if substash:
                        mdir_contents = substash.pop()
                        continue
                    missing_mail = mdir.files.filter(File.q.last_seen < \
                                                          started_at)
                    for mail in missing_mail:
                        #pub.sendMessage('nara.xindex.delete', docid=mail.uuid)
                        #XXX: use sqlobject's signalling
                        mail.destroySelf()
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
                    item = item.split(colon)[0]
                    try:
                        item = mdir.files.filter(File.q.name == item).getOne()
                        item.update_seen()
                    except SQLObjectNotFound:
                        item = File(name=item, parent_dir=mdir)
                        #print('add to xapian - %r' % item)
                        #add to xapian



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
                        pub.sendMessage('nara.xindex.delete', docid=mail.uuid)
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



if __name__ == '__main__':
    scan_mail()

