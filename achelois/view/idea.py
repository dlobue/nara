class machined_widget(urwid.widget): pass

class group_state(list):
    def __init__(self, data):
        self._cache([widgetize(x) for x in data])
        self.collapsed = False
        self.detailed = False
        self.label = urwid.label("+--- blarg")

    def __getitem__(self, idx):
        if type(idx) is not int:
            raise TypeError "index must be an integer"
        elif idx == 0:
            return self.label
        elif idx > 0:
            return list.__getitem__(self._cache, idx-1)
        else:
            return list.__getitem__(self._cache, idx)
