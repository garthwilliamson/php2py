from __future__ import unicode_literals

import re

class Token(object):
    def __init__(self, line, column, value, kind=None):
        self.line = line
        self.col = column
        self.val = value
        self.kind = kind

    def __str__(self):
        return '{} ({}) at col {} of line {}'.format(repr(self.val), self.kind, self.col, self.line)

    def __repr__(self):
        return "Token(line={}, column={}, value=\"{!r}\", kind={})".format(self.line, self.col, repr(self.val), self.kind)


class Tokeniser(object):
    def __init__(self, linestream, tokens, keep_white=False):
        self.linestream = linestream
        self.tokens = tokens
        self.keep_white = keep_white
        self.line_number = 0
        self.next_line()
        self.state = "html"
        self.peeked = None

    def __iter__(self):
        return self

    def position(self):
        return self.line, " " * self.cursor + "^---- column {}, line {}".format(self.cursor, self.line_number)

    def next(self):
        if self.peeked is not None:
            res = self.peeked
            self.peeked = None
            return res
        if self.cursor >= len(self.line):
            try:
                self.next_line()
            except StopIteration:
                return Token(self.line_number + 1, 0, "EOF", "PHPEND")
            #return Token(self.line_number, self.cursor, "\n", "NEWLINE")
        if self.state == "html":
            php_start_index = self.line.lower().find("<?php", self.cursor)
            if php_start_index >= 0:
                # Found a <?php token in this line
                if php_start_index > self.cursor:
                    # Cursor is before the start of <?php, so return up til then and set the cursor to the start
                    html_t = Token(self.line_number, self.cursor, self.line[self.cursor:php_start_index], "HTML")
                    self.cursor = php_start_index
                    return html_t
                else:
                    self.state = "php"
                    # Cursor is at <?php
                    php_start_token = Token(self.line_number, self.cursor, self.line[self.cursor:self.cursor + 5], "PHPSTART")
                    self.cursor += 5
                    return php_start_token
            else:
                # No <?php in the line
                html_t = Token(self.line_number, self.cursor, self.line, "HTML")
                self.cursor = len(self.line)
                return html_t
        elif self.state == "blockcomment":
            m = self.match_for(end_block_comment)
            if m is None:
                l = self.line
                self.next_line()
                return Token(self.line_number, self.cursor, l, "BLOCKCOMMENT")
            else:
                self.state = "php"
                return Token(self.line_number, self.cursor, m, "BLOCKCOMMENT")
        else:
            # PHP State
            while self.match_for(whitespace) is not None or len(self.line) == 0:
                #print("\033[94m" + repr(self.line) + "\n" + " " * (self.cursor + 2) + "^----")
                if self.cursor >= len(self.line):
                    try:
                        self.next_line()
                    except StopIteration:
                        return Token(self.line_number + 1, 0, "EOF", "PHPEND")
            if self.match_for(php_end):
                self.state = "html"
                return Token(self.line_number, self.cursor, "?>", "PHPEND")
            m = self.match_for(full_block_comment)
            if m is not None:
                return Token(self.line_number, self.cursor, m, "BLOCKCOMMENT")
            m = self.match_for(start_block_comment)
            if m is not None:
                self.state = "blockcomment"
                return Token(self.line_number, self.cursor, m, "BLOCKCOMMENT")
            t = self.match_for(self.tokens)
            if t is None:
                return Token(self.line_number + 1, 0, "EOF", "PHPEND")
            t = t.rstrip()
            kind = lookup_kind(t)
            return Token(self.line_number, self.cursor, t, kind)

    def match_for(self, match_re):
        m = match_re.match(self.line, self.cursor)
        if m is None:
            return None
        self.cursor = m.end()
        self.last_match = m.group()
        return m.group()

    def peek(self):
        self.peeked = self.next()
        return self.peeked

    def next_line(self):
        self.line = next(self.linestream).rstrip("\n")
        self.line_number += 1
        self.cursor = 0


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
    "(unset)": None,    #TODO: unset should be not so shit
}

CASTERS = [c for c in cast_map]
COMPARATORS = ["===", "!==", "==", "!=", "<>", "<=", ">=", "<", ">"]
OPERATORS = ["new ", "and ", "xor " "or ", "as ",
             "=>", "->", "::",        # Here because I don't know where else to put it
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
#STRINGS = EMPTYSTRING + "|" + DOUBLEQUOTED + "|" + SINGLEQUOTED
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
TOKENS = COMMENTS + "|" + NUMBERS + "|" + escape_and_join(SYMBOLS) + "|" + STRINGS + "|"+ VARIABLES + "|" + INDENTIFIERS

more_table = {
    "INT": full_matcher("-?[0-9]+"),
    "STRING": full_matcher(STRINGS),
    "IDENT": full_matcher(INDENTIFIERS),
}


def tokens(linestream, keep_white=False):
    return Tokeniser(linestream, re.compile(TOKENS, flags=re.IGNORECASE), keep_white=keep_white)


if __name__ == "__main__":
    import sys
    print("matching for " + TOKENS)
    f = open(sys.argv[1], "r")
    for l, c, t, extra in tokens(f):
        print(l, c, repr(t), extra)
