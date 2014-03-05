from __future__ import unicode_literals
from __future__ import print_function

from .parsetree import ParseNode, print_tree


class TransformException(Exception):
    pass


def transform(root_node):
    for n in root_node:
        if n.node_type == "PHP":
            transform_php(n)


def transform_php(php_node):
    out_statements = []
    for s in php_node:
        statements = transform_statement(s)
        for s_o in statements:
            out_statements.append(s_o)
    php_node.children = out_statements
    return php_node


def transform_statement(statement_node):
    if statement_node.node_type == "IF":
        return transform_if(statement_node)
    elif statement_node.node_type == "WHILE":
        return transform_while(statement_node)
    elif len(statement_node.children) == 0:
        return [statement_node]
    elif statement_node[0].node_type =="EXPRESSION":
        transform_expression(statement_node[0])
        return [statement_node]
    else:
        return [statement_node]


def transform_expression(expression_node):
    if expression_node[0].node_type == "OPERATOR":
        expression_node[0] = transform_operator(expression_node[0])
    return expression_node


def transform_operator(operator_node):
    if operator_node.value == "++":
        operator_node.value = "+="
        operator_node.children.insert(0, ParseNode("INT", 1))
    return operator_node


#def transform_node(node):
    #for c in node:
        #if c.node_type in ("VAR", "GLOBALVAR"):
            #i = 0
            #for var_child in c:
                #if var_child.node_type == "POSTINC":
                    #post_transform(c, "+", i)
                #elif var_child.node_type == "POSTDEC":
                    #post_transform(c, "-", i)
                #i += 1
        ##elif c.node_type == "EXPRESSION":
            ##if len(c.children) == 3 and c[1].node_type == "KEYVALUE":
                ##keyvalue_transform(c)
            ##else:
                ##transform_node(c)
        #elif c.node_type in ("IF", "WHILE"):
            #if_transform(c)
            #transform_node(c)
        #elif c.node_type == "COMPARATOR":
            ##TODO: == should probably be .equals or something similar
            #if c.value in ("===", "!=="):
                #c.value = c.value[0:2]
        #elif c.node_type == "BLOCK":
            #block_transform(c)
        #else:
            #transform_node(c)


#def post_transform(var_node, op, child_index):
    #var_value = var_node.value
    #if var_value is None:
        #raise TransformException("Variables can't be called None'")
    #var_type = var_node.node_type
    #del var_node[child_index]

    #new_expression = ParseNode("EXPRESSION", None)
    #new_expression.append(ParseNode(var_type, value=var_value))
    #new_expression.append(ParseNode("OPERATOR", op + "="))
    #new_expression.append(ParseNode("INT", 1))
    #parent = var_node.parent
    #if parent.node_type == "EXPRESSION":
        #statement = parent.parent
        #if statement.node_type == "STATEMENT":
            #statement.insert_after(parent, new_expression)
        #else:
            #print_tree(var_node.parent.parent)
            #raise TransformException("Unimplemented post or preinc")
    #else:
        #print_tree(var_node.parent.parent)
        #raise TransformException("Unimplemented post or preinc")


#def keyvalue_transform(expression):
    #if len(expression.children) != 3:
        #raise TransformException("A key value expression must have 3 children")
    #expression.node_type = "KEYVALUE"
    ## Delete original KEYVALUE node
    #del expression[1]


def transform_if(if_statement):
    out = []
    if_expression = if_statement[0][0]
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
    out = []
    return transform_php(while_statement[1])

#def block_transform(block_node):
    #empty = True
    #for c in block_node:
        #if len(c.children) > 0 and c[0].node_type not in ("COMMENTLINE", "COMMENTBLOCK"):
            #empty = False
        #transform_node(c)
    #if empty:
        #block_node.append(ParseNode("PASS", None))


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