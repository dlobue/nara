#observer pattern.. i think
from overwatch import mail_grab, emit_signal, eband, MetaSignals, register_signal

#system modules
from collections import deque, namedtuple
from operator import attrgetter
from weakref import WeakValueDictionary
from bisect import insort_right
from datetime import datetime
from email.utils import parsedate
from uuid import uuid4

#other modules i need that aren't sys, and I didn't write
from lib import threadmap

#lastly my tools
from tools import delNone, filterNone
from lib.metautil import MetaSuper

msg_fields = ('sent', 'sender', 'to', 'cc', 'subject', 'osubject', 'msgid', 'muuid', 'flags', 'labels', 'mtime', 'in_reply_to', 'references', 'sample', 'thread')
conv_fields = ('nique_terms', 'labels', 'muuids', 'thread', 'messages')

_msg_container = namedtuple('msg_container', msg_fields)
_conv_container = namedtuple('conv_container', conv_fields)

class prop_deque(deque):
    #__slots__ = ()
    def __str__(self):
        if len(self) == 1:
            return self[0]
        return self

    def __call__(self):
        if len(self) == 1:
            return self[0]
        return self

def auto_deque(func):
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
    '''
    Takes a xapian search result objects and maildir message objects and
    returns a standardized msg_container with everything I need.
    Always working with data in the same format makes it easier to index it
    and write code to display it.
    '''
    try:
        muuid, msg = muuid.id, muuid.data
    except AttributeError:
        try:
            muuid, msg = muuid
        except: pass


    '''
    if type(muuid) is xappy.searchconnection.SearchResult:
        muuid, msg = muuid.id, muuid.data
    elif type(muuid) is tuple:
        muuid, msg = muuid
    elif type(muuid) is ProcessedDocument:
        muuid, msg = muuid.id, muuid.data
    elif type(muuid) is SearchResult:
        muuid, msg = muuid.id, muuid.data
    elif type(muuid) is UnprocessedDocument:
        muuid, msg = muuid.id, muuid.data
        '''

    if not msg:
        msg = mail_grab.get(muuid)
        if not msg:
            raise KeyError("invalid muuid given! Couldn't find a message to parse!\nmuuid type is: %s" % str(type(muuid)))
    __r = _msg_factory(muuid, msg)
    __r = msg_container(*__r)
    return __r

def _msg_factory(muuid, msg):
    '''
    This does the actual work of pulling the information we care about
    out of the message containers we'll be working with.
    '''
    field_map = {'sender': 'From', 'msgid': 'Message-ID', 'sent': 'Date',
                    'osubject': 'Subject', 'in_reply_to': 'In-Reply-To'}
    field_map_blank = {}
    field_multis = {'cc':',', 'to':',', 'flags':None, 'labels':None, 'references':None}
    @auto_deque
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

        return __data
    #__data_m = map(do_get, msg_fields)
    #__data_m = threadmap.map(do_get, msg_fields)
    __data_m = (do_get(x) for x in msg_fields)
    return __data_m

def conv_factory(msg):
    '''
    Takes msg_containers and puts them in conversation containers.
    
    This is actually just a preparation function.

    When creating the conversation container put all unique information that
    could help us in identifying other messages in the conversation into easy
    to reach places.
    '''
    if type(msg) is not msg_container:
        raise TypeError('Unsupported message container type. Use msg_factory first to encapsulate msg in a msg_container.\nMessage object type: %s' % type(msg))
    __r = _conv_factory(msg)
    __r = conv_container(*__r)
    return __r

def _conv_factory(msg):
    '''
    This does the actual work pulling the unique information out of a message.
    '''
    __muuid = prop_deque(msg.get('muuid', []))

    __msgid = set(msg.get('msgid', []))
    __in_reply = set(msg.get('in_reply_to', []))
    __refs = set(msg.get('references', []))
    __subjects = set(msg.get('subject',[]))

    __nique_terms = __msgid | __in_reply | __refs | __subjects
    delNone(__nique_terms)

    __labels = set(msg.get('labels',[]))
    delNone(__labels)

    __thread = msg.get('thread',[])
    __thread = prop_deque(__thread)
    return (__nique_terms, __labels, __muuid, __thread, [msg])

class msg_container(_msg_container):
    '''
    Monkey patch the named tuple _msg_container and add in a dict-like
    get method. (Don't remember why I needed this originally).
    '''
    __slots__ = ()

    def __getstate__(self):
        return dict((name, getattr(self, name)) for name in self.__slots__ if hasattr(self,name))
    def __setstate__(self, state):
        for name,value in state.iteritems():
            setattr(self, name, value)

    def get(self, key, alt=None):
        try: return getattr(self, key)
        except AttributeError:
            return alt

class conv_container(object):
    '''
    Wrap the conv_container named tuple and add some needed methods.
    '''
    __slots__ = ('__weakref__', '_container', '_wcallback', '_urwid_signals')
    __slots__ = ('__weakref__', '_container', '_wcallback', '_urwid_signals')
    _factory_callback = staticmethod(_conv_factory)

    def __init__(self, *args, **kwargs):
        self._container = _conv_container(*args, **kwargs)

    #def __getstate__(self):
        #    return dict((name, getattr(self, name)) for name in self.__slots__ if hasattr(self,name))
    #def __setstate__(self, state):
        #    for name,value in state.iteritems():
            #        setattr(self, name, value)

    def __getattr__(self, name):
        return getattr(self._container, name)

    def __getstate__(self):
        return dict((name, getattr(self, name)) for name in self.__slots__ if hasattr(self,name))
    def __setstate__(self, state):
        for name,value in state.iteritems():
            setattr(self, name, value)
    def __repr__(self):
        return repr(self._container)
    def __iter__(self):
        return iter(self._container)

    @property
    def last_update(self):
        '''
        Convenience method to quickly find out when this conversation was last
        updated.
        '''
        return self.messages[-1].sent[0]

    def get(self, key, alt=None):
        try: return getattr(self, key)
        except AttributeError:
            return alt

    def _rebuild(self):
        '''
        In case the merging of two conversations ever messes up and needed
        information is lost, or garbage is added, clear the attribute containers
        and rebuild them from the messages.
        '''
        self.nique_terms.clear()
        self.labels.clear()
        self.muuids.clear()
        __res = map(lambda x: self._factory_callback(x)[:3], self.messages)
        __res = zip(__res)
        map(self.nique_terms.update, __res[0])
        map(self.labels.update, __res[1])
        map(self.muuids.append, __res[2])

    def merge(self, dispose):
        '''
        Merge given conversation into ourself. Copy all messages we do not already have
        into out message container, and copy unqiue identifying terms we do not have
        into ourself.
        '''
        def do_insort(x):
            '''
            Use bisect to put new messages into our message list in the correct order
            the first time so we never have to waste time using sort later.
            '''
            insort_right(self.messages, x)
            self.muuids.extend(x.muuid)

        self.nique_terms.update(dispose.nique_terms)
        self.labels.update(dispose.labels)
        #threadmap.map(do_insort,
        map(do_insort,
                filter(lambda x: x.muuid[0] not in self.muuids, dispose.messages))
        try: self._wcallback()()
        except: pass

class tup_conv_container(_conv_container):
    '''
    This monkey patches the conversation container named tuple instead of just
    wrapping it. Unfortunately you can't create weak references to namedtuples.

    This is identical otherwise to the wrapper version.
    '''
    __slots__ = ()
    _factory_callback = staticmethod(_conv_factory)

    @property
    def last_update(self):
        return self.messages[-1].sent

    def get(self, key, alt=None):
        try: return getattr(self, key)
        except AttributeError:
            return alt

    def _rebuild(self):
            self.nique_terms.clear()
            self.labels.clear()
            self.muuids.clear()
            #__res = map(lambda x: self._factory_callback(x)[:3], self.messages)
            __res = (self._factory_callback(x)[:3] for x in self.messages)
            __res = zip(__res)
            map(self.nique_terms.update, __res[0])
            map(self.labels.update, __res[1])
            map(self.muuids.append, __res[2])

    def merge(self, dispose):
	def do_insort(x):
	    insort_right(self.messages, x)
            self.muuids.extend(x.muuid)

        self.nique_terms.update(dispose.nique_terms)
        self.labels.update(dispose.labels)
        #threadmap.map(do_insort,
        map(do_insort,
                filter(lambda x: x.muuid[0] not in self.muuids, dispose.messages))

#conv_container = obj_conv_container

class lazy_refmap(dict):
    '''
    This was a (I think) rather clever solution to emulate weakvaluedictionaries.
    This was previously required for the thread containers to work since it is
    not possible create weak references to namedtuples.

    While no longer required, I may find another use for it or the techniques
    it employs in the future.
    '''
    __slots__ = ('_list', '_keyattr')
    __metaclass__ = MetaSuper
    def __init__(self, reflist, keyattr=None):
        self._list = reflist
        self._keyattr = keyattr
        self.__super.__init__()

    _getitem = dict.__getitem__

    def __getitem__(self, key):
        val = self._getitem(key)
        if val in self._list: return val
        else:
            if self._keyattr:
                to_remove = getattr(val, self._keyattr)
                map(self.__delitem__,
                    filter(lambda k: val is self._getitem(k), to_remove))

            del self[key]
            raise KeyError("Item key %s references no longer exists." % key)

class thread_container(list):
    '''
    Base class for thread containers. This container requires "hints" in
    order to work. Okay, it requires more than hints. It needs every
    conversation container to list its conversaton id.

    To be clear, thread_containers are used to merge related conversations
    into the same object, and are used to contain all emails/conversations
    in a folder or those found in a query.

    The thread_container holds the conversations inside itself (it is a list)
    and holds metadata that is used to instantly find related conversations
    in self._map when adding new messages to the container.

    While Jamie Zawinski makes some excellent arguments against storing
    which message belongs to which conversation, doing threading his way
    requires either loading every message into ram in order to find every
    message that goes in a conversation, or doing dozens of searches until
    everything we find everything. This eats up lots of ram unfortunately. :(
    '''
    __slots__ = ('_map')
    __metaclass__ = MetaSuper
    def __init__(self):
        #self._map = lazy_refmap(self, 'nique_terms')
        #self._map = {}
        self._map = WeakValueDictionary()
    def datesort(self):
        '''
        Sort conversations so newest are at the top.
        '''
        self.sort(key=attrgetter('last_update'), reverse=True)

    def __getitem__(self, idx):
        '''
        If the key we're given is an integer, what's being asked for is a
        message at index idx. Otherwise we've been given a string and are being
        asked to look up something in the lookup table instead.
        '''
        try: idx.__int__
        except AttributeError: return self._map[idx]
        else: return self.__super.__getitem__(idx)
    def __setitem__(self, idx, value):
        try: idx.__int__
        except AttributeError: return self._map.__setitem__(idx, value)
        else: return self.__super.__setitem__(idx, value)
    def __delitem__(self, idx):
        try: idx.__int__
        except AttributeError: return self._map.__delitem__(idx)
        else: return self.__super.__delitem__(idx)

        #def append(self, item):
            #    if type(item) is not conv_container:
                #        raise TypeError('Wrong type of container. Use a conv_container instead of %s' % type(item))
                #    return list.append(self, item)

    def join(self, item):
        '''
        To keep things lite and simple (translation: use the least amount of
        of ram possible while still keeping things fast), look conversations
        up only based upon their threadid.
        '''
        if type(item) is conv_container:
            try: return self[item.thread[0]].merge(item)
            except KeyError:
                self.append(item)
                self[item.thread[0]] = item
        elif type(item) is msg_container:
            raise TypeError('Unable to thread that.')
            #return self.join(conv_container(item))

    _thread = join

    def thread(self, msgs):
        #map(self._thread, threadmap.map(conv_factory, msgs) )
        map(self._thread, (conv_factory(x) for x in msgs) )
        self.datesort()
        return
        

class lazythread_container(thread_container):
    '''
    Builds upon thread_container and does not require a conv_container to know
    what conversation it belongs to.

    This container finds related conversations based on the following email headers:
        -in-reply-to
        -references
        -subject

    Why subject? Because not everybody uses an email client that handles
    reference ids like they should, and forwarding an email wipes out the
    reference ids.
    '''
    __slots__ = ()
    def append(self, conv):
        '''
        Appends one conversation to the list. If the conversation does not
        already have a thread id, it creates a unique new one.

        As a last step it updates the lookup table with any new unique terms.
        '''
        if not conv.thread:
            conv.thread.append(uuid4().hex)
        self.__super.append(conv)
        self.dictify(conv)

    def extend(self, keymatch, new):
        '''
        Merges an orphaned conversation in with the rest of its "family",
        and then updates the lookup table with any new unique terms.
        '''
        self[keymatch].merge(new)
        self.dictify(self[keymatch])

    def dictify(self, dictifyee=False):
        '''
        This method is the very core of my threading method. It works by
        putting every unique term a conversation can be identified by goes into
        the _map dictionary (unique term = key, conversation = value).

        This method has two purposes: to add new terms to the lookup table,
        and to ensure threading integrity. This method works by iterating over
        every unique term in a given conversation and adding it to the lookup
        table.

        Weak references are used in the lookup table to prevent new conversatons
        from being threaded into conversation containers that are being discarded.
        '''
        termlist = []
        def quack(key):
            try:
                if self[key] is dictifyee: return #term is already in table
                                                  # and points to the right conv
            except (IndexError, KeyError):
                self[key] = dictifyee #never heard of the term before so set it.
            else:
                if self[key] is not dictifyee: #term is in table, but points to
                                                #another conversation. remove
                                                #newly discovered conversation
                                                #and merge it into ours.
                    removee = self[key]
                    self.remove(self[key])
                    try:
                        __new_terms = removee.nique_terms.difference(termlist)
                        dictifyee.merge(removee)
                        termlist.extend(__new_terms)
                        if self._map is not WeakValueDictionary:
                            map(self._map.__delitem__,
                                filter(lambda k: removee is self[k], removee.nique_terms))
                        #for k in removee.nique_terms:
                            #try: v = self[k]
                            #except KeyError: continue
                            #if v is removee: del v, self[k]
                    except AttributeError: pass

                    #del removee
                    self[key] = dictifyee

        if dictifyee:
            #add unique terms from new conversation to lookup table.
            termlist.extend(dictifyee.nique_terms)
            map(quack, termlist)
        else:
            #verify threading integrity.
            map(self.dictify, iter(self))

    def thread(self, messages):
        '''
        This method is for threading batch jobs of messages.
        As a last step this method sorts all conversations by date, newest
        first (ie- most recently updated conversation is at index 0).
        '''
        #map(self._thread, messages)
        map(self._thread, (conv_factory(x) for x in messages if isinstance(x, msg_container)) )
        self.datesort()
        return

    def _thread(self, msg):
        '''
        does the actual threading
        '''
        #If we're empty, don't bother trying any lookups, just add the message.
        if not self:
            return self.append(msg)

        #for every term unique to this conversation...
        for key in msg.nique_terms:
            #see if the key is in the lookup table.
            try: self[key]
            except: pass
            else:
                return self.extend(key, msg)

        #none of our unique terms are apart of any conversation this container
        #already knows about. just append.
        return self.append(msg)


if __name__ == '__main__':
    pass
