#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgitb
cgitb.enable(format='txt')

from overwatch import settings, xapidx, MetaSignals, connect_signal, eband
#from overwatch import settings, MetaSignals, eband, Signals

import urwid.curses_display
import urwid
from urwid import CanvasCache
from buffer import buffer_manager
from collections import deque
import sys

import xappy

from index_mode import index_box
from read_mode import read_box
from databasics import conv_container

#def set_rbuffer(cls, buffer):
    #frame.set_body(buffer)


class info_log(urwid.ListBox): pass
class info_log_list(deque):
    def __hash__(self): return id(self)

class console_out(object):
    def write(self, txt):
        addLine(('stdout', txt.strip()))
class console_error(object):
    def write(self, txt):
        addLine(('stderr', txt.strip()))


sys.stdout = console_out()
sys.stderr = console_error()

keymap_alias = {'k':'up', 'j':'down', 'h':'left', 'l':'right', 'J':'page down', 'K':'page up'}

palette = [
            ('body', 'light gray', 'black'),
            ('blank', 'light gray', 'black'),
            ('selected', 'white', 'black', ('bold')),
            ('focus', 'light blue', 'black', ('bold')),
            ('selected focus', 'light cyan', 'black', ('bold')),
            ('test', 'yellow', 'dark cyan'),
            ('default attr', 'yellow', 'dark cyan'),
            ('default focus', 'light magenta', 'dark cyan'),
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
            ('index new', 'white', 'black'),
            ('index read', 'light gray', 'black'),
            ('index starred', 'yellow', 'black'),
            ('index label', 'brown', 'black'),
            ('index sample', 'dark cyan', 'black'),
            ('index notfocus', 'light gray', 'black'),
            ('index focus', 'white', 'dark cyan', ('bold')),
            ('index new focus', 'white', 'dark cyan', ('bold')),
            ('index read focus', 'light gray', 'dark cyan', ('bold')),
            ('index starred focus', 'yellow', 'dark cyan', ('bold')),
            ('index label focus', 'brown', 'dark cyan', ('bold')),
            ('index sample focus', 'light cyan', 'dark cyan', ('bold')),
            ('stdout', 'dark cyan', 'black'),
            ('stderr', 'light red', 'black'),
            ]


class fraMe(urwid.Frame):
    signals = ['modified']
    def exit(self):
        raise urwid.ExitMainLoop
    def keypress(self, size, key):
        if key == 'x':
            buffer_manager.destroy()
        elif key == 'Q':
            raise urwid.ExitMainLoop
        elif key == 'f2':
            buffer_manager.set_buffer(self.lines2)
        elif key == 'b':
            buffer_manager.set_next()
        elif key == 'B':
            buffer_manager.set_prev()
        else:
            return self.__super.keypress(size, key)

def frame_con(w):
    connect_signal(w, 'modified', frame._invalidate)

#self.summarytxt = urwid.Text('inbox, blalkjsdfn %i threads' % len(self.thread), align='left')
#summarytxt = urwid.Text('inbox, blalkjsdfn %i threads' % len(self.thread), align='left')
summarytxt = urwid.Text('inbox, blalkjsdfn number threads', align='left')
summarytxt = urwid.AttrWrap(summarytxt, 'status')
input = urwid.Edit()
bframe = urwid.Pile([summarytxt, input])
body_loading = urwid.ListBox([urwid.Text('Loading....')])

frame = fraMe(body_loading, footer=bframe)
frame.set_focus('body')

buffer_manager.register_rootobj(frame.set_body)
#buffer_manager.register_rootobj(set_rbuffer)

lines2 = info_log_list([urwid.Text(('test','hello2'))],500)

sconn = xappy.SearchConnection(xapidx)
qall = sconn.query_all()
buffer_manager.register_support( qall, index_box)
buffer_manager.register_support(lines2, info_log)
buffer_manager.register_support(conv_container, read_box)

#listbox2 = buffer_manager.set_buffer(lines2)
listbox2 = buffer_manager.get_buffer(lines2)
#listbox = buffer_manager.get_buffer(qall)
listbox1 = buffer_manager.set_buffer(qall)

#buffer_manager.register_noremove(listbox)
#buffer_manager.register_noremove(listbox2)

def addLine(text):
    lines2.append(urwid.Text(text))
    listbox2.set_focus(len(lines2) - 1)

main = urwid.MainLoop(frame, palette, screen=urwid.curses_display.Screen(), handle_mouse=False)
#main = urwid.MainLoop(frame, palette, handle_mouse=False)

connect_signal(eband, 'log', addLine)
connect_signal(eband, 'redisplay', main.draw_screen)
connect_signal(eband, 'emergency', frame.exit)
connect_signal(eband, 'frame_connect', frame_con)


if __name__ == '__main__':
    main.run()
    #screen = Screen()
    #screen.main()
