import email
import os
import mailbox
import whoosh.index
import tools
from whoosh.fields import ID, TEXT, KEYWORD, STORED, Schema
from whoosh.writing import NO_MERGE, OPTIMIZE

from whoosh import store
from whoosh.qparser import QueryParser
from whoosh.searching import Paginator


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

schema = Schema(subject=TEXT(stored=True),
                recipient=TEXT(stored=True),
                sender=TEXT(stored=True),
                muuid=ID(stored=True, unique=True),
                msgid=ID(stored=True),
                in_reply_to=KEYWORD(stored=True),
                references=KEYWORD(stored=True),
                date=ID(stored=True),
                labels=KEYWORD(stored=True),
                content=TEXT)

ixmetadir = "/tank/projects/emailtest/index_dir"
badchars = dict(map(lambda x: (ord(x), None), '><@'))

class indexer(object):

    def __init__(self):
        self.ix = whoosh.index.create_in(ixmetadir, schema=schema)

        self.mpath = os.path.join(rdir, maildirinc[1])
        self.maild = mailbox.Maildir(self.mpath, factory=mailbox.MaildirMessage, create=False)

        self.writer = self.ix.writer()

    def start(self):
        #c=0
        for muuid, msg in self.maild.iteritems():
            #c +=1
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
        
            badchars = dict(map(lambda x: (ord(x), None), '><@'))
            msgid = u'%s' % msg['Message-ID']
            msgid = msgid.translate(badchars)
            self.writer.add_document(subject=u'%s' % msg['Subject'],
                                muuid=unicode(muuid),
                                msgid=msgid,
                                in_reply_to=u'%s' % msg['In-Reply-To'],
                                references=u'%s' % msg['References'],
                                recipient=u'%s' % msg['To'],
                                sender=u'%s' % msg['From'],
                                date=u'%s' % msg._date,
                                labels=u'%s' % msg['Labels'],
                                content=ucontent)
            '''if c == 500:
                """periodically commit so if we crash (gasp), at least
                we don't have to redo all that damn work we just did.
                in addition, we do _not_ want whoosh to optimize the index
                every time we commit, or we'll be waiting forever"""
                print 'periodic save-state'
                writer.commit(NO_MERGE)
                c=0
                '''

        print 'optimizing index'
        self.writer.commit(OPTIMIZE)

class locate(object):
    def __init__(self, pri_field=u"subject"):
        self.storage = store.FileStorage(ixmetadir)
        self.ix = whoosh.index.Index(self.storage)
        self.ix = whoosh.index.open_dir(ixmetadir)
        self.searcher = self.ix.searcher()
        self.parser = QueryParser(pri_field, schema=self.ix.schema)
        self.cache = {'references':[], 'messages': []}

    def start(self, target, sortkey=None):
        if sortkey is not None:
            reverse = True
        else:
            reverse = False
        self.query = self.parser.parse(target)
        self.results = self.searcher.search(self.query, sortedby=sortkey, reverse=reverse)
        return self.results

    def threadpage(self, recquery=u'*', pagenum=1, perpage=20):
        #self.query = self.parser.parse('*')
        #self.results = self.searcher.search(self.query, sortedby='date', reverse=True)
        self.results = start(recquery, sortkey='date')
        if recquery == u'*': self.results = Paginator(self.results, perpage=perpage).page(pagenum)
        [self.cache['messages'].append(i) for i in self.results if i not in self.cache['messages']]
        self.refs = [ [p['in_reply_to'], p['references'].split()] for p in self.results ]
        self.refs = list(set(tools.flatten(self.refs)))

        self.newref = False
        for i in self.refs:
            if i in self.cache['references']: continue
            self.newref = True
            self.cache['references'].append(i)

        if self.newref:
            self.refs = u' OR '.join(self.refs).translate(badchars)
            return threadpage(recquery=self.refs)
        else:
            #return threadMessages(self.cache['messages'])
            return self.cache


if __name__ == '__main__':
    #a = indexer()
    #a.start()
    q = locate('msgid')
    #r = q.start(u'Enterprise Reporting Center Down', sortkey=u'date')
    r = q.threadpage()
    print len(r)
    print r
