from __future__ import unicode_literals
from __future__ import print_function

from .parsetree import ParseNode, print_tree


DEBUG = False


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
    elif statement_node.node_type == "SWITCH":
        return transform_switch(statement_node)
    elif len(statement_node.children) == 0:
        return [statement_node]
    elif statement_node[0].node_type =="EXPRESSION":
        transform_expression(statement_node[0])
        return [statement_node]
    else:
        pdebug("UNKNOWN STATEMENT", statement_node)
        return [statement_node]


def transform_expression(expression_node):
    if len(expression_node) == 0:
        return ParseNode("NOOP", "")
    expression_node[0] = transform_node(expression_node[0])
    return expression_node


op_map = {
    "!": "not ",
    ".": "+",
    "&&": "and",
    "===": "==",     # TODO: Do we need to use a function here?
}


def transform_node(node):
    if node.node_type in transform_map:
        return transform_map[node.node_type](node)
    else:
        print("UNKNOWN TRANSFORM", node)
        for i in range(len(node)):
            node[i] = transform_node(node[i])
        return node


def transform_operator(operator_node):
    pdebug("T OPERATOR", operator_node)
    if operator_node.value == "++":
        operator_node.value = "+="
        operator_node.children.insert(0, ParseNode("INT", 1))
        operator_node.node_type = "OPERATOR2"
    elif operator_node.value in op_map:
        operator_node.value = op_map[operator_node.value]
    for i in range(len(operator_node)):
        operator_node[i] = transform_node(operator_node[i])
    return operator_node


def transform_attr(attr_node):
    if attr_node[0].node_type == "CALL":
        call_node = attr_node[0]
        object_node = attr_node[1]
        call_node.node_type = "METHODCALL"
        call_node.append(object_node)
        return call_node
    return attr_node

def transform_if(if_statement):
    pdebug("T IF", if_statement)
    out = []
    if_op = if_statement.get("EXPRESSIONGROUP").get("EXPRESSION")[0]
    if_op = transform_node(if_op)
    if_block = transform_node(if_statement.get("BLOCK"))
    #TODO: This probably only deals with the most basic cases
    if if_op.node_type == "ASSIGNMENT":
        assign_statement = ParseNode("STATEMENT", None, token=if_op.token)
        assign_ex = ParseNode("EXPRESSION", None, token=if_op.token)
        assign_ex.append(if_op)
        assign_statement.append(assign_ex)
        out.append(assign_statement)
        if_op = if_op[1]
    if_ex = ParseNode("EXPRESSION", None)
    if_ex.append(if_op)
    if_statement.children = [if_ex, if_block]
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
    for_node = ParseNode("PYFOR", "for", token=foreach_statement.token)
    for_node.append(var)
    for_node.append(in_)
    for_node.append(transform_php(foreach_statement[1]))
    return [for_node]


def transform_switch(switch_statement):
    out = []
    # Rearrange to have _switch_choice = <expression> so expression is only run once
    decide_ex = switch_statement.get("EXPRESSIONGROUP").get("EXPRESSION")

    assign = ParseNode("ASSIGNMENT", "=")
    switch_var = ParseNode("VAR", "_switch_choice")
    assign.append(decide_ex[0])
    assign.append(switch_var)

    assign_ex = ParseNode("EXPRESSION", None)
    assign_ex.append(assign)

    assign_statement = ParseNode("STATEMENT", None)
    assign_statement.append(assign_ex)
    out.append(assign_statement)

    # The contents of the switch will be rearranged into a whole series of elif
    contents = switch_statement.get("BLOCK")
    # We are going to ignore "STATEMENT" nodes directly in block for now - these are comments
    i = 0
    for c in contents:
        #print("??")
        #print_tree(c)
        #print("??")
        if c.node_type == "CASE":
            #print("FOUND CASE")
            out.append(transform_case(switch_var, c, i))
            i += 1
        elif c.node_type == "DEFAULT":
            out.append(transform_default(c, i))
            i += 1
        elif c.node_type.startswith("CASE"):
            raise TransformException("Implement new case type for " + c.node_type)
            i += 1
        elif c.node_type == "STATEMENT":
            # Probably a statement with a comment
            pass
    print_tree(out[1])
    return out


def transform_case(switch_var, case_node, i):
    if i > 0:
        if_statement = ParseNode("ELIF", "elif", token=case_node.token)
    else:
        if_statement = ParseNode("IF", "if", token=case_node.token)
    orig_ex = case_node.get("EXPRESSION")
    if_ex = ParseNode("EXPRESSION", None, token=orig_ex.token)
    comp = ParseNode("COMPARATOR", "==", token=case_node.token)
    comp.append(switch_var)
    comp.append(orig_ex[0])
    if_ex.append(comp)
    if_statement.append(if_ex)
    if_statement.append(transform_php(case_node.get("BLOCK")))
    return if_statement


def transform_default(default_node, i):
    if i > 0:
        else_statement = ParseNode("ELSE", "else", token=default_node.token)
    else_statement.append(transform_php(default_node.get("BLOCK")))
    return else_statement


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


transform_map = {
    "OPERATOR1": transform_operator,
    "OPERATOR2": transform_operator,
    "BLOCK": transform_php,
    "ATTR": transform_attr,
    "EXPRESSION": transform_expression,
}