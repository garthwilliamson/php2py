from __future__ import unicode_literals

class ParseNode(object):
    def __init__(self, node_type, parent=None, value=None):
        self.node_type = node_type
        self.parent = parent
        self.value = value
        self.children = []

    def append(self, node, value=None):
        if value is None:
            self.children.append(node)
        else:
            self.children.append(ParseNode(node, self, value))

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
        self.last = self.cur

    def up(self):
        #print("Going up from", self.cur, "to", self.cur.parent)
        if self.cur.parent is None:
            raise UpTooMuchException("Can't go up from here")
        self.cur = self.cur.parent

    def append(self, node_type, value=None):
        #print("Appending node", node_type, value, "to", self.cur)
        new_node = ParseNode(node_type, self.cur, value)
        self.cur.append(new_node)
        self.last = new_node
        return new_node

    def print_(self, node=None):
        if node is None:
            node = self.root_node
        def print_tree(tree, indent):
            print(indent * " " + str(tree))
            for c in tree:
                print_tree(c, indent + 4)
        print_tree(node, 0)


def print_tree(tree):
    p = ParseTree("temp")
    p.root_node = tree
    p.print_()