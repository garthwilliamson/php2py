from __future__ import unicode_literals

import collections

from .clib.segment import CompiledSegment
from php2py import transformer
from .clib import parsetree


constant_map = {
    "true": "True",
    "false": "False",
    "null": "None",
}

magic_map = {
    "__file__": "_f_.get__file__(p, __file__)",
}


class CompilationFailure(Exception):
    pass


class CompileError(Exception):
    def __init__(self, node: parsetree.ParseNode, msg: str, *args):
        self.node = node
        self.msg = msg
        super(CompileError, self).__init__(*args)


class UnimplementedCompileError(CompileError):
    pass



def compiled_line(string: str) -> CompiledSegment:
    """ Factory for creating single line compiled segments

    """
    cs = CompiledSegment()
    cs.append(string)
    return cs


def echo(value: str) -> str:
    return "_app_.write({0})".format(value)


def python_safe(ident):
    """ Not implemented yet - depends if we ever get unsafe idents

    """
    return ident


def python_escape(string: str) -> str:
    """ Kinda ditto
    """
    return string


class Compiler(object):
    """ Compiler for a parse tree

    Uses the transformer to convert and optimise? the tree

    Compiles statement by statement

    """

    def __init__(self, tree=None, strip_comments=False):
        self.strip_comments = strip_comments
        self.imports = collections.defaultdict(list)
        self.imports["php2py.engine.metavars"] = ["_f_", "_g_", "_c_", "_constants_"]
        self.compiled = CompiledSegment()
        self.compiled.br(2)
        self.tree = tree

    def compile(self, tree=None) -> str:
        if tree is None:
            tree = self.tree
        tree = transformer.transform(tree)

        if not tree.kind == "ROOT":
            raise CompilationFailure("Must pass instance of RootNode to compile")
        success = True
        errors = []
        for c in tree:
            try:
                self.compiled.append(c.compile())
            except CompileError as e:
                success = False
                errors.append(e)
            self.compiled.br()
        if not success:
            raise CompilationFailure("Compilation failed with {} errors".format(len(errors)), errors)
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
        self.compiled.append('print("Try running php2py_run.py <script_name>")')
        self.compiled.dedent()

    def add_import(self, module: str, els=None):
        """ Add a python import at the top of the file.

        Capable of both import foo and from foo import baz style imports, depending on the optional parameter
        els.

        Args:
            module: The module name to import
            els: An optional list of items to import from that module

        """
        module = python_safe(module)
        if els is None or els[0] is None:
            self.compiled.prepend("import {0}".format(module))
        else:
            els = ", ".join([python_safe(e) for e in els])
            self.compiled.prepend("from {0} import {1}".format(module, els))

class Junk:
    def noop_compile(self, _) -> CompiledSegment:
        cs = CompiledSegment()
        cs.br()
        return cs

    def call_compile_str(self, node: parsetree.ParseNode) -> str:
        """ Compile a function or method call

        """
        # Process args
        # TODO: Deal with positional and other args combined
        arg_list = []
        kwarg_list = []
        if len(node.get("ARGSLIST")) > 0:
            for e in node.get("ARGSLIST"):
                if e.kind == "KEYVALUE":
                    kwarg_list.append(self.keyvalue_compile_str(e))
                else:
                    arg_list.append(self.expression_compile_str(e))
        if len(kwarg_list) != 0:
            kwargs = "**{" + ", ".join(kwarg_list) + "}"
            arg_list.append(kwargs)
        args = ", ".join(arg_list)
        return "{0}({1})".format(self.marshal_str(node[1]), args)

    def keyvalue_compile_str(self, node: parsetree.ParseNode, assign=": ") -> str:
        if len(node) != 2:
            parsetree.print_tree(node.parent)
            raise CompileError(node, "Keyvalues must have more than one child")
        return self.marshal_str(node[0]) + assign + self.marshal_str(node[1])

    def new_compile_str(self, node) -> str:
        return self.call_compile_str(node[0])

    def return_compile_str(self, node: parsetree.ParseNode) -> str:
        # TODO: Remove this method if exception never fires, else work out why two kinds of return
        raise Exception("We actually got here")
        # return "return " + self.expression_compile_str(node[0])


    def pass_compile_str(self, _) -> str:
        return "pass"


    def var_compile_str(self, node: parsetree.ParseNode) -> str:
        sub_var = ""
        if len(node) > 0:
            sub_var = self.subvar_compile_str(node[0])
        return python_safe(node.value) + sub_var

    def subvar_compile_str(self, node: parsetree.ParseNode) -> str:
        return '.{0}'.format(node.value)


    def getattr_compile_str(self, node):
        return "getattr({}, {})".format(self.marshal_str(node[1]), self.marshal_str(node[0]))

    def staticattr_compile_str(self, node):
        """ Static attr should change references to self etc to the proper class name..."""
        return "_c_.{}.{}".format(self.marshal_str(node[1]), self.marshal_str(node[0]))

    def constant_compile_str(self, node):
        # TODO: Contants might need further thought
        return "_constants_.{}".format(node.value)

    def comparator_compile_str(self, node):
        return self.operator2_compile_str(node)

    def global_compile_str(self, _):
        return ""

    def string_compile_str(self, node):
        fmt = ""
        if len(node) > 0:
            fmt = ".format({})".format(", ".join([v.value for v in node]))
        return 'u"' + node.value + '"' + fmt

    def oct_compile_str(self, node):
        return "0o" + node.value

    def phpconstant_compile_str(self, node: parsetree.ParseNode) -> str:
        return constant_map[node.value]

    def commentline_compile_str(self, node):
        # Should do something about putting comments on the end of a line properly
        if self.strip_comments:
            return ""
        return "#" + node.value

    def commentblock_compile_str(self, node):
        if self.strip_comments:
            return ""
        return "# " + node.value

    def commentblock_compile(self, node):
        seg = CompiledSegment()
        seg.append(self.commentblock_compile_str(node))
        return seg

    def magic_compile_str(self, node):
        if node.value not in magic_map:
            raise CompileError(node, "No magic value {} known".format(node.value))
        return magic_map[node.value]

    def dict_compile(self, node) -> CompiledSegment:
        out = CompiledSegment()
        for c in node:
            if len(c.children) == 3:
                out.append(self.marshal_str(c[0]) + ": " + self.marshal_str(c[2]))
        return out

    def tuple_compile_str(self, node):
        return "(" + ", ".join(self.marshal_str(c) for c in node) + ")"

    def list_compile_str(self, node):
        return "[" + ", ".join(self.marshal_str(c) for c in node) + "]"

    def expressiongroup_compile_str(self, node):
        return "({})".format(", ".join([self.marshal_str(c) for c in node]))

    def try_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("try:")
        seg.indent()
        seg.append(self.block_compile(node.get("BLOCK")))
        seg.dedent()
        for c in node.children[1:]:
            if c.kind != "CATCH":
                raise CompileError(node, "Expected catch block as child of try {}".format(c.token))
            exception_nodes = list(c.get_all("EXCEPTION"))
            if len(exception_nodes) == 1:
                catch_matches = exception_nodes[0].value
            else:
                catch_matches = "({})".format(
                    ", ".join([e.value for e in exception_nodes]))
            if "AS" in c:
                seg.append("except {} as {}:".format(
                    catch_matches,
                    self.marshal_str(c["AS"][0])
                ))
            else:
                seg.append("except {}:".format(catch_matches))
            seg.indent()
            catch_block = c["BLOCK"]
            seg.append(self.marshal(catch_block))
            seg.dedent()
        return seg

    def cast_compile_str(self, node: parsetree.ParseNode) -> str:
        return "{}({})".format(node.value, self.marshal_str(node[0]))

    def argslist_compile_str(self, node: parsetree.ParseNode) -> str:
        return ", ".join([self.marshal_str(child) for child in node])
