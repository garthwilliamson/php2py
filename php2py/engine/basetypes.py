class PhpBase(object):
    """ The base class for all "php" classes"

    """
    def __init__(self, *args, **kwargs):
        self._php_construct(*args, **kwargs)

    def _php_construct(self, *args, **kwargs):
        """ _-construct is the php version of __init__

        """
        pass

    def __str__(self):
        return "Object"
