import importlib.machinery
import os
import sys
from typing import TypeVar, List, Any
from ..engine.exceptions import PhpImportWarning, PhpError

from .phptypes import PhpArray


StringOrInt = TypeVar("StringOrInt", str, int)


class Specials:
    def array(self, *args) -> PhpArray:
        return PhpArray(*args)

    def clone(self):
        """ Clone the object.

        Performs a shallow copy. Tries to call __clone() method first

        """
        raise NotImplementedError("Clone is not implmented yet")


    def die(self, m: StringOrInt = 0) -> None:
        sys.exit(m)


    def empty(self, v):
        raise NotImplementedError("Probably should be done at the transform stage")


    def eval(self, s):
        raise NotImplementedError("Eval will never be implemented probably")


    def exit(self, m: StringOrInt = 0) -> None:
        # http://php.net/manual/en/function.exit.php
        # TODO: Check functionality
        # TODO: Run shutdown functions etc
        if isinstance(m, int):
            sys.exit(m)
        else:
            print(m)
            sys.exit(-2)


    def list(self, *args):
        """ Actually normally used like tuple unpacking

        This niave implementation won't work normally - it actually should be rewritten to a tuple at the
        tranformation level

        """
        raise NotImplementedError("List needs to be implemented at transform")
        # return tuple(*args)


    def unset(self, *args: List[Any]) -> None:
        for name in args:
            del name


    def require_once(self, filename: str) -> None:
        if filename in self.app.i:
            return
        self.require(filename)


    def require(self, filename: str) -> None:
        try:
            self.include(filename)
        except PhpImportWarning as e:
            raise PhpError(e)


    def include_once(self, filename: str) -> None:
        if filename in self.app.i:
            return
        self.include(filename)


    def include(self, rel_code_path: str) -> None:
        # Remember, because the fullpath is calculated dynamically, this shouldn't break things on other machines
        # abs_code_path is probably passed in with a leading /. It is in this format to help with urls
        code_path = os.path.join(self.app.code_root, rel_code_path.lstrip("/"))
        abspath = os.path.abspath(code_path)
        if abspath.endswith(".php"):
            abspath = abspath[0:-4] + ".py"
        try:
             new_module = importlib.machinery.SourceFileLoader(abspath, abspath).load_module()
        except ImportError:
            raise PhpImportWarning("Couldn't import {} as {}".format(abspath, abspath))
        except FileNotFoundError:
            raise PhpImportWarning("Couldn't import {} as {}".format(abspath, abspath))
        # new_module._f_ = self.f
        # new_module._g_ = self.g
        # new_module._c_ = self.c
        new_module._app_ = self.app
        # new_module._constants_ = self.constants

        # Run it in the local context
        new_module.body()

        # Record that this import has happened
        self.app.i[abspath] = new_module

    def echo(self, *strings: List[str]):
        self.app.write("".join(strings))
