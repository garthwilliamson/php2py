from __future__ import absolute_import

import os.path

from .exceptions import *

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


def require_once(p, filename):
    if filename in p.i:
        return
    require(p, filename)


def require(p, filename):
    try:
        include(p, filename)
    except PhpImportWarning as e:
        raise PhpError(e)


def include_once(p, filename):
    if filename in p.i:
        return
    include(p, filename)


def include(p, filename):
    iname = filename.replace("/", ".")
    try:
        return "Couldn't imported if I wanted to'"
        p.i[filename] = __import__(iname)
    except ImportError:
        raise PhpImportWarning("Couldn't import {} as {}".format(filename, iname))

    # Run it in the local context
    mod.body(p)


def unset(p, name):
    del name


class stdClass(object):
    def __init__(self, p):
        self.p = p


class array(dict):
    def __init__(self, p, **kwargs):
        super(array, self).__init__(**kwargs)
        self.p = p


def py_func(f):
    def unwrapper(p, *args, **kwargs):
        return f(*args, **kwargs)
    return unwrapper


functionlist = [
    ("require_once",     require_once),
    ("isset",            isset),
    ("unset",            unset),
    ("stdClass",         stdClass),
    ("array",            array),
    ("dirname",          py_func(os.path.dirname)),
]