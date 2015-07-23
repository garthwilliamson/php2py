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
