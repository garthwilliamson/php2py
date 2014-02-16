from __future__ import unicode_literals


import collections


constant_map = {
    "true": "True",
    "false": "False",
    "null": "None",
}


class Compiler(object):
    def __init__(self, tree):
        self.imports = collections.defaultdict(list)
        self.imports["php"].append(None)
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

    def generic_footer_compile(self):
        self.append("""if __name__ == "__main__":\n    php.print_output()\n""")

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
        #print("marshalling", node)
        try:
            return getattr(self, node.node_type.lower() + "_compile")(node)
        except TypeError:
            raise

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
        self.append("def {0}({1}):".format(node.value, ", ".join([self.var_compile(v[0]) for v in node[0]])))
        self.indent += 4
        self.marshal(node[1])
        self.indent -= 4
        self.append("php.f.{0} = {0}".format(node.value))
        if self.indent == 0:
            self.blank_lines(2)
        else:
            self.blank_lines(1)

    def call_compile(self, node):
        return "php.f.{0}({1})".format(node.value, ", ".join([self.expression_compile(e) for e in node[0]]))

    def return_compile(self, node):
        self.append("return " + self.expression_compile(node[0]))

    def expression_compile(self, node):
        return " ".join([self.marshal(c) for c in node])

    def var_compile(self, node):
        return self.python_safe(node.value)

    def comparator_compile(self, node):
        return node.value

    def block_compile(self, node):
        for c in node.children:
            self.marshal(c)

    def echo_compile(self, node):
        self.add_output(" + ".join([self.marshal(c) for c in node]))

    def string_compile(self, node):
        fmt = ""
        if len(node.children) > 0:
            print(node.children[0])
            fmt = ".format({})".format(", ".join([v.value for v in node]))
        return repr(node.value) + fmt

    def assignment_compile(self, node):
        return "{}".format(node.value)

    def operator_compile(self, node):
        return "{}".format(node.value)

    def statement_compile(self, node):
        if len(node.children) != 0:
            self.append(" ".join([self.marshal(c) for c in node]))

    def int_compile(self, node):
        return str(node.value)

    def constant_compile(self, node):
        return constant_map[node.value]
