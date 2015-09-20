class PhpException(Exception):
    pass


class PhpError(PhpException):
    pass


class PhpWarning(PhpException):
    pass


class PhpImportWarning(PhpWarning):
    pass


class HttpRedirect(Exception):
    def __init__(self, response_code):
        self.response_code = response_code


class PDOException(PhpException):
    pass
