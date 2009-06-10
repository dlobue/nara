import email
import os
import mailbox
import tools
import threadMessages
from datetime import datetime

import whoosh.index
from whoosh.fields import ID, TEXT, KEYWORD, STORED, Schema
from whoosh.writing import NO_MERGE, OPTIMIZE

from whoosh import store
from whoosh.qparser import QueryParser
from whoosh.searching import Paginator

import simplejson

global settings
f = open('settings.json', 'r')
settings = simplejson.loads(f.read())
f.close()

#rdir = '/tank/projects/emailtest/offlineimap/dlobue'
#ixmetadir = "/tank/projects/emailtest/index_dir"
global badchars
badchars = dict(map(lambda x: (ord(x), None), '><@'))
dispHeight = 30

inuse_message_cache = None



'''maildirinc = ['INBOX',
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
        '''

schema = Schema(subject=TEXT(stored=True),
                recipient=TEXT(stored=True),
                sender=TEXT(stored=True),
                muuid=ID(stored=True, unique=True),
                msgid=ID(stored=True),
                in_reply_to=KEYWORD(stored=True),
                references=KEYWORD(stored=True),
                date=ID(stored=True),
                mtime=ID(stored=True),
                labels=KEYWORD(stored=True),
                content=TEXT(stored=True))

class indexer(object):

    def __init__(self):
        self.ix = whoosh.index.create_in(settings['ixmetadir'], schema=schema)

        self.mpath = os.path.join(settings['rdir'], settings['maildirinc'][1])
        self.maild = mailbox.Maildir(self.mpath, factory=mailbox.MaildirMessage, create=False)

        self.writer = self.ix.writer()
        self.mtime = u'%s' % datetime.now().isoformat()

    def test(self):
        msg = self.maild.next()
        return msg

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
        
            #badchars = dict(map(lambda x: (ord(x), None), '><@'))
            msgid = u'%s' % msg['Message-ID']
            #indexable_msgid = msgid.translate(badchars)
            self.writer.add_document(subject=u'%s' % msg['Subject'] or u'None',
                                muuid=unicode(muuid),
                                msgid=msgid.translate(badchars),
                                _stored_msgid=msgid,
                                in_reply_to=u'%s' % msg['In-Reply-To'],
                                references=u'%s' % msg['References'],
                                recipient=u'%s' % msg['To'],
                                sender=u'%s' % msg['From'],
                                date=u'%s' % datetime.fromtimestamp(msg._date).isoformat(),
                                mtime=self.mtime,
                                labels=u'%s' % msg['Labels'],
                                content=ucontent,
                                _stored_content=ucontent[:80])
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
        self.storage = store.FileStorage(settings['ixmetadir'])
        self.ix = whoosh.index.Index(self.storage)
        self.ix = whoosh.index.open_dir(settings['ixmetadir'])
        self.searcher = self.ix.searcher()
        self.parser = QueryParser(pri_field, schema=self.ix.schema)
        self.cache = {'references':[], 'messages': [], 'page': 1}

    def start(self, target, sortkey=None):
        if sortkey is None:
            reverse = True
        else:
            reverse = False
        self.query = self.parser.parse(target)
        self.results = self.searcher.search(self.query, sortedby=sortkey, reverse=reverse)
        return self.results

    def cacheadder(self, field, entity):
        self.newref = True
        self.cache[field].append(entity)

    def threadpage(self, recquery=u'subject:*', pagenum=1, perpage=40, dispHeight=30, external_cache=None):
        if external_cache is not None: self.cache = external_cache

        self.results = self.start(recquery, sortkey='date')
        if recquery == u'subject:*': self.results = Paginator(self.results, perpage=perpage).page(pagenum)

        self.newref = False
        [self.cache['messages'].append(i) for i in self.results if i not in self.cache['messages']]
        self.refs = [ [p['in_reply_to'], p['references'].split()] for p in self.results ]
        self.refs = list(set(tools.flatten(self.refs)))

        [self.cacheadder('references', i) for i in self.refs if i not in self.cache['references']]
        '''for i in self.refs:
            if i in self.cache['references']: continue
            self.newref = True
            self.cache['references'].append(i)
            '''

        if self.newref:
            # Last batch of messages found reference new messages.
            # keep going.
            self.refs = u' OR '.join(self.refs).translate(badchars)
            return self.threadpage(recquery=self.refs)
        else:
            # no new references found in last batch of messages.
            # lets save the current cache and thread!
            #return threadMessages.jwzThread(self.cache['messages'])
            thread = threadMessages.jwzThread(self.cache['messages'])
            if len(thread) < dispHeight:
                # Didn't get enough root messages to fill the screen.
                # grab the next page and run through the gauntlet again.
                self.cache['page'] += 1
                return self.threadpage(pagenum=self.cache['page'])

            global inuse_message_cache
            inuse_message_cache = self.cache
            return thread


def printRecurse(node,depth=0):
    for message in node.messages:
        print "  "*depth+message.get("date")
    for child in node.children:
        printRecurse(child,depth+1)
    return None

def printSubjects(listOfTrees):
    for tree in listOfTrees:
        printRecurse(tree)
    return None


if __name__ == '__main__':
    #a = indexer()
    #a.start()
    q = locate('msgid')
    #r = q.start(u'*', sortkey=u'date')
    #p = Paginator(r, perpage=40)
    #for y in p.page(1): print y['date'], y['subject']
    r = q.threadpage()
    #for y in r: print y
    import inspect
    print r
    print len(r)
    for i in r:
        w = inspect.getmembers(i)
        for y in w:
            print y
        print '\n\n\n'
    #printSubjects(r)
    #print r['messages']
    #print len(r['messages'])
