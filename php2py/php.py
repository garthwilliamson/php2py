from functools import wraps
import phpfunctions
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
        """ The wrapper function. Instantiates a subscope of p (the calling scope)

        """
        p2 = PhpContext(p.g, p.f, p.c, i=p.i)
        try:
            return f(p2, *args, **kwargs)
        except PhpWarning as e:
            # TODO: Check for a global warning should error
            print(e)
            return None
    return wrapper


########## in php.py
class PhpContext(object):
    def __init__(self, g, f, c, l=None, i=None):
        """ Initialise a new php context

        Args:
            g: A php_var object which contains the globals
            f: A php_var object which contains the functions - initialise this please!
            c: A php_var object for containing classes
            l: A php_var object for containing locals
            i: A dict with lists of files already imported

        """
        if l is None:
            l = PhpVars()
        if i is None:
            i = {}
        self.f = f
        self.g = g
        self.c = c
        self.l = l
        self.i = i


class PhpVars(object):
    def __getattr__(self, name):
        """ Apparently getattr is called after first searching to see if there is already an attribute attr

        """
        return None


class PhpFunctions(PhpVars):
    def _add_php_functions(self):
        for fname, f in phpfunctions.functionlist:
            setattr(self, fname, php_func(f))


class PhpGlobals(PhpVars):
    def __init__(self, root_dir):
        # Sets the super-global variables
        # $_POST etc
        self.__rootdir__ = root_dir

    pass
    #This be where the globals go


class PhpClasses(PhpVars):
    pass
    #This be where the classes go


def serve_up(body, root_dir):
    g = PhpGlobals(root_dir=root_dir)
    f = PhpFunctions()
    f._add_php_functions()
    c = PhpClasses()
    # Globals and locals are the same for the entry point
    p = PhpContext(g, f, c, l=g)
    body(p)
