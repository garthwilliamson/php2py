#!/usr/bin/python

import php2py
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("-d", "--debug", type=int, default=0, help="Enable basic debugging")
ap.add_argument("file", help="file to compile")
args = ap.parse_args()

print(php2py.compile(args.file, debug=args.debug))
