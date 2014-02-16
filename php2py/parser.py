from __future__ import unicode_literals
from .parsetree import ParseTree

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


class Parser(object):
    def __init__(self, contents, name, debug=False):
        self.scope = []
        self.globals = []
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
CONTROLS = "function global return switch while class for if do".split()
SPECIAL_STATEMENTS = ["echo"]
special_search = re.compile("(" + "|".join([re.escape(w) for w in SPECIAL_STATEMENTS]) + ")([ \\(])")
control_search = re.compile("(" + "|".join([re.escape(w) for w in CONTROLS]) + ")([ \\(])")
int_search = re.compile("[0-9]+")
callable_search = re.compile(IDENTIFIERS + "\\(", flags=re.IGNORECASE)


class PhpParser(Parser):
    def parse(self):
        self.push_scope("GLOBAL")
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
        if self.scope_is("GLOBAL") or self.is_global(match):
            self.pt.append("GLOBALVAR", match)
        else:
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
        if keyword in ("if", "while"):
            if not self.check_for("("):
                raise ExpectedCharError("Expected ( at start of if statement")
            self.cursor += 1
            self.parse_statement(expr=True)
            self.cursor += 1
            self.next_non_white()
            self.parse_block()
        elif keyword == "function":
            self.push_scope("LOCAL")
            match = self.match_for(ident_search)
            if match is None:
                raise ExpectedCharError("Alpha or _ expected as function name")
            self.pt.cur.value = match
            self.parse_arg_list()
            self.parse_block()
            self.pop_scope()
        elif keyword == "return":
            self.next_non_white()
            self.parse_statement(expr=True)
        elif keyword == "global":
            while True:
                self.next_non_white()
                if self.check_for(";"):
                    break
                self.parse_variable()
                self.match_for(re.compile(",? *"))
            for var in self.pt.cur:
                self.add_global(var.value)
            self.cursor += 1
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
