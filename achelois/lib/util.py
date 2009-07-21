class MetaSuper(type):
    '''blatent ripoff of Urwid's MetaSuper class
    adds a .__super method I've come to depend on'''
    def __init__(cls, name, bases, d):
        super(MetaSuper, cls).__init__(name, bases, d)
        if hasattr(cls, "_%s__super" % name):
            raise AttributeError, "Class has same name as one of its super classes"
        setattr(cls, "_%s__super" % name, super(cls))
