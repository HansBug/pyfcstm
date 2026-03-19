"""
Reverse conversion utilities from Z3 expressions to pyfcstm expressions.

This module provides :func:`z3_to_expr`, which performs structural parsing of
Z3 ASTs and converts them into canonical :class:`pyfcstm.model.expr.Expr`
objects.

Because several high-level pyfcstm expressions intentionally compile to the
same Z3 AST shape (for example ``floor(x)`` on integer inputs or ``abs(x)``
compiled as an ``If`` expression), this inverse is inherently many-to-one in
some cases. For such expressions, :func:`z3_to_expr` returns a stable canonical
representation rather than attempting out-of-band stateful recovery.
"""

from typing import Dict, Iterable, Optional, Union

import z3
from ..model.expr import (
    BinaryOp,
    Boolean,
    ConditionalOp,
    Expr,
    Float,
    Integer,
    UFunc,
    UnaryOp,
    Variable,
)


def _same_z3_expr(left: Union[z3.ArithRef, z3.BoolRef], right: Union[z3.ArithRef, z3.BoolRef]) -> bool:
    """
    Check whether two Z3 expressions are structurally identical.

    :param left: Left Z3 expression.
    :type left: Union[z3.ArithRef, z3.BoolRef]
    :param right: Right Z3 expression.
    :type right: Union[z3.ArithRef, z3.BoolRef]
    :return: Whether the two expressions share the same AST.
    :rtype: bool
    """
    return bool(left.eq(right))


def _is_numeric_literal(z3_expr: Union[z3.ArithRef, z3.BoolRef], value: int) -> bool:
    """
    Check whether a Z3 arithmetic expression is the exact numeric literal value.

    :param z3_expr: Z3 expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :param value: Expected numeric value.
    :type value: int
    :return: Whether the expression is exactly the requested literal.
    :rtype: bool
    """
    if z3.is_expr(z3_expr) and z3_expr.decl().kind() == z3.Z3_OP_UMINUS and z3_expr.num_args() == 1:
        return _is_numeric_literal(z3_expr.arg(0), -value)
    if z3.is_int_value(z3_expr):
        return z3_expr.as_long() == value
    if z3.is_rational_value(z3_expr):
        return z3_expr.numerator_as_long() == value and z3_expr.denominator_as_long() == 1
    return False


def _extract_zero_compare_operand(
    z3_expr: Union[z3.ArithRef, z3.BoolRef],
    direct_kind: int,
    reverse_kind: Optional[int] = None,
) -> Optional[Union[z3.ArithRef, z3.BoolRef]]:
    """
    Extract the non-zero operand from a comparison against numeric zero.

    :param z3_expr: Comparison expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :param direct_kind: Z3 operator kind for ``operand <op> 0``.
    :type direct_kind: int
    :param reverse_kind: Z3 operator kind for ``0 <op> operand``, defaults to ``direct_kind``
    :type reverse_kind: Optional[int]
    :return: Non-zero operand if the pattern matches, otherwise ``None``.
    :rtype: Optional[Union[z3.ArithRef, z3.BoolRef]]
    """
    reverse_kind = direct_kind if reverse_kind is None else reverse_kind

    if z3_expr.num_args() != 2:
        return None

    left_operand, right_operand = z3_expr.arg(0), z3_expr.arg(1)
    if z3_expr.decl().kind() == direct_kind and _is_numeric_literal(right_operand, 0):
        return left_operand
    if z3_expr.decl().kind() == reverse_kind and _is_numeric_literal(left_operand, 0):
        return right_operand
    return None


def _fold_binary_expr(op: str, items: Iterable[Union[z3.ArithRef, z3.BoolRef]]) -> Expr:
    """
    Fold a sequence of Z3 expressions into nested binary Expr nodes.

    :param op: Binary operator symbol.
    :type op: str
    :param items: Sequence of Z3 expressions.
    :type items: Iterable[Union[z3.ArithRef, z3.BoolRef]]
    :return: Nested binary expression.
    :rtype: Expr
    :raises ValueError: If no items are supplied.
    """
    iterator = iter(items)
    try:
        first_item = next(iterator)
    except StopIteration as err:
        raise ValueError('Cannot fold an empty Z3 expression sequence.') from err

    current = _z3_to_expr_impl(first_item)
    for item in iterator:
        current = BinaryOp(x=current, op=op, y=_z3_to_expr_impl(item))
    return current


def _z3_real_value_to_expr(z3_expr: z3.RatNumRef) -> Expr:
    """
    Convert a Z3 rational literal into a canonical pyfcstm expression.

    :param z3_expr: Z3 rational literal.
    :type z3_expr: z3.RatNumRef
    :return: Corresponding pyfcstm expression.
    :rtype: Expr
    """
    numerator = z3_expr.numerator_as_long()
    denominator = z3_expr.denominator_as_long()

    if denominator == 1:
        return Float(float(numerator))

    finite_denominator = denominator
    while finite_denominator % 2 == 0:
        finite_denominator //= 2
    while finite_denominator % 5 == 0:
        finite_denominator //= 5
    if finite_denominator == 1:
        return Float(float(numerator) / float(denominator))

    return BinaryOp(
        x=Integer(numerator),
        op='/',
        y=Integer(denominator),
    )


def _match_abs(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Optional[Expr]:
    """
    Match a canonical ``abs``-style Z3 encoding.

    :param z3_expr: Z3 expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Matched pyfcstm expression or ``None``.
    :rtype: Optional[Expr]
    """
    if z3_expr.decl().kind() != z3.Z3_OP_ITE or z3_expr.num_args() != 3:
        return None

    condition, true_branch, false_branch = (z3_expr.arg(i) for i in range(3))
    operand = _extract_zero_compare_operand(condition, z3.Z3_OP_GE, z3.Z3_OP_LE)
    if operand is None:
        return None
    if not _same_z3_expr(true_branch, operand):
        return None
    if false_branch.decl().kind() != z3.Z3_OP_UMINUS or false_branch.num_args() != 1:
        return None
    if not _same_z3_expr(false_branch.arg(0), operand):
        return None

    return UFunc(func='abs', x=_z3_to_expr_impl(operand))


def _match_sign(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Optional[Expr]:
    """
    Match a canonical ``sign``-style Z3 encoding.

    :param z3_expr: Z3 expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Matched pyfcstm expression or ``None``.
    :rtype: Optional[Expr]
    """
    if z3_expr.decl().kind() != z3.Z3_OP_ITE or z3_expr.num_args() != 3:
        return None

    eq_zero, zero_branch, inner_if = (z3_expr.arg(i) for i in range(3))
    if inner_if.decl().kind() != z3.Z3_OP_ITE or inner_if.num_args() != 3:
        return None

    operand = _extract_zero_compare_operand(eq_zero, z3.Z3_OP_EQ)
    if operand is None or not _is_numeric_literal(zero_branch, 0):
        return None

    gt_zero, one_branch, minus_one_branch = (inner_if.arg(i) for i in range(3))
    positive_operand = _extract_zero_compare_operand(gt_zero, z3.Z3_OP_GT, z3.Z3_OP_LT)
    if positive_operand is None or not _same_z3_expr(positive_operand, operand):
        return None
    if not _is_numeric_literal(one_branch, 1) or not _is_numeric_literal(minus_one_branch, -1):
        return None

    return UFunc(func='sign', x=_z3_to_expr_impl(operand))


def _match_trunc(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Optional[Expr]:
    """
    Match a canonical ``trunc``-style Z3 encoding.

    :param z3_expr: Z3 expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Matched pyfcstm expression or ``None``.
    :rtype: Optional[Expr]
    """
    if z3_expr.decl().kind() != z3.Z3_OP_ITE or z3_expr.num_args() != 3:
        return None

    condition, true_branch, false_branch = (z3_expr.arg(i) for i in range(3))
    operand = _extract_zero_compare_operand(condition, z3.Z3_OP_GE, z3.Z3_OP_LE)
    if operand is None:
        return None

    if true_branch.decl().kind() != z3.Z3_OP_TO_INT or true_branch.num_args() != 1:
        return None
    if not _same_z3_expr(true_branch.arg(0), operand):
        return None

    if false_branch.decl().kind() != z3.Z3_OP_UMINUS or false_branch.num_args() != 1:
        return None
    false_inner = false_branch.arg(0)
    if false_inner.decl().kind() != z3.Z3_OP_TO_INT or false_inner.num_args() != 1:
        return None
    neg_operand = false_inner.arg(0)
    if neg_operand.decl().kind() != z3.Z3_OP_UMINUS or neg_operand.num_args() != 1:
        return None
    if not _same_z3_expr(neg_operand.arg(0), operand):
        return None

    return UFunc(func='trunc', x=_z3_to_expr_impl(operand))


def _match_ceil(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Optional[Expr]:
    """
    Match a canonical ``ceil``-style Z3 encoding.

    :param z3_expr: Z3 expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Matched pyfcstm expression or ``None``.
    :rtype: Optional[Expr]
    """
    if z3_expr.decl().kind() != z3.Z3_OP_UMINUS or z3_expr.num_args() != 1:
        return None

    to_int_expr = z3_expr.arg(0)
    if to_int_expr.decl().kind() != z3.Z3_OP_TO_INT or to_int_expr.num_args() != 1:
        return None

    neg_operand = to_int_expr.arg(0)
    if neg_operand.decl().kind() != z3.Z3_OP_UMINUS or neg_operand.num_args() != 1:
        return None

    return UFunc(func='ceil', x=_z3_to_expr_impl(neg_operand.arg(0)))


def _match_round(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Optional[Expr]:
    """
    Match a canonical ``round``-style Z3 encoding.

    :param z3_expr: Z3 expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Matched pyfcstm expression or ``None``.
    :rtype: Optional[Expr]
    """
    if z3_expr.decl().kind() != z3.Z3_OP_TO_INT or z3_expr.num_args() != 1:
        return None

    add_expr = z3_expr.arg(0)
    if add_expr.decl().kind() != z3.Z3_OP_ADD or add_expr.num_args() != 2:
        return None

    left_operand, right_operand = add_expr.arg(0), add_expr.arg(1)
    if z3.is_rational_value(left_operand) and not z3.is_rational_value(right_operand):
        left_operand, right_operand = right_operand, left_operand
    if not z3.is_rational_value(right_operand):
        return None
    if right_operand.numerator_as_long() != 1 or right_operand.denominator_as_long() != 2:
        return None

    return UFunc(func='round', x=_z3_to_expr_impl(left_operand))


def _match_sqrt(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Optional[Expr]:
    """
    Match a canonical ``sqrt``-style Z3 encoding.

    :param z3_expr: Z3 expression to inspect.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Matched pyfcstm expression or ``None``.
    :rtype: Optional[Expr]
    """
    if z3_expr.decl().kind() != z3.Z3_OP_POWER or z3_expr.num_args() != 2:
        return None

    base_expr, exponent_expr = z3_expr.arg(0), z3_expr.arg(1)
    if not z3.is_rational_value(exponent_expr):
        return None
    if exponent_expr.numerator_as_long() != 1 or exponent_expr.denominator_as_long() != 2:
        return None

    return UFunc(func='sqrt', x=_z3_to_expr_impl(base_expr))


def _z3_to_expr_impl(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Expr:
    """
    Internal implementation for structural Z3 to Expr conversion.

    :param z3_expr: Z3 expression to convert.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Converted pyfcstm expression.
    :rtype: Expr
    :raises ValueError: If the Z3 expression shape is unsupported.
    """
    if z3.is_true(z3_expr):
        return Boolean(True)
    if z3.is_false(z3_expr):
        return Boolean(False)
    if z3.is_int_value(z3_expr):
        return Integer(z3_expr.as_long())
    if z3.is_rational_value(z3_expr):
        return _z3_real_value_to_expr(z3_expr)

    if not z3.is_expr(z3_expr):
        raise ValueError(f'Unsupported non-expression Z3 value: {z3_expr!r}')

    for matcher in (_match_abs, _match_sign, _match_trunc, _match_ceil, _match_round, _match_sqrt):
        matched_expr = matcher(z3_expr)
        if matched_expr is not None:
            return matched_expr

    if z3_expr.num_args() == 0 and z3_expr.decl().kind() == z3.Z3_OP_UNINTERPRETED:
        return Variable(z3_expr.decl().name())

    kind = z3_expr.decl().kind()
    args = [z3_expr.arg(i) for i in range(z3_expr.num_args())]

    if kind in (z3.Z3_OP_ADD, z3.Z3_OP_BADD):
        return _fold_binary_expr('+', args)
    if kind in (z3.Z3_OP_SUB, z3.Z3_OP_BSUB):
        return _fold_binary_expr('-', args)
    if kind in (z3.Z3_OP_MUL, z3.Z3_OP_BMUL):
        return _fold_binary_expr('*', args)
    if kind in (z3.Z3_OP_DIV, z3.Z3_OP_IDIV, z3.Z3_OP_BSDIV, z3.Z3_OP_BUDIV):
        return _fold_binary_expr('/', args)
    if kind in (z3.Z3_OP_MOD, z3.Z3_OP_REM, z3.Z3_OP_BSMOD, z3.Z3_OP_BSREM, z3.Z3_OP_BUREM):
        return _fold_binary_expr('%', args)
    if kind == z3.Z3_OP_POWER:
        return BinaryOp(x=_z3_to_expr_impl(args[0]), op='**', y=_z3_to_expr_impl(args[1]))
    if kind in (z3.Z3_OP_BAND,):
        return _fold_binary_expr('&', args)
    if kind in (z3.Z3_OP_BOR,):
        return _fold_binary_expr('|', args)
    if kind in (z3.Z3_OP_BXOR,):
        return _fold_binary_expr('^', args)
    if kind in (z3.Z3_OP_BSHL,):
        return _fold_binary_expr('<<', args)
    if kind in (z3.Z3_OP_BASHR, z3.Z3_OP_BLSHR):
        return _fold_binary_expr('>>', args)
    if kind == z3.Z3_OP_LT:
        return BinaryOp(x=_z3_to_expr_impl(args[0]), op='<', y=_z3_to_expr_impl(args[1]))
    if kind == z3.Z3_OP_LE:
        return BinaryOp(x=_z3_to_expr_impl(args[0]), op='<=', y=_z3_to_expr_impl(args[1]))
    if kind == z3.Z3_OP_GT:
        return BinaryOp(x=_z3_to_expr_impl(args[0]), op='>', y=_z3_to_expr_impl(args[1]))
    if kind == z3.Z3_OP_GE:
        return BinaryOp(x=_z3_to_expr_impl(args[0]), op='>=', y=_z3_to_expr_impl(args[1]))
    if kind == z3.Z3_OP_EQ:
        return BinaryOp(x=_z3_to_expr_impl(args[0]), op='==', y=_z3_to_expr_impl(args[1]))
    if kind == z3.Z3_OP_DISTINCT:
        if len(args) != 2:
            raise ValueError(
                f'Unsupported n-ary distinct expression for Expr conversion: {z3_expr.sexpr()}'
            )
        return BinaryOp(x=_z3_to_expr_impl(args[0]), op='!=', y=_z3_to_expr_impl(args[1]))
    if kind == z3.Z3_OP_AND:
        return _fold_binary_expr('&&', args)
    if kind == z3.Z3_OP_OR:
        return _fold_binary_expr('||', args)
    if kind == z3.Z3_OP_NOT:
        return UnaryOp(op='!', x=_z3_to_expr_impl(args[0]))
    if kind in (z3.Z3_OP_UMINUS, z3.Z3_OP_BNEG):
        return UnaryOp(op='-', x=_z3_to_expr_impl(args[0]))
    if kind in (z3.Z3_OP_BNOT,):
        return UnaryOp(op='~', x=_z3_to_expr_impl(args[0]))
    if kind == z3.Z3_OP_TO_INT:
        return UFunc(func='floor', x=_z3_to_expr_impl(args[0]))
    if kind == z3.Z3_OP_TO_REAL:
        return _z3_to_expr_impl(args[0])
    if kind == z3.Z3_OP_ITE:
        return ConditionalOp(
            cond=_z3_to_expr_impl(args[0]),
            if_true=_z3_to_expr_impl(args[1]),
            if_false=_z3_to_expr_impl(args[2]),
        )

    raise ValueError(
        f'Unsupported Z3 expression for Expr conversion: {z3_expr.sexpr()} '
        f'(kind={kind}, decl={z3_expr.decl().name()})'
    )


def z3_to_expr(z3_expr: Union[z3.ArithRef, z3.BoolRef]) -> Expr:
    """
    Convert a Z3 expression back into a pyfcstm :class:`Expr`.

    This function performs structural parsing and returns a canonical pyfcstm
    expression for supported Z3 AST shapes.

    :param z3_expr: Z3 expression to convert.
    :type z3_expr: Union[z3.ArithRef, z3.BoolRef]
    :return: Equivalent pyfcstm expression.
    :rtype: Expr
    :raises ValueError: If the Z3 AST shape is unsupported.

    Example::

        >>> import z3
        >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
        >>> from pyfcstm.solver.reverse_expr import z3_to_expr
        >>> z3_expr = z3.Int('x') + 5
        >>> expr = BinaryOp(x=Variable('x'), op='+', y=Integer(5))
        >>> recovered = z3_to_expr(z3_expr)
        >>> recovered == expr
        True
    """
    return _z3_to_expr_impl(z3_expr)
