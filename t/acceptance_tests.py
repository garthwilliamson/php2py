import os.path
import unittest
import subprocess
import logging

logging.basicConfig(level=logging.INFO)

php_interpreter = "php"
python_interpreter = "python"
if os.path.isfile("t/config.py"):
    import config
    php_interpreter = config.php
    python_interpreter = config.python


def comparison_factory(php_file_name):
    def unit_test_actual(self):
        subprocess.call([python_interpreter, "php2py.py", php_file_name])
        php_result = subprocess.check_output([php_interpreter, php_file_name])
        python_result = subprocess.check_output([python_interpreter, "php2py_run.py", php_file_name])
        self.assertSequenceEqual(php_result.split(b"\n"), python_result.split(b"\n"))
    return unit_test_actual


class ComparisonTests(unittest.TestCase):
    pass


# TODO: autogeneration of list
tests = [
    "hello00",
    "hello01",
    "hello02",
    "defines00",
    "defines01",
]
for t in tests:
    test_name = "test_{}".format(t)
    php_file_name = "t/php/{}.php".format(t)
    setattr(ComparisonTests, test_name, comparison_factory(php_file_name))
