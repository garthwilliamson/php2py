Optimisations
=============

These all take places at start of transform

Locals
------

Locals can be optimised by:
    Iterate through children in same scope, recording locals
    At start of function,
        a = b = c = d = None
    Change references to locals to not go via p

Globals
-------

Globals can be optimised by:
    Iterate though the scope, recording and counting global references
    If number of references is greater than MIN_GLOBALS_REFACTOR then:
        At start of scope,
            a, b, c, d = p.g.a, p.g.b, p.g.c, p.g.d
        At end of scope,
            p.g.a, p.g.b, p.g.c, p.g.d = a, b, c, d


Pythonification
===============

For loops
---------

Rather than:
    for (i = 0; i < 10, i++) {}
Rendering to:
    i = 0
    while i < 10:
        i += 1
Instead:
    for i in range(0, 10):
