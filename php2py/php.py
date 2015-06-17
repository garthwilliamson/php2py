from functools import wraps
from collections import OrderedDict

from . import phpfunctions
from .exceptions import *


def php_func(f):
    """ Wrap a function f in a context. F should take a scope as its first argument

    Args:
        f: The function to wrap

    Returns:
        the functions wrapped
    """
    @wraps(f)
    def wrapper(p, *args, **kwargs):
        """ The wrapper function. Instantiates a sub-scope of p (the calling scope)

        """
        p2 = PhpContext(p.app, p.f, p.c, i=p.i)
        try:
            return f(p2, *args, **kwargs)
        except PhpWarning as e:
            # TODO: Check for a global warning should error
            print(e)
            return None
    return wrapper


class PhpContext(object):
    def __init__(self, app, f=None, c=None, i=None):
        """ Initialise a new php context

        Args:
            app: A wsgi application object
            f: A php_var object which contains the functions
            c: A php_var object for containing classes
            l: A php_var object for containing locals
            g: A php_var object for containing Globals
            i: A dict with lists of files already imported

        If f is set to None, assume this is the top level instantiation and create all the other variables

        If l is set to something other than None,
        """
        self.g = app.g
        self.app = app

        if f is None:
            # At the top level, f should hold all the available php functions
            f = PhpFunctions()
            # c should hold all the classes
            c = PhpClasses()
            # There are no imports yet
            i = {}
            # And I _think_ locals are the same as globals here
            l = self.g
        else:
            # Everywhere except global scope, locals are locals!
            l = PhpVars()
        self.f = f
        self.c = c
        self.l = l
        self.i = i


class PhpVars(object):
    def __getattr__(self, name):
        """ Apparently getattr is called after first searching to see if there is already an attribute attr

        """
        return None


class PhpFunctions(PhpVars):
    def __init__(self):
        for fname, f in phpfunctions.functionlist:
            setattr(self, fname, php_func(f))


class PhpGlobals(PhpVars):
    def __init__(self):
        # Sets the super-global variables
        # $_POST etc
        pass


class PhpClasses(PhpVars):
    pass
    # This be where the classes go


class PhpApp(object):
    """ The inner application to be eventually served up.

    Attributes:
        headers: A list of headers to be returned
        response_code: The http response code to use. Defaults to 500

    """
    def __init__(self, body, root_dir):
        """ Initialise the app

        Args:
            body: A callable which return a string for the body
            root_dir: The root directory this application is being served from

        """
        self.body = body
        self.root_dir = root_dir
        self._headers = OrderedDict()
        self.response_code = 500
        self.response_msg = "Server Error"
        self.p = None
        self.g = None
        self.body_str = ""
        self._initialise_context()  # TODO: Here for now. Think about it.

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

    def _initialise_context(self):
        self.g = PhpGlobals()
        self.p = PhpContext(self)

    def http_headers_str(self):
        self.body_str = self.body(self.p)
        out = "HTTP/1.1 {} {}".format(self.response_code, self.response_msg)
        for name in self.headers:
            for value in self.headers[name]:
                out += "\r\n{}: {}".format(name, value)
        return out


def serve_up(body, root_dir):
    app = PhpApp(body, root_dir)
    # Globals and locals are the same for the entry point
    try:
        print(app.http_headers_str())
        print()
        print(app.body_str)
    except HttpRedirect as r:
        app.response_code = r.response_code
        print(app.http_headers_str())