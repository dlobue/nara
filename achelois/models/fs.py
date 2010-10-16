
from os.path import join, getmtime
from os import listdir
from uuid import uuid4

from sqlobject import *

class Directory(SQLObject):
    class sqlmeta:
        style = Style()
    name = StringCol(notNone=True)
    parent_dir = ForeignKey('Directory', cascade=True)
    full_path_index = DatabaseIndex('name', 'parent_dir', unique=True)
    last_modified = FloatCol(notNone=True)
    files = SQLMultipleJoin('File', joinColumn='parent_dir')
    directories = SQLMultipleJoin('Directory', joinColumn='parent_dir')

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




class File(SQLObject):
    class sqlmeta:
        style = Style()
    name = StringCol(notNone=True)
    parent_dir = ForeignKey('Directory', notNone=True, cascade=True)
    full_path_index = DatabaseIndex('name', 'parent_dir', unique=True)
    last_seen = DateTimeCol(default=DateTimeCol.now)
    uuid = StringCol(notNone=True, alternateID=True,
                     default=lambda: uuid4().hex,
                    alternateMethodName="by_uuid")

    def update_seen(self):
        self.last_seen = DateTimeCol.now()

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

