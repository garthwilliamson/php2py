from __future__ import unicode_literals
from __future__ import print_function

import collections

from . import parsetree, transformer


constant_map = {
    "true": "True",
    "false": "False",
    "null": "None",
}

magic_map = {
    "__file__": "p.f.get__file__(p, __file__)",
}


class CompileError(Exception):
    pass


class Compiler(object):
    """ Compiler for a parse tree

    Uses the transformer to convert and optimise? the tree

    Compiles statement by statement

    """
    def __init__(self, tree=None, strip_comments=False):
        self.strip_comments = strip_comments
        self.imports = collections.defaultdict(list)
        self.imports["php2py"].append("php")
        self.imports["php2py.specials"].append("*")
        self.functions = []
        self.indent = 0
        self.tree = tree
        body = ["def body(p):"]
        self.cur_function = body
        self.functions.append(body)
        self.indent += 4

    def compile(self, tree=None):
        if tree is None:
            tree = self.tree
        transformer.transform(tree)

        for c in tree:
            self.marshal(c)

        self.results = []
        for f in self.functions:
            self.blank_lines(2)
            self.results += f
        self.generic_footer_compile()

        for i, v in self.imports.items():
            self.add_import(i, v)
        return "\n".join(self.results)

    def __str__(self):
        return "\n".join(["\n".join(f) for f in self.functions])

    def generic_footer_compile(self):
        """ Adds the __name__ == __main__ magic to the bottom of the file

        """
        self.results.append("""\n\nif __name__ == "__main__":""")
        self.results.append("""    import os.path""")
        self.results.append("""    php.serve_up(body, root_dir=os.path.abspath(os.path.dirname(__file__)))""")

    def add_import(self, module, els=None):
        """ Add a python import at the top of the file.

        Capable of both import foo and from foo import baz style imports, depending on the optional parameter
        els.

        Args:
            module: The module name to import
            els: An optional list of items to import from that module

        """
        module = self.python_safe(module)
        if els is None or els[0] is None:
            self.prepend("import {0}".format(module))
        else:
            els = ", ".join([self.python_safe(e) for e in els])
            self.prepend("from {0} import {1}".format(module, els))

    def add_output(self, value):
        self.append("php.write({0})".format(value))

    def append(self, line):
        """ Normal method to add another line of code to the current function

        Will add the current indentation level to the start of the line.

        Args:
            line: A text representation of the code to add

        """
        self.cur_function.append(' ' * self.indent + line)

    def prepend(self, line):
        """ Puts the line at the top of the file

        """
        self.results.insert(0, line)

    def blank_lines(self, number):
        for i in range(0, number):
            # Direct call to results to avoid extra spaces
            self.results.append("")

    def python_safe(self, ident):
        """ Not implemented yet - depends if we ever get unsafe idents

        """
        return ident

    def python_escape(self, string):
        return string

    def marshal(self, node):
        """ Tries to find the correct function from a given node from the parse tree

        When given a node, tries to find a compile<node_name> function.

        Args:
            node: The node to try to compile

        Raises:
            CompileError: A common error to be returned is the CompileError when a given node type doesn't
                          have an appropriate compile method defined yet.

        """
        try:
            return getattr(self, node.node_type.lower() + "_compile")(node)
        except TypeError:
            print("Tried to compile...")
            parsetree.print_tree(node)
            print("...but failed")
            raise  # CompileError("Probably something isn't returning a string when it should", e)
        except AttributeError:
            print("Tried to compile {}...".format(node.token))
            parsetree.print_tree(node)
            print("...but failed")
            raise CompileError("Unimplemented method " + node.node_type.lower() + "_compile")

    def php_compile(self, node):
        for c in node:
            self.marshal(c)

    def html_compile(self, node):
        self.add_output(repr(node.value))

    def while_compile(self, node):
        self.append("while {0}:".format(self.marshal(node[0][0])))
        self.indent += 4
        self.marshal(node[1])
        self.indent -= 4

    def if_compile(self, node):
        try:
            #print("Compiled " + "if {0}:".format(self.expression_compile(node.get("EXPRESSION"))))
            #print("from")
            #parsetree.print_tree(node.get("EXPRESSION"))
            self.append("if {0}:".format(self.expression_compile(node.get("EXPRESSION"))))
        except IndexError:
            print("Compile Error at ", node.token)
            parsetree.print_tree(node)
            raise
        self.indent += 4
        self.marshal(node.get("BLOCK"))
        #TODO: We should catch failure to get somewhere at the top level. IndexError maybe?
        self.indent -= 4

    def elif_compile(self, node):
        self.append("elif {}:".format(self.expression_compile(node.get("EXPRESSION"))))
        self.indent += 4
        self.marshal(node.get("BLOCK"))
        self.indent -= 4

    def pyfor_compile(self, node):
        self.append("for {} in {}:".format(self.marshal(node[0]), self.marshal(node[1])))
        self.indent += 4
        self.marshal(node[2])
        self.indent -= 4

    def function_compile(self, node):
        old_function = self.cur_function
        args = ["p"]
        parsetree.print_tree(node)
        for v in node["ARGSLIST"]:
            args.append(self.marshal(v))
        self.cur_function = ["@phpfunc", "def {0}({1}):".format(node.value, ", ".join(args))]
        self.marshal(node[1])
        self.functions.append(self.cur_function)
        self.cur_function = old_function
        self.append("p.f.{0} = {0}".format(node.value))

    def class_compile(self, node):
        old_function = self.cur_function
        self.cur_function = ["class {}(PhpClass):"]
        self.marshal(node.get("BLOCK"))
        self.functions.append(self.cur_function)
        self.cur_function = old_function
        self.append("p.c.{0} = {0}".format(node.value))

    def classmethod_compile(self, node):
        return self.function_compile(node)

    def method_compile(self, node):
        return self.function_compile(node)

    def _call_inner_compile(self, node):
        """ Compile a function or method call

        Deals with the function name and arg list but not the scoping.

        """
        # Process args
        # TODO: Deal with positional and other args combined
        arg_list = ["p"]
        kwarg_list = []
        if len(node.get("ARGSLIST")) > 0:
            for e in node.get("ARGSLIST"):
                if e.node_type == "KEYVALUE":
                    kwarg_list.append(self.keyvalue_compile(e))
                else:
                    arg_list.append(self.expression_compile(e))
        kwargs = ""
        if len(kwarg_list) != 0:
            kwargs = "**{" + ", ".join(kwarg_list) + "}"
            arg_list.append(kwargs)
        args = ", ".join(arg_list)
        return "{0}({1})".format(node.value, args)

    def call_compile(self, node):
        return "p.f." + self._call_inner_compile(node)

    def methodcall_compile(self, node):
        # Don't like that this is a repeat of above, but oh well
        return "{}.{}".format(self.marshal(node[1]), self._call_inner_compile(node))

    def callspecial_compile(self, node):
        return self._call_inner_compile(node)

    def keyvalue_compile(self, node, assign=": "):
        if len(node.children) != 2:
            parsetree.print_tree(node.parent)
            raise CompileError("Keyvalues must have more than one child")
        return self.marshal(node[0]) + assign + self.marshal(node[1])

    def new_compile(self, node):
        return self.call_compile(node[0])

    def return_compile(self, node):
        self.append("return " + self.expression_compile(node[0]))

    def pass_compile(self, node):
        self.append("pass")

    def expression_compile(self, node):
        #print("Compiling expression")
        #print("from")
        #parsetree.print_tree(node)
        if len(node.children) == 0:
            return ""
        r = "".join([self.marshal(c) for c in node]).lstrip()
        return r

    def var_compile(self, node):
        sub_var = ""
        if len(node.children) > 0:
            sub_var = self.subvar_compile(node.children[0])
        return self.python_safe(node.value) + sub_var

    def subvar_compile(self, node):
        return '.{0}'.format(node.value)

    def globalvar_compile(self, node):
        return "p.g." + self.var_compile(node).lstrip()

    def ident_compile(self, node):
        return node.value

    def index_compile(self, node):
        return "{}[{}]".format(self.marshal(node[1]), self.marshal(node[0]))

    def attr_compile(self, node):
        return "{}.{}".format(self.marshal(node.children[1]), self.marshal(node.children[0]))

    def staticattr_compile(self, node):
        """ Static attr should change references to self etc to the proper class name..."""
        return "p.c.{}.{}".format(self.marshal(node.children[1]), self.marshal(node.children[0]))

    def constant_compile(self, node):
        #TODO: Contants might need further thought
        return "p.constants.{}".format(node.value)

    def comparator_compile(self, node):
        return self.operator2_compile(node)

    def global_compile(self, node):
        return ""

    def block_compile(self, node):
        for c in node.children:
            self.marshal(c)

    def string_compile(self, node):
        fmt = ""
        if len(node.children) > 0:
            fmt = ".format({})".format(", ".join([v.value for v in node]))
        return 'u"' + node.value + '"' + fmt

    def assignment_compile(self, node):
        return "{} {} {}".format(self.marshal(node[1]), node.value, self.marshal(node[0]))

    def operator2_compile(self, node):
        try:
            return "({} {} {})".format(self.marshal(node[1]), node.value, self.marshal(node[0]))
        except IndexError:
            raise CompileError("Expected two children for {}".format(node))

    def operator1_compile(self, node):
        return "{} ({})".format(node.value, self.marshal(node[0]))

    def statement_compile(self, node):
        if len(node.children) != 0:
            #for n in node:
                #print(n)
            self.append(" ".join([self.marshal(c) for c in node]))

    def int_compile(self, node):
        return str(node.value)

    def oct_compile(self, node):
        return "0o" + node.value

    def phpconstant_compile(self, node):
        return constant_map[node.value]

    def commentline_compile(self, node):
        # Should do something about putting comments on the end of a line properly
        if self.strip_comments:
            return ""
        if node.parent.node_type in ("STATEMENT", "EXPRESSION"):
            return "#" + node.value + "\n"
        else:
            self.append("#" + node.value)

    def commentblock_compile(self, node):
        # TODO: Note that we don't deal with comments inline very well. Should strip them if they are in the
        # wrong place
        if self.strip_comments:
            return ""
        if node.parent.node_type in("STATEMENT", "EXPRESSION"):
            return '"""{}"""\n'.format(node.value)
        else:
            self.append('"""{}"""\n'.format(node.value))

    def magic_compile(self, node):
        if node.value not in magic_map:
            raise CompileError("No magic value {} known".format(node.value))
        return magic_map[node.value]

    def dict_compile(self, node):
        out = []
        for c in node:
            if len(c.children) == 3:
                out.append(self.marshal(c[0]) + ": " + self.marshal(c[2]))
        return (", ".join(out))

    def tuple_compile(self, node):
        return "(" + ", ".join(self.marshal(c) for c in node) + ")"

    def list_compile(self, node):
        return "[" + ", ".join(self.marshal(c) for c in node) + "]"

    def expressiongroup_compile(self, node):
        return "({})".format(", ".join([self.marshal(c) for c in node.children]))

    def try_compile(self, node):
        self.append("try:")
        self.indent += 4
        self.marshal(node.get("BLOCK"))
        self.indent -= 4
        for c in node[1:]:
            if c.node_type != "CATCH":
                raise CompileError("Expected catch block as child of try {}".format(c.token))
        catch = node.get()
        catch_match = catch[0]
        catch_block = catch[1]
        self.append(
            "except {} as {}:".format(
                self.marshal(catch_match[0][0]),
                self.marshal(catch_match[0][1])
            ))
        self.indent += 4
        self.marshal(catch_block)
        self.indent -= 4

    def switch_compile(self, node):
        #TODO: Transform switch statements. Probably mostly already done.
        pass

    def cast_compile(self, node):
        return "{}({})".format(node.value, self.marshal(node[0]))
