"""
Expression handling module for mathematical expressions and operations.

This module provides a comprehensive set of classes for representing and evaluating
mathematical expressions. It includes support for basic data types (integers, floats, booleans),
various operators (unary, binary, conditional), mathematical functions, and variables.

The expression system allows for:

- Building complex mathematical expressions
- Evaluating expressions with variable substitution
- Converting expressions to AST nodes
- Analyzing expressions to extract variables
- Handling operator precedence correctly

All expression classes inherit from the base `Expr` class and implement the AstExportable interface.
"""

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
    """
    Base class for all expressions.

    This abstract class defines the common interface for all expression types.
    It provides methods for traversing the expression tree, evaluating expressions,
    and converting expressions to AST nodes.

    :rtype: Expr
    """

    def _iter_subs(self) -> Iterator['Expr']:
        """
        Iterate over direct sub-expressions of this expression.

        :return: Iterator over sub-expressions
        :rtype: Iterator[Expr]
        """
        yield from []

    def _iter_all_subs(self):
        """
        Recursively iterate over all sub-expressions including this expression.

        :return: Iterator over all sub-expressions
        :rtype: Iterator[Expr]
        """
        yield self
        for sub in self._iter_subs():
            yield from sub._iter_all_subs()

    def list_variables(self):
        """
        List all unique variables used in this expression.

        :return: List of unique Variable objects
        :rtype: list[Variable]
        """
        vs, retval = set(), []
        for item in self._iter_all_subs():
            if isinstance(item, Variable) and item.name not in vs:
                retval.append(item)
                vs.add(item.name)
        return retval

    def _call(self, **kwargs):
        """
        Internal method to evaluate the expression with given variable values.

        :param kwargs: Variable name to value mapping
        :return: Result of the expression evaluation
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError  # pragma: no cover

    def __call__(self, **kwargs):
        """
        Evaluate the expression with given variable values.

        :param kwargs: Variable name to value mapping
        :return: Result of the expression evaluation
        """
        return self._call(**kwargs)

    def __str__(self):
        """
        Get string representation of the expression.

        :return: String representation
        :rtype: str
        """
        return str(self.to_ast_node())

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert this expression to an AST node.

        :return: AST node representation
        :rtype: dsl_nodes.Expr
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError  # pragma: no cover


@dataclass
class Integer(Expr):
    """
    Integer literal expression.

    :param value: Integer value
    :type value: int
    """
    value: int

    def _call(self, **kwargs):
        """
        Return the integer value.

        :param kwargs: Ignored
        :return: Integer value
        :rtype: int
        """
        return self.value

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to an Integer AST node.

        :return: Integer AST node
        :rtype: dsl_nodes.Integer
        """
        return dsl_nodes.Integer(raw=str(int(self.value)))


@dataclass
class Float(Expr):
    """
    Floating point literal expression.

    :param value: Float value
    :type value: float
    """
    value: float

    def _call(self, **kwargs):
        """
        Return the float value.

        :param kwargs: Ignored
        :return: Float value
        :rtype: float
        """
        return self.value

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to a Float AST node or a Constant node for special values.

        Recognizes mathematical constants like pi, e, and tau.

        :return: Float or Constant AST node
        :rtype: Union[dsl_nodes.Float, dsl_nodes.Constant]
        """
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
    """
    Boolean literal expression.

    :param value: Boolean value
    :type value: bool
    """
    value: bool

    def __post_init__(self):
        """
        Ensure the value is a boolean.
        """
        self.value = bool(self.value)

    def _call(self, **kwargs):
        """
        Return the boolean value.

        :param kwargs: Ignored
        :return: Boolean value
        :rtype: bool
        """
        return self.value

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to a Boolean AST node.

        :return: Boolean AST node
        :rtype: dsl_nodes.Boolean
        """
        return dsl_nodes.Boolean(raw=str(self.value).lower())


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
    """
    Base class for all operator expressions.

    This abstract class provides common functionality for operator expressions.
    """

    @property
    def op_mark(self):
        """
        Get the operator mark for precedence lookup.

        :return: Operator mark
        :rtype: str
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError  # pragma: no cover


@dataclass
class BinaryOp(Op):
    """
    Binary operator expression.

    :param x: Left operand
    :type x: Expr
    :param op: Operator symbol
    :type op: str
    :param y: Right operand
    :type y: Expr
    """
    __aliases__ = {
        'and': '&&',
        'or': '||',
    }

    x: Expr
    op: str
    y: Expr

    def __post_init__(self):
        """
        Normalize operator aliases.
        """
        self.op = self.__aliases__.get(self.op, self.op)

    @property
    def op_mark(self):
        """
        Get the operator mark for precedence lookup.

        :return: Operator mark
        :rtype: str
        """
        return self.op

    def _iter_subs(self):
        """
        Iterate over operands.

        :return: Iterator over operands
        :rtype: Iterator[Expr]
        """
        yield self.x
        yield self.y

    def _call(self, **kwargs):
        """
        Evaluate the binary operation.

        :param kwargs: Variable name to value mapping
        :return: Result of the operation
        """
        return _OP_FUNCTIONS[self.op_mark](self.x._call(**kwargs), self.y._call(**kwargs))

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to a BinaryOp AST node.

        Handles operator precedence by adding parentheses where needed.

        :return: BinaryOp AST node
        :rtype: dsl_nodes.BinaryOp
        """
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
    """
    Unary operator expression.

    :param op: Operator symbol
    :type op: str
    :param x: Operand
    :type x: Expr
    """
    __aliases__ = {
        'not': '!',
    }

    op: str
    x: Expr

    def __post_init__(self):
        """
        Normalize operator aliases.
        """
        self.op = self.__aliases__.get(self.op, self.op)

    @property
    def op_mark(self):
        """
        Get the operator mark for precedence lookup.

        :return: Operator mark
        :rtype: str
        """
        return f'unary{self.op}' if self.op in {'+', '-'} else self.op

    def _iter_subs(self):
        """
        Iterate over operands.

        :return: Iterator over operands
        :rtype: Iterator[Expr]
        """
        yield self.x

    def _call(self, **kwargs):
        """
        Evaluate the unary operation.

        :param kwargs: Variable name to value mapping
        :return: Result of the operation
        """
        return _OP_FUNCTIONS[self.op_mark](self.x._call(**kwargs))

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to a UnaryOp AST node.

        Handles operator precedence by adding parentheses where needed.

        :return: UnaryOp AST node
        :rtype: dsl_nodes.UnaryOp
        """
        my_pre = _OP_PRECEDENCE[self.op_mark]
        x_node = self.x.to_ast_node()
        if isinstance(self.x, Op):
            value_pre = _OP_PRECEDENCE[self.x.op_mark]
            if value_pre <= my_pre:
                x_node = dsl_nodes.Paren(expr=x_node)
        return dsl_nodes.UnaryOp(op=self.op, expr=x_node)


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
    """
    Mathematical function expression.

    Represents calls to mathematical functions like sin, cos, sqrt, etc.

    :param func: Function name
    :type func: str
    :param x: Function argument
    :type x: Expr
    """
    func: str
    x: Expr

    def _iter_subs(self):
        """
        Iterate over function arguments.

        :return: Iterator over arguments
        :rtype: Iterator[Expr]
        """
        yield self.x

    def _call(self, **kwargs):
        """
        Evaluate the function.

        :param kwargs: Variable name to value mapping
        :return: Result of the function call
        """
        return _MATH_FUNCTIONS[self.func](self.x._call(**kwargs))

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to a UFunc AST node.

        :return: UFunc AST node
        :rtype: dsl_nodes.UFunc
        """
        return dsl_nodes.UFunc(func=self.func, expr=self.x.to_ast_node())


@dataclass
class ConditionalOp(Op):
    """
    Conditional (ternary) operator expression.

    :param cond: Condition expression
    :type cond: Expr
    :param if_true: Expression to evaluate if condition is true
    :type if_true: Expr
    :param if_false: Expression to evaluate if condition is false
    :type if_false: Expr
    """
    cond: Expr
    if_true: Expr
    if_false: Expr

    @property
    def op_mark(self):
        """
        Get the operator mark for precedence lookup.

        :return: Operator mark
        :rtype: str
        """
        return '?:'

    def _iter_subs(self):
        """
        Iterate over sub-expressions.

        :return: Iterator over sub-expressions
        :rtype: Iterator[Expr]
        """
        yield self.cond
        yield self.if_true
        yield self.if_false

    def _call(self, **kwargs):
        """
        Evaluate the conditional operation.

        :param kwargs: Variable name to value mapping
        :return: Result of either if_true or if_false based on condition
        """
        cond_value = self.cond._call(**kwargs)
        if cond_value:
            return self.if_true._call(**kwargs)
        else:
            return self.if_false._call(**kwargs)

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to a ConditionalOp AST node.

        Handles operator precedence by adding parentheses where needed.

        :return: ConditionalOp AST node
        :rtype: dsl_nodes.ConditionalOp
        """
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
    """
    Variable reference expression.

    :param name: Variable name
    :type name: str
    """
    name: str

    def _call(self, **kwargs):
        """
        Lookup the variable value from kwargs.

        :param kwargs: Variable name to value mapping
        :return: Variable value
        :raises KeyError: If variable name is not found in kwargs
        """
        return kwargs[self.name]

    def to_ast_node(self) -> dsl_nodes.Expr:
        """
        Convert to a Name AST node.

        :return: Name AST node
        :rtype: dsl_nodes.Name
        """
        return dsl_nodes.Name(name=self.name)


def parse_expr_node_to_expr(node: dsl_nodes.Expr) -> Expr:
    """
    Parse an AST expression node into an Expr object.

    This function converts DSL expression nodes into the corresponding expression objects.

    :param node: AST expression node
    :type node: dsl_nodes.Expr
    :return: Corresponding expression object
    :rtype: Expr
    :raises TypeError: If the node type is not recognized

    Example::

        >>> ast_node = dsl_nodes.Integer(raw="42")
        >>> expr = parse_expr_node_to_expr(ast_node)
        >>> isinstance(expr, Integer)
        True
        >>> expr.value
        42
    """
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
        raise TypeError(f'Unknown node type - {node!r}.')  # pragma: no cover
