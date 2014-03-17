import sys
import os.path
from collections import OrderedDict
import importlib

from .exceptions import *


class array(dict):
    def __init__(self, p, **kwargs):
        super(array, self).__init__(**kwargs)
        self.p = p


def clone(p):
    """ Clone the object.

    Performs a shallow copy. Tries to call __clone() method first

    """
    raise NotImplementedError("Clone is not implmented yet")


def die(p, m=0):
    sys.exit(m)


def empty(p, v):
    raise NotImplementedError("Probably should be done at the transform stage")


def eval(p, s):
    raise NotImplementedError("Eval will never be implemented probably")


def exit(p, m=0):
    sys.exit(m)


def isset(p, variable):
    raise NotImplementedError("Probably should be done at the transform stage")


def list(p, *args):
    """ Actually normally used like tuple unpacking

    This niave implementation won't work normally - it actually should be rewritten to a tuple at the
    tranformation level

    """
    raise NotImplementedError("List needs to be implemented at transform")
    return tuple(*args)


def unset(p, name):
    del name


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


def include(p, fullpath):
    file_dir, file_name = os.path.split(fullpath)
    print(1)
    print(file_dir, file_name)
    file_n, file_ext = os.path.splitext(file_name)
    print(file_dir, p.g.__rootdir__)
    print(p.g)
    relative_path = os.path.relpath(file_dir, p.g.__rootdir__)
    path = os.path.join(relative_path, file_n)
    iname = path.replace("/", ".")
    print(iname)
    try:
        p.i[file_name] = importlib.import_module(iname)
    except ImportError:
        raise PhpImportWarning("Couldn't import {} as {}".format(fullpath, iname))

    # Run it in the local context
    mod = p.i[file_name]
    p.i[file_name].body(p)


def array(p, l):
    return OrderedDict(l)