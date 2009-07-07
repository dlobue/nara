'''Since I don't care about the structure of the message,
I'm not going to bother with jwz's threading algorithem,
which isn't very pythonic anyway.

structure of container:
    { 'msgids': [], 'subjects': [], 'messages': [] }
'''

#import tools
from tools import flatnique, deuniNone, unidecode_date
import time
from weakref import WeakValueDictionary

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


def asciisplitstripSubject(subj):
    '''alternate method of removing unwanted "re:"s and "fwd:"s'''
    lower = str.lower
    strip = str.strip
    split = str.split
    startswith = str.startswith
    subj = str(subj)

    def striplower(l):
        return strip(lower(l))

    def minifunc(bit):
        if len(bit) <= 3:
            b = striplower(bit)
            if startswith(b, 're') or startswith(b, 'fw'):
                return
        return bit
    #subj = subj.split(':')
    subj = split(subj, ':')
    subj = filter(minifunc,subj)
    #return [minifunc(x) for x in subj if x]
    return deuniNone(map(strip,subj))

def splitstripSubject(subj):
    '''alternate method of removing unwanted "re:"s and "fwd:"s'''
    lower = unicode.lower
    strip = unicode.strip
    split = unicode.split
    startswith = unicode.startswith

    def striplower(l):
        return strip(lower(l))

    def minifunc(bit):
        if len(bit) <= 3:
            b = striplower(bit)
            if startswith(b, 're') or startswith(b, 'fw'):
                return
        return bit
    #subj = subj.split(':')
    subj = split(subj, u':')
    subj = filter(minifunc,subj)
    #return [minifunc(x) for x in subj if x]
    return deuniNone(map(strip,subj))

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
        ddate = self['messages'][-1]['date']
        dsender = u','.join([x['sender'].split()[0].strip('"') for x in self['messages'][-3:]])
        dcontained = len(self['messages'])
        dsubject = stripSubject(self['messages'][-1].get(u'subject',u''))
        dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        dpreview = u' '.join(self['messages'][-1].get(u'content',u'').split())
        disprender = u"%s\t%s\t%i\t%s %s %s" % \
            (ddate, dsender, dcontained, dsubject, dlabels, dpreview)
        return disprender

class lazy_thread(object):
    def __init__(self):
        #this is where all the good stuff is stored
        self.threadList = []
        self.thread_dict = WeakValueDictionary()
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

    def __x_date(self,x):
        #return x['date']
        return unidecode_date(x['date'])

    def __x_newest_msg_date(self,x):
        #return x['messages'][-1]['date']
        return unidecode_date(x['messages'][-1]['date'])

    def sort(self):
        [msgobj['messages'].sort(key=self.__x_date) for msgobj in self.threadList]
        self.threadList.sort(key=self.__x_newest_msg_date)
        self.threadList.reverse()

    '''
    @property
    def msgid_list(self):
        return map(self.__x_msgid, self.threadList)

    def by_msgid(self, key):
        return [msgobj for msgobj in self.thread \
                    if key in msgobj['msgids']]

    def by_subject(self, key):
        return [msgobj for msgobj in self.thread \
                    if key in msgobj['subjects']]
        '''

    def dictify(self, one=False):
        def quack(key, msgobj):
            try: found = self[key]
            except: self[key] = msgobj
            else:
                if self[key] is not msgobj:
                    if self[key] not in self.duplist:
                        self.duplist.append(self[key])
                        self.merge(self[key], msgobj)
                        self.sumlist.extend([x for x in sum([msgobj['msgids'],msgobj['subjects']],[]) \
                                            if x not in self.sumlist])
                        self.threadList.remove(self[key])
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
            return [x for x in found[key] if x not in workobj[key]]

        workobj['msgids'].extend(fun('msgids'))
        workobj['subjects'].extend(fun('subjects'))
        workobj['labels'].extend(fun('labels'))
        workobj['messages'].extend(fun('messages'))

    def append(self, data):
        self.threadList.append(data)
        self.dictify(data)

    def extend(self, key, msgobj):
        self.merge(msgobj, self[key])
        self.dictify(self[key])

    def thread(self, messages):
        #self._text_prep = []
        #t = time.time()
        _text_prep = [self._msg_prep(msg) for msg in messages]
        [self._thread(msg) for msg in _text_prep]
        #[self._thread(msg) for msg in self._text_prep]
        #t = time.time() - t
        #print 'message threading took %r seconds' % t

        self.sort()
        return

    def _msg_prep(self, msg):
        '''prepares all of the messages to be threaded'''

        __inreplyto = self.get(msg,u'in_reply_to',u'')
        __msgid = self.get(msg,u'msgid')
        __refs = self.split(self.get(msg,u'references',u''))
        msg_refs = [[__inreplyto],[__msgid],__refs]

        '''self.msg_refs = [[self.get(msg,u'in_reply_to',u'')],
                        [self.get(msg,u'msgid')],
                        self.split(self.get(msg,u'references',u''))]
                        '''

        #next flattens, unique-ifys, and removes unicode None's
        msg_refs = deuniNone(flatnique(msg_refs))
        msg_msgid = self.get(msg,u'msgid',u'')
        #msg_subject = [stripSubject(self.get(msg,u'subject',u''))]
        msg_subject = stripSubject(self.get(msg,u'subject',u''))
        #msg_subject = splitstripSubject(self.get(msg,u'subject',u''))
        #msg_subject = asciisplitstripSubject(self.get(msg,u'subject',u''))
        msg_labels = self.get(msg, u'labels', u'')

        #hate this, but it helps us avoid unnecessary processing
        if msg_labels and msg_labels != u'None':
            msg_labels = deuniNone(self.split(msg_labels))
        else: msg_labels = []
        if u':' in msg_subject: msg_subject = splitstripSubject(msg_subject)
        else: msg_subject = [msg_subject]

        loop_msgobj=convContainer(msg_refs, msg_subject,
                                    msg_labels, [msg])

        return loop_msgobj
        #self._text_prep.append(loop_msgobj)

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
        for convident in sum([msg.msgids,msg.subjects],[]):
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
