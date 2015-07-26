from __future__ import unicode_literals

import collections
import logging

from . import parsetree, transformer


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


class CompiledSegment(object):
    def __init__(self) -> 'CompiledSegment':
        self._indent = 0
        self.lines = []

    def append(self, item):
        """ Append a string or CompiledSegment to the end of this segment

        """
        if item is None:
            raise TypeError("Can't append a null item to compiled segment")
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
        for l, i in self.lines:
            out += "    " * i + l + "\n"
        return out

    def __iter__(self):
        return iter(self.lines)

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, item):
        return self.lines[item][0]


def compiled_line(string: str) -> CompiledSegment:
    """ Factory for creating single line compiled segments

    """
    cs = CompiledSegment()
    cs.append(string)
    return cs


def echo(value: str) -> str:
    return "echo({0})".format(value)


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
        self.imports["php2py.php"] = ["_app_", "_f_", "_g_", "_c_", "_constants_"]
        self.imports["php2py.specials"].append("*")
        self.compiled = CompiledSegment()
        self.compiled.br(2)
        self.tree = tree

    def compile(self, tree=None) -> str:
        if tree is None:
            tree = self.tree
        transformer.transform(tree)

        success = True
        errors = []
        for c in tree:
            try:
                self.compiled.append(self.marshal(c))
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
        self.compiled.append('import os.path')
        self.compiled.append('_app_.init_console(body, script_name=__file__)')
        self.compiled.append('import sys')
        self.compiled.append('sys.stdout.buffer.write(_app_.console_response())')
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

    def marshal(self, node: parsetree.ParseNode) -> CompiledSegment:
        """ Tries to find the correct function from a given node from the parse tree

        When given a node, tries to find a compile_<node_name> function.

        Args:
            node: The node to try to compile

        Raises:
            CompileError: A common error to be returned is the CompileError when a given node type doesn't
                          have an appropriate compile method defined yet.

        """
        try:
            res = getattr(self, node.node_type.lower() + "_compile")(node)
            return res
        except AttributeError:
            raise UnimplementedCompileError(node, "Unimplemented method " + node.node_type.lower() + "_compile")
        except CompileError:
            raise
        except Exception as e:
            raise CompileError(node, "Unexpected error compiling node", e)

    def marshal_str(self, node: parsetree.ParseNode) -> str:
        try:
            res = getattr(self, node.node_type.lower() + "_compile_str")(node)
            assert isinstance(res, str)
            return res
        except AttributeError:
            raise UnimplementedCompileError(node, "Unimplemented method " + node.node_type.lower() + "_compile_str")
        except CompileError:
            raise
        except Exception as e:
            raise CompileError(node, "Unexpected error compiling node", e)

    def php_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        php_segment = CompiledSegment()
        for c in node:
            php_segment.append(self.marshal(c))
        return php_segment

    def html_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        # return self.echo(repr(node.value))
        return compiled_line(echo(repr(node.value)))

    def noop_compile(self, _) -> CompiledSegment:
        cs = CompiledSegment()
        cs.br()
        return cs

    def noop_compile_str(self, _) -> str:
        return ""

    def while_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("while {0}:".format(self.expression_compile_str(node["EXPRESSIONGROUP"]["EXPRESSION"])))
        seg.indent()
        seg.append(self.block_compile(node["BLOCK"]))
        seg.dedent()
        return seg

    def if_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        try:
            # print("Compiled " + "if {0}:".format(self.expression_compile(node.get("EXPRESSION"))))
            # print("from")
            # parsetree.print_tree(node.get("EXPRESSION"))
            seg.append("if {0}:".format(self.expression_compile_str(node.get("EXPRESSION"))))
        except IndexError:
            print("Compile Error at ", node.token)
            parsetree.print_tree(node)
            raise
        seg.indent()
        seg.append(self.marshal(node.get("BLOCK")))
        # TODO: We should catch failure to get somewhere at the top level. IndexError maybe?
        seg.dedent()
        for n in node.get_all("ELIF"):
            seg.append(self.elif_compile(n))
        for n in node.get_all("ELSE"):
            seg.append(self.else_compile(n))
        return seg

    def elif_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("elif {}:".format(self.expression_compile_str(node.get("EXPRESSION"))))
        seg.indent()
        seg.append(self.marshal(node.get("BLOCK")))
        seg.dedent()
        return seg

    def else_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("else:")
        seg.indent()
        seg.append(self.marshal(node.get("BLOCK")))
        seg.dedent()
        return seg

    def pyfor_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("for {} in {}:".format(self.marshal_str(node[0]), self.marshal_str(node["EXPRESSION"])))
        seg.indent()
        seg.append(self.marshal(node["BLOCK"]))
        seg.dedent()
        return seg

    def function_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        args = []
        for v in node["ARGSLIST"]:
            args.append(self.marshal_str(v))
        # seg.append("@phpfunc")
        seg.append("def {0}({1}):".format(node.value, ", ".join(args)))
        seg.indent()
        seg.append(self.marshal(node["BLOCK"]))
        seg.dedent()
        return seg

    def class_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        seg.append("class {}(_c_.{}):".format(node.value, node["EXTENDS"].value))
        seg.indent()
        seg.append(self.marshal(node.get("BLOCK")))
        seg.dedent()
        return seg

    def classmethod_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        # TODO: This is wrong - we should do _most_ of the function compile, but not the adding to php functions bit
        return self.function_compile(node)

    def method_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        # TODO: Ditto
        return self.function_compile(node)

    def call_compile_str(self, node: parsetree.ParseNode) -> str:
        """ Compile a function or method call

        """
        # Process args
        # TODO: Deal with positional and other args combined
        arg_list = []
        kwarg_list = []
        if len(node.get("ARGSLIST")) > 0:
            for e in node.get("ARGSLIST"):
                if e.node_type == "KEYVALUE":
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

    def return_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        return compiled_line("return {}".format(self.expression_compile_str(node[0])))

    def pass_compile_str(self, _) -> str:
        return "pass"

    def expression_compile_str(self, node: parsetree.ParseNode) -> str:
        # print("Compiling expression")
        # print("from")
        # parsetree.print_tree(node)
        if len(node) == 0:
            return ""
        r = "".join([self.marshal_str(c) for c in node]).lstrip()
        return r

    def var_compile_str(self, node: parsetree.ParseNode) -> str:
        sub_var = ""
        if len(node) > 0:
            sub_var = self.subvar_compile_str(node[0])
        return python_safe(node.value) + sub_var

    def subvar_compile_str(self, node: parsetree.ParseNode) -> str:
        return '.{0}'.format(node.value)

    def globalvar_compile_str(self, node):
        return "_g_." + self.var_compile_str(node).lstrip()

    def ident_compile_str(self, node):
        return node.value

    def index_compile_str(self, node):
        return "{}[{}]".format(self.marshal_str(node[1]), self.marshal_str(node[0]))

    def attr_compile_str(self, node):
        return "{}.{}".format(self.marshal_str(node[1]), self.marshal_str(node[0]))

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

    def block_compile(self, node: parsetree.ParseNode) -> CompiledSegment:
        seg = CompiledSegment()
        for c in node:
            seg.append(self.marshal(c))
        return seg

    def string_compile_str(self, node):
        fmt = ""
        if len(node) > 0:
            fmt = ".format({})".format(", ".join([v.value for v in node]))
        return 'u"' + node.value + '"' + fmt

    def assignment_compile_str(self, node):
        return "{} {} {}".format(self.marshal_str(node[1]), node.value, self.marshal_str(node[0]))

    def operator2_compile_str(self, node):
        fmt_str = "{} {} {}"
        if node.value in ["."]:
            fmt_str = "{}{}{}"
        try:
            return fmt_str.format(self.marshal_str(node[1]), node.value, self.marshal_str(node[0]))
        except IndexError:
            raise CompileError(node, "Expected two children for {}".format(node))

    def operator1_compile_str(self, node):
        return "{} {}".format(node.value, self.marshal_str(node[0]))

    def operator3_compile_str(self, node):
        if node.value != "?":
            raise UnimplementedCompileError("There are ternaries not called ?")
        return "{} if {} else {}".format(
            self.marshal_str(node[0]),
            self.marshal_str(node[2]),
            self.marshal_str(node[1]))

    def statement_compile(self, node) -> CompiledSegment:
        if len(node) != 0:
            # for n in node:
            # print(n)
            cs = CompiledSegment()
            for c in node:
                cs.append(self.marshal_str(c))
            return cs

    def int_compile_str(self, node):
        return str(node.value)

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
            if c.node_type != "CATCH":
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
