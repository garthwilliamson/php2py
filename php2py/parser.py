from __future__ import unicode_literals

import logging

from .clib.parsetree import ParseTree, print_tree, ParseNode
from . import tokeniser


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


super_globals = [
    "GLOBALS",
    "_SERVER",
    "_GET",
    "_POST",
    "_FILES",
    "_COOKIE",
    "_SESSION",
    "_REQUEST",
    "_ENV",
]


class Parser(object):
    def __init__(self, contents, name):
        self.scope = []
        # TODO: This is probably not actually working - get globals working... or at least test them
        self.globals = []
        self.pt = ParseTree(name)
        self.chars = contents
        self.current = None
        self.debug_indent = 0
        self.tokens = None

    def to_list(self, ):
        return self.get_tree().to_list()

    def get_tree(self):
        return self.pt.root_node

    def push_scope(self, name):
        self.scope.append(name)
        self.globals.append([])

    def pop_scope(self):
        self.scope.pop()
        self.globals.pop()

    def is_global(self, variable):
        if variable in self.globals[-1] or variable in super_globals:
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
            logging.warning(
                "{} has no end cursor. Up mustn't have been called for it or one of its children".format(node))
            end = len(self.chars)
        # print("{:<30}{:<7}{}{!r}".format(str(node), str(start) + ":" + str(end), " " * (indent), self.chars[start:end]))

        if recurse:
            for c in node:
                self.print_node_info(c, recurse, start_indent)

    def pdebug(self, s, i_change=0):
        logging.debug(" " * self.debug_indent + str(s))
        self.debug_indent += i_change

    def next(self) -> tokeniser.Token:
        self.current = self.tokens.next()
        self.pdebug("^^^^^^^" + str(self.current))
        return self.current

    def peek(self) -> tokeniser.Token:
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
        return t


operator_map = {
#   OP:        (ARITY,    PREC, ASSOC)
#   "[":        (2,        120,  "left"),
    ".":        (2,        90,  "left"),
    "::":       (2,        160,  "right"),
    "->":       (2,        155,  "left"),
    "->{":      (1,        152,  "left"),
    "return":   (1,        150,  "none"),
    "new":      (1,        150,  "right"),
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
    "and":      (2,        30,   "left"),
    "xor":      (2,        29,   "left"),
    "or":       (2,        28,   "left"),
    "as":       (2,        20,   "right"),
    "EX":       (1,       -1000, "right")
}


indent_map = {
    "true": "True",
    "false": "False",
    "__FILE__": "__file__"
}


EOF = ["EOF"]
PHPEND = EOF + ["?>"]
ENDBLOCK = PHPEND + ["}"]
ENDSTATEMENT = [";"] + ENDBLOCK
ENDGROUP = ENDSTATEMENT + [")"]
ENDEXPRESSION = [",", "]", ":"] + ENDGROUP


def lookup_op_type(op_value):
    # print("LOOKING UP " + op_value)
    if op_value in tokeniser.ASSIGNMENTS:
        return "ASSIGNMENT"
    elif op_value == "[":
        return "INDEX"
    elif op_value == "->":
        return "ATTR"
    elif op_value == "->{":
        return "GETATTR"
    elif op_value == "::":
        return "STATICATTR"
    elif op_value in ("return", "new"):
        return op_value.upper()
    elif operator_map[op_value][0] == 1:
        return "OPERATOR1"
    elif operator_map[op_value][0] == 3:
        return "OPERATOR3"
    else:
        return "OPERATOR2"


PYTHON_KEYWORDS = ["continue"]


class PhpParser(Parser):
    def __init__(self, linestream):
        Parser.__init__(self, "", "Test")
        self.tokens = tokeniser.tokens(linestream)
        logging.log(logging.DEBUG - 1, tokeniser.TOKENS)
        self.debug_indent = 0
        self.push_scope("GLOBAL")
        self.comments = None
        try:
            self.parse()
        except ExpectedCharError:
            logging.critical("\n".join(self.tokens.position()))
            raise
        except:
            logging.critical("\n".join(self.tokens.position()))
            raise

    def next_non_white(self):
        while self.peek().kind in ("WHITESPACE", "NEWLINE"):
            self.next()

    def parse(self):
        # print("\n".join(self.tokens.position()))
        for _ in self.peek_until(("EOF",)):
            h = self.parse_html()
            if h is not None:
                self.pt.root_node.append(h)
            if self.peek().kind == "PHPSTART":
                self.pt.root_node.append(self.parse_php())

    def parse_html(self):
        contents = ""
        logging.debug("Parsing html")
        t = self.peek()
        for t in self.next_while_kind(("HTML",)):
            logging.debug("FOUND HTML")
            contents += t.val
        if len(contents) > 0:
            self.pdebug("FOUND HTML CONTENTS. APPENDING NOW")
            return self.pt.new("HTML", t, contents)
        else:
            return None

    def parse_php(self):
        self.pdebug("PHP:", 4)
        php_node = self.pt.new("PHP", self.assert_next("PHPSTART"))
        for _ in self.peek_until(PHPEND):
            self.next_non_white()
            php_node.append(self.parse_statement())

        self.next()
        self.debug_indent -= 4
        return php_node

    def parse_statement(self):
        self.pdebug("STATEMENT starting with {}:".format(self.peek()), 4)
        self.comments = []
        # TODO: Move to using attr to look up these
        if self.peek().kind == "CONTROL":
            statement = self.parse_control()
        elif self.peek().kind == "TRY":
            statement = self.parse_try()
        elif self.peek().kind == "IF":
            statement = self.parse_if()
        elif self.peek().kind == "FUNCTION":
            statement = self.parse_function()
        elif self.peek().kind == "CLASS":
            statement = self.parse_class()
        elif self.peek().kind == "BLANKLINE":
            statement = self.parse_blankline()
        elif self.peek().kind == "METHODMOD":
            static = False
            visibility = None
            while self.peek().kind == "METHODMOD":
                mm = self.next()
                if mm.val == "static":
                    static = True
                elif mm.val in ("public", "protected", "private"):
                    visibility = mm
            if self.peek().kind == "FUNCTION":
                statement = self.parse_method(static, visibility)
            elif self.peek().kind == "VARIABLE":
                # TODO: This should be limited, not a full expression
                statement = self.pt.new("STATEMENT", self.peek())
                en = self.parse_expression()
                statement.append(en)
                self.assert_next("ENDSTATEMENT", ";")
            else:
                raise ExpectedCharError("function", self.peek().val)
        elif self.peek().kind == "RETURN":
            statement = self.parse_simple_control("RETURN", "return")
        elif self.peek().kind == "THROW":
            statement = self.parse_simple_control("THROW", "throw")
        elif self.peek().kind == "GLOBAL":
            statement = self.parse_global()
        elif self.peek().kind == "CASE":
            statement = self.parse_case()
        elif self.peek().kind == "DEFAULT":
            statement = self.parse_default()
        else:
            statement = self.pt.new("STATEMENT", self.peek())
            if self.peek().kind in ("COMMENTLINE", "BLOCKCOMMENT"):
                while self.peek().kind in ("COMMENTLINE", "BLOCKCOMMENT"):
                    self.comments.append(self.parse_comment(self.next()))
            else:
                statement.append(self.parse_expression())
                cur_line = self.tokens.line_number
                if self.peek().val == ";":
                    self.next()
                if self.peek().kind == "COMMENTLINE" and self.tokens.line_number == cur_line:
                    self.comments.append(self.parse_comment(self.next()))
        # Now we've collected all the comments, append them to the statement
        for c in self.comments:
            statement.append(c)
        self.pdebug("STATEMENT END")
        self.debug_indent -= 4
        return statement

    def parse_block(self):
        self.pdebug("Staring new block", 4)
        block = self.pt.new("BLOCK", self.assert_next("STARTBRACE", "{"))
        for _ in self.peek_until(["}"]):
            if self.peek().kind == "PHPEND":
                self.next()
                block.append(self.parse_html())
                self.assert_next("PHPSTART")
                #block.append(self.pt.new("HTML", self.next()))
            block.append(self.parse_statement())

        self.pdebug("At end of block")
        # print_tree(block)
        self.pdebug("=-=-=-=-=-")
        self.assert_next("ENDBRACE", "}")
        self.debug_indent -= 4
        return block

    def parse_if(self):
        i = self.pt.new("IF", self.next())
        i.append(self.parse_expression_group(self.next()))
        # TODO: Factor this out to use in if, while, elif etc etc
        if self.peek().val == "{":
            i.append(self.parse_block())
        else:
            i.append(self.parse_statement())
        while self.peek().kind == "ELSEIF":
            e = self.pt.new("ELIF", self.next())
            e.append(self.parse_expression_group(self.next()))
            e.append(self.parse_block())
            i.append(e)
        if self.peek().kind == "ELSE":
            e = self.pt.new("ELSE", self.next())
            if self.peek().kind == "IF":
                e.append(self.parse_if())
            else:
                e.append(self.parse_block())
            i.append(e)
        return i

    def parse_case(self):
        case = self.pt.new("CASE", self.next())
        case.append(self.parse_expression())
        block = self.pt.new("BLOCK", self.assert_next("COLON", ":"))
        while self.peek().kind not in ("CASE", "BREAK", "DEFAULT", "ENDBRACE"):
            block.append(self.parse_statement())
        if self.peek().kind != "BREAK":
            # self.next()
            case.kind = "CASEFALLTHROUGH"
        else:
            self.assert_next("BREAK")
        case.append(block)
        return case

    def parse_default(self):
        default = self.pt.new("DEFAULT", self.next())
        block = self.pt.new("BLOCK", self.assert_next("COLON", ":"))
        while self.peek().kind not in ("BREAK", "ENDBRACE"):
            block.append(self.parse_statement())
        if self.peek().kind == "BREAK":
            # Skip the break, we are at the end anyway I hope
            self.next()
        default.append(block)
        return default

    def parse_control(self):
        control_token = self.next()
        keyword = control_token.val.upper()
        c = self.pt.new(keyword, control_token)
        c.append(self.parse_expression_group(self.next()))
        c.append(self.parse_block())
        return c

    def parse_try(self) -> ParseNode:
        try_node = self.pt.new("TRY", self.next())
        try_node.append(self.parse_block())
        for t in self.next_while(("catch",)):
            c = self.pt.new("CATCH", t)
            self.assert_next("STARTBRACE", "(")
            catchmatch = self.pt.new("EXCEPTION", self.next())
            c.append(catchmatch)

            if self.peek().kind == "VARIABLE":
                as_node = self.pt.new("AS", t)
                as_node.append(self.parse_variable(self.next()))
                c.append(as_node)
            self.assert_next("ENDBRACE", ")")
            c.append(self.parse_block())
            try_node.append(c)
        return try_node

    def parse_function(self):
        self.pdebug("Doing a function call", 4)
        self.push_scope("LOCAL")
        self.next()
        # Function names are case insensitive
        f = self.pt.new("FUNCTION", self.peek(), self.next().val.lower())
        f.append(self.parse_expression_group(self.next(), "ARGSLIST"))
        f.append(self.parse_block())
        self.pdebug("At end of function")
        # print_tree(f)
        self.pdebug("=-=-=-=-=-")
        self.debug_indent -= 4
        self.pop_scope()
        return f

    def parse_class(self):
        """ Chomp a class

        class ClassName extends ParentClassName { //contents }
        CLASS CLASS.val <    parse_extends    > <parse_block >

        """
        self.pdebug("Doing a class call", 4)
        self.push_scope("CLASS")
        self.next()
        c = self.pt.new("CLASS", self.next())
        if self.peek().val == "extends":
            c.append(self.parse_extends())
        c.append(self.parse_block())
        self.pop_scope()
        self.debug_indent -= 4
        return c

    def parse_extends(self):
        """ Chomp the extends keyword and value

        class ClassName extends ParentClassName {
                       >EXTENDS IDENT<

        """
        self.assert_next("EXTENDS")
        parent = self.assert_next("IDENT")
        return self.pt.new("EXTENDS", parent)

    def parse_method(self, static=False, visibility=None):
        # For now, methods are functions with visibility
        f = self.parse_function()
        if static:
            f.kind = "CLASSMETHOD"
        else:
            f.kind = "METHOD"
        if visibility is not None:
            f.append(self.pt.new("VISIBILITY", visibility))
        return f

    def parse_expression(self):
        ex = self.pt.new("EXPRESSION", self.peek(), "EX")
        self.pdebug("\033[94m########Starting new expression##########", 4)
        full_ex = []
        noo1a = True  # We expect that the next item is a non-operator or an arrity 1 operator
        for t in self.next_until(ENDEXPRESSION):
            self.pdebug("Current token is {}".format(t))
            if t.val in operator_map:
                op_node = self.parse_operator(t)
                if noo1a and op_node.arrity > 1:
                    if op_node.value == "&":
                        op_node.kind = "REFERENCE"
                        op_node.arrity = 1
                        op_node.assoc = "right"
                    else:
                        raise ParseError("Expected to see a 1-ary operator or a non-operator here")
                full_ex.append(op_node)
                self.pdebug("Appended an operator")
                if t.val == "?":
                    op_node.append((self.parse_expression()))
                    self.assert_next("COLON", ":")
                if t.val == "->{":
                    op_node.append(self.parse_expression())
                    self.assert_next("ENDBRACE", "}")
                noo1a = True
            elif t.kind in ("BLOCKCOMMENT", "COMMENTLINE"):
                # Get rid of block comments for the meantime - too hard to deal with
                self.comments.append(self.parse_comment(t))
            elif t.val == "(":
                # TODO: When lhs is an operator, this isn't a call...
                self.pdebug("About to deal with an expression group")
                eg = self.parse_expression_group("(")
                op_node = self.pt.new("CALL", t, "")
                op_node.append(eg)
                op_node.arrity = 1
                op_node.assoc = "left"
                op_node.precedence = 155
                full_ex.append(op_node)
                # print_tree(full_ex[-1])
                self.pdebug("Finished with expression group")
                noo1a = False
            elif t.kind == "IDENT":
                # Hopefully we haven't missed too many ident cases
                full_ex.append(self.parse_ident(t, bare=True))
                noo1a = False
            #elif t.kind == "STARTBRACE":
            #    # Assume we have a attr lookup
            #    full_ex.append(self.parse_startbrace())
            else:
                try:
                    self.pdebug("Going to try to run parse_" + t.kind.lower())
                    full_ex.append(getattr(self, "parse_" + t.kind.lower())(t))
                except AttributeError:
                    raise ParseError("function for parsing {} not yet implemented".format(t))
                self.pdebug("Appended notoperator")
                noo1a = False
        self.pdebug("Expresion nodes")
        self.pdebug([str(n) for n in full_ex])

        def shuffle_stacks(op_stack, opee_stack):
            o2 = op_stack.pop()
            # TODO: Spell arity correctly everywhere else
            pretend_arity = 1 if o2.arrity == 1 else 2
            args = [opee_stack.pop() for _ in range(0, pretend_arity)]
            [o2.children.append(a) for a in args]
            if o2.kind not in ("CALL", "GETATTR"):
                o2.kind = lookup_op_type(o2.value)
            opee_stack.append(o2)

        # Here follows the shunting algorithm(ish)
        op_stack = []
        opee_stack = []
        for n in full_ex:
            if n is None:
                continue
            if n.kind not in ("OPERATOR", "INDEX", "REFERENCE", "CALL", "GETATTR"):
                opee_stack.append(n)
            else:
                if len(op_stack) == 0:
                    op_stack.append(n)
                else:
                    while len(op_stack) > 0:
                        o2 = op_stack[-1]
                        if (n.assoc == "left" and n.precedence == o2.precedence) or n.precedence < o2.precedence:
                            shuffle_stacks(op_stack, opee_stack)
                        else:
                            break
                    op_stack.append(n)
        while len(op_stack) != 0:
            shuffle_stacks(op_stack, opee_stack)
        if len(opee_stack) > 1:
            self.pdebug("========opee_stack > 1========")
            [print_tree(n) for n in op_stack]
            self.pdebug("----ops-----")
            [print_tree(n) for n in opee_stack]
            self.pdebug("----opees-----")
            raise ParseError("Shit")
        elif len(opee_stack) == 1:
            ex.append(opee_stack[0])
        self.pdebug("Expression ended at")
        self.pdebug(self.tokens.position()[0])
        self.pdebug(self.tokens.position()[1])
        self.debug_indent -= 4
        return ex

    def parse_expression_group(self, start_token, kind="EXPRESSIONGROUP"):
        eg = self.parse_comma_list(kind)
        self.assert_next("ENDBRACE", ")")
        return eg

    def parse_comma_list(self, kind="COMMALIST"):
        self.pdebug("COMMA LIST", 4)
        cl = self.pt.new(kind, self.peek())
        self.pdebug(self.peek())
        for _ in self.peek_until(ENDGROUP):
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
        if v in PYTHON_KEYWORDS:
            v += "_"
        if self.scope_is("GLOBAL") or self.is_global(v):
            t = "GLOBALVAR"
        var = self.pt.new(t, var_token, v)
        return var

    def parse_string(self, string_token):
        self.pdebug("STRING:", 4)
        self.pdebug("String is {}".format(string_token))
        s = string_token.val[1:-1]
        self.pdebug("String contents are " + s)

        # TODO: Lots of work parsing strings
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
        string = self.pt.new("STRING", string_token, s)
        #string.children = format_vars
        self.debug_indent -= 4
        return string

    def parse_simple_control(self, name, value):
        r = self.pt.new(name, self.next(), value)
        r.append(self.parse_expression())
        if self.peek().val == ";":
            self.next()
        return r

    def parse_special(self, keyword_token):
        special = self.pt.new("CALLSPECIAL", keyword_token, keyword_token.val.lower())
        if self.peek().val == "(":
            args = self.parse_expression_group(self.next(), "ARGSLIST")
        else:
            args = self.parse_comma_list("ARGSLIST")
        special.append(args)
        # print("EXIT SPECIAL")
        return special

    def parse_global(self):
        g = self.pt.new("GLOBAL", self.next(), "global")
        args = self.parse_comma_list("GLOBALS")
        for v in args:
            g.append(v[0])
            self.globals[-1].append(v[0].value)
        if self.peek().val == ";":
            self.next()
        return g

    def parse_operator(self, op_token):
        arrity, prec, assoc = operator_map[op_token.val]
        op_node = self.pt.new("OPERATOR", op_token)
        op_node.arrity = arrity
        op_node.precedence = prec
        op_node.assoc = assoc
        return op_node

    def parse_int(self, int_token):
        if len(int_token.val) > 1 and int_token.val[0] == "0":
            # IGNORE: We are deliberately ignoring what php call octal weirdness
            return self.pt.new("OCT", int_token, int_token.val[1:])
        # TODO: Implement hex
        return self.pt.new("INT", int_token, int(int_token.val))

    def parse_newline(self, t=None):
        if t is not None:
            # If t isn't none, then this was called from within an expression
            return None
        t = self.next()
        return self.pt.new("NOOP", t, "\n")

    parse_blankline = parse_newline

    def parse_ident(self, ident, bare=False):
        """ Parse an identifier. bare indicates that this isn't part of a variable or anything.

        TODO: Refactor to work out if bare is actually needed.

        """
        if ident.val in indent_map:
            ident.val = indent_map[ident.val]
        elif bare:
            # Assume all bare idents which aren't message calls and are bare  are constants
            return self.pt.new("CONSTANT", ident)
        return self.pt.new("IDENT", ident)

    def parse_unknown(self):
        raise UnexpectedCharError(None)

    def parse_index(self, t):
        """
        Args:
            item: The item to index
        """
        i = self.pt.new("INDEX", t)
        i.append(self.parse_expression())
        i.precedence = 130
        i.arrity = 1
        i.assoc = "left"
        self.assert_next("ENDBRACE", "]")
        return i

    def parse_comment(self, comment_token):
        if comment_token.kind == "COMMENTLINE":
            return self.pt.new("COMMENTLINE", comment_token, value=comment_token.val[2:])
        else:
            return self.pt.new("COMMENTBLOCK", comment_token, value=comment_token.val.strip(" \t\r\n*/"))
