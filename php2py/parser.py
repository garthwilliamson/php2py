from __future__ import unicode_literals
from __future__ import print_function

from .parsetree import ParseTree, ParseTreeError

import re
from functools import wraps


class ParseException(Exception):
    pass


class ParseError(ParseException):
    pass


class ExpectedCharError(ParseError):
    pass


class UnexpectedCharError(ParseError):
    def __init__(self, tree_so_far, *args):
        super(UnexpectedCharError, self).__init__(*args)
        self.known = tree_so_far


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
            print("Searching at", repr(self.get(10)), self.cursor, search_re.pattern)
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
            print("Matching at |{}| for {}".format(repr(self.get(10)), match_re.pattern))
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
OPERATORS = ["and", "xor",
             "=>",        # Here because I don't know where else to put it
             "<<", ">>", "||", "&&", "or", "++", "--",
             "+", "-", "*", "/", "%", ".", "&", "|", "^", "~", "!"]
ASSIGNMENTS = ["<<=", ">>=",
              "+=", "-=", "*=", "/=", "|=", "^=", "="]
MAGIC_CONSTANTS = ["__line__", "__file__", "__dir__", "__function__", "__class__",
                   "__trait__", "__method__", "__namespace__"]
CONSTANTS = ["true", "false"]
SYMBOLS = COMPARATORS + OPERATORS + ASSIGNMENTS + MAGIC_CONSTANTS
SYMBOLS.sort(key=len, reverse=True)
symbol_search = create_pattern(SYMBOLS)
whitespace_search = re.compile("\\s+")
CONTROLS = "function switch while class call for if do".split()
SPECIAL_STATEMENTS = ["echo", "new", "die", "require_once", "require", "include", "global", "return"]
special_search = create_pattern(SPECIAL_STATEMENTS)
control_search = re.compile("(" + "|".join([re.escape(w) for w in CONTROLS]) + ")([ \\(])")
int_search = re.compile("[0-9]+")
callable_search = re.compile(IDENTIFIERS + "\\s*\\(", flags=re.IGNORECASE)
endline_search = re.compile("(\\r)?\\n|$")
endstatement_search = create_pattern(("?>", ";", "}"))

else_search = re.compile("else( |\\{)")
elif_search = re.compile("else\\s+if")

open_brace_search = re.compile("\\(")
close_brace_search = re.compile(re.escape(")"))

comma_search = re.compile(re.escape(","))
space_tab_search = re.compile("[\t ]*")

open_curly_search = re.compile(re.escape("{"))
close_curly_search = re.compile(re.escape("}"))


class PhpParser(Parser):
    def parse(self):
        self.push_scope("GLOBAL")
        try:
            self.pt.cur.end_cursor = len(self.chars)
            self.parse_html()
            if self.pt.cur.node_type != "ROOT":
                self.pt.up()
        except UnexpectedCharError as e:
            print("Parse error on line {}:".format(self.line_number()))
            self.print_node_info(self.pt.root_node)
            print("Parsed so far")
            self.print_node_info(e.known)
            self.print_cur_location(str(e))
            raise
        except ParseException as e:
            print("Parse error on line {}:".format(self.line_number()))
            self.print_node_info(self.pt.root_node)
            self.print_cur_location(str(e))
            raise
        except ParseTreeError as e:
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
                print("*************************")
            self.next_non_white()
            if self.is_eof():
                break
            if self.check_for("//"):
                self.pt.cur.append(self.parse_comment_line())
            elif self.check_for("#"):
                self.pt.cur.append(self.parse_comment_line())
            elif self.match_for(re.compile(re.escape("?>"))) is not None or self.is_eof():
                break
            elif self.check_for("/*"):
                self.pt.cur.append(self.parse_comment_group())
            else:
                self.pt.cur.append(self.parse_statement())
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
        self.next_non_white()
        control = control_search.match(self.chars, self.cursor)
        if control is not None:
            self.cursor = control.end() - 1    # go back one in case we had a "("
            return self.parse_control(control.group(1))
        elif self.check_for("//") or self.check_for("#"):
            statement = self.pt.new("STATEMENT", start=self.cursor)
            statement.append(self.parse_comment_line())
            return statement
        else:
            statement = self.pt.new("STATEMENT", start=self.cursor)
            statement.append(self.parse_expression())
            self.next_non_white()
            if self.is_eof():
                return statement
            m = self.match_for(endstatement_search)
            if m is None:
                raise UnexpectedCharError(statement, "Didn't expect to see `{}` here".format(self.get()))
            # Statements can end with comments
            self.match_for(space_tab_search)
            if self.check_for("//"):
                print("Putting a comment line in the block")
                statement.append(self.parse_comment_line())
            elif self.check_for("/*"):
                statement.append(self.parse_comment_group())
            statement.end_cursor = self.cursor
            return statement

    def parse_expression(self):
        if self.debug:
            print("^^^^^^^^ Parsing expression at ", self.cursor)
        expr = self.pt.new("EXPRESSION", start=self.cursor)
        while True:
            self.next_non_white()
            if self.check_for(";") or self.check_for(")") or self.check_for(",") or self.check_for("?>") or self.check_for("]") or self.is_eof():
                break
            ep = self.parse_expression_part()
            if ep is False:
                raise UnexpectedCharError(expr, "`{}` in expression".format(self.get()))
            expr.append(ep)
        expr.end_cursor = self.cursor
        if self.debug:
            print("vvvvvvv Finished parsing expression")
        return expr

    def parse_expression_part(self):
        self.start_marker = self.cursor
        self.next_non_white()
        if self.debug:
            print("Looking for ")
        if self.check_for("("):
            return self.parse_expression_group()
        elif self.check_for("//"):
            return self.parse_comment_line()
        elif self.check_for("/*"):
            return self.parse_comment_group()
        elif self.check_for('"') or self.check_for("'"):
            return self.parse_string()
        elif self.check_for("$"):
            return self.parse_variable()
        elif self.check_for("["):
            return self.parse_index()
        elif self.match_for(symbol_search) is not None:
            return self.parse_symbol(self.last_match)
        elif self.match_for(int_search):
            return self.parse_basic("INT", int(self.last_match))
        elif self.match_for(callable_search):
            return self.parse_callable(self.last_match)
        elif self.match_for(ident_search):
            # I don't like doing this - will it always be a constant or a special statement? I don't think so!
            match = self.last_match
            if match.lower() in SPECIAL_STATEMENTS:
                return self.parse_special(match)
            elif match.lower() in CONSTANTS:
                return self.parse_basic("PHPCONSTANT", match.lower())
            else:
                return self.parse_basic("CONSTANT", match)
        else:
            return False

    def parse_expression_group(self):
        start = self.cursor
        self.next_non_white()
        m = self.match_for(open_brace_search)
        if m != "(":
            raise ExpectedCharError("Expected ( at start of item")
        self.next_non_white()
        m = self.match_for(close_brace_search)
        if m == ")":
            return self.pt.new("EXPRESSIONGROUP", start=start, end=self.cursor)

        eg = self.parse_comma_list("EXPRESSIONGROUP", start=start)
        if self.match_for(close_brace_search) is None:
            raise ExpectedCharError("Expected to see `)` after sub expression `{}`".format(eg))
        eg.end_cursor = self.cursor
        return eg

    def parse_comma_list(self, name, value=None, start=0):
        res = self.pt.new(name, value, start=start)
        while True:
            self.next_non_white()
            res.append(self.parse_expression())
            self.next_non_white()
            if self.match_for(comma_search) is None:
                return res

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
            var.append(self.parse_attr())
        start = self.cursor
        if self.match_for(create_pattern(("++", "--"))):
            if self.last_match == "++":
                var.append(self.pt.new("POSTINC", start=start, end=self.cursor))
            else:
                var.append(self.pt.new("POSTDEC", start=start, end=self.cursor))
        return var

    def parse_attr(self):
        start = self.cursor
        match = self.match_for(ident_search)
        v = self.pt.new("ATTR", match, start, self.cursor)
        if self.match_for(re.compile(re.escape("->"))):
            self.cursor += 2
            v.append(self.parse_attr())
        return v

    def parse_index(self):
        if self.get() != "[":
            raise ExpectedCharError("Expected [ at start of index")
        self.cursor += 1
        ex = self.parse_expression()
        ex.node_type = "INDEX"
        if self.get() != "]":
            raise ExpectedCharError("Expected ] at end of index")
        else:
            self.cursor += 1
        return ex

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
        st = self.pt.new("STRING", res, start=start_cursor, end=self.cursor)
        for v in format_vars:
            st.append(self.pt.new("VARIABLE", v))
        return st

    def parse_comment_group(self):
        start = self.cursor
        self.cursor += 2
        match, comment = self.search_until(re.compile("\\*\\/"))
        return self.pt.new("COMMENTBLOCK", comment, start=start, end=self.cursor)

    def parse_comment_line(self):
        start = self.cursor
        if self.check_for("#"):
            self.cursor += 1
        else:
            self.cursor += 2
        match, value = self.search_until(endline_search)
        return self.pt.new("COMMENTLINE", value, start=start, end=self.cursor)

    def parse_symbol(self, symbol):
        symbol = symbol.lower()
        if symbol in COMPARATORS:
            return self.parse_basic("COMPARATOR", symbol)
        elif symbol in OPERATORS:
            return self.parse_operator(symbol)
        elif symbol in ASSIGNMENTS:
            return self.parse_basic("ASSIGNMENT", symbol)
        elif symbol in MAGIC_CONSTANTS:
            return self.parse_basic("MAGIC", symbol)
        raise NotImplementedError("Implement" + symbol)

    def parse_block(self):
        start = self.cursor
        if self.match_for(open_curly_search) is None:
            raise ExpectedCharError("Expected { to start block")
        block = self.pt.new("BLOCK", start=start)
        self.next_non_white()
        self.start_marker = self.cursor
        while self.match_for(close_curly_search) is None:
            block.append(self.parse_statement())
            self.next_non_white()
        return block

    def parse_control(self, keyword):
        c = None
        if keyword.lower() in ("while",):
            c = self.parse_control_general(keyword)
        else:
            c = getattr(self, "parse_" + keyword.lower())()
        return c

    def parse_control_general(self, keyword):
        start = self.cursor - 2
        i = self.pt.new(keyword.upper(), start=start)
        i.append(self.parse_expression_group())
        self.next_non_white()
        i.append(self.parse_block())
        i.end_cursor = self.cursor
        return i

    def parse_if(self):
        i = self.parse_control_general("if")
        while True:
            self.next_non_white()
            if self.match_for(elif_search):
                i.append(self.parse_control_general("ELIF"))
            elif self.match_for(else_search):
                if self.last_match == "else{":
                    self.cursor -= 1
                else:
                    self.next_non_white()
                i.append(self.parse_block())
            else:
                return i

    def parse_function(self):
        start = self.cursor - 8
        self.push_scope("LOCAL")
        self.match_for(space_tab_search)
        match = self.match_for(ident_search)
        if match is None:
            raise ExpectedCharError("Alpha or _ expected as function name")
        f = self.pt.new("FUNCTION", match, start=start)
        # Arglist is pretty much just an expression group
        al = self.parse_expression_group()
        al.node_type = "ARGLIST"
        f.append(al)
        self.next_non_white()
        f.append(self.parse_block())
        self.pop_scope()
        return f

    def parse_return(self):
        return self.parse_expression()

    def parse_new(self):
        if self.debug:
            print("NEW")
        self.next_non_white()
        match = self.match_for(callable_search)
        return self.parse_callable(match)

    def parse_global(self):
        g = self.parse_comma_list("GLOBALLIST", start=self.cursor)
        for var in g:
            self.add_global(var.value)
        return g

    def parse_special(self, keyword):
        start = self.cursor
        special = self.pt.new("CALL", keyword.lower(), start=start)
        if keyword in ("new", "return", "global"):
            special.append(getattr(self, "parse_" + keyword.lower())())
            special.node_type = keyword.upper()
        else:
            self.next_non_white()
            args = None
            if self.check_for("("):
                args =self.parse_expression_group()
            else:
                args = self.parse_comma_list("ARGLIST")
            for a in args:
                special.append(a)
        special.end_cursor = self.cursor
        return special

    def parse_basic(self, node_type, value):
        return self.pt.new(node_type, value, start=self.start_marker, end=self.cursor)

    def parse_operator(self, o):
        start = self.cursor - len(o)
        if o == ".":
            o = "+"
        if o == "=>":
            return self.pt.new("KEYVALUE", start=start, end=self.cursor)
        else:
            return self.pt.new("OPERATOR", o, start=start, end=self.cursor)

    def parse_callable(self, c):
        sm = self.start_marker
        # Matched the "(" too...
        if self.debug:
            print("CALLABLE")
        self.cursor -= 1
        self.next_non_white()
        call = self.parse_expression_group()
        call.node_type = "CALL"
        call.trim_childless_children("EXPRESSION")
        call.value = c[:-1]
        call.start_cursor = sm - self.cursor
        self.next_non_white()
        return call
