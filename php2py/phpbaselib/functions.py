import os
import re
import string
from typing import Any, Callable, Optional, Union

from php2py.engine.exceptions import HttpRedirect
from .phptypes import PhpArray


class Functions:

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

    def preg_replace(self, pattern: str, replacement: str, subject: str, limit: int = -1) -> str:
        if isinstance(pattern, PhpArray) or isinstance(replacement, PhpArray):
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

    def explode(self, delim: str, target: str, limit: int = None) -> PhpArray:
        """ COMPLETE?
    
        """
        if limit is not None and limit < 0:
            # Negative limits mean we return all but the last n
            return target.split(delim)[:limit]
            # raise NotImplementedError("Negative limits not implemented")
        if limit == None:
            limit = -1
        return PhpArray(*target.split(delim, limit))

    def array_values(self, php_array: PhpArray) -> PhpArray:
        z = php_array.data.values()
        return PhpArray(*php_array.data.values())

    def method_exists(self, obj: Any, method_name: str) -> bool:
        if isinstance(obj, str):
            obj = getattr(self.c, obj)
        try:
            m = getattr(obj, method_name)
            if callable(m):
                return True
            else:
                return False
        except:
            return False

    def strlen(self, s: str) -> int:
        # TODO: should return number of bytes rather than chars
        # TODO: Work out if None is actually allowed in php
        if s is None:
            return 0
        return len(s)

    abspath = os.path.abspath

    def get_included_files(self) -> PhpArray:
        raise NotImplementedError()

    get_required_files = get_included_files

    def getenv(self, varname: str) -> str:
        """ The value of the environment variable varname

        These might just be the contents of the _SERVER array?
        """
        # TODO: Return false if variable doesn't exist
        return self.app.c._SERVER[varname]

    def putenv(self, setting: str) -> bool:
        """ Puts setting into _SERVER

        setting is like ABC=1234

        """
        raise NotImplementedError()

    def getlastmod(self) -> int:
        """ A unix timestamp of when the main script was last modified

        """
        raise NotImplementedError()

    def getopt(self, options: str, longopts: PhpArray = None) -> PhpArray:
        """ Basically optparse

        """
        raise NotImplementedError()

    def getrusage(self, who: int = 0) -> PhpArray:
        """ see getrusage(2)

        """
        raise NotImplementedError()

    def memory_get_peak_usage(self, real_usage: bool = False) -> int:
        raise NotImplementedError()

    def memory_get_usage(self, real_usage: bool = False) -> int:
        raise NotImplementedError()

    def php_sapi_name(self) -> str:
        """ A string indicating the wrapper being used.

        """
        return self.c.PHP_SAPI

    def zend_thread_id(self) -> int:
        raise DeprecationWarning("Never will be implemented")

    def zend_version(self) -> str:
        # TODO: What's an appropriate version to hardcode here?
        raise NotImplementedError()
    
    ################### Error reporting functions ################

    def debug_backktrace(self, *args):
        raise DeprecationWarning("This function won't be implemented. Use ... instead")

    debug_print_backtrace = debug_backktrace

    def error_get_last(self) -> PhpArray:
        raise NotImplementedError()

    def error_log(self,
                  message: str,
                  message_type: int = 0,
                  destination: str = None,
                  extra_headers: str = None):
        raise NotImplementedError()

    def error_reporting(self, level: int) -> int:
        ol = self.app.error_level
        self.app.error_level = level
        return ol

    def restore_error_handler(self) -> bool:
        raise NotImplementedError()

    def restore_exception_handler(self) -> bool:
        raise NotImplementedError()

    def set_error_handler(self, error_handler: callable, error_types: int = None) -> Any:
        if error_types is None:
            error_types = self.app.c.E_ALL | self.app.c.E_STRICT
            raise NotImplementedError()

    def set_exception_handler(self, exception_handler: callable) -> callable:
        raise NotImplementedError()

    def trigger_error(self, error_msg: str, error_type: int = None) -> bool:
        if error_type is None:
            error_type = self.app.c.E_USER_NOTICE
        raise NotImplementedError()

    user_error = trigger_error

    ############# Extension loading ##############

    def extension_loaded(self, name: str) -> bool:
        """ Is the extension called name loaded?

        """
        # TODO: As extensions are implemented, return True as appropriate
        return False

    def get_extension_funcs(self, module_name: str) -> PhpArray:
        """ The name of all functions defined in module_name

        """
        raise NotImplementedError()

    def get_loaded_extensions(self, zend_extensions: bool = False) -> PhpArray:
        """ the loaded extensions

        if zend_extensions is False, then return the normal extensions loaded.

        """
        if zend_extensions == True:
            raise DeprecationWarning("Zend extensions are unlikely to be supported")
        raise NotImplementedError()

    ############### Config settings ##############

    def get_cfg_var(self, option: str) -> str:
        raise NotImplementedError()

    def get_current_user(self) -> str:
        return os.getlogin()

    def getmygid(self) -> Union(int, False):
        try:
            return os.getgid()
        except:
            return False

    def getmyuid(self) -> int:
        try:
            return os.getuid()
        except:
            return False

    def getmyinode(self) -> int:
        """ The inode of the current script. False if error.

        """
        raise NotImplementedError()

    def getmypid(self) -> int:
        return os.getpid()

    def php_uname(self, mode: str = "a") -> str:
        """ Kinda like uname

        modes:
        a: all the below
        s: OS Name (os.name?)
        n: Host name
        r: Release name
        v: Version information
        m: cpu architecture

        """
        raise NotImplementedError()

    def phpcredits(self, *args) -> None:
        raise DeprecationWarning("Unlikely to be implemented")

    phpinfo = phpcredits

    def phpversion(self, extension: str = None) -> str:
        if extension is not None:
            raise NotImplementedError()
        return self.c.PHP_VERSION

    def version_compare(self,
                        version1: str,
                        version2: str,
                        operator: str = None) -> Any:
        raise NotImplementedError()

    def get_include_path(self) -> str:
        raise NotImplementedError()

    def set_include_path(self, new_include_path: str) -> str:
        """ Sets the include path, backing up the value

        returns the old include path

        """
        raise NotImplementedError()

    def restore_include_path(self) -> None:
        """ Restore the include path back to its original value

        """
        raise NotImplementedError()

    def ini_set(self, name: str, value: str) -> str:
        # TODO: Set the old value somewhere so we can use restore on it
        old = None
        if name in self.app.ini:
            old = self.app.ini[name]
        self.app.ini[name] = value
        return old

    ini_alter = ini_set

    def ini_get_all(self, extension: str, details: bool = True) -> PhpArray:
        """ All of the config options

        """
        raise NotImplementedError()

    def ini_get(self, varname: str) -> Union[str, bool]:
        raise NotImplementedError()
        """if varname in self.app.ini:
            return self.app.ini[varname]
        else:
            return False"""

    def ini_restore(self, varname) -> None:
        """ Restore the original value to an ini setting

        """
        raise NotImplementedError()

    def php_ini_loaded_file(self) -> Union[bool, str]:
        """ Location of the ini file used

        returns False is no ini file was loaded

        """
        return False

    def php_ini_scanned_files(self) -> Union[bool, str]:
        """ Additional ini files loaded

        Returns false if no additional ini files were loaded

        """
        return False

    def get_magic_quotes_gpc(self) -> bool:
        """ Magic quotes are treated as in php > 5.4. i.e. the don't exist

        """
        return False

    get_magic_quotes_runtime = get_magic_quotes_gpc

    def set_magic_quotes_gpc(self, *args) -> None:
        raise DeprecationWarning("This will never be made available")

    set_magic_quotes_runtime = set_magic_quotes_gpc
    magic_quotes_runtime = set_magic_quotes_runtime

    def php_logo_guid(self):
        raise DeprecationWarning("Never will be implemented")

    zend_logo_guid = php_logo_guid

    def set_time_limit(self, seconds: int) -> bool:
        """ Sets the time limit for script execution

        Default is meant to be 30 seconds

        """
        raise NotImplementedError()

    ################## Constants ##################

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

    def get_defined_constants(self, categorize: bool = False) -> PhpArray:
        """ Return an array of all known constants

        """
        if categorize:
            raise DeprecationWarning("Categorize will probably never be implemented")
        raise NotImplementedError()

    #################### Paths and directories ####################

    def dirname(self, d: str) -> str:
        """ Return the parent directory of the given one

        """
        if d == "":
            return ""
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

    def sys_get_temp_dir(self) -> str:
        raise NotImplementedError()

    def get__file__(self, _file_: str) ->  str:
        if _file_[0] == "/":
            return _file_
        else:
            return os.path.join(self.g.__rootdir__, _file_)

    ############### Hashing functions ################

    def hash_algos(self) -> PhpArray:
        return PhpArray("md5")

    def hash_copy(self, context: Any) -> Any:
        raise NotImplementedError()

    def hash_final(self, context: Any, raw_output: bool = False) -> str:
        raise NotImplementedError()

    def hash_file(self,
                  algo: str,
                  filename: str,
                  raw_output: bool = False) -> str:
        if raw_output:
            raise NotImplementedError()
        import hashlib
        h = hashlib.new(open(filename, "b").readall())
        return h.hexdigest()

    def hash_hmac_file(self, algo: str, filename: str, ):
