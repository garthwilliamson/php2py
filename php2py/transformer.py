from __future__ import absolute_import, unicode_literals

import logging

from .parsetree import ParseNode


transform_map = {}


def transforms(*args):
    def wrap(f):
        for node_type in args:
            transform_map[node_type] = f
        return f
    return wrap


def pdebug(*s):
    logging.debug("|".join([str(p) for p in s]))


class TransformException(Exception):
    pass


def transform(root_node: ParseNode):
    functions = []
    classes = []
    body_function = ParseNode("FUNCTION", None, "body")
    body_function.append(ParseNode("ARGSLIST", None))
    block = ParseNode("BLOCK", None)
    body_function.append(block)

    for tln in root_node:
        pdebug("Transforming top level node {}".format(tln))
        if tln.node_type == "PHP":
            pdebug("T PHP")
            for php_child in tln:
                for n in transform_node(php_child):
                    if n.node_type == "FUNCTION":
                        functions.append(n)
                    elif n.node_type == "CLASS":
                        classes.append(n)
                    else:
                        block.append(n)
        else:
            pdebug("T HTML")
            # TODO: Change to a call to "echo" here
            block.append(tln)

    # TODO: Maybe change this so that the body function is generated in transform2 stage. This would let you possibly
    # use jinja2 instead if you wanted.
    functions.append(body_function)
    out = []
    out += functions
    out += classes
    root_node.children = out


def transform_node(node):
    if node.node_type in transform_map:
        yield from transform_map[node.node_type](node)
    else:
        pdebug("UNKNOWN TRANSFORM", node)
        transform_children(node)
        yield node


def transform_single_node(node):
    return next(transform_node(node))


def transform_children(node):
    new_children = []
    for c in node:
        for n in transform_node(c):
            new_children.append(n)
    node.children = new_children


def transform_block(block_node):
    pdebug("T BLOCK", block_node)
    transform_children(block_node)
    return block_node


def transform_statement(statement_node: ParseNode):
    pdebug("T STATEMENT", statement_node)
    if statement_node.node_type in transform_map:
        yield from transform_map[statement_node.node_type](statement_node)
    elif statement_node[0].node_type == "EXPRESSION":
        transform_expression(statement_node[0])
        yield statement_node
    else:
        pdebug("UNKNOWN STATEMENT", statement_node)
        yield statement_node


@transforms("EXPRESSION")
def transform_expression(expression_node):
    if len(expression_node) == 0:
        yield ParseNode("NOOP", expression_node.token, "")
    transform_children(expression_node)
    yield expression_node


op_map = {
    "!": "not ",
    ".": "+",
    "&&": "and",
    "||": "or",
    "===": "==",     # TODO: Do we need to use a function here? I think the == case is the naughty one...
    "!==": "!=",
}


@transforms("OPERATOR1", "OPERATOR2")
def transform_operator(operator_node):
    pdebug("T OPERATOR", operator_node)
    if operator_node.value == "++":
        operator_node.value = "+="
        operator_node.children.insert(0, ParseNode("INT", operator_node.token, 1))
        operator_node.node_type = "OPERATOR2"
    elif operator_node.value in op_map:
        operator_node.value = op_map[operator_node.value]
    transform_children(operator_node)
    # Check if the second argument is now "False" - then we should use the "blah is false" pattern.
    # Same True and None. I think "is" should be treated as an operator in this regard.
    yield operator_node


@transforms("ATTR")
def transform_attr(attr_node):
    if attr_node[0].node_type == "CALL":
        call_node = attr_node[0]
        object_node = attr_node[1]
        call_node.node_type = "METHODCALL"
        call_node.append(object_node)
        yield call_node
        return
    yield attr_node


@transforms("CALL")
def transform_call(call_node):
    call_node[0].node_type = "ARGSLIST"
    transform_children(call_node[0])
    lhs = call_node[1]
    transform_children(lhs)
    if lhs.node_type == "CONSTANT":
        lhs.node_type = "IDENT"
        # TODO: Cheating!
        lhs.value = "_f_." + lhs.value
    yield call_node


@transforms("IF")
def transform_if(if_statement):
    pdebug("T IF", if_statement)
    transform_children(if_statement["BLOCK"])

    if_op = if_statement.get("EXPRESSIONGROUP").get("EXPRESSION")[0]
    if_op = transform_single_node(if_op)
    # TODO: This probably only deals with the most basic cases. Need to go down tree and extract all assignments.
    if if_op.node_type == "ASSIGNMENT":
        assign_statement = ParseNode("STATEMENT", if_op.token)
        assign_ex = ParseNode("EXPRESSION", if_op.token)
        assign_ex.append(if_op)
        assign_statement.append(assign_ex)
        yield assign_statement
        if_op = if_op[1]
    if_ex = ParseNode("EXPRESSION", if_op.token)
    if_ex.append(if_op)
    if_statement.children = [if_ex, if_statement["BLOCK"]]
    yield if_statement


@transforms("TRY")
def transform_try(try_statement):
    transform_children(try_statement)
    yield try_statement


@transforms("WHILE")
def transform_while(while_statement):
    pdebug("T WHILE", while_statement)
    transform_children(while_statement[1])
    yield while_statement


@transforms("FOREACH")
def transform_foreach(foreach_statement: ParseNode):
    pdebug("T FOREACH")
    """ Transform key=>value loop into

    for k, v in dict.items():
        body

    Transform plain foreach into
    PYFOR:
        VAR: A
        EXPR: B
        BLOCK: C

    to be compiled as
    for A in B:
        C

    """
    as_ = foreach_statement.match("EXPRESSIONGROUP/EXPRESSION/OPERATOR2")
    var = as_[0]
    in_ = as_[1]

    expr = ParseNode("EXPRESSION", as_.token)
    if var.value == "=>":
        items = ParseNode("CALL", var.token, "items")
        items.append(ParseNode("ARGSLIST", var.token))
        method_call = ParseNode("OPERATOR2", in_.token, ".")
        method_call.append(in_)
        method_call.append(items)
        expr.append(method_call)
        var.node_type = "ARGSLIST"
    else:
        expr.append(in_)
    for_node = ParseNode("PYFOR", foreach_statement.token, value="for")
    for_node.append(var)
    for_node.append(expr)
    for_node.append(transform_block(foreach_statement[1]))
    yield for_node


@transforms("SWITCH")
def transform_switch(switch_statement):
    # Rearrange to have _switch_choice = <expression> so expression is only run once
    decide_ex = switch_statement.get("EXPRESSIONGROUP").get("EXPRESSION")

    assign = ParseNode("ASSIGNMENT", decide_ex.token, "=")
    switch_var = ParseNode("VAR", decide_ex.token, "_switch_choice")
    assign.append(decide_ex[0])
    assign.append(switch_var)

    assign_ex = ParseNode("EXPRESSION", decide_ex.token, None)
    assign_ex.append(assign)

    assign_statement = ParseNode("STATEMENT", decide_ex.token, None)
    assign_statement.append(assign_ex)
    yield assign_statement

    # The contents of the switch will be rearranged into a whole series of elif
    contents = switch_statement.get("BLOCK")
    # We are going to ignore "STATEMENT" nodes directly in block for now - these are comments
    i = 0
    extras = []
    for c in contents:
        if c.node_type == "CASE":
            yield transform_case(switch_var, c, i, extras)
            i += 1
            extras = []
        elif c.node_type == "DEFAULT":
            yield transform_default(c, i)
            i += 1
        elif c.node_type == "CASEFALLTHROUGH":
            ctf_node = transform_case(switch_var, c, i, extras)
            yield ctf_node
            extras.append(ctf_node.get("EXPRESSION").get("COMPARATOR"))
            # raise TransformException("Implement new case type for " + c.node_type)
            i += 1
        elif c.node_type == "STATEMENT":
            # Probably a statement with a comment
            # TODO: check for non comment
            pass


def transform_case(switch_var, case_node, i, extras):
    if i > 0:
        if_statement = ParseNode("ELIF", case_node.token, value="elif")
    else:
        if_statement = ParseNode("IF", case_node.token, value="if")
    orig_ex = case_node.get("EXPRESSION")
    if_ex = ParseNode("EXPRESSION", orig_ex.token)
    comp = ParseNode("COMPARATOR", case_node.token, value="==")
    comp.append(switch_var)
    comp.append(orig_ex[0])
    if len(extras) > 0:
        # Add the extras to a tree of or nodes like:
        # or(extras[0], or(extras[1], ... or(extras[-2], extras[-1])))
        or_node = ParseNode("OPERATOR2", comp.token, "or")
        or_node.append(comp)
        for e in extras[:-1]:
            new_or_node = ParseNode("OPERATOR2", e.token, "or")
            new_or_node.append(e)
            or_node.append(new_or_node)
            or_node = new_or_node
        or_node.append(extras[-1])
        if_ex.append(or_node)
    else:
        if_ex.append(comp)
    if_statement.append(if_ex)
    if_statement.append(transform_block(case_node.get("BLOCK")))
    return if_statement


def transform_default(default_node, i):
    if i > 0:
        else_statement = ParseNode("ELSE", default_node.token, value="else")
    else:
        raise TransformException("Something unknown went wrong")
    else_statement.append(transform_block(default_node.get("BLOCK")))
    return else_statement


@transforms("CALLSPECIAL")
def transform_callspecial(cs_node: ParseNode):
    cs_node.node_type = "CALL"
    cs_node.append(ParseNode("IDENT", cs_node.token, cs_node.value))
    if cs_node.value == "array":
        yield from transform_array(cs_node)
    elif cs_node.value == "__dir__":
        # We don't need to transform_call if we are generating the argslist entirely ourselves
        cs_node["IDENT"].value = "dirname"
        add_argument(cs_node, ParseNode("IDENT", cs_node.token, value="__file__"))
        yield cs_node
    else:
        yield from transform_call(cs_node)


@transforms("INDEX")
def transform_index(index_node: ParseNode):
    # TODO: Maybe change to a call to append? Would require altering parent too
    exp = index_node["EXPRESSION"]
    if len(exp) == 0:
        exp.append(ParseNode("STRING", exp.token, "MagicEmptyArrayIndex"))
    transform_children(index_node)
    yield index_node


def transform_array(array_node):
    i = 0
    list_node = ParseNode("LIST", array_node.token, value="[", parent=array_node)
    for e in array_node.get("ARGSLIST"):
        c = e[0]
        tuple_node = ParseNode("TUPLE", c.token, value="(")
        if c.value == "=>":
            tuple_node.append(transform_single_node(c[1]))
            tuple_node.append(transform_single_node(c[0]))
        else:
            tuple_node.append(ParseNode("INT", c.token, value=i))
            tuple_node.append(c)
            i += 1
        list_node.append(tuple_node)
    l_e = ParseNode("EXPRESSION", list_node.token, "_list expression")
    l_e.append(list_node)
    array_node.get("ARGSLIST").children = [l_e]
    yield array_node


@transforms("FUNCTION")
def transform_function(function_node: ParseNode):
    pdebug("T FUNCTION")
    transform_children(function_node["ARGSLIST"])
    transform_children(function_node["BLOCK"])
    yield function_node
    # TODO: Highly cheating - need to make an attr access properly instead
    t = function_node.token
    attr_node = ParseNode("VAR", t, "_f_.{}".format(function_node.value))
    assign_node = ParseNode("ASSIGNMENT", t, "=")
    assign_node.append(ParseNode("VAR", t, function_node.value))
    assign_node.append(attr_node)
    yield assign_node


@transforms("CLASS")
def transform_class(class_node: ParseNode):
    pdebug("T CLASS", class_node)
    cnt = class_node.token

    # The base class for all php derived classes should be PhpBase
    if "EXTENDS" not in class_node:
        class_node.append(ParseNode("EXTENDS", cnt, "PhpBase"))

    # Fix the class contents up
    transform_children(class_node["BLOCK"])
    yield class_node

    # TODO: Highly cheating - need to make an attr access properly instead
    attr_node = ParseNode("VAR", cnt, "_c_.{}".format(class_node.value))
    assign_node = ParseNode("ASSIGNMENT", cnt, "=")
    assign_node.append(ParseNode("VAR", cnt, class_node.value))
    assign_node.append(attr_node)
    statement_node = ParseNode("STATEMENT", cnt)
    statement_node.append(assign_node)
    yield statement_node


@transforms("METHOD", "CLASSMETHOD")
def transform_method(node):
    args = node["ARGSLIST"]
    args.children.insert(0, ParseNode("VAR", args.token, value="self", parent=args))
    transform_children(node["BLOCK"])
    # TODO: Probably have to rearrange some things here
    yield node


def add_argument(node: ParseNode, argument: ParseNode):
    """ Add an expression or another node as an argument to a call function

    Will wrap a non-expression argument up in an expression

    """
    if argument.node_type != "EXPRESSION":
        e = ParseNode("EXPRESSION", argument.token)
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
    "(unset)": None,    # TODO: unset should be not so shit. Use "del"
}


# MAGIC_CONSTANTS = ["__line__", "__file__", "__dir__", "__function__", "__class__",
#                   "__trait__", "__method__", "__namespace__"]
