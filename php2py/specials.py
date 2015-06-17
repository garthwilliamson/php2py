import sys
import os.path
from collections import OrderedDict
import importlib.machinery

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
    # http://php.net/manual/en/function.exit.php
    # TODO: Check functionality
    # TODO: Run shutdown functions etc
    if isinstance(m, int):
        sys.exit(m)
    else:
        print(m)
        sys.exit(-2)


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
    # Remember, because the fullpath is calculated dynamically, this shouldn't break things on other machines
    abspath = os.path.abspath(fullpath)
    if abspath.endswith(".php"):
        abspath = abspath[0:-4] + ".py"
    try:
        p.i[abspath] = importlib.machinery.SourceFileLoader(abspath, abspath).load_module()
    except ImportError:
        raise PhpImportWarning("Couldn't import {} as {}".format(abspath, abspath))
    except FileNotFoundError:
        raise PhpImportWarning("Couldn't import {} as {}".format(abspath, abspath))

    # Run it in the local context
    p.i[abspath].body(p)


def array(p, l):
    return OrderedDict(l)

