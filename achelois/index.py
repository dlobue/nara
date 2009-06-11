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
        # to index 500 megs of ram. the cache has to be flushed way
        # way too many times, and as a result slows indexing down immensely.
        self.writer = self.ix.writer(postlimit=256*1024*1024)
        self.mtime = u'%s' % datetime.now().isoformat()

    def test(self):
        msg = self.maild.next()
        return msg

    def start(self):
        for mdir in settings['maildirinc']:
            self.mpath = os.path.join(settings['rdir'], mdir)
            self.maild = mailbox.Maildir(self.mpath, factory=mailbox.MaildirMessage, create=False)

            for muuid, msg in self.maild.iteritems():
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
            
                msgid = u'%s' % msg['Message-ID']
                self.writer.add_document(subject=u'%s' % msg['Subject'] or u'None',
                                    muuid=unicode(muuid),
                                    msgid=msgid.translate(badchars),
                                    _stored_msgid=msgid,
                                    in_reply_to=u'%s' % msg['In-Reply-To'],
                                    references=u'%s' % msg['References'],
                                    recipient=u'%s' % msg['To'],
                                    sender=u'%s' % msg['From'],
                                    date=u'%s' % datetime.fromtimestamp(msg.get_date()).isoformat(),
                                    mtime=self.mtime,
                                    labels=u'%s' % msg['Labels'],
                                    content=ucontent,
                                    _stored_content=ucontent[:80])
    
            print "writing out index"
            self.writer.commit(OPTIMIZE)

class locate(object):
    def __init__(self, pri_field=u"subject"):
        self.storage = store.FileStorage(settings['ixmetadir'])
        self.ix = whoosh.index.Index(self.storage)
        self.ix = whoosh.index.open_dir(settings['ixmetadir'])
        self.searcher = self.ix.searcher()
        self.parser = QueryParser(pri_field, schema=self.ix.schema)
        self.cache = {'references':[], 'messages': [], 'page': 1}

    def start(self, target, sortkey=None, resultlimit=5000):
        if sortkey is None:
            reverse = True
        else:
            reverse = False
        self.query = self.parser.parse(target)
        self.results = self.searcher.search(self.query, limit=resultlimit, sortedby=sortkey, reverse=reverse)
        return self.results

    def cacheadder(self, field, entity):
        self.newref = True
        self.cache[field].append(entity)

    def threadpage(self, recquery=u'muuid:*', pagenum=1, perpage=40, dispHeight=30, external_cache=None):
        if external_cache is not None: self.cache = external_cache

        # fuck, why am i searching AGAIN when i have the fucking cache?!
        self.results = self.start(recquery, sortkey='date', resultlimit=50000000)
        return threadMessages.jwzThread(self.results)
        if recquery == u'muuid:*':
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
    '''for i in r:
        w = inspect.getmembers(i)
        for y in w:
            print y
        print '\n\n\n'
        '''
    #printSubjects(r)
    #print r['messages']
    #print len(r['messages'])
