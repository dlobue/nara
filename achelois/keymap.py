
to do: put key bindings into yaml or json config files

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

class Singleton(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance

class key_bind_manager(Singleton):
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
            return [('%s%s' % (ctx, set_grp[ctx][act]), act)
                        for ctx in set_grp for act in set_grp[ctx]]
        cls._default.update(cmap(default))
        cls._custom.update(cmap(custom))

    @classmethod
    def __getitem__(cls, (context, key)):
        """First look for the key asked for in the custom
        configurations. If not found, then use the default"""
        try: return cls._custom['%s%s' % (context, key)]
        except KeyError:
            try: return cls._default['%s%s' % (context, key)]
            except KeyError: return 'nomap'

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
