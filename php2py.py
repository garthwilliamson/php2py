#!/usr/bin/python

import php2py
import argparse
from php2py.compiler import Compiler
from php2py.parser import PhpParser

ap = argparse.ArgumentParser()
ap.add_argument("-d", "--debug", type=int, default=0, help="Enable basic debugging")
ap.add_argument("-s", "--strip", type=int, default=0, help="Strip comments and crap")
ap.add_argument("file", help="file to compile")
args = ap.parse_args()

#print(php2py.compile(args.file, debug=args.debug, strip_comments=args.strip))

debug_deep = args.debug > 1
parser = PhpParser("".join(open(args.file).readlines()), args.file, debug_deep)
parser.parse()
if args.debug:
    parser.pt.print_()
c = Compiler(parser.get_tree(), strip_comments=args.strip)
print(str(c))