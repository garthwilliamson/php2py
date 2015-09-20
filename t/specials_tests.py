import unittest

from php2py.engine.metavars import init_metavars, _f_ as specials
from php2py import php


class SpecialsTests(unittest.TestCase):
    def setUp(self):
        self.app = php.PhpApp({"root": __file__, "code_root": "./"})
        init_metavars(self.app)

    def test_echo(self):
        specials.echo("hello")
        self.assertEqual("hello", self.app.body_str)

    def test_echo_again(self):
        specials.echo("hello again")
        self.assertEqual("hello again", self.app.body_str)

    def test_echo_multi_arg(self):
        specials.echo("A", "B", "C")
        self.assertEqual("ABC", self.app.body_str)

    def test_array(self):
        a = specials.array(("a", "b"))
        self.assertEqual("b", a["a"])
        b = specials.array(("a", 1), ("b", 2))
        self.assertEqual(2, b["b"])
        c = specials.array((1, "a"), (2, "b"))
        self.assertEqual("a", c[1])

    def test_array_key_cast(self):
        """ Php arrays are fun. They can cast keys...

        """
        a = specials.array(("1", "a"))
        self.assertRaises(KeyError, a.__getitem__, "1")
        self.assertEqual("a", a[1])
        b = specials.array((1.7, "b"))
        self.assertEqual("b", b[1])
        c = specials.array((True, "True"), (False, "False"))
        self.assertEqual("False", c[0])

    def test_array_indexing(self):
        a = specials.array("thingy")
        self.assertEqual("thingy", a[0])
        a[100] = "majigy"
        a.append("bobity")
        self.assertEqual("majigy", a[100])
        self.assertEqual("bobity", a[101])

    def test_array_bool(self):
        a = specials.array()
        self.assertFalse(a)
        b = specials.array(0)
        self.assertTrue(b)

    def test_array_as_string(self):
        self.assertEqual("Array", str(specials.array(1, 2, 3)))

    # Should I make a special string type?
    # TODO: if "0" is falsey in php
    # TODO: Autoconversion of string + number
    # TODO: Strings are actually bytes... encoded in the encoding of the source file
    # Might be safest to assume utf8 and ignore the whole byte thing?!
