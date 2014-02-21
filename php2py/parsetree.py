from __future__ import unicode_literals


class ParseTreeError(Exception):
    pass


next_id = 0
def get_next_id():
    global next_id
    next_id += 1
    return next_id - 1


class ParseNode(object):
    def __init__(self, node_type, value=None, parent=None):
        self.node_type = node_type
        self.parent = parent
        self.value = value
        self.children = []
        self.id_ = get_next_id()

    def append(self, node, value=None):
        if not isinstance(node, ParseNode):
            raise ParseTreeError("Expected a node, saw a {} as a child of {}".format(node, self))
        if value is None:
            self.children.append(node)
            node.parent = self
        else:
            self.children.append(ParseNode(node, value, self))

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

    def insert_after(self, search, new_node):
        i = self.children.index(search) + 1
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
    def __init__(self, name, get_cursor=None):
        self.get_cursor = get_cursor

        self.root_node = ParseNode("ROOT", value=name)
        self.root_node.start_cursor = 0
        self.cur = self.root_node
        self.last = self.cur

    def up(self, end_offset=0):
        #print("Going up from", str(self.cur), "to", str(self.cur.parent))
        if self.cur.parent is None:
            raise Exception("Can't go up from here")
        # The end of the item should be around where the cursor currently is
        self.cur.end_cursor = self.get_cursor() + end_offset
        self.cur = self.cur.parent

    def append(self, node_type, value=None, start_offset=0):
        new_node = ParseNode(node_type, value, self.cur)
        # The start of the item should be where the cursor currently is
        new_node.start_cursor = self.get_cursor() + start_offset
        #print("Appending node", str(new_node), value, "to", str(self.cur))
        self.cur.append(new_node)
        self.last = new_node
        return new_node

    def append_and_into(self, node_type, value=None, start_offset=0):
        self.cur = self.append(node_type, value, start_offset)
        return self.cur

    def print_(self, node=None):
        if node is None:
            node = self.root_node
        def print_tree(tree, indent):
            print(indent * " " + str(tree))
            for c in tree:
                print_tree(c, indent + 4)
        print_tree(node, 0)

    def new(self, node_type=None, value=None, start=0, end=0):
        n = ParseNode(node_type, value=value)
        n.start_cursor = start
        n.end_cursor = end
        return n


def print_tree(tree):
    p = ParseTree("temp")
    p.root_node = tree
    p.print_()