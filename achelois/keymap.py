#from achelois.lib.metautil import Singleton

#TODO: put key bindings into yaml or json config files

'''
configs look like this:
default = {
    context: {action: key, action: key, action: key},
    context: {action: key, action: key, action: key},
    context: {action: key, action: key, action: key},
    }

custom = {
    context: {action: key, action: key, action: key},
    context: {action: key, action: key, action: key},
    context: {action: key, action: key, action: key},
    }
'''

default = {
    'global': {
        'cursor_up': ['k', 'up'],
        'cursor_down': ['j', 'down'],
        'cursor_page_up': ['K', 'page up'],
        'cursor_page_down': ['J', 'page down'],
        'activate': [' ', 'enter'],
        },
    'read_mode': {
        'toggle_expanded': ['f'],
        'toggle_detailed': ['d'],
        'open_expanded': ['F'],
        'open_detailed': ['D'],
        'close_expanded': ['C'],
        'close_detailed': ['c'],
        },
    }
custom = {}

#class key_bind_manager(Singleton):
class key_bind_manager(object):
    """ This is a key bind manager for urwid.
    Its purpose is to centralize key configurations, and at
    the same time allow for customization by users without
    requiring knowledge of how to modify the program.
    """
    _default = {}
    _custom = {}

    @classmethod
    def __init__(cls):
        """First time we're instantiated load all settings"""
        cls.load_settings()

    @classmethod
    def load_settings(cls):
        def cmap(set_grp):
            return [('%s%s' % (ctx, key), act) for ctx in set_grp
                        for act in set_grp[ctx] for key in set_grp[ctx][act]]
        cls._default.update(cmap(default))
        cls._custom.update(cmap(custom))

    @classmethod
    def __getitem__(cls, (context, key)):
        """First look for the key asked for in the custom
        configurations. If not found, then use the default"""
        if context == 'global': nomap = 'nomap'
        else: nomap = 'global'
        try: return cls._custom['%s%s' % (context, key)]
        except KeyError:
            try: return cls._default['%s%s' % (context, key)]
            except KeyError: return nomap


kbm = key_bind_manager()

'''
actionmap = {
        'resize': {
            'key': 'window resize',
            'action': 'self.size = self.tui.get_cols_rows()',
            'help': False,
            'modes': ['all']}
        'load_all_threads': {
            'key': 'ctrl g',
            'action': 'load all threads',
            'help': 'Load all threads (this may take a while...)',
            'modes': ['index']}
}
'''
