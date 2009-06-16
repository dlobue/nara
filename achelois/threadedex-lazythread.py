'''Since I don't care about the structure of the message,
I'm not going to bother with jwz's threading algorithem,
which isn't very pythonic anyway.

structure of container:
    { 'msgids': [], 'subjects': [], 'messages': [] }
'''

import tools
import threading
import time

def stripSubject(subj):
    '''strips out all "re:"s and "fwd:"s'''
    lower = unicode.lower
    strip = unicode.strip
    while 1:
        l = lower(subj)
        if l.startswith(u're:') or l.startswith(u'fw:'):
            subj = strip(subj[3:])
        elif l.startswith(u'fwd:'):
            subj = strip(subj[4:])
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
        self.ddate = self['messages'][-1]['date']
        self.dsender = u','.join([x['sender'].split()[0].strip('"') for x in self['messages'][:3]])
        self.dcontained = len(self['messages'])
        self.dsubject = stripSubject(self['messages'][0].get(u'subject',u''))
        self.dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        self.dpreview = u' '.join(self['messages'][0].get(u'content',u'').split())[:30]
        self.disprender = "\t%s\t%s\t%i\t%s %s %s" % \
            (self.ddate, self.dsender, self.dcontained, self.dsubject, self.dlabels, self.dpreview)
        return self.disprender

class lazy_thread(dict):
    def __init__(self):
        #this is where all the good stuff is stored
        self.threadList = []

        #Thread is a dict only as a convenience object
        #and because list has less methods to copy over than
        #a dict would ;)
        self.__getslice__ = self.threadList.__getslice__
        self.__setslice__ = self.threadList.__setslice__
        self.__len__ = self.threadList.__len__
        self.__iter__ = self.threadList.__len__
        self.count = self.threadList.count
        self.reverse = self.threadList.reverse

        #because calling a function once is faster
        #than calling it 9000 times.
        self.get = dict.get
        self.split = unicode.split
        self.deuniNone = tools.deuniNone
        self.flatnique = tools.flatnique

        self._pthread = threading.Thread

    '''def __iter__(self):
        for msgobj in self.threadList:
            yield msgobj
            '''

    def __x_msgid(self,x):
        return x['msgid']

    def __x_date(self,x):
        return x['date']

    def __x_newest_msg_date(self,x):
        return x['messages'][-1]['date']

    def sort(self):
        [msgobj['messages'].sort(key=self.__x_date) for msgobj in self.threadList]
        self.threadList.sort(key=self.__x_newest_msg_date)

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
            #FIXME: duplist will not function properly if we do a
            #general dictify - there's no sumlist var I can extend!
            #think of way to fix this
            [quack(x, msgobj) for msgobj in self.threadList for x in \
                        sum([msgobj['msgids'],msgobj['subjects']],[])]

    def merge(self, found, workobj):
        workobj['msgids'].extend([x for x in found['msgids'] if x not in workobj['msgids']])
        workobj['subjects'].extend([x for x in found['subjects'] if x not in workobj['subjects']])
        workobj['labels'].extend([x for x in found['labels'] if x not in workobj['labels']])
        workobj['messages'].extend(found['messages'])

    def append(self, data):
        self.threadList.append(data)
        self.dictify(data)

    def extend(self, key, msgobj):
        self.merge(msgobj, self[key])
        self.dictify(self[key])

    def _init_thread(self, msg_chunk):
        __current = self._pthread(target=self._msg_prep_chunk, args=(msg_chunk,))
        self._text_threadlist.append(__current)
        __current.start()
    
    def _msg_prep_chunk(self, chunk):
        [self._msg_prep(msg) for msg in chunk]

    def thread(self, messages):
        self._text_prep = []
        t = time.time()
        [self._msg_prep(msg) for msg in messages]
        t = time.time() - t
        print 'non-threaded message processing took %r seconds' % t

        def chunk_get(n):
            return messages[__c_size*n:__c_size*(n+1)]

        self._text_prep = []
        self._text_threadlist = []

        #I don't know why, but _msg_prep runs faster in its own thread
        #the bigger the chunks the faster it goes. 
        #keeping it in the main thread causes the method to more than 
        #doubles the time needed to process. whatever.
        __c_size=9000
        __msg_len = len(messages)
        if __msg_len % __c_size: __r = 1
        else: __r = 0
        __r_tot = __msg_len/__c_size+__r

        __chunk_state = (chunk_get(n) for n in xrange(__r_tot))
        t = time.time()
        [self._init_thread(msg_chunk) for msg_chunk in __chunk_state]
        [__thegoods.join() for __thegoods in self._text_threadlist]
        t = time.time() - t
        print 'threaded message processing took %r seconds' % t

        t = time.time()
        [self._thread(msg) for msg in self._text_prep]
        t = time.time() - t
        print 'message threading took %r seconds' % t

        self.sort()
        return

    def _msg_prep(self, msg):
        '''prepares all of the messages to be threaded'''

        __inreplyto = self.get(msg,u'in_reply_to',u'')
        __msgid = self.get(msg,u'msgid')
        __refs = self.split(self.get(msg,u'references',u''))
        self.msg_refs = [[__inreplyto],[__msgid],__refs]

        '''self.msg_refs = [[self.get(msg,u'in_reply_to',u'')],
                        [self.get(msg,u'msgid')],
                        self.split(self.get(msg,u'references',u''))]
                        '''

        #next flattens, unique-ifys, and removes unicode None's
        self.msg_refs = self.deuniNone(self.flatnique(self.msg_refs))
        self.msg_msgid = self.get(msg,u'msgid',u'')
        self.msg_subject = [stripSubject(self.get(msg,u'subject',u''))]
        self.msg_labels = self.get(msg, u'labels', u'')

        #hate this, but it helps us avoid unnecessary processing
        if self.msg_labels and self.msg_labels != u'None':
            self.msg_labels = deuniNone(split(self.msg_labels))
        else: self.msg_labels = []

        self.loop_msgobj=convContainer(self.msg_refs, self.msg_subject,
                                            self.msg_labels, [msg])
        self._text_prep.append(self.loop_msgobj)

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
