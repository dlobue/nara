from achelois.overwatch import settings
from buffer import buffer_manager

from datetime import datetime, timedelta
from weakref import WeakKeyDictionary

from urwid import ListWalker, ListBox, WidgetWrap, MetaSuper, emit_signal, connect_signal, MetaSignals
import xappy

from achelois.databasics import thread_container
from achelois.search_utils import get_threads, get_members
from achelois.tools import filterNone

import threadmap

#from string import ascii_lowercase, digits, maketrans
#anonitext = maketrans(ascii_lowercase + digits, 'x'*26 + '7'*len(digits))

srchidx = 'xap.idx'

class index_box(ListBox):
    __slots__ = ()
    def __init__(self, query):
        w = index_walker(query)
        self.__super.__init__(w)

    def render(self, size, focus=False):
        maxcol, maxrow = size
        if self.body._rows != (maxrow-2):
            self.body._rows = (maxrow-2)
        self.__super.render(size, focus)

class index_walker(ListWalker):
    __slots__ = ('focus', '_tids', '_query', 'container', '_wstorage', '_rows')

    def __hash__(self): return id(self)

    def __init__(self, query):
        self._tids = []
        self._wstorage = {}
        self._wstorage = WeakKeyDictionary()
        self._rows = 20
        self.container = sigthread_container()
        self._query = query
        self.focus = 0

        self.more_threads()

    def get_focus(self):
        if len(self.container) == 0: return None, None
        return self._get_widget(self.container[self.focus]), self.focus

    def set_focus(self):
        assert type(position) is int
        self.focus = position
        self._modified()

    def get_next(self, start_from):
        pos = start_from + 1
        if len(self.container) <= pos:
            try: self.more_threads()
            except: pass
            if len(self.container) <= pos: return None, None
           
        return self._get_widget(self.container[pos]), pos

    def get_prev(self, start_from):
        pos = start_from - 1
        if pos < 0: return None, None
        return self._get_widget(self.container[pos]), pos

    def _get_widget(self, conv):
        w = self._wstorage.setdefault(conv, conv_widget())
        if not hasattr(w, '_conv'): w._init(conv)
        return w

    def more_threads(self):
        cur = len(self.container)
        sconn = xappy.SearchConnection(srchidx)
        self._update_tids(sconn)

        to_get = filter(lambda x: x in self.container._map, self._tids[:cur])
        to_get = filterNone(set(to_get))
        to_get.extend(self._tids[cur:(cur+self._rows-len(to_get))])

        self._add_more_threads(sconn, to_get)
        
        sconn.close()

    def _update_tids(self, sconn):
        threads = get_threads(sconn, self._query)
        self._tids = threads

    def _add_more_threads(self, sconn, tids):
        to_join = get_members(sconn, tids)
        self.container.thread(to_join)
        self._modified()

class conv_widget(WidgetWrap):
    __slots__ = ('_conv', '_urwid_signals')
    signals = ['keypress', 'modified']
    ignore_focus = False
    _selectable = True
    
    def __init__(self): pass

    def _init(self, conv):
        connect_signal(conv, 'modified', self.update)
        self._conv = conv
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

        ddate = ('new index', ' {0:>10}'.format(rep_date))

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

        dsubject = ('%s index' % tstat, ' %s' % oldest_new.get('subject',[''])[0])
        dpreview = ('index sample', ' %s' % ' '.join(oldest_new.get('sample',[''])[0].split()))

        sendmarkup = []
        c=0
        w=25
        for x in dsender:
            if 'S' not in x.flags: stat = 'new'
            else: stat = 'read'
            fname = ' %s,' % x.sender[0].split()[0].strip('"')
            l=(len(fname)+2)
            if (c+l) >= w:
                charsleft = (w-c)
                fname = fname[:charsleft].strip(',')
            elif x == dsender[-1]:
                fname = fname.strip(',')
            c+=l
            sendmarkup.append(('%s index' % stat, fname))
            if c >= w: break

        dcontained = ('%s index' % tstat, ' {0!s:^5}'.format(len(self._conv.messages)))
        dlabels = ('index label', ' +%s' % ' +'.join(self._conv.labels))

        return (ddate, sendmarkup, dcontained, dsubject, dlabels, dpreview)

    def update(self):
        self.set_text( self.idx_repr() )
        self._invalidate()

    def set_text(self, markup):
        #def privatize_txt(x):
            #    if type(x) is list:
                #        return map(privatize_txt, x)
                #    if type(x) is tuple and len(x) == 2:
                    #        return (x[0], x[1].translate(anonitext))
        return self._w.original_widget.set_text(markup)

    def keypress(self, (maxcol,), key):
        if key not in (' ','enter'):
            return key
        buffer_manager.set_buffer(self._conv)

class sigthread_container(thread_container):
    __slots__ = ()
    __metaclass__ = MetaSuper
    def join(self, conv):
        self.__super.join(conv)
        conv = self[conv.thread[0]]
        emit_signal(conv, 'modified')
