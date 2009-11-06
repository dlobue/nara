'''Since I don't care about the structure of the message,
I'm not going to bother with jwz's threading algorithem,
which isn't very pythonic anyway.

structure of container:
    { 'msgids': [], 'subjects': [], 'labels': [], 'messages': [] }
'''

from tools import flatnique, deuniNone, unidecode_date
from weakref import WeakValueDictionary, ref
from bisect import insort_right
from random import seed, random
from cPickle import dumps

def stripSubject(subj):
    '''strips out all "re:"s and "fwd:"s'''
    lower = unicode.lower
    strip = unicode.strip
    _container = []
    _last = 0
    while 1:
        l = lower(subj)
        if l.startswith(u're:') or l.startswith(u'fw:'):
            subj = strip(subj[3:])
        elif l.startswith(u'fwd:'):
            subj = strip(subj[4:])
        #elif u':' in subj[_last:]:
            #rawr, fixme!
            #_container.append(subj[:subj.index(u':')])
        else:
            return subj

def splitstripSubject(subj):
    '''alternate method of removing unwanted "re:"s and "fwd:"s'''
    lower = unicode.lower
    strip = unicode.strip
    split = unicode.split
    startswith = unicode.startswith
    
    def striplower(l):
        return strip(lower(l))
    
    def filterfunc(bit):
        if len(bit) <= 3:
            b = striplower(bit)
            if startswith(b, 're') or startswith(b, 'fw'):
                return
        return bit

    subj = split(subj, u':')
    subj = filter(filterfunc,subj)
    return [u':'.join(subj)]

class convContainer(dict):
    def __init__(self, msgids, subjects, labels, messages):
        self['msgids'] = msgids
        self['subjects'] = subjects
        self['messages'] = messages
        self['labels'] = labels
        
        #becuse attributes are fun
        self.msgids = self['msgids']
        self.subjects = self['subjects']
        self.messages = self['messages']
        self.labels = self['labels']

    @property
    def id(self):
        return self['id']

    @property
    def last_update(self):
        return self['messages'][-1][0]

    def _always_fresh(self):
        #return self['messages'][-1][0]
        return self.last_update

    def always_fresh(self):
        return always_fresh(self)

    def listing(self):
        return ref(List([self.always_fresh(), self.id]))

    def __repr__(self):
        __ddate = self['messages'][-1][-1]['date']
        __dsender = u','.join([x[-1]['sender'].split()[0].strip('"') for x in self['messages'][-3:]])
        __dcontained = len(self['messages'])
        __dsubject = stripSubject(self['messages'][-1][-1].get(u'subject',u''))
        __dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        __dpreview = u' '.join(self['messages'][-1][-1].get(u'content',u'').splitlines())
        __disprender = u"%s\t%s\t%i\t%s %s %s" % \
            (__ddate, __dsender, __dcontained, __dsubject, __dlabels, __dpreview)
        return __disprender

class List(list): pass
class always_fresh(object):
    def __init__(self, parent):
        self.parent = parent._always_fresh
    def __repr__(self):
        return str(self.parent())
    def __cmp__(self, other):
        return cmp(self.parent(), other)

class sorted_tuple_dict(WeakValueDictionary):
    _list = []

    def __getslice__(self, beg, end): return self._list.__getslice__(beg,end)
    def sort(self, *args, **kwargs): self._list.sort(*args, **kwargs)
    def reverse(self): self._list.reverse()
    def count(self): return self._list.count()
    def __len__(self): return len(self._list)
    def __iter__(self): return (item for item in self._list)

    def append(self, data):
        self[data[-1]] = data[0]
        #self._list.append(kkkkkkkkk)
        #insort_right(self._list, data)

    def extend(self, datalist):
        [self.append(data) for data in datalist]
       
class lazy_thread(object):
    def __init__(self):
        #this is where all the good stuff is stored
        self.threadList = []
        self.thread_dict = WeakValueDictionary()
        self.thread_persist = {}
        #self.thread_dict = {}

        #because calling a function once is faster
        #than calling it 9000 times.
        self.get = dict.get
        self.split = unicode.split

    def __getslice__(self, beg, end):
        return self.threadList.__getslice__(beg,end)

    def __getitem__(self, name):
        #this works because all keys are coming from our search results
        #where _everything_ is unicode :)
        try: name.__int__
        except:
            return self.thread_dict[name]
        else:
            return self.threadList[name]
    
    def __setitem__(self, name, value):
        try: name.__int__
        except:
            self.thread_dict[name] = value
        else:
            self.threadList[name] = value

    def __delitem__(self, name):
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

    def __x_msgid(self,x):
        return x['msgid']

    def __x_newest_msg_date(self,x):
        #return x['messages'][-1]['date']
        return unidecode_date(x['messages'][-1]['date'])

    def sort(self):
        #[msgobj['messages'].sort(key=self.__x_date) for msgobj in self.threadList]
        #self.threadList.sort(key=self.__x_newest_msg_date)
        self.threadList.sort()
        self.threadList.reverse()

    def dictify(self, one=False):
        def quack(key, msgobj):
            try: found = self[key]
            except: self[key] = msgobj
            else:
                if self[key] is not msgobj:
                    if self[key] not in self.duplist:
                        self.duplist.append(self[key])
                        self.merge(self[key], msgobj)
                        self.sumlist.extend([x for x in \
                                sum([msgobj['msgids'],msgobj['subjects']],[]) \
                                if x not in self.sumlist])
                        del self.thread_persist[self[key].id]
                    self[key] = msgobj

        self.duplist = []
        if one:
            self.sumlist = sum([one['msgids'],one['subjects']],[])
            [quack(x, one) for x in self.sumlist]
            del self.sumlist, self.duplist
        else:
            [self.dictify(msgobj) for msgobj in self.threadList]

    def merge(self, found, workobj):
        def fun(key):
            return [__x for __x in found[key] if __x not in workobj[key]]

        def do_insort(x):
            insort_right(workobj['messages'],x)

        workobj['msgids'].extend(fun('msgids'))
        workobj['subjects'].extend(fun('subjects'))
        workobj['labels'].extend(fun('labels'))
        #workobj['messages'].extend(fun('messages'))
        map(do_insort, fun('messages'))
        '''for blarg in self.threadList:
            if workobj['id'] == blarg[-1]:
                print blarg[-1], blarg[0], workobj.last_update
                break
                '''
        #if [workobj.last_update, workobj['id']] not in self.threadList:
            #print 'fuuuuuuuuuck', workobj.last_update, workobj['id']

    def append(self, data):
        data['id'] = hex(hash(dumps(data)))
        self.thread_persist[data.id] = data
        #self.threadList.append(tuple([always_fresh(data), data['id']]))
        self.threadList.append(data.listing())
        self.dictify(data)

    def extend(self, key, msgobj):
        self.merge(msgobj, self[key])
        self.dictify(self[key])

    def thread(self, messages):
        __text_prep = [self._msg_prep(msg) for msg in messages]
        [self._thread(msg) for msg in __text_prep]
        del __text_prep

        #self.sort()
        return

    def _msg_prep(self, msg):
        '''prepares all of the messages to be threaded'''

        __inreplyto = self.get(msg,u'in_reply_to',u'')
        __msgid = self.get(msg,u'msgid')
        #__refs = self.split(self.get(msg,u'references',u''))
        __refs = self.get(msg,u'references',u'')

        if u' ' in __refs: __refs = self.split(__refs)
        else: __refs = [__refs]

        __msg_refs = [[__inreplyto],[__msgid],__refs]

        '''self.msg_refs = [[self.get(msg,u'in_reply_to',u'')],
                        [self.get(msg,u'msgid')],
                        self.split(self.get(msg,u'references',u''))]
                        '''

        #next flattens, unique-ifys, and removes unicode None's
        __msg_refs = deuniNone(flatnique(__msg_refs))
        __msg_msgid = self.get(msg,u'msgid')
        __msg_labels = self.get(msg, u'labels', u'')
        __msg_date = unidecode_date(self.get(msg, u'date'))
        #msg_subject = [stripSubject(self.get(msg,u'subject',u''))]
        __msg_subject = stripSubject(self.get(msg,u'subject',u''))
        #msg_subject = splitstripSubject(self.get(msg,u'subject',u''))

        #hate this, but it helps us avoid unnecessary processing
        if __msg_labels and __msg_labels != u'None':
            __msg_labels = deuniNone(self.split(__msg_labels))
        else: __msg_labels = []
        if u':' in __msg_subject: __msg_subject = splitstripSubject(__msg_subject)
        else: __msg_subject = [__msg_subject]

        __loop_msgobj=convContainer(__msg_refs, __msg_subject,
                                    __msg_labels, [(__msg_date, msg)])

        return __loop_msgobj

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
        for __convident in sum([msg.msgids,msg.subjects],[]):
            try: self[__convident]
            except: pass
            else:
                #we found our conversation! extend the conversation
                #and include ourselves in it.
                self.extend(__convident, msg)
                return

        #if we didn't find anything, then we're either first of
        #a new conversation, the only email in the conversation,
        #or some jackass is using an email client that doesn't
        #follow standards. whichever the case, we do the same thing: append
        #oh, or we're not being given messages in the order that they were sent
        self.append(msg)

    def verify_thread(self):
        for conv in self.threadList:
            for uniqident in sum([conv['msgids'], conv['subjects']],[]):
                found = self[uniqident]
                if found is not conv:
                    import pdb
                    pdb.set_trace()
