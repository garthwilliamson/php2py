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
        p2 = PhpContext(p.f, p.c, i=p.i)
        try:
            return f(p2, *args, **kwargs)
        except PhpWarning as e:
            # TODO: Check for a global warning should error
            print(e)
            return None
    return wrapper


########## in php.py
class PhpContext(object):
    def __init__(self, f, c, l=None, i=None):
        """ Initialise a new php context

        Args:
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
        self.c = c
        self.l = l
        self.i = i
        global g
        self.g = g


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
    def __init__(self):
        # Sets the super-global variables
        # $_POST etc
        pass


class PhpClasses(PhpVars):
    pass
    #This be where the classes go


# g stores the php global variables
g = PhpGlobals()


def serve_up(body, root_dir):
    global g
    g.__rootdir__ = root_dir
    print(g)
    f = PhpFunctions()
    f._add_php_functions()
    c = PhpClasses()
    # Globals and locals are the same for the entry point
    p = PhpContext(f, c, l=g)
    body(p)
