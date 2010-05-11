#!/usr/bin/python

from overwatch import mail_grab, settings, xapidx

from email.iterators import typed_subpart_iterator
from Queue import Queue, Empty
from threading import Thread
from operator import itemgetter
from functools import partial
from types import GeneratorType
from mailbox import MaildirMessage
import cPickle
from os import path

from datetime import datetime

import xappy

from settings import settingsdir
from lib.metautil import Singleton, MetaSuper
from databasics import msg_fields, msg_container, msg_factory, lazythread_container, conv_factory

from lib import threadmap, forkmap, exc

#srchidx = 'xap.idx'
srchidx = xapidx

class XapProxy(Singleton):
    __slots__ = ()
    __metaclass__ = MetaSuper
    _queue = Queue()
    thread_started = False
    indexer_started = False
    _idxconn = None

    #def __init__(self):
        #self.indexer_init()
        #self.thread_init()

    def __getattr__(self, name):
        if name in xappy.IndexerConnection.__dict__:
            return self._q_add(name)
        raise AttributeError('No such attribute %s' % name)

    def process(self, doc):
        try: return self._idxconn.process(doc)
        except:
            self.indexer_init()
            return self._idxconn.process(doc)

    def worker(self):
        def shutdown():
            self._idxconn.flush()
            try: sconn.reopen()
            except: pass
            self._idxconn.close()
            self.thread_started = False
            self.indexer_started = False
        while 1:
            try: job = self._queue.get(True, 30)
            except Empty:
                shutdown()
                break
            task, args, kwargs = job
            getattr(self._idxconn, task)(*args, **kwargs)

            self._queue.task_done()
            if task == 'flush':
                print "%s - processing flush now" % datetime.now()
                try: sconn.reopen()
                except: pass
                if self._queue.empty():
                    shutdown()
                    break

    def thread_init(self):
        if not self.thread_started:
            t = Thread(target=self.worker)
            t.start()
        self.thread_started = True
        if not self.indexer_started: self.indexer_init()

    def indexer_init(self):
        if not self.indexer_started:
            _idxconn = xappy.IndexerConnection(srchidx)
            self._idxconn = _set_field_actions(_idxconn)
        self.indexer_started = True
        if not self.thread_started: self.thread_init()

    def _q_add(self, action):
        def wrapper(*args, **kwargs):
            self._queue.put((action, args, kwargs))
            if not self.indexer_started: self.indexer_init()
            if not self.thread_started: self.thread_init()
        return wrapper


def _set_field_actions(idxconn):
    idxconn.add_field_action('subject', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
    idxconn.add_field_action('subject', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('osubject', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
    idxconn.add_field_action('osubject', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('to', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
    idxconn.add_field_action('to', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('sender', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
    idxconn.add_field_action('sender', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('cc', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
    idxconn.add_field_action('cc', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('content', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en', nopos=True)
    idxconn.add_field_action('sample', xappy.FieldActions.STORE_CONTENT)

    idxconn.add_field_action('labels', xappy.FieldActions.INDEX_EXACT)
    idxconn.add_field_action('labels', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('flags', xappy.FieldActions.INDEX_EXACT)
    idxconn.add_field_action('flags', xappy.FieldActions.STORE_CONTENT)

    idxconn.add_field_action('muuid', xappy.FieldActions.INDEX_EXACT)
    idxconn.add_field_action('muuid', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('msgid', xappy.FieldActions.INDEX_EXACT)
    idxconn.add_field_action('msgid', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('in_reply_to', xappy.FieldActions.INDEX_EXACT)
    idxconn.add_field_action('in_reply_to', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('references', xappy.FieldActions.INDEX_EXACT)
    idxconn.add_field_action('references', xappy.FieldActions.STORE_CONTENT)

    idxconn.add_field_action('sent', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('sent', xappy.FieldActions.SORTABLE, type='date')
    idxconn.add_field_action('mtime', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('mtime', xappy.FieldActions.SORTABLE, type='date')

    idxconn.add_field_action('thread', xappy.FieldActions.INDEX_EXACT)
    idxconn.add_field_action('thread', xappy.FieldActions.STORE_CONTENT)
    idxconn.add_field_action('thread', xappy.FieldActions.COLLAPSE)
    #idxconn.add_field_action('thread', xappy.FieldActions.SORTABLE, type='string')

    idxconn.set_max_mem_use(max_mem=256*1024*1024)

    return idxconn

xconn = XapProxy()

def _preindex_thread(msgs):
    tracker = {}
    for msg in msgs:
        if msg.thread: raise ValueError('This is weird. why am i trying to thread something that already has a thread id?')
        tracker[msg.msgid[0]] = msg

    threader = lazythread_container()
    all_msgs = iterdocs()
    if all_msgs:
        print 'yes to all_msgs'
        all_msgs = map(msg_factory, all_msgs)
        all_msgs = threadmap.map(conv_factory, all_msgs)
        threader.thread(all_msgs)
    print 'threader b4 convs %s' % len(threader)
    threader.thread( threadmap.map(conv_factory, msgs) )
    print 'threader after convs %s' % len(threader)

    c = 0
    ct = 0
    for conv in threader:
        ct+= len(conv.messages)
        if len(conv.messages) == 1:
            c+=1

    print "found %s threads with one msg" % c
    print "threader contains %s messages out of a total %s" % (ct, len(msgs))

    c = 0
    if all_msgs:
        for key in tracker:
            msg = tracker[key]
            try:
                try: conv = threader[key]
                except: conv = threader[msg.subject[0]]
            except:
                c+=1
                '''
                print "unable to find msg in thread"
                print key
                print msg.subject[0]
                '''
                continue
            threadid = conv.thread
            msg.thread.extend(threadid)
        print "%s messages didn't find a thread" % c
    return msgs, threader

def _ensure_threading_integrity(threader=None, all_new=False):
    if not threader:
        threader = lazythread_container()
        all_msgs = iterdocs()
        all_msgs = map(msg_factory, all_msgs)
        all_msgs = threadmap.map(conv_factory, all_msgs)
        threader.thread(all_msgs)

    to_update = []
    to_replace = []

    def ctid_to_mtid(conv):
        ctid = conv.thread
        for msg in conv.messages:
            id_data_tple = (msg, [('thread', ctid)]) #optimization: pass msg_container so we don't have to rebuild it again
            #id_data_tple = (msg.muuid, [('thread', ctid)])
            if not msg.thread:
                to_update.append(id_data_tple)
            elif ctid != msg.thread:
                to_replace.append(id_data_tple)

    threadmap.map(ctid_to_mtid, threader)
    print "in update queue  %i" % len(to_update)
    print "in replace queue %i" % len(to_replace)
    print '%s - starting modify factory on to_update' % datetime.now()
    docs1 = modify_factory(to_update, update_existing, all_new)
    print '%s - starting modify factory on to_replace' % datetime.now()
    #docs.extend( modify_factory(to_replace, replace_existing, all_new) )
    docs2 = modify_factory(to_replace, replace_existing, all_new)
    def chn_gen(gg):
        it = gg.next()
        while 1:
            try: r = it.next()
            except StopIteration:
                try:
                    it = gg.next()
                    continue
                except StopIteration:
                    break
            yield r

    docs = chn_gen( (x for x in [docs1, docs2]) )
    return docs

def modify_factory(id_data_tples, modify_callback, all_new=False):
    """
    Used for getting the document items necessary for the search document
    modification functions.

    Examples of valid input data:
        (muuid, [(field,), (field,), ...])
        (muuid, [(field, (data,)), (field, (data, data,...)), (field, (data,))])

    Return data is a list of the now-modified documents, ready to be stored.
    """
    print '%s - building tuples' % datetime.now()
    if all_new:
        #__docs = forkmap.map(lambda x: (make_doc(x[0]), x[1]), id_data_tples )
        #__docs = forkmap.map(lambda x: (make_doc(x[0]), x[1]), id_data_tples )
        __docs = ( (make_doc(muuid), data) for muuid,data in id_data_tples )
    else:
        #__docs = threadmap.map(lambda x: (_get_doc(x[0]), x[1]), id_data_tples )
        #__docs = forkmap.map(lambda x: (_get_doc(x[0]), x[1]), id_data_tples )
        #__docs = threadmap.map(lambda muuid,data: (_get_doc(muuid), data), id_data_tples )
        __docs = ( (_get_doc(muuid), data) for muuid,data in id_data_tples )
    print '%s - running callback modifier' % datetime.now()
    __docs = modify_callback(__docs)
    print '%s - extracting docs' % datetime.now()
    #__docs = threadmap.map(itemgetter(0), __docs)
    __docs = (x[0] for x in __docs)
    return __docs

def remove_fields(doc_data_tples):
    """
    doc_field_tples: list of tuples whose values are like either below
        (doc, [(field,), (field,), ...])
        (doc, [(field, (data,)), (field, (data, data,...)), (field, (data,))])
    """
    __docs = ( (_remove_fields(doc, zip(*data)[0]), data) for doc,data in doc_data_tples )
    return __docs

def _remove_fields(doc, fields):
    try: map(doc.clear_field, fields)
    except:
        print exc.format_exc_info()
    return doc

def replace_existing(doc_data_tples):
    """
    doc_data_tples: list of tuples like below
        (doc, [(field, (data,)), (field, (data, data,...)), (field, (data,))])
    """
    doc_data_tples = remove_fields(doc_data_tples)
    doc_data_tples = update_existing(doc_data_tples)
    return doc_data_tples

def update_existing(doc_data_tples):
    """
    Update a series of existing messages 
    doc_data_tples: list of tuples like below
        (doc, [(field, (data,)), (field, (data, data,...)), (field, (data,))])
    """
    def per_doc(doc, data_tples):
        def per_field(data_tple):
            field, datas = data_tple
            map(_do_append_field(doc, field), datas)
        map(per_field, data_tples)
        return doc

    #__docs = threadmap.map(lambda x: (per_doc(x[0], x[1]), x[1]), doc_data_tples )
    #__docs = threadmap.map(lambda doc,data_tples: (per_doc(doc, data_tples), data_tples), doc_data_tples )
    __docs = ( (per_doc(doc, data_tples), data_tples) for doc,data_tples in doc_data_tples )
    return __docs

def modify_existing(id_data_tples, field, value=None, termadd=True, dataadd=None):
    """
    id_data_tples: list of tuples who values are (muuid, data)
    muuid = message universally unique identifier
    data = data to index
    """
    #__moddocs = [ _modify_existing(muuid, field, data, value, termadd, dataadd) for muuid,data in id_data_tples ]
    #__moddocs = [ __x.prepare() for __x in __moddocs ]
    __moddocs = ( _modify_existing(muuid, field, data, value, termadd, dataadd) for muuid,data in id_data_tples )
    __moddocs = ( __x.prepare() for __x in __moddocs )
    map(xconn.replace, __moddocs)
    xconn.flush()

def _modify_existing(muuid, field, data, value=None, termadd=True, dataadd=None):
    __doc = sconn.get_document(muuid)
    if type(data) is list:
        if len(data) > 1: raise TypeError("data is a list containing more than one value. this function should only be called once per value. data contains: %s" % str(data))
        data = data[0]
    if termadd: __doc.add_term(field, data)
    if value: __doc.add_value(field, data, value)
    if dataadd is False: pass
    elif dataadd is True: __doc.data[field] = [data]
    elif dataadd is None: 
        try: __test = __doc.data[field]
        except: pass
        else:
            if __test: return __doc
        __doc.data[field] = [data]
    return __doc

def content_parse(muuid):
    msg = mail_grab.get(muuid)
    r = _content_parse(msg)
    return r

def _content_parse(msg):
    if not msg.is_multipart():
        __content = msg.get_payload(decode=True)
    else:
        __content = (m.get_payload(decode=True) for m in \
                        typed_subpart_iterator(msg, 'text', 'plain') \
                        if 'filename' not in m.get('Content-Disposition',''))
        __content = ' '.join(__content)
    return __content

def make_doc(msg, threader=None):
    '''
    Build xapian document from a msg_container or from a MaildirMessage
    '''
    if type(msg) is not msg_container:
        if type(msg) is tuple and isinstance(msg[1], MaildirMessage):
            srcmesg = msg[1]
        else:
            srcmesg = None
        msg = msg_factory(msg)
    if threader:
        threader.thread(msg)
    doc = xappy.UnprocessedDocument()
    map(partial(_make_doc, doc, msg, srcmesg=srcmesg), msg_fields)
    #__doc = _make_doc(msg)
    return doc

#def _make_doc(msg):

    #for field in msg_fields:
def _make_doc(doc, msg, field, srcmesg=None):
        if field == 'sample':
            if srcmesg:
                __data = _content_parse(srcmesg)
            else:
                __data = content_parse(msg.muuid[0])
            _do_append_field(doc, 'content', __data)
            __data = __data[:80]
        else:
            __data = getattr(msg, field)

        if field == 'muuid': doc.id = __data[0]
        if hasattr(__data, '__iter__'):
            [ _do_append_field(doc, field, __x) for __x in __data if __x ]
        else:
            _do_append_field(doc, field, __data)

    #return doc

def _get_doc(muuid):
    if hasattr(muuid, '__iter__'):
        muuid = muuid[0]
    try: doc = sconn.get_document(muuid)
    except KeyError:
        doc = make_doc(muuid)
    return doc


def _do_append_field(doc, field, data=None):
    def wrapper(data):
        try: doc.fields.__iter__
        except: doc.fields = []
        doc.fields.append(xappy.Field(field, data))
        return doc
    if data: return wrapper(data)
    else: return wrapper

def iterdocs():
    return ( _get_doc(__x) for __x in sconn.iterids() )

def index_factory(msgs, ensure=False):
    if not hasattr(msgs, '__iter__'):
        msgs = [msgs]
    if type(msgs) is GeneratorType:
        ensure = True
        msg_count = 0
        tot_count = 0
        last_integ_chk = 0
        since_last = 0
    else:
        msg_count = len(msgs)
        tot_count = msg_count + settings.get('total_indexed',0)
        last_integ_chk = settings.get('integrity_chk',0)
        since_last = tot_count - last_integ_chk

    if ensure or msg_count > 10 or since_last > 10:
        msgs, threader =_preindex_thread(msgs)
    __docs = map(make_doc, msgs)
    print 'after make_doc %i' % len(__docs)
    #if ensure or since_last > 10:
        #__docs.extend( _ensure_threading_integrity(threader) )
    #__docs = map(xconn.process, __docs)
    map(xconn.replace, __docs)
    xconn.flush()


if __name__ == '__main__':
    print "%s - started indexing" % datetime.now()
    try: sconn = xappy.SearchConnection(srchidx)
    except:
        xconn.indexer_init()
        sconn = xappy.SearchConnection(srchidx)
    import time
    print 'iterating through mail and creating msg_containers'
    t = time.time()
    #all_rmsgs = [ msg_factory(muuid, msg) for muuid,msg in mail_grab.iteritems() ]
    #all_msgs = forkmap.map(msg_factory, mail_grab.iteritems())
    #t = time.time() - t
    #print "done! took %r seconds" % t
    #print 'all_rmsgs %i' % len(all_msgs)

    #print 'starting index factory now'
    #t = time.time()
    #index_factory(all_msgs, True)
    #t = time.time() - t
    #print "done! took %r seconds" % t


    #import sys
    #sys.exit()
    #print "building msgs now"
    #t = time.time()
    #all_msgs = forkmap.map(msg_factory, iterdocs())
    #t = time.time() - t
    #print "done! took %r seconds" % t
    #threader = lazythread_container()
    #print "building conversations"
    #t = time.time()
    #convs = map(conv_factory, all_msgs)
    #convs = threadmap.map(conv_factory, all_msgs)
    #t = time.time() - t
    #print "done! took %r seconds" % t
    #print 'threading'
    #t = time.time()
    #threader.thread( convs )
    #t = time.time() - t
    #print "done! took %r seconds" % t
    #print len(threader), ' conversations'
    #c = 0
    #for conv in threader:
        #c+=len(conv.messages)
    #print c, " total messages, out of ", len(all_msgs)
    #print 'running integrity checker'
    #t = time.time()
    #docs = _ensure_threading_integrity(threader, True)
    #t = time.time() - t
    #print "done! took %r seconds" % t
    #print "pickling results"
    #t = time.time()
    #finwork = path.join(settingsdir, 'preprocess.pickle')
    #try:
        #with open(finwork, 'wb') as f:
            #cPickle.dump(docs, f)
            #except:
                #pass
    #t = time.time() - t
    #print "done! took %r seconds" % t
    #print 'processing docs'
    #t = time.time()
    #docs = threadmap.map(xconn.process, docs)
    #docs = map(xconn.process, docs)
    #t = time.time() - t
    #print "done! took %r seconds" % t
    from stream import ForkedFeeder, PCollector

    print 'making xapian docs from maildir sources'
    t = time.time()
    threader = lazythread_container()
    #docs = PCollector()
    def getgen():
        return (make_doc(x, threader=threader) for x in mail_grab.iteritems())
    #for _ in range(4):
        #ForkedFeeder(getgen) >> docs
    docs = (make_doc(x, threader=threader) for x in mail_grab.iteritems())
    #docs = forkmap.map(partial(make_doc, threader=threader), mail_grab.iteritems())
    t = time.time() - t
    print "done! took %r seconds" % t

    print 'queueing docs'
    t = time.time()
    map(xconn.replace, docs)
    xconn.flush()
    t = time.time() - t
    print "done! took %r seconds" % t
    print "waiting for work to finish"
    print "%s - started waiting at" % datetime.now()
