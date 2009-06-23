#!/usr/bin/python

import urwid.curses_display
import urwid

import lazythread
import index

#class convContainer(dict):
def _callback(fn):
    def wrapper(self, *args):
        r = fn(self, *args)
        self.parentmethod()
        return r
    return wrapper

class callback_list(list):
    def __init__(self, parentmethod):
        self.parentmethod = parentmethod

    append = _callback(list.append)
    extend = _callback(list.extend)
    __setslice__ = _callback(list.__setslice__)
    __setitem__ = _callback(list.__setitem__)
    
class conv_repr(lazythread.convContainer):
    def __init__(self, msgids, subjects, labels, messages):
        self.widget = urwid.Text('Loading', wrap='clip')

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

        self.selectable = self.widget.selectable
        self.render = self.widget.render
        self.rows = self.widget.rows



    '''def selectable(self):
        return False
    def rows(self, (maxcol,), focus=False):
        return 1
        '''

    def update_widget(self):
        #self.widget = urwid.Text(self.__repr__(), wrap='clip')
        self.widget.set_text(self.__repr__())


    '''def __repr__(self):
        self.ddate = self['messages'][-1]['date']
        self.dsender = u','.join([x['sender'].split()[0].strip('"') for x in self['messages'][-3:]])
        self.dcontained = len(self['messages'])
        self.dsubject = stripSubject(self['messages'][-1].get(u'subject',u''))
        self.dlabels = u' '.join(u'+%s' % x for x in self['labels'])
        self.dpreview = u' '.join(self['messages'][-1].get(u'content',u'').split())
        self.disprender = u"%s\t%s\t%i\t%s %s %s" % \
            (self.ddate, self.dsender, self.dcontained, self.dsubject, self.dlabels, self.dpreview)
        return self.disprender
        '''

    '''def set_label(self, label):
        self.label = label
        self.w = Columns([
            ('fixed', 1, self.button_left),
            urwid.Text( label ),
            ('fixed', 1, self.button_right)],
            dividechars=1)
        self._invalidate()

    def keypress(self, (maxcol,), key):
        if key not in something:
            return key
        somewhere.message_state_machine(self.messages)
        newwin(showmessages)
        '''

lazythread.convContainer = conv_repr
#lazythread.convContainer = convRep

class myWalker(urwid.SimpleListWalker):
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

class Screen:
    def __init__(self, tui):
        self.tui = tui
        self.result_machine = index.result_machine('msgid')
        self.unsortlist = self.result_machine.search('muuid:*', sortkey=u'date', resultlimit=50000000)
        self.thread = lazythread.lazy_thread()

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

    def run(self):
        self.size = self.tui.get_cols_rows()

        self.lines = [urwid.Text('Hello')]
        self.lines2 = [urwid.Text('Hello2')]
        #self.listbox = urwid.ListBox(self.lines)
        self.threadview_list = []
        #self.threadwalker = urwid.SimpleListWalker(self.threadview_list)
        #self.threadwalker = urwid.SimpleListWalker([])
        #self.thread.threadList.__new__(urwid.SimpleListWalker)
        #self.threadwalker = self.thread.threadList
        #self.listbox = urwid.ListBox(self.thread)
        #self.listbox = urwid.ListBox(self.threadview_list)
        self.threadwalker = urwid.PollingListWalker(self.thread.threadList)
        self.listbox = urwid.ListBox(self.threadwalker)
        self.listbox2 = urwid.ListBox(self.lines2)
        self.input = urwid.Edit()
        self.summarytxt = urwid.Text('inbox, blalkjsdfn %i threads' % len(self.thread), align='left')

        self.bframe = urwid.Pile([self.summarytxt, self.input])

        self.frame = urwid.Frame(self.listbox, footer=self.bframe)
        self.frame.set_focus('footer')

        self.redisplay()
        self.thread.thread(self.unsortlist)
        #self.threadwalker._modified()
        #for i in dir(self.threadwalker): self.addLine2(i)
        #self.threadview_list.extend([urwid.Text(x.__repr__()[:self.size[0]]) for x in self.thread])
        #self.threadwalker.extend([urwid.Text(x.__repr__()[:self.size[0]]) for x in self.thread])
        #self.listbox.set_focus(len(self.thread) - 1)
        self.redisplay()

        while 1:
            keys = self.tui.get_input()

            for key in keys:
                if key == 'window resize':
                    self.size = self.tui.get_cols_rows()
                elif key == 'enter':
                    text = self.input.get_edit_text()
                    self.input.set_edit_text('')
                    self.addLine(text)
                elif key in ('up', 'down', 'page up', 'page down'):
                    self.listbox.keypress(self.size, key)
                elif key == 'f1':
                    self.frame.set_body(self.listbox)
                elif key == 'f2':
                    self.frame.set_body(self.listbox2)
                else:
                    self.frame.keypress(self.size, key)

                self.redisplay()

if __name__ == '__main__':
    tui = urwid.curses_display.Screen()
    screen = Screen(tui)
    tui.run_wrapper(screen.run)
