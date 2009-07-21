from achelois.lib import util
from achelois import lazythread
import urwid

class conv_repr(dict):
    #{{{
    __metaclass__ = urwid.MetaSignals
    signals = ['keypress']

    def __init__(self, msgids, subjects, labels, messages):
        self.widget = conv_widget('Loading')
        urwid.Signals.connect(self.widget, 'keypress', self.load_msg)

        self['msgids'] = msgids
        self['subjects'] = subjects
        self['labels'] = labels
        #self['messages'] = callback_list(self.update_widget)
        #self['messages'].extend(messages)
        self['messages'] = messages
        
        #becuse attributes are fun
        self.msgids = self['msgids']
        self.subjects = self['subjects']
        self.messages = self['messages']
        self.labels = self['labels']

        #self.selectable = self.widget.selectable
        #self.render = self.widget.render
        #self.rows = self.widget.rows

    #def __hash__(self): return id(self)

    @property
    def id(self):
        return self['id']

    @property
    def last_update(self):
        return self['messages'][-1][0]

    def update_widget(self):
        self.widget.set_label(self.__repr__())
        try: urwid.Signals.emit(screen.thread.threadList, "modified")
        except: pass

    def load_msg(self): pass

    def __repr__(self):
        __ddate = self['messages'][-1][-1]['date']
        __dsender = u','.join([x[-1]['sender'].split()[0].strip('"') for x in self['messages'][-3:]])
        __dcontained = len(self['messages'])
        __dsubject = lazythread.stripSubject(self['messages'][-1][-1].get(u'subject',u''))
        __dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        __dpreview = u' '.join(self['messages'][-1][-1].get(u'content',u'').split())
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
        self.label = label
        w = urwid.Text( label, wrap='clip' )
        self.w = urwid.AttrWrap( w, 'body', 'focus' )
        '''self.w-no = urwid.Columns([
            ('fixed', 1, self.button_left),
            urwid.Text( label ),
            ('fixed', 1, self.button_right)],
            dividechars=1)
            '''
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
    __metaclass__ = util.MetaSuper

    def merge(self, found, workobj):
        self.__super.merge(found, workobj)
        workobj.update_widget()

    def append(self, data):
        self.__super.append(data)
        data.update_widget()
