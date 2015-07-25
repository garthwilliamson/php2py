Comparability
=============

The progress made towards compiling *all* of the php programs.

Identical Command Line Output
-----------------------------

The following give byte for byte compatibility at the command line:

* hello00.php, hello01.php and hello02.php test scripts

Identical Web Browser Output
----------------------------

There aren't any. There needs to be a wsgi interface stuck on first

At least index.php running
--------------------------

Programs which run at least the index.php part of themselves

* mini (https://github.com/panique/mini)

Doesn't Break the Compiler
--------------------------

This is an important first step to running the programs. It is almost certain that these programs
have a ludicrous amount of bugs. It is also probably that code will have magically disappeared
during the conversion process.

* tiny (https://github.com/panique/tiny)
