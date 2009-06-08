import email
import os
import mailbox
import whoosh.index
from whoosh.fields import ID, TEXT, KEYWORD, STORED
from whoosh.writing import NO_MERGE, OPTIMIZE


rdir = '/tank/projects/emailtest/offlineimap/dlobue'

maildirinc = ['INBOX',
        'INBOX.MIEN',
        'INBOX.Read',
        'INBOX.alertsite',
        'INBOX.atg errors',
        'INBOX.hp sim',
        'INBOX.misc',
        'INBOX.mom',
        'INBOX.monit',
        'INBOX.nagios',
        'INBOX.networkperf',
        'INBOX.receipt',
        'INBOX.save',
        'INBOX.scom',
        'Sent',
        'Sent Items']


ix = whoosh.index.create_in("index_dir",
        subject=TEXT(stored=True),
        recipient=TEXT(stored=True),
        sender=TEXT(stored=True),
        msgid=ID(stored=True, unique=True),
        in_reply_to=KEYWORD(stored=True),
        references=KEYWORD(stored=True),
        date=ID(stored=True),
        labels=KEYWORD(stored=True),
        content=TEXT)

mpath = os.path.join(rdir, maildirinc[1])
maild = mailbox.Maildir(mpath, factory=mailbox.MaildirMessage, create=False)

writer = ix.writer()
c=0
for msgid, msg in maild.iteritems():
    c +=1
    #msg = maild.next()
    #if msg is None: break
    tmp = ' '.join([m.get_payload(decode=True) for m in \
            email.iterators.typed_subpart_iterator(msg)])
    clist = filter(lambda x: x, list(set(msg.get_charsets())))
    ucontent = None
    if clist == []: clist = ['utf-8']
    for citem in clist:
        try:
            ucontent = unicode(tmp, citem)
            break
        except: pass

    if ucontent is None:
        raise TypeError("couldn't encode email body into unicode properly.", clist, msg._headers, tmp, msg.get_charsets())
    # FIXME: add in more robust error checking on unicode conversion.
    # ex- try guessing what the character that's giving us grief is.
    # fail that, just ignore the strangly encoded char

    writer.add_document(subject=u'%s' % msg['Subject'],
                        msgid=unicode(msgid),
                        references=u'%s' % msg['References'],
                        recipient=u'%s' % msg['To'],
                        sender=u'%s' % msg['From'],
                        date=u'%s' % msg._date,
                        labels=u'%s' % msg['Labels'],
                        content=ucontent)
    if c == 50:
        """periodically commit so if we crash (gasp), at least
        we don't have to redo all that damn work we just did.
        in addition, we do _not_ want whoosh to optimize the index
        every time we commit, or we'll be waiting forever"""
        writer.commit(NO_MERGE)
        c=0

writer.commit(OPTIMIZE)
