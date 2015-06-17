from __future__ import absolute_import, unicode_literals, print_function

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
    elif statement_node.node_type == "SWITCH":
        return transform_switch(statement_node)
    elif statement_node.node_type == "TRY":
        return transform_try(statement_node)
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
    "||": "or",
    "===": "==",     # TODO: Do we need to use a function here? I think the == case is the naughty one...
    "!==": "!=",
}


def transform_node(node):
    if node.node_type in transform_map:
        return transform_map[node.node_type](node)
    else:
        pdebug("UNKNOWN TRANSFORM", node)
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
    # Check if the second argument is now "False" - then we should use the "blah is false" pattern.
    # Same True and None. I think "is" should be treated as an operator in this regard.
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


def transform_try(try_statement):
    out = []
    for c in try_statement:
        out.append(transform_php(c))
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
    extras = []
    for c in contents:
        #print("??")
        #print_tree(c)
        #print("??")
        if c.node_type == "CASE":
            #print("FOUND CASE")
            out.append(transform_case(switch_var, c, i, extras))
            i += 1
            extras = []
        elif c.node_type == "DEFAULT":
            out.append(transform_default(c, i))
            i += 1
        elif c.node_type == "CASEFALLTHROUGH":
            ctf_node = transform_case(switch_var, c, i, extras)
            out.append(ctf_node)
            extras.append(ctf_node.get("EXPRESSION").get("COMPARATOR"))
            #raise TransformException("Implement new case type for " + c.node_type)
            i += 1
        elif c.node_type == "STATEMENT":
            # Probably a statement with a comment
            pass
    return out


def transform_case(switch_var, case_node, i, extras):
    if i > 0:
        if_statement = ParseNode("ELIF", "elif", token=case_node.token)
    else:
        if_statement = ParseNode("IF", "if", token=case_node.token)
    orig_ex = case_node.get("EXPRESSION")
    if_ex = ParseNode("EXPRESSION", None, token=orig_ex.token)
    comp = ParseNode("COMPARATOR", "==", token=case_node.token)
    comp.append(switch_var)
    comp.append(orig_ex[0])
    if len(extras) > 0:
        # Add the extras to a tree of or nodes like:
        # or(extras[0], or(extras[1], ... or(extras[-2], extras[-1])))
        or_node = ParseNode("OPERATOR2", "or")
        or_node.append(comp)
        for e in extras[:-1]:
            new_or_node = ParseNode("OPERATOR2", "or")
            new_or_node.append(e)
            or_node.append(new_or_node)
            or_node = new_or_node
        or_node.append(extras[-1])
        if_ex.append(or_node)
    else:
        if_ex.append(comp)
    if_statement.append(if_ex)
    if_statement.append(transform_php(case_node.get("BLOCK")))
    return if_statement


def transform_default(default_node, i):
    if i > 0:
        else_statement = ParseNode("ELSE", "else", token=default_node.token)
    else_statement.append(transform_php(default_node.get("BLOCK")))
    return else_statement


def transform_callspecial(cs_node: ParseNode):
    if cs_node.value == "array":
        return transform_array(cs_node)
    elif cs_node.value == "__dir__":
        # We don't need to transform_call if we are generating the argslist entirely ourselves
        cs_node.node_type = "CALL"
        cs_node.value = "dirname"
        add_argument(cs_node, ParseNode("IDENT", "__file__", token=cs_node.token))
        return cs_node
    else:
        return transform_call(cs_node)


def transform_call(call_node):
    new_args = ParseNode("ARGSLIST", None, token=call_node.get("ARGSLIST").token)
    for e in call_node.get("ARGSLIST"):
        new_args.append(transform_expression(e))
    call_node[0] = new_args
    return call_node


def transform_array(array_node):
    i = 0
    list_node = ParseNode("LIST", "[", token=array_node.token)
    for e in array_node.get("ARGSLIST"):
        c = e[0]
        tuple_node = ParseNode("TUPLE", "(", token=c.token)
        if c.value == "=>":
            tuple_node.append(transform_node(c[1]))
            tuple_node.append(transform_node(c[0]))
        else:
            tuple_node.append(ParseNode("INT", i, token=c.token))
            tuple_node.append(c)
            i += 1
        list_node.append(tuple_node)
    l_e = ParseNode("EXPRESSION", None)
    l_e.append(list_node)
    array_node.get("ARGSLIST").children = [l_e]
    return array_node


def add_argument(node: ParseNode, argument: ParseNode):
    """ Add an expression or another node as an argument to a call function

    Will wrap a non-expression argument up in an expression
    """
    if argument.node_type != "EXPRESSION":
        e = ParseNode("EXPRESSION", token=argument.token)
        e.append(argument)
        argument = e
    node.get("ARGSLIST").append(argument)


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
    "(unset)": None,    #TODO: unset should be not so shit. Use "del"
}


MAGIC_CONSTANTS = ["__line__", "__file__", "__dir__", "__function__", "__class__",
                   "__trait__", "__method__", "__namespace__"]


transform_map = {
    "OPERATOR1": transform_operator,
    "OPERATOR2": transform_operator,
    "BLOCK": transform_php,
    "ATTR": transform_attr,
    "EXPRESSION": transform_expression,
    "CALLSPECIAL": transform_callspecial,
}