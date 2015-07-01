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


class CompiledSegment(object):
    def __init__(self) -> 'CompiledSegment':
        self._indent = 0
        self.lines = []

    def append(self, item):
        """ Append a string or CompiledSegment to the end of this segment

        """
        if isinstance(item, CompiledSegment):
            for l, i in item:
                self.lines.append((l, i + self._indent))
        else:
            self.lines.append((item, self._indent))

    def indent(self):
        """ Increase the indent level by one

        """
        self._indent += 1

    def dedent(self):
        """ Decrease the indent level by one

        """
        self._indent -= 1

    def br(self, number=1):
        """ Add a blank line to this segment

        """

        for i in range(0, number):
            # Direct call to results to avoid extra spaces
            self.lines.append(("", 0))

    def prepend(self, line):
        """ Insert a zero indented item at the start of this segment

        """
        self.lines.insert(0, (line, 0))

    def __str__(self):
        out = ""
        from pprint import pprint
        pprint(self.lines)
        for l, i in self.lines:
            print(l, i)
            out += "    " * i + l
        return out

    def __iter__(self):
        return iter(self.lines)

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, item):
        return self.lines[item][0]


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
        self.compiled = CompiledSegment()
        self.tree = tree

    def compile(self, tree=None) -> str:
        if tree is None:
            tree = self.tree
        transformer.transform(tree)

        for c in tree:
            self.compiled.append(self.marshal(c))

        self.generic_footer_compile()

        for i, v in self.imports.items():
            self.add_import(i, v)
        return str(self)

    def __str__(self):
        return str(self.compiled)

    def generic_footer_compile(self):
        """ Adds the __name__ == __main__ magic to the bottom of the file

        """
        self.compiled.br()
        self.compiled.append('if __name__ == "__main__":')
        self.compiled.indent()
        self.compiled.append('import os.path')
        self.compiled.append('php.serve_up(body, root_dir=os.path.abspath(os.path.dirname(__file__)))')
        self.compiled.dedent()

    def add_import(self, module:str, els=None):
        """ Add a python import at the top of the file.

        Capable of both import foo and from foo import baz style imports, depending on the optional parameter
        els.

        Args:
            module: The module name to import
            els: An optional list of items to import from that module

        """
        module = self.python_safe(module)
        if els is None or els[0] is None:
            self.compiled.prepend("import {0}".format(module))
        else:
            els = ", ".join([self.python_safe(e) for e in els])
            self.compiled.prepend("from {0} import {1}".format(module, els))

    def echo(self, value: str) -> str:
        return "php.write({0})".format(value)

    def python_safe(self, ident):
        """ Not implemented yet - depends if we ever get unsafe idents

        """
        return ident

    def python_escape(self, string:str) -> str:
        """ Kinda ditto
        """
        return string

    def marshal(self, node: parsetree.ParseNode):
        """ Tries to find the correct function from a given node from the parse tree

        When given a node, tries to find a compile_<node_name> function.

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

    def php_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        php_segment = CompiledSegment()
        for c in node:
            php_segment.append(self.marshal(c))
        return php_segment

    def html_compile(self, node: parsetree.ParseNode) -> str:
        return self.echo(repr(node.value))

    def while_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("while {0}:".format(self.marshal(node[0][0])))
        seg.indent()
        seg.append(self.marshal(node[1]))
        seg.dedent()
        return seg

    def if_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        try:
            # print("Compiled " + "if {0}:".format(self.expression_compile(node.get("EXPRESSION"))))
            # print("from")
            # parsetree.print_tree(node.get("EXPRESSION"))
            seg.append("if {0}:".format(self.expression_compile(node.get("EXPRESSION"))))
        except IndexError:
            print("Compile Error at ", node.token)
            parsetree.print_tree(node)
            raise
        seg.indent()
        seg.append(self.marshal(node.get("BLOCK")))
        # TODO: We should catch failure to get somewhere at the top level. IndexError maybe?
        seg.dedent()
        return seg

    def elif_compile(self, node:parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("elif {}:".format(self.expression_compile(node.get("EXPRESSION"))))
        seg.indent()
        seg.append(self.marshal(node.get("BLOCK")))
        seg.dedent()
        return seg

    def pyfor_compile(self, node:parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("for {} in {}:".format(self.marshal(node[0]), self.marshal(node[1])))
        seg.indent()
        seg.append(self.marshal(node[2]))
        seg.dedent()
        return seg

    def function_compile(self, node:parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        args = ["p"]
        parsetree.print_tree(node)
        for v in node["ARGSLIST"]:
            args.append(self.marshal(v))
        seg.append("@phpfunc")
        seg.append("def {0}({1}):".format(node.value, ", ".join(args)))
        seg.indent()
        seg.append(self.marshal(node[1]))
        seg.dedent()
        return seg

    def class_compile(self, node: parsetree.ParseNode) -> str:
        seg = CompiledSegment()
        seg.append("class {}(PhpClass):".format(node.value))
        seg.indent()
        seg.append(self.marshal(node.get("BLOCK")))
        seg.dedent()
        self.compiled.append(seg)
        return "p.c.{0} = {0}".format(node.value)

    def classmethod_compile(self, node):
        # TODO: This is wrong - we should do _most_ of the function compile, but not the adding to php functions bit
        return self.function_compile(node)

    def method_compile(self, node):
        # TODO: Ditto
        return self.function_compile(node)

    def _call_inner_compile(self, node: parsetree.ParseNode) -> str:
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

    def call_compile(self, node: parsetree.ParseNode) -> str:
        return "p.f." + self._call_inner_compile(node)

    def methodcall_compile(self, node: parsetree.ParseNode) -> str:
        return "{}.{}".format(self.marshal(node[1]), self._call_inner_compile(node))

    def callspecial_compile(self, node: parsetree.ParseNode) -> str:
        return self._call_inner_compile(node)

    def keyvalue_compile(self, node: parsetree.ParseNode, assign=": "):
        if len(node.children) != 2:
            parsetree.print_tree(node.parent)
            raise CompileError("Keyvalues must have more than one child")
        return self.marshal(node[0]) + assign + self.marshal(node[1])

    def new_compile(self, node):
        return self.call_compile(node[0])

    def return_compile(self, node:parsetree.ParseNode) -> str:
        return "return " + self.expression_compile(node[0])

    def pass_compile(self, node) -> str:
        return "pass"

    def expression_compile(self, node:parsetree.ParseNode) -> str:
        # print("Compiling expression")
        # print("from")
        # parsetree.print_tree(node)
        if len(node.children) == 0:
            return ""
        r = "".join([self.marshal(c) for c in node]).lstrip()
        return r

    def var_compile(self, node:parsetree.ParseNode) -> str:
        sub_var = ""
        if len(node.children) > 0:
            sub_var = self.subvar_compile(node.children[0])
        return self.python_safe(node.value) + sub_var

    def subvar_compile(self, node: parsetree.ParseNode) -> str:
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
        # TODO: Contants might need further thought
        return "p.constants.{}".format(node.value)

    def comparator_compile(self, node):
        return self.operator2_compile(node)

    def global_compile(self, node):
        return ""

    def block_compile(self, node:parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        for c in node.children:
            seg.append(self.marshal(c))
        return seg

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

    def statement_compile(self, node) -> str:
        if len(node.children) != 0:
            # for n in node:
            # print(n)
            return " ".join([self.marshal(c) for c in node])

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
            return "#" + node.value

    def commentblock_compile(self, node):
        # TODO: Note that we don't deal with comments inline very well. Should strip them if they are in the
        # wrong place
        if self.strip_comments:
            return ""
        if node.parent.node_type in ("STATEMENT", "EXPRESSION"):
            return '"""{}"""\n'.format(node.value)
        else:
            return '"""{}"""\n'.format(node.value)

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
        seg = CompiledSegment()
        seg.append("try:")
        seg.indent()
        seg.append(self.block_compile(node.get("BLOCK")))
        seg.dedent()
        for c in node[1:]:
            if c.node_type != "CATCH":
                raise CompileError("Expected catch block as child of try {}".format(c.token))
            catch_match = c[0]
            catch_block = c[1]
            seg.append("except {} as {}:".format(
                    self.marshal(catch_match[0][0]),
                    self.marshal(catch_match[0][1])
            ))
            seg.indent()
            seg.append(self.marshal(catch_block))
            seg.dedent()
        return seg

    def switch_compile(self, node):
        # TODO: Transform switch statements. Probably mostly already done.
        pass

    def cast_compile(self, node):
        return "{}({})".format(node.value, self.marshal(node[0]))
