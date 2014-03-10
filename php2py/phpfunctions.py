from __future__ import absolute_import

import os.path


def isset(self, p, name):
    """ Check whether a value was already set

    Must be set in locals

    """
    #TODO: does being set in globals mean anything?
    try:
        p.l.__getattribute__(name)
        return True
    except AttributeError:
        return False


def get__file__(p, _file_):
    if _file_[0] == "/":
        return _file_
    else:
        return os.path.join(p.g.__rootdir__, _file_)

class stdClass(object):
    def __init__(self, p):
        self.p = p



def py_func(f):
    def unwrapper(p, *args, **kwargs):
        print args, kwargs
        return f(*args, **kwargs)
    return unwrapper


functionlist = [
    ("isset",            isset),
    ("stdClass",         stdClass),
    ("dirname",          py_func(os.path.dirname)),
    ("abspath",          py_func(os.path.abspath)),
    ("get__file__",      get__file__),
]