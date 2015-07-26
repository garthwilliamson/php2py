from collections import OrderedDict
import importlib.machinery
import os.path
import urllib.parse
from typing import Callable
import sys

from .engine.metavars import _f_, _c_, _g_, _constants_, init_metavars


class PhpApp(object):
    """ The inner application to be eventually served up.

    Attributes:
        script_name: The name of the script we are running
        headers: A list of headers to be returned
        response_code: The http response code to use. Defaults to 500
        response_message: The http message to include along with the response code
        i: A dict containing information about what has already been imported
        # TODO: Is this actually used any more


    """
    def __init__(self, script_name: str) -> None:
        self.script_name = script_name

        # TODO: body_str should be replaced with an iterable - list probably
        self.body_str = ""
        self.environ = {}
        self._headers = OrderedDict()
        self.response_code = 500
        self.response_msg = "Server Error"

        # The php engine runs on these variables
        self.i = {}
        self.ini = {}

        # Get the meta variables for convenient access
        self.g = _g_
        self.constants = _constants_
        self.f = _f_
        self.c = _c_

        # TODO: If actually needed, this can be used to decide what exception to ignore
        self.error_level = self.constants.E_ALL

    def write(self, item):
        # Write the item as a string to the body string
        # TODO: Build the body string much more nicely. Think about making a phpfunction called echo instead
        self.body_str += str(item)

    # TODO: You are doing this wrong?
    @property
    def headers(self):
        return self._headers

    def add_header(self, name, value):
        """ Add  a new header to be output when used as a wsgi app

        Params:
            name: The name of the header to add
            value: The value the header should take

        This function will add additional  headers of the same name

        """
        if name in self._headers:
            self.headers[name].append(value)
        else:
            self.headers[name] = [value]

    def replace_header(self, name, value):
        """ Add  a new header to be output when used as a wsgi app

        Params:
            name: The name of the header to add
            value: The value the header should take

        This function will replace any existing headers called name

        """
        self.headers[name] = [value]

    def init_environ(self):
        """ Initialise the globabls and superglobals
        """
        self.g._SERVER["HTTP_HOST"] = self.environ["HTTP_HOST"]
        # TODO: Get this from wsgi server somehow
        # TODO: This is a hack to get things working. I think I'll need to use a full routing library in future
        self.g._SERVER["SCRIPT_NAME"] = self.script_name
        get = self.g._GET
        get["url"] = self.environ["PATH_INFO"]
        queries = urllib.parse.parse_qs(self.environ["QUERY_STRING"])
        get.update(queries)


class WsgiApp(PhpApp):
    """ Designed to implement the wgsi specifications

    """
    def __call__(self, environ: dict, start_response: Callable):
        init_metavars(self)
        self.i = {}
        self.body_str = ""
        # TODO: This isn't thread safe at all
        # TODO: it probably isn't even cross request safe
        self.environ = environ
        self.init_environ()
        self.f.include(self.script_name)
        # If body didn't change the response code, we must be ok
        if self.response_code == 500:
            self.response_code = 200
            self.response_msg = "OK"
        status = "{} {}".format(self.response_code, self.response_msg)
        headers = list(self.headers.items())
        start_response(status, headers)
        return [self.body_str.encode("utf-8")]


class ConsoleApp(WsgiApp):
    def run(self):
        environ = {
            "HTTP_HOST":    '',
            "PATH_INFO": '',
            "QUERY_STRING": '',
        }
        res = self(environ, self.start_response)
        for r in res:
            sys.stdout.buffer.write(r)

    def start_response(self, status: str, headers: str) -> str:
        return ""
