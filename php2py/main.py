from .compiler import Compiler
from .parser import PhpParser


def parse_and_compile(string, name="anon", debug=False):
    parser = PhpParser(string, "test", False)
    parser.parse()
    if debug:
        parser.pt.print_()
    c = Compiler(parser.get_tree())
    if debug:
        print(c)
    return c


def compile(filename, debug=0):
    parser = PhpParser("".join(open(filename).readlines()), filename, bool(debug))
    parser.parse()
    if debug:
        parser.pt.print_()
    c = Compiler(parser.get_tree())
    return str(c)