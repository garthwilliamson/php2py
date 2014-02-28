from __future__ import unicode_literals

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
    def __init__(self, tree=None, strip_comments=False):
        self.strip_comments = strip_comments
        self.imports = collections.defaultdict(list)
        self.imports["php2py"].append(("php"))
        self.results = []
        self.indent = 0
        self.tree = tree

    def compile(self, tree=None):
        if tree is None:
            tree = self.tree
        tree = transformer.transform(tree)

        self.generic_header_compile()
        for c in self.tree:
            self.marshal(c)
        self.generic_footer_compile()

        for i, v in self.imports.items():
            self.add_import(i, v)

    def __str__(self):
        return "\n".join(self.results)

    def generic_header_compile(self):
        self.blank_lines(2)
        self.append("def body(p):")
        self.indent += 4

    def generic_footer_compile(self):
        self.indent -= 4
        self.append("""\n\nif __name__ == "__main__":""")
        self.indent += 4
        self.append("""import os.path""")
        self.append("""php.serve_up(body, root_dir=os.path.abspath(os.path.dirname(__file__)))""")
        self.indent -= 4

    def add_import(self, module, els=None):
        module = self.python_safe(module)
        if els is None or els[0] is None:
            self.prepend("import {0}".format(module))
        else:
            els = ", ".join([self.python_safe(e) for e in els])
            self.prepend("from {0} import {1}".format(module, els))

    def add_output(self, value):
        self.append("php.write({0})".format(value))

    def append(self, line):
        self.results.append(' ' * self.indent + line)

    def prepend(self, line):
        self.results.insert(0, line)

    def blank_lines(self, number):
        for i in range(0, number):
            # Direct call to results to avoid extra spaces
            self.results.append("")

    def python_safe(self, ident):
        return ident

    def python_escape(self, string):
        return string

    def marshal(self, node):
        try:
            return getattr(self, node.node_type.lower() + "_compile")(node)
        except TypeError as e:
            print("Tried to compile...")
            parsetree.print_tree(node)
            print("...but failed")
            raise # CompileError("Probably something isn't returning a string when it should", e)
        except AttributeError as e:
            print("Tried to compile...")
            parsetree.print_tree(node)
            print("...but failed")
            raise CompileError("Unimplemented method " + node.node_type.lower() + "_compile", e)

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
        self.append("if {0}:".format(self.marshal(node[0][0])))
        self.indent += 4
        self.marshal(node[1])
        self.indent -= 4
        #TODO: Think about elif

    def function_compile(self, node):
        args = ["p"]
        for v in node[0]:
            args.append(self.var_compile(v[0]))
        self.append("@phpfunc")
        self.append("def {0}({1}):".format(node.value, ", ".join(args)))
        self.indent += 4
        self.marshal(node[1])
        self.indent -= 4
        self.append("p.f.{0} = {0}".format(node.value))
        if self.indent == 0:
            self.blank_lines(2)
        else:
            self.blank_lines(1)

    def call_compile(self, node):
        # Process args
        # TODO: Deal with possitional and other args combined
        arg_list = ["p"]
        kwarg_list = []
        kwargs = ""
        if len(node.children) > 0:
            for e in node:
                if e.node_type == "KEYVALUE":
                    kwarg_list.append(self.keyvalue_compile(e))
                else:
                    arg_list.append(self.expression_compile(e))

        if len(kwarg_list) != 0:
            kwargs = "**{" + ", ".join(kwarg_list) + "}"
            arg_list.append(kwargs)
        args = ", ".join(arg_list)
        return " p.f.{0}({1})".format(node.value, args, kwargs)

    def keyvalue_compile(self, node, assign=": "):
        if len(node.children) != 2:
            parsetree.print_tree(node.parent)
            raise CompileError("Keyvalues must have more than one child")
        return self.marshal(node[0]) + assign + self.marshal(node[1])

    def new_compile(self, node):
        return self.call_compile(node[0])

    def return_compile(self, node):
        return "return " + self.expression_compile(node[0])

    def pass_compile(self, node):
        self.append("pass")

    def expression_compile(self, node):
        if len(node.children) == 0:
            return ""
        r = "".join([self.marshal(c) for c in node]).lstrip()
        return r

    def var_compile(self, node):
        sub_var = ""
        if len(node.children) > 0:
            sub_var = self.subvar_compile(node.children[0])
        return " " + self.python_safe(node.value) + sub_var

    def subvar_compile(self, node):
        return '.{0}'.format(node.value)

    def globalvar_compile(self, node):
        return " p.g." + self.var_compile(node).lstrip()

    def index_compile(self, node):
        return "[{}]".format(self.expression_compile(node).lstrip())

    def constant_compile(self, node):
        #TODO: Contants might need further thought
        return " " + node.value

    def comparator_compile(self, node):
        return node.value

    def global_compile(self, node):
        return ""

    def block_compile(self, node):
        for c in node.children:
            self.marshal(c)

    def string_compile(self, node):
        fmt = ""
        if len(node.children) > 0:
            fmt = ".format({})".format(", ".join([v.value for v in node]))
        return " " + repr(node.value) + fmt

    def assignment_compile(self, node):
        return " {}".format(node.value)

    def operator_compile(self, node):
        return "({} {} {})".format(self.marshal(node.children[1]), node.value, self.marshal(node.children[0]))

    def statement_compile(self, node):
        if len(node.children) != 0:
            #for n in node:
                #print(n)
            self.append(" ".join([self.marshal(c) for c in node]))

    def int_compile(self, node):
        return str(node.value)

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
        # TODO: Note that we don't deal with comments inline very well. Should strip them if they are in the wrong place
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

    def expressiongroup_compile(self, node):
        return " ({})".format([self.marshal(c) for c in node.children])

    def try_compile(self, node):
        self.append("try:")
        self.indent += 4
        self.marshal(node[0])
        self.indent -= 4
        catch = node[1]
        catch_match = catch[0]
        catch_block = catch[1]
        self.append("except {} as {}:".format(self.marshal(catch_match[0][0]), self.marshal(catch_match[0][1])))
        self.indent += 4
        self.marshal(catch_block)
        self.indent -= 4

    def switch_compile(self, node):
        #TODO: Transform switch statements
        pass

    def cast_compile(self, node):
        return " {}({})".format(node.value, self.marshal(node[0]))