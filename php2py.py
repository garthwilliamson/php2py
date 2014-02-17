#!/usr/bin/python

import sys
import php2py

for f in sys.argv[1:]:
    print php2py.compile(f)
    print "#####################################"