import math
import operator
from dataclasses import dataclass
from typing import Iterator

from .base import AstExportable
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
class Expr(AstExportable):
    def _iter_subs(self) -> Iterator['Expr']:
        yield from []

    def _iter_all_subs(self):
        yield self
        for sub in self._iter_subs():
            yield from sub._iter_all_subs()

    def list_variables(self):
        vs, retval = set(), []
        for item in self._iter_all_subs():
            if isinstance(item, Variable) and item.name not in vs:
                retval.append(item)
                vs.add(item.name)
        return retval

    def _call(self, **kwargs):
        raise NotImplementedError  # pragma: no cover

    def __call__(self, **kwargs):
        return self._call(**kwargs)

    def to_ast_node(self) -> dsl_nodes.Expr:
        raise NotImplementedError  # pragma: no cover


@dataclass
class Integer(Expr):
    value: int

    def __str__(self):
        return str(self.value)

    def _call(self, **kwargs):
        return self.value

    def to_ast_node(self) -> dsl_nodes.Expr:
        return dsl_nodes.Integer(raw=str(int(self.value)))


@dataclass
class Float(Expr):
    value: float

    def __str__(self):
        return str(self.value)

    def _call(self, **kwargs):
        return self.value

    def to_ast_node(self) -> dsl_nodes.Expr:
        const_name = None
        if abs(self.value - math.pi) < 1e-10:
            const_name = 'pi'
        elif abs(self.value - math.e) < 1e-10:
            const_name = 'E'
        elif abs(self.value - math.tau) < 1e-10:
            const_name = 'tau'

        if const_name is None:
            return dsl_nodes.Float(raw=str(float(self.value)))
        else:
            return dsl_nodes.Constant(raw=const_name)


@dataclass
class Boolean(Expr):
    value: bool

    def __post_init__(self):
        self.value = bool(self.value)

    def __str__(self):
        return 'true' if self.value else 'false'

    def _call(self, **kwargs):
        return self.value

    def to_ast_node(self) -> dsl_nodes.Expr:
        return dsl_nodes.Boolean(raw=str(self))


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

_OP_FUNCTIONS = {
    # Unary operators
    "unary+": operator.pos,
    "unary-": operator.neg,
    "!": lambda x: not bool(x),
    "not": lambda x: not bool(x),

    # Binary operators
    "**": operator.pow,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    "+": operator.add,
    "-": operator.sub,
    "<<": operator.lshift,
    ">>": operator.rshift,
    "&": operator.and_,
    "^": operator.xor,
    "|": operator.or_,
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
    "&&": lambda x, y: bool(x) and bool(y),
    "and": lambda x, y: bool(x) and bool(y),
    "||": lambda x, y: bool(x) or bool(y),
    "or": lambda x, y: bool(x) or bool(y),

    # Ternary operator
    "?:": lambda condition, true_value, false_value: true_value if condition else false_value
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

    def _call(self, **kwargs):
        return _OP_FUNCTIONS[self.op_mark](self.x._call(**kwargs), self.y._call(**kwargs))

    def to_ast_node(self) -> dsl_nodes.Expr:
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

        left_term = self.x.to_ast_node()
        if left_need_paren:
            left_term = dsl_nodes.Paren(left_term)
        right_term = self.y.to_ast_node()
        if right_need_paren:
            right_term = dsl_nodes.Paren(right_term)

        return dsl_nodes.BinaryOp(
            expr1=left_term,
            op=self.op,
            expr2=right_term,
        )


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

    def _call(self, **kwargs):
        return _OP_FUNCTIONS[self.op_mark](self.x._call(**kwargs))

    def to_ast_node(self) -> dsl_nodes.Expr:
        return dsl_nodes.UnaryOp(op=self.op, expr=self.x.to_ast_node())


_MATH_FUNCTIONS = {
    # Trigonometric functions
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,

    # Hyperbolic functions
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "asinh": math.asinh,
    "acosh": math.acosh,
    "atanh": math.atanh,

    # Root and power functions
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.pow(x, 1 / 3),  # Cube root implementation
    "exp": math.exp,

    # Logarithmic functions
    "log": math.log,  # Natural logarithm (base e)
    "log10": math.log10,
    "log2": math.log2,
    "log1p": math.log1p,  # log(1+x)

    # Rounding and absolute value functions
    "abs": abs,  # Python's built-in abs function
    "ceil": math.ceil,
    "floor": math.floor,
    "round": round,  # Python's built-in round function
    "trunc": math.trunc,

    # Sign function
    "sign": lambda x: 0 if x == 0 else (1 if x > 0 else -1)  # Returns the sign of x
}


@dataclass
class UFunc(Expr):
    func: str
    x: Expr

    def __str__(self):
        return f'{self.func}({self.x})'

    def _iter_subs(self):
        yield self.x

    def _call(self, **kwargs):
        return _MATH_FUNCTIONS[self.func](self.x._call(**kwargs))

    def to_ast_node(self) -> dsl_nodes.Expr:
        return dsl_nodes.UFunc(func=self.func, expr=self.x.to_ast_node())


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

    def _call(self, **kwargs):
        cond_value = self.cond._call(**kwargs)
        if cond_value:
            return self.if_true._call(**kwargs)
        else:
            return self.if_false._call(**kwargs)

    def to_ast_node(self) -> dsl_nodes.Expr:
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

        cond_term = self.cond.to_ast_node()
        true_term = self.if_true.to_ast_node()
        if true_need_paren:
            true_term = dsl_nodes.Paren(true_term)
        false_term = self.if_false.to_ast_node()
        if false_need_paren:
            false_term = dsl_nodes.Paren(false_term)

        return dsl_nodes.ConditionalOp(
            cond=cond_term,
            value_true=true_term,
            value_false=false_term,
        )


@dataclass
class Variable(Expr):
    name: str

    def __str__(self):
        return self.name

    def _call(self, **kwargs):
        return kwargs[self.name]

    def to_ast_node(self) -> dsl_nodes.Expr:
        return dsl_nodes.Name(name=self.name)


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
