from typing import Optional, List, TypeVar

from php2py.parsetree import *

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


class StatementNode(IntermediateNode):
    base_kind = "STATEMENT"
    kind = None


class BlockNode(IntermediateNode):
    base_kind = "BLOCK"
    kind = "BLOCK"

    def __init__(self, parse_node: PnOrStr, children: List[StatementNode]) -> None:
        super().__init__(parse_node)
        self.children = children

    def __iter__(self):
        yield from self.children


class CommentNode(IntermediateNode):
    base_kind = "COMMENT"
    kind = "COMMENT"

    def __init__(self, parse_node: ParseNode) -> None:
        super().__init__(parse_node)


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


class VariableNode(ExpressionNode):
    kind = "VAR"


class CommaListNode(ExpressionNode):
    kind = "COMMALIST"

    def __init__(self, parse_node: ParseNode, children: List[ExpressionNode]) -> None:
        super().__init__(parse_node)
        self.children = children

    def __iter__(self):
        yield from self.children


class StringNode(ExpressionNode):
    kind = "STRING"


class IntNode(ExpressionNode):
    kind = "INT"


class BoolNode(ExpressionNode):
    kind = "BOOL"


class NoneNode(ExpressionNode):
    kind = "NONE"


class ListNode(CommaListNode):
    kind = "LIST"


class TupleNode(CommaListNode):
    kind = "TUPLE"


class IdentNode(ExpressionNode):
    kind = "IDENT"


class ExceptionNode(IdentNode):
    kind = "EXCEPTION"


class FunctionNode(IntermediateNode):
    base_kind = "FUNCTION"
    kind = "FUNCTION"

    def __init__(self, parse_node: ParseNode, args: Optional[List[ExpressionNode]], body: BlockNode):
        super().__init__(parse_node)
        if args is None:
            args = []
        self.args = args
        self.body = body

    def __iter__(self):
        yield from self.args
        yield self.body


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


class Operator1Node(ExpressionNode):
    kind = "OPERATOR1"

    def __init__(self, parse_node: PnOrStr, child: ExpressionNode):
        super().__init__(parse_node)
        self.child = child

    def __iter__(self):
        yield self.child


class AssignmentNode(Operator2Node):
    kind = "ASSIGNMENT"

    # TODO: Add new method annotate_types
    # lhs.type = rhs.type


class AttributeNode(AssignmentNode):
    kind = "ATTRIBUTE"


class ClassNode(IntermediateNode):
    base_kind = "CLASS"
    kind = "CLASS"

    def __init__(self,
                 parse_node: PnOrStr,
                 parent: VariableNode,
                 attributes: List[AttributeNode],
                 methods: List[MethodNode]):
        super().__init__(parse_node)
        self.parent = parent
        self.attributes = attributes
        self.methods = methods

    def __iter__(self):
        yield self.parent
        yield from self.attributes
        yield from self.methods


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


class NoopNode(ExpressionNode):
    kind = "NOOP"


class CallNode(ExpressionNode):
    kind = "CALL"

    def __init__(self, parse_node: PnOrStr, callee, args: List[ExpressionNode]) -> None:
        super().__init__(parse_node)
        self.callee = callee
        self.args = args

    def __iter__(self):
        yield self.callee
        yield from self.args


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


class BlockStatement(StatementNode):
    kind = "BLOCK_STATEMENT"

    def __init__(self, parse_node: PnOrStr, block: BlockNode):
        super().__init__(parse_node)
        self.block = block

    def __iter__(self):
        yield self.block


class ElseNode(BlockStatement):
    kind = "ELSE"


class ElifNode(ElseNode):
    kind = "ELIF"

    def __init__(self,
                 parse_node: PnOrStr,
                 decision: ExpressionNode,
                 block: BlockNode):
        super().__init__(parse_node, block)
        self.decision = decision

    def __iter__(self):
        yield self.decision
        yield from super().__iter__()


class IfNode(BlockStatement):
    kind = "IF"

    def __init__(self,
                 parse_node: PnOrStr,
                 decision: ExpressionNode,
                 block: BlockNode,
                 elses: List[ElseNode]):
        super().__init__(parse_node, block)
        self.decision = decision
        self.elses = elses

    def __iter__(self):
        yield self.decision
        yield from super().__iter__()
        yield from self.elses


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


class CatchNode(BlockStatement):
    kind = "CATCH"

    def __init__(self,
                 parse_node: PnOrStr,
                 exception: ExceptionNode,
                 block: BlockNode) -> None:
        super().__init__(parse_node, block)
        self.exception = exception

    def __iter__(self):
        yield self.exception
        yield from super().__iter__()


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
