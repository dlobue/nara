#!/usr/bin/python

#observer pattern.. i think
from overwatch import mail_grab

#system modules
from collections import deque, namedtuple
from operator import attrgetter
from weakref import WeakValueDictionary
from bisect import insort_right
from datetime import datetime
from email.utils import parsedate
from uuid import uuid4

import pdb

#other modules i need that aren't sys, and I didn't write
from xappy.datastructures import ProcessedDocument
import threadmap
import forkmap

#lastly my tools
from tools import unidecode_date, delNone, filterNone
from lib.metautil import MetaSuper
#from offlinemaildir import mail_sources

#mail_grab = mail_sources()

msg_fields = ('sender', 'to', 'cc', 'subject', 'osubject', 'msgid', 'muuid', 'flags', 'labels', 'sent', 'mtime', 'in_reply_to', 'references', 'sample', 'thread')
conv_fields = ('msgids', 'subjects', 'labels', 'thread', 'messages')

_msg_container = namedtuple('msg_container', msg_fields)
_conv_container = namedtuple('conv_container', conv_fields)

#class msg_container(_msg_container):
class msg_container(object):
    __slots__ = ('__weakref__', '_container')

    def __init__(self, *msgargs):
        self._container = _msg_container(*msgargs)

    def __getattr__(self, name):
        return getattr(self._container, name)

    def __cmp__(self, y):
        return cmp(self.sent, y)

    def get(self, key, alt=None):
        try: return getattr(self, key)
        except AttributeError:
            print "couldn't find attribute %s, wtf?" % key
            return alt

#class conv_container(_conv_container):
class conv_container(object):
    __slots__ = ('__weakref__', 'msgids', 'subjects', 'labels', 'thread', 'messages')

    def __init__(self, msgids, subjects, labels, thread, messages):
        self.msgids = msgids
        self.subjects = subjects
        self.labels = labels
        self.thread = thread
        self.messages = messages

    #def __getattr__(self, name):
        #return getattr(self._container, name)

    @property
    def last_update(self):
        return self.messages[-1].sent

    def get(self, key, alt=None):
        try: return getattr(self, key)
        except AttributeError:
            print "couldn't find attribute %s, wtf?" % key
            return alt

    def merge(self, msg_cntr):
        tomerge = ('msgids', 'subjects', 'labels')
	def minsort(x):
	    return [ __x for __x in getattr(msg_cntr, x) if __x not in getattr(self, x)]
	def domerge(x):
	    getattr(self, x).update(getattr(msg_cntr, x))
	def do_insort(x):
	    insort_right(self.messages, x)
	threadmap.map(domerge, tomerge)
	threadmap.map(do_insort, minsort('messages'))

class conv_container_orig(object):
    __slots__ = ('__weakref__', '_container')

    def __init__(self, *convargs):
        self._container = _conv_container(*convargs)

    def __getattr__(self, name):
        return getattr(self._container, name)

    @property
    def last_update(self):
        return self.messages[-1].sent

    def get(self, key, alt=None):
        try: return getattr(self, key)
        except AttributeError:
            print "couldn't find attribute %s, wtf?" % key
            return alt

    def merge(self, msg_cntr):
        tomerge = ('msgids', 'subjects', 'labels')
	def minsort(x):
	    return [ __x for __x in getattr(msg_cntr, x) if __x not in getattr(self, x)]
	def domerge(x):
	    getattr(self, x).update(getattr(msg_cntr, x))
	def do_insort(x):
	    insort_right(msg_cntr.messages, x)
	map(domerge, tomerge)
	map(do_insort, minsort('messages'))

class thread_container(list):
    __slots__ = ('__weakref__')
    __metaclass__ = MetaSuper
    #_map = {}
    _map = WeakValueDictionary()
    def datesort(self):
        self.sort(key=attrgetter('last_update'), reverse=True)
    def __getitem__(self, idx):
        try: idx.__int__
        except: return self._map[idx]
        else: return self[idx]
    def __setitem__(self, idx, value):
        try: idx.__int__
        except: return self._map.setdefault(idx, value)
        else: return list.__setitem__(self, idx, value)
    def __delitem__(self, idx):
        try: idx.__int__
        except: return self._map.__delitem__(idx)
        else: return list.__delitem__(self, idx)

        #def append(self, item):
            #    if type(item) is not conv_container:
                #        raise TypeError('Wrong type of container. Use a conv_container instead of %s' % type(item))
                #    return list.append(self, item)

    def join(self, item):
        if type(item) is conv_container:
            try: return self[item.thread].merge(item)
            except KeyError:
                self.append(item)
                self[item.thread] = item
        elif type(item) is msg_container:
            return self.join(conv_container(item))
        

class lazythread_container(thread_container):
    __slots__ = ('_duplist', '_sumlist')
    def append(self, conv):
        if not conv.thread:
            conv.thread.append(uuid4().hex)
        self.__super.append(conv)
        self.dictify(conv)

    def extend(self, keymatch, new):
        #pdb.set_trace()
        self[keymatch].merge(new)
        self.dictify(self[keymatch])

    def dictify(self, one=False):
        def quack(key, msgobj):
            try: self[key]
            except: self[key] = msgobj
            else:
                if self[key] is not msgobj:
                    if self[key] not in self._duplist and self[key] is not None:
                        self._duplist.append(self[key])
                        msgobj.merge(self[key])
                        self._sumlist.extend([x for x in \
                                msgobj.msgids|msgobj.subjects \
                                if x not in self._sumlist])
                        try: self.remove(self[key])
                        except: pass
                    self[key] = msgobj

        self._duplist = []
        if one:
            self._sumlist = list(one.msgids|one.subjects)
            #self._sumlist.extend(one.msgids|one.subjects)
            [quack(x, one) for x in self._sumlist]
            del self._sumlist, self._duplist
        else:
            [self.dictify(msgobj) for msgobj in self]
            #del duplist, sumlist

    def thread(self, messages):
        map(self._thread, messages)
        self.datesort()
        return

    def _thread(self, msg):
        '''does the actual threading'''
        # in case we're on the first pass...
        if not self:
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


class prop_deque(deque):
	__slots__ = ()
        #def __repr__(self):
            #	if self.__len__() == 1: return self[0]
            #	else: return deque.__repr__(self)

def prop_wrap(func):
    def wrapper(*args, **kwargs):
        __ret = func(*args, **kwargs)
        if not hasattr(__ret, '__iter__'):
            __ret = [__ret]
        return prop_deque(__ret)
    return wrapper

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

def msg_factory(muuid, msg=None):
    if not msg:
        msg = mail_grab.get(muuid)
    __r = _msg_factory(muuid, msg)
    #except:
        #    if type(msg) is not ProcessedDocument or \
                #        not hasattr(msg, get_flags):
            #        raise TypeError('Unsupported message type. Tried parsing anyway, but it still failed.\nMessage object type: %s' % type(msg))
    __r = msg_container(*__r)
    return __r
        
def _msg_factory(muuid, msg):
    field_map = {'sender': 'to', 'msgid': 'message-id', 'sent': 'date',
                    'osubject': 'subject', 'in_reply_to': 'in-reply-to'}
    field_map_blank = {}
    field_multis = {'cc':',', 'to':',', 'flags':None, 'labels':None, 'references':None}
    @prop_wrap
    def do_get(field):
        def do_multi(data):
            try: __x = filterNone(set(data.split(field_multis[field])))
            except AttributeError: __x = data
            try: __x.__iter__
            except: return __x
            else:
                try: return [__i.strip() for __i in __x]
                except AttributeError: return __x
        try: msg.get_flags
        except: field_dict = field_map_blank
        else: field_dict = field_map

        __data = msg.get(field_dict.get(field, field), [])
        if field_dict:
            if field == 'subject': __data = stripSubject(__data)
            elif field == 'sent': __data = datetime(*parsedate(__data)[:6])
            elif field == 'muuid' and not __data: __data = muuid
            elif field in field_multis:
                if field == 'flags': __data = [__x for __x in msg.get_flags()]
                else: __data = do_multi(__data)
                #else: __data = map(do_multi, __data)
                #__data = do_multi(__data, field)

        return __data
    #__data_generator = ( prop_deque(do_get(msg, field)) for field in msg_field )
    __data_generator = ( do_get(field) for field in msg_fields )
    return __data_generator

def conv_factory(msg):
    if type(msg) is not msg_container:
        raise TypeError('Unsupported message container type. Use msg_factory first to encapsulate msg in a msg_container.\nMessage object type: %s' % type(msg))
        #msg = msg_container(msg)
    __r = _conv_factory(msg)
    __r = conv_container(*__r)
    return __r

def _conv_factory(msg):
    __msgid = set(msg.get('msgid'))
    __in_reply = set(msg.get('in_reply_to'))
    __refs = set(msg.get('references'))

    __msgids = __msgid | __in_reply | __refs
    delNone(__msgids)
    __subjects = set(msg.get('subject',[]))
    delNone(__subjects)
    __labels = set(msg.get('labels',[]))
    delNone(__labels)
    __thread = msg.get('thread',[])
    __thread = prop_deque(__thread)
    return __msgids, __subjects, __labels, __thread, [msg]
