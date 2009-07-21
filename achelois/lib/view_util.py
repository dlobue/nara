
def _callback(fn):
    def wrapper(self, *args, **kwargs):
        r = fn(self, *args, **kwargs)
        self.parentmethod()
        return r
    return wrapper

class callback_list(list):
    def __hash__(self): return id(self)
    def __init__(self, parentmethod):
        self.parentmethod = parentmethod

    append = _callback(list.append)
    extend = _callback(list.extend)
    sort = _callback(list.sort)
    insert = _callback(list.insert)
    __setslice__ = _callback(list.__setslice__)
    __setitem__ = _callback(list.__setitem__)
    
