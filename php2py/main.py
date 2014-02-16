from .compiler import Compiler
from .parser import PhpParser


def print_tree(tree, indent=0):
    print(indent * " " + str(tree))
    for c in tree:
        print_tree(c, indent + 4)


def parse_and_compile(string, name="anon"):
    parser = PhpParser(string, "test", False)
    parser.parse()
    c = Compiler(parser.get_tree())
    return c
