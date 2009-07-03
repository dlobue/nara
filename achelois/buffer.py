import weakref.WeakKeyDictionary

class buffer_manager(object):
    #__metaclass__ = urwid.MetaSignals
    #signals = ['buffer_update']

    _buffers = weakref.WeakKeyDictionary()
    #_buffers = WeakKeyOrderedDict()
    _rbufferobj = None
    _supported = {}
    _noremove = []

    @classmethod
    def register_rootobj(cls, rbufferobj):
        cls._rbufferobj = rbufferobj

    @classmethod
    def register_support(cls, data_obj, buffer_obj, noremove=False):
        cls._supported.setdefault(type(data_obj), buffer_obj)
        if noremove: cls._noremove.append(buffer_obj)

    @classmethod
    def register_noremove(cls, buffer_obj):
        cls._noremove.append(buffer_obj)

    @classmethod
    def _new_buffer(cls, data):
        buffer_type = type(data)
        try: newbuffer = cls._supported[buffer_type]
        except: raise TypeError("Don't know how to make a buffer for that type of object", buffer_type, cls._supported)
        else: return cls._buffers.setdefault(data, newbuffer(data))

    @classmethod
    def get_buffer(cls, data):
        try: bufferdisp = cls._buffers[data]
        except: bufferdisp = cls._new_buffer(data)
        return bufferdisp

    @classmethod
    def set_buffer(cls, data):
        bufferdisp = cls.get_buffer(data)
        cls._rbufferobj(bufferdisp)
        return bufferdisp

    @classmethod
    def destroy(cls, data):
        if cls._buffers[data] not in cls._noremove:
            try: del cls._buffers[data]
            except: pass

