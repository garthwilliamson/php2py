import os
import re
import string
from typing import Any, Callable, Optional

from php2py.engine.exceptions import HttpRedirect
from .phptypes import array


class Functions:
    def get__file__(self, _file_: str) ->  str:
        if _file_[0] == "/":
            return _file_
        else:
            return os.path.join(self.g.__rootdir__, _file_)

    def header(self, header: str, replace: bool = True, http_response_code: None = None) -> None:
        # TODO: Write some tests and heal with http_response_code
        if header.startswith("HTTP/"):
            # Mixed up functionality ftw
            x, error_code, error_msg = [h.strip() for h in header.split(" ")]
            self.app.response_code = error_code
            self.app.response_msg = error_msg
            return
        name, value = [h.strip() for h in header.split(":", 1)]
        if replace is True:
            self.app.replace_header(name, value)
        else:
            self.app.add_header(name, value)

        # If the header is a location header, we need to perform a redirect
        if name == "Location":
            if str(self.app.response_code)[0] != "3" and str(self.app.response_code) != "201":
                raise HttpRedirect(302)

    def define(self, name: str, value, case_insensitive=False) -> bool:
        """ Define a constant
    
        If case_insensitive is true, then we should be able to find it insensitively
    
        Returns False if constant already defined, else True
    
        # TODO: Actually implement case_insensitive
    
        """
        if case_insensitive:
            raise NotImplementedError("Whoever heard of configurable case insensitivity")
        if getattr(self.constants, name) is not None:
            return False
        setattr(self.constants, name, value)
        return True
    
    
    def error_reporting(self, level: int) -> int:
        ol = self.app.error_level
        self.app.error_level = level
        return ol
    
    
    def ini_set(self, name: str, value: str) -> str:
        old = None
        if name in self.app.ini:
            old = self.app.ini[name]
        self.app.ini[name] = value
        return old
    
    
    def str_replace(self, search: str, replace: str, subject: str, count: Optional[int] = None) -> str:
        """ Replaces instances of a string
    
        Note that this can accept either arrays of strings...........
    
        TODO: Implement arrays, check functionality
    
        """
        if count is None:
            count = -1
        if not isinstance(subject, str):
            raise NotImplementedError
        return subject.replace(search, replace, count)
    
    
    def dirname(self, d: str) -> str:
        """ Return the parent directory of the given one
    
        """
        if d[-1] in "/\\":
            d = d[:-1]
        res = os.path.dirname(d)
        if res == '':
            return '.'
        else:
            return res
    
    
    def file_exists(self, name: str) -> bool:
        # TODO: Look up url wrappers - apparently can be used with some
        return os.path.isfile(name)
    
    
    def preg_replace(self, pattern: str, replacement: str, subject: str, limit: int = -1) -> str:
        if isinstance(pattern, array) or isinstance(replacement, array):
            raise NotImplementedError("Php can take arrays as args to preg_replace")
        # TODO: There are a lot of differences between regex engines in different languages
        if limit == -1:
            limit = 0
        return re.sub(pattern, replacement, subject, limit)
    
    
    def is_string(self, item: Any) -> bool:
        # TODO: This could be a transform
        if isinstance(item, str):
            return True
        else:
            return False
    
    
    def trim(self, target: str, mask: str = string.whitespace) -> str:
        """ exactly the same as string.strip.
    
        TODO: mask can contain character ranges apparently
    
        """
        if ".." in mask:
            raise NotImplementedError("Can't do character ranges")
        return target.strip(mask)
    
    
    def filter_var(self, input: Any, filter: Callable, options: Any = None) -> Any:
        return filter(input, options)
    
    
    def explode(self, delim: str, target: str, limit: int = None) -> array:
        """ COMPLETE?
    
        """
        if limit is not None and limit < 0:
            # Negative limits mean we return all but the last n
            return target.split(delim)[:limit]
            # raise NotImplementedError("Negative limits not implemented")
        if limit == None:
            limit = -1
        return array(*target.split(delim, limit))
    
    
    def array_values(self, php_array: array) -> array:
        z = php_array.data.values()
        return array(*php_array.data.values())

    abspath = os.path.abspath
