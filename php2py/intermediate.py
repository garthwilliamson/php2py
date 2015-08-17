from typing import Optional, List, TypeVar

from php2py.clib.segment import CompiledSegment
from php2py.clib.parsetree import *

# TODO: Check usage of typevar


PnOrStr = TypeVar("PnOrStr", ParseNode, str)


class IntermediateNode(MatchableNode):
    base_kind = None
    kind = None

    def __init__(self, parse_node: PnOrStr) -> None:
        """ If passed a parse_node as arg, constructs out of the parse_node

        Otherwise must supply value
        """
        if isinstance(parse_node, ParseNode):
            self.parse_node = parse_node
            self.value = parse_node.value
            self.id_ = parse_node.id_
            self.token = parse_node.token
        else:
            self.parse_node = None
            self.value = parse_node
            self.id_ = get_next_id()
            self.token = None
        self.type = "Unknown"

    def __str__(self):
        return "{}:{} -> {}".format(self.kind, self.value, self.type)

    def __iter__(self):
        return iter([])


class ExpressionNode(IntermediateNode):
    base_kind = "EX"
    kind = None

    def compile(self) -> str:
        return str(self.value)


class StatementNode(IntermediateNode):
    base_kind = "STATEMENT"
    kind = None

    def compile(self) -> CompiledSegment:
        cs = CompiledSegment()
        for c in self:
            cs.append(c.compile())
        return cs


class HtmlNode(StatementNode):
    kind = "HTML"

    def compile(self) -> CompiledSegment:
        cs = CompiledSegment()
        cs.append("_app_.write({})".format(repr(self.value)))
        return cs


class BlockNode(IntermediateNode):
    base_kind = "BLOCK"
    kind = "BLOCK"

    def __init__(self, parse_node: PnOrStr, children: List[StatementNode]) -> None:
        super().__init__(parse_node)
        self.children = children

    def __iter__(self):
        yield from self.children

    def compile(self) -> CompiledSegment:
        cs = CompiledSegment()
        cs.indent()
        for c in self:
            cs.append(c.compile())
        cs.dedent()
        return cs


class CommentNode(IntermediateNode):
    base_kind = "COMMENT"
    kind = "COMMENT"

    def __init__(self, parse_node: ParseNode) -> None:
        super().__init__(parse_node)

    def compile(self):
        return "# " + self.value


class ExpressionStatement(StatementNode):
    kind = "EX_STATEMENT"

    def __init__(self, parse_node: PnOrStr, child: ExpressionNode, comment: Optional[CommentNode]=None) -> None:
        super().__init__(parse_node)
        # Expression statements don't need a type
        self.type = "Any"

        self.child = child
        self.comment = comment

    def __iter__(self):
        yield self.child
        if self.comment is not None:
            yield self.comment

    def compile(self):
        cs = CompiledSegment()
        line = self.child.compile()
        if self.comment is not None:
            if line == "":
                line = self.comment.compile()
            else:
                line = "{} {}".format(line, self.comment.compile())
        cs.append(line)
        return cs


class VariableNode(ExpressionNode):
    kind = "VAR"


class CommaListNode(ExpressionNode):
    kind = "COMMALIST"

    def __init__(self, parse_node: ParseNode, children: List[ExpressionNode]) -> None:
        super().__init__(parse_node)
        self.children = children

    def __iter__(self):
        yield from self.children

    def compile(self):
        return ", ".join([c.compile() for c in self.children])


class StringNode(ExpressionNode):
    kind = "STRING"

    def compile(self):
        return '"{}"'.format(self.value)


class IntNode(ExpressionNode):
    kind = "INT"


class BoolNode(ExpressionNode):
    kind = "BOOL"


class NoneNode(ExpressionNode):
    kind = "NONE"

    def compile(self):
        return "None"


class ListNode(CommaListNode):
    kind = "LIST"

    def compile(self):
        return "[{}]".format(super().compile())


class TupleNode(CommaListNode):
    kind = "TUPLE"

    def compile(self):
        return "({})".format(super().compile())


class IdentNode(ExpressionNode):
    kind = "IDENT"


class ExceptionNode(IdentNode):
    kind = "EXCEPTION"


class FunctionNode(IntermediateNode):
    base_kind = "FUNCTION"
    kind = "FUNCTION"

    def __init__(self, parse_node: PnOrStr, args: Optional[List[ExpressionNode]], body: BlockNode):
        super().__init__(parse_node)
        if args is None:
            args = []
        self.args = args
        self.body = body

    def __iter__(self):
        yield from self.args
        yield self.body

    def compile(self):
        cs = CompiledSegment()
        args = ", ".join([a.compile() for a in self.args])
        cs.append("def {}({}):".format(self.value, args))
        cs.append(self.body.compile())
        return cs


class MethodNode(FunctionNode):
    kind = "METHOD"


class ClassMethodNode(MethodNode):
    kind = "CLASSMETHOD"


class Operator2Node(ExpressionNode):
    kind = "OPERATOR2"

    def __init__(self,
                 parse_node: PnOrStr,
                 lhs: ExpressionNode,
                 rhs: ExpressionNode) -> None:
        super().__init__(parse_node)
        self.lhs = lhs
        self.rhs = rhs

    def __iter__(self):
        yield self.lhs
        yield self.rhs

    def compile(self):
        # TODO: Think about putting "." operators in own class
        if self.value in ("."):
            return "{}{}{}".format(self.lhs.compile(), self.value, self.rhs.compile())
        else:
            return "{} {} {}".format(self.lhs.compile(), self.value, self.rhs.compile())


class Operator3Node(ExpressionNode):
    kind = "OPERATOR3"

    def __init__(self,
                 parse_node: PnOrStr,
                 condition: ExpressionNode,
                 true_res: ExpressionNode,
                 false_res: ExpressionNode):
        super().__init__(parse_node)
        self.condition = condition
        self.true_res = true_res
        self.false_res = false_res

    def __iter__(self):
        yield self.condition
        yield self.true_res
        yield self.false_res

    def compile(self):
        return "{} if {} else {}".format(self.true_res.compile(), self.condition.compile(), self.false_res.compile())


class Operator1Node(ExpressionNode):
    kind = "OPERATOR1"

    def __init__(self, parse_node: PnOrStr, child: ExpressionNode):
        super().__init__(parse_node)
        self.child = child

    def __iter__(self):
        yield self.child

    def compile(self) -> str:
        return "{} {}".format(self.value, self.child.compile())


class AssignmentNode(Operator2Node):
    kind = "ASSIGNMENT"

    # TODO: Add new method annotate_types
    # lhs.type = rhs.type

    def compile(self):
        return "{} = {}".format(self.lhs.compile(), self.rhs.compile())


class AttributeNode(AssignmentNode):
    kind = "ATTRIBUTE"


class ClassNode(IntermediateNode):
    base_kind = "CLASS"
    kind = "CLASS"

    def __init__(self,
                 parse_node: PnOrStr,
                 parent: ExpressionNode,
                 body: BlockNode,
                 attributes: List[AttributeNode],
                 methods: List[MethodNode]):
        super().__init__(parse_node)
        self.parent = parent
        self.body = body
        self.attributes = attributes
        self.methods = methods

    def __iter__(self):
        yield self.parent
        yield self.body

    def compile(self):
        cs = CompiledSegment()
        cs.append("class {}({}):".format(self.value, self.parent.compile()))
        cs.indent()
        # TODO: Move as appropriate to __init__
        cs.append(self.body.compile())
        return cs


class RootNode(IntermediateNode):
    base_kind = "ROOT"
    kind = "ROOT"

    def __init__(self, parse_node: PnOrStr, functions: List[FunctionNode], classes: List[ClassNode]):
        super().__init__(parse_node)
        self.functions = functions
        self.classes = classes

    def __iter__(self):
        yield from iter(self.functions)
        yield from iter(self.classes)


class ReturnNode(ExpressionStatement):
    kind = "RETURN_STATEMENT"

    def compile(self):
        cs = CompiledSegment()
        cs.append("return {}".format(self.child.compile()))
        # TODO: Comments
        return cs


class NoopNode(ExpressionNode):
    kind = "NOOP"

    def compile(self) -> str:
        return ""


class CallNode(ExpressionNode):
    kind = "CALL"

    def __init__(self, parse_node: PnOrStr, callee, args: List[ExpressionNode]) -> None:
        super().__init__(parse_node)
        self.callee = callee
        self.args = args

    def __iter__(self):
        yield self.callee
        yield from self.args

    def compile(self) -> str:
        args = ", ".join([a.compile() for a in self.args])
        return "{}({})".format(self.callee.compile(), args)


class PySpecial(VariableNode):
    kind = "PYSPECIAL"


class IndexNode(ExpressionNode):
    kind = "INDEX"

    def __init__(self, parse_node: PnOrStr, target: ExpressionNode, key: ExpressionNode) -> None:
        super().__init__(parse_node)
        self.target = target
        self.key = key

    def __iter__(self):
        yield self.target
        yield self.key

    def compile(self) -> str:
        return "{}[{}]".format(self.target.compile(), self.key.compile())


class BlockStatement(StatementNode):
    kind = "BLOCK_STATEMENT"

    def __init__(self, parse_node: PnOrStr, block: BlockNode):
        super().__init__(parse_node)
        self.block = block

    def __iter__(self):
        yield self.block


class ElseNode(BlockStatement):
    kind = "ELSE"

    def compile(self):
        cs = CompiledSegment()
        cs.append("else:")
        cs.append(self.block.compile())
        return cs


class ElifNode(ElseNode):
    kind = "ELIF"

    def __init__(self,
                 parse_node: PnOrStr,
                 condition: ExpressionNode,
                 block: BlockNode):
        super().__init__(parse_node, block)
        self.condition = condition

    def __iter__(self):
        yield self.condition
        yield from super().__iter__()

    def compile(self):
        cs = CompiledSegment()
        cs.append("elif {}:".format(self.condition.compile()))
        cs.append(self.block.compile())
        return cs


class IfNode(BlockStatement):
    kind = "IF"

    def __init__(self,
                 parse_node: PnOrStr,
                 condition: ExpressionNode,
                 block: BlockNode,
                 elses: List[ElseNode]):
        super().__init__(parse_node, block)
        self.condition = condition
        self.elses = elses

    def __iter__(self):
        yield self.condition
        yield from super().__iter__()
        yield from self.elses

    def compile(self):
        cs = CompiledSegment()
        cs.append("if {}:".format(self.condition.compile()))
        cs.append(self.block.compile())
        for e in self.elses:
            cs.append(e.compile())
        return cs


class WhileNode(BlockStatement):
    kind = "WHILE"

    def __init__(self,
                 parse_node: PnOrStr,
                 condition: ExpressionNode,
                 block: BlockNode):
        super().__init__(parse_node, block)
        self.condition = condition

    def __iter__(self):
        yield self.condition
        yield from super().__iter__()

    def compile(self):
        cs = CompiledSegment()
        cs.append("while {}:".format(self.condition.compile()))
        cs.append(self.block.compile())
        return cs


class ForNode(BlockStatement):
    kind = "FOR"

    def __init__(self,
                 parse_node: PnOrStr,
                 thing: ExpressionNode,
                 items: ExpressionNode,
                 block: BlockNode):
        super().__init__(parse_node, block)
        self.thing = thing
        self.items = items

    def __iter__(self):
        yield self.thing
        yield self.items
        yield from super().__iter__()

    def compile(self):
        cs = CompiledSegment()
        cs.append("for {} in {}:".format(self.thing.compile(), self.items.compile()))
        cs.append(self.block.compile())
        return cs


class CatchNode(BlockStatement):
    kind = "CATCH"

    def __init__(self,
                 parse_node: PnOrStr,
                 exceptions: List[ExceptionNode],
                 exc_name: Optional[ExpressionNode],
                 block: BlockNode) -> None:
        super().__init__(parse_node, block)
        self.exceptions = exceptions
        self.exc_name = exc_name

    def __iter__(self):
        yield from self.exceptions
        yield from super().__iter__()

    def compile(self):
        cs = CompiledSegment()
        if len(self.exceptions) > 1:
            exceptions = "({})".format(", ".join([e.compile() for e in self.exceptions]))
        else:
            exceptions = self.exceptions[0].compile()

        if self.exc_name is None:
            cs.append("except {}:".format(exceptions))
        else:
            cs.append("except {} as {}:".format(exceptions, self.exc_name.compile()))
        cs.append(self.block.compile())
        return cs


class TryNode(BlockStatement):
    kind = "TRY"

    def __init__(self,
                 parse_node: PnOrStr,
                 block: BlockNode,
                 catches: List[CatchNode]) -> None:
        super().__init__(parse_node, block)
        self.catches = catches

    def __iter__(self):
        yield from super().__iter__()
        yield from self.catches

    def compile(self):
        cs = CompiledSegment()
        cs.append("try:")
        cs.append(self.block.compile())
        for c in self.catches:
            cs.append(c.compile())
        return cs
