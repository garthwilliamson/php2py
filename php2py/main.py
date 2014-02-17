from .compiler import Compiler
from .parser import PhpParser


def parse_and_compile(string, name="anon"):
    parser = PhpParser(string, "test", False)
    parser.parse()
    c = Compiler(parser.get_tree())
    return c


def compile(filename):
    parser = PhpParser("".join(open(filename).readlines()), filename, False)
    parser.parse()
    #parser.pt.print_()
    c = Compiler(parser.get_tree())
    return str(c)