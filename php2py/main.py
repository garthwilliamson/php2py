import fnmatch
import os
import sys
import logging
import time

from .compiler import Compiler, CompilationFailure
from .parser import PhpParser


BAD_FILE = 1
COMPILE_FAILURE = 2


def compile_file(filename: str, compile: bool, strip_comments: bool, print_tree: bool = False):
    """ Compile a file called file_name

    """
    print("Parsing {}".format(filename))
    try:
        # newline='' means we just accept whatever line ending is already in the file
        parser = PhpParser(open(filename, "r", newline=''))
    except FileNotFoundError:
        logging.critical("Unknown file: {}. Check filename and try again.".format(filename))
        sys.exit(BAD_FILE)

    if print_tree:
        parser.pt.print_()

    if not compile:
        return

    dir_name, php_filename = os.path.split(filename)
    name, ext = os.path.splitext(php_filename)
    py_filename = os.path.join(dir_name, name + ".py")

    print()
    print("Compiling {} to {}".format(filename, py_filename))
    c = Compiler(parser.get_tree(), strip_comments=strip_comments)
    try:
        results = c.compile()
    except CompilationFailure as e:
        print()
        print(e.args[0] + ":")
        for cause in e.args[1]:
            print("    " + cause.msg)
            print("        Node was {}".format(cause.node))
            t = cause.node.token
            if t is None:
                print("        Node didn't include a token. Unknown location")
            else:
                print("        Original token was {}".format(t))
            print()
        sys.exit(COMPILE_FAILURE)
    with open(py_filename, "w") as py_file:
        py_file.write(str(results))


def compile_dir(dirname: str, compile: bool, strip_comments: bool):
    print("Searching for php files in {} to compile".format(dirname))
    print("-" * 50)
    count = 0
    start_time = time.time()
    for root, dirnames, filenames in os.walk(dirname):
        for filename in fnmatch.filter(filenames, '*.php'):
            compile_file(os.path.join(root, filename), compile, strip_comments)
            count += 1
    end_time = time.time()
    print("-" * 50)
    print("Compiled {} files in {:.3f} seconds".format(count, end_time - start_time))
