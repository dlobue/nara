
from datetime import datetime
from email.utils import parsedate
from email.iterators import typed_subpart_iterator
from threading import Thread, Lock
from multiprocessing import Queue as pQueue
from multiprocessing import Process
from Queue import Queue, Empty
import logging

from overwatch import mail_grab, xappy, xapidx
from lib.metautil import Singleton, MetaSuper
from tools import delNone, filterNone

logger = logging.getLogger('nara.%s' % __name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


index_msg_fields = ('sent', 'sender', 'to', 'cc', 'subject', 'labels', 'flags', 'subdir')
index_conv_fields = ('unique_terms', 'muuids')
unique_terms = ('subject', 'msgid', 'in_reply_to', 'references')

field_map = {'sender': 'From', 'msgid': 'Message-ID', 'sent': 'Date',
                    'subject': 'Subject', 'in_reply_to': 'In-Reply-To'}
field_map_blank = {}
field_multis = {'cc':',', 'to':',', 'flags':None, 'labels':None, 'references':None}

flag_label_map = {'D': 'draft',
                  'F': 'starred',
                  'P': 'resent',
                  'R': 'replied',
                  'S': 'read',
                  'T': 'delete'
                 }

subdir_label_map = {'new': 'unseen', 'cur': '-unseen'}

def _content_parse(msg):
    if not msg.is_multipart():
        __content = msg.get_payload(decode=True)
    else:
        __content = (m.get_payload(decode=True) for m in \
                        typed_subpart_iterator(msg, 'text', 'plain') \
                        if 'filename' not in m.get('Content-Disposition',''))
        __content = ' '.join(__content)
    return __content


field_action_map = {'content': _content_parse,
                    'subdir': lambda msg: msg.get_subdir(),
                    'flags': lambda msg: [x for x in msg.get_flags()],
                   }



def IndexerProcess(xapdb_path, que):
    xapproxy = XapProxy(xapdb_path, _set_field_actions)
    while 1:
        try:
            work = que.get(True, 30)
        except Empty:
            xapproxy.flush()
            break
            #do some cleanup and kill process

        task = work[0]
        globals()[task](xapproxy, *work[1:])


def _populate_fields(msg, doc, labels):
    for field in index_msg_fields:
        data = _extract_msg_data(msg, field)
        if data:
            if field in ('subdir', 'flags'):
                field = 'labels'
            _do_append_field(doc, field, data)
    
    doc = _add_labels(doc, labels)

    return doc

def index(xapproxy, msg_key, labels):
    msg = mail_grab.get(msg_key)
    doc = xappy.UnprocessedDocument()
    doc.id = str(msg_key)
    doc = _populate_fields(msg, doc, labels)
    doc = _do_append_field(doc, 'content', _content_parse(msg))
    xapproxy.replace(doc)
    # to send following to conv indexer
    #data = [ _extract_msg_data(msg, field) for field in index_conv_fields ]


def _add_labels(doc, labels):
    for label in labels:
        _do_append_field(doc, 'labels', label)
    return doc

def add_labels(xapproxy, msg_key, labels):
    if not isinstance(msg_key, (str, unicode)):
        msg_key = str(msg_key)
    doc = xapproxy.get_document(msg_key)
    doc = _add_labels(doc, labels)
    xapproxy.replace(doc)

def _do_append_field(doc, field, data):
    if hasattr(data, '__iter__'):
        [ _do_append_field(doc, field, d) for d in data ]
        return doc
    if not hasattr(doc, 'fields') or doc.fields is None:
        doc.fields = []
    #logger.debug('Field: "%s" Content: """%r"""' % (field, data))
    doc.fields.append(xappy.Field(field, data))
    return doc


def _extract_msg_data(msg, field):
    def do_multi(data):
        try: __x = filterNone(set(data.split(field_multis[field])))
        except AttributeError: __x = data
        if hasattr(__x, '__iter__'):
            try: __x = [ i.strip() for i in __x ]
            except AttributeError:
                pass
        return __x

    field_name = field_map.get(field, field)
    __data = field_action_map.get(field_name,
                                  lambda msg: msg.get(field_name, None))(msg)
    if __data is None:
        if field not in field_multis:
            return None
        else:
            __data = []

    if field in field_multis:
        __data = do_multi(__data)
    elif field == 'sent':
        __data = datetime(*parsedate(__data)[:6])

    return __data



class XapProxy(Singleton):
    #__slots__ = ()
    _queue = Queue()
    thread_started = False
    indexer_started = False
    _idxconn = None
    _worker = None
    _timeout = 1
    _lock = Lock()
    _noque = ('process', 'iterids', 'get_document', 'iter_facet_query_types',
              'iter_subfacets', 'iter_synonyms')

    def __init__(self, idxdb, actions_init):
        self._idxdb = idxdb
        self._set_field_actions = actions_init

    def __getattr__(self, name):
        if name in self._noque:
            try:
                if self._idxconn._index is None:
                    self.indexer_init()
                return getattr(self._idxconn, name)
            except (xappy.IndexerError, AttributeError):
                self.indexer_init()
                return getattr(self._idxconn, name)
        elif hasattr(xappy.IndexerConnection, name):
            return self._q_add(name)
        raise AttributeError('No such attribute %s' % name)

    def flush(self):
        '''
        Flush all writes to the database and don't do
        anything else until done!
        '''
        print "flush called now"
        self._q_add('flush')()
        #self._queue.join()
        self._worker.join()
        if self._lock.locked():
            print "lock still locked??!"
            self._lock.release()
        if self.thread_started:
            print "thread is still started??!!"
            self.thread_started = False
        if self.indexer_started:
            print "indexer is still started??!!"
            self.indexer_started = False
        print "worker should now be done, and all cleanup checks run"

    def worker(self):
        with self._lock:
            def shutdown():
                self._idxconn.flush()
                self._idxconn.close()
                self.thread_started = False
                self.indexer_started = False
            while 1:
                try: job = self._queue.get(True, self._timeout)
                except Empty:
                    shutdown()
                    break
                task, args, kwargs = job
                try: getattr(self._idxconn, task)(*args, **kwargs)
                except xappy.XapianDatabaseModifiedError, e:
                    self._idxconn._index.reopen()
                    getattr(self._idxconn, task)(*args, **kwargs)

                self._queue.task_done()
                if task == 'flush':
                    print "%s - processing flush now" % datetime.now()
                    if self._queue.empty():
                        shutdown()
                        break

    def thread_init(self):
        with self._lock:
            if not self.thread_started:
                t = Thread(target=self.worker)
                #t.daemon = True
                t.start()
                self._worker = t
            self.thread_started = True
        if not self.indexer_started: self.indexer_init()

    def indexer_init(self):
        with self._lock:
            if not self.indexer_started:
                _idxconn = xappy.IndexerConnection(self._idxdb)
                self._idxconn = self._set_field_actions(_idxconn)
            self.indexer_started = True
        if not self.thread_started: self.thread_init()

    def delete(self, docid):
        return self._q_add('delete')(docid)

    def _q_add(self, action):
        def wrapper(*args, **kwargs):
            self._queue.put((action, args, kwargs))
            if not self.indexer_started: self.indexer_init()
            if not self.thread_started: self.thread_init()
        return wrapper






def stripSubject(subj):
    '''strips out all "re:"s and "fwd:"s'''
    to_strip = ('re:', 'Re:', 'RE:', 'fw:', 'Fw:', 'FW:', 'fwd:', 'Fwd:', 'FWD:')

    osubj = subj
    subj = subj.split(' ')
    isubj = iter(subj)
    modified = False
    while 1:
        try:
            sbjprt = isubj.next()
        except StopIteration:
            #XXX: none, or an empty string?
            return None

        if sbjprt in to_strip:
            subj.pop(0)
            modified = True
        else:
            if modified:
                return ' '.join(subj)
            else:
                return osubj



def _set_msgdb_field_actions(idxconn):
    idxconn.add_field_action('subject', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en')
    idxconn.add_field_action('to', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en')
    idxconn.add_field_action('sender', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en')
    idxconn.add_field_action('cc', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en')
    idxconn.add_field_action('content', xappy.FieldActions.INDEX_FREETEXT,
                                                    language='en')

    idxconn.add_field_action('labels', xappy.FieldActions.FACET, type='string')
    idxconn.add_field_action('labels', xappy.FieldActions.STORE_CONTENT)

    idxconn.add_field_action('sent', xappy.FieldActions.SORTABLE, type='date')

    idxconn.set_max_mem_use(max_mem=256*1024*1024)

    return idxconn



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



if __name__ == '__main__':
    from functools import partial
    from change_scan import update_maildir_cache, scan_mail, created_listener,\
            destroy_listener, File, Directory, indexer_listener
    from sqlobject.events import listen, RowDestroySignal, RowCreatedSignal

    msg_indexer_queue = pQueue()

    ps = []
    p = Process(target=IndexerProcess, args=('%s%i' % (xapidx, 1), msg_indexer_queue))
    ps.append(p)
    p.start()

    p = Process(target=IndexerProcess, args=('%s%i' % (xapidx, 2), msg_indexer_queue))
    ps.append(p)
    p.start()

    p = Process(target=IndexerProcess, args=('%s%i' % (xapidx, 3), msg_indexer_queue))
    ps.append(p)
    p.start()


    il = indexer_listener(msg_indexer_queue)
    listen(il.created_listener, File, RowCreatedSignal)
    #listen(partial(created_listener, msg_indexer_queue=msg_indexer_queue), File, RowCreatedSignal)
    #listen(destroy_listener, File, RowDestroySignal)
    from time import time
    t = time()
    update_maildir_cache(scan_mail())
    t = time() - t
    print('took %r seconds to scan messages' % t)

