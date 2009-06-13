'''Since I don't care about the structure of the message,
I'm not going to bother with jwz's threading algorithem,
which isn't very pythonic anyway.

structure of container:
    { 'msgids': [], 'subjects': [], 'messages': [] }
'''


def stripSubject(subj):
    '''strips out all "re:"s and "fwd:"s'''
    lower = unicode.lower
    strip = unicode.strip
    while 1:
        l = lower(subj)
        if l.startswith('re:'):
            subj = strip(subj[3:])
        elif l.startswith('fwd:'):
            subj = strip(subj[4:])
        else:
            return subj

class Thread(dict):
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

    '''def __repr__(self):
        return self.thread
        '''

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
            try: self[key]
            except: self[key] = msgobj
            else: pass
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
    
        for self.msg in messages:
            self.msg_refs = [[get(self.msg,'in_reply_to',u'')],
                            [get(self.msg,'msgid')],
                            split(get(self.msg,'references',u''))]
            self.msg_refs = list(set(sum(self.msg_refs,[]))) #flatten and unique-ify
            #self.msg_refs = [ref for ref in self.msg_refs if ref and not u'None'] #remove any null values
            try: self.msg_refs.remove(u'None')
            except: pass
            self.msg_msgid = get(self.msg,'msgid',u'')
            self.msg_subject = [stripSubject(get(self.msg,'subject',u''))]
    
            self.loop_msgobj={'msgids': self.msg_refs,
                        'subjects': self.msg_subject,
                        'messages': [self.msg]}


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
