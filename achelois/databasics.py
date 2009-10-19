#!/usr/bin/python

from collections import deque, namedtuple
from xappy.datastructures import ProcessedDocument


msg_container = namedtuple('msg_container', ['sender', 'to', 'cc', 'subject', 'osubject', 'msgid', 'muuid', 'flags', 'labels', 'sent', 'mtime', 'in_reply_to', 'references', 'sample', 'thread']
conv_cont = namedtuple('conv_container', ['msgids', 'subjects', 'labels', 'thread', 'messages'])

class conv_container(conv_cont):
	__slots__ = ()
	last_update = _property(_itemgetter(4)[-1].sent)
	def merge(self, msg_cntr):
		tomerge = ('msgids', 'subjects', 'labels')
		def minsort(x):
			return [__x for __x in getattr(msg_cntr, x), if __x not in getattr(self, x)]
		def domerge(x):
			getattr(self, x).extend(minsort(x))
		def do_insort(x):
			insort_right(msg_cntr.messages, x)
		map(domerge, tomerge)
		map(do_insort, minsort('messages'))

class prop_deque(deque):
	__slots__ = ()
	def __repr__(self):
		if self.__len__() == 1: return self[0]
		else: return deque.__repr__(self)

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



def msg_factory(data):
    __data, __muuid = data

    field_dict = {'sender': 'to', 'msgid': 'message-id'}
    #field_multis = ('cc', 'to', 'flags', 'labels', 'references')
    field_multis = {'cc':',', 'to':',', 'flags':None, 'labels':None, 'references':None)
    def do_get(msg, field):
        def do_multi(data, field):
            try: __x = deuniNone(set(data.split(field_multis[field])))
            except: __x = data
            return [__i.strip() for __i in __x]
        __data = msg.get(field_dict.get(field, field), [])
        try: msg.get_flags
        except: pass #TODO: pass, or return?
        else:
            if field in field_multis:
                if field == 'flags': __data = [x for x in msg.get_flags()]
                __data = do_multi(__data, field)
        return prop_deque(__data)


