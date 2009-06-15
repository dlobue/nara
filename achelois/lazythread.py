'''Since I don't care about the structure of the message,
I'm not going to bother with jwz's threading algorithem,
which isn't very pythonic anyway.

structure of container:
    { 'msgids': [], 'subjects': [], 'messages': [] }
'''

import pdb
import tools
from weakref import WeakValueDictionary

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

    def __repr__(self):
        self.ddate = self['messages'][0]['date']
        self.dsender = u','.join([x['sender'].split()[0] for x in self['messages'][:3]])
        self.dcontained = len(self['messages'])
        self.dsubject = stripSubject(self['messages'][0]['subject'])
        self.dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        self.dpreview = self['messages'][0]['content']
        self.disprender = "\t%s\t%s\t%i\t%s %s %s" % \
            (self.ddate, self.dsender, self.dcontained, self.dsubject, self.dlabels, self.dpreview)
        return self.disprender

class Thread(WeakValueDictionary):
    def __init__(self):
        self.threadList = []

        self.__getslice__ = self.threadList.__getslice__
        self.__setslice__ = self.threadList.__setslice__
        self.__len__ = self.threadList.__len__
        self.count = self.threadList.count
        self.reverse = self.threadList.reverse

    def __iter__(self):
        for msgobj in self.thread:
            yield msgobj

    def sort(self):
        [msgobj['messages'].sort(key=lambda x: x['date']) for msgobj in self.threadList]
        self.threadList.sort(key=lambda x: x['messages'][0]['date'])

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
                    if lookingglass: pass
                    else:
                        lookingglass = True
                        self.merge(self[key], msgobj)
                    self[key] = msgobj

        lookingglass = False
        if one:
            '''for msgid in sum([one['msgids'],one['subjects']],[]):
                quack(x, one)
                '''
            [quack(x, one) for x in sum([one['msgids'],one['subjects']],[])]
        else:
            [quack(x, msgobj) for msgobj in self.threadList for x in \
                        sum([msgobj['msgids'],msgobj['subjects']],[])]

    def append(self, data):
        self.threadList.append(data)
        self.dictify(data)

    def extend(self, key, msgobj):
        index = self.threadList.index(self[key])
        self.threadList[index]['msgids'] = list(set(sum(
                [self.threadList[index]['msgids'],msgobj['msgids']],[])))
        self.threadList[index]['subjects'] = list(set(sum(
                [self.threadList[index]['subjects'],msgobj['subjects']],[])))
        self.threadList[index]['messages'].extend(msgobj['messages'])
        self.dictify(self.threadList[index])

    @property
    def msgid_list(self):
        return map(lambda x: x['msgids'], self.threadList)

    def thread(self, messages):
        split = unicode.split
        get = dict.get
        deuniNone = tools.deuniNone
    
        for self.msg in messages:
            self.msg_refs = [[get(self.msg,u'in_reply_to',u'')],
                            [get(self.msg,u'msgid')],
                            split(get(self.msg,u'references',u''))]
            self.msg_refs = deuniNone(list(set(sum(self.msg_refs,[])))) #flatten and unique-ify
            self.msg_msgid = get(self.msg,u'msgid',u'')
            self.msg_subject = [stripSubject(get(self.msg,u'subject',u''))]
            self.msg_labels = get(self.msg, u'labels', None)

            if self.msg_labels:
                self.msg_labels = deuniNone(split(self.msg_labels))
    
            self.loop_msgobj=convContainer(self.msg_refs, self.msg_subject,
                                                self.msg_labels, [self.msg])
            '''self.loop_msgobj={'msgids': self.msg_refs,
                        'subjects': self.msg_subject,
                        'messages': [self.msg]}
                        '''


            # in case we're the first...
            if not self.threadList:
                self.append(self.loop_msgobj)
                continue

            self.threadFound=False
            for uniqident in sum([self.msg_refs,self.msg_subject],[]):
                try: self[uniqident]
                except: pass
                else:
                    self.extend(uniqident, self.loop_msgobj)
                    self.threadFound = True
                    break

            if not self.threadFound:
                self.append(self.loop_msgobj)

        return self.threadList

    def uniq_thread(self, umsgobj, ifnotuniq):
        for uniqdent in sum([umsgobj['msgids'], umsgobj['subjects']],[]):
            try: self[uniqdent]
            except: pass
            else: ifnotuniq

    def merge(self, found, new):
        gindex = self.threadList.index(found)
        bindex = self.threadList.index(interloper)

        #merge the two conversations
        self.threadList[gindex]['msgids'] = flatnique([conv['msgids'],self.found['msgids']])
        self.threadList[gindex]['subjects'] = flatnique([conv['subjects'],self.found['subjects']])
        self.threadlist[gindex]['messages'].extend(self.found['messages'])

    def squish(self):
        flatnique = tools.flatnique
        for conv in self.threadList:
            for uniqident in sum([conv['msgids'], conv['subjects']],[]):
                self.found = self[uniqident]
                if self.found is not conv:
                    gindex = self.threadList.index(conv)
                    bindex = self.threadList.index(self.found)
                    
                    #merge the two conversations
                    self.threadList[gindex]['msgids'] = flatnique([conv['msgids'],self.found['msgids']])
                    self.threadList[gindex]['subjects'] = flatnique([conv['subjects'],self.found['subjects']])
                    self.threadlist[gindex]['messages'].extend(self.found['messages'])

    def verify_thread(self):
        for conv in self.threadList:
            for uniqident in sum([conv['msgids'], conv['subjects']],[]):
                self.found = self[uniqident]
                if self.found is not conv:
                    pdb.set_trace()
