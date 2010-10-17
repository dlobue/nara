from weakref import WeakValueDictionary

class buffer_manager(object):

    _buffers = WeakValueDictionary()
    _rbufferobj = None
    _supported = {}
    _noremove = []
    _current = None
    _order = []

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
        if bufferdisp not in cls._order:
            cls._order.append(bufferdisp)
        return bufferdisp

    @classmethod
    def set_buffer(cls, data):
        bufferdisp = cls.get_buffer(data)
        cls._current = bufferdisp
        cls._rbufferobj(bufferdisp)
        return bufferdisp

    @classmethod
    def set_next(cls, data=None):
        if data:
            bufferdisp = cls.get_buffer(data)
        else:
            bufferdisp = cls._current
        idx = cls._order.index(bufferdisp)
        try: bufferdisp = cls._order[idx+1]
        except IndexError: bufferdisp = cls._order[0]
        cls._current = bufferdisp
        cls._rbufferobj(bufferdisp)
        return bufferdisp

    @classmethod
    def set_prev(cls, data=None):
        if data:
            bufferdisp = cls.get_buffer(data)
        else:
            bufferdisp = cls._current
        idx = cls._order.index(bufferdisp)
        bufferdisp = cls._order[idx-1]
        cls._current = bufferdisp
        cls._rbufferobj(bufferdisp)
        return bufferdisp

    @classmethod
    def destroy(cls, data=None):
        if not data:
            data = cls._current
            if data not in cls._noremove:
                cls.set_prev()
                data._invalidate()
                __tmp = []
                for d in cls._buffers.iteritems():
                    if data in d:
                        __tmp.append(d[0])
                map(lambda x: cls._buffers.__delitem__(x), __tmp)
                del cls._order[cls._order.index(data)]
                del data
        else:
            if cls._buffers[data] not in cls._noremove:
                try:
                    cls.set_prev(data)
                    data._invalidate()
                    del cls._order[cls._order.index(cls._buffers[data])]
                    del cls._buffers[data]
                except: pass

