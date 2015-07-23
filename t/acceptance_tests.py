import os.path
import unittest
import subprocess

php_interpreter = "php"
python_interpreter = "python"
if os.path.isfile("t/config.py"):
    import config
    php_interpreter = config.php
    python_interpreter = config.python

def comparison_factory(php_file_name):
    def unit_test_actual(self):
        dir_name, _file_name = os.path.split(php_file_name)
        file_name, ext = os.path.splitext(_file_name)
        python_file_name = os.path.join(dir_name, file_name + ".py")

        subprocess.call([python_interpreter, "php2py.py", php_file_name])
        php_result = subprocess.check_output([php_interpreter, php_file_name])
        python_result = subprocess.check_output([python_interpreter, python_file_name])
        self.assertEqual(php_result, python_result)
    return unit_test_actual


class ComparisonTests(unittest.TestCase):
    pass


tests = [
    "hello00",
    "hello01",
    "hello02",
]
for t in tests:
    test_name = "test_{}".format(t)
    php_file_name = "t/php/{}.php".format(t)
    setattr(ComparisonTests, test_name, comparison_factory(php_file_name))
