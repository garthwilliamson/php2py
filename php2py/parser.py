from __future__ import unicode_literals
from __future__ import print_function

from .parsetree import ParseTree, ParseTreeError, print_tree
from . import tokeniser

import re
from functools import wraps


class ParseException(Exception):
    pass


class ParseError(ParseException):
    pass


class ExpectedCharError(ParseError):
    def __init__(self, expected, saw, *args):
        super(ExpectedCharError, self).__init__(*args)
        self.expected = expected
        self.saw = saw

    def __str__(self):
        return "Excepted a {}, instead saw {}".format(self.expected, self.saw)


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
        self.pt = ParseTree(name)
        self.chars = contents
        self.debug = debug

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

    def print_node_info(self, node, recurse=True, start_indent=None):
        if start_indent is None:
            start_indent = node.start_cursor
        start = node.start_cursor
        indent = len(repr(self.chars[start_indent:start]))

        try:
            end = node.end_cursor
            if end - start > 30:
                end = start + 30
        except AttributeError:
            print("{} has no end cursor. Up mustn't have been called for it or one of its children".format(node))
            end = len(self.chars)
        #print("{:<30}{:<7}{}{!r}".format(str(node), str(start) + ":" + str(end), " " * (indent), self.chars[start:end]))

        if recurse:
            for c in node:
                self.print_node_info(c, recurse, start_indent)

    def pdebug(self, s, i_change=0):
        if self.debug:
            print(" " * self.debug_indent + str(s))
        self.debug_indent += i_change

    def next(self):
        self.current = self.tokens.next()
        self.pdebug("^^^^^^^" + str(self.current))
        return self.current

    def peek(self):
        return self.tokens.peek()

    def next_while_kind(self, match):
        while True:
            if self.peek().kind in match:
                yield self.next()
            else:
                raise StopIteration

    def next_while(self, match):
        for t in self.peek_while(match):
            self.next()
            yield t

    def next_until(self, match):
        for t in self.peek_until(match):
            self.next()
            yield t

    def peek_until(self, match):
        while True:
            if self.peek().val in match:
                raise StopIteration
            else:
                yield self.peek()

    def peek_while(self, match):
        while True:
            if self.peek().val in match:
                yield self.peek()
            else:
                raise StopIteration

    def assert_next(self, kind, value=None):
        t = self.next()
        if t.kind != kind:
            raise ExpectedCharError(kind + ":" + value, self.current)
        if value is not None and t.val != value:
            raise ExpectedCharError(kind + ":" + value, self.current)


def create_pattern(items):
    pattern = "|".join([re.escape(i) for i in items])
    return re.compile(pattern, flags=re.IGNORECASE)


cast_map = {
    "(int)": "int",
    "(integer)": "int",
    "(bool)": "bool",
    "(boolean)": "bool",
    "(float)": "float",
    "(double)": "float",
    "(real)": "float",
    "(string)": "str",
    "(array)": "list",
    "(object)": "object",
    "(unset)": None,    #TODO: unset should be not so shit
}


# REMEMBER BIGGEST TO SMALLEST
PHP_START = ("<?php",)
html_search = create_pattern(PHP_START)
IDENTIFIERS = "[a-z_][a-z_1-9:]*"
ident_search = re.compile(IDENTIFIERS, flags=re.IGNORECASE)
# Have to do these all at once because of sizing issues
COMPARATORS = ["===", "!==", "==", "!=", "<>", "<=", ">=", "<", ">"]
OPERATORS = ["and", "xor",
             "=>",        # Here because I don't know where else to put it
             "<<", ">>", "||", "&&", "or", "++", "--",
             "+", "-", "*", "/", "%", ".", "&", "|", "^", "~", "!", "?", ":"]
ASSIGNMENTS = ["<<=", ">>=",
              "+=", "-=", "*=", "/=", "|=", "^=", "="]
MAGIC_CONSTANTS = ["__line__", "__file__", "__dir__", "__function__", "__class__",
                   "__trait__", "__method__", "__namespace__"]
CONSTANTS = ["true", "false"]
SYMBOLS = COMPARATORS + OPERATORS + ASSIGNMENTS + MAGIC_CONSTANTS
SYMBOLS.sort(key=len, reverse=True)
symbol_search = create_pattern(SYMBOLS)
whitespace_search = re.compile("\\s+")
CONTROLS = "function return switch while catch class call try for if do".split()
SPECIAL_STATEMENTS = "echo new die require_once require include global return case".split()
cast_search = create_pattern(cast_map.keys())
special_search = create_pattern(SPECIAL_STATEMENTS)
control_search = re.compile("(" + "|".join([re.escape(w) for w in CONTROLS]) + ")([ \\(])")
int_search = re.compile("[0-9]+")
callable_search = re.compile("\\@?\\$?" + IDENTIFIERS + "\\s*\\(", flags=re.IGNORECASE)
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

operator_map = {
    #OP:        (ARITY,    PREC, ASSOC)
#   "[":        (2,        120,  "left"),
    ".":        (2,        170,  "left"),
    "::":       (2,        160,  "right"),
    "return":   (1,        150,  "none"),
    "new":      (0,        150,  "right"),
    "++":       (1,        110,  "right"),
    "--":       (1,        110,  "right"),
    "~":        (1,        110,  "right"),
    "(int)":    (1,        110,  "right"),
    "(float)":  (1,        110,  "right"),
    "(string)": (1,        110,  "right"),
    "(array)":  (1,        110,  "right"),
    "(object)": (1,        110,  "right"),
    "(bool)":   (1,        110,  "right"),
    "@":        (1,        110,  "right"),
    "!":        (1,        105,  "right"),
    "*":        (2,        100,  "left"),
    "/":        (2,        100,  "left"),
    "%":        (2,        100,  "left"),
    "+":        (2,        90,   "left"),
    "-":        (2,        90,   "left"),
    "<<":       (2,        80,   "left"),
    ">>":       (2,        80,   "left"),
    "<":        (2,        70,   "none"),
    "<=":       (2,        70,   "none"),
    ">":        (2,        70,   "none"),
    ">=":       (2,        70,   "none"),
    "==":       (2,        60,   "none"),
    "!=":       (2,        60,   "none"),
    "===":      (2,        60,   "none"),
    "!==":      (2,        60,   "none"),
    "<>":       (2,        60,   "none"),
    "&":        (2,        55,   "left"),
    "^":        (2,        54,   "left"),
    "|":        (2,        53,   "left"),
    "&&":       (2,        52,   "left"),
    "||":       (2,        51,   "left"),
    "?":        (3,        50,   "left"),
    "=":        (2,        40,   "right"),
    "+=":       (2,        40,   "right"),
    "-=":       (2,        40,   "right"),
    "*=":       (2,        40,   "right"),
    "/=":       (2,        40,   "right"),
    ".=":       (2,        40,   "right"),
    "%=":       (2,        40,   "right"),
    "&=":       (2,        40,   "right"),
    "|=":       (2,        40,   "right"),
    "^=":       (2,        40,   "right"),
    "<<=":      (2,        40,   "right"),
    ">>=":      (2,        40,   "right"),
    "=>":       (2,        40,   "right"),
    "->":       (2,        155,   "left"),
    "EX":       (1,       -1000, "right")
}


EOF = ["EOF"]
PHPEND = EOF + ["?>"]
ENDBLOCK = PHPEND + ["}"]
ENDSTATEMENT = [";"] + ENDBLOCK
ENDGROUP = ENDSTATEMENT + [")"]
ENDEXPRESSION = [",", "]"] + ENDGROUP


def lookup_op_type(op_value):
    #print("LOOKING UP " + op_value)
    if op_value in ASSIGNMENTS:
        return "ASSIGNMENT"
    elif op_value == "[":
        return "INDEX"
    elif op_value == "->":
        return "ATTR"
    elif op_value in ("return", "new"):
        return op_value.upper()
    else:
        return "OPERATOR"


class PhpParser(Parser):
    def __init__(self, linestream, debug=False):
        Parser.__init__(self, "", "Test", debug)

        self.tokens = tokeniser.tokens(linestream)
        #print(tokeniser.TOKENS)
        self.debug_indent = 0
        self.push_scope("GLOBAL")

        try:
            self.parse()
        except ExpectedCharError as e:
            self.print_cur_location(str(e))
            raise

    def next_non_white(self):
        while self.peek().kind in ("WHITESPACE", "NEWLINE"):
            self.next()

    def parse(self):
        #print("\n".join(self.tokens.position()))
        for t in self.peek_until(("EOF",)):
            self.parse_html()
            if self.peek().kind == "PHPSTART":
                self.parse_php()

    def parse_html(self):
        contents = ""
        #print("Parsing html")
        for t in self.next_while_kind(("HTML",)):
            #print("FOUND HTML")
            contents += t.val
        if len(contents) > 0:
            self.pdebug("FOUND HTML CONTENTS")
            self.pt.append("HTML", contents)
        else:
            pass

    def parse_blockcomment(self):
        contents = ""
        for t in self.next_while_kind(("BLOCKCOMMENT",)):
            contents += t.val
        return self.pt.new("BLOCKCOMMENT", contents)

    def parse_php(self):
        self.pdebug("PHP:", 4)
        self.assert_next("PHPSTART")
        php_node = self.pt.new("PHP", None)
        for t in self.peek_until(PHPEND):
            self.next_non_white()
            php_node.append(self.parse_statement())

        self.pt.cur.append(php_node)
        self.next()
        self.debug_indent -= 4

    def parse_statement(self):
        self.pdebug("STATEMENT starting with {}:".format(self.peek()), 4)
        self.comments = []
        #TODO: Move to using attr to look up these
        if self.peek().kind == "CONTROL":
            statement = self.parse_control()
        elif self.peek().kind == "TRY":
            statement = self.parse_try()
        elif self.peek().kind == "FUNCTION":
            statement = self.parse_function()
        elif self.peek().kind == "RETURN":
            statement = self.parse_return()
        else:
            statement = self.pt.new("STATEMENT", None)
            if self.peek().kind == "COMMENTLINE":
                self.comments.append(self.parse_comment(self.next()))
            else:
                statement.append(self.parse_expression())
                if self.peek().val == ";":
                    self.next()
        statement.comments = self.comments
        self.debug_indent -= 4
        return statement

    def parse_block(self):
        self.pdebug("Staring new block", 4)
        self.assert_next("STARTBRACE", "{")
        block = self.pt.new("BLOCK", None)
        for t in self.peek_until(ENDBLOCK):
            block.append(self.parse_statement())

        self.pdebug("At end of block")
        #print_tree(block)
        self.pdebug("=-=-=-=-=-")
        self.assert_next("ENDBRACE", "}")
        self.debug_indent -= 4
        return block

    def parse_control(self):
        control_token = self.next()
        keyword = control_token.val.upper()
        c = self.pt.new(keyword, None)
        c.append(self.parse_expression_group(self.next()))
        c.append(self.parse_block())
        return c

    def parse_try(self):
        self.next()
        try_node = self.pt.new("TRY", None)
        try_node.append(self.parse_block())
        for t in self.next_while(("catch",)):
            c = self.pt.new("CATCH", None)
            self.assert_next("STARTBRACE", "(")
            catchmatch = self.pt.new("EXCEPTION", self.next().val)
            catchmatch.append(self.parse_variable(self.next()))
            c.append(catchmatch)
            self.assert_next("ENDBRACE", ")")
            c.append(self.parse_block())
            try_node.append(c)
        return try_node

    def parse_function(self):
        self.pdebug("Doing a function call", 4)
        self.push_scope("LOCAL")
        self.next()
        f = self.pt.new("FUNCTION", self.next().val)
        f.append(self.parse_expression_group(self.next(), "ARGSLIST"))
        f.append(self.parse_block())
        self.pdebug("At end of function")
        #print_tree(f)
        self.pdebug("=-=-=-=-=-")
        self.debug_indent -= 4
        self.pop_scope()
        return f

    def parse_expression(self):
        ex = self.pt.new("EXPRESSION", "EX")
        self.pdebug("\033[94m########Starting new expression##########", 4)
        full_ex = []
        for t in self.next_until(ENDEXPRESSION):
            self.pdebug("Current token is {}".format(t))
            if t.val in operator_map:
                full_ex.append(self.parse_operator(t))
                self.pdebug("Appended an operator")
            elif t.kind in ("BLOCKCOMMENT", "COMMENTLINE"):
                # Get rid of block comments for the meantime - too hard to deal with
                self.comments.append(self.parse_comment(t))
            elif t.val == "(":
                self.pdebug("About to deal with an expression group")
                full_ex.append(self.parse_expression_group("("))
                #print_tree(full_ex[-1])
                self.pdebug("Finished with expression group")
            else:
                self.pdebug("Appended notoperator")
                try:
                    self.pdebug("Going to try to run parse_" + t.kind.lower())
                    full_ex.append(getattr(self, "parse_" + t.kind.lower())(t))
                except AttributeError:
                    raise ParseError("function for parsing {} not yet implemented".format(t))
        self.pdebug("Expresion nodes")
        self.pdebug([str(n) for n in full_ex])
        op_stack = []
        opee_stack = []
        for n in full_ex:
            if n is None:
                continue
            if n.node_type not in ("OPERATOR", "INDEX"):
                opee_stack.append(n)
            else:
                if len(op_stack) == 0:
                    op_stack.append(n)
                else:
                    while len(op_stack) > 0:
                        o2 = op_stack[-1]
                        if (n.assoc == "left" and n.precedence == o2.precedence) or n.precedence < o2.precedence:
                            #print("{} <=? {} so outing {}".format(n, o2, o2))
                            o2 = op_stack.pop()
                            args = [opee_stack.pop() for i in range(0, o2.arrity)]
                            [o2.children.append(a) for a in args]
                            o2.node_type = lookup_op_type(o2.value)
                            opee_stack.append(o2)
                        else:
                            break
                    op_stack.append(n)
            #self.pdebug("====ops====")
            #[print_tree(n) for n in op_stack]
            #self.pdebug("----opees-----")
            #[print_tree(n) for n in opee_stack]
            #self.pdebug("---------")
        while len(op_stack) != 0:
            o2 = op_stack.pop()
            args = [opee_stack.pop() for i in range(0, o2.arrity)]
            [o2.children.append(a) for a in args]
            o2.node_type = lookup_op_type(o2.value)
            opee_stack.append(o2)
        if len(opee_stack) > 1:
            self.pdebug("========opee_stack > 1========")
            [print_tree(n) for n in op_stack]
            self.pdebug("----ops-----")
            [print_tree(n) for n in opee_stack]
            self.pdebug("----opees-----")
            raise ParseError("Shit")
        ex.append(opee_stack[0])
        self.pdebug("Expression ended at")
        self.pdebug(self.tokens.position()[0])
        self.pdebug(self.tokens.position()[1])
        self.debug_indent -= 4
        return ex

    def parse_expression_group(self, start_token, node_type="EXPRESSIONGROUP"):
        eg = self.parse_comma_list(node_type)
        self.assert_next("ENDBRACE", ")")
        return eg

    def parse_comma_list(self, node_type="COMMALIST"):
        self.pdebug("COMMA LIST", 4)
        cl = self.pt.new(node_type)
        self.pdebug(self.peek())
        for t in self.peek_until(ENDGROUP):
            cl.append(self.parse_expression())
            if self.peek().kind == "COMMA":
                self.next()
            else:
                break
        self.pdebug("Reached end of comma list at")
        self.pdebug(repr(self.peek().val))
        self.pdebug(self.tokens.position()[0])
        self.pdebug(self.tokens.position()[1])
        self.debug_indent -= 4
        return cl

    def parse_variable(self, var_token):
        t = "VAR"
        v = var_token.val[1:]
        if self.scope_is("GLOBAL") or self.is_global(v):
            t = "GLOBALVAR"
        var = self.pt.new(t, v)
        return var

    def parse_string(self, string_token):
        self.pdebug("STRING:", 4)
        self.pdebug("String is {}".format(string_token))
        s = string_token.val[1:-1]
        self.pdebug("String contents are " + s)

        #st = tokeniser.tokens(iter([s]), keep_white=True)
        #out = ""
        #format_vars = []
        #while True:
            #print("tokens")
            #try:
                #t = st.next()
                #self.pdebug("{} found in string".format(t))
            #except StopIteration:
                #break
            #if t.kind == "ESCAPE":
                #out.append(t.next().val)
            #if t.kind != "VARIABLE":
                #out.append(t.val)
            #else:
                #out.append("{}")
                #format_vars.append(self.pt.new("VARIABLE", t.val))
        string = self.pt.new("STRING", s)
        #string.children = format_vars
        self.debug_indent -= 4
        return string

    def parse_return(self):
        r = self.pt.new("RETURN", "return")
        r.append(self.parse_expression())
        if self.peek().val == ";":
            self.next()
        return r

    def parse_special(self, keyword_token):
        special = self.pt.new("CALL", keyword_token.val.lower())
        if self.peek().val == "(":
            args = self.parse_expression_group(self.next(), "ARGSLIST")
        else:
            args = self.parse_comma_list("ARGLIST")
        special.append(args)
        #print("EXIT SPECIAL")
        return special

    #def parse_assignment(self):
        #ass_token = self.next()
        #return self.pt.new("ASSIGNMENT", ass_token.val)

    #def parse_comparator(self):
        #comp_token = self.next()
        #return self.pt.new("COMPARATOR", comp_token.val)

    def parse_operator(self, op_token):
        #if op_token.val == "[":
            #return self.parse_index(op_token)
        arrity, prec, assoc = operator_map[op_token.val]
        op_node = self.pt.new("OPERATOR", op_token.val)
        op_node.arrity = arrity
        op_node.precedence = prec
        op_node.assoc = assoc
        if op_token.val == "new":
            op_node.append(self.parse_ident(self.next()))
        return op_node

    def parse_int(self, int_token):
        return self.pt.new("INT", int(int_token.val))

    def parse_newline(self):
        self.next()
        return self.pt.new("NEWLINE", "\n")

    def parse_ident(self, ident):
        if self.peek().val == "(":
            # Function call
            self.pdebug("Function call", 4)
            call = self.pt.new("CALL", ident.val)
            call.append(self.parse_expression_group(self.next(), "ARGSLIST"))
            self.debug_indent -= 4
            return call
        else:
            return self.pt.new("IDENT", ident.val)

    def parse_unknown(self):
        raise UnexpectedCharError()

    def parse_index(self, t):
        """
        Args:
            item: The item to index
        """
        i = self.pt.new("INDEX", t.val)
        i.append(self.parse_expression())
        i.precedence = 130
        i.arrity = 1
        i.assoc = "left"
        self.assert_next("ENDBRACE", "]")
        return i

    def parse_comment(self, comment_token):
        #TODO: change to chop off first chars
        if comment_token.kind == "COMMENTLINE":
            return self.pt.new("COMMENTLINE", value=comment_token.val[2:])
        else:
            return self.pt.new("COMMENTBLOCK", value=comment_token.val)
