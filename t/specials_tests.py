import unittest
from php2py import php, specials


class SpecialsTests(unittest.TestCase):
    def setUp(self):
        self.app = php.PhpApp()
        specials._app_ = self.app

    def test_echo(self):
        specials.echo("hello")
        self.assertEqual("hello", self.app.body_str)

    def test_echo_again(self):
        specials.echo("hello again")
        self.assertEqual("hello again", self.app.body_str)

    def test_echo_multi_arg(self):
        specials.echo("A", "B", "C")
        self.assertEqual("ABC", self.app.body_str)
