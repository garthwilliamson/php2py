from __future__ import unicode_literals

import collections

from . import parsetree


constant_map = {
    "true": "True",
    "false": "False",
    "null": "None",
}

magic_map = {
    "__file__": "__file__",
}

class CompileError(Exception):
    pass


class Compiler(object):
    def __init__(self, tree):
        self.imports = collections.defaultdict(list)
        self.imports["php2py"].append(("php"))
        self.results = []
        self.indent = 0

        self.generic_header_compile()
        for c in tree:
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
        self.append("""if __name__ == "__main__":\n    php.serve_up(body)\n""")

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
        #print(line)
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
            raise CompileError("Probably something isn't returning a string when it should", e)
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
        self.append("while {0}:".format(self.marshal(node[0])))
        self.indent += 4
        self.marshal(node[1])
        self.indent -= 4

    def if_compile(self, node):
        self.append("if {0}:".format(self.marshal(node[0])))
        self.indent += 4
        self.marshal(node[1])
        self.indent -= 4
        #TODO: Think about elif

    def function_compile(self, node):
        self.append("@phpfunc\ndef {0}(p, {1}):".format(node.value, ", ".join([self.var_compile(v[0]) for v in node[0]])))
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
        args = ""
        if node[0].node_type == "DICT":
            args = "**{" + self.dict_compile(node[0]) + "}"
        else:
            for e in node[0]:
                arg_list = []
                arg_list.append(self.expression_compile(e))
                args = ", ".join(arg_list)
        return "p.f.{0}(p, {1})".format(node.value, args)

    def new_compile(self, node):
        return self.call_compile(node[0])

    def return_compile(self, node):
        self.append("return " + self.expression_compile(node[0]))

    def expression_compile(self, node):
        return " ".join([self.marshal(c) for c in node])

    def var_compile(self, node):
        sub_var = ""
        if len(node.children) > 0:
            sub_var = self.subvar_compile(node.children[0])
        return self.python_safe(node.value) + sub_var

    def subvar_compile(self, node):
        return '.{0}'.format(node.value)

    def globalvar_compile(self, node):
        return "p.g." + self.var_compile(node)

    def comparator_compile(self, node):
        return node.value

    def global_compile(self, node):
        pass

    def block_compile(self, node):
        for c in node.children:
            self.marshal(c)

    def echo_compile(self, node):
        return " + ".join([self.marshal(c) for c in node])

    def string_compile(self, node):
        fmt = ""
        if len(node.children) > 0:
            fmt = ".format({})".format(", ".join([v.value for v in node]))
        return repr(node.value) + fmt

    def assignment_compile(self, node):
        return "{}".format(node.value)

    def operator_compile(self, node):
        return "{}".format(node.value)

    def statement_compile(self, node):
        if len(node.children) != 0:
            #for n in node:
                #print(n)
            self.append(" ".join([self.marshal(c) for c in node]))

    def int_compile(self, node):
        return str(node.value)

    def constant_compile(self, node):
        return constant_map[node.value]

    def commentline_compile(self, node):
        # Should do something about putting comments on the end of a line properly
        if node.parent.node_type in ("STATEMENT", "EXPRESSION"):
            return "#" + node.value + "\n"
        else:
            self.append("#" + node.value)

    def commentblock_compile(self, node):
        # TODO: Note that we don't deal with comments inline very well. Should strip them if they are in the wrong place
        self.append('"""{}"""\n'.format(node.value))

    def require_once_compile(self, node):
        return "p.f.require_once(p, {0})".format(self.expression_compile(node[0]))

    def magic_compile(self, node):
        if node.value not in magic_map:
            raise CompileError("No magic value {0} known".format(node.value))
        return magic_map[node.value]

    def dict_compile(self, node):
        out = []
        for c in node:
            if len(c.children) == 3:
                out.append(self.marshal(c[0]) + ": " + self.marshal(c[2]))
        return (", ".join(out))
