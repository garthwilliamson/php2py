from __future__ import unicode_literals

import unittest
import php2py.parser as p


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.matching = "AABBCC1234<?php"
        self.simple_parser = p.Parser(self.matching, "test1", False)

    def test_create_pattern(self):
        res = p.create_pattern(("AA", "BB"))
        self.assertEqual(res.pattern, "AA|BB")
        self.assertEqual(res.match(self.matching).group(0), "AA")

    def test_sizing(self):
        pat = p.create_pattern(("AABBD", "AABBC", "AAB", "BC", "B"))
        self.assertEqual(pat.search(self.matching).group(0), "AABBC")

    def test_matching(self):
        pat = p.create_pattern(("BB", "CC"))
        self.assertIs(None, self.simple_parser.match_for(pat))
        pat = p.create_pattern(("BB", "AA"))
        self.assertEqual("AA", self.simple_parser.match_for(pat))

    def test_searching(self):
        pat = p.create_pattern(("DD",))
        match, until = self.simple_parser.search_until(pat)
        self.assertEqual(match, "EOF")

    def retest_searching(self):
        pat = p.create_pattern(("CC",))
        match, until = self.simple_parser.search_until(pat)
        self.assertEqual(match, "CC")
        self.assertEqual(until, "AABB")
        match, until = self.simple_parser.search_until(p.create_pattern(("<?php",)))
        self.assertEqual(match, "<?php")
        self.assertEqual(until, "1234")

    def test_scopes(self):
        self.simple_parser.push_scope("GLOBAL")
        self.assertTrue(self.simple_parser.scope_is("GLOBAL"))
        self.simple_parser.push_scope("LOCAL")
        self.assertTrue(self.simple_parser.scope_is("LOCAL"))
        self.simple_parser.pop_scope()
        self.assertTrue(self.simple_parser.scope_is("GLOBAL"))

