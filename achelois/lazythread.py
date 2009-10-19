'''Since I don't care about the structure of the message,
I'm not going to bother with jwz's threading algorithem,
which isn't very pythonic anyway.

structure of container:
    { 'msgids': [], 'subjects': [], 'messages': [] }
'''

from tools import deuniNone, unidecode_date
from bisect import insort_right
from weakref import WeakValueDictionary
from uuid import uuid4


def stripSubject(subj):
    '''strips out all "re:"s and "fwd:"s'''
    __lower = str.lower
    __ulower = unicode.lower
    __strip = str.strip
    __ustrip = unicode.strip
    def lower(x):
        try: return __lower(x)
        except: return __ulower(x)
    def strip(x):
        try: return __strip(x)
        except: return __ustrip(x)

    while 1:
        l = lower(subj)
        if l.startswith(u're:') or l.startswith(u'fw:'):
            subj = strip(subj[3:])
        elif l.startswith(u'fwd:'):
            subj = strip(subj[4:])
        else:
            return subj

def xap_container(msg):
    __msgid = set(msg.get('msgid'))
    __in_reply = set(msg.get('in_reply_to'))
    __refs = set(msg.get('references'))

    __msgids = __msgid | __in_reply | __refs
    try: __msgids.remove('')
    except KeyError: pass
    __subjects = set(msg.get('subject',[]))
    try: __subjects.remove('')
    except KeyError: pass
    __labels = set(msg.get('labels',[]))
    try: __labels.remove('')
    except KeyError: pass

    try: __threadid = msg.get('thread',[])[0]
    except KeyError: __threadid = None
    except IndexError: __threadid = None

    return convContainer(__msgids, __subjects, __labels,
                            [(msg.get('date')[0], msg)],
                            threadid=__threadid)

class convContainer(dict):
    def __init__(self, msgids, subjects, labels, messages, threadid=None):
        self['msgids'] = msgids
        self['subjects'] = subjects
        self['messages'] = messages
        self['labels'] = labels
        self['threadid'] = threadid
        
        #becuse attributes are fun
        self.msgids = self['msgids']
        self.subjects = self['subjects']
        self.messages = self['messages']
        self.labels = self['labels']
        self.threadid = self['threadid']

    @property
    def last_update(self):
        return self.messages[-1][0]
    @property
    def id(self):
        return self['id']

    def __repr__(self):
        __ddate = self.messages[-1][-1]['date']
        __dsender = u','.join([x[-1]['sender'].split()[0].strip('"') for x in self.messages[-3:]])
        __dcontained = len(self.messages)
        __dsubject = stripSubject(self.messages[-1][-1].get(u'subject',u''))
        __dlabels = u' '.join(u'+%s' % x for x in self.labels)
        __dpreview = u' '.join(self.messages[-1][-1].get(u'content',u'').split())
        __disprender = u"%s\t%s\t%i\t%s %s %s" % \
            (__ddate, __dsender, __dcontained, __dsubject, __dlabels, __dpreview)
        return __disprender

class lazy_thread(object):
    def __init__(self):
        #this is where all the good stuff is stored
        self.threadList = []
        self.thread_dict = WeakValueDictionary()
#        e = bsddb.db.DBEnv()
#        e.set_cachesize(0, 20480)
#        e.set_lk_detect(db.DB_LOCK_DEFAULT)
#        e.open('/root/.achelois/bsddb', db.DB_PRIVATE | db.DB_CREATE | db.DB_THREAD | db.DB_INIT_LOCK | db.DB_INIT_MPOOL)
#        self.thread_persist = dbshelve.open('conv_shelve.db', dbenv=e)
#        #d = db.DB(e)
#        d = dbshelve.DBShelf(e)
#        d.db.set_bt_compare(conv_btree_cmp)
#        d.open('conv_secondary.db', db.DB_BTREE, db.DB_CREATE, 0660)
#        self.threadList = d
#        self.thread_persist.associate(d.db, conv_callback, db.DB_CREATE)

        #because calling a function once is faster
        #than calling it 9000 times.
        self.get = dict.get
        self.split = unicode.split
        self.deuniNone = deuniNone
        self.unidecode_date = unidecode_date


    def __getslice__(self, beg, end):
        return self.threadList.__getslice__(beg,end)

    def __getitem__(self, name):
        #this works because all keys are coming from our search results
        #where _everything_ is unicode :)
        #return self.thread_dict[name]
        try: name.__int__
        except:
            return self.thread_dict[name]
        else:
            return self.threadList[name]
    
    def __setitem__(self, name, value):
        #self.thread_dict[name] = value
        try: name.__int__
        except:
            self.thread_dict[name] = value
        else:
            self.threadList[name] = value

    def __delitem__(self, name):
        #del self.thread_dict[name]
        try: name.__int__
        except:
            del self.thread_dict[name]
        else:
            del self.threadList[name]

    def count(self):
        return self.threadList.count()

    def reverse(self):
        return self.threadList.reverse()

    def __iter__(self):
        for msgobj in self.threadList:
            yield msgobj

    def __len__(self):
        return len(self.threadList)

    def __x_newest_msg_date(self,x):
        #return self.unidecode_date(x.messages[-1][-1]['date'])
        return getattr(x, 'last_update')

    def sort(self):
        self.threadList.sort(key=self.__x_newest_msg_date, reverse=True)
        #self.threadList.reverse()

    def dictify(self, one=False):
        def quack(key, msgobj):
            try: found = self[key]
            except: self[key] = msgobj
            else:
                if self[key] is not msgobj:
                    if self[key] not in self.duplist:
                        try:
                            global dodebug
                            if dodebug:
                                global dupcount
                                dupcount +=1
                                print 'merging preexisting threads'
                                print 'key ', key
                                print 'found ', len(self[key].messages)
                                print 'new ', len(msgobj.messages)
                                #print 'found ', self[key].messages
                                #print 'new ', msgobj.messages
                        except: pass
                        self.duplist.append(self[key])
                        self.merge(self[key], msgobj)
                        self.sumlist.extend([x for x in \
                                msgobj.msgids|msgobj.subjects \
                                if x not in self.sumlist])
                        self.threadList.remove(self[key])
                        #try: del self.thread_persist[self[key].id]
                        #except: pass
                        #del self._fcache[self[key].id]
                    self[key] = msgobj

        self.duplist = []
        if one:
            #self.sumlist = sum([one.msgids,one.subjects],[])
            self.sumlist = list(one.msgids|one.subjects)
            [quack(x, one) for x in self.sumlist]
            del self.sumlist, self.duplist
        else:
            #[self.dictify(msgobj) for msgobj in self.thread_persist]
            [self.dictify(msgobj) for msgobj in self.threadList]

    def merge(self, found, workobj):
        def fun(key):
            return [__x for __x in found[key] if __x not in workobj[key]]
        def do_insort(x):
            insort_right(workobj.messages,x)

        workobj.msgids |= found.msgids
        workobj.subjects |= found.subjects
        workobj.labels |= found.labels

        map(do_insort, fun('messages'))

    def append(self, data):
        #data['id'] = uuid4().hex
        #self._fcache[data.id] = data
        self.threadList.append(data)
        self.dictify(data)

    def extend(self, key, msgobj):
        self.merge(msgobj, self[key])
        self.dictify(self[key])

    def thread(self, messages, pre_prepped=True):
        #self._fcache = {}
        if pre_prepped:
            #__prep = [xap_container(msg) for msg in messages]
            #[self._thread(msg) for msg in __prep]
            [self._thread(xap_container(msg)) for msg in messages]
        else:
            __text_prep = (self._msg_prep(msg) for msg in messages)
            [self._thread(msg) for msg in __text_prep]

        #[self.thread_persist.put(key,data) for key,data in self._fcache.iteritems()]
        #if not pre_prepped: del __text_prep
        #del self._fcache
        #self.thread_persist.sync()
        self.sort()
        return

    def _msg_prep(self, msg):
        '''prepares all of the messages to be threaded'''

        __inreplyto = set([self.get(msg,u'in_reply_to',u'')])
        __msgid = set([self.get(msg,u'msgid')])
        __refs = set(self.split(self.get(msg,u'references',u'')))

        __msg_refs = self.deuniNone(__inreplyto|__msgid|__refs)
        __msg_subject = set([stripSubject(self.get(msg,u'subject',u''))])
        __msg_date = self.unidecode_date(self.get(msg,u'date'))
        __msg_labels = self.get(msg, u'labels', u'')

        #hate this, but it helps us avoid unnecessary processing
        if __msg_labels and __msg_labels != u'None':
            __msg_labels = self.deuniNone(split(__msg_labels))
        else: __msg_labels = []

        return convContainer( __msg_refs, __msg_subject,
                                        set(__msg_labels), [(__msg_date, msg)])

    def _thread(self, msg):
        '''does the actual threading'''
        # in case we're on the first pass...
        if not self.threadList:
            self.append(msg)
            return

        #see if the convenience dict knows of the conversation 
        #this message belongs to. We look for everything we might have
        #in common with the conversation thread: our message-id, 
        #in-reply-to header, references header, and subject
        #for convident in sum([msg.msgids,msg.subjects],[]):
        for convident in msg.msgids|msg.subjects:
            try: self[convident]
            except: pass
            else:
                #we found our conversation! extend the conversation
                #and include ourselves in it.
                self.extend(convident, msg)
                return

        #if we didn't find anything, then we're either first of
        #a new conversation, the only email in the conversation,
        #or some jackass is using an email client that doesn't
        #follow standards. whichever the case, we do the same thing: append
        self.append(msg)

    def verify_thread(self):
        for conv in self.threadList:
            for uniqident in sum([conv.msgids, conv.subjects],[]):
                found = self[uniqident]
                if found is not conv:
                    import pdb
                    pdb.set_trace()


if __name__ == '__main__':
    global dodebug
    dodebug = True
    if dodebug:
        global dupcount
        dupcount = 0
    dotime = True
    doram = True
    if dotime: import time
    if doram:
        from guppy import hpy
        hp = hpy()
    import xappy
    msgthread = lazy_thread()
    if doram: hp.setrelheap()
    xconn = xappy.IndexerConnection('xap.idx')
    r = (xconn.get_document(x).data for x in xconn.iterids())
    print 'going for broke - lets thread!'
    if dotime: t = time.time()
    msgthread.thread(r)
    print 'done threading!'
    if dodebug:
        print dupcount
    if dotime: t  = time.time() - t
    if dotime: print 'message threading took %r seconds' % t
    print len(msgthread.threadList)
    if doram:
        h = hp.heap()
        print h
        print '\n'
