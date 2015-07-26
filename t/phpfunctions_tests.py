import unittest
from php2py import php, phpfunctions


class PhpFunctionsTests(unittest.TestCase):
    def setUp(self):
        self.app = php.PhpApp()
        phpfunctions._app_ = self.app

    def test_define(self):
        predef = phpfunctions.define("YOHOHO", "A bottle of rum")
        self.assertIs(True, predef)
        self.assertIs(False, phpfunctions.define("YOHOHO", "A pirates life for me"))
        self.assertEqual("A bottle of rum", self.app.constants.YOHOHO)
        self.assertRaises(NotImplementedError,
                          phpfunctions.define,
                          "AnyOldCaps", "are acceptable", case_insensitive=True)

    def test_dirname(self):
        self.assertEqual(".", phpfunctions.dirname("hello.py"))
        self.assertEqual("somewhere", phpfunctions.dirname("somewhere/a/"))
        self.assertEqual("somewhere", phpfunctions.dirname("somewhere\\a"))
        self.assertEqual("/", phpfunctions.dirname("/etc/"))
        self.assertEqual("somewhere/else", phpfunctions.dirname("somewhere/else/a"))

    def test_file_exists(self):
        self.assertTrue(phpfunctions.file_exists("php2py.py"))
        self.assertFalse(phpfunctions.file_exists("THISFILEDONTEXISTS"))

    def test_trim(self):
        self.assertEqual("a", phpfunctions.trim(" a "))
        self.assertEqual(" lo", phpfunctions.trim(" lol", "l"))
        self.assertRaises(NotImplementedError, phpfunctions.trim, "lol", "a..g")
