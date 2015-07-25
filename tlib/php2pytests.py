from functools import wraps
import unittest
import logging

from php2py.parser import PhpParser
from php2py.compiler import Compiler
from php2py import transformer, compiler    # Used by the kiddies
from php2py.parsetree import ParseNode, print_tree


logging.basicConfig(level=logging.DEBUG)


def parse_string(s: str, debug=False) -> PhpParser:
    parser = PhpParser(iter(s.splitlines(True)))
    parser.parse()
    if debug:
        parser.pt.print_()
    return parser

# TODO: Is this useless because debugging requires to be able to inspect pre and post transform?
"""
def transform_t(f):
    Wrap a function to supply root_node and root_node_t

    Uses the docstring as the source code

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        root_node = parse_string(f.__doc__).get_tree()
        root_node_t = transformer.transform(root_node)
        f(self, root_node, root_node_t, *args, **kwargs)

    return wrapper
    """


def parse_t(f):
    """ Wrap a function to parse a php string given as a docstring

    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        """ The wrapper

        """
        root_node = parse_string(f.__doc__).get_tree()
        f(self, root_node, *args, **kwargs)

    return wrapper


def compile_body_t(f):
    """ Wraps a function to parse a php string given as a docstring

    The wrapped function should take an argument of "lines" - these are the main lines of the function
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        root_node = parse_string(f.__doc__).get_tree()
        transformer.transform(root_node)
        body_block = get_body(root_node)
        lines_seg = Compiler().marshal(body_block)
        lines = [l[0] for l in lines_seg.lines[1:]]
        f(self, lines, *args, **kwargs)

    return wrapper


def compile_class_t(f):
    """ Wrap a function to parse a php string containing a class (from docstring)

    The wrapped function should accept an argument lines which will contain all the lines of the class definition
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        root_node = parse_string(f.__doc__).get_tree()
        transformer.transform(root_node)
        class_block = root_node["CLASS"]
        lines_seg = Compiler().marshal(class_block)
        lines = [l[0] for l in lines_seg.lines]
        f(self, lines, *args, **kwargs)

    return wrapper

class Php2PyTestCase(unittest.TestCase):
    def setUp(self):
        self.compiler = Compiler()

    def assertEcho(self, node, string, node_type="STRING"):
        self.assertEqual(node[0].node_type, "EXPRESSION")
        self.assertEqual(node[0][0].node_type, "CALLSPECIAL")
        self.assertEqual(node[0][0][0].node_type, "ARGSLIST")
        self.assertEqual(node[0][0][0][0].node_type, "EXPRESSION")
        self.assertEqual(node[0][0][0][0][0].node_type, node_type)
        self.assertEqual(node[0][0][0][0][0].value, string)

    def assertContainsNode(self, node: ParseNode, match_str: str, msg=None):
        try:
            node.match(match_str)
        except:
            if msg is None:
                msg = "{} doesn't contain {}".format(node, match_str)
            print("Actual node contents are:")
            print_tree(node)
            raise AssertionError(msg)

    def assertLinesMatch(self, expected_lines, got_lines):
        for expected, got in zip(expected_lines, got_lines):
            self.assertEqual(expected, got)


def get_body(root_node: ParseNode) -> ParseNode:
    """ Get the main block of the "body" function

    Use post-transform

    """
    return root_node.match("FUNCTION|body/BLOCK")
