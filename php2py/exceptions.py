class PhpException(Exception):
    pass

class PhpError(PhpException):
    pass

class PhpWarning(PhpException):
    pass

class PhpImportWarning(PhpWarning):
    pass
