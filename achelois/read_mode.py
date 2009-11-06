#!/usr/bin/python

from urwid import ListWalker, Text
from weakref import ref

from achelois.lib.message_machine import msg_machine
from achelois.lib.metautil import MetaMelt
from achelois import offlinemaildir

#from string import ascii_lowercase, digits, maketrans
#anonitext = maketrans(ascii_lowercase + digits, 'x'*26 + '7'*len(digits))

class xresult_ref(object):
    __slots__ = ('_cache',)

    def __init__(self, data):
        self._cache = ref(data)

    def __getattr__(self, attr):
        __ret = self._cache()[attr]
        try: return __ret[0]
        except: return __ret

mymail = offlinemaildir.mail_sources()

state_dict = {
            'BLOCK': 'block quote',
            'HTML': 'html-encoded text',
            'QUOTE': 'quotted text',
            'DUNNO': 'not sure what block is',
            'ATTACHMENT': 'attached file',
            }
attr_dict = {
            'BLOCK': 'block quote',
            'HTML': 'html',
            'QUOTE': 'block quote',
            'DUNNO': 'dunno',
            'ATTACHMENT': 'attachment',
            }
fold_guide = {
        'MSG': (True, True),
        'BLOCK': (False,),
        'HTML': (False,),
        'QUOTE': (False,),
        'DUNNO': (False,),
        'ATTACHMENT': (False, False),
        }

class text_select_templ(Text, MetaMelt):
    __slots__ = ()
    _selectable = True
    ignore_focus = False

class text_select(text_select_templ):
    __slots__ = ()
    def keypress(self, (maxcol,), key):
        self._emit('keypress', (maxcol,), key)

class text_select_collapse(text_select_templ):
    __slots__ = ()
    expanded = False
    context = 'conversation_view'
    def __init__(self, __data, align='left', wrap='space', layout=None):
        __state, __detail = __data
        self.state = __state
        self._detail = __detail
        self.expanded = fold_guide[__state][0] # some widgets should be open by default, others not
        self.__super.__init__(self.auto_text(), align, wrap, layout)

    def do_toggle(self, (maxcol,),):
        try: self.expanded = fold_guide[self.state][1] #some widgets should never open, or be closed
        except IndexError: self.expanded = not self.expanded #the rest can toggle

    def update_widget(self):
        self.set_text(self.auto_text())
        self._modified()
    def auto_text(self):
        if self.expanded: return self.detail
        else: return self.summary
    @property
    def detail(self):
        __r = self._detail
        return __r
    @property
    def summary(self):
        __r = '+--- %s, enter or space to expand' % state_dict[self.state]
        return __r

class collapser_label(text_select): pass

class collapser(MetaMelt):
    __slots__ = ()
    context = 'conversation_view'
    expanded = False
    detailed = False
    label = collapser_label('Loading')
    _cache = []

    def __init__(self, data):
        self._cache.extend(data)
        #self.label = collapser_label(self.auto_text())
        #self.label = Text('+--(%i) %s' % (len(self._cache), state_dict[self._cache[0][0]]))

    def __iter__(self):
        return self._cache.__iter__()

    def _allconn_4cache(self):
        """Create signals for all of our children so that
        they need only emit(self,... and they're speaking
        directly to their parent"""
        map(self.all_connect, self._cache)

    def _allconn_4child_cache(self):
        """Be generous and initiate kconn_cache on all of
        our children so their children have a direct line
        to them. If one child doesn't have kconn_cache though,
        the rest probably don't either."""
        def quack(__x):
            __x.allconn_4cache()
        try: map(quack, self._cache)
        except AttributeError: pass

    def allconn_4cache(self):
        self._allconn_4cache()
        self._allconn_4child_cache()

    def update_widget(self):
        self.label.set_text(self.auto_text())
        self._modified()

    def auto_text(self): return 'Placeholder text'

    def _do_set_expanded(self, (maxcol,), status=None): self._change_expanded(status)
    def _do_toggle_expanded(self, (maxcol,),): self._change_expanded(None)
    def _do_open_expanded(self, (maxcol,),): self._change_expanded(True)
    def _do_close_expanded(self, (maxcol,),): self._change_expanded(False)

    def _do_set_detailed(self, (maxcol,), status=None): self._change_detailed(status)
    def _do_toggle_detailed(self, (maxcol,),): self._change_detailed(None)
    def _do_open_detailed(self, (maxcol,),): self._change_detailed(True)
    def _do_close_detailed(self, (maxcol,),): self._change_detailed(False)

    def _change_expanded(self, status=None):
        if status is None: self.expanded = not self.expanded
        elif type(status) is bool: self.expanded = status
        if self.detailed and not self.expanded:
            self.detailed = False
        self.update_widget()

    def _change_detailed(self, statue=None):
        if open is None: self.detailed = not self.detailed
        elif type(open) is bool: self.detailed = open
        if self.detailed and not self.expanded:
            self.expanded = True
        self.update_widget()

    def __getitem__(self, idx):
        if type(idx) is not int:
            raise TypeError("Index must be an integer.")
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
                raise IndexError("Invalid index")

    def __len__(self):
        if self.expanded:
            return list.__len__(self._cache)+1
        else:
            return 1

    def append(self, data):
        list.append(self._cache, data)

class group_state(collapser):
    __slots__ = ()
    def auto_text(self):
        if self.expanded: return self.open
        else: return self.close
    @property
    def open(self):
        return '[-]---enter or space to close group of %s' % state_dict[self._cache[0].state]
    @property
    def close(self):
        return '[+]---Set of (%i) %s, enter or space to expand' % (len(self._cache), state_dict[self.state])

    do_group_set_expanded = _do_set_expanded
    do_group_toggle_expanded = _do_toggle_expanded
    do_group_open_expanded = _do_open_expanded
    do_group_close_expanded = _do_close_expanded

    do_group_set_detailed = _do_set_detailed
    do_group_toggle_detailed = _do_toggle_detailed
    do_group_open_detailed = _do_open_detailed
    do_group_close_detailed = _do_close_detailed

    '''
    def do_group_set_expanded(self, (maxcol,), status=None): self._change_expanded(status)
    def do_group_toggle_expanded(self, (maxcol,),): self._change_expanded(None)
    def do_group_open_expanded(self, (maxcol,),): self._change_expanded(True)
    def do_group_close_expanded(self, (maxcol,),): self._change_expanded(False)

    def do_group_set_detailed(self, (maxcol,), status=None): self._change_detailed(status)
    def do_group_toggle_detailed(self, (maxcol,),): self._change_detailed(None)
    def do_group_open_detailed(self, (maxcol,),): self._change_detailed(True)
    def do_group_close_detailed(self, (maxcol,),): self._change_detailed(False)
    '''

class message_widget(collapser):
    __slots__ = ('msgobj', '_state_order')
    def __init__(self, msgobj):
        __msg_get = mymail.get(msgobj['muuid'][0])
        __processed = msg_machine.process(__msg_get)

        self.msgobj = msgobj
        if 'S' in msgobj.get('flags', ''): self.change_expanded(True)
        #self.label = header_widget(msgobj)
        self._state_order = {'CONTENT':0}

        def fadd(p):
            try: self._cache[self._state_order[p[0]]].append(machined_widget(p))
            except KeyError:
                self._state_order[p[0]] = len(self._state_order)
                return fadd(p)
            except IndexError: 
                self._cache[self._state_order[p[0]]] = group_state(machined_widget(p))

        map(fadd, __processed)

    def auto_text(self):
        if self.detailed: return self.detail
        else: return self.summary

    def _get_details(self, __detlist):
        def quack(__field):
            __d = self.msgobj.get(__field, '')
            try: return __d[0]
            except: return __d
        return map(quack, __detlist)
        
    @property
    def detail(self):
        __fd = self._get_details(['sender', 'date', 'recipient', 'cc', 'flags', 'subject'])
        __r = 'From: %s\nSent: %s\nTo: %s\nCc: %s\nFlags: %s\nSubject: %s' % __fd
                #(__fd[0], __fd[1], __fd[2], __fd[3], __fd[4], __fd[5])
        return __r
    @property
    def summary(self):
        __fd = self._get_details(['data', 'sender'])
        __r = u"Sent %s by %s" % __fd
        #__r = u"Sent %s by %s" % (__fd[0], __fd[1])
        return __r

    do_msg_set_expanded = _do_set_expanded
    do_msg_toggle_expanded = _do_toggle_expanded
    do_msg_open_expanded = _do_open_expanded
    do_msg_close_expanded = _do_close_expanded

    do_msg_set_detailed = _do_set_detailed
    do_msg_toggle_detailed = _do_toggle_detailed
    do_msg_open_detailed = _do_open_detailed
    do_msg_close_detailed = _do_close_detailed

    '''
    def do_msg_set_expanded(self, (maxcol,), status=None): self._change_expanded(status)
    def do_msg_toggle_expanded(self, (maxcol,),): self._change_expanded(None)
    def do_msg_open_expanded(self, (maxcol,),): self._change_expanded(True)
    def do_msg_close_expanded(self, (maxcol,),): self._change_expanded(False)

    def do_msg_set_detailed(self, (maxcol,), status=None): self._change_detailed(status)
    def do_msg_toggle_detailed(self, (maxcol,),): self._change_detailed(None)
    def do_msg_open_detailed(self, (maxcol,),): self._change_detailed(True)
    def do_msg_close_detailed(self, (maxcol,),): self._change_detailed(False)
    '''

class read_walker(ListWalker, MetaMelt):
    __slots__ = ('_cache', 'focus')
    def __init__(self, convobj):
        def quack(__x):
            __x.allconn_4cache()

        self._cache = map(message_widget, convobj.messages)
        map(quack, self._cache)
        self.focus = 0, 0, 0
        self.find_oldest_new()

    def find_oldest_new(self):
        return self.find_next_new(start_from=(0,0,0))
        
    def find_next_new(self, start_from=None):
        if start_from: convpos, msgpos, statepos = start_from
        else: convpos, msgpos, statepos = self.focus
        if convpos > 0: convpos += 1
        for __w in self._cache[convpos:]:
            if __w.expanded: break
        __w.change_detailed(True)
        convpos = self._cache.index(__w)
        return self.set_focus((convpos, 0, 0))

    def get_next_msg(self):
        convpos, msgpos, statepos = self.focus
        convpos, msgpos, statepos = convpos+1, 0, 0
        try: return self._cache[convpos][msgpos][statepos], (convpos, msgpos, statepos)
        except IndexError: return None, (None, None, None)

    def get_prev_msg(self):
        convpos, msgpos, statepos = self.focus
        convpos, msgpos, statepos = convpos-1, 0, 0
        try: return self._cache[convpos][msgpos][statepos], (convpos, msgpos, statepos)
        except IndexError: return None, (None, None, None)

    def do_find_oldest_new(self, *args, **kwargs):
        self.find_oldest_new(self, *args, **kwargs)
    def do_find_next_new(self, *args, **kwargs):
        self.find_next_new(self, *args, **kwargs)
    def do_get_next_msg(self, *args, **kwargs):
        self.get_next_msg(self, *args, **kwargs)
    def do_get_prev_msg(self, *args, **kwargs):
        self.get_prev_msg(self, *args, **kwargs)

    def get_focus(self):
        convpos, msgpos, statepos = self.focus
        __w = self._cache[convpos][msgpos][statepos]
        return __w, self.focus

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
