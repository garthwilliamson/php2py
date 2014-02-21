from __future__ import unicode_literals
from __future__ import print_function

from .parsetree import ParseNode, print_tree


class TransformException(Exception):
    pass


def transform(tree):
    transform_node(tree)


def transform_node(node):
    for c in node:
        if c.node_type in ("VAR", "GLOBALVAR"):
            i = 0
            for var_child in c:
                if var_child.node_type == "POSTINC":
                    post_transform(c, "+", i)
                elif var_child.node_type == "POSTDEC":
                    post_transform(c, "-", i)
                i += 1
        elif c.node_type == "EXPRESSION":
            if len(c.children) == 3 and c[1].node_type == "KEYVALUE":
                keyvalue_transform(c)
            else:
                transform_node(c)
        else:
            transform_node(c)


def post_transform(var_node, op, child_index):
    var_value = var_node.value
    if var_value is None:
        print_tree(var_node)
        raise TransformException("Variables can't be called None'")
    var_type = var_node.node_type
    del var_node[child_index]

    new_expression = ParseNode("EXPRESSION", None)
    new_expression.append(ParseNode(var_type, value=var_value))
    new_expression.append(ParseNode("OPERATOR", op + "="))
    new_expression.append(ParseNode("INT", 1))
    parent = var_node.parent
    if parent.node_type == "EXPRESSION":
        statement = parent.parent
        if statement.node_type == "STATEMENT":
            statement.insert_after(parent, new_expression)
        else:
            print_tree(var_node.parent.parent)
            raise TransformException("Unimplemented post or preinc")
    else:
        print_tree(var_node.parent.parent)
        raise TransformException("Unimplemented post or preinc")


def keyvalue_transform(expression):
    if len(expression.children) != 3:
        raise TransformException("A key value expression must have 3 children")
    expression.node_type = "KEYVALUE"
    # Delete original KEYVALUE node
    del expression[1]