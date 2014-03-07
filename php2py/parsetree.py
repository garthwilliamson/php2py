from __future__ import unicode_literals


class ParseTreeError(Exception):
    pass


next_id = 0
def get_next_id():
    global next_id
    next_id += 1
    return next_id - 1


class ParseNode(object):
    def __init__(self, node_type, value=None, parent=None, token=None):
        if not isinstance(node_type, basestring):
            raise ParseTreeError("node_type must be a string, not {}".format(node_type))
        self.node_type = node_type
        self.parent = parent
        self.value = value
        self.children = []
        self.id_ = get_next_id()
        self.token = token

    def append(self, node):
        if not isinstance(node, ParseNode):
            raise ParseTreeError("Expected a node, saw a {} as a child of {}".format(node, self))
        self.children.append(node)
        node.parent = self

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
            return self.node_type + ":" + repr(self.value) + ":" + str(self.id_)
        else:
            return self.node_type + ":" + str(self.id_)

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def get(self, node_type):
        for c in self.children:
            if c.node_type == node_type:
                return c
        raise IndexError("No node of type {} is a child of {}".format(node_type, self))

    def insert_after(self, search, new_node):
        i = self.children.index(search) + 1
        self.children.insert(i, new_node)

    def insert_before(self, search, new_node):
        i = self.children.index(search)
        print("inserting {} in {} before {}".format(new_node, self, self[i]))
        self.children.insert(i, new_node)

    def trim_childless_children(self, node_type):
        new_children = []
        for i in range(0, len(self.children)):
            if self.children[i].node_type == node_type and len(self.children[i].children) == 0:
                pass
            else:
                new_children.append(self.children[i])
        self.children = new_children


class ParseTree(object):
    def __init__(self, name):
        self.root_node = ParseNode("ROOT", value=name)
        self.cur = self.root_node
        self.last = self.cur

    def up(self):
        #print("Going up from", str(self.cur), "to", str(self.cur.parent))
        if self.cur.parent is None:
            raise Exception("Can't go up from here")
        self.cur = self.cur.parent

    def append(self, node_type, value=None):
        new_node = ParseNode(node_type, value, self.cur)
        #print("Appending node", str(new_node), value, "to", str(self.cur))
        self.cur.append(new_node)
        self.last = new_node
        return new_node

    def append_and_into(self, node_type, value=None):
        self.cur = self.append(node_type, value)
        return self.cur

    def print_(self, node=None):
        if node is None:
            node = self.root_node
        def print_tree(tree, indent):
            s = str(tree)
            if len(s) > 50:
                s = s[0:51]
            print(indent * " " + str(tree))
            for c in tree:
                if indent > 50:
                    print_tree(c, indent)
                else:
                    print_tree(c, indent + 4)
        print_tree(node, 0)

    def new(self, node_type=None, value=None, token=None):
        n = ParseNode(node_type, value=value, token=token)
        #print("New node: {}".format(n))
        return n


def print_tree(tree):
    p = ParseTree("temp")
    p.root_node = tree
    p.print_()