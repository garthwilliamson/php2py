#!/bin/bash

export PYTHONPATH="./"
#python -m unittest discover t/ '*_test.py'
nosetests $1 t --with-coverage --cover-package=parser --exe --with-timer --timer-top-n=5 2>&1 | tee out.txt
