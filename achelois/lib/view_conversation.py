from achelois.lib.message_machine import msg_machine
from achelois import offlinemaildir
from achelois import tools

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


class message_machine(list):
    def __init__(self, conv, mindex, muuid):
        self.muuid = muuid
        msg_get = mymail.get(muuid)
        processed = msg_machine.process(msg_get)
        self.extend((machined_widget(conv, mindex, idx, data) for idx,data in enumerate(processed)))


class conversation_cache(object):
    #__metaclass__ = urwid.MetaSignals
    #signals = ['log']
    #_inst_buffers = weakref.WeakKeyDictionary()
    _inst_buffers = {}

    @classmethod
    def destroy(cls, conv):
        try: del cls._inst_buffers[conv]
        except KeyError: pass

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


class conversation_widget(urwid.WidgetWrap):
    ''' This widget is not meant for direct use.
    conv is the conv_repr.messages of the particular conversation
    mindex is index of the msg we're on in conv
    index is the position in the results from the state machine
    display are the contents of the state we're in
    '''

    def __init__(self, conv, mindex=0, index=None, attr=None, focus_attr=None):
        self.conv = conv
        self.mindex = mindex
        self.index = index

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
        #elif key == 'x':
            #buffer_manager.destroy()
            #conversation_cache.destroy(self.conv)
        else:
            return key

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


class machined_widget(conversation_widget):
    def __init__(self, conv, mindex, index, contents):
        state, part = contents
        self.state = state
        self.contents = '\n%s' % part
        if state == 'MSG':
            self.expanded = True
            attr = 'new msg'
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


class message_widget(conversation_widget):
    def __init__(self, conv, mindex):
        msg = conv[mindex]
        #FIXME: add in support for labels and Cc targets
        self.headers = u'From: %s\nSent: %s\nTo: %s\nSubject: %s' % \
                (msg['sender'], tools.unidecode_date(msg['date']), msg['recipient'], msg['subject'])
        self.condensed = u"%s %s %s" % \
                (tools.unidecode_date(msg['date']), msg['sender'], msg['subject'])
        self._cache = None

        try:
            if 'S' in msg['flags']:
                self.expanded = False
            else:
                self.expanded = True
        except: self.expanded = True

        self.__super.__init__(conv, mindex, None, 'new headers', 'focus headers')
        self.update_widget()

    def update_widget(self):
        if self.expanded:
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


class read_walker(urwid.ListWalker):
    def __init__(self, conv):
        #begin = conversation_cache.get_part(conv, 0, None)
        for n in xrange(len(conv)):
            try:
                try: trashvar = conversation_cache.get_part(conv, n, 0)
                except: trashvar = conversation_cache.get_part(conv, n, None)
            except: pass
        self.conv = conv
        self.focus = 0, None

    def __del__(self):
        assert 0 == 1
        conversation_cache.destroy(self.conv)

    def get_focus(self):
        msgidx, stateidx = self.focus
        widget = conversation_cache.get_part(self.conv, msgidx, stateidx)
        return widget, self.focus

    def set_focus(self, focus):
        msgidx, stateidx = focus
        self.focus = msgidx, stateidx
        self._modified()

    def get_next(self, start_from):
        msgidx, stateidx = start_from
        widget = conversation_cache.get_part(self.conv, msgidx, stateidx)
        next_up = widget.next_inorder()
        if next_up is None:
            return None, None
        return next_up, (next_up.mindex, next_up.index)

    def get_prev(self, start_from):
        msgidx, stateidx = start_from
        widget = conversation_cache.get_part(self.conv, msgidx, stateidx)
        prev_up = widget.prev_inorder()
        if prev_up is None:
            return None, None
        return prev_up, (prev_up.mindex, prev_up.index)
