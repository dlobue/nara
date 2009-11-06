
m operator import itemgetter
sorted(d.iteritems(), key=itemgetter(1))


import anydbm
import cPickle as pickle

class pdict(object):
    """ A persistent, lazy, caching, dictionary, using the anydbm module for 
    persistence. Keys must be basic strings (this is an anydbm limitation) and
    values must be pickle-able objects. """
    def __init__(self, file, mode):
        """ Create new pdict using file. mode is passed to anydbm.open(). """
        self._cache = {}
        self._flush = {}
        self._dbm = anydbm.open(file, mode)

    def iterkeys(self):
        __f_keys = self._flush.iterkeys()
        __db_keys = self._dbm.iterkeys()
        #__new_keys = []
        #for __k in __f_keys:
            #try: self._dbm[__k]
            #except: __new_keys.append(__k)
        return iter(set((__f_keys, __db_keys)))

    def __contains__(self, key):
        return key in self._cache or key in self._dbm

    def __getitem__(self, key):
        try: return self._cache[key]
        except: return self._cache.setdefault(key, pickle.loads(self._dbm[key]))

        if key in self._cache:
            return self._cache[key]
        return self._cache.setdefault(key, pickle.loads(self._dbm[key]))

    def __setitem__(self, key, value):
        self._cache[key] = self._flush[key] = value

    def __delitem__(self, key):
        found = False
        for data in (self._cache, self._flush, self._dbm):
            if key in data:
                del data[key]
                found = True
        if not found:
            raise KeyError(key)

    def keys(self):
        keys = set(self._cache.keys())
        keys.update(self._dbm.keys())
        return keys

    def sync(self):
        for key, value in self._flush.iteritems():
            self._dbm[key] = pickle.dumps(value, 2)
        self._dbm.sync()
        self._flush = {}
