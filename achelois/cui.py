#!/usr/bin/python

import urwid.curses_display
import urwid
import collections
import tools

import lazythread
import index

import weakref

from buffer import buffer_manager
from offlinemaildir import mail_sources
from message_machine import chunkify

from achelois.lib.view-util import callback_list

import email, mailbox
#from weakkeyordereddict import WeakKeyOrderedDict

#import imapthread

mymail = mail_sources()
state_mech = chunkify()

class conv_repr(dict):
    __metaclass__ = urwid.MetaSignals
    signals = ['keypress']

    def __init__(self, msgids, subjects, labels, messages):
        self.widget = conv_widget('Loading')
        urwid.Signals.connect(self.widget, 'keypress', self.load_msg)

        self['msgids'] = msgids
        self['subjects'] = subjects
        self['labels'] = labels
        self['messages'] = callback_list(self.update_widget)
        self['messages'].extend(messages)
        
        #becuse attributes are fun
        self.msgids = self['msgids']
        self.subjects = self['subjects']
        self.messages = self['messages']
        self.labels = self['labels']

        #self.selectable = self.widget.selectable
        #self.render = self.widget.render
        #self.rows = self.widget.rows

    #def __hash__(self): return id(self)

    def update_widget(self):
        self.widget.set_label(self.__repr__())
        try: urwid.Signals.emit(screen.thread.threadList, "modified")
        except: pass

    def load_msg(self):
        #msg_get = (mymail.get(x['muuid']) for x in self.messages)
        #bodies = (u' '.join([m.get_payload(decode=True) for m in email.iterators.typed_subpart_iterator(msg) if 'filename' not in m.get('Content-Disposition','')]) for msg in messages)
        self.msg_collection = []

        def plaintext(chunk):
            for state,part in chunk:
                if 'MSG' in state: generic(part)
                else: consolation_prize(part)
        def generic(chunk):
            self.msg_collection.append(urwid.Text(chunk))
        def consolation_prize(chunk):
            self.msg_collection.append(urwid.Text('pretend collapse'))

        for msg in self.messages:
            if self.msg_collection: generic('\n\n')
            msg_get = mymail.get(msg['muuid'])
            res = state_mech.process(msg_get)
            '''msg_stats = u'From: %s\nSent: %s\n%To: %s\n%Cc:\nSubject: %s' % \
                    (msg['from'], tools.unidecode_date(msg['date']), msg['recipient'], msg['cc'], msg['subject'])
                    '''
            msg_headers = u'From: %s\nSent: %s\nTo: %s\nSubject: %s\n\n' % \
                    (msg['sender'], tools.unidecode_date(msg['date']), msg['recipient'], msg['subject'])
            machine_mesg = [tuple(['HEADER', msg_headers])]
            machine_mesg.extend(res)
            for state, chunk in machine_mesg:
                if 'PLAINTXT' in state: plaintext(chunk)
                elif 'HEADER' in state: generic(chunk)
                else: consolation_prize(chunk)

        #widgetize = [urwid.Text(txt) for txt in bodies]
        buffer_manager.set_buffer(urwid.PollingListWalker(self.msg_collection))

    def __repr__(self):
        self.ddate = self['messages'][-1]['date']
        self.dsender = u','.join([x['sender'].split()[0].strip('"') for x in self['messages'][-3:]])
        self.dcontained = len(self['messages'])
        self.dsubject = lazythread.stripSubject(self['messages'][-1].get(u'subject',u''))
        self.dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        self.dpreview = u' '.join(self['messages'][-1].get(u'content',u'').split())
        self.disprender = "%s   %s   %i   %s %s %s" % \
            (self.ddate, self.dsender, self.dcontained, self.dsubject, self.dlabels, self.dpreview)
        return self.disprender

state_dict = {
            'BLOCK': 'block quote',
            'HTML': 'html-encoded text',
            'QUOTE': 'quotted text',
            'DUNNO': 'not sure what block is',
            'ATTACHMENT': 'attached file',
            }


class conversation_widget(urwid.WidgetWrap):
    ''' This widget is not meant for direct use.
    conv is the conv_repr.messages of the particular conversation
    msg is the return from the index for the message we're on
    mindex is index of the msg we're on in conv
    index is the position in the results from the state machine
    display are the contents of the state we're in
    '''

    def __init__(self, conv, msg=None, mindex=0, index=None, display=None):
        self.conv = conv
        self.msg = msg
        self.mindex = mindex
        self.index = index

        if not msg:
            self.msg = self.conv[0]

        if not display: display = 'Loading'
        widget = urwid.Text(display)
        self.widget = widget
        w = urwid.AttrWrap(widget, None)
        self.__super.__init__(w)

    def selectable(self):
        return True

    def keypress(self, (maxcol,), key):
        return key

    def first_part(self):
        return None

    def last_part(self):
        return None

    def next_inorder(self):
        part = self.first_part()
        if part: return part
        if self.index is not None:
            #from here find cached message_widget
            return 
        try: return self.conv[self.mindex+1]
        except: return None

    def prev_inorder(self):
        if self.mindex == 0: return None
        try: return self.conv[self.mindex-1]
        except: return None


def get_cached_message(index):
    try: return _message_cache[index]
    except: return message_widget

class display_conversation(object):
    _inst_buffers = weakref.WeakKeyDictionary

    @classmethod
    def get_conv(cls, conv):
        try: _inst_buffers[conv]
        except:
            _inst_buffers.setdefault(conv,[])

class machined_widget(conversation_widget):
    def __init__(self, conv, msg, mindex, index, contents):
        state, part = contents
        self.state = state
        self.contents = part
        if state == 'MSG':
            self.expanded = True
        else:
            self.expanded = False
        self.__super.__init__(conv, index, msg)
        self.update_widget()

    def update_widget(self):
        if self.expanded:
            display = self.contents
        else:
            display = '+--- %s, enter or space to expand' % state_dict[self.state]
        self.widget.set_text(display)

class message_widget(conversation_widget):
    def __init__(self, conv, msg, mindex, index=None):
        #FIXME: add in support for labels and Cc targets
        self.headers = u'From: %s\nSent: %s\nTo: %s\nSubject: %s\n\n' % \
                (msg['sender'], tools.unidecode_date(msg['date']), msg['recipient'], msg['subject'])
        self._cache = None

        if 'S' in msg['flags']:
            self.expanded = False
        else:
            self.expanded = True

        self.__super.__init__(conv, index, msg)
        self.update_widget()

    def update_widget(self):
        if self.expanded:
            display = self.headers
        else:
            display = u"%s %s %s" % \
                (tools.unidecode_date(msg['date']), msg['sender'], msg['subject']))
        self.widget.set_text(display)

    def keypress(self, (maxcol,), key):
        if key in (" ", "enter"):
            self.expanded = not self.expanded
            self.update_widget()
        else:
            return self.__super.keypress((maxcol,), key)

    @property
    def machined(self):
        if not self._cache:
            self._cache = self._process()
        return self._cache

    def _process(self):
        msg_get = mymail.get(self.msg['muuid'])
        res = state_mech.process(msg_get)
        return res

    def first_part(self):
        if not self.expanded:
            return None
        return self.machined[0]

    def last_part(self):
        if not self.expanded:
            return None
        return self.machined[-1]


class conv_widget(urwid.Button):
    __metaclass__ = urwid.MetaSignals
    signals = ['keypress']

    def set_label(self, label):
        self.label = label
        self.w = urwid.Text( label, wrap='clip' )
        '''self.w-no = urwid.Columns([
            ('fixed', 1, self.button_left),
            urwid.Text( label ),
            ('fixed', 1, self.button_right)],
            dividechars=1)
            '''
        self._invalidate()

    def update_w(self):
        if self.selected:
            self._w.attr = 'selected'
            self._w.focus_attr = 'selected focus'
        else:
            self._w.attr = 'body'
            self._w.focus_attr = 'focus'

    def keypress(self, (maxcol,), key):
        if key not in (' ','enter'):
            return key
        urwid.Signals.emit(self, 'keypress')

lazythread.convContainer = conv_repr


class thread_walker(urwid.SimpleListWalker):
    def get_focus(self):
        if len(self) == 0: return None, None
        return self[self.focus].widget, self.focus

    def get_next(self, start_from):
        pos = start_from + 1
        if len(self) <= pos: return None, None
        return self[pos].widget, pos

    def get_prev(self, start_from):
        pos = start_from - 1
        if pos < 0: return None, None
        return self[pos].widget, pos

class thread_index(urwid.ListBox): pass
class info_log(urwid.ListBox): pass
class view_conversation(urwid.ListBox): pass
class info_log_list(collections.deque):
    def __hash__(self): return id(self)

class Screen(object):
    __metaclass__ = urwid.MetaSignals
    signals = ['buffer_update']

    palette = [
            ('body', 'light gray', 'black'),
            ('selected', 'white', 'black', ('bold')),
            ('focus', 'light blue', 'black', ('bold')),
            ('selected focus', 'light cyan', 'black', ('bold')),
            ]
    def __init__(self, tui):
        self.tui = tui
        self.tui.register_palette(self.palette)
        self.result_machine = index.result_machine()
        self.unsortlist = self.result_machine.search('*', sortkey=u'date', resultlimit=50000000)
        self.thread = lazythread.lazy_thread()
        #urwid.Signals.connect(buffer_manager, 'buffer_update', set_buffer)

    def addLine(self, text):
        self.lines.append(urwid.Text(text))
        self.listbox.set_focus(len(self.lines) - 1)
        self.redisplay()

    def addLine2(self, text):
        self.lines2.append(urwid.Text(text))
        self.listbox2.set_focus(len(self.lines2) - 1)
        self.redisplay()

    def redisplay(self):
        canvas = self.frame.render(self.size, focus=True)
        self.tui.draw_screen(self.size, canvas)

    def set_buffer(self, buffer):
        self.frame.set_body(buffer)
        self.focused_listbox = buffer

    def run(self):
        self.size = self.tui.get_cols_rows()
        a = urwid.PollingListWalker([x for x in xrange(2)])

        #self.summarytxt = urwid.Text('inbox, blalkjsdfn %i threads' % len(self.thread), align='left')
        self.summarytxt = urwid.Text('inbox, blalkjsdfn number threads', align='left')
        self.input = urwid.Edit()
        self.bframe = urwid.Pile([self.summarytxt, self.input])
        self.body_loading = urwid.ListBox([urwid.Text('Loading....')])

        self.frame = urwid.Frame(self.body_loading, footer=self.bframe)
        self.frame.set_focus('body')

        #buffer_manager.register_rootobj(self.frame.set_body)
        buffer_manager.register_rootobj(self.set_buffer)

        self.lines = None
        self.lines2 = info_log_list([urwid.Text('Hello2')],500)
        self.thread.threadList = thread_walker([])
        buffer_manager.register_support(self.thread.threadList, thread_index)
        buffer_manager.register_support(self.lines2, info_log)
        buffer_manager.register_support(a, view_conversation)
        del a

        #self.listbox = urwid.ListBox(self.thread.threadList)
        #self.listbox2 = urwid.ListBox(self.lines2)
        self.listbox = buffer_manager.set_buffer(self.thread.threadList)
        self.listbox2 = buffer_manager.get_buffer(self.lines2)
        buffer_manager.register_noremove(self.listbox)
        buffer_manager.register_noremove(self.listbox2)


        self.redisplay()
        #imapthread._thread_init(self.addLine2)
        self.c = 0
        self.unsortlist = list(self.unsortlist)
        self.unsortlist.reverse()
        self.thread.thread(self.unsortlist[500*self.c:500*(self.c+1)])
        self.redisplay()

        self.focused_listbox = self.listbox

        while 1:
            keys = self.tui.get_input()

            for key in keys:
                if key == 'window resize':
                    self.size = self.tui.get_cols_rows()
                elif key in ('up', 'down', 'page up', 'page down'):
                    self.focused_listbox.keypress(self.size, key)
                elif key == 'f1':
                    #self.frame.set_body(self.listbox)
                    #self.listbox = buffer_manager.set_buffer(self.thread.threadList)
                    buffer_manager.set_buffer(self.thread.threadList)
                    #self.focused_listbox = self.listbox
                elif key == 'f2':
                    #self.frame.set_body(self.listbox2)
                    #self.listbox2 = buffer_manager.set_buffer(self.lines2)
                    buffer_manager.set_buffer(self.lines2)
                    #self.focused_listbox = self.listbox2
                elif key == 't':
                    self.c += 1
                    self.thread.thread(self.unsortlist[500*self.c:500*(self.c+1)])
                else:
                    self.frame.keypress(self.size, key)

                self.redisplay()

if __name__ == '__main__':
    tui = urwid.curses_display.Screen()
    screen = Screen(tui)
    tui.run_wrapper(screen.run)
