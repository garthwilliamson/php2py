from __future__ import absolute_import, unicode_literals
from builtins import str


class ParseTreeError(Exception):
    pass


class NoMatchesError(ParseTreeError):
    pass


next_id = 0
def get_next_id():
    global next_id
    next_id += 1
    return next_id - 1


class MatchableNode(object):
    """ Mixin to provide matching functionality to nodes

    """
    def __iter__(self):
        raise NotImplementedError("MatchableNodeClasses must implement __iter__")

    def match(self, match_str: str):
        """ Takes a forwardslash delimited string and returns the node matching

        Examples:
            match("PHP*") - returns all children of this node of kind "PHP"
            match("PHP/FUNCTION*/BLOCK") - Tries to return all blocks of functions which are children
                                          of the first PHP child of this node
            match("FUNCTION|body/BLOCK") - Tries to return the BLOCK of the function which is a child
                                           of this node and is called "body"

        Returns:
            Either a single ParseNode object if no * is specified or a list if * is.
        """
        next_match = None
        this_match = match_str
        try:
            this_match, next_match = match_str.split("/", 1)
        except ValueError:
            pass
        child_name = None
        single = this_match[-1] != "*"
        if not single:
            this_match = this_match[:-1]
        try:
            this_match, child_name = this_match.split("|")
        except ValueError:
            pass
        # print("Matching {},{} {} times.".format(this_match, child_name, "one" if single else "many"))
        matches = []
        for c in self.get_all(this_match, child_name):
            child_matched = c
            if next_match is not None:
                # Look deeper
                try:
                    child_matched = c.match(next_match)
                except NoMatchesError:
                    child_matched = None
            if child_matched is not None:
                if single:
                    return child_matched
                else:
                    matches.append(child_matched)
        if len(matches) == 0:
            raise NoMatchesError()
        return matches

    def get_all(self, kind: str, node_name: str = None):
        for c in self:
            if node_name is None:
                if c.kind == kind:
                    yield c
            else:
                if c.kind == kind and str(c.value) == node_name:
                    yield c

    def get(self, kind):
        """ Returns the first instance of a node kind which is a child of this node
        """
        for c in self:
            if c.kind == kind:
                return c
        raise KeyError("No node of type {} is a child of {}".format(kind, self))

    def __getitem__(self, item):
        """ Returns the first item of a node kind which is a child of this node
        """
        return self.get(item)


class ParseNode(MatchableNode):
    def __init__(self, kind, token, value=None, parent=None):
        if not isinstance(kind, str):
            raise ParseTreeError("kind must be a string, not {}".format(kind))
        self.kind = kind
        self.parent = parent
        self.value = value
        self.children = []
        self.id_ = get_next_id()
        self.token = token

    def append(self, node):
        # if not isinstance(node, ParseNode):
        #     raise ParseTreeError("Expected a node, saw a {} as a child of {}".format(type(node), self))
        self.children.append(node)
        node.parent = self
        return node

    def to_list(self):
        if len(self.children) > 0:
            return self.kind, self.value, [c.to_list() for c in self.children]
        else:
            return self.kind, self.value

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.children[key]
        return self.get(key)

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.children[key] = value
            return
        i = 0
        while i < len(self.children):
            if self.children[i].kind == key:
                self.children[i] = value
                return
        self.append(value)

    def __delitem__(self, key):
        del(self.children[key])

    def __str__(self):
        if self.value is not None:
            return self.kind + ":" + repr(self.value) + ":" + str(self.id_)
        else:
            return self.kind + ":" + str(self.id_)

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def __contains__(self, item):
        try:
            self.get(item)
            return True
        except KeyError:
            return False

    def insert_after(self, search, new_node):
        i = self.children.index(search) + 1
        self.children.insert(i, new_node)

    def insert_before(self, search, new_node):
        i = self.children.index(search)
        print("inserting {} in {} before {}".format(new_node, self, self[i]))
        self.children.insert(i, new_node)

    def trim_childless_children(self, kind):
        new_children = []
        for i in range(0, len(self.children)):
            if self.children[i].kind == kind and len(self.children[i].children) == 0:
                pass
            else:
                new_children.append(self.children[i])
        self.children = new_children


class ParseTree(object):
    def __init__(self, name):
        self.root_node = ParseNode("ROOT", None, value=name)

    def print_(self, node=None):
        if node is None:
            node = self.root_node

        def print_tree(tree, indent):
            s = str(tree)
            if len(s) > 50:
                s = s[0:51]
            print(indent * " " + s)
            for c in tree:
                if indent > 50:
                    print_tree(c, indent)
                else:
                    print_tree(c, indent + 4)
        print_tree(node, 0)

    def new(self, kind: str, token, value=None) -> ParseNode:
        """ Create a new ParseNode

        If value is None, then we get the value from the token

        """
        if value is None:
            value = token.val
        n = ParseNode(kind, token, value=value)
        # print("New node: {}".format(n))
        return n


def print_tree(tree):
    p = ParseTree("temp")
    p.root_node = tree
    p.print_()
