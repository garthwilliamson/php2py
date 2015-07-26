php2py
======

A toy project to convert php files into python files.

Completely unfinished as of yet.

Usage
-----

**NOTE! php2py is python 3 only**

See php2py.py  --help

Convert the files to python:
    Run php2py.py php/index.php
    or...
    Run php2py.py --search php/ to attempt to compile all the php files in a given directory

Run the converted files on the command line:
    php2py_run.py php/index.py

Run the php files under a web server:
    simple_server.py php/config.json

Motivation
----------

To see if it's possible. It'd be interesting to be able to enable people to start moving thier
php applications to a different language. Ideally I'd like to make it as easy as possible to
continue development after the conversion in a more and more pythonic fashion.
