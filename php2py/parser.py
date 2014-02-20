from __future__ import unicode_literals
from __future__ import print_function

from .parsetree import ParseTree

import re
from functools import wraps


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


class Parser(object):
    def __init__(self, contents, name, debug=False):
        self.scope = []
        self.globals = []
        self.pt = ParseTree(name, self.get_cursor)
        self.chars = contents
        self.debug = debug
        self.cursor = 0

    def get_cursor(self):
        return self.cursor

    def search_until(self, search_re):
        if self.debug:
            print("Searching at", self.get(10), self.cursor, search_re.pattern)
        m = search_re.search(self.chars, self.cursor)
        if m is None:
            # Set the cursor to the end of the file
            text_until = self.chars[self.cursor:]
            self.cursor = len(self.chars)
            return "EOF", text_until
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
            print("Found", m.group())
        self.cursor = m.end()
        self.last_match = m.group()
        return m.group()

    def check_for(self, s):
        if self.debug:
            print(s, end="")
        if self.chars.startswith(s, self.cursor):
            if self.debug:
                print("found")
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

    def push_scope(self, name):
        self.scope.append(name)
        self.globals.append([])

    def pop_scope(self):
        self.scope.pop()
        self.globals.pop()

    def is_global(self, variable):
        if variable in self.globals[-1]:
            return True
        else:
            return False

    def scope_is(self, s):
        if self.scope[-1] == s:
            return True
        else:
            return False

    def add_global(self, g):
        self.globals[-1].append(g)

    def line_start(self):
        return self.chars.rfind("\n", 0, self.cursor) + 1

    def get_line(self):
        start = self.line_start()
        if start == -1:
            start = 0
        end = self.chars.find("\n", self.cursor)
        if end == -1:
            end = 0
        return self.chars[start:end]

    def line_number(self):
        return self.chars.count("\n", 0, self.cursor) + 1

    def print_cur_location(self, msg):
        print(self.get_line())
        print(" " * (self.cursor - self.line_start()) + "^ --- " + msg)

    def print_node_info(self, node, recurse=True, start_indent=None):
        if start_indent is None:
            start_indent = node.start_cursor
        start = node.start_cursor
        indent = len(repr(self.chars[start_indent:start]))

        try:
            end = node.end_cursor
        except AttributeError:
            print("{} has no end cursor. Up mustn't have been called for it or one of its children".format(node))
            end = len(self.chars)
        print("{:<30}{:<7}{}{!r}".format(str(node), str(start) + ":" + str(end), " " * (indent), self.chars[start:end]))

        if recurse:
            for c in node:
                self.print_node_info(c, recurse, start_indent)


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
             "=>",        # Here because I don't know where else to put it
             "<<", ">>", "||", "&&", "OR", "++", "--",
             "+", "-", "*", "/", "%", ".", "&", "|", "^", "~", "!"]
ASSIGNMENTS = ["<<=", ">>=",
              "+=", "-=", "*=", "/=", "|=", "^=", "="]
MAGIC_CONSTANTS = ["__line__", "__file__", "__dir__", "__function__", "__class__",
                   "__trait__", "__method__", "__namespace__"]
CONSTANTS = ["true", "false"]
SYMBOLS = COMPARATORS + OPERATORS + ASSIGNMENTS + CONSTANTS + MAGIC_CONSTANTS
SYMBOLS.sort(key=len, reverse=True)
symbol_search = create_pattern(SYMBOLS)
whitespace_search = re.compile("\\s+")
CONTROLS = "function global return switch while class call for if do".split()
SPECIAL_STATEMENTS = ["echo ", "echo(",
                      "new ",
                      "die ", "die;",
                      "require_once ", "require_once(", "require ", "require(",
                      "include ", "include("]
special_search = create_pattern(SPECIAL_STATEMENTS)
control_search = re.compile("(" + "|".join([re.escape(w) for w in CONTROLS]) + ")([ \\(])")
int_search = re.compile("[0-9]+")
callable_search = re.compile(IDENTIFIERS + "\\s*\\(", flags=re.IGNORECASE)
endline_search = re.compile("(\\r)?\\n|$")
endstatement_search = create_pattern(("?>", ";", "}"))
open_brace_search = re.compile("\\(")
close_brace_search = re.compile("\\)")
comma_search = re.compile(re.escape(","))
space_tab_search = re.compile("\t| ")


class PhpParser(Parser):
    def parse(self):
        self.push_scope("GLOBAL")
        try:
            self.pt.cur.end_cursor = len(self.chars)
            self.parse_html()
            if self.pt.cur.node_type != "ROOT":
                self.pt.up()
        except ParseException as e:
            print("Parse error on line {}:".format(self.line_number()))
            self.print_node_info(self.pt.root_node)
            self.print_cur_location(str(e))
            raise

    def parse_html(self):
        while True:
            match, contents = self.search_until(html_search)
            if contents != "":
                self.pt.append("HTML", contents, -len(contents))
                self.pt.last.end_cursor = self.cursor
            if match != "EOF" and match is not None:
                self.parse_php()
                if self.is_eof():
                    return
            else:
                return
        return

    def parse_php(self):
        self.pt.cur = self.pt.append("PHP", None)
        while True:
            self.start_marker = self.cursor
            if self.debug:
                print("*********")
            self.next_non_white()
            if self.is_eof():
                break
            if self.check_for("//"):
                self.parse_comment_line()
            elif self.check_for("#"):
                self.parse_comment_line()
            elif self.match_for(re.compile(re.escape("?>"))) is not None or self.is_eof():
                break
            elif self.check_for("/*"):
                self.parse_comment_group()
            else:
                self.parse_statement()
            self.next_non_white()
            if self.is_eof():
                break
        if self.last_match == "?>":
            self.pt.up(end_offset=-2)
        else:
            self.pt.up()

    def parse_statement(self, start_offset=0):
        if self.debug:
            print("+++++++++++++++++++++++++++")
            print("Parsing statement at |{0}|".format(self.get(10)))
            print(self.get_line())
        control = control_search.match(self.chars, self.cursor)
        if control is not None:
            self.cursor = control.end() - 1    # go back one in case we had a "("
            self.parse_control(control.group(1))
            self.next_non_white()
            m = self.match_for(endstatement_search)
            if m is None:
                raise ExpectedCharError("Expected to see ; or } after control structure")
            return
        else:
            self.pt.append_and_into("STATEMENT", self.start_marker)
            self.next_non_white()
            self.parse_expression()
            self.next_non_white()
            if self.is_eof():
                return
            m = self.match_for(endstatement_search)
            if m is None:
                raise UnexpectedCharError("Didn't expect to see `{}` here".format(self.get()))
            statement_end = self.cursor + len(m)
            # Statements can end with comments
            self.match_for(space_tab_search)
            if self.check_for("//"):
                self.parse_comment_line()
                statement_end = self.cursor
            elif self.check_for("/*"):
                self.parse_comment_group()
                statement_end = self.cursor
            self.pt.up(end_offset=-self.cursor + statement_end)

    def parse_expression(self):
        if self.debug:
            print("^^^^^^^^ Parsing expresion at ", self.cursor)
        self.pt.cur = self.pt.append("EXPRESSION")
        while True:
            self.start_marker = self.cursor
            self.next_non_white()
            if self.check_for("("):
                self.parse_expression_group()
                break
            if self.check_for(";") or self.check_for(")") or self.check_for(",") or self.check_for("?>") or self.is_eof():
                print("breaking from {} because reached {}".format(self.pt.cur, self.get()))
                break
            elif self.check_for("//"):
                if self.debug:
                    print("COMMENT")
                self.parse_comment_line()
            elif self.check_for("/*"):
                self.parse_comment_group()
            elif self.check_for('"') or self.check_for("'"):
                self.parse_string()
            elif self.check_for("$"):
                self.pt.cur.append(self.parse_variable())
            elif self.match_for(symbol_search) is not None:
                self.parse_symbol(self.last_match)
            elif self.match_for(int_search) is not None:
                self.parse_basic("INT", int(self.last_match))
            elif self.match_for(special_search) is not None:
                self.parse_special(self.last_match)
            elif self.match_for(callable_search) is not None:
                self.parse_callable(self.last_match)
            elif self.match_for(ident_search) is not None:
                # I don't like doing this - will it always be a constant? I don't think so!
                self.parse_constant(self.last_match)
            else:
                raise UnexpectedCharError("`{}` in expression".format(self.get()))
        print("Returning from {} at {} because end of expression function".format(self.pt.cur, self.get()))
        self.pt.up()

    def parse_expression_group(self):
        m = self.match_for(open_brace_search)
        if m != "(":
            raise ExpectedCharError("Expected ( at start of item")
        eg = self.pt.append_and_into("EXPRESSIONGROUP", start_offset=-1)
        self.next_non_white()
        m = self.match_for(close_brace_search)
        if m == ")":
            print("Returning from {} because )".format(self.pt.cur))
            self.pt.up()
            return eg
        while True:
            self.next_non_white()
            self.parse_expression()
            self.next_non_white()
            if self.match_for(comma_search) is None:
                break
        m = self.match_for(close_brace_search)

        if m != ")":
            raise ExpectedCharError("Expected to see `)` after sub expression `{}`".format(self.pt.cur))
        self.pt.up()
        print("Returning from {} because function end".format(self.pt.cur))
        return eg


    def parse_variable(self):
        start = self.cursor
        self.cursor += 1    # eliminate $
        match = self.match_for(ident_search)
        if match is None:
            raise ExpectedCharError("Alpha or _ expected after $")

        t = "VAR"
        if self.scope_is("GLOBAL") or self.is_global(match):
            t = "GLOBALVAR"
        var = self.pt.new(t, match, start=start, end=self.cursor)
        if self.match_for(re.compile(re.escape("->"))):
            var.append(self.parse_subvar())
        return var

    def parse_subvar(self):
        start = self.cursor
        match = self.match_for(ident_search)
        v = self.pt.new("SUBVAR", match, start, self.cursor)
        if self.match_for(re.compile(re.escape("->"))):
            self.cursor += 2
            v.append(self.parse_subvar())
        return v

    def parse_constant(self, name):
        self.pt.append("CONSTANT", name, start_offset=-len(name))
        self.pt.last.end_cursor = self.cursor

    def parse_string(self):
        delim = self.get()
        start_cursor = self.cursor
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
        self.pt.append_and_into("STRING", res, start_offset=-self.cursor + start_cursor)
        if len(format_vars) > 0:
            for v in format_vars:
                self.pt.append("VARIABLE", v)
        self.pt.up()
        self.next_non_white()

    def parse_comment_group(self):
        self.cursor += 2
        match, comment = self.search_until(re.compile("\\*\\/"))
        self.pt.append("COMMENTBLOCK", comment)
        self.next_non_white()

    def parse_comment_line(self):
        if self.check_for("#"):
            self.cursor += 1
        else:
            self.cursor += 2
        match, value = self.search_until(endline_search)
        self.pt.append("COMMENTLINE", value)
        self.next_non_white()

    def parse_symbol(self, symbol):
        symbol = symbol.lower()
        if symbol in COMPARATORS:
            self.parse_basic("COMPARATOR", symbol)
        elif symbol in OPERATORS:
            self.parse_operator(symbol)
        elif symbol in ASSIGNMENTS:
            self.parse_basic("ASSIGNMENT", symbol)
        elif symbol in CONSTANTS:
            self.parse_basic("CONSTANT", symbol)
        elif symbol in MAGIC_CONSTANTS:
            self.parse_basic("MAGIC", symbol)
        else:
            raise NotImplementedError("Implement" + symbol)
        self.next_non_white()

    def parse_block(self):
        self.start_marker = self.cursor
        self.next_non_white()
        if self.match_for(re.compile("\\{")) is None:
            raise ExpectedCharError("Expected { to start block")
        self.pt.append_and_into("BLOCK", start_offset=self.start_marker - self.cursor)
        self.next_non_white()
        self.start_marker = self.cursor
        while True:
            self.parse_statement()
            self.next_non_white()
            if self.check_for("}"):
                break
            self.start_marker = self.cursor
        self.pt.up(end_offset=1)

    def parse_control(self, keyword):

        self.next_non_white()
        self.pt.append_and_into(keyword.upper(), start_offset=self.start_marker - self.cursor)
        getattr(self, "parse_" + keyword.lower())()
        self.next_non_white()
        self.pt.up(end_offset=1)

    def parse_if(self):
        self.parse_expression_group()
        self.next_non_white()
        self.parse_block()

    def parse_while(self):
        self.parse_if()    # It looks the same!

    def parse_function(self):
        self.push_scope("LOCAL")
        match = self.match_for(ident_search)
        if match is None:
            raise ExpectedCharError("Alpha or _ expected as function name")
        self.pt.cur.value = match

        # Arglist is pretty much just an expression group
        self.parse_expression_group()
        self.pt.last.node_type = "ARGLIST"
        self.parse_block()
        self.pop_scope()

    def parse_return(self):
        self.parse_expression()

    def parse_new(self):
        if self.debug:
            print("NEW")
        self.next_non_white()
        match = self.match_for(callable_search)
        self.parse_callable(match)

    def parse_global(self):
        while True:
            self.next_non_white()
            if self.check_for(";"):
                break
            self.pt.cur.append(self.parse_variable())
            self.match_for(re.compile(",? *"))
        for var in self.pt.cur:
            self.add_global(var.value)

    def parse_special(self, keyword):
        # keyword might have a ( on the end, otherwise it has a space
        brace_end = False
        if keyword[-1] == "(":
            brace_end = True
        if keyword[-1] == ";":
            self.cursor -= 1
        keyword = keyword[:-1]
        self.next_non_white()
        self.pt.append_and_into(keyword.upper(), start_offset=-self.cursor + self.start_marker)
        if keyword in ("new"):
            getattr(self, "parse_" + keyword.lower())()
        else:
            self.parse_expression()
        if brace_end:
            # Skip over closing brace
            self.next_non_white()
            self.cursor += 1
        self.pt.up()
        self.next_non_white()

    def parse_basic(self, node_type, value):
        self.pt.append(node_type, value, start_offset=-self.cursor + self.start_marker)
        self.pt.last.end_cursor = self.cursor
        self.next_non_white()

    def parse_operator(self, o):
        if o in ("++", "--"):
            self.pt.append("ASSIGNMENT", o[0] + "=", start_offset=-2)
            self.pt.last.end_cursor = self.cursor
            self.pt.append("INT", 1, start_offset=-2)
        elif o == "=>":
            self.pt.cur.parent.node_type = "DICT"
            self.pt.append("KEYVALUE", start_offset=-2)
        elif o == ".":
            self.pt.append("OPERATOR", "+", start_offset=-1)
        else:
            self.pt.append("OPERATOR", o, start_offset=-len(o))
        self.pt.last.end_cursor = self.cursor
        self.next_non_white()

    def parse_callable(self, c):
        sm = self.start_marker
        # Matched the "(" too...
        if self.debug:
            print("CALLABLE")
        self.cursor -= 1
        self.next_non_white()
        call = self.parse_expression_group()
        call.node_type = "CALL"
        call.value = c[:-1]
        call.start_cursor = sm - self.cursor
        self.next_non_white()
