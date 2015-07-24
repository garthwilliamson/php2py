#!/usr/bin/python
import argparse
import logging

from php2py.main import compile_file, compile_dir


ap = argparse.ArgumentParser()
ap.add_argument("-d", "--debug", type=int, default=1, help="Enable basic debugging")
ap.add_argument("-s", "--strip", action="store_true", help="Strip comments and crap")
ap.add_argument("-c", "--compile", action="store_false", help="Compile to file.py")
ap.add_argument("--tree", action="store_true", help="Display the parse tree.")
ap.add_argument("file", help="file to compile")
ap.add_argument("--search", action="store_true", help="Search for php files in a given directory")
args = ap.parse_args()

print_tree = False
if args.tree or args.debug > 0:
    print_tree = True

levels = {
    -1: logging.ERROR,      # Silent mode
    0: logging.WARNING,     # Critical information
    1: logging.INFO,        # Compiling information, and bad php code
    2: logging.DEBUG,       # Debug php2py
    3: logging.DEBUG - 1,   # Ridiculous verbosity
}
logging.basicConfig(level=levels[args.debug], format=None)

if args.search:
    compile_dir(args.file, args.compile, args.strip)
else:
    parser = compile_file(args.file, args.compile, args.strip, print_tree)
