from __future__ import absolute_import, unicode_literals

import logging

from .parsetree import ParseNode
from .intermediate import *
from typing import Tuple, Iterable


TransformExprTuple = Tuple[Iterable[StatementNode], ExpressionNode, Iterable[StatementNode]]

transform_map = {}


def transforms(*args):
    def wrap(f):
        for kind in args:
            transform_map[kind] = f
        return f
    return wrap


def pdebug(*s):
    logging.debug("|".join([str(p) for p in s]))


class TransformException(Exception):
    pass


def transform(root_node: ParseNode) -> RootNode:
    functions = []
    classes = []
    body_statements = []

    for tln in root_node:
        pdebug("Transforming top level node {}".format(tln))
        if tln.kind == "PHP":
            pdebug("T PHP")
            for php_child in tln:
                for n in t.transform_statement_node(php_child):
                    if n.kind == "FUNCTION":
                        functions.append(n)
                    elif n.kind == "CLASS":
                        classes.append(n)
                    else:
                        body_statements.append(n)
        else:
            pdebug("T HTML")
            # TODO: Change to a call to "echo" here
            body_statements.append(tln)

    body_block = BlockNode(ParseNode("BLOCK", None), body_statements)

    body_function = FunctionNode(ParseNode("FUNCTION", None, "body"), None, body_block)
    functions.append(body_function)
    return RootNode(root_node, functions, classes)


class Transformer:
    def __init__(self):
        self.hoisting = False
        self.pre_statements = []
        self.post_statements = []

    def transform_statement_node(self, node: ParseNode) -> StatementNode:
        if node.kind in transform_map:
            statement = transform_map[node.kind](node)
            yield from self.pre_statements
            yield statement
            yield from self.post_statements
            self.pre_statements.clear()
            self.post_statements.clear()
        else:
            raise NotImplementedError("UNKNOWN TRANSFORM " + str(node))

    def transform_expr_node(self, node: ParseNode) -> ExpressionNode:
        if node.kind in transform_map:
            res = transform_map[node.kind](node)
            return res
        else:
            raise NotImplementedError("UNKNOWN TRANSFORM " + str(node))


t = Transformer()


def transform_block(node: ParseNode) -> BlockNode:
    new_children = []
    for c in node:
        for statement in t.transform_statement_node(c):
            new_children.append(statement)
    return BlockNode(node, new_children)


@transforms("CLASS")
def transform_class(node: ParseNode) -> ClassNode:
    if "EXTENDS" not in node:
        parent = VariableNode("PhpBase")
    else:
        parent = VariableNode(node["EXTENDS"])
    attribs = []
    methods = []
    for c in node["BLOCK"]:
        if c.kind in ("METHOD", "CLASSMETHOD"):
            methods.append(transform_method(c))
        elif c.kind == "STATEMENT":
            # Construct an attribute
            a = transform_assignment(c["EXPRESSION"]["ASSIGNMENT"])
            attribs.append(AttributeNode(a.lhs.value, a.lhs, a.rhs))
    t.post_statements.append(assignment_statement(c_access(node), VariableNode(node)))
    return ClassNode(node, parent, attribs, methods)


@transforms("FUNCTION")
def transform_function(node: ParseNode) -> FunctionNode:
    args = []
    for a in node["ARGSLIST"]:
        args.append(transform_plain_expression(a))
    body = transform_block(node["BLOCK"])
    t.post_statements.append(assignment_statement(f_access(node), VariableNode(node)))
    return FunctionNode(node, args, body)


def transform_method(node: ParseNode) -> MethodNode:
    # Php methods starting with __ include the constructor
    if node.value.startswith("__"):
        node.value = "_php_" + node.value[2:]
    args = [VariableNode("this")]
    for a in node["ARGSLIST"]:
        args.append(transform_plain_expression(a))
    body = transform_block(node["BLOCK"])
    if node.kind == "CLASSMETHOD":
        return ClassMethodNode(node, args, body)
    else:
        return MethodNode(node, args, body)


@transforms("STATEMENT")
def transform_plain_statement(node: ParseNode) -> StatementNode:
    """ We expect plain statements to contain just an EXPRESSION

    """
    if "EXPRESSION" in node:
        expr = transform_plain_expression(node["EXPRESSION"])
    else:
        expr = NoopNode("")

    if "COMMENTLINE" in node:
        comment = CommentNode(node[0])
    else:
        comment = None

    return ExpressionStatement(node, expr, comment)


@transforms("IF")
def transform_if(node: ParseNode) -> IfNode:
    # Check if this if was a one liner
    # TODO: Maybe use python one liners? Not very pythonic though
    if "STATEMENT" in node:
        s = transform_plain_statement(node["STATEMENT"])
        if_block = BlockNode(s.parse_node, [s])
    else:
        if_block = transform_block(node["BLOCK"])
    t.hoisting = True
    if_op = t.transform_expr_node(node["EXPRESSIONGROUP"]["EXPRESSION"][0])
    t.hoisting = False
    elses = []

    for c in node:
        if c.kind == "ELIF":
            elses.append(transform_elif(c))
        elif c.kind == "ELSE":
            elses.append(transform_else(c))
    return IfNode(node, if_op, if_block, elses)


@transforms("FOREACH")
def transform_foreach(node: ParseNode):
    as_ = node.match("EXPRESSIONGROUP/EXPRESSION/OPERATOR2")
    thing = as_[0]
    items = as_[1]
    if thing.value == "=>":
        its = Operator2Node(".", t.transform_expr_node(items), VariableNode("items"))
        items = CallNode(thing, its, [])
        key = t.transform_expr_node(thing[1])
        value = t.transform_expr_node(thing[0])
        thing = CommaListNode(thing, [key, value])
    else:
        items = t.transform_expr_node(items)
        thing = t.transform_expr_node(thing)
    return ForNode(node, thing, items, transform_block(node["BLOCK"]))


@transforms("SWITCH")
def transform_switch(node: ParseNode) -> IfNode:
    decide_ex = t.transform_expr_node(node["EXPRESSIONGROUP"]["EXPRESSION"])
    switch_var = VariableNode("_switch_choice")

    # The contents of the switch will be rearranged into a whole series of elif
    contents = node["BLOCK"]
    # We are going to ignore "STATEMENT" nodes directly in block for now - these are comments
    first = contents[0]
    if_rhs = t.transform_expr_node(first["EXPRESSION"])
    if_decide = Operator2Node(first, switch_var, if_rhs)
    if_block = transform_block(first["BLOCK"])

    extras = []
    elses = []
    for c in contents:
        if c.kind == "CASE":
            elses.append(transform_case(c, switch_var, extras))
            extras = []
        elif c.kind == "DEFAULT":
            elses.append(ElseNode(c, transform_block(c["BLOCK"])))
        elif c.kind == "CASEFALLTHROUGH":
            ctf_node = transform_case(c, switch_var, extras)
            elses.append(ctf_node)
            extras.append(ctf_node.decision)
        elif c.kind == "STATEMENT":
            pass

    t.pre_statements.append(assignment_statement(switch_var, decide_ex))
    return IfNode(first, if_decide, if_block, elses)


def transform_case(node: ParseNode, switch_var: VariableNode, extras: List[ExpressionNode]) -> ElifNode:

    rhs = t.transform_expr_node(node["EXPRESSION"])
    decision = Operator2Node("==", switch_var, rhs)
    for e in extras:
        decision = Operator2Node("or", e, decision)
    block = transform_block(node["BLOCK"])
    return ElifNode(node, decision, block)


@transforms("RETURN")
def transform_return(node: ParseNode) -> ReturnNode:
    return ReturnNode(node, t.transform_expr_node(node[0]))


@transforms("EXPRESSION")
def transform_plain_expression(expression_node: ParseNode) -> ExpressionNode:
    if len(expression_node) == 0:
        return NoopNode(ParseNode("NOOP", expression_node.token))
    return t.transform_expr_node(expression_node[0])


@transforms("ASSIGNMENT")
def transform_assignment(node: ParseNode) -> AssignmentNode:
    # hoist assignments out of if statements etc
    lhs = t.transform_expr_node(node[1])
    rhs = t.transform_expr_node(node[0])
    if t.hoisting:
        t.pre_statements.append(assignment_statement(lhs, rhs))
        return lhs
    else:
        return AssignmentNode(node, lhs, rhs)


@transforms("NOOP")
def transform_noop(node: ParseNode) -> NoopNode:
    return NoopNode(node)


@transforms("INDEX")
def transform_index(node: ParseNode) -> IndexNode:
    exp = node["EXPRESSION"]
    if len(exp) == 0:
        exp.append(ParseNode("STRING", exp.token, "MagicEmptyArrayIndex"))
    lookup = transform_plain_expression(node[0])
    target = t.transform_expr_node(node[1])
    return IndexNode(node, target, lookup)


@transforms("STRING")
def transform_string(node: ParseNode) -> StringNode:
    return StringNode(node)


@transforms("INT")
def transform_int(node: ParseNode) -> IntNode:
    # TODO: Move the octal etc logic from the parser into here
    return IntNode(node)


@transforms("GLOBALVAR")
def transform_globalvar(node: ParseNode) -> Operator2Node:
    return g_access(node)


@transforms("VAR")
def transform_var(node: ParseNode) -> VariableNode:
    return VariableNode(node)


@transforms("IDENT")
def transform_ident(node: ParseNode) -> IdentNode:
    return IdentNode(node)


@transforms("CONSTANT")
def transform_constant(node: ParseNode) -> Operator2Node:
    return constant_access(node)


@transforms("CALLSPECIAL")
def transform_callspecial(node: ParseNode) -> CallNode:
    if node.value == "array":
        return transform_array(node)
    elif node.value == "isset":
        return transform_isset(node)

    # Basis transforms
    args = [t.transform_expr_node(c) for c in node["ARGSLIST"].children]
    if node.value == "unset":
        return CallNode(node, IdentNode("del"), args)
    else:
        # Straight _f_ calls
        return f_call(node, node.value, args)


def transform_array(node: ParseNode) -> CallNode:
    i = 0
    children = []
    for exp in node["ARGSLIST"]:
        el = t.transform_expr_node(exp)
        if el.value == "=>":
            assert isinstance(el, Operator2Node)
            children.append(TupleNode(el.parse_node, [el.lhs, el.rhs]))
        else:
            index = IntNode(ParseNode("INT", el.parse_node.token, str(i)))
            i += 1
            children.append(TupleNode(el.parse_node, [index, el]))
    ln = ListNode(node, children)
    return f_call(node, "array", [ln])


def transform_isset(node: ParseNode):
    """
    With input
    VAR1 = isset(VAR2)
    Expected output:
    try:
        _tempvar = not VAR2 is None
    except NameError:
        _tempvar = False
    VAR1 =_tempvar
    """
    # TODO: Deal with more than one argument
    is_ = Operator2Node("is", t.transform_expr_node(node["ARGSLIST"]["EXPRESSION"]), NoneNode(node))
    not_ = Operator1Node("not", is_)
    tempvar = VariableNode("_tempvar")
    try_contents = [assignment_statement(tempvar, not_)]
    try_block = BlockNode(node, try_contents)
    catch_block = BlockNode(node, [assignment_statement(tempvar, BoolNode("False"))])
    NameError_node = CatchNode(node, ExceptionNode("NameError"), catch_block)
    KeyError_node = CatchNode(node, ExceptionNode("KeyError"), catch_block)
    t.pre_statements.append(TryNode(node, try_block, [NameError_node, KeyError_node]))
    return tempvar


@transforms("OPERATOR2")
def transform_operator2(node: ParseNode) -> Operator2Node:
    if node.value in op_map:
        node.value = op_map[node.value]
    lhs = t.transform_expr_node(node[1])
    rhs = t.transform_expr_node(node[0])
    return Operator2Node(node, lhs, rhs)


@transforms("OPERATOR1")
def transform_operator1(node: ParseNode):
    if node.value in ["++", "--"]:
        node.value = node.value[0] + "="
        node.children.insert(0, ParseNode("INT", node.token, "1"))
        node.kind = "OPERATOR2"
        return transform_operator2(node)

    if node.value in op_map:
        node.value = op_map[node.value]
    child = t.transform_expr_node(node[0])
    return Operator1Node(node, child)


@transforms("CALL")
def transform_call(node: ParseNode):
    lhs = t.transform_expr_node(node[1])
    args = []
    for a in node["EXPRESSIONGROUP"]:
        args.append(t.transform_expr_node(a))
    return CallNode(node, lhs, args)


@transforms("ATTR")
def transform_attr(node: ParseNode) -> Operator2Node:
    lhs = t.transform_expr_node(node[1])
    # right hand side of attrs are just idents
    if node[0].kind == "CONSTANT":
        node[0].kind = "IDENT"
    rhs = t.transform_expr_node(node[0])
    return Operator2Node(".", lhs, rhs)


@transforms("NEW")
def transform_new(node: ParseNode) -> CallNode:
    class_call = node[0]
    class_name = class_call[1]
    if class_name.kind == "CONSTANT":
        access_node = c_access(class_name)
        args = []
        for a in class_call["EXPRESSIONGROUP"]:
            args.append(t.transform_expr_node(a))
        return CallNode(node, access_node, args)
    else:
        raise NotImplementedError("This should be implemented")
        return transform_call(node["CALL"])


def g_access(node: ParseNode) -> Operator2Node:
    """ Creates a new attribute access into the _g_ namespace

    """
    var = VariableNode(node)
    g = VariableNode("_g_")
    return Operator2Node(".", g, var)


def c_access(node: ParseNode) -> Operator2Node:
    """ Creates a new attribute access into the _c_ namespace

    """
    var = VariableNode(node)
    c = VariableNode("_c_")
    return Operator2Node(".", c, var)


def constant_access(node: ParseNode) -> Operator2Node:
    var = VariableNode(node)
    c = VariableNode("_constants_")
    return Operator2Node(".", c, var)


def f_access(node: ParseNode) -> Operator2Node:
    """ Creates a new attribute access into the _c_ namespace

    """
    var = VariableNode(node)
    f = VariableNode("_f_")
    return Operator2Node(".", f, var)


def f_call(node: ParseNode, f_name: str, args: List[ExpressionNode]):
    """ Create a new call to an element of the _f_ namespace
    """
    f = VariableNode("_f_")
    op2 = Operator2Node(".", f, IdentNode(f_name))
    return CallNode(node, op2, args)


def assignment_statement(lhs, rhs) -> ExpressionStatement:
    token = lhs.token
    op2_pn = ParseNode("ASSIGNMENT", token, "=")
    op2 = AssignmentNode(op2_pn, lhs, rhs)
    return ExpressionStatement(op2_pn, op2)


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


op_map = {
    "!": "not ",
    ".": "+",
    "&&": "and",
    "||": "or",
    "===": "==",     # TODO: Do we need to use a function here? I think the == case is the naughty one...
    "!==": "!=",
}
