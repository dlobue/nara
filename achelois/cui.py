#!/usr/bin/python
# -*- coding: utf-8 -*-

from overwatch import settings, xapidx, MetaSignals, connect_signal, eband
#from overwatch import settings, MetaSignals, eband, Signals

import urwid.curses_display
import urwid
from urwid import CanvasCache
from buffer import buffer_manager
from collections import deque

import xappy

from index_mode import index_box
from read_mode import read_box
from databasics import conv_container


class info_log(urwid.ListBox): pass
class info_log_list(deque):
    def __hash__(self): return id(self)


keymap_alias = {'k':'up', 'j':'down', 'h':'left', 'l':'right', 'J':'page down', 'K':'page up'}

class Screen(object):
    __metaclass__ = MetaSignals
    signals = ['emergency']

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
            ]
    def __init__(self):
        connect_signal(eband, 'emergency', self.shutdown)
        connect_signal(eband, 'log', self.addLine2)
        connect_signal(eband, 'frame_connect', self.frame_con)
        connect_signal(eband, 'redisplay', self.redisplay)

    def frame_con(self, w):
        connect_signal(w, 'modified', self.frame._invalidate)

    def shutdown(self):
        self.tui.stop()

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
        if canvas is None: raise ValueError('canvas is None!!!!')
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
        #summarytxt = urwid.Text('inbox, blalkjsdfn %i threads' % len(self.thread), align='left')
        summarytxt = urwid.Text('inbox, blalkjsdfn number threads', align='left')
        self.summarytxt = urwid.AttrWrap(summarytxt, 'status')
        self.input = urwid.Edit()
        self.bframe = urwid.Pile([self.summarytxt, self.input])
        self.body_loading = urwid.ListBox([urwid.Text('Loading....')])

        self.frame = urwid.Frame(self.body_loading, footer=self.bframe)
        self.frame.set_focus('body')

        buffer_manager.register_rootobj(self.set_buffer)

        self.lines = None
        self.lines2 = info_log_list([urwid.Text(('test','hello2'))],500)

        sconn = xappy.SearchConnection(xapidx)
        qall = sconn.query_all()
        buffer_manager.register_support( qall, index_box)
        buffer_manager.register_support(self.lines2, info_log)
        buffer_manager.register_support(conv_container, read_box)

        #self.listbox2 = buffer_manager.set_buffer(self.lines2)
        self.listbox2 = buffer_manager.get_buffer(self.lines2)
        #self.listbox = buffer_manager.get_buffer(qall)
        self.listbox = buffer_manager.set_buffer(qall)

        #buffer_manager.register_noremove(self.listbox)
        #buffer_manager.register_noremove(self.listbox2)

        self.redisplay()


        while 1:
            keys = self.tui.get_input()

            if 'Q' in keys:
                break

            for key in keys:
                #if key in ('h','j','k','l','J','K'):
                    #key = keymap_alias[key]

                if key == 'x':
                    buffer_manager.destroy()

                elif key == 'window resize':
                    self.size = self.tui.get_cols_rows()
                    #elif key == 'f1':
                        #buffer_manager.set_buffer(self.thread.threadList)
                elif key == 'f2':
                    buffer_manager.set_buffer(self.lines2)
                elif key == 'b':
                    buffer_manager.set_next()
                elif key == 'B':
                    buffer_manager.set_prev()
                elif key == 'r':
                    self.addLine2(str(len(CanvasCache._widgets)))
                    self.addLine2(str(len(CanvasCache._refs)))
                    self.addLine2(str(len(CanvasCache._deps)))
                elif key == 't':
                    self.addLine2("\n\nbuffer manager _buffer contents:")
                    for d in buffer_manager._buffers:
                        self.addLine2('\n%s' % str(d))
                    self.addLine2("\nbuffer manager _buffer len: %s" % str(len(buffer_manager._buffers)))
                    self.addLine2("\nbuffer manager _order contents:")
                    self.addLine2(str(buffer_manager._order))
                    #emit_signal(eband, 'log', 'hello world')
                    #tids = get_threads(sconn, qall)
                    #data = get_members(sconn, tids)
                    c = 0
                    #while c < 5:
                        #self.addLine2(str(data.next().data))
                        #c+=1
                        
                    #val = dir(self.listbox2)
                    #[ self.addLine2('%s        %s' % (x, getattr(self.listbox2, x))) for x in val ]
                    #map(self.addLine2, getattr(self.listbox2, val))
                    #self.addLine2('adding another 500 to index')
                    #self.c += 1
                    #self.thread.thread(self.unsortlist[500*self.c:500*(self.c+1)])
                else:
                    self.frame.keypress(self.size, key)

                self.redisplay()

if __name__ == '__main__':
    screen = Screen()
    screen.main()
