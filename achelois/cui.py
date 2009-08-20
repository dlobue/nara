#!/usr/bin/python

import urwid.curses_display
import urwid
from urwid import ListWalker
from buffer import buffer_manager
import collections
import weakref
from datetime import datetime, timedelta
from email.utils import getaddresses
from operator import itemgetter

from lazythread import convContainer

import xappy
import lazythread
#import index
from achelois.lib import util
#from achelois.lib.view_util import callback_list
#from curwalk import cursor_walk
#from achelois.lib.view_conversation import read_walker, conversation_cache

from achelois.lib.message_machine import msg_machine
from achelois import offlinemaildir
from achelois import tools

from string import ascii_lowercase, digits, maketrans
anonitext = maketrans(ascii_lowercase + digits, 'x'*26 + '7'*len(digits))

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

#import imapthread

class id_list(list):
    def __hash__(self): return id(self)
    def __getitem__(self, idx):
        return list.__getitem__(self,idx)[1]
    def __getslice__(self, beg, end):
        return map(itemgetter(1), list.__getslice__(self,beg,end))

class conv_repr(object):
    #{{{
    __metaclass__ = urwid.MetaSignals
    signals = ['keypress']

    #widget = conv_widget('Loading')

    def __init__(self, dataobj):
    #def __init__(self, msgids, subjects, labels, messages):
        self.widget = conv_widget('Loading')
        urwid.Signals.connect(self.widget, 'keypress', self.load_msg)

        #self['msgids'] = msgids
        #self['subjects'] = subjects
        #self['labels'] = labels
        #self['messages'] = callback_list(self.update_widget)
        #self['messages'].extend(messages)
        #self['messages'] = id_list(messages)
        
        #becuse attributes are fun
        self.dataobj = dataobj
        self.msgids = dataobj.msgids
        self.subjects = dataobj.subjects
        self.messages = id_list(dataobj.messages)
        self.labels = dataobj.labels

        self.update_widget()

        #self.selectable = self.widget.selectable
        #self.render = self.widget.render
        #self.rows = self.widget.rows

    #def __hash__(self): return id(self)

    @property
    def id(self):
        return self.dataobj.id

    @property
    def last_update(self):
        return self.messages[-1]['date']

    def update_widget(self):
        #self.widget.set_label(self.__repr__())
        self.widget.set_label(self.idx_repr())
        #try: urwid.Signals.emit(screen.thread.threadList, "modified")
        #except: pass

    def load_msg(self):
        __s = self.messages
        try: buffer_manager.set_buffer(__s)
        except:
            buffer_manager.register_support(__s, view_conversation)
            buffer_manager.set_buffer(__s)

    def idx_repr(self):
        def chk_new(x):
            if type(x) is tuple: x = x[1]
            if 'S' in x['flags']: return False
            return True

        __tot_new = len(filter(chk_new,self.messages))
        if __tot_new:
            __tstat = 'new'
        else:
            __tstat = 'read'

        __now = datetime.now()
        __ddate = self.messages[-1]['date'][0]
        if __now.date() == __ddate.date():
            __rep_date = __ddate.strftime('%X')
        elif __now.year > __ddate.year:
            __rep_date = __ddate.strftime('%y %b %d')
        else:
            __yest = __now - timedelta(days=1)
            if __yest.date() == __ddate.date():
                __rep_date = __ddate.strftime('Yest %X')
            else:
                __rep_date = __ddate.strftime('%b %d')

        __ddate = ('new index', __rep_date)

        def sender_markup(x):
            if type(x) is tuple: x = x[1]
            if 'S' not in x['flags']: __stat = 'new'
            else: __stat = 'read'
            __fname = x['sender'][0].split()[0].strip('"')
            return ('%s index' % __stat, '%s,' % __fname)

        if __tot_new < 3:
            if __tot_new == 0: __idx = -1
            __dsender = filter(chk_new, self.messages)
            __dsender.extend([x for x in self.messages[-(3 - __tot_new):]])
            #__dsender = [x for x in self['messages'][-(3 - __tot_new):]]
        else:
            __idx = 0
            __dsender = [x for x in self.messages if 'S' not in x[1]['flags']][:3]

        try: __idx
        except:
            try: __oldest_new = filter(chk_new, __dsender)[0]
            except IndexError:
                screen.tui.stop()
                print __tot_new
                print len(filter(chk_new, __dsender))
                print len(self.messages)
                import sys
                sys.exit()
        else:
            __oldest_new = __dsender[__idx]
        if type(__oldest_new) is tuple: __oldest_new = __oldest_new[1]
        __dsubject = ('%s index' % __tstat, __oldest_new.get('subject','')[0])
        __dpreview = ('index sample', ' '.join(__oldest_new.get('sample','')[0].split()))

        __dsender = map(sender_markup, __dsender)
        __send_caboose = __dsender.pop()
        try: __dsender.append((__send_caboose[0], __send_caboose[1].strip(',')))
        except:
            screen.tui.stop()
            print __dsender
            import sys
            sys.exit()


        __dcontained = ('%s index' % __tstat, '%i' % len(self.messages))
        __dlabels = ('index label', ' '.join('+%s' % x for x in self.labels))

        return (__ddate, __dsender, __dcontained, __dsubject, __dlabels, __dpreview)

    def __repr__(self):
        __ddate = self.messages[-1]['date'][0]
        #__ddate = self['messages'][-1][-1]['date'][0]
        __dsender = ','.join([x['sender'][0].strip('"') for x in self.messages[-3:]])
        #__dsender = u','.join([x[-1]['sender'][0].strip('"') for x in self['messages'][-3:]])
        __dcontained = len(self.messages)
        __dsubject = self.messages[-1].get(u'subject',u'')
        #__dsubject = self['messages'][-1][-1].get(u'subject',u'')
        __dlabels = ' '.join(u'+%s' % x for x in self.labels)
        __dpreview = ' '.join(self.messages[-1].get(u'content',u'').split())
        #__dpreview = u' '.join(self['messages'][-1][-1].get(u'content',u'').split())
        __disprender = "%s   %s   %i   %s %s %s" % \
            (__ddate, __dsender, __dcontained, __dsubject, __dlabels, __dpreview)
        return __disprender
    #}}}

class conv_widget(urwid.WidgetWrap):
    #{{{
    __metaclass__ = urwid.MetaSignals
    signals = ['keypress']

    def selectable(self): return True

    def __init__(self, label):
        self.__super.__init__(None)
        self.set_label( label )

    def set_label(self, label):
        #w = urwid.Text( label, wrap='clip' )
        def privatize_txt(x):
            if type(x) is list:
                return map(privatize_txt, x)
            if type(x) is tuple and len(x) == 2:
                return (x[0], x[1].translate(anonitext))

        self.label = label
        if type(label) is tuple:
            #label = map(privatize_txt, list(label))

            __ddate = label[0]
            __ddate = urwid.Text(__ddate, align='right')
            __dsender = label[1]
            __dsender = urwid.Text(__dsender, wrap='clip')
            #__dsender = urwid.AttrWrap( urwid.Text(__dsender[1], align='left', wrap='clip'), __dsender[0], 'focus')
            __dcontained = label[2]
            __dcontained = urwid.Text(__dcontained, align='center')
            #__dsubject = label[3]
            #__dsubject = urwid.AttrWrap( urwid.Text(__dsubject[1], wrap='clip'), __dsubject[0], 'focus')
            #__dlabels = label[4]
            #__dlabels = urwid.AttrWrap( urwid.Text(__dlabels[1], wrap='clip'), __dlabels[0], 'focus')
            #__dpreview = label[5]
            #__dpreview = urwid.AttrWrap( urwid.Text(__dpreview[1], wrap='clip'), __dpreview[0], 'focus')
            __rest = list(label[3:])
            if not __rest[-1][1]: del __rest[-1]
            if not __rest[1][1]: del __rest[1]
            __rest = urwid.Text(__rest, wrap='clip')
    

            w = urwid.Columns([
                ('fixed', 10, __ddate),
                ('fixed', 25, __dsender),
                ('fixed', 5, __dcontained),
                __rest],
                dividechars=1, min_width=4)
    
            #__l = list(label)
            #if not __l[-2][1]: del __l[-2]
            #if not __l[-1][1]: del __l[-1]
            #w = urwid.Text(__l, wrap='clip')

            #w = urwid.WidgetWrap(w)
                #urwid.Text( label[4], wrap='clip' ),
                #urwid.Text( label[5], wrap='clip' )],

        else:
            #if type(label) is str:
                #label = label.translate(anonitext)
            #else: label = str(type(label))
            w = urwid.Text(label, wrap='clip')

        #self.w = urwid.AttrWrap( w, 'body', 'focus' )
        self.w = urwid.AttrWrap( w, 'body', 'index focus' )
        self._invalidate()

    def get_label(self):
        return self.label

    def keypress(self, (maxcol,), key):
        if key not in (' ','enter'):
            return key
        urwid.Signals.emit(self, 'keypress')
        #}}}

#lazythread.convContainer = conv_repr

class monkey_thread(lazythread.lazy_thread):
    #{{{
    __metaclass__ = util.MetaSuper

    def merge(self, found, workobj):
        self.__super.merge(found, workobj)
        #workobj.update_widget()

    def append(self, data):
        self.__super.append(data)
        #data.update_widget()
        #}}}

class cursor_walk(ListWalker):
    #{{{
    def __init__(self, bdb):
        self.bdb = bdb
        self.cursor = bdb.cursor()
        try: self.focus = self.cursor.first()[0]
        except: self.focus = None

    def __hash__(self): return id(self)

    def _modified(self):
        ListWalker._modified(self)

    def get_focus(self):
        if len(self.bdb) == 0: return None, None
        try: __cur = self.cursor.current()
        except: __cur = self.cursor.first()
        return conv_repr(__cur[1]).widget, __cur[0]

    def set_focus(self, position):
        self.cursor.set(position)
        self._modified()

    def get_next(self, start_from):
        __cur = self.cursor.current()
        if __cur != start_from:
            self.cursor.set(start_from)
        try:
            __ncur = self.cursor.next()
            return cov_repr(__ncur[1]).widget, __ncur[0]
        except:
            return None, None

    def get_prev(self, start_from):
        __cur = self.cursor.current()
        if __cur != start_from:
            self.cursor.set(start_from)
        try:
            __ncur = self.cursor.prev()
            return cov_repr(__ncur[1]).widget, __ncur[0]
        except:
            return None, None
        #}}}

class thread_walker(urwid.SimpleListWalker):
    #{{{
    def get_focus(self):
        if len(self) == 0: return None, None
        return conv_repr(self[self.focus]).widget, self.focus

    def get_next(self, start_from):
        pos = start_from + 1
        if len(self) <= pos: return None, None
        return conv_repr(self[pos]).widget, pos

    def get_prev(self, start_from):
        pos = start_from - 1
        if pos < 0: return None, None
        return conv_repr(self[pos]).widget, pos
    #}}}

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

class message_widget(conversation_widget):
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

class read_walker(urwid.ListWalker):
    #{{{
    def __init__(self, conv):
        for n in xrange(len(conv)):
            try:
                try: trashvar = conversation_cache.get_part(conv, n, 0)
                except: trashvar = conversation_cache.get_part(conv, n, None)
            except: pass
        self.conv = conv
        self.focus = 0, None
        self.find_oldest_new()

    def self_destruct(self):
        conversation_cache.destroy(self.conv)

    def find_oldest_new(self):
        msgidx, stateidx = self.focus
        while 1:
            #try:
            print self.conv
            widget = conversation_cache.get_part(self.conv, msgidx, None)
            #except: break
            if widget.expanded: break
            msgidx += 1
        newfocus = widget.mindex, None
        return self.set_focus(newfocus)

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
    #}}}

class thread_index(urwid.ListBox): pass
class info_log(urwid.ListBox): pass
class view_conversation(urwid.ListBox):
    def __init__(self, body):
        self.conv = body
        self.__super.__init__(read_walker(body))

    def self_destruct(self):
        conversation_cache.destroy(self.conv)
        self._invalidate()

class info_log_list(collections.deque):
    def __hash__(self): return id(self)


keymap_alias = {'k':'up', 'j':'down', 'h':'left', 'l':'right', 'J':'page down', 'K':'page up'}

class Screen(object):
    __metaclass__ = urwid.MetaSignals
    signals = ['log','buffer_update']

    palette = [
            ('body', 'light gray', 'black'),
            ('selected', 'white', 'black', ('bold')),
            ('focus', 'light blue', 'black', ('bold')),
            ('index focus', 'black', 'light gray', ('bold')),
            ('selected focus', 'light cyan', 'black', ('bold')),
            ('test', 'yellow', 'dark cyan'),
            ('status', 'white', 'dark blue'),
            ('read headers', 'black', 'dark blue'),
            ('new headers', 'black', 'dark green', ('standout')),
            ('focus headers', 'white', 'dark cyan'),
            ('read msg', 'light gray', 'black'),
            ('new msg', 'white', 'black'),
            ('attachment', 'dark green', 'black'),
            ('block quote', 'brown', 'black'),
            ('dunno', 'light magenta', 'black'),
            ('html', 'light green', 'black'),
            ('new index', 'white', 'black'),
            ('read index', 'light gray', 'black'),
            ('starred index', 'yellow', 'black'),
            ('index label', 'brown', 'black'),
            ('index sample', 'dark cyan', 'black'),
            ]
    def __init__(self):
        #self.tui = tui
        #self.tui.register_palette(self.palette)
        #self.result_machine = index.result_machine()
        self.thread = monkey_thread()
        #self.thread = lazythread.lazy_thread()

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

    def main(self):
        self.tui = urwid.curses_display.Screen()
        self.tui.register_palette(self.palette)
        self.tui.run_wrapper(self.run)

    def run(self):
        self.size = self.tui.get_cols_rows()
        cols, rows = self.size

        #self.summarytxt = urwid.Text('inbox, blalkjsdfn %i threads' % len(self.thread), align='left')
        summarytxt = urwid.Text('inbox, blalkjsdfn number threads', align='left')
        self.summarytxt = urwid.AttrWrap(summarytxt, 'status')
        self.input = urwid.Edit()
        self.bframe = urwid.Pile([self.summarytxt, self.input])
        self.body_loading = urwid.ListBox([urwid.Text('Loading....')])

        self.frame = urwid.Frame(self.body_loading, footer=self.bframe)
        self.frame.set_focus('body')

        #buffer_manager.register_rootobj(self.frame.set_body)
        buffer_manager.register_rootobj(self.set_buffer)

        self.lines = None
        self.lines2 = info_log_list([urwid.Text(('test','hello2'))],500)
        self.thread.threadList = thread_walker([])
        #self.threadcursor = cursor_walk(self.thread.threadList)
        buffer_manager.register_support(self.thread.threadList, thread_index)
        buffer_manager.register_support(self.lines2, info_log)

        #urwid.register_signal(buffer_manager, ['log'])
        #urwid.Signals.register(conversation_cache, ['log'])
        #urwid.Signals.connect(buffer_manager, 'log', self.addLine2)
        #urwid.Signals.connect(conversation_cache, 'log', self.addLine2)

        #self.listbox = urwid.ListBox(self.thread.threadList)
        #self.listbox2 = urwid.ListBox(self.lines2)
        self.listbox2 = buffer_manager.get_buffer(self.lines2)
        self.listbox = buffer_manager.set_buffer(self.thread.threadList)
        buffer_manager.register_noremove(self.listbox)
        buffer_manager.register_noremove(self.listbox2)


        self.redisplay()
        #imapthread._thread_init(self.addLine2)
        #self.c = 0
        #result_machine = index.result_machine()
        #unsortlist = list(result_machine.search('*', sortkey=u'date', resultlimit=50000000))

        xconn = xappy.IndexerConnection('xap.idx')
        #r = [xconn.get_document(x).data for x in xconn.iterids()]
        r = (xconn.get_document(x).data for x in xconn.iterids())
        self.thread.thread(r)

        #self.unsortlist = list(self.result_machine.search('*', sortkey=u'date', resultlimit=50000000))
        #self.unsortlist = list(self.unsortlist)
        #self.unsortlist.reverse()
        #self.thread.thread(self.unsortlist)
        #self.thread.thread(self.unsortlist[500*self.c:500*(self.c+1)])
        self.redisplay()

        while 1:
            keys = self.tui.get_input()

            if 'Q' in keys:
                break

            for key in keys:
                if key in ('h','j','k','l','J','K'):
                    key = keymap_alias[key]

                #if key == 'x':
                    #buffer_manager.destroy()

                if key == 'window resize':
                    self.size = self.tui.get_cols_rows()
                elif key == 'f1':
                    buffer_manager.set_buffer(self.thread.threadList)
                elif key == 'f2':
                    buffer_manager.set_buffer(self.lines2)
                elif key == 'b':
                    buffer_manager.set_next()
                elif key == 'B':
                    buffer_manager.set_prev()
                elif key == 't':
                    self.addLine2('adding another 500 to index')
                    #self.c += 1
                    #self.thread.thread(self.unsortlist[500*self.c:500*(self.c+1)])
                else:
                    self.frame.keypress(self.size, key)
                    if key == 'x':
                        self.addLine2(str(conversation_cache._inst_buffers.items()))

                self.redisplay()

if __name__ == '__main__':
    screen = Screen()
    screen.main()
