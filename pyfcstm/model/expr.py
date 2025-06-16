from dataclasses import dataclass
from typing import Iterator

from ..dsl import node as dsl_nodes

__all__ = [
    'Expr',
    'Integer',
    'Float',
    'Boolean',
    'Op',
    'UnaryOp',
    'BinaryOp',
    'ConditionalOp',
    'UFunc',
    'Variable',
    'parse_expr_node_to_expr',
]


@dataclass
class Expr:
    def _iter_subs(self) -> Iterator['Expr']:
        yield from []

    def _iter_all_subs(self):
        yield self
        for sub in self._iter_subs():
            yield from sub._iter_all_subs()

    def list_variables(self):
        vs, retval = set(), []
        for item in self._iter_all_subs():
            print('x', item)
            if isinstance(item, Variable) and item.name not in vs:
                retval.append(item)
                vs.add(item.name)
        return retval


@dataclass
class Integer(Expr):
    value: int

    def __str__(self):
        return str(self.value)


@dataclass
class Float(Expr):
    value: float

    def __str__(self):
        return str(self.value)


@dataclass
class Boolean(Expr):
    value: bool

    def __str__(self):
        return 'true' if self.value else 'false'


_OP_PRECEDENCE = {
    # Parentheses (highest precedence)
    "()": 100,

    # Function calls
    "function_call": 90,

    # Unary operators
    "unary+": 80,
    "unary-": 80,
    "!": 80,
    "not": 80,

    # Exponentiation (right associative)
    "**": 70,

    # Multiplicative operators
    "*": 60,
    "/": 60,
    "%": 60,

    # Additive operators
    "+": 50,
    "-": 50,

    # Bitwise shift operators
    "<<": 40,
    ">>": 40,

    # Bitwise AND
    "&": 35,

    # Bitwise XOR
    "^": 30,

    # Bitwise OR
    "|": 25,

    # Comparison operators
    "<": 20,
    ">": 20,
    "<=": 20,
    ">=": 20,
    "==": 20,
    "!=": 20,

    # Logical operators
    "&&": 15,
    "and": 15,
    "||": 10,
    "or": 10,

    # Conditional/ternary operator (C-style)
    "?:": 5
}


@dataclass
class Op(Expr):
    @property
    def op_mark(self):
        raise NotImplementedError  # pragma: no cover


@dataclass
class BinaryOp(Op):
    __aliases__ = {
        'and': '&&',
        'or': '||',
    }

    x: Expr
    op: str
    y: Expr

    def __post_init__(self):
        self.op = self.__aliases__.get(self.op, self.op)

    @property
    def op_mark(self):
        return self.op

    def __str__(self):
        my_pre = _OP_PRECEDENCE[self.op_mark]

        left_need_paren = False
        if isinstance(self.x, Op):
            left_pre = _OP_PRECEDENCE[self.x.op_mark]
            if left_pre < my_pre:
                left_need_paren = True

        right_need_paren = False
        if isinstance(self.y, Op):
            right_pre = _OP_PRECEDENCE[self.y.op_mark]
            if right_pre <= my_pre:
                right_need_paren = True

        left_term = str(self.x)
        if left_need_paren:
            left_term = f'({left_term})'
        right_term = str(self.y)
        if right_need_paren:
            right_term = f'({right_term})'

        return f'{left_term} {self.op} {right_term}'

    def _iter_subs(self):
        yield self.x
        yield self.y


@dataclass
class UnaryOp(Op):
    __aliases__ = {
        'not': '!',
    }

    op: str
    x: Expr

    def __post_init__(self):
        self.op = self.__aliases__.get(self.op, self.op)

    @property
    def op_mark(self):
        return f'unary{self.op}' if self.op in {'+', '-'} else self.op

    def __str__(self):
        return f'{self.op}{self.x}'

    def _iter_subs(self):
        yield self.x


@dataclass
class UFunc(Expr):
    func: str
    x: Expr

    def __str__(self):
        return f'{self.func}({self.x})'

    def _iter_subs(self):
        yield self.x


@dataclass
class ConditionalOp(Op):
    cond: Expr
    if_true: Expr
    if_false: Expr

    @property
    def op_mark(self):
        return '?:'

    def __str__(self):
        my_pre = _OP_PRECEDENCE[self.op_mark]

        true_need_paren = False
        if isinstance(self.if_true, Op):
            true_pre = _OP_PRECEDENCE[self.if_true.op_mark]
            if true_pre <= my_pre:
                true_need_paren = True

        false_need_paren = False
        if isinstance(self.if_false, Op):
            false_pre = _OP_PRECEDENCE[self.if_false.op_mark]
            if false_pre <= my_pre:
                false_need_paren = True

        cond_term = f'({self.cond})'
        true_term = str(self.if_true)
        if true_need_paren:
            true_term = f'({true_term})'
        false_term = str(self.if_false)
        if false_need_paren:
            false_term = f'({false_term})'

        return f'{cond_term} ? {true_term} : {false_term}'

    def _iter_subs(self):
        yield self.cond
        yield self.if_true
        yield self.if_false


@dataclass
class Variable(Expr):
    name: str

    def __str__(self):
        return self.name


def parse_expr_node_to_expr(node: dsl_nodes.Expr) -> Expr:
    if isinstance(node, dsl_nodes.Name):
        return Variable(name=node.name)
    elif isinstance(node, (dsl_nodes.Integer, dsl_nodes.HexInt)):
        return Integer(value=node.value)
    elif isinstance(node, (dsl_nodes.Constant, dsl_nodes.Float)):
        return Float(value=node.value)
    elif isinstance(node, dsl_nodes.Boolean):
        return Boolean(value=node.value)
    elif isinstance(node, dsl_nodes.Paren):
        return parse_expr_node_to_expr(node.expr)
    elif isinstance(node, dsl_nodes.UnaryOp):
        return UnaryOp(
            op=node.op,
            x=parse_expr_node_to_expr(node.expr),
        )
    elif isinstance(node, dsl_nodes.BinaryOp):
        return BinaryOp(
            x=parse_expr_node_to_expr(node.expr1),
            op=node.op,
            y=parse_expr_node_to_expr(node.expr2),
        )
    elif isinstance(node, dsl_nodes.ConditionalOp):
        return ConditionalOp(
            cond=parse_expr_node_to_expr(node.cond),
            if_true=parse_expr_node_to_expr(node.value_true),
            if_false=parse_expr_node_to_expr(node.value_false),
        )
    elif isinstance(node, dsl_nodes.UFunc):
        return UFunc(
            func=node.func,
            x=parse_expr_node_to_expr(node.expr),
        )
    else:
        raise TypeError(f'Unknown node type - {node!r}.')
