from functools import wraps
import unittest
import logging

from php2py.parser import PhpParser
from php2py.compiler import Compiler
from php2py import transformer  # Used by the kiddies
from php2py.clib.parsetree import ParseNode, print_tree, MatchableNode
from intermediate import BlockNode


logging.basicConfig(level=logging.DEBUG)


def parse_string(s: str, debug=False) -> PhpParser:
    parser = PhpParser(iter(s.splitlines(True)))
    parser.parse()
    if debug:
        parser.pt.print_()
    return parser


def transform_t(f):
    """
    Wrap a function to supply root_node and root_node_t

    Uses the docstring as the source code
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        root_node = parse_string(f.__doc__).get_tree()
        try:
            root_node_t = transformer.transform(root_node)
        except:
            print_tree(root_node)
            raise
        try:
            f(self, root_node_t, *args, **kwargs)
        except:
            print_tree(root_node)
            print("------------------")
            print_tree(root_node_t)
            raise


    return wrapper


def parse_t(f):
    """ Wrap a function to parse a php string given as a docstring

    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        """ The wrapper

        """
        root_node = parse_string(f.__doc__).get_tree()
        try:
            f(self, root_node, *args, **kwargs)
        except:
            print_tree(root_node)
            raise

    return wrapper


def compile_body_t(f):
    """ Wraps a function to parse a php string given as a docstring

    The wrapped function should take an argument of "lines" - these are the main lines of the function
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        root_node = parse_string(f.__doc__).get_tree()
        root_node_t = transformer.transform(root_node)
        body_block = root_node_t.match("FUNCTION|body/BLOCK")
        try:
            lines_seg = body_block.compile()
        except:
            print_tree(root_node)
            print("------------------")
            print_tree(root_node_t)
            raise
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
        root_node_t = transformer.transform(root_node)
        class_ = root_node_t["CLASS"]
        lines_seg = class_.compile()
        lines = [l[0] for l in lines_seg.lines]
        try:
            f(self, lines, *args, **kwargs)
        except:
            print_tree(root_node_t)
            raise

    return wrapper

class Php2PyTestCase(unittest.TestCase):
    def setUp(self):
        self.compiler = Compiler()

    def assertEcho(self, node, string, kind="STRING"):
        self.assertEqual(node[0].kind, "EXPRESSION")
        self.assertEqual(node[0][0].kind, "CALLSPECIAL")
        self.assertEqual(node[0][0][0].kind, "ARGSLIST")
        self.assertEqual(node[0][0][0][0].kind, "EXPRESSION")
        self.assertEqual(node[0][0][0][0][0].kind, kind)
        self.assertEqual(node[0][0][0][0][0].value, string)

    def assertContainsNode(self, node: MatchableNode, match_str: str, msg=None):
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


def get_body(root_node: ParseNode) -> BlockNode:
    """ Get the main block of the "body" function

    Use post-transform

    """
    return root_node.match("FUNCTION|body/BLOCK")
