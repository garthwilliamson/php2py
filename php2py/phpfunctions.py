from __future__ import absolute_import

import os.path
import re

from .exceptions import *
from php2py.php import _g_, _app_, _constants_
from .specials import *

#def isset(name):
#    """ Check whether a value was already set
#
#    Must be set in locals
#
#    """
#    # TODO: does being set in globals mean anything?
#    try:
#        # TODO: We aren't using .l any  more
#        p.l.__getattribute__(name)
#        return True
#    except AttributeError:
#        return False


def get__file__(_file_):
    if _file_[0] == "/":
        return _file_
    else:
        return os.path.join(_g_.__rootdir__, _file_)


class stdClass(object):
    def __init__(self, p):
        self.p = p


def header(header: str, replace=True, http_response_code=None):
    if header.startswith("HTTP/"):
        # Mixed up functionality ftw
        x, error_code, error_msg = [h.strip() for h in header.split(" ")]
        _app_.response_code = error_code
        _app_.response_msg = error_msg
        return
    name, value = [h.strip() for h in header.split(":")]
    if replace is True:
        _app_.replace_header(name, value)
    else:
        _app_.add_header(name, value)

    # If the header is a location header, we need to perform a redirect
    if name == "Location":
        if str(_app_.response_code)[0] != "3" and str(_app_.response_code) != "201":
            raise HttpRedirect(302)


def define(name: str, value, case_insensitive=False) -> bool:
    """ Define a constant

    If case_insensitive is true, then we should be able to find it insensitively

    Returns False if constant already defined, else True

    # TODO: Actually implement case_insensitive

    """
    if case_insensitive:
        raise NotImplementedError("Whoever heard of configurable case insensitivity")
    if getattr(_app_.constants, name) is not None:
        return False
    setattr(_app_.constants, name, value)
    return True


def error_reporting(level: int) -> int:
    ol = _app_.error_level
    _app_.error_level = level
    return ol


def ini_set(name: str, value: str) -> str:
    old = None
    if name in _app_.ini:
        old = _app_.ini[name]
    _app_.ini[name] = value
    return old


def str_replace(search, replace, subject, count=0):
    """ Replaces instances of a string

    Note that this can accept either arrays of strings...........

    TODO: Implement arrays, check functionality

    """
    if not isinstance(subject, str):
        raise NotImplementedError
    return subject.replace(search, replace, count)


def dirname(d: str) -> str:
    """ Return the parent directory of the given one

    """
    if d[-1] in "/\\":
        d = d[:-1]
    res = os.path.dirname(d)
    if res == '':
        return '.'
    else:
        return res


def file_exists(name: str) -> bool:
    # TODO: Look up url wrappers - apparently can be used with some
    return os.path.isfile(name)


def preg_replace(pattern, replacement, subject, limit: int = -1):
    if isinstance(pattern, array) or isinstance(replacement, array):
        raise NotImplementedError("Php can take arrays as args to preg_replace")
    # TODO: There are a lot of differences between regex engines in different languages
    if limit == -1:
        limit = 0
    return re.sub(pattern, replacement, subject, limit)


def is_string(self, item):
    # TODO: This could be a transform
    if isinstance(item, str):
        return True
    else:
        return False


functionlist = [
#    ("isset", isset),
    ("stdClass", stdClass),
    ("dirname", dirname),
    ("abspath", os.path.abspath),
    ("file_exists", os.path.isfile), # http://php.net/manual/en/function.file-exists.php
    ("get__file__", get__file__),
    ("header", header), # http://php.net/manual/en/function.header.php
    ("define", define),
    ("error_reporting", error_reporting), # http://php.net/manual/en/function.error-reporting.php
    ("ini_set", ini_set), # http://php.net/manual/en/function.ini-set.php
    ("str_replace", str_replace), # http://php.net/manual/en/function.str-replace.php
]
