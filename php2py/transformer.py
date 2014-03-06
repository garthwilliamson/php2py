from __future__ import unicode_literals
from __future__ import print_function

from .parsetree import ParseNode, print_tree


DEBUG = True


def pdebug(*s):
    if DEBUG:
        print("|".join([str(p) for p in s]))


class TransformException(Exception):
    pass


def transform(root_node):
    for n in root_node:
        if n.node_type == "PHP":
            transform_php(n)


def transform_php(php_node):
    pdebug("T PHP", php_node)
    out_statements = []
    for s in php_node:
        statements = transform_statement(s)
        for s_o in statements:
            out_statements.append(s_o)
    php_node.children = out_statements
    return php_node


def transform_statement(statement_node):
    pdebug("T STATEMENT", statement_node)
    if statement_node.node_type == "IF":
        return transform_if(statement_node)
    elif statement_node.node_type == "WHILE":
        return transform_while(statement_node)
    elif statement_node.node_type == "FOREACH":
        return transform_foreach(statement_node)
    elif len(statement_node.children) == 0:
        return [statement_node]
    elif statement_node[0].node_type =="EXPRESSION":
        transform_expression(statement_node[0])
        return [statement_node]
    else:
        return [statement_node]


def transform_expression(expression_node):
    expression_node[0] = transform_node(expression_node[0])
    return expression_node


op_map = {
    "!": "not ",
    ".": "+"
}


def transform_node(node):
    if node.node_type.startswith("OPERATOR"):
        return transform_operator(node)
    else:
        return node


def transform_operator(operator_node):
    pdebug("T OPERATOR", operator_node)
    print_tree(operator_node)
    if operator_node.value == "++":
        operator_node.value = "+="
        operator_node.children.insert(0, ParseNode("INT", 1))
        operator_node.node_type = "OPERATOR2"
    elif operator_node.value in op_map:
        operator_node.value = op_map[operator_node.value]
    print_tree(operator_node)
    for i in range(len(operator_node)):
        operator_node[i] = transform_node(operator_node[i])
    print_tree(operator_node)
    return operator_node


def transform_if(if_statement):
    pdebug("T IF", if_statement)
    out = []
    if_expression = if_statement[0][0]
    if_expression = transform_expression(if_expression)
    #TODO: This probably only deals with the most basic cases
    if if_expression[0].node_type == "ASSIGNMENT":
        assign_statement = ParseNode("STATEMENT", None)
        assign_ex = ParseNode("EXPRESSION", None)
        assign_ex.append(if_expression[0])
        assign_statement.append(assign_ex)
        out.append(assign_statement)
        var_node = if_expression[0][1]
        if_expression[0] = var_node
    out.append(if_statement)
    return out


def transform_while(while_statement):
    pdebug("T WHILE", while_statement)
    out = []
    return transform_php(while_statement[1])


def transform_foreach(foreach_statement):
    as_ = foreach_statement.get("EXPRESSIONGROUP").get("EXPRESSION").get("OPERATOR2")
    var = as_[0]
    in_ = as_[1]
    for_node = ParseNode("PYFOR", "for")
    for_node.append(var)
    for_node.append(in_)
    for_node.append(transform_php(foreach_statement[1]))
    return [for_node]


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


MAGIC_CONSTANTS = ["__line__", "__file__", "__dir__", "__function__", "__class__",
                   "__trait__", "__method__", "__namespace__"]