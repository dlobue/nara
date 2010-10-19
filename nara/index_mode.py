from overwatch import settings, emit_signal, eband, emit_signal, connect_signal, MetaSignals, register_signal, xapidx
#from overwatch import settings, eband, MetaSignals, Signals
from buffer import buffer_manager

from datetime import datetime, timedelta
from weakref import WeakKeyDictionary, ref
from threading import Thread

from urwid import ListWalker, ListBox, WidgetWrap, MetaSuper, Text, AttrWrap, Columns
import xappy

from lib.metautil import MetaMixin, ScrollMixin
from databasics import thread_container
from search_utils import get_threads, get_members
from tools import filterNone
from read_mode import read_box

from lib import threadmap, forkmap

#from string import ascii_lowercase, digits, maketrans
#anonitext = maketrans(ascii_lowercase + digits, 'x'*26 + '7'*len(digits))

srchidx = xapidx

class index_box(ListBox):
    signals = ['modified']

    def __init__(self, query):
        w = index_walker(query)
        emit_signal(eband, 'frame_connect', self)
        self.__super.__init__(w)

    def _invalidate(self):
        emit_signal(self, 'modified')
        self.__super._invalidate()

    def render(self, size, focus=False):
        maxcol, maxrow = size
        if self.body._rows != maxrow:
            self.body._rows = maxrow
        return self.__super.render(size, focus)



class index_walker(ListWalker, MetaMixin):
    #__slots__ = ('focus', '_tids', '_query', 'container', '_wstorage', '_rows', '_urwid_signals')
    signals = ['modified', 'keypress']
    context = 'index_mode'

    def __hash__(self): return id(self)

    def __init__(self, query):
        self._tids = []
        #self._wstorage = {}
        self._wstorage = WeakKeyDictionary()
        self._rows = 20
        self.container = thread_container()
        self._query = query
        self.focus = 0

        self.more_threads()

    def _modified(self):
        if self.focus >= len(self.container):
            self.focus = max(0, len(self.container)-1)
        ListWalker._modified(self)
            #emit_signal(self, 'modified')

    def get_focus(self):
        if len(self.container) == 0: return None, None
        w = self._get_widget(self.container[self.focus])
        return w, self.focus

    def set_focus(self, position):
        assert type(position) is int
        self.focus = position
        self._modified()

    def get_next(self, start_from):
        pos = start_from + 1
        if len(self.container) <= pos:
            if len(self.container) != len(self._tids):
                self._more_threads()
                #thread = self.more_threads()
                #thread.join()
            elif self.chk_new():
                self._more_threads()
                #thread = self.more_threads()
                #thread.join()
            else: return None, None
            return None, None
           
        w = self._get_widget(self.container[pos])
        return w, pos

    def get_prev(self, start_from):
        pos = start_from - 1
        if pos < 0: return None, None
        w = self._get_widget(self.container[pos])
        return w, pos

    def _get_widget(self, conv):
        w = self._wstorage.setdefault(conv, conv_widget())
        if not hasattr(w, '_conv'):
            w._init(conv)
            connect_signal(w, 'modified', self._modified)
            connect_signal(w, 'keypress', self.keypress)
        return w

    def _keypress(self, key):
        if key == "r":
            emit_signal(eband, 'log', str(len(self.container)))
        elif key == "e":
            self._more_threads()

    def more_threads(self):
        thread = Thread(target=self._more_threads)
        thread.start()
        return thread

    def _more_threads(self):
        emit_signal(eband, 'log', 'running more_threads')
        cur = len(self.container)
        emit_signal(eband, 'log', 'len container at start: %s' % str(cur))
        sconn = xappy.SearchConnection(srchidx)
        self._update_tids(sconn)

        to_get = filter(lambda x: x not in self.container._map, self._tids[:cur])
        to_get = filterNone(set(to_get))
        #emit_signal(eband, 'log', str(to_get))
        to_get.extend(self._tids[cur:(cur+self._rows-len(to_get))])
        #emit_signal(eband, 'log', str(to_get))

        self._add_more_threads(sconn, to_get)
        
        sconn.close()

    def do_all_threads(self, size, key):
        self._all_threads()

    def _all_threads(self):
        sconn = xappy.SearchConnection(srchidx)
        self._update_tids(sconn)
        self._add_more_threads(sconn, self._tids)
        sconn.close()

    def chk_new(self):
        start_count = len(self._tids)
        self._chk_new()
        new_count = len(self._tids)
        if start_count == new_count:
            return False
        else:
            return True

    def _chk_new(self):
        sconn = xappy.SearchConnection(srchidx)
        self._update_tids(sconn)
        sconn.close()

    def _update_tids(self, sconn):
        threads = get_threads(sconn, self._query)
        self._tids = threads

    def _add_more_threads(self, sconn, tids):
        emit_signal(eband, 'log', 'in _add_more_threads')
        to_join = get_members(sconn, tids)
        emit_signal(eband, 'log', 'thread is now %s convs' % str(len(self.container)))
        emit_signal(eband, 'log', 'got %s messages to thread' % str(len(to_join)))
        self.container.thread(to_join)
        emit_signal(eband, 'log', 'thread is now %s convs' % str(len(self.container)))
        self._modified()
        emit_signal(eband, 'redisplay')
        #if len(to_join): self._modified()
        #return



class conv_widget_text(MetaMixin, ScrollMixin, WidgetWrap):
    __slots__ = ('_conv')
    #__slots__ = ('_conv', '_urwid_signals')
    signals = ['keypress', 'modified']
    ignore_focus = False
    context = 'index_mode'
    
    def __init__(self):
        txt = "Loading"
        w = Text(txt, wrap='clip')
        w = AttrWrap(w, 'index notfocus',
                     {None: 'index focus',
                      'index notfocus': 'index focus',
                      'index new': 'index new focus',
                      'index read': 'index read focus',
                      'index starred': 'index starred focus',
                      'index label': 'index label focus',
                      'index sample': 'index sample focus'
                     }
                    )
        self.__super.__init__(w)

    def _init(self, conv):
        conv._wcallback = ref(self.update)
        #register_signal(conv, 'modified')
        #connect_signal(conv, 'modified', self.update)
        self._conv = conv
        self.update()

    def selectable(self): return True

    def idx_repr(self):
        def chk_new(x):
            if 'S' in x.flags: return False
            return True

        tot_new = len(filter(chk_new, self._conv.messages))
        if tot_new:
            tstat = 'new'
        else:
            tstat = 'read'

        now = datetime.now()
        ddate = self._conv.last_update
        if now.date() == ddate.date():
            rep_date = ddate.strftime('%X')
        elif now.year > ddate.year:
            rep_date = ddate.strftime('%y %b %d')
        else:
            yest = now - timedelta(days=1)
            if yest.date() == ddate.date():
                rep_date = ddate.strftime('Yest %X')
            else:
                rep_date = ddate.strftime('%b %d')

        ddate = ('index new', ' {0:>10}'.format(rep_date))

        dsender = filter(chk_new, self._conv.messages)[:3]
        idx = None
        if tot_new < 3:
            if tot_new == 0: idx = -1
            dsender.extend(self._conv.messages[-(3 - tot_new):])

        if idx is None:
            isender = iter(dsender)
            while 1:
                try: oldest_new = isender.next()
                except StopIteration: break
                if 'S' not in oldest_new.flags: break
        else:
            oldest_new = dsender[idx]

        dsubject = ('index %s' % tstat, ' %s' % oldest_new.get('subject',[''])[0])
        dpreview = ('index sample', ' %s' % ' '.join(oldest_new.get('sample',[''])[0].split()))

        sendmarkup = []
        c=0
        w=25
        break_early = False
        for x in dsender:
            if 'S' not in x.flags: stat = 'new'
            else: stat = 'read'
            fname = x.sender[0].split()[0].strip('"')
            if '@' in fname: fname = fname.split('@')[0]
            fname = ' %s,' % fname
            l=len(fname)
            charsleft = (w-c)
            if (c+l) >= w:
                fname = fname.strip(',')
                fname = fname[:charsleft]
                break_early = True
            c+=l
            sendmarkup.append(('index %s' % stat, fname))
            if break_early: break

        if not break_early:
            last_sender = sendmarkup.pop()
            attr, fname = last_sender
            fname = fname.strip(',')
            fname = fname.ljust(charsleft)
            sendmarkup.append((attr, fname))

        dcontained = ('index %s' % tstat, ' {0!s:^5}'.format(len(self._conv.messages)))
        dlabels = ('index label', ' %s' % ' '.join(map(lambda x: '+%s' % x, self._conv.labels)))
        if dlabels[1] == ' ':
            dlabels = ' '

        return [ddate, sendmarkup, dcontained, dsubject, dlabels, dpreview]

    def update(self):
        self.set_text( self.idx_repr() )
        self._invalidate()
        emit_signal(self, 'modified')

    def set_text(self, markup):
        #def privatize_txt(x):
            #    if type(x) is list:
                #        return map(privatize_txt, x)
                #    if type(x) is tuple and len(x) == 2:
                    #        return (x[0], x[1].translate(anonitext))
        return self._w.original_widget.set_text(markup)

    def do_activate(self, size, key):
        try: buffer_manager.set_buffer(self._conv)
        except TypeError:
            buffer_manager.register_support(self._conv, read_box)
            buffer_manager.set_buffer(self._conv)

    def do_nomap(self, size, key):
        return key

    def _keypress(self, (maxcol,), key):
        if key in ('r', 'e'):
            emit_signal(self, 'keypress', key)
            return key
        elif key not in (' ','enter'):
            return key
        try: buffer_manager.set_buffer(self._conv)
        except TypeError:
            buffer_manager.register_support(self._conv, read_box)
            buffer_manager.set_buffer(self._conv)



class conv_widget_columns(MetaMixin, ScrollMixin, WidgetWrap):
    #__slots__ = ('_conv')
    #__slots__ = ('_conv', '_urwid_signals')
    signals = ['keypress', 'modified']
    ignore_focus = False
    context = 'index_mode'
    
    '''
    def __init__(self):
        txt = "Loading"
        w = Text(txt, wrap='clip')
        w = AttrWrap(w, 'index notfocus',
                     {None: 'index focus',
                      'index notfocus': 'index focus',
                      'index new': 'index new focus',
                      'index read': 'index read focus',
                      'index starred': 'index starred focus',
                      'index label': 'index label focus',
                      'index sample': 'index sample focus'
                     }
                    )
        self.__super.__init__(w)
    '''

    def __init__(self):
        txt = "Loading"
        wsent = Text(txt, align='right')
        wsender = Text(txt, wrap='clip')
        wmsgs = Text(txt, align='center')
        wsummary = Text(txt, wrap='clip')
        w = Columns([
                ('fixed', 10, wsent),
                ('fixed', 25, wsender),
                ('fixed', 5, wmsgs),
                wsummary],
                dividechars=1, min_width=4)
        w = AttrWrap(w, 'index notfocus',
                     {None: 'index focus',
                      'index notfocus': 'index focus',
                      'index new': 'index new focus',
                      'index read': 'index read focus',
                      'index starred': 'index starred focus',
                      'index label': 'index label focus',
                      'index sample': 'index sample focus'
                     }
                    )
        self.__super.__init__(w)

    def _init(self, conv):
        conv._wcallback = ref(self.update)
        #register_signal(conv, 'modified')
        #connect_signal(conv, 'modified', self.update)
        self._conv = conv
        self.update()

    def selectable(self): return True

    def idx_repr(self):
        def is_new(x):
            if 'S' in x.flags: return False
            return True

        tot_new = len(filter(is_new, self._conv.messages))
        if tot_new:
            tstat = 'new'
        else:
            tstat = 'read'

        now = datetime.now()
        ddate = self._conv.last_update
        if now.date() == ddate.date():
            rep_date = ddate.strftime('%X')
        elif now.year > ddate.year:
            rep_date = ddate.strftime('%y %b %d')
        else:
            yest = now - timedelta(days=1)
            if yest.date() == ddate.date():
                rep_date = ddate.strftime('Yest %X')
            else:
                rep_date = ddate.strftime('%b %d')

        ddate = ('index new', str(rep_date))
        #ddate = ('index new', ' {0:>10}'.format(rep_date))

        dsender = filter(is_new, self._conv.messages)[:3]
        idx = None
        if tot_new < 3:
            if tot_new == 0: idx = -1
            dsender.extend(filter(lambda x: not is_new(x),
                                    self._conv.messages[-(3 - tot_new):]))

        if idx is None:
            isender = iter(dsender)
            while 1:
                try: oldest_new = isender.next()
                except StopIteration: break
                if 'S' not in oldest_new.flags: break
        else:
            oldest_new = dsender[idx]

        try:
            #dsubject = ('index %s' % tstat, ' %s' % oldest_new.get('subject',[''])[0])
            #dsubject = ('index %s' % tstat, ' %s' % oldest_new.get('subject',''))
            dsubject = ('index %s' % tstat, ' %s' % oldest_new.subject or '')
        except IndexError, e:
            with open('/tmp/nara-crash.dump', 'w') as f:
                f.write(repr(oldest_new.msgid))
                f.write('\n')
                f.write(repr(oldest_new.muuid))
                f.write('\n')
                f.write(repr(oldest_new.thread))
                f.write('\n')
                f.write(repr(oldest_new))
                f.write('\n')
                f.write(repr(oldest_new.subject))
                f.write('\n')
            raise IndexError(e)
        #dpreview = ('index sample', ' %s' % ' '.join(oldest_new.get('sample','').split()))
        #dpreview = ('index sample', ' %s' % ' '.join(oldest_new.get('sample',[''])[0].split()))
        dpreview = ('index sample', ' %s' % ' '.join((oldest_new.sample or '').split()))

        sendmarkup = []
        c=0
        w=25
        break_early = False
        for x in dsender:
            if 'S' not in x.flags: stat = 'new'
            else: stat = 'read'
            fname = (x.sender or 'None').split()[0].strip('"')
            #fname = x.sender[0].split()[0].strip('"')
            if '@' in fname: fname = fname.split('@')[0]
            fname = ' %s,' % fname
            l=len(fname)
            charsleft = (w-c)
            if (c+l) >= w:
                fname = fname.strip(',')
                fname = fname[:charsleft]
                break_early = True
            c+=l
            sendmarkup.append(('index %s' % stat, fname))
            if break_early: break

        if not break_early:
            last_sender = sendmarkup.pop()
            attr, fname = last_sender
            fname = fname.strip(',')
            #fname = fname.ljust(charsleft)
            sendmarkup.append((attr, fname))

        dcontained = ('index %s' % tstat, str(len(self._conv.messages)))
        #dcontained = ('index %s' % tstat, ' {0!s:^5}'.format(len(self._conv.messages)))
        dlabels = ('index label', ' %s' % ' '.join(map(lambda x: '+%s' % x, self._conv.labels)))
        if dlabels[1] == ' ':
            dlabels = ' '

        return [ddate, sendmarkup, dcontained, dsubject, dlabels, dpreview]

    def update(self):
        self.set_text( self.idx_repr() )
        self._invalidate()
        emit_signal(self, 'modified')

    def set_text(self, markup):
        #def privatize_txt(x):
        #    if type(x) is list:
        #        return map(privatize_txt, x)
        #    if type(x) is tuple and len(x) == 2:
        #        return (x[0], x[1].translate(anonitext))
        #return self._w.original_widget.set_text(markup)
        w = self._w.original_widget.widget_list
        w[0].set_text(markup[0])
        w[1].set_text(markup[1])
        w[2].set_text(markup[2])
        w[3].set_text(markup[3:])

    def do_activate(self, size, key):
        try: buffer_manager.set_buffer(self._conv)
        except TypeError:
            buffer_manager.register_support(self._conv, read_box)
            buffer_manager.set_buffer(self._conv)

    def do_nomap(self, size, key):
        return key

    def _keypress(self, (maxcol,), key):
        if key in ('r', 'e'):
            emit_signal(self, 'keypress', key)
            return key
        elif key not in (' ','enter'):
            return key
        try: buffer_manager.set_buffer(self._conv)
        except TypeError:
            buffer_manager.register_support(self._conv, read_box)
            buffer_manager.set_buffer(self._conv)



conv_widget = conv_widget_columns



class sigthread_container(thread_container):
    __slots__ = ()
    __metaclass__ = MetaSuper
    def join(self, conv):
        self.__super.join(conv)
        conv = self[conv.thread]
        #Signals.emit(conv, 'modified')
        #emit_signal(conv, 'modified')

