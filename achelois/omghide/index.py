from datetime import datetime
from achelois.offlinemaildir import mail_sources
import tools
from email.utils import parsedate, getaddresses
from email.iterators import typed_subpart_iterator
#from mailbox import Maildir, MaildirMessage

from lazythread import stripSubject

from uuid import uuid4
import xappy

#from settings import settings
#from string import punctuation

#global badchars
#badchars = dict(map(lambda x: (ord(x), None), punctuation))

#inuse_message_cache = None

class indexer(object):
    def __init__(self):

        #self.mpath = os.path.join(settings['rdir'], settings['maildirinc'][1])
        #self.maild = mailbox.Maildir(self.mpath, factory=mailbox.MaildirMessage, create=False)

        self.mail_sources = mail_sources()

        self.stripSubj = stripSubject
        self.deuniNone = tools.deuniNone
        self.usplit = unicode.split
        self.ssplit = str.split
        self.strip = str.strip

    def split(self, *x):
        try: return self.ssplit(*x)
        except: return self.usplit(*x)

    def open_set_act(self):
        xconn = xappy.IndexerConnection('xap.idx')

        xconn.add_field_action('subject', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
        xconn.add_field_action('subject', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('osubject', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
        xconn.add_field_action('osubject', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('recipient', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
        xconn.add_field_action('recipient', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('sender', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
        xconn.add_field_action('sender', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('cc', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
        xconn.add_field_action('cc', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('content', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
        xconn.add_field_action('sample', xappy.FieldActions.STORE_CONTENT)

        xconn.add_field_action('labels', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('labels', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('flags', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('flags', xappy.FieldActions.STORE_CONTENT)

        xconn.add_field_action('muuid', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('muuid', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('msgid', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('msgid', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('in_reply_to', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('in_reply_to', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('references', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('references', xappy.FieldActions.STORE_CONTENT)

        #xconn.add_field_action('date', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('date', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('date', xappy.FieldActions.SORTABLE, type='date')
        #xconn.add_field_action('mtime', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('mtime', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('mtime', xappy.FieldActions.SORTABLE, type='date')

        xconn.add_field_action('thread', xappy.FieldActions.INDEX_EXACT)
        xconn.add_field_action('thread', xappy.FieldActions.STORE_CONTENT)
        xconn.add_field_action('thread', xappy.FieldActions.COLLAPSE)
        #xconn.add_field_action('thread', xappy.FieldActions.SORTABLE, type='string')

        self.writer = xconn
        self.writer.set_max_mem_use(max_mem=256*1024*1024)


    def index_all(self):
        try: self.writer
        except: self.open_set_act()

        self.mtime = datetime.now()
        #self.mtime = u'%s' % datetime.now().isoformat()

        print '%s - started indexing' % datetime.now()
        __undocs = [self.parse(muuid,msg) for muuid,msg in self.mail_sources.iteritems()]
        print "%s - processing" % datetime.now()
        __pdocs = map(self.writer.process, __undocs)
        print "%s - writing out index" % datetime.now()
        map(self.writer.add, __pdocs)
        print "%s - flushing" % datetime.now()
        self.writer.flush()
        print "%s - writing complete" % datetime.now()
        self.writer.close()

    def parse(self, muuid, msg=None):
        if msg: __msg = msg
        else:
            __msg = self.mail_sources.get(muuid)

        if not __msg.is_multipart():
            __content = __msg.get_payload(decode=True)
        else:
            __content = ' '.join([m.get_payload(decode=True) for m in \
                                    typed_subpart_iterator(__msg, 'text', 'plain') \
                                    if 'filename' not in m.get('Content-Disposition','')])


        '''__tmp = ' '.join([m.get_payload(decode=True) for m in \
                typed_subpart_iterator(__msg) \
                if 'filename' not in m.get('Content-Disposition','')])
        __clist = filter(lambda x: x, list(set(__msg.get_charsets())))
        __ucontent = None
        if __clist == []: __clist = ['utf-8']
        for __citem in __clist:
            try:
                __ucontent = unicode(__tmp, __citem)
                break
            except: pass
    
        if __ucontent is None:
            raise TypeError("couldn't encode email body into unicode properly.", __clist, __msg._headers, __tmp, __msg.get_charsets(), muuid, self.mpath)
        '''
        # FIXME: add in more robust error checking on unicode conversion.
        # ex- try guessing what the character that's giving us grief is.
        # fail that, just ignore the strangly encoded char
        # _so far_ the above works. then again, all email I've tested
        # was sent using a faily standard client, outlook, and downloaded
        # off a faily standard imap server, exchange, and I've not
        # received any emails encoded in anything exotic, like japanese or arabic
    
        # in case timezone ever becomes an issue...
        #__sent_date = parsedate_tz(__msg['date'])
        #__tz = __sent_date[-1]
        #if __tz is None:

        __sent_date = datetime(*parsedate(__msg['date'])[:6])
        __subj = __msg['Subject']

        __doc = xappy.UnprocessedDocument()
        __doc.fields.append(xappy.Field('subject', self.stripSubj(__subj) or ''))
        __doc.fields.append(xappy.Field('osubject', __subj or ''))
        __doc.fields.append(xappy.Field('muuid', muuid))
        __doc.fields.append(xappy.Field('msgid', __msg['Message-ID'] or ''))
        __doc.fields.append(xappy.Field('in_reply_to', __msg['In-Reply-To'] or ''))
        __doc.fields.append(xappy.Field('sender', __msg['From'] or ''))
        __doc.fields.append(xappy.Field('date', __sent_date))
        __doc.fields.append(xappy.Field('mtime', self.mtime))
        __doc.fields.append(xappy.Field('content', __content or ''))
        __doc.fields.append(xappy.Field('sample', __content[:80] or ''))


        def multi_add(field, data=None, split=False, strip=False, spliton=None):
            if data:    __x = data
            else:       __x = __msg[field]
            if __x:
                if split: __x = self.deuniNone(set(self.split(__x, spliton)))
                for __i in __x:
                    if strip: __i = __i.strip()
                    __doc.fields.append(xappy.Field(field, __i))
            else:
                __doc.fields.append(xappy.Field(field, ''))

        __flags = [x for x in __msg.get_flags()]

        multi_add('labels', split=True)
        multi_add('flags', data=__flags)
        multi_add('references', split=True)
        multi_add('recipient', split=True, strip=True, spliton=',')
        multi_add('cc', split=True, strip=True, spliton=',')

        #__doc.fields.append(xappy.Field('thread', ''))
        __doc.id = muuid

        return __doc
        #self.writer.add(__doc)


class threadIndexer(object):
    def __init__(self):
        xconn = xappy.IndexerConnection('xap.idx')
        #xconn.add_field_action('thread', xappy.FieldActions.INDEX_EXACT)
        #xconn.add_field_action('thread', xappy.FieldActions.STORE_CONTENT)
        #xconn.add_field_action('thread', xappy.FieldActions.COLLAPSE)
        #xconn.add_field_action('thread', xappy.FieldActions.SORTABLE, type='string')
        self.writer = xconn
        self.writer.set_max_mem_use(max_mem=256*1024*1024)

        import lazythread
        self.thread = lazythread.lazy_thread()

    def test_ids(self):
        for id in self.writer.iterids():
            print id

    def start(self):
        print '%s starting thread indexer' % datetime.now()
        __r = (self.writer.get_document(x).data for x in self.writer.iterids())
        print '%s done making generator' % datetime.now()
        self.thread.thread(__r)
        print '%s done threading' % datetime.now()
        __replacements = []

        for thread in self.thread:
            newid = True
            try: threadid = thread.threadid
            except: threadid = uuid4().hex
            else:
                if threadid: newid = False
                else: threadid = uuid4().hex

            for msg in thread.messages:
                try: __id = msg['muuid']
                except: __id = msg[1]['muuid']
                if type(__id) is list: __id = __id[0]
                try: __doc = self.writer.get_document(__id)
                except KeyError:
                    print "wtf, couldn't find msg %s... try later" % __id
                    continue
                __doc.add_term('thread', threadid)
                __doc.add_value('thread', threadid, 'collsort')
                __doc.data['thread'] =  [threadid]
                __doc.prepare()
                __replacements.append(__doc)


        print '%s done prepping index update, writing out' % datetime.now()
        map(self.writer.replace, __replacements)
        print '%s done updating index on threading' % datetime.now()
        self.writer.flush()
        self.writer.close()


'''class result_machine(object):
    def __init__(self, pri_field=u"muuid"):
        self.storage = store.FileStorage(settings['ixmetadir'])
        self.ix = whoosh.index.Index(self.storage)
        self.ix = whoosh.index.open_dir(settings['ixmetadir'])
        self.searcher = self.ix.searcher()
        self.parser = QueryParser(pri_field, schema=self.ix.schema)
        self.cache = {'references':[], 'messages': [], 'page': 1}

    def search(self, target, sortkey=None, resultlimit=5000):
        if sortkey is None:
            __reverse = False
        else:
            __reverse = True
        __query = self.parser.parse(target)
        __results = self.searcher.search(__query, limit=resultlimit, sortedby=sortkey, reverse=__reverse)
        return __results

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
            return thread'''


if __name__ == '__main__':
    #import time
    a = indexer()
    a.index_all()
    #ti = threadIndexer()
    #ti.start()
    #ti.test_ids()