#!/usr/bin/python

from overwatch import mail_grab, settings

import pdb

from weakref import WeakValueDictionary
from email.iterators import typed_subpart_iterator
from Queue import Queue, Empty
from threading import Thread
from operator import itemgetter
from types import GeneratorType

import xappy

from lib.metautil import Singleton, MetaSuper
from databasics import msg_fields, msg_container, msg_factory, lazythread_container, conv_factory

srchidx = 'xap.idx'

class XapProxy(Singleton):
    __slots__ = ()
    __metaclass__ = MetaSuper
    _queue = Queue()
    thread_started = False
    indexer_started = False
    _idxconn = None

    def __init__(self):
        self.indexer_init()
        self.thread_init()

    def __getattr__(self, name):
        if name in xappy.IndexerConnection.__dict__:
            return self._q_add(name)
        raise AttributeError('No such attribute %s' % name)

    def worker(self):
        while 1:
            try: job = self._queue.get(True, 30)
            except Empty:
                self._idxconn.flush()
                self._idxconn.close()
                self.thread_started = False
                self.indexer_started = False
                break
            task, args, kwargs = job
            getattr(self.idxconn, task)(*args, **kwargs)
            self._queue.task_done()

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
            self._queue.add(action, args, kwargs)
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
sconn = xappy.SearchConnection(srchidx)

def _preindex_thread(msgs):
    tracker = {}
    for msg in msgs:
        if msg.thread: raise ValueError('This is weird. why am i trying to thread something that already has a thread id?')
        tracker[msg.msgid[0]] = msg

    threader = lazythread_container()
    all_msgs = iterdocs()
    if all_msgs:
        all_msgs = ( msg_factory( xmsg['muuid'][0], xmsg ) for xmsg in all_msgs )
        all_msgs = map(conv_factory, all_msgs)
        threader.thread(all_msgs)
    print 'threader b4 convs %s' % len(threader)
    threader.thread( map(conv_factory, msgs) )
    print 'threader after convs %s' % len(threader)

    pdb.set_trace()

    for key in tracker:
        conv = threader[key]
        threadid = conv.thread
        tracker[key].thread.append(threadid[0])
    return msgs, threader

def _ensure_threading_integrity(threader=None):
    if not threader:
        threader = lazythread_container()
        all_msgs = iterdocs()
        all_msgs = ( msg_factory( xmsg['muuid'][0], xmsg ) for xmsg in all_msgs )
        all_msgs = map(conv_factory, all_msgs)
        threader.thread(all_msgs)

    to_update = []
    to_replace = []

    def ctid_to_mtid(conv):
        ctid = conv.thread
        if len(ctid) == 2: ctid.remove(None)
        for msg in conv.messages:
            id_data_tple = (msg.muuid, [('thread', ctid)])
            if not msg.thread:
                to_update.append(id_data_tple)
            elif ctid != msg.thread:
                to_replace.append(id_data_tple)

    map(ctid_to_mtid, threader)
    docs = modify_factory(to_update, update_existing)
    docs.extend( modify_factory(to_replace, replace_existing) )
    return docs

def modify_factory(id_data_tples, modify_callback):
    """
    Used for getting the document items necessary for the search document
    modification functions.

    Examples of valid input data:
        (muuid, [(field,), (field,), ...])
        (muuid, [(field, (data,)), (field, (data, data,...)), (field, (data,))])

    Return data is a list of the now-modified documents, ready to be stored.
    """
    __docs = ( (_get_doc(muuid), data) for muuid,data in id_data_tples )
    __docs = modify_callback(__docs)
    __docs = map(itemgetter(1), __docs)
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
    map(doc.clear_field, fields)
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
        def per_field(field, datas):
            [ _do_append_field(doc, field, data) for data in datas ]
        map(per_field, data_tples)
        return doc

    __docs = ( (per_doc(doc, data_tples), data_tples) for doc,data_tples in doc_data_tples )
    return __docs

def modify_existing(id_data_tples, field, value=None, termadd=True, dataadd=None):
    """
    id_data_tples: list of tuples who values are (muuid, data)
    muuid = message universally unique identifier
    data = data to index
    """
    __moddocs = [ _modify_existing(muuid, field, data, value, termadd, dataadd) for muuid,data in id_data_tples ]
    __moddocs = [ __x.prepare() for __x in __moddocs ]
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

def _content_parse(muuid):
    msg = mail_grab.get(muuid)
    if not msg.is_multipart():
        __content = msg.get_payload(decode=True)
    else:
        __content = [m.get_payload(decode=True) for m in \
                        typed_subpart_iterator(msg, 'text', 'plain') \
                        if 'filename' not in m.get('Content-Disposition','')]
    __content = ' '.join(__content)
    return __content
    
def make_doc(msg):
    if type(msg) is not msg_container:
        msg = msg_factory(msg)
    __doc = _make_doc(msg)
    return __doc
        
def _make_doc(msg):
    doc = xappy.UnprocessedDocument()

    for field in msg_fields:
        if field == 'sample':
            __data = _content_parse(msg.muuid[0])
            _do_append_field(doc, 'content', __data)
            __data = __data[:80]
        else:
            __data = getattr(msg, field)

        if field == 'muuid': __doc.id = __data[0]
        if hasattr(__data, '__iter__'):
            [ _do_append_field(doc, field, __x) for __x in __data if __x ]
        else:
            _do_append_field(doc, field, __data)

    return doc

def _get_doc(muuid):
    try: doc = sconn.get_document(muuid)
    except KeyError:
        doc = make_doc(muuid)
    return doc


def _do_append_field(doc, field, data):
    try: doc.fields.__iter__
    except: doc.fields = []
    doc.fields.append(xappy.Field(field, data))
    return doc

def iterdocs():
    return ( sconn.get_document(__x).data for __x in sconn.iterids() )

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
    if ensure or since_last > 10:
        __docs.extend( _ensure_threading_integrity(threader) )
    __docs = map(xconn.process, __docs)
    map(xconn.replace, __docs)
    xconn.flush()


if __name__ == '__main__':
    all_rmsgs = [ msg_factory(muuid, msg) for muuid,msg in mail_grab.iteritems() ]
    print len(all_rmsgs)
    index_factory(all_rmsgs, True)
