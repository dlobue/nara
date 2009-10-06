#!/usr/bin/python

from weakref import ref
import urwid
from urwid import ListWalker
from buffer import buffer_manager
import collections
import weakref
from datetime import datetime, timedelta
from email.utils import getaddresses
from operator import itemgetter, attrgetter

from achelois.lib import util

from achelois.lib.message_machine import msg_machine
from achelois import offlinemaildir
from achelois import tools

from string import ascii_lowercase, digits, maketrans
anonitext = maketrans(ascii_lowercase + digits, 'x'*26 + '7'*len(digits))

mymail = offlinemaildir.mail_sources()

fold_dict = {
            'empty': None,
            'detail': True,
            'expanded': True,
            'collapse': False
            }
state_dict = {
            'BLOCK': 'block quote',
            'HTML': 'html-encoded text',
            'QUOTE': 'quotted text',
            'DUNNO': 'not sure what block is',
            'ATTACHMENT': 'attached file',
            }
type_dict = state_dict
attr_dict = {
            'BLOCK': 'block quote',
            'HTML': 'html',
            'QUOTE': 'block quote',
            'DUNNO': 'dunno',
            'ATTACHMENT': 'attachment',
            }


class message_machine(list):
    #{{{
    def __init__(self, conv, mindex, muuid):
        self.muuid = muuid
        msg_get = mymail.get(muuid[0])
        processed = msg_machine.process(msg_get)
        self.extend((machined_widget(conv, mindex, idx, data) for idx,data in enumerate(processed)))
        #}}}

class conversation_cache(object):
    #{{{
    #__metaclass__ = urwid.MetaSignals
    #signals = ['log']
    #_inst_buffers = weakref.WeakKeyDictionary()
    _inst_buffers = {}

    @classmethod
    def destroy(cls, conv):
        del cls._inst_buffers[conv]

    @classmethod
    def get_conv(cls, conv):
        try: return cls._inst_buffers[conv]
        except:
            cls._inst_buffers.setdefault(conv,{'msgs':conv, 'parts':{}, 'headers':{}})
            return cls.get_conv(conv)

    @classmethod
    def get_msg(cls, conv, mindex):
        try: return cls._inst_buffers[conv]['parts'][mindex]
        except:
            muuid = cls.get_conv(conv)['msgs'][mindex]['muuid']
            cls._inst_buffers[conv]['parts'][mindex] = message_machine(conv, mindex, muuid)
            return cls.get_msg(conv, mindex)

    @classmethod
    def get_mindex(cls, conv, mindex):
        try: return cls._inst_buffers[conv]['msgs'][mindex]
        except:
            return cls.get_conv(conv)['msgs'][mindex]

    @classmethod
    def get_part(cls, conv, mindex, index):
        if index is None:
            try: return cls._inst_buffers[conv]['headers'][mindex]
            except:
                r = cls.get_mindex(conv, mindex)
                cls._inst_buffers[conv]['headers'][mindex] = message_widget(conv, mindex)
                return cls.get_part(conv, mindex, index)
        try: return cls._inst_buffers[conv]['parts'][mindex][index]
        except: return cls.get_msg(conv, mindex)[index]
        #}}}

class conversation_widget(urwid.WidgetWrap):
    #{{{
    ''' This widget is not meant for direct use.
    conv is the conv_repr.messages of the particular conversation
    mindex is index of the msg we're on in conv
    index is the position in the results from the state machine
    display are the contents of the state we're in
    '''

    __metaclass__ = urwid.MetaSignals
    signals = ['focus']

    def __init__(self, conv, mindex=0, index=None, attr=None, focus_attr=None):
        self.conv = conv
        self.mindex = mindex
        self.index = index

        #mywalker = buffer_manager.get_buffer(conv)
        #urwid.Signals.connect(self, 'focus', mywalker.set_focus)

        widget = urwid.Text('Loading')
        self.widget = widget
        w = urwid.AttrWrap(widget, attr, focus_attr)
        self.__super.__init__(w)

    def selectable(self):
        return True

    def keypress(self, (maxcol,), key):
        if key in (" ", "enter"):
            self.expanded = not self.expanded
            self.update_widget()
        elif key == 'x':
            buffer_manager.destroy()
        #elif key == 'n':
            #focus = self.find_next_new()
            #urwid.Signals.emit(self, 'focus', focus)
            #run find_next_new and send results via signal to walker
        elif key == 'm':
            container = conversation_cache.get_part(self.conv, self.mindex, None)
            container.detail = not container.detail
            if container.detail: container.expanded = True
            container.update_widget()
        else:
            return key

    def find_next_new(self):
        msgidx = self.mindex
        while 1:
            try: container = conversation_cache.get_part(self.conv, msgidx, None)
            except: break
            if container.expanded: break
            msgidx += 1
        return container.mindex, None

    def first_part(self):
        return None

    def last_part(self):
        return None

    def next_inorder(self):
        part = self.first_part()
        if part: return part
        if self.index is not None:
            try: return conversation_cache.get_part(self.conv, self.mindex, self.index+1)
            except IndexError: pass
        try: return conversation_cache.get_part(self.conv, self.mindex+1, None)
        except: return None

    def prev_inorder(self):
        if self.index >= 1:
            return conversation_cache.get_part(self.conv, self.mindex, self.index-1)
        elif self.index == 0:
            return conversation_cache.get_part(self.conv, self.mindex, None)
        if self.mindex > 0:
            r = conversation_cache.get_part(self.conv, self.mindex-1, None)
            part = r.last_part()
            if part: return part
            return r
        return None
    #}}}

class machined_widget(conversation_widget):
    #{{{
    def __init__(self, conv, mindex, index, contents):
        msg = conv[mindex]
        state, part = contents
        self.state = state
        self.contents = '\n%s' % part
        if state == 'MSG':
            container = conversation_cache.get_part(conv, mindex, None)
            if container.seen: attr = 'read msg'
            else: attr = 'new msg'
            self.expanded = True
        else:
            self.expanded = False
            attr = attr_dict[state]
        self.__super.__init__(conv, mindex, index, attr, 'focus')
        self.update_widget()

    def update_widget(self):
        if self.expanded:
            display = self.contents
        else:
            display = '+--- %s, enter or space to expand' % state_dict[self.state]
        self.widget.set_text(display)

    def keypress(self, (maxcol,), key):
        if self.state == 'MSG':
            container = conversation_cache.get_part(self.conv, self.mindex, None)
            return container.keypress((maxcol,), key)
        return self.__super.keypress((maxcol,), key)
    #}}}

class header_widget(conversation_widget):
    #{{{
    def __init__(self, conv, mindex):
        msg = conv[mindex]
        sender = msg.get('sender','')
        date = msg.get('date','')
        recipient = msg.get('recipient','')
        cc = msg.get('cc','')
        flags = msg.get('flags','')
        subject = msg.get('subject','')

        self.headers = u'From: %s\nSent: %s\nTo: %s\nCc: %s\nFlags: %s\nSubject: %s' % \
                (sender, date, recipient, cc, flags, subject)
        self.condensed = u"%s %s %s" % \
                (date, sender, subject)

        self.muuid = msg['muuid']

        if 'S' in flags:
            self.seen = True
            colors = 'read headers'
        else:
            self.seen = False
            colors = 'new headers'

        if mindex == 0 and not self.seen:
            self.detail = True
        elif conv[mindex] is conv[-1] and self.seen:
            self.detail = True
            self.expanded = True
        else: self.detail = False

        try: self.expanded
        except: self.expanded = not self.seen

        self.__super.__init__(conv, mindex, None, colors, 'focus headers')
        self.update_widget()

    def update_widget(self):
        if self.detail and self.expanded:
            display = self.headers
        else:
            display = self.condensed
        self.widget.set_text(display)
    
    def first_part(self):
        if not self.expanded:
            return None
        return conversation_cache.get_part(self.conv, self.mindex, 0)

    def last_part(self):
        if not self.expanded:
            return None
        return conversation_cache.get_part(self.conv, self.mindex, -1)
    #}}}

class collapsible(urwid.WidgetWrap):
    def __init__(self, contents=[]):
        self.contents = contents
        self.state
        self.type
        if contents:
            s = data[0].state
            l = len(data)
            w = urwid.Text('+--(%i) %s' % (l, state_dict[s]))
        else:
            # FUCK
    def selectable(self):
        return True

class group_state(object):
    def __init__(self, data):
        self.expanded = False
        self.detailed = False
        self._cache = [data]
        self.label = urwid.Text('+--(%i) %s' % (len(self._cache), state_dict[self._cache[0][0]]))

    def __getitem__(self, idx):
        if type(idx) is not int:
            raise TypeError "Index must be an integer."
        elif idx == 0:
            return self.label
        elif expanded:
            if idx > 0:
                return list.__getitem__(self._cache, idx-1)
            elif idx < 0:
                return list.__getitem__(self._cache, idx)
        elif not expanded:
            if idx == -1:
                return self.label
            else:
                raise IndexError "Invalid index"

    def __len__(self):
        if self.expanded:
            return list.__len__(self._cache)+1
        else:
            return 1

    def append(self, data):
        list.append(self._cache, data)

class message_widget(group_state):
    def __init__(self, msgobj):
        self.expanded = False
        self.detailed = False
        self._cache = []
        __msg_get = mymail.get(msgobj['muuid'][0])
        __processed = msg_machine.process(__msg_get)

        self.label = header_widget(msgobj)
        self._state_order = {'CONTENT':0}

        def fadd(p):
            try: self._cache[self._state_order[p[0]]].append(machined_widget(p))
            except KeyError:
                self._state_order[p[0]] = len(self._state_order)
                return fadd(p)
            except IndexError: 
                self._cache[self._state_order[p[0]]] = group_state(machined_widget(p))

        map(fadd, __processed)

    @property
    def last(self):
        if not self.expanded: return self.header


class collapse(list):
    def __init__(self, msg_level, data=[]):
        if msg_level == 'message':
            ##do processing
        if msg_level == 'state':
            if data: self.extend(data)

class read_walker(urwid.ListWalker):
    #{{{
    part_order = ('headers', 'content', 'blockquote', 'html', 'attachment')
    def __init__(self, convobj):
        self.order = []
        self._cache = map(message_widget, convobj.messages)
        self.focus = 0, 0, 0
    '''def __init__(self, conv):
        self.find_oldest_new()'''

    def find_oldest_new(self):
        msgidx, stateidx = self.focus
        while 1:
            #try:
            widget = attrgetter(self._cache[msgidx], self.part_order[0])
            #except: break
            if widget.expanded: break
            if msgidx == len(self._cache)-1: break
            msgidx += 1
        return self.set_focus((msgidx, 0))

    def get_focus(self):
        convpos, msgpos, statepos = self.focus
        w = self._cache[convpos][msgpos][statepos]
        return w, self.focus

    def set_focus(self, focus):
        convpos, msgpos, statepos = focus
        self.focus = convpos, msgpos, statepos
        self._modified()

    def get_next(self, start_from):
        convpos, msgpos, statepos = start_from
        def mdef(convpos, msgpos, statepos):
            return self._cache[convpos][msgpos][statepos], (convpos, msgpos, statepos)
        try: return mdef(convpos, msgpos, statepos+1)
        except IndexError:
            try: return mdef(convpos, msgpos+1, 0)
            except IndexError:
                try: return mdef(convpos+1, 0, 0)
                except IndexError:
                    return None, (None, None, None)

    def get_prev(self, start_from):
        convpos, msgpos, statepos = start_from
        def mdef(convpos, msgpos, statepos):
            if msgpos == -1:
                msgpos = len(self._cache[convpos])-1
            if statepos == -1:
                statepos = len(self._cache[convpos][msgpos])-1
            return self._cache[convpos][msgpos][statepos], (convpos, msgpos, statepos)

        if statepos == 0:
            if msgpos == 0:
                if convpos == 0:
                    return None, (None, None, None)
                return mdef(convpos-1, -1, -1)
            return mdef(convpos, msgpos-1, -1)
        return mdef(convpos, msgpos, statepos-1)

    '''
    def get_focus(self):
        msgidx, stateidx = self.focus
        widget = attrgetter(self._cache[msgidx], self.part_order[stateidx])
        return widget, self.focus

    def set_focus(self, focus):
        msgidx, stateidx = focus
        self.focus = msgidx, stateidx
        self._modified()

    def get_next(self, start_from):
        msgidx, stateidx, minoridx = start_from
        if minoridx == 0:
            if stateidx == 0:
                if fold_dict[self._cache[msgidx].state]:
                    if msgidx == len(self._cache)-1:
                        return None, None, None
                    else:
                        return msgidx+1, 0, 0

        if not self._cache[msgidx][stateidx].state:
            return msgidx, stateidx+1, 0
        if minoridx == len(self._cache[msgidx][stateidx])-1:
            if stateidx == len(self._cache[msgidx])-1:
                if msgidx == len(self._cache)-1:
                    return None, None, None
                else:
    def get_next(self, start_from):
        msgidx, stateidx = start_from
        def advance_one(msgidx, stateidx):
            if stateidx == len(self.part_order)-1:
                if msgidx == len(self._cache)-1:
                    return None, None
                else:
                    msgidx += 1
                    stateidx = 0
            else:
                stateidx += 1
            return msgidx, stateidx
        msgidx, stateidx = advance_one(msgidx, stateidx)
        while 1:
            try: widget = attrgetter(self._cache[msgidx], self.part_order[stateidx])
            except: msgidx, stateidx = advance_one(msgidx, stateidx)
            else: break
        return widget, (msgidx, stateidx)

    def get_prev(self, start_from):
        msgidx, stateidx = start_from
        def back_one(msgidx, stateidx):
            if not stateidx:
                if not msgidx:
                    return None, None
                else:
                    msgidx -= 1
                    go_last = True
            else:
                stateidx -= 1
                go_last = False
            return msgidx, stateidx, go_last
        msgidx, stateidx, go_last = back_one(msgidx, stateidx)
        while 1:
            if go_last:
                widget = attrgetter(self._cache[msgidx], 'last')
                stateidx = self.part_order.index(widget.state)
                break
            else:
                try: widget = attrgetter(self._cache[msgidx], self.part_order[stateidx])
                except: msgidx, stateidx, go_last = back_one(msgidx, stateidx)
        return widget, (msgidx, stateidx)
        '''
    #}}}
