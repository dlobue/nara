#!/usr/bin/python

from overwatch import eband, emit_signal, connect_signal, mail_grab

from weakref import ref
from threading import Thread

from urwid import ListWalker, Text, ListBox, AttrMap, WidgetWrap

from nara.lib.message_machine import msg_machine
from nara.lib.metautil import MetaMixin, MetaSupSig, ScrollMixin
from nara.lib import threadmap, forkmap
from mailutils import set_read, set_unread
from xindex import modify_factory, remove_fields, update_existing, replace_existing, xconn
from lib.async import Async

async = Async(Thread)

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


state_dict = {
            'MSG': 'body content',
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

class text_select(MetaMixin, ScrollMixin, WidgetWrap):
    __slots__ = ('__size')
    #ignore_focus = False
    _selectable = True
    no_cache = ['rows']
    signals = ['focus_modify']
    context = 'read_mode'

    def __init__(self, txt='Loading', attr='default attr', focus='default focus'):
        w = Text(txt)
        w = AttrMap(w, attr, focus)
        self.__super.__init__(w)

    def selectable(self): return self._selectable

    def __len__(self):
        return 1

    def _fconnect(self, child):
        self._connect('focus_modify', child, self._femit)
    def _femit(self, restore=False):
        self._emit('focus_modify', restore)
    def _femit1(self, mthd, status=None):
        self._emit('focus_modify', mthd, status)

    def _rows(self, size=None, focus=False):
        if type(size) is tuple: self.__size = size
        elif not hasattr(self, '__size'):
            raise TypeError
        else:
            size = self.__size
        return self._w.rows(size, focus)
    rows = _rows

    def __getitem__(self, idx):
        if idx == 0 or idx == -1:
            return self
        raise IndexError("no index %i here" % idx)

    def do_nomap(self, (maxcol,), key):
        #self._emit('keypress', (maxcol,), key)
        return key

    def set_attr_map(self, *args, **kwargs):
        return self._w.set_attr_map(*args, **kwargs)
    def set_focus_map(self, *args, **kwargs):
        return self._w.set_focus_map(*args, **kwargs)
    def set_text(self, *args, **kwargs):
        return self._w.original_widget.set_text(*args, **kwargs)
    def pack(self, *args, **kwargs):
        return self._w.original_widget.pack(*args, **kwargs)

class machined_widget(text_select):
    __slots__ = ('state', '_detail', 'expanded', '_parent')
    context = 'read_mode'
    def __init__(self, data, parent):
        __state, __detail = data
        self.state = __state
        self._detail = __detail
        self._parent = parent
        self.expanded = fold_guide[__state][0] # some widgets should be open by default, others not

        self.__super.__init__()
        self.update_widget()

    @property
    def new(self):
        return self._parent().new

    def do_toggle_expanded(self, (maxcol,), key):
        if self.state == 'MSG': return self._kemit((maxcol,), key)
        emit_signal(eband, 'log', 'in do_toggle_expanded for class %s' % str(self.__class__.__name__))
        try: self.expanded = fold_guide[self.state][1] #some widgets should never open, or be closed
        except IndexError: self.expanded = not self.expanded #the rest can toggle
        self.update_widget()

    def update_widget(self):
        txt, attr, focus_attr = self.auto_text()
        if type(attr) is str:
            attr = {None: attr}
        if type(focus_attr) is str:
            focus_attr = {None: focus_attr}
        self.set_attr_map(attr)
        self.set_focus_map(focus_attr)
        self.set_text(txt)
        self._modified()

    def auto_text(self):
        focus_attr = 'focus'
        if self.state == 'MSG':
            if self.new: stat = 'new'
            else: stat = 'read'
            return self.detail, '%s msg' % stat, focus_attr
        if self.expanded: return self.detail, attr_dict[self.state], focus_attr
        else: return self.summary, attr_dict[self.state], focus_attr

    @property
    def detail(self):
        __r = self._detail
        return __r
    @property
    def summary(self):
        __r = '+--- %s, enter or space to expand' % state_dict[self.state]
        return __r

class collapser_label(text_select):
    __slots__ = ()
    no_cache = ['rows']
    context = 'read_mode'
    #def keypress(self, (maxcol,), key):
        #    self._emit('keypress', (maxcol,), key)
        #    return key

class collapser_blank(text_select):
    __slots__ = ()
    ignore_focus = True
    no_cache = ()
    _selectable = False
    context = 'read_mode'


class collapser(MetaMixin, ScrollMixin):
    __slots__ = ('expanded', 'detailed', 'label', '_cache', '_urwid_signals', '__weakref__', 'spacer')
    __metaclass__ = MetaSupSig
    signals = ['focus_modify']
    context = 'read_mode'

    def __init__(self, txt='Loading'):
        self.expanded = False
        self.detailed = False
        self.label = collapser_label(txt)
        self._cache = []

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
        self._kconnect(self.label)
        if hasattr(self, 'spacer'):
            self._kconnect(self.spacer)

    def _fconnect(self, child):
        self._connect('focus_modify', child, self._femit)
    def _femit(self, restore=False):
        self._emit('focus_modify', restore)
    def _femit1(self, mthd, status=None):
        self._emit('focus_modify', mthd, status)

    def update_widget(self):
        if not hasattr(self, 'label'): return
        txt, attr, focus_attr = self.auto_text()
        if type(attr) is str:
            attr = {None: attr}
        if type(focus_attr) is str:
            focus_attr = {None: focus_attr}
        #start_rows = self.label._rows()
        self.label.set_attr_map(attr)
        self.label.set_focus_map(focus_attr)
        self.label.set_text(txt)
        #mod_rows = self.label._rows()
        #if start_rows != mod_rows:
            #emit_signal(eband, 'redisplay')
        #self._modified()

    def auto_text(self): return 'Placeholder text'

    def _do_set_expanded(self, (maxcol,), status=None): self.change_expanded(status)
    def _do_toggle_expanded(self, (maxcol,), key): self.change_expanded(None)
    def _do_open_expanded(self, (maxcol,), key): self.change_expanded(True)
    def _do_close_expanded(self, (maxcol,), key): self.change_expanded(False)

    def _do_set_detailed(self, (maxcol,), status=None):self.change_detailed(status)
    def _do_toggle_detailed(self, (maxcol,), key): self.change_detailed(None)
    def _do_open_detailed(self, (maxcol,), key): self.change_detailed(True)
    def _do_close_detailed(self, (maxcol,), key): self.change_detailed(False)

    def _change_expanded(self, status=None):
        if status is None: self.expanded = not self.expanded
        elif type(status) is bool: self.expanded = status
        if self.detailed and not self.expanded:
            self.detailed = False
        self.update_widget()

    def change_expanded(self, status=None):
        #self._femit('_change_expanded', status)
        self._femit()
        self._change_expanded(status)
        self._femit(True)

    def _change_detailed(self, status=None):
        if status is None: self.detailed = not self.detailed
        elif type(status) is bool: self.detailed = status
        if self.detailed and not self.expanded:
            self.expanded = True
        self.update_widget()

    def change_detailed(self, status=None):
        #self._femit('_change_detailed', status)
        self._femit()
        self._change_detailed(status)
        self._femit(True)

    def __getitem__(self, idx):
        if type(idx) is not int:
            raise TypeError("Index must be an integer.")
        elif idx == 0:
            return self.label
        elif self.expanded:
            if idx == len(self)-1 and hasattr(self, 'spacer'):
                return self.spacer
            elif idx > 0:
                return list.__getitem__(self._cache, idx-1)
            elif idx == -1 and hasattr(self, 'spacer'):
                return self.spacer
            elif idx < 0:
                return list.__getitem__(self._cache, idx-1)
        elif not self.expanded:
            if idx == -1:
                return self.label
            else:
                raise IndexError("Invalid index: %i" % idx)

    def row_len(self):
        tot = self.label.pack()
        if not self.expanded:
            return tot
        else:
            if hasattr(self, 'spacer'):
                tot += self.spacer.pack()
            try:
                mtot = map(lambda x: x.pack(), self._cache)
            except AttributeError:
                mtot = map(lambda x: x.row_len(), self._cache)
            tot += sum(mtot)
            return tot

    def __len__(self):
        if self.expanded:
            if hasattr(self, 'spacer'): v = 2
            else: v = 1
            return list.__len__(self._cache)+v
        else:
            return 1

    def append(self, data):
        list.append(self._cache, data)

class group_state(collapser):
    __slots__ = ('_parent')
    def __init__(self, data, parent):
        self.__super.__init__()
        self._cache.append(data)
        self._parent = parent
        #self.new = new
        if self.state == 'MSG':
            del self.label
            self.label = self.spacer = collapser_blank('', 'blank', 'blank')
            #self.spacer = collapser_label('', 'blank', 'blank')
            self.expanded = True

    @property
    def new(self):
        return self._parent().new

    @property
    def state(self):
        return self._cache[0].state

    def auto_text(self):
        if self.state == 'MSG': return '', 'blank', 'blank'
        focus_attr = 'focus'
        if self.expanded: return self.open, attr_dict[self.state], focus_attr
        else: return self.close, attr_dict[self.state], focus_attr

    @property
    def open(self):
        return '[-]---enter or space to close group of %s' % state_dict[self.state]
    @property
    def close(self):
        return '[+]---Set of (%i) %s, enter or space to expand' % (len(self._cache), state_dict[self.state])

    def do_group_set_expanded(self, *args, **kwargs): return self._do_set_expanded(*args, **kwargs)
    def do_group_toggle_expanded(self, *args, **kwargs): return self._do_toggle_expanded(*args, **kwargs)
    def do_group_open_expanded(self, *args, **kwargs): return self._do_open_expanded(*args, **kwargs)
    def do_group_close_expanded(self, *args, **kwargs): return self._do_close_expanded(*args, **kwargs)

    def do_group_set_detailed(self, *args, **kwargs): return self._do_set_detailed(*args, **kwargs)
    def do_group_toggle_detailed(self, *args, **kwargs): return self._do_toggle_detailed(*args, **kwargs)
    def do_group_open_detailed(self, *args, **kwargs): return self._do_open_detailed(*args, **kwargs)
    def do_group_close_detailed(self, *args, **kwargs): return self._do_close_detailed(*args, **kwargs)

    def do_toggle_expanded(self, *args, **kwargs):
        if self.state == 'MSG':
            return self._kemit(*args, **kwargs)
        return self.do_group_toggle_expanded(*args, **kwargs)

    def do_open_expanded(self, *args, **kwargs):
        if self.state == 'MSG':
            return self._kemit(*args, **kwargs)
        return self.do_group_open_expanded(*args, **kwargs)

    def do_close_expanded(self, *args, **kwargs):
        if self.state == 'MSG':
            return self._kemit(*args, **kwargs)
        return self.do_group_close_expanded(*args, **kwargs)

    #do_set_detailed = do_group_set_detailed
    #do_toggle_detailed = do_group_toggle_detailed
    #do_open_detailed = do_group_open_detailed
    #do_close_detailed = do_group_close_detailed

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
        self.spacer = collapser_blank('', 'blank', 'blank')
        #self.spacer = collapser_label('', 'blank', 'blank')
        #self.spacer = collapser_label('\n', 'blank', 'blank')
        self.__super.__init__()
        self.msgobj = msgobj
        self._state_order = {}
        #if 'S' in msgobj.get('flags', ''): self.new = False
        #else: self.new = True

        __msg_get = mail_grab.get(msgobj.muuid())
        __processed = msg_machine.process(__msg_get)

        if self.new: self._change_detailed(True)
        else: self.update_widget()
        #if self.new: self.update_widget()
        #else: self._change_expanded(False)

        def fadd(p):
            try: self._cache[self._state_order[p[0]]].append(machined_widget(p, ref(self)))
            except KeyError:
                self._state_order[p[0]] = len(self._state_order)
                return fadd(p)
            except IndexError: 
                #try: self._cache.append(group_state(machined_widget(p)))
                try: self._cache[self._state_order[p[0]]] = group_state(machined_widget(p, ref(self)), ref(self))
                except:
                     self._cache.append(group_state(machined_widget(p, ref(self)), ref(self)))
                     #raise ValueError('data: %s\nstate_order: %s\ncache: %s' % (str(p), str(self._state_order), str(self._cache)))

        map(fadd, __processed)
        threadmap.map(lambda x: x.update_widget(), self._cache)

        #insert spacers
        #try: self._cache[self._state_order['MSG']].append(collapser_label('\n', 'blank', 'blank'))
        #except: pass
        #self._cache[-1].append(collapser_label('\n\n', 'blank', 'blank'))

    @property
    def new(self):
        if 'S' in self.msgobj.get('flags', ''): 
            return False
        else:
            return True

    @new.setter
    def new(self, new):
        if type(new) is not bool: raise TypeError("The heck you think you're doing? msg.new can be True or False, not type %s with value %s" % (str(type(new)), str(new)))
        if new:
            id_dat_tple = set_unread(self.msgobj.muuid())
            emit_signal(eband, 'log', str(id_dat_tple))
            if id_dat_tple:
                docs = modify_factory([id_dat_tple], remove_fields)
                map(xconn.replace, docs)
                xconn.flush()

            if self.new: return
            #else: set_unread(self.msgobj.muuid())
            else: self.msgobj.flags.remove('S')
        else:
            id_dat_tple = set_read(self.msgobj.muuid())
            emit_signal(eband, 'log', str(id_dat_tple))
            if id_dat_tple:
                docs = modify_factory([id_dat_tple], update_existing)
                map(xconn.replace, docs)
                xconn.flush()

            if not self.new: return
            self.msgobj.flags.append('S')

    def auto_text(self):
        if self.new: stat = 'new'
        else: stat = 'read'
        focus_attr = 'focus headers'
        if self.detailed: return self.detail, '%s headers' % stat, focus_attr
        else: return self.summary, '%s headers' % stat, focus_attr

    def _get_details(self, __detlist):
        def quack(__field):
            __d = self.msgobj.get(__field, '')
            try: return __d[0]
            except: return __d
        return map(quack, __detlist)

    @property
    def detail(self):
        m = self.msgobj
        #__fd = self._get_details(['sender', 'date', 'recipient', 'cc', 'flags', 'subject'])
        #__r = 'From: %s\nSent: %s\nTo: %s\nCc: %s\nFlags: %s\nSubject: %s' % __fd
        __r = 'From: %s\nSent: %s\nTo: %s\nCc: %s\nFlags: %s\nSubject: %s' % \
                (m.sender(), m.sent(), m.to(), m.cc(), m.flags(), m.subject())
                #(__fd[0], __fd[1], __fd[2], __fd[3], __fd[4], __fd[5])
        return __r
    @property
    def summary(self):
        #__fd = self._get_details(['data', 'sender'])
        #__r = "Sent %s by %s" % __fd
        __r = "Sent %s by %s" % (self.msgobj.sent(), self.msgobj.sender())
        #__r = u"Sent %s by %s" % (__fd[0], __fd[1])
        return __r

    def do_num_rows(self, (maxcol,), key):
        lines = self.label.pack()
        emit_signal(eband, 'log', '%s' % str(lines))

    def top_down_rerender(self):
        def func(x):
            try: map(lambda y: y.update_widget(), x._cache)
            except: pass
        map(func, self._cache)
        map(lambda x: x.update_widget(), self._cache)

    def do_set_read(self, (maxcol,), key):
        emit_signal(eband, 'log', 'in do_set_read, new was %s' % str(self.new))
        self.new = False
        self.top_down_rerender()
        self.update_widget()

    def do_set_unread(self, (maxcol,), key):
        emit_signal(eband, 'log', 'in do_set_unread, new was %s' % str(self.new))
        self.new = True
        self.top_down_rerender()
        self.update_widget()

    def do_msg_set_expanded(self, *args, **kwargs): return self._do_set_expanded(*args, **kwargs)
    def do_msg_toggle_expanded(self, *args, **kwargs): return self._do_toggle_expanded(*args, **kwargs)
    def do_msg_open_expanded(self, *args, **kwargs): return self._do_open_expanded(*args, **kwargs)
    def do_msg_close_expanded(self, *args, **kwargs): return self._do_close_expanded(*args, **kwargs)

    def do_msg_set_detailed(self, *args, **kwargs): return self._do_set_detailed(*args, **kwargs)
    def do_msg_toggle_detailed(self, *args, **kwargs): return self._do_toggle_detailed(*args, **kwargs)
    def do_msg_open_detailed(self, *args, **kwargs): return self._do_open_detailed(*args, **kwargs)
    def do_msg_close_detailed(self, *args, **kwargs): return self._do_close_detailed(*args, **kwargs)

    do_set_expanded = do_msg_set_expanded
    do_toggle_expanded = do_msg_toggle_expanded
    do_open_expanded = do_msg_open_expanded
    do_close_expanded = do_msg_close_expanded

    do_set_detailed = do_msg_set_detailed
    do_toggle_detailed = do_msg_toggle_detailed
    do_open_detailed = do_msg_open_detailed
    do_close_detailed = do_msg_close_detailed

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

class read_box(ListBox):
    __slots__ = ('_urwid_signals', '__size', '_last_top')
    signals = ['modified', 'yank']
    _snap = True
    def __init__(self, convobj):
        self.__size = None
        w = read_walker(convobj, self)
        connect_signal(w, 'yank', self.yank)
        self.__super.__init__(w)
        emit_signal(eband, 'frame_connect', self)

    def modify_focus_valign(self, to_add):
        shft = self.offset_rows + to_add
        self.set_focus_valign(('fixed top', shft))

    def store_top(self):
        middle, (top_offset, top_widgets), bottom = self.calculate_visible(self.__size, True)
        if len(top_widgets):
            top_idx = top_widgets[-1][1]
            if top_offset > 0:
                top_offset = top_offset*-1
                #top_offset = (top_offset-1)*-1
        else:
            top_idx = 0,0,0
            top_offset = 0
        self._last_top = (top_offset, top_idx)

    def restore_top(self):
        cur_focus = self.body.focus
        top_offset, top_idx = self._last_top
        self.change_focus(self.__size, top_idx, top_offset)
        self.set_focus(cur_focus)

    #def change_focus(self, size, position, offset_inset = 0, coming_from = None, cursor_coords = None, snap_rows = None):
        #    emit_signal(eband, 'log', 'size: %s\npos: %s\nrow_offset: %s' % (str(size), position, offset_inset))
        #    return self.__super.change_focus(size, position, offset_inset, coming_from, cursor_coords, snap_rows)

    def yank(self, size=None):
        emit_signal(eband, 'log', str(self.__size))
        emit_signal(eband, 'log', str(self.offset_rows))
        emit_signal(eband, 'log', str(self.get_focus()))
        vis = self.calculate_visible(self.__size, True)
        emit_signal(eband, 'log', 'middle:\n%s' % str(vis[0]))
        emit_signal(eband, 'log', 'top:\n%s' % str(vis[1]))
        emit_signal(eband, 'log', 'bottom:\n%s' % str(vis[2]))
        #cur_focus = self.body.focus
        #self.change_focus(self.__size, (4,1,1), -2)
        #self.set_focus(cur_focus)
        #self.modify_focus_valign(6)
        #self.set_focus_valign(('fixed top', 6))
        #self._invalidate()

    def render(self, size, focus=False):
        if self.__size != size: self.__size = size
        return self.__super.render(size, focus)

    def _invalidate(self):
        emit_signal(self, 'modified')
        return self.__super._invalidate()

class read_walker(ListWalker, MetaMixin):
    __slots__ = ('_cache', 'focus', '_listbox', '_last_focus')
    signals = ['yank', 'focus_modify']
    context = 'read_mode'
    def __init__(self, convobj, box):
        def quack(__x):
            __x.allconn_4cache()

        self._listbox = ref(box)
        self._cache = map(message_widget, convobj.messages)
        map(quack, self._cache)
        map(self.all_connect, self._cache)
        self.focus = 0, 0, 0
        self.find_oldest_new()

        emit_signal(eband, 'log', str(self._listbox()))
        emit_signal(eband, 'log', str(dir(self._listbox())))

    def _fconnect(self, child):
        self._connect('focus_modify', child, self._focus_modify)
    def _femit(self, restore=False):
        self._emit('focus_modify', restore)
    def _femit1(self, mthd, status=None):
        self._emit('focus_modify', mthd, status)

    def _focus_modify(self, restore=False):
        #emit_signal(eband, 'log', 'doing focus modifier')
        if restore:
            return self._listbox().restore_top()
            #return self._listbox().set_focus(self._last_focus)
        else:
            return self._listbox().store_top()
            #cur_focus = self.focus
            #self._last_focus = cur_focus
            #return self._listbox().set_focus((cur_focus[0], 0, 0))

    def _focus_modify1(self, mthd, status=None):
        emit_signal(eband, 'log', 'doing focus modifier, %s' % str(self.focus))
        beg_focus = self.focus
        #if beg_focus == (0,0,0): raise TypeError
        self._listbox().set_focus((beg_focus[0], 0, 0))
        #self.set_focus((beg_focus[0], 0, 0))

        cllps = self._cache[beg_focus]
        getattr(cllps, mthd)(status)

        return self._listbox().set_focus(beg_focus)

    def do_yank(self, (maxcol,), key):
        #emit_signal(self, 'yank', (maxcol,))
        #self.find_next_new()
        self.collapse_read()

    def expand_all(self):
        map(lambda x: x._change_expanded(True), self._cache)

    def collapse_all(self):
        convpos, msgpos, statepos = self.focus
        def func((idx, msg)):
            if idx != convpos:
                msg._change_expanded(False)

        map(func, enumerate(self._cache))

    def collapse_read(self):
        convpos, msgpos, statepos = self.focus
        def func((idx, msg)):
            if not msg.new and idx != convpos:
                msg._change_expanded(False)

        map(func, enumerate(self._cache))

    def find_oldest_new(self):
        self.find_next_new(start_from=(-1,0,0))

    def find_next_new(self, start_from=None):
        if start_from: convpos, msgpos, statepos = start_from
        else:
            convpos, msgpos, statepos = self.focus
        convpos += 1
        for __w in self._cache[convpos:]:
            if __w.expanded: break
        try: __w._change_detailed(True)
        except UnboundLocalError: return
        convpos = self._cache.index(__w)
        #self._listbox().set_focus_valign(('fixed top', 0))
        self.set_focus((convpos, 0, 0), ('fixed top', 0))

    def get_next_msg(self):
        convpos, msgpos, statepos = self.focus
        if convpos < (len(self._cache)-1):
            convpos += 1
            self.set_focus((convpos, 0, 0), ('fixed top', 0))

    def get_prev_msg(self):
        convpos, msgpos, statepos = self.focus
        if convpos > 0:
            convpos -= 1
            self.set_focus((convpos, 0, 0), ('fixed top', 0))

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
        try: __w = self._cache[convpos][msgpos][statepos]
        except IndexError:
            return self.get_next(self.focus)
        return __w, self.focus

    def set_focus(self, focus, valign=None):
        convpos, msgpos, statepos = focus
        self.focus = convpos, msgpos, statepos
        if valign:
            self._listbox().set_focus_valign(valign)
        self._modified()

    def get_next(self, start_from):
        convpos, msgpos, statepos = start_from
        def mdef(convpos, msgpos, statepos):
            return self._cache[convpos][msgpos][statepos], (convpos, msgpos, statepos)
        try: return mdef(convpos, msgpos, statepos+1)
        except IndexError:
            try: return mdef(convpos, msgpos+1, 0)
            except AttributeError:
                return mdef(convpos, msgpos+1, 1)
            except IndexError:
                try: return mdef(convpos+1, 0, 0)
                except AttributeError:
                    #no self.label
                    return mdef(convpos+1, 0, 1)
                except IndexError:
                    return None, None

    def get_prev(self, start_from):
        convpos, msgpos, statepos = start_from
        def mdef(convpos, msgpos, statepos):
            if msgpos == -1:
                msgpos = len(self._cache[convpos])-1
            if statepos == -1:
                try: statepos = len(self._cache[convpos][msgpos])-1
                except TypeError:
                    try: statepos = len(self._cache[convpos][msgpos+1])-1
                    except:
                        statepos = len(self._cache[convpos][msgpos-1])-1
            pos = (convpos, msgpos, statepos)
            try: w = self._cache[convpos][msgpos][statepos]
            except IndexError:
                return self.get_prev(pos)
            return w, pos
            #return self._cache[convpos][msgpos][statepos], (convpos, msgpos, statepos)

        if statepos == 0:
            if msgpos == 0:
                if convpos == 0:
                    return None, None
                return mdef(convpos-1, -1, -1)
            return mdef(convpos, msgpos-1, -1)
        try: return mdef(convpos, msgpos, statepos-1)
        except AttributeError:
            #no self.label
            return mdef(convpos, msgpos-1, -1)
