import sys
import os.path
from collections import OrderedDict
import importlib.machinery

from .exceptions import *
from .php import _app_


class array():
    def __init__(self, *args):
        """ Args should be a series of key, value tuples

        """
        # TODO: because dicts are unordered, building an array from a dict will require a transform
        self.next_index = 0
        self.data = OrderedDict()
        self.append_many(args)

    def append_many(self, items):
        for i in items:
            self.append(i)

    def append(self, item):
            if isinstance(item, tuple):
                self[item[0]] = item[1]
            else:
                self[self.next_index] = item

    def __setitem__(self, key, value):
        """
        if key is None:
            key = self.max_index
        if isinstance(key, int):
            super(array, self).__setattr__(str(key), value)
            if key >= self.max_index:
                self.max_index = key + 1
        else:
            super(array, self).__setattr__(key, value)
        """
        # TODO: Move this to a transform, although if it were from an expression...
        if isinstance(key, str):
            try:
                key = int(key)
            except ValueError:
                pass
        if isinstance(key, float):
            key = int(key)
        if key is None:
            key = ""
        self.data[key] = value
        if isinstance(key, int) and key >= self.next_index:
            self.next_index = key + 1

    def __getitem__(self, key):
        """
        if isinstance(key, int):
            return super(array, self).__getitem__(str(key))
        else:
            return super(array, self).__getitem__(key)
        """
        return self.data[key]


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


def require(filename):
    try:
        include(filename)
    except PhpImportWarning as e:
        raise PhpError(e)


def include_once(p, filename):
    if filename in p.i:
        return
    include(p, filename)


def include(fullpath):
    # Remember, because the fullpath is calculated dynamically, this shouldn't break things on other machines
    abspath = os.path.abspath(fullpath)
    if abspath.endswith(".php"):
        abspath = abspath[0:-4] + ".py"
    try:
        _app_.i[abspath] = importlib.machinery.SourceFileLoader(abspath, abspath).load_module()
    except ImportError:
        raise PhpImportWarning("Couldn't import {} as {}".format(abspath, abspath))
    except FileNotFoundError:
        raise PhpImportWarning("Couldn't import {} as {}".format(abspath, abspath))

    # Run it in the local context
    _app_.i[abspath].body()

def echo(*strings):
    _app_.write("".join(strings))
