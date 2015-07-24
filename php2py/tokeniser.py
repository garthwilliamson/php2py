from __future__ import unicode_literals

import re
import logging


class Token(object):
    def __init__(self, line, column, value, kind=None):
        self.line = line
        self.col = column
        self.val = value
        self.kind = kind

    def __str__(self):
        return '{} ({}) on line {}, column {}'.format(repr(self.val), self.kind, self.line, self.col)

    def __repr__(self):
        return "Token(line={}, column={}, value=\"{!r}\", kind={})".format(self.line,
                                                                           self.col,
                                                                           repr(self.val),
                                                                           self.kind)


class Tokenizer(object):
    def __init__(self, linestream, tokens):
        self.linestream = linestream
        self.tokens = tokens

        # Set up the first line ready to go
        self.line = ""
        self.line_number = -1
        self.cursor = -1

        self.state = "html"
        self.peeked = None
        self.token_stream = self.token_gen()
        self.last_match = None
    # TODO: Work out how this is meant to be done

    def __iter__(self):
        return self

    def position(self):
        return self.line, " " * self.cursor + "^---- column {}, line {}".format(self.cursor, self.line_number)

    def next(self) -> Token:
        if self.peeked is not None:
            res = self.peeked
            self.peeked = None
            logging.debug("Produced1 {}".format(res))
            return res
        else:
            res = next(self.token_stream)
            logging.debug("Produced2 {}".format(res))
            return res

    def __next__(self):
        return self.next()

    def next_line(self):
        self.line = next(self.linestream)
        self.line_number += 1
        self.cursor = 0

    def match_for(self, match_re):
        m = match_re.match(self.line, self.cursor)
        if m is None:
            return None
        self.cursor = m.end()
        self.last_match = m.group()
        return m.group()

    def peek(self):
        if self.peeked is None:
            self.peeked = next(self.token_stream)
        return self.peeked

    def token_gen(self):
        while True:
            try:
                self.next_line()
            except StopIteration:
                break
            yield from self.tokenize_line()
        yield Token(self.line_number + 1, 0, "EOF", "PHPEND")

    def tokenize_line(self):
        state_map = {
            "html": self.tokenize_html,
            "php": self.tokenize_php,
            "blockcomment": self.tokenize_blockcomment,
        }
        while self.cursor < len(self.line):
            yield from state_map[self.state]()

    def tokenize_html(self) -> Token:
        """ Tokenizes the html state

        """
        next_state_at = self.line.lower().find("<?", self.cursor)
        if next_state_at >= 0:
            if next_state_at == self.cursor:
                # We don't need to insert a blank html element here - straight into the php state
                self.state = "php"
                php_start_t = Token(self.line_number,
                                    self.cursor,
                                    self.line[self.cursor:self.cursor + 5],
                                    "PHPSTART")
                self.cursor += 2
                if len(self.line) > self.cursor + 3:
                    if self.line[self.cursor:self.cursor + 3].lower() == "php":
                        self.cursor += 3
                yield php_start_t
                raise StopIteration()
        else:
            next_state_at = len(self.line)
        html_t = Token(self.line_number, self.cursor, self.line[self.cursor:next_state_at], "HTML")
        self.cursor = next_state_at
        yield html_t

    def tokenize_blockcomment(self):
        m = self.match_for(end_block_comment)
        if m is None:
            bc_t = Token(self.line_number, self.cursor, self.line[self.cursor:len(self.line)], "BLOCKCOMMENT")
            self.cursor = len(self.line)
            yield bc_t
        else:
            # TODO: m here is probably the last thing matched... Should run from old cursor to cur
            bc_t = Token(self.line_number, self.cursor, m, "BLOCKCOMMENT")
            self.state = "php"
            yield bc_t

    def tokenize_php(self):
        # yield up blank lines first of all. Then we can strip "\n" after checking for end php.
        if self.cursor == 0 and self.line.strip() == "":
            bl_t = Token(self.line_number, self.cursor, "\n", "BLANKLINE")
            self.cursor = len(self.line)
            yield bl_t
            raise StopIteration()
        while True:
            # Eliminate leading whitespace
            self.match_for(whitespace)
            if self.match_for(php_end):
                self.state = "html"
                yield Token(self.line_number, self.cursor, "?>", "PHPEND")
                raise StopIteration()
            m = self.match_for(full_block_comment)
            if m is not None:
                yield Token(self.line_number, self.cursor, m, "BLOCKCOMMENT")
                continue
            m = self.match_for(start_block_comment)
            if m is not None:
                # Remember, if it is just the start of a block comment then it goes past the end of the line
                self.state = "blockcomment"
                yield Token(self.line_number, self.cursor, m, "BLOCKCOMMENT")
                raise StopIteration()
            t = self.match_for(self.tokens)
            if t is None:
                if self.cursor == len(self.line):
                    raise StopIteration()
                raise NotImplementedError("How did we get here?")
            t = t.rstrip()
            kind = lookup_kind(t)
            yield Token(self.line_number, self.cursor, t, kind)


def lookup_kind(s):
    if s in COMPARATORS:
        return "COMPARATOR"
    elif s in OPERATORS:
        return "OPERATOR"
    elif s in ASSIGNMENTS:
        return "ASSIGNMENT"
    elif s == "[":
        return "INDEX"
    elif s in STARTBRACES:
        return "STARTBRACE"
    elif s in ENDBRACES:
        return "ENDBRACE"
    elif s.startswith("//") or s.startswith("#"):
        return "COMMENTLINE"
    elif s.startswith("$"):
        return "VARIABLE"
    elif s == ";":
        return "ENDSTATEMENT"
    elif s[0] in " \t\r\n":
        return "WHITESPACE"
    else:
        if s in keyword_table:
            return keyword_table[s]
        match = match_more(s)
        if match is None:
            return "UNKNOWN"
        else:
            return match


def match_more(s):
    for kind, reg in more_table.items():
        if reg.match(s) is not None:
            return kind


def escape_and_join(items):
    return "|".join([re.escape(i) for i in items])


def create_pattern(items):
    pattern = escape_and_join(items)
    return re.compile(pattern, flags=re.IGNORECASE)


def full_matcher(s):
    return re.compile("^{}$".format(s), flags=re.IGNORECASE)


keyword_table = {
    "try": "TRY",
    "case": "CASE",
    "default": "DEFAULT",
    "catch": "CATCH",
    "break": "BREAK",
    "throw": "THROW",
    "while": "CONTROL",
    "foreach": "CONTROL",
    "switch": "CONTROL",
    "return": "RETURN",
    "global": "GLOBAL",
    "extends": "EXTENDS",
    "array": "SPECIAL",
    "clone": "SPECIAL",
    "die": "SPECIAL",
    "echo": "SPECIAL",
    "empty": "SPECIAL",
    "eval": "SPECIAL",
    "exit": "SPECIAL",
    "isset": "SPECIAL",
    "list": "SPECIAL",
    "unset": "SPECIAL",
    "require_once": "SPECIAL",
    "require": "SPECIAL",
    "include_once": "SPECIAL",
    "include": "SPECIAL",
    "if": "IF",
    "class": "CLASS",
    "static": "METHODMOD",
    "public": "METHODMOD",
    "private": "METHODMOD",
    "else": "ELSE",
    "elseif": "ELSEIF",
    "function": "FUNCTION",
    ",": "COMMA",
    ":": "COLON",
    "__DIR__": "SPECIAL",
}


php_start = create_pattern(("<?php",))
php_end = create_pattern(("?>",))
whitespace = re.compile("\\s+")

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
    "(unset)": None,    # TODO: unset should be not so shit
}

CASTERS = [c for c in cast_map]
COMPARATORS = ["===", "!==", "==", "!=", "<>", "<=", ">=", "<", ">"]
OPERATORS = ["new ", "and ", "xor " "or ", "as ",
             "->{", "=>", "->", "::",        # TODO: is ->{ allowed whitespace?
             "<<", ">>", "||", "&&", "++", "--",
             "+", "-", "*", "/", "%", ".", "&", "|", "^", "~", "!", "?", "@"]
ASSIGNMENTS = ["<<=", ">>=",
               "+=", "-=", "*=", "/=", "|=", "^=", "="]
STARTBRACES = ["(", "{", "["]
ENDBRACES = [")", "}", "]"]
BRACES = STARTBRACES + ENDBRACES
EXTRA = [";", ",", ":"]
SYMBOLS = COMPARATORS + OPERATORS + ASSIGNMENTS + BRACES + EXTRA + CASTERS

SYMBOLS.sort(key=len, reverse=True)

DOUBLEQUOTE = re.escape('"')
SINGLEQUOTE = re.escape("'")
BACKEDDOUBLE = '\\"'
BACKEDSINGLE = "\\'"
DOUBLEQUOTED = DOUBLEQUOTE + "(.|[^" + BACKEDDOUBLE + "])+?" + DOUBLEQUOTE
SINGLEQUOTED = SINGLEQUOTE + "(.|[^" + BACKEDSINGLE + "])+?" + SINGLEQUOTE
EMPTYSTRING = "\"\"|''"
# STRINGS = EMPTYSTRING + "|" + DOUBLEQUOTED + "|" + SINGLEQUOTED
STRINGS = '"(?:[^"\\\\]|\\\\.)*"|' + "'(?:[^'\\\\]|\\\\.)*'"
NUMBERS = "-?[0-9]+\\.?[0-9]*"
STARTBLOCKCOMMENT = re.escape("/*")
ENDBLOCKCOMMENT = re.escape("*/")
start_block_comment = re.compile("{}(.|[^*/])*".format(STARTBLOCKCOMMENT, ENDBLOCKCOMMENT))
end_block_comment = re.compile(".*?{}".format(ENDBLOCKCOMMENT))
full_block_comment = re.compile(STARTBLOCKCOMMENT + ".*?" + ENDBLOCKCOMMENT)
COMMENTS = "\/\/.*"
VARIABLES = "\\$[a-z1-9_]+"
INDENTIFIERS = "[a-z_][a-z_1-9]*"
TOKENS = "{0}|{1}|{2}|{3}|{4}|{5}".format(COMMENTS, NUMBERS, escape_and_join(SYMBOLS), STRINGS, VARIABLES, INDENTIFIERS)

more_table = {
    "INT": full_matcher("-?[0-9]+"),
    "STRING": full_matcher(STRINGS),
    "IDENT": full_matcher(INDENTIFIERS),
}


def tokens(linestream):
    logging.debug("Tokenizing")
    return Tokenizer(linestream, re.compile(TOKENS, flags=re.IGNORECASE))


if __name__ == "__main__":
    import sys
    print("matching for " + TOKENS)
    f = open(sys.argv[1], "r")
    for token in tokens(f):
        print(token)
