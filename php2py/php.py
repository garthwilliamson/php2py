from collections import OrderedDict
import os.path
import sys

from .exceptions import *


class PhpVars(object):
    def __getattr__(self, name):
        """ Apparently getattr is called after first searching to see if there is already an attribute attr

        I think we have to do this because php eats undefined variables for breakfast

        """
        return None


class PhpFunctions(PhpVars):
    def __init__(self):
        for fname, f in phpfunctions.functionlist:
            setattr(self, fname, f)


class PhpGlobals(PhpVars):
    def __init__(self):
        # Sets the super-global variables
        # $_POST etc
        self._SERVER = {}
        self._GET = {}
        pass


class PhpClasses(PhpVars):
    def __init__(self):
        self.PhpBase = PhpBase


class PhpBase(object):
    """ The base class for all "php" classes"

    """
    def __init__(self, *args, **kwargs):
        self._php_construct(*args, **kwargs)

    def _php_construct(self, *args, **kwargs):
        """ _-construct is the php version of __init__

        """
        pass


class PhpConstants(PhpVars):
    def __init__(self):
        self.DIRECTORY_SEPARATOR = os.path.sep

        # Error reporting constants
        # TODO: Maybe we should just always be something like E_ALL...
        self.E_ERROR            = 1    # Fatal errors. Exit
        self.E_WARNING          = 2    # Run time errors. Don't exit
        self.E_PARSE            = 4    # Parse errors.
        self.E_NOTICE           = 8    # Run time notices. Might or might not be an actual error
        self.E_CORE_ERROR       = 16   # Errors on startup in the core
        self.E_CORE_WARNING     = 32   # Errors at startup which aren't fatal
        self.E_COMPILE_ERROR    = 64   # Fatal compile time errors
        self.E_COMPILE_WARNING  = 128  # Compile time non fatal errors
        self.E_USER_ERROR       = 256  # Fatal user error generated by trigger_error function
        self.E_USER_WARNING     = 512  # Not fatal...
        self.E_USER_NOTICE      = 1024 # Just a notice
        self.E_STRICT           = 2048 # Enables suggestions from php engine
        self.E_RECOVERABLE_ERROR= 4096 # Probably dangerous? Like an exception I think
        self.E_DEPRECATED       = 8192 # Indicated deprecated functionality at run time
        self.E_USER_DEPRECATED  = 16384
        self.E_ALL              = 32797 # All errors and warnings


class PhpApp(object):
    """ The inner application to be eventually served up.

    Attributes:
        body: A callable function that will return the body of the response
        headers: A list of headers to be returned
        response_code: The http response code to use. Defaults to 500
        response_message: The http message to include along with the response code
        f: All the functions defined in the php engine and by translated php code
        c: All the classes defined in the php engine and by translated php code
        i: A dict containing information about what has already been imported
        # TODO: Is this actually used any more


    """
    def __init__(self):
        self.body = None
        self.body_str = ""
        self._headers = OrderedDict()
        self.response_code = 500
        self.response_msg = "Server Error"

        # The php engine runs on these variables
        self.g = PhpGlobals()
        self.constants = PhpConstants()
        self.f = None
        self.c = PhpClasses()
        self.i = {}
        self.root_dir = None
        self.error_level = self.constants.E_ALL
        self.ini = {}

    def __call__(self, environ, start_response):
        self.body()
        # If body didn't change the response code, we must be ok
        if self.response_code == 500:
            self.response_code = 200
            self.response_msg = "OK"
        status = "{} {}".format(self.response_code, self.response_msg)
        headers = list(self.headers.items())
        start_response(status, headers)
        # should this be bytes?
        return [self.body_str.encode("utf-8")]

    def init_http(self, body, root_dir):
        """ Initialise the app

        Args:
            body: A callable which return a string for the body
            root_dir: The root directory this application is being served from

        """
        # HTTP
        self.body = body

        # Helpers for php engine
        self.root_dir = root_dir

        # Set POST, GET, SERVER etc variables
        # TODO: SERVER and at least some others are reserved. Should probably treat them specially.
        self.g._SERVER["HTTP_HOST"] = "TODO"
        self.g._SERVER["SCRIPT_NAME"] = "TODO"

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

    def http_headers_str(self):
        self.body()
        # If body didn't change the response code, we must be ok
        if self.response_code == 500:
            self.response_code = 200
            self.response_msg = "OK"
        out = "HTTP/1.1 {} {}".format(self.response_code, self.response_msg)
        for name in self.headers:
            for value in self.headers[name]:
                out += "\r\n{}: {}".format(name, value)
        return out

    def full_http_response(self, body, root_dir):
        self.init_http(body, root_dir)
        # Globals and locals are the same for the entry point
        try:
            print(self.http_headers_str())
            print()
            print(self.body_str, end='')
        except HttpRedirect as r:
            self.response_code = r.response_code
            print(self.http_headers_str())

    def body_http_response(self, body, root_dir):
        # Only print the body response
        # TODO: Should we allow interactive use here?
        self.init_http(body, root_dir)
        self.http_headers_str()
        # TODO: Probably should check php's default encoding
        # Write in binary mode This enables use of newlines consistent(ish) with php
        sys.stdout.buffer.write(self.body_str.encode('utf-8'))

    def write(self, item):
        # Write the item as a string to the body string
        # TODO: Build the body string much more nicely. Think about making a phpfunction called echo instead
        self.body_str += str(item)


# Using the module import to create a kind of singleton
_app_ = PhpApp()
_c_ = _app_.c
_g_ = _app_.g
_constants_ = _app_.constants

# Need to define singletons before we can import things that use them
from . import phpfunctions
_app_.f = PhpFunctions()
_f_ = _app_.f
