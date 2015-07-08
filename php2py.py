#!/usr/bin/python
import sys
import argparse
import os.path

from php2py.compiler import Compiler
from php2py.parser import PhpParser

ap = argparse.ArgumentParser()
ap.add_argument("-d", "--debug", type=int, default=0, help="Enable basic debugging")
ap.add_argument("-s", "--strip", action="store_true", help="Strip comments and crap")
ap.add_argument("-c", "--compile", action="store_false", help="Compile to file.py")
ap.add_argument("--tree", action="store_true", help="Display the parse tree.")
ap.add_argument("file", help="file to compile")
args = ap.parse_args()

# set up some filenames and paths
dir_name, php_filename = os.path.split(args.file)
file_name, ext = os.path.splitext(php_filename)
py_filename = os.path.join(dir_name, file_name + ".py")


debug_deep = args.debug > 1
try:
    parser = PhpParser(open(args.file), debug_deep)
except FileNotFoundError:
    print("Unknown file: {}. Check filename and try again.".format(args.file))
    sys.exit(1)

parser.parse()
if args.debug or args.tree:
    parser.pt.print_()

if args.compile:
    c = Compiler(parser.get_tree(), strip_comments=args.strip)
    results = c.compile()
    py_file = open(py_filename, "w")
    py_file.write(str(results))
    py_file.close()
