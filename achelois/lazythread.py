'''Since I don't care about the structure of the message,
I'm not going to bother with jwz's threading algorithem,
which isn't very pythonic anyway.

structure of container:
    { 'msgids': [], 'subjects': [], 'messages': [] }
'''

from tools import deuniNone, unidecode_date
from bisect import insort_right

def stripSubject(subj):
    '''strips out all "re:"s and "fwd:"s'''
    __lower = unicode.lower
    __strip = unicode.strip
    while 1:
        l = __lower(subj)
        if l.startswith(u're:') or l.startswith(u'fw:'):
            subj = __strip(subj[3:])
        elif l.startswith(u'fwd:'):
            subj = __strip(subj[4:])
        else:
            return subj

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

    def __repr__(self):
        __ddate = self['messages'][-1][-1]['date']
        __dsender = u','.join([x[-1]['sender'].split()[0].strip('"') for x in self['messages'][-3:]])
        __dcontained = len(self['messages'])
        __dsubject = stripSubject(self['messages'][-1][-1].get(u'subject',u''))
        __dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        __dpreview = u' '.join(self['messages'][-1][-1].get(u'content',u'').split())
        __disprender = u"%s\t%s\t%i\t%s %s %s" % \
            (__ddate, __dsender, __dcontained, __dsubject, __dlabels, __dpreview)
        return __disprender

class lazy_thread(object):
    def __init__(self):
        #this is where all the good stuff is stored
        self.threadList = []
        self.thread_dict = {}

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

    def __x_date(self,x):
        #return x['date']
        return self.unidecode_date(x['date'])

    def __x_newest_msg_date(self,x):
        #return x['messages'][-1]['date']
        return self.unidecode_date(x['messages'][-1][-1]['date'])

    def sort(self):
        #[msgobj['messages'].sort(key=self.__x_date) for msgobj in self.threadList]
        self.threadList.sort(key=self.__x_newest_msg_date)
        self.threadList.reverse()

    @property
    def msgid_list(self):
        return map(self.__x_msgid, self.threadList)

    def by_msgid(self, key):
        return [msgobj for msgobj in self.thread \
                    if key in msgobj['msgids']]

    def by_subject(self, key):
        return [msgobj for msgobj in self.thread \
                    if key in msgobj['subjects']]

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
                                msgobj['msgids']|msgobj['subjects'] \
                                if x not in self.sumlist])
                        self.threadList.remove(self[key])
                    self[key] = msgobj

        self.duplist = []
        if one:
            #self.sumlist = sum([one['msgids'],one['subjects']],[])
            self.sumlist = list(one['msgids']|one['subjects'])
            [quack(x, one) for x in self.sumlist]
            del self.sumlist, self.duplist
        else:
            [self.dictify(msgobj) for msgobj in self.threadList]

    def merge(self, found, workobj):
        def fun(key):
            return [__x for __x in found[key] if __x not in workobj[key]]
        def do_insort(x):
            insort_right(workobj['messages'],x)

        #workobj['msgids'].extend([x for x in found['msgids'] if x not in workobj['msgids']])
        #workobj['subjects'].extend([x for x in found['subjects'] if x not in workobj['subjects']])
        #workobj['labels'].extend([x for x in found['labels'] if x not in workobj['labels']])
        #workobj['messages'].extend(found['messages'])

        #workobj['msgids'].extend(fun('msgids'))
        #workobj['subjects'].extend(fun('subjects'))
        #workobj['labels'].extend(fun('labels'))

        workobj['msgids'] |= found['msgids']
        workobj['subjects'] |= found['subjects']
        workobj['labels'] |= found['labels']

        #workobj['messages'].extend(fun('messages'))
        map(do_insort, fun('messages'))

    def append(self, data):
        self.threadList.append(data)
        self.dictify(data)

    def extend(self, key, msgobj):
        self.merge(msgobj, self[key])
        self.dictify(self[key])

    def thread(self, messages):
        __text_prep = (self._msg_prep(msg) for msg in messages)
        [self._thread(msg) for msg in __text_prep]

        self.sort()
        return

    def _msg_prep(self, msg):
        '''prepares all of the messages to be threaded'''

        __inreplyto = set([self.get(msg,u'in_reply_to',u'')])
        __msgid = set([self.get(msg,u'msgid')])
        __refs = set(self.split(self.get(msg,u'references',u'')))
        #__inreplyto = self.get(msg,u'in_reply_to',u'')
        #__msgid = self.get(msg,u'msgid')
        #__refs = self.split(self.get(msg,u'references',u''))
        #__inreplyto = msg.get(u'in_reply_to',u'')
        #__msgid = msg.get(u'msgid')
        #__refs = self.split(msg.get(u'references',u''))
        #__refs = self.get(msg,u'references',u'')
        #if u' ' in __refs: __refs = self.split(__refs)
        #else: __refs = [__refs]

        #__msg_refs = [[__inreplyto],[__msgid],__refs]

        '''self.msg_refs = [[self.get(msg,u'in_reply_to',u'')],
                        [self.get(msg,u'msgid')],
                        self.split(self.get(msg,u'references',u''))]
                        '''

        #next flattens, unique-ifys, and removes unicode None's
        #__msg_refs = deuniNone(flatnique(__msg_refs))
        __msg_refs = self.deuniNone(__inreplyto|__msgid|__refs)
        __msg_subject = set([stripSubject(self.get(msg,u'subject',u''))])
        #__msg_labels = msg.get( u'labels', u'')
        __msg_date = self.unidecode_date(self.get(msg,u'date'))
        __msg_labels = self.get(msg, u'labels', u'')

        #hate this, but it helps us avoid unnecessary processing
        if __msg_labels and __msg_labels != u'None':
            __msg_labels = self.deuniNone(split(__msg_labels))
        else: __msg_labels = []

        return convContainer( __msg_refs, __msg_subject,
                                        set(__msg_labels), [(__msg_date, msg)])
        #return __loop_msgobj

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
            for uniqident in sum([conv['msgids'], conv['subjects']],[]):
                found = self[uniqident]
                if found is not conv:
                    import pdb
                    pdb.set_trace()
