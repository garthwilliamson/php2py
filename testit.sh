#!/bin/bash

export PYTHONPATH="./"
#python -m unittest discover t/ '*_test.py'
nosetests3 $1 t --with-coverage --cover-package=php2py.parser,py2php.compiler,py2php.parsetree,py2php --exe --with-timer --timer-top-n=5 2>&1 | tee out.txt
