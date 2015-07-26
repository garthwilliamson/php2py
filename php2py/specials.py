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
        # TODO: Move this to a transform, although if it were from an expression...
        if isinstance(key, str):
            try:
                key = int(key)
            except ValueError:
                pass
            if key == "MagicEmptyArrayIndex":
                # This is actually an append. Magic!
                key = self.next_index
        if isinstance(key, float):
            key = int(key)
        if key is None:
            key = ""
        self.data[key] = value
        if isinstance(key, int) and key >= self.next_index:
            self.next_index = key + 1

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self):
        return len(self.data)

    def __delitem__(self, key):
        try:
            del self.data[key]
        except KeyError:
            # TODO: Does php actually ignore this?
            pass

def clone():
    """ Clone the object.

    Performs a shallow copy. Tries to call __clone() method first

    """
    raise NotImplementedError("Clone is not implmented yet")


def die(m=0):
    sys.exit(m)


def empty(v):
    raise NotImplementedError("Probably should be done at the transform stage")


def eval(s):
    raise NotImplementedError("Eval will never be implemented probably")


def exit(m=0):
    # http://php.net/manual/en/function.exit.php
    # TODO: Check functionality
    # TODO: Run shutdown functions etc
    if isinstance(m, int):
        sys.exit(m)
    else:
        print(m)
        sys.exit(-2)


def isset(variable):
    raise NotImplementedError("Probably should be done at the transform stage")


def list(*args):
    """ Actually normally used like tuple unpacking

    This niave implementation won't work normally - it actually should be rewritten to a tuple at the
    tranformation level

    """
    raise NotImplementedError("List needs to be implemented at transform")
    # return tuple(*args)


def unset(*args):
    for name in args:
        del name


def require_once(filename):
    if filename in _app_.i:
        return
    require(filename)


def require(filename):
    try:
        include(filename)
    except PhpImportWarning as e:
        raise PhpError(e)


def include_once(filename):
    if filename in _app_.i:
        return
    include(filename)


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
