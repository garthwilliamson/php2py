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
        #elif c.node_type == "EXPRESSION":
            #if len(c.children) == 3 and c[1].node_type == "KEYVALUE":
                #keyvalue_transform(c)
            #else:
                #transform_node(c)
        elif c.node_type in ("IF", "WHILE"):
            if_transform(c)
            transform_node(c)
        elif c.node_type == "COMPARATOR":
            #TODO: == should probably be .equals or something similar
            if c.value in ("===", "!=="):
                c.value = c.value[0:2]
        elif c.node_type == "BLOCK":
            block_transform(c)
        else:
            transform_node(c)


def post_transform(var_node, op, child_index):
    var_value = var_node.value
    if var_value is None:
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

def if_transform(if_statement):
    if_expression = if_statement[0][0]
    i = 0
    #TODO: This probably only deals with the most basic cases
    for c in if_expression:
        if c.node_type == "ASSIGNMENT":
            print("FOUND ASSIGNMENT !!!")
            print(if_statement.node_type)
            print(if_statement.parent.node_type)
            assign_statement = ParseNode("STATEMENT", None)
            assign_statement.append(if_expression)
            if_statement.parent.insert_before(if_statement, assign_statement)
            var_node = if_expression[i - 1]
            ex = ParseNode("EXPRESSION", None)
            ex.append(var_node)
            if_statement[0][0] = ex
        i += 1

def block_transform(block_node):
    empty = True
    for c in block_node:
        if len(c.children) > 0 and c[0].node_type not in ("COMMENTLINE", "COMMENTBLOCK"):
            empty = False
        transform_node(c)
    if empty:
        block_node.append(ParseNode("PASS", None))