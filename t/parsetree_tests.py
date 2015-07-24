from __future__ import unicode_literals

import unittest
import php2py.parser as p


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.matching = "AABBCC1234<?php"
        self.simple_parser = p.Parser(self.matching, "test1")

    def test_scopes(self):
        self.simple_parser.push_scope("GLOBAL")
        self.assertTrue(self.simple_parser.scope_is("GLOBAL"))
        self.simple_parser.push_scope("LOCAL")
        self.assertTrue(self.simple_parser.scope_is("LOCAL"))
        self.simple_parser.pop_scope()
        self.assertTrue(self.simple_parser.scope_is("GLOBAL"))
