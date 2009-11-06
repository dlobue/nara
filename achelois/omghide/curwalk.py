from urwid import ListWalker

class cursor_walk(ListWalker):
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
        __cur = self.cursor.current()
        return __cur[1], __cur[0]

    def set_focus(self, position):
        self.cursor.set(position)
        self._modified()

    def get_next(self, start_from):
        __cur = self.cursor.current()
        if __cur != start_from:
            self.cursor.set(start_from)
        try:
            __ncur = self.cursor.next()
            return __ncur[1], __ncur[0]
        except:
            return None, None

    def get_prev(self, start_from):
        __cur = self.cursor.current()
        if __cur != start_from:
            self.cursor.set(start_from)
        try:
            __ncur = self.cursor.prev()
            return __ncur[1], __ncur[0]
        except:
            return None, None
