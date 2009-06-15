import email
import os
import mailbox
import tools
from datetime import datetime
import time

import cProfile

import threadMessages
import jwzthreading

import whoosh.index
from whoosh.fields import ID, TEXT, KEYWORD, STORED, Schema
from whoosh.writing import NO_MERGE, OPTIMIZE

from whoosh import store
from whoosh.qparser import QueryParser
from whoosh.searching import Paginator

from string import punctuation

import simplejson

global settings
f = open('settings.json', 'r')
settings = simplejson.loads(f.read())
f.close()

global badchars
badchars = dict(map(lambda x: (ord(x), None), punctuation))
dispHeight = 30

inuse_message_cache = None

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

        # whoosh's default of 4 megs of ram is simply not enough 
        # to index 500 megs of mail. the cache has to be flushed way
        # way too many times, and as a result slows indexing down immensely.
        self.writer = self.ix.writer(postlimit=256*1024*1024)

    def index_all(self):
        self.mtime = u'%s' % datetime.now().isoformat()

        print '%s - started indexing' % datetime.now()
        for mdir in settings['maildirinc']:
            self.mpath = os.path.join(settings['rdir'], mdir)
            self.maild = mailbox.Maildir(self.mpath, factory=mailbox.MaildirMessage, create=False)
            
            #speeds everything up by reading entire header cache into ram
            #before searching, rather than doing it one header at a time.
            self.maild._refresh()

            #for muuid, msg in self.maild.iteritems():

            print "%s - indexing %s" % (datetime.now(), mdir)
            [self.parse(muuid, msg) for muuid,msg in self.maild.iteritems()]
    
        print "%s - writing out and optimizing index" % datetime.now()
        self.writer.commit(OPTIMIZE)
        print "%s - writing complete" % datetime.now()

    def parse(self, muuid, msg):
        tmp = ' '.join([m.get_payload(decode=True) for m in \
                email.iterators.typed_subpart_iterator(msg) \
                if 'filename' not in m.get('Content-Disposition','')])
        clist = filter(lambda x: x, list(set(msg.get_charsets())))
        ucontent = None
        if clist == []: clist = ['utf-8']
        for citem in clist:
            try:
                ucontent = unicode(tmp, citem)
                break
            except: pass
    
        if ucontent is None:
            raise TypeError("couldn't encode email body into unicode properly.", clist, msg._headers, tmp, msg.get_charsets(), muuid, self.mpath)
        # FIXME: add in more robust error checking on unicode conversion.
        # ex- try guessing what the character that's giving us grief is.
        # fail that, just ignore the strangly encoded char
        # _so far_ the above works. then again, all email I've tested
        # was sent using a faily standard client, outlook, and downloaded
        # off a faily standard imap server, exchange, and I've not
        # received any emails encoded in anything exotic, like japanese or arabic
    
        msgid = u'%s' % msg['Message-ID']
        sent_date = email.utils.parsedate(msg['date'])

        self.writer.add_document(subject=u'%s' % msg['Subject'],
                            muuid=unicode(muuid),
                            msgid=msgid.translate(badchars),
                            _stored_msgid=msgid,
                            in_reply_to=u'%s' % msg['In-Reply-To'],
                            references=u'%s' % msg['References'],
                            recipient=u'%s' % msg['To'],
                            sender=u'%s' % msg['From'],
                            date=tools.uniencode_date(sent_date),
                            mtime=self.mtime,
                            labels=u'%s' % msg['Labels'],
                            content=ucontent,
                            _stored_content=ucontent[:80])


class result_machine(object):
    def __init__(self, pri_field=u"subject"):
        self.storage = store.FileStorage(settings['ixmetadir'])
        self.ix = whoosh.index.Index(self.storage)
        self.ix = whoosh.index.open_dir(settings['ixmetadir'])
        self.searcher = self.ix.searcher()
        self.parser = QueryParser(pri_field, schema=self.ix.schema)
        self.cache = {'references':[], 'messages': [], 'page': 1}

    def search(self, target, sortkey=None, resultlimit=5000):
        if sortkey is None:
            reverse = False
        else:
            reverse = True
        self.query = self.parser.parse(target)
        self.results = self.searcher.search(self.query, limit=resultlimit, sortedby=sortkey, reverse=reverse)
        return self.results

    def cacheadder(self, field, entity):
        self.newref = True
        self.cache[field].append(entity)

    def thread_search(self, recquery=u'muuid:*', pagenum=1, perpage=40, dispHeight=30, external_cache=None):
        if external_cache is not None: self.cache = external_cache

        # fuck, why am i searching AGAIN when i have the fucking cache?!
        self.results = self.start(recquery, sortkey='date', resultlimit=50000000)
        #print 'starting map'
        #print 'done with map, starting threading'
        #return jwzthreading.thread(self.results)
        #return threadMessages.jwzThread(self.results)
        return self.results
        if recquery == u'muuid:*':
            self.results = [ jwzthreading.make_message(self.msg) for self.msg in self.results ]
            self.results = jwzthreading.thread(self.results)
            return self.results
            self.results = Paginator(self.results, perpage=perpage).page(pagenum)

        self.newref = False
        #[self.cache['messages'].append(i) for i in self.results if i not in self.cache['messages']]
        [self.cacheadder('messages', i) for i in self.results if i not in self.cache['messages']]
        self.refs = [[p['in_reply_to'], p['references'].split()] for p in self.results]
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
            #self.refs = u' OR '.join(self.refs).translate(badchars)
            self.refs = self.refs.translate(badchars)
            self.subjects = [u'subject:(%s)' %
                    threadMessages.stripSubjJunk(x['subject']).translate(badchars) \
                    for x in self.results]
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


if __name__ == '__main__':
    #a = indexer()
    #a.index_all()
    import lazythread
    msgthread = lazythread.Thread()
    q = result_machine('msgid')
    #r = q.start(u'*', sortkey=u'date')
    #p = Paginator(r, perpage=40)
    #for y in p.page(1): print y['date'], y['subject']
    r = q.search('muuid:*', sortkey=u'date', resultlimit=50000000)
    print 'going for broke - lets thread!'
    print datetime.utcnow()
    #r = [ jwzthreading.make_message(msg) for msg in r]
    #r = jwzthreading.thread(r)
    msgthread.thread(r)
    print datetime.utcnow()
    print len(msgthread.threadList)
    msgthread.verify_thread()
    print 'done threading!'
    msgthread.sort()
    print 'done sorting'
    #for y in r: print y
    #import inspect
    #print r
    #print len(r)
    print msgthread.threadList[0]
    print msgthread.threadList[-1]
    '''for i in r:
        #print inspect.getmembers(i)
        print i
        print '\n\n\n'
        '''
    #printSubjects(r)
    #print r['messages']
    #print len(r['messages'])
