
from os.path import join, getmtime
from os import listdir

from sqlobject import *


class _Record(SQLObject):
    class sqlmeta:
        style = Style()
    name = StringCol(notNone=True)
    parent_dir = ForeignKey('Directory', cascade=True)
    full_path_index = DatabaseIndex('name', 'parent_dir', unique=True)

    def _get_full_path(self):
        try:
            return self.__cached_path
        except AttributeError:
            p = [self.name]
            r = self
            while 1:
                r = r.parent_dir
                if r is None:
                    self.__cached_path = fpath = join(*p)
                    return fpath
                p.insert(0, r.name)
    

class Directory(_Record):
    files = SQLMultipleJoin('File', joinColumn='parent_dir')
    directories = SQLMultipleJoin('Directory', joinColumn='parent_dir')
    last_modified = FloatCol(notNone=True)

    def listdir(self):
        return iter(listdir(self.full_path))

    def _get_has_changed(self):
        new_mtime = getmtime(self.full_path)
        if self.last_modified != new_mtime:
            self.last_modified = new_mtime
            return new_mtime
        return False
    
    _doc_has_changed = """
    If there are no changes returns False. If files have 
    been removed or added, returns the new modified timestamp.
    """


class File(_Record):
    was_seen = BoolCol(notNone=True)

    def update_seen(self):
        self.was_seen = r = not self.was_seen
        return r

