import re


class ParseException(Exception):
    pass


class ParseError(ParseException):
    pass


class ExpectedCharError(ParseError):
    pass


class UnexpectedCharError(ParseError):
    pass


class UpTooMuchException(Exception):
    pass


class ParseNode(object):
    def __init__(self, node_type, parent=None, value=None):
        self.node_type = node_type
        self.parent = parent
        self.value = value
        self.children = []

    def append(self, node):
        self.children.append(node)

    def to_list(self):
        if len(self.children) > 0:
            return self.node_type, self.value, [c.to_list() for c in self.children]
        else:
            return self.node_type, self.value

    def __getitem__(self, key):
        return self.children[key]

    def __setitem__(self, key, value):
        self.children[key] = value

    def __delitem__(self, key):
        del(self.children[key])

    def __str__(self):
        if self.value is not None:
            return self.node_type + ":" + str(self.value)
        else:
            return self.node_type

    def __iter__(self):
        return iter(self.children)


class ParseTree(object):
    def __init__(self, name):
        self.root_node = ParseNode("ROOT", value=name)
        self.cur = self.root_node

    def up(self):
        #print("Going up from", self.cur, "to", self.cur.parent)
        if self.cur.parent is None:
            raise UpTooMuchException("Can't go up from here")
        self.cur = self.cur.parent

    def append(self, node_type, value=None):
        #print("Appending node", node_type, value, "to", self.cur)
        new_node = ParseNode(node_type, self.cur, value)
        self.cur.append(new_node)
        return new_node


class Parser(object):
    def __init__(self, contents, name, debug=False):
        self.pt = ParseTree(name)
        self.chars = contents
        self.debug = debug
        self.cursor = 0

    def search_until(self, search_re):
        if self.debug:
            print("Searching at", self.get(10), self.cursor, search_re.pattern)
        m = search_re.search(self.chars, self.cursor)
        if m is None:
            return "EOF", self.chars[self.cursor:]
        text_until = self.chars[self.cursor:m.start()]
        self.cursor = m.end()
        return m.group(0), text_until

    def match_for(self, match_re):
        if self.debug:
            print("Matching at", self.get(10), self.cursor, match_re.pattern)
        m = match_re.match(self.chars, self.cursor)
        if m is None:
            return None
        if self.debug:
            print("Found", m.group(0))
        self.cursor = m.end()
        return m.group(0)

    def check_for(self, s):
        if self.chars.startswith(s, self.cursor):
            return True
        return False

    def get(self, length=1):
        return self.chars[self.cursor:self.cursor + length]

    def next_non_white(self):
        self.match_for(whitespace_search)

    def is_eof(self):
        if self.cursor >= len(self.chars):
            return True
        else:
            return False

    def to_list(self, ):
        return self.pt.root_node.to_list()

    def get_tree(self):
        return self.pt.root_node


def create_pattern(items):
    pattern = "|".join([re.escape(i) for i in items])
    return re.compile(pattern, flags=re.IGNORECASE)


# REMEMBER BIGGEST TO SMALLEST
PHP_START = ("<?php",)
html_search = create_pattern(PHP_START)
IDENTIFIERS = "[a-z_][a-z_1-9]*"
ident_search = re.compile(IDENTIFIERS, flags=re.IGNORECASE)
# Have to do these all at once because of sizing issues
COMPARATORS = ["===", "!==", "==", "!=", "<>", "<=", ">=", "<", ">"]
OPERATORS = ["AND", "XOR",
             "<<", ">>", "||", "OR", "++", "--",
             "+", "-", "*", "/", "%", ".", "&", "|", "^", "~", "!"]
ASSIGNMENTS = ["<<=", ">>=",
              "+=", "-=", "*=", "/=", "|=", "^=", "="]
FUNKY_KEYWORDS = ["require", "include"]
CONSTANTS = ["true", "false"]
SYMBOLS = COMPARATORS + OPERATORS + ASSIGNMENTS + FUNKY_KEYWORDS + CONSTANTS
SYMBOLS.sort(key=len, reverse=True)
symbol_search = create_pattern(SYMBOLS)
whitespace_search = re.compile("\\s*")
CONTROLS = "function return switch while class for if do".split()
SPECIAL_STATEMENTS = ["echo"]
special_search = re.compile("(" + "|".join([re.escape(w) for w in SPECIAL_STATEMENTS]) + ")([ \\(])")
control_search = re.compile("(" + "|".join([re.escape(w) for w in CONTROLS]) + ")([ \\(])")
int_search = re.compile("[0-9]+")
callable_search = re.compile(IDENTIFIERS + "\\(", flags=re.IGNORECASE)


class PhpParser(Parser):
    def parse(self):
        self.parse_html()

    def parse_html(self):
        while True:
            match, contents = self.search_until(html_search)
            if contents != "":
                self.pt.append("HTML", contents)
            if match != "EOF" and match is not None:
                self.pt.cur = self.pt.append("PHP", None)
                self.parse_php()
                self.pt.up()
                if self.is_eof():
                    return
            else:
                return
        return

    def parse_php(self):
        while True:
            self.next_non_white()
            self.parse_statement()
            if self.check_for("?>") or self.is_eof():
                self.cursor += 2
                return

    def parse_statement(self, expr=False, comma=False):
        control = control_search.match(self.chars, self.cursor)
        if control is not None:
            self.cursor = control.end() - 1    # go back one in case we had a "("
            self.parse_control(control.group(1))
            return
        special = special_search.match(self.chars, self.cursor)
        if special is not None:
            self.cursor = special.end() - 1
            self.parse_special(special.group(1))
            return
        if expr:
            self.pt.cur = self.pt.append("EXPRESSION")
        else:
            self.pt.cur = self.pt.append("STATEMENT")
        while True:
            if self.check_for("$"):
                self.parse_variable()
            elif self.check_for('"'):
                self.parse_string()
            elif self.check_for("//"):
                self.cursor += 2
                self.parse_comment_line()
            elif self.check_for("#"):
                self.cursor += 1
                self.parse_comment_line()
            elif self.check_for(';'):
                self.cursor += 1
                self.next_non_white()    # do this here because statements ending with ?> shouldn't do it
                break
            elif self.check_for("?>"):
                break
            elif self.check_for("{"):
                self.cursor += 1
                self.parse_block()
            elif self.check_for("}"):
                break
            elif self.check_for(")"):
                break
            elif comma and self.check_for(","):
                # This is for special operators mostly
                break
            else:
                match = self.match_for(symbol_search)
                if match is not None:
                    self.parse_symbol(match)
                    continue
                match = self.match_for(int_search)
                if match is not None:
                    self.parse_int(match)
                    continue
                match = self.match_for(callable_search)
                if match is not None:
                    self.parse_callable(match)
                    continue

                # Deal with the dregs
                self.next_non_white()
                if self.is_eof():
                    break
                else:
                    raise UnexpectedCharError("Didn't expect to see " + self.get(10) + " here")
        self.pt.up()

    def parse_variable(self):
        self.cursor += 1    # eliminate $
        match = self.match_for(ident_search)
        if match is None:
            raise ExpectedCharError("Alpha or _ expected after $")
        self.pt.append("VAR", match)
        if self.check_for("->"):
            self.cursor += 2
            match = self.match_for(ident_search)
            self.pt.cur = self.pt.append("SUBVAR", match)
        self.next_non_white()

    def parse_string(self):
        delim = self.get()
        self.cursor += 1
        format_vars = []

        def search_string(delim):
            search_expr = re.compile("\\\\" + delim + "|\\$|" + delim)
            res = ""
            while True:
                match, string_until = self.search_until(search_expr)
                res += string_until
                if match == "EOF":
                    raise ExpectedCharError("Expected the end of a string")
                elif match == delim:
                    return res
                elif match == "$":
                    var = self.match_for(ident_search)
                    res += "{}"
                    format_vars.append(var)
                else:
                    # get rid of the backslash
                    res += string_until[-2:] + delim
        res = search_string(delim)
        if len(format_vars) > 0:
            self.pt.cur = self.pt.append("STRING", res)
            for v in format_vars:
                self.pt.append("VARIABLE", v)
            self.pt.up()
        else:
            self.pt.append("STRING", res)
        self.next_non_white()

    def parse_comment_line(self):
        match, value = self.search_until("\\\\n")
        self.pt.append("COMMENT_L", value)
        self.next_non_white()

    def parse_symbol(self, symbol):
        symbol = symbol.lower()
        if symbol in COMPARATORS:
            self.parse_comparator(symbol)
        elif symbol in OPERATORS:
            self.parse_operator(symbol)
        elif symbol in ASSIGNMENTS:
            self.parse_assignment(symbol)
        elif symbol in FUNKY_KEYWORDS:
            self.pt.append(symbol)
            raise NotImplemented
        elif symbol in CONSTANTS:
            self.pt.append("CONSTANT", symbol)
        else:
            raise ParseException("Implement" + symbol)
        self.next_non_white()

    def parse_block(self):
        self.next_non_white()
        if not self.check_for("{"):
            raise ExpectedCharError("Expected { to start block, instead saw " + self.get(10))
        self.cursor += 1
        self.pt.cur = self.pt.append("BLOCK")
        self.next_non_white()
        while True:
            self.parse_statement()
            self.next_non_white()
            if self.check_for("}"):
                self.cursor += 1
                break
        self.pt.up()

    def parse_control(self, keyword):
        self.next_non_white()
        self.pt.cur = self.pt.append(keyword.upper())
        if keyword in "if while":
            if not self.check_for("("):
                raise ExpectedCharError("Expected ( at start of if statement")
            self.cursor += 1
            self.parse_statement(expr=True)
            self.cursor += 1
            self.next_non_white()
            self.parse_block()
        elif keyword in "function":
            match = self.match_for(ident_search)
            if match is None:
                raise ExpectedCharError("Alpha or _ expected as function name")
            self.pt.cur.value = match
            self.parse_arg_list()
            self.parse_block()
        elif keyword in "return":
            self.next_non_white()
            self.parse_statement(expr=True)
        else:
            raise NotImplemented
        self.next_non_white()
        self.pt.up()

    def parse_arg_list(self):
        if not self.check_for("("):
            raise ExpectedCharError("Expected ( at start of function statement")
        self.cursor += 1
        self.pt.cur = self.pt.append("ARGLIST")
        while True:
            if self.check_for(")"):
                break
            elif self.check_for(","):
                self.cursor += 1
            self.next_non_white()
            self.parse_statement(expr=True, comma=True)
        self.cursor += 1
        self.pt.up()
        #while True:
            #self.next_non_white()
            #
                #self.cursor += 1
                #self.pt.up()
                #return
            #elif self.check_for("$"):
                #self.parse_variable()
            #else:
                #raise UnexpectedCharError("Didn't expect to see " + self.get(10) + " in function arguments")

    def parse_special(self, keyword):
        self.next_non_white()
        self.pt.cur = self.pt.append(keyword.upper())
        if keyword in "echo":
            while True:
                self.parse_statement(expr=True, comma=True)
                self.next_non_white()
                if self.get() != ",":
                    self.pt.up()
                    return

    def parse_comparator(self, c):
        self.pt.append("COMPARATOR", c)
        self.next_non_white()

    def parse_assignment(self, a):
        self.pt.append("ASSIGNMENT", a)
        self.next_non_white()

    def parse_int(self, i):
        self.pt.append("INT", int(i))

    def parse_operator(self, o):
        if o in ("++", "--"):
            self.pt.append("ASSIGNMENT", o[0] + "=")
            self.pt.append("INT", 1)
        else:
            self.pt.append("OPERATOR", o)
        self.next_non_white()

    def parse_callable(self, c):
        # Matched the "(" too...
        self.cursor -= 1
        self.next_non_white()
        self.pt.cur = self.pt.append("CALL", c[0:-1])
        self.parse_arg_list()
        self.next_non_white()
        self.pt.up()


constant_map = {
    "true": "True",
    "false": "False",
    "null": "None",
}


import collections


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

################# HERE FOLLOWS SOME USEFUL UTILS #####################


def print_tree(tree, indent=0):
    print(indent * " " + str(tree))
    for c in tree:
        print_tree(c, indent + 4)


def parse_and_compile(string, name="anon"):
    parser = PhpParser(string, "test", False)
    parser.parse()
    c = Compiler(parser.get_tree())
    return c


if __name__ == "__main__":
    import sys
    fname = sys.argv[1]
    contents = "".join(open(fname, "r").readlines())