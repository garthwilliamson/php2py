from .compiler import Compiler
from .parser import PhpParser


def parse_and_compile(string, name="anon"):
    parser = PhpParser(string, "test", False)
    parser.parse()
    c = Compiler(parser.get_tree())
    return c
