#!/usr/bin/python
# -*- coding: utf-8 -*-

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

from achelois import offlinemaildir

from string import ascii_lowercase, digits, maketrans
anonitext = maketrans(ascii_lowercase + digits, 'x'*26 + '7'*len(digits))

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
    __metaclass__ = urwid.MetaSignals
    signals = ['keypress']

    #widget = conv_widget('Loading')

    #def __init__(self, dataobj):
    #def __init__(self, msgids, subjects, labels, messages):
    def __init__(self, msgids, subjects, labels, messages, threadid=None):
        self.widget = conv_widget('Loading')
        urwid.Signals.connect(self.widget, 'keypress', self.load_msg)

        #self['msgids'] = msgids
        #self['subjects'] = subjects
        #self['labels'] = labels
        #self['messages'] = callback_list(self.update_widget)
        #self['messages'].extend(messages)
        #self['messages'] = id_list(messages)
        
        #becuse attributes are fun
#        self.dataobj = dataobj
#        self.msgids = dataobj.msgids
#        self.subjects = dataobj.subjects
#        self.messages = id_list(dataobj.messages)
#        self.labels = dataobj.labels

        self.msgids = msgids
        self.subjects = subjects
        self.messages = id_list(messages)
        self.labels = labels
        self.threadid = threadid

        self.update_widget()

        #self.selectable = self.widget.selectable
        #self.render = self.widget.render
        #self.rows = self.widget.rows

    #def __hash__(self): return id(self)

    @property
    def id(self):
        return self.threadid

    #id = threadid

    def __getitem__(self, key):
        return getattr(self, key)

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

class conv_widget(urwid.WidgetWrap):
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

lazythread.convContainer = conv_repr

class monkey_thread(lazythread.lazy_thread):
    #{{{
    __metaclass__ = util.MetaSuper

    def merge(self, found, workobj):
        self.__super.merge(found, workobj)
        workobj.update_widget()

    def append(self, data):
        self.__super.append(data)
        data.update_widget()
        #}}}

def get_threadids(query='*', field='muuid'):
    __sconn = xappy.SearchConnection('xap.idx')
    if query == '*':
        __q = __sconn.query_all()
    else:
        __q = __sconn.query_field(field, query)
    __r = [a.data['thread'][0] for a in __sconn.search(__q, 0, 99999999, checkatleast=-1, collapse='thread', sortby='-date')]
    #__r = [a.data['thread'][0] for a in __sconn.search(__q, 0, 999999999, checkatleast=-1, collapse='thread', sortby='-date')]
    __sconn.close()
    return __r

class thread_walker(urwid.SimpleListWalker):
    def __init__(self, threadids):
        self.threader = lazythread.lazy_thread()
        self.threadids = threadids              
        self.count = 0
        self.focus = 0
        self.more_threads()

    def more_threads(self):
        __c_size = 30 

        __sconn = xappy.SearchConnection('xap.idx')
        __nq = __sconn.query_composite(__sconn.OP_OR,
                map(lambda x: __sconn.query_field('thread', x, __sconn.OP_OR),
                self.threadids))
        __r = __sconn.search(__nq, 0, 60, checkatleast=-1, sortby='-date')
        #__r = __sconn.search(__nq, __c_size*self.count, __c_size*(self.count+1), checkatleast=-1, sortby='-date')
        __sconn.close()
        #if len(__r) < 1: raise IndexError('no more!')
        self.threader.thread([x.data for x in __r])
        self.count +=1

    def get_focus(self):
        if len(self.threader.threadList) == 0: return None, None
        return self.threader.threadList[self.focus].widget, self.focus

    def set_focus(self, focus):
        self.focus = focus
        self._modified()

    def get_next(self, start_from):
        pos = start_from + 1
        try: return self.threader.threadList[pos].widget, pos
        except IndexError: return None, None

        if len(self.threader.threadList) <= pos:
            try: self.more_threads()
            except IndexError: return None, None
        return self.threader.threadList[pos].widget, pos

    def get_prev(self, start_from):
        if start_from == 0: return None, None
        pos = start_from - 1
        return self.threader.threadList[pos].widget, pos

class thread_index(urwid.ListBox):
    def __init__(self, body):
        if type(body) is thread_walker:
            self.__super.__init__(body)
        else:
            __b = thread_walker(get_threadids(body))
            self.__super.__init__(__b)
            
class info_log(urwid.ListBox): pass
class view_conversation(urwid.ListBox):
    def __init__(self, body):
        self.conv = body
        self.__super.__init__(read_walker(body))

    def self_destruct(self):
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
        summarytxt = urwid.Text('inbox, blalkjsdfn %i threads' % len(self.thread), align='left')
        #summarytxt = urwid.Text('inbox, blalkjsdfn number threads', align='left')
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
        '''
        self.thread.threadList = thread_walker([])
        '''
        #self.threadcursor = cursor_walk(self.thread.threadList)
        #buffer_manager.register_support(self.thread.threadList, thread_index)
        '''
        buffer_manager.register_support(thread_walker, thread_index)
        '''
        buffer_manager.register_support( '*', thread_index)
        buffer_manager.register_support(self.lines2, info_log)

        #urwid.register_signal(buffer_manager, ['log'])
        #urwid.Signals.register(conversation_cache, ['log'])
        #urwid.Signals.connect(buffer_manager, 'log', self.addLine2)
        #urwid.Signals.connect(conversation_cache, 'log', self.addLine2)

        #self.listbox = urwid.ListBox(self.thread.threadList)
        #self.listbox2 = urwid.ListBox(self.lines2)
        self.listbox2 = buffer_manager.get_buffer(self.lines2)
        self.listbox = buffer_manager.set_buffer('*')
        '''
        self.listbox = buffer_manager.set_buffer(self.thread.threadList)
        '''
        #buffer_manager.register_noremove(self.listbox)
        #buffer_manager.register_noremove(self.listbox2)


        self.redisplay()
        #imapthread._thread_init(self.addLine2)
        #self.c = 0
        #result_machine = index.result_machine()
        #unsortlist = list(result_machine.search('*', sortkey=u'date', resultlimit=50000000))

        #xconn = xappy.IndexerConnection('xap.idx')
        #r = [xconn.get_document(x).data for x in xconn.iterids()]
        #r = [xconn.get_document(x).data for x in xconn.iterids()]
        #self.thread.thread(r[:500])
        '''
        sconn = xappy.SearchConnection('xap.idx')
        #r = [a.data['thread'][0] for a in sconn.search(sconn.query_all(), 0, -1, checkatleast=-1, collapse='thread', sortby='-date')]
        r = [a.data['thread'][0] for a in sconn.search(sconn.query_all(), 0, 99999999, checkatleast=-1, collapse='thread', sortby='-date')]
        nq = sconn.query_composite(sconn.OP_OR, map(lambda x: sconn.query_field('thread', x, sconn.OP_OR), r))
        res = sconn.search(nq, 0, 60, checkatleast=-1, sortby='-date')
        #res = sconn.search(nq, 0, 99999999, checkatleast=-1, sortby='-date')
        self.thread.thread([x.data for x in res])
        '''

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

                self.redisplay()

if __name__ == '__main__':
    screen = Screen()
    screen.main()
