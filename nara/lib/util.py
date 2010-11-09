from functools import wraps
from cPickle import dumps

class MetaSuper(type):
    '''blatent ripoff of Urwid's MetaSuper class
    adds a .__super method I've come to depend on'''
    def __init__(cls, name, bases, d):
        super(MetaSuper, cls).__init__(name, bases, d)
        if hasattr(cls, "_%s__super" % name):
            raise AttributeError, "Class has same name as one of its super classes"
        setattr(cls, "_%s__super" % name, super(cls))

def static_memoize(fctn):
    @wraps(fctn)
    def memo(self):
        cached_mthd_name = '__%s_%s_cache' % (fctn.im_class.__name__,
                                              fctn.im_func.func_name)
        if hasattr(self, cached_mthd_name):
            return getattr(self, cached_mthd_name)

        v = fctn(self)
        setattr(self, cached_mthd_name, v)

        return v
    if memo.__doc__:
        memo.__doc__ = "\n".join([memo.__doc__,"This function is memoized."])
    return memo


def memoize(fctn):
    memory = {}
    @wraps(fctn)
    def memo(*args,**kwargs):
        haxh = dumps((args, sorted(kwargs.iteritems())))

        if haxh not in memory:
            r = fctn(*args,**kwargs)
            if r is not None:
                memory[haxh] = r

        return memory[haxh]
    if memo.__doc__:
        memo.__doc__ = "\n".join([memo.__doc__,"This function is memoized."])
    return memo

