from collections import OrderedDict
import urllib.parse
from typing import Callable, List
import sys
import re
import os.path

from .engine.metavars import _f_, _c_, _g_, _constants_, init_metavars


class PhpApp(object):
    """ The inner application to be eventually served up.

    Attributes:
        headers: A list of headers to be returned
        response_code: The http response code to use. Defaults to 500
        response_message: The http message to include along with the response code
        i: A dict containing information about what has already been imported
        # TODO: Is this actually used any more


    """
    def __init__(self, config: dict) -> None:
        self.config = config
        self.http_root = config["root"]
        self.code_root = config["code_root"]
        self.rewrites = []
        if "rewrites" in config:
            for r in config["rewrites"]:
                self.rewrites.append((r["match"], r["dest"]))

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

    def init_environ(self, script_name: str) -> None:
        """ Initialise the globabls and superglobals
        """
        self.g._SERVER["SCRIPT_NAME"] = script_name
        self.g._SERVER["HTTP_HOST"] = self.environ["HTTP_HOST"]

        # TODO: . and space should convert to underscores
        get = self.g._GET
        queries = urllib.parse.parse_qsl(self.environ["QUERY_STRING"])
        get.update(queries)
        self.g._REQUEST.update(queries)

        # TODO: _POST

        # TODO: _COOKIE


class WsgiApp(PhpApp):
    """ Designed to implement the wgsi specifications

    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.c.PHP_SAPI = "wsgi"

    def __call__(self, environ: dict, start_response):
        init_metavars(self)
        self.i = {}
        self.body_str = ""
        # TODO: This isn't thread safe at all
        # TODO: it probably isn't even cross request safe
        self.environ = environ
        self.rewrite()
        # PHP on the console has the script name as you'd expect.
        # On the server, there is always a leading "/"
        if "script_name" in self.config:
            script_name = self.config["script_name"]
        else:
            script_name = "/" + os.path.join(self.http_root, environ["PATH_INFO"].lstrip("/"))
        self.init_environ(script_name)
        self.f.include(script_name)
        # If body didn't change the response code, we must be ok
        if self.response_code == 500:
            self.response_code = 200
            self.response_msg = "OK"
        status = "{} {}".format(self.response_code, self.response_msg)
        headers = self.wsgi_headers()
        start_response(status, headers)
        return [self.body_str.encode("utf-8")]

    def wsgi_headers(self) -> List[str]:
        out = []
        # TODO: Deal with multiple headers
        for k, v in self.headers.items():
            out.append((k, ", ".join(v)))
        return out

    def rewrite(self) -> None:
        if len(self.rewrites) == 0:
            return
        path_query = self.environ["PATH_INFO"]
        if "QUERY_STRING" in self.environ and len(self.environ["QUERY_STRING"]) != 0:
            path_query = path_query + "?" + self.environ["QUERY_STRING"]
        for match, repl in self.rewrites:
            path_query = re.sub(match, repl, path_query)
        # TODO: Can ? appear elsewhere in the url?
        try:
            self.environ["PATH_INFO"], self.environ["QUERY_STRING"] = path_query.split("?", 1)
        except:
            self.environ["PATH_INFO"], self.environ["QUERY_STRING"] = path_query, ""


class ConsoleApp(WsgiApp):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.c.PHP_SAPI = "cli"

    def run(self):
        environ = {
            "HTTP_HOST":    '',
            "PATH_INFO":    self.config["script_name"],
            "QUERY_STRING": '',
        }
        res = self(environ, self.start_response)
        for r in res:
            sys.stdout.buffer.write(r)

    def start_response(self, status: str, headers: str) -> str:
        return ""

    def rewrite(self):
        pass
