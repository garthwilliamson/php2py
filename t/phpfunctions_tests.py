import unittest
from php2py import php
from php2py.engine.metavars import init_metavars, _f_ as phpfunctions


class PhpFunctionsTests(unittest.TestCase):
    def setUp(self):
        self.app = php.PhpApp({"root": __file__})
        init_metavars(self.app)

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

    def test_explode(self):
        self.assertSequenceEqual(["a", "b"], phpfunctions.explode(" ", "a b"))
        self.assertSequenceEqual(["a", "b", "c"], phpfunctions.explode(",", "a,b,c,d", -1))

    def test_array_values(self):
        php_array = phpfunctions.array(("a", "a"), ("b", "b"))
        reindexed_array = phpfunctions.array_values(php_array)
        self.assertEqual("a", reindexed_array[0])
        self.assertEqual("b", reindexed_array[1])
        self.assertRaises(KeyError, reindexed_array.__getitem__, "a")
