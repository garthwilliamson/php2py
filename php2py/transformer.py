from __future__ import absolute_import, unicode_literals

import logging
from typing import Tuple, Iterable

from .intermediate import *


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
            body_statements.append(HtmlNode(tln))

    body_block = BlockNode(ParseNode("BLOCK", None), body_statements)

    body_function = FunctionNode("body", None, body_block)
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
        parent = c_access(ParseNode("IDENT", None, "PhpBase"))
    else:
        parent = c_access(node["EXTENDS"])
    attribs = []
    methods = []
    body = []
    for c in node["BLOCK"]:
        if c.kind in ("METHOD", "CLASSMETHOD", "FUNCTION"):
            m = transform_method(c)
            methods.append(m)
            body.append(m)
        elif c.kind == "STATEMENT":
            ex_s = transform_plain_statement(c)
            if ex_s.child.kind == "ASSIGNMENT":
                attribs.append(ex_s.child)
            body.append(ex_s)
    t.post_statements.append(assignment_statement(c_access(node), VariableNode(node)))
    return ClassNode(node, parent, BlockNode("", body), attribs, methods)


@transforms("HTML")
def transform_html(node: ParseNode) -> HtmlNode:
    return HtmlNode(node)


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
def transform_plain_statement(node: ParseNode) -> ExpressionStatement:
    """ We expect plain statements to contain just an EXPRESSION

    """
    if "EXPRESSION" in node:
        expr = transform_plain_expression(node["EXPRESSION"])
    else:
        expr = NoopNode("")

    if "COMMENTLINE" in node:
        comment = CommentNode(node[0])
    elif "COMMENTBLOCK" in node:
        lines = []
        for c in node.get_all("COMMENTBLOCK"):
            lines.append(c)
        comment = CommentNode(lines[0])
        if len(lines) > 1:
            for l in lines[1:]:
                t.post_statements.append(ExpressionStatement(l, NoopNode(""), CommentNode(l)))
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


def transform_elif(node: ParseNode) -> ElifNode:
    # TODO: One liners
    t.hoisting = True
    condition = t.transform_expr_node(node["EXPRESSIONGROUP"]["EXPRESSION"][0])
    t.hoisting = False
    block = transform_block(node["BLOCK"])
    return ElifNode(node, condition, block)


def transform_else(node: ParseNode) -> ElseNode:
    # TODO: One liners
    return ElseNode(node, transform_block(node["BLOCK"]))


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


@transforms("WHILE")
def transform_while(node: ParseNode):
    condition = t.transform_expr_node(node["EXPRESSIONGROUP"]["EXPRESSION"])
    block = transform_block(node["BLOCK"])
    return WhileNode(node, condition, block)


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


@transforms("TRY")
def transform_try(node: ParseNode):
    catches = []
    for c in node.get_all("CATCH"):
        exc = [transform_exception(e) for e in c.get_all("EXCEPTION")]
        exc_name = t.transform_expr_node(c["AS"][0])
        catch_block = transform_block(c["BLOCK"])
        catches.append(CatchNode(c, exc, exc_name, catch_block))

    block = transform_block(node["BLOCK"])
    return TryNode(node, block, catches)


def transform_exception(node: ParseNode) -> ExceptionNode:
    return ExceptionNode(node)


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
    elif node.value == "__dir__":
        file = VariableNode("__file__")
        return f_call(node, "dirname", [file])

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
            index = IntNode(str(i))
            i += 1
            children.append(TupleNode(el.parse_node, [index, el]))
    return f_call(node, "array", children)


def transform_isset(node: ParseNode):
    """
    With input
    VAR1 = isset(VAR2)
    Expected output:
    try:
        _tempvar = VAR2 is not None
    except NameError:
        _tempvar = False
    VAR1 =_tempvar
    """
    # TODO: Deal with more than one argument
    not_none = Operator1Node("not", NoneNode(node))
    is_ = Operator2Node("is", t.transform_expr_node(node["ARGSLIST"]["EXPRESSION"]), not_none)
    tempvar = VariableNode("_tempvar")
    try_contents = [assignment_statement(tempvar, is_)]
    try_block = BlockNode(node, try_contents)
    catch_block = BlockNode(node, [assignment_statement(tempvar, BoolNode("False"))])
    exceptions = [ExceptionNode("NameError"), ExceptionNode("KeyError")]
    catch_node = CatchNode(node, exceptions, None, catch_block)
    t.pre_statements.append(TryNode(node, try_block, [catch_node]))
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


@transforms("OPERATOR3")
def transform_operator3(node: ParseNode) -> Operator3Node:
    condition = t.transform_expr_node(node[2])
    true_res = t.transform_expr_node(node[0])
    false_res = t.transform_expr_node(node[1])
    return Operator3Node(node, condition, true_res, false_res)


@transforms("CALL")
def transform_call(node: ParseNode):
    if node[1].kind == "CONSTANT":
        node[1].value = node[1].value.lower()
        lhs = f_access(node[1])
    elif node[1].kind == "ATTR":
        node[1][0].value = node[1][0].value.lower()
        lhs = transform_attr(node[1])
    else:
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


@transforms("STATICATTR")
def transform_staticattr(node: ParseNode) -> Operator2Node:
    if node[1].kind == "CONSTANT":
        lhs = c_access(node[1])
    else:
        raise NotImplementedError("Expect LHS of staticattr to be constant")
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
        ga = IdentNode("getattr")
        ga_args = [VariableNode("_c_"), t.transform_expr_node(node["CALL"][1])]
        ga_call = CallNode("node", ga, ga_args)
        args = []
        for a in node["CALL"]["EXPRESSIONGROUP"]:
            args.append(t.transform_expr_node(a))
        return CallNode(node, ga_call, args)


@transforms("GETATTR")
def transform_getattr(node: ParseNode) -> CallNode:
    obj = t.transform_expr_node(node[1])
    name = t.transform_expr_node(node[0])
    return CallNode(node, IdentNode("getattr"), [obj, name])


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


# TODO: String casts for bools are "1" and "", not "True" and "False"
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
