from __future__ import absolute_import

import os.path

from .exceptions import *


def isset(p, name):
    """ Check whether a value was already set

    Must be set in locals

    """
    # TODO: does being set in globals mean anything?
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


def header(p, header: str, replace=True, http_response_code=None):
    if header.startswith("HTTP/"):
        # Mixed up functionality ftw
        x, error_code, error_msg = [h.strip() for h in header.split(" ")]
        p.app.response_code = error_code
        p.app.response_msg = error_msg
        return
    name, value = [h.strip() for h in header.split(":")]
    if replace == True:
        p.app.replace_header(name, value)
    else:
        p.app.add_header(name, value)

    # If the header is a location header, we need to perform a redirect
    if name == "Location":
        if str(p.app.response_code)[0] != "3" and str(p.app.response_code) != "201":
            raise HttpRedirect(302)

def py_func(f):
    def unwrapper(p, *args, **kwargs):
        print(args, kwargs)
        return f(*args, **kwargs)

    return unwrapper


def define(p, name: str, value):
    setattr(p.constants, name, value)


def error_reporting(p, level: int) -> int:
    ol = p.app.error_level
    p.app.error_level = level
    return ol


def ini_set(p, name: str, value: str) -> str:
    old = None
    if name in p.app.ini:
        old = p.app.ini[name]
    p.app.ini[name] = value
    return old


functionlist = [
    ("isset", isset),
    ("stdClass", stdClass),
    ("dirname", py_func(os.path.dirname)),
    ("abspath", py_func(os.path.abspath)),
    ("file_exists", py_func(os.path.isfile)), # http://php.net/manual/en/function.file-exists.php
    ("get__file__", get__file__),
    ("header", header), # http://php.net/manual/en/function.header.php
    ("define", define),
    ("error_reporting", error_reporting), # http://php.net/manual/en/function.error-reporting.php
    ("ini_set", ini_set), # http://php.net/manual/en/function.ini-set.php
]
