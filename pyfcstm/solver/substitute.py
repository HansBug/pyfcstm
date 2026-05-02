"""
Substitution and literalization helpers for Z3 expressions.

This module provides a small substitution utility that mixes symbolic
replacement with aggressive literal folding. It supports two layers:

* :func:`_substitute_and_literalize_expr` - Internal helper for a single Z3 expression
* :func:`substitute_and_literalize` - Public recursive helper for Z3 expressions and containers

The substitution dictionary is keyed by variable name. Each value may be:

* A Python literal (``bool``, ``int``, or ``float``)
* A Z3 expression, which may itself reference other substitution entries

After substitution, the helper simplifies the expression tree bottom-up. If the
final result has no remaining unknowns, it is converted to a Python literal.
Otherwise, a simplified Z3 expression is returned with ground subtrees folded as
much as Z3 can prove locally.

Example::

    >>> import z3
    >>> from pyfcstm.solver.substitute import substitute_and_literalize
    >>> x = z3.Int('x')
    >>> y = z3.Int('y')
    >>> substitute_and_literalize(x + 3, {'x': y + 1, 'y': 2})
    6
    >>> substitute_and_literalize({'expr': x + 2, 'raw': 'ok'}, {'x': 5})
    {'expr': 7, 'raw': 'ok'}
"""

from fractions import Fraction
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import z3

LiteralValue = Union[bool, int, float]
SubstitutionValue = Union[LiteralValue, z3.ExprRef]

_SIMPLIFY_KWARGS = {
    'som': True,
    'mul_to_power': True,
    'arith_lhs': True,
    'pull_cheap_ite': True,
    'push_ite_arith': True,
}


def _is_python_literal(value: Any) -> bool:
    """Return whether the object is a supported Python literal for substitution."""
    return isinstance(value, bool) or isinstance(value, (int, float))


def _sort_label(sort: z3.SortRef) -> str:
    """Return a readable label for a Z3 sort."""
    return sort.sexpr()


def _is_bool_sort(sort: z3.SortRef) -> bool:
    """Return whether the sort is Bool."""
    return sort.kind() == z3.Z3_BOOL_SORT


def _is_int_sort(sort: z3.SortRef) -> bool:
    """Return whether the sort is Int."""
    return sort.kind() == z3.Z3_INT_SORT


def _is_real_sort(sort: z3.SortRef) -> bool:
    """Return whether the sort is Real."""
    return sort.kind() == z3.Z3_REAL_SORT


def _is_bv_sort(sort: z3.SortRef) -> bool:
    """Return whether the sort is BitVec."""
    return sort.kind() == z3.Z3_BV_SORT


def _is_arith_sort(sort: z3.SortRef) -> bool:
    """Return whether the sort is Int or Real."""
    return _is_int_sort(sort) or _is_real_sort(sort)


def _basic_simplify(expr: z3.ExprRef) -> z3.ExprRef:
    """Run Z3 simplification with the local preferred options."""
    return z3.simplify(expr, **_SIMPLIFY_KWARGS)


def _expr_hash(expr: z3.ExprRef) -> int:
    """Return a stable structural hash for bucketing equivalent expressions."""
    return expr.hash()


def _find_equivalent_index(
    expr: z3.ExprRef,
    items: List[z3.ExprRef],
    buckets: Dict[int, List[int]],
) -> Optional[int]:
    """Find the first structurally equivalent expression index in ``items``."""
    for index in buckets.get(_expr_hash(expr), ()):
        if items[index].eq(expr):
            return index
    return None


def _append_equivalent_item(
    expr: z3.ExprRef,
    items: List[z3.ExprRef],
    buckets: Dict[int, List[int]],
) -> int:
    """Append one expression to an ordered equivalence bucket list."""
    index = len(items)
    items.append(expr)
    buckets.setdefault(_expr_hash(expr), []).append(index)
    return index


def _make_zero(sort: z3.SortRef) -> z3.ExprRef:
    """Create a zero literal matching the given sort."""
    if _is_int_sort(sort):
        return z3.IntVal(0)
    if _is_real_sort(sort):
        return z3.RealVal(0)
    if _is_bv_sort(sort):
        return z3.BitVecVal(0, sort.size())
    raise TypeError(f"Unsupported zero sort {_sort_label(sort)}.")


def _try_arith_fraction(expr: z3.ExprRef) -> Optional[Fraction]:
    """Try to evaluate one ground arithmetic expression into a fraction."""
    if z3.is_int_value(expr):
        return Fraction(expr.as_long(), 1)
    if z3.is_rational_value(expr):
        return Fraction(expr.numerator_as_long(), expr.denominator_as_long())
    if not z3.is_app(expr):
        return None

    kind = expr.decl().kind()
    children = expr.children()
    if kind == z3.Z3_OP_UMINUS and len(children) == 1:
        value = _try_arith_fraction(children[0])
        return None if value is None else -value
    if kind == z3.Z3_OP_ADD:
        total = Fraction(0, 1)
        for child in children:
            value = _try_arith_fraction(child)
            if value is None:
                return None
            total += value
        return total
    if kind == z3.Z3_OP_SUB and children:
        value = _try_arith_fraction(children[0])
        if value is None:
            return None
        for child in children[1:]:
            child_value = _try_arith_fraction(child)
            if child_value is None:
                return None
            value -= child_value
        return value
    if kind == z3.Z3_OP_MUL:
        total = Fraction(1, 1)
        for child in children:
            value = _try_arith_fraction(child)
            if value is None:
                return None
            total *= value
        return total
    if kind == z3.Z3_OP_DIV and len(children) == 2:
        numerator = _try_arith_fraction(children[0])
        denominator = _try_arith_fraction(children[1])
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator
    if kind == z3.Z3_OP_TO_REAL and len(children) == 1:
        return _try_arith_fraction(children[0])
    if kind == z3.Z3_OP_TO_INT and len(children) == 1:
        value = _try_arith_fraction(children[0])
        if value is None:
            return None
        return Fraction(math.floor(value), 1)
    return None


def _try_bool_value(expr: z3.ExprRef) -> Optional[bool]:
    """Try to evaluate one ground boolean expression into a Python bool."""
    if z3.is_true(expr):
        return True
    if z3.is_false(expr):
        return False
    return None


def _normalize_not(expr: z3.ExprRef) -> z3.ExprRef:
    """Normalize a boolean negation with only local linear-time rules."""
    child = expr.children()[0]
    child_value = _try_bool_value(child)
    if child_value is not None:
        return z3.BoolVal(not child_value)
    if z3.is_app(child) and child.decl().kind() == z3.Z3_OP_NOT:
        return child.children()[0]
    return expr


def _compare_ground_literals(left: z3.ExprRef, right: z3.ExprRef) -> Optional[int]:
    """Compare two ground arithmetic or bitvector literals."""
    left_fraction = _try_arith_fraction(left)
    right_fraction = _try_arith_fraction(right)
    if left_fraction is not None and right_fraction is not None:
        if left_fraction < right_fraction:
            return -1
        if left_fraction > right_fraction:
            return 1
        return 0
    if z3.is_bv_value(left) and z3.is_bv_value(right):
        left_value = left.as_long()
        right_value = right.as_long()
        if left_value < right_value:
            return -1
        if left_value > right_value:
            return 1
        return 0
    return None


def _fold_nonfamily_root(expr: z3.ExprRef) -> z3.ExprRef:
    """Fold one non-family expression root using local linear-time rules."""
    if not z3.is_app(expr):
        return expr

    kind = expr.decl().kind()
    children = expr.children()
    if kind == z3.Z3_OP_NOT and len(children) == 1:
        return _normalize_not(expr)
    if kind == z3.Z3_OP_ITE and len(children) == 3:
        condition, when_true, when_false = children
        condition_value = _try_bool_value(condition)
        if condition_value is True:
            return when_true
        if condition_value is False:
            return when_false
        if when_true.eq(when_false):
            return when_true
        return expr
    if kind == z3.Z3_OP_EQ and len(children) == 2:
        left, right = children
        if left.eq(right):
            return z3.BoolVal(True)
        comparison = _compare_ground_literals(left, right)
        if comparison is not None:
            return z3.BoolVal(comparison == 0)
        left_bool = _try_bool_value(left)
        right_bool = _try_bool_value(right)
        if left_bool is not None and right_bool is not None:
            return z3.BoolVal(left_bool == right_bool)
        return expr
    if kind == z3.Z3_OP_DISTINCT and len(children) == 2:
        left, right = children
        if left.eq(right):
            return z3.BoolVal(False)
        comparison = _compare_ground_literals(left, right)
        if comparison is not None:
            return z3.BoolVal(comparison != 0)
        left_bool = _try_bool_value(left)
        right_bool = _try_bool_value(right)
        if left_bool is not None and right_bool is not None:
            return z3.BoolVal(left_bool != right_bool)
        return expr
    if kind in (z3.Z3_OP_LE, z3.Z3_OP_LT, z3.Z3_OP_GE, z3.Z3_OP_GT) and len(children) == 2:
        comparison = _compare_ground_literals(children[0], children[1])
        if comparison is None:
            return expr
        if kind == z3.Z3_OP_LE:
            return z3.BoolVal(comparison <= 0)
        if kind == z3.Z3_OP_LT:
            return z3.BoolVal(comparison < 0)
        if kind == z3.Z3_OP_GE:
            return z3.BoolVal(comparison >= 0)
        return z3.BoolVal(comparison > 0)
    if kind == z3.Z3_OP_TO_REAL and len(children) == 1:
        value = _try_arith_fraction(children[0])
        if value is not None:
            return _fraction_to_arith_value(value, z3.RealSort())
        return expr
    if kind == z3.Z3_OP_TO_INT and len(children) == 1:
        value = _try_arith_fraction(children[0])
        if value is not None:
            return z3.IntVal(math.floor(value))
        return expr
    return expr


def _is_ground_arith_numeral(expr: z3.ExprRef) -> bool:
    """Return whether the expression is an Int or Real numeral."""
    return _try_arith_fraction(expr) is not None


def _arith_numeral_to_fraction(expr: z3.ExprRef) -> Fraction:
    """Convert an arithmetic Z3 numeral to :class:`fractions.Fraction`."""
    value = _try_arith_fraction(expr)
    if value is None:
        raise TypeError(f"Expression {expr!r} is not an arithmetic numeral.")
    return value


def _fraction_to_arith_value(value: Fraction, sort: z3.SortRef) -> z3.ExprRef:
    """Convert a fraction into an Int or Real Z3 literal."""
    if _is_int_sort(sort):
        if value.denominator != 1:
            raise TypeError(
                f"Cannot create Int literal from non-integer fraction {value!r}."
            )
        return z3.IntVal(value.numerator)
    if _is_real_sort(sort):
        if value.denominator == 1:
            return z3.RealVal(value.numerator)
        return z3.RealVal(f"{value.numerator}/{value.denominator}")
    raise TypeError(f"Unsupported arithmetic sort {_sort_label(sort)}.")


def _flatten_same_kind(expr: z3.ExprRef, kind: int) -> List[z3.ExprRef]:
    """Flatten nested applications of the same operator kind."""
    if z3.is_app(expr) and expr.decl().kind() == kind:
        items: List[z3.ExprRef] = []
        for child in expr.children():
            items.extend(_flatten_same_kind(child, kind))
        return items
    return [expr]


def _build_sorted_product(factors: List[z3.ExprRef]) -> z3.ExprRef:
    """Build a left-associated product from non-numeric factors in encounter order."""
    result = factors[0]
    for factor in factors[1:]:
        result = result * factor
    return result


def _build_bool_xor_chain(args: List[z3.ExprRef]) -> z3.ExprRef:
    """Build a left-associated boolean XOR chain."""
    result = args[0]
    for arg in args[1:]:
        result = z3.Xor(result, arg)
    return result


def _extract_additive_term(expr: z3.ExprRef) -> Tuple[Fraction, Union[z3.ExprRef, None]]:
    """
    Extract a scalar coefficient and symbolic core from one additive term.

    The function pulls numeric multipliers out of product terms. Nonlinear cores
    are kept as opaque symbolic factors.
    """
    value = _try_arith_fraction(expr)
    if value is not None:
        return value, None

    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_UMINUS:
        coeff, core = _extract_additive_term(expr.children()[0])
        return -coeff, core

    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_MUL:
        coeff = Fraction(1, 1)
        factors: List[z3.ExprRef] = []
        for child in expr.children():
            child_value = _try_arith_fraction(child)
            if child_value is not None:
                coeff *= child_value
            else:
                factors.append(child)

        if not factors:  # pragma: no cover
            return coeff, None

        core = factors[0] if len(factors) == 1 else _build_sorted_product(factors)
        return coeff, core

    if (
        _is_real_sort(expr.sort())
        and z3.is_app(expr)
        and expr.decl().kind() == z3.Z3_OP_DIV
    ):
        numerator, denominator = expr.children()
        denominator_value = _try_arith_fraction(denominator)
        if denominator_value not in (None, 0):
            coeff, core = _extract_additive_term(numerator)
            return coeff / denominator_value, core

    return Fraction(1, 1), expr


def _collect_additive_terms(
    expr: z3.ExprRef,
    sign: int,
    representatives: List[z3.ExprRef],
    coefficients: List[Fraction],
    buckets: Dict[int, List[int]],
) -> Fraction:
    """Collect a flattened additive linear form and return the constant part."""
    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_ADD:
        constant = Fraction(0, 1)
        for child in expr.children():
            constant += _collect_additive_terms(
                child,
                sign,
                representatives,
                coefficients,
                buckets,
            )
        return constant
    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_SUB:
        children = expr.children()
        constant = _collect_additive_terms(
            children[0],
            sign,
            representatives,
            coefficients,
            buckets,
        )
        for child in children[1:]:
            constant += _collect_additive_terms(
                child,
                -sign,
                representatives,
                coefficients,
                buckets,
            )
        return constant
    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_UMINUS:
        return _collect_additive_terms(
            expr.children()[0],
            -sign,
            representatives,
            coefficients,
            buckets,
        )

    coeff, core = _extract_additive_term(expr)
    coeff *= sign
    if core is None:
        return coeff

    index = _find_equivalent_index(core, representatives, buckets)
    if index is None:
        _append_equivalent_item(core, representatives, buckets)
        coefficients.append(coeff)
    else:
        coefficients[index] += coeff
    return Fraction(0, 1)


def _build_linear_expr(sort: z3.SortRef, expr: z3.ExprRef) -> z3.ExprRef:
    """Rebuild an arithmetic additive expression in a compact deterministic form."""
    representatives: List[z3.ExprRef] = []
    coefficients: List[Fraction] = []
    buckets: Dict[int, List[int]] = {}
    constant = _collect_additive_terms(expr, 1, representatives, coefficients, buckets)

    positive_terms: List[z3.ExprRef] = []
    negative_terms: List[z3.ExprRef] = []
    for term_expr, coeff in zip(representatives, coefficients):
        if coeff == 0:  # pragma: no cover
            continue

        abs_coeff = abs(coeff)
        if abs_coeff != 1:
            term_expr = _fraction_to_arith_value(abs_coeff, sort) * term_expr

        if coeff > 0:
            positive_terms.append(term_expr)
        else:
            negative_terms.append(term_expr)

    remaining_constant = constant
    result: Union[z3.ExprRef, None] = None

    if positive_terms:
        result = positive_terms[0]
        for term in positive_terms[1:]:
            result = result + term
    elif remaining_constant != 0:
        if remaining_constant > 0:
            result = _fraction_to_arith_value(remaining_constant, sort)
        else:
            result = -_fraction_to_arith_value(-remaining_constant, sort)
        remaining_constant = Fraction(0, 1)
    elif negative_terms:
        result = -negative_terms[0]
        negative_terms = negative_terms[1:]
    else:
        return _make_zero(sort)

    for term in negative_terms:
        result = result - term

    if remaining_constant > 0:
        result = result + _fraction_to_arith_value(remaining_constant, sort)
    elif remaining_constant < 0:
        result = result - _fraction_to_arith_value(-remaining_constant, sort)

    return result


def _extract_product_scalars(
    expr: z3.ExprRef,
    allow_numeric_division: bool,
) -> Tuple[Fraction, List[z3.ExprRef]]:
    """
    Extract safe scalar factors from a product-like expression.

    Numeric division is only pulled across the top-level core when the divisor is
    already a ground numeral. Symbolic division nodes remain opaque factors.
    """
    value = _try_arith_fraction(expr)
    if value is not None:
        return value, []

    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_UMINUS:
        scalar, cores = _extract_product_scalars(expr.children()[0], allow_numeric_division)
        return -scalar, cores

    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_MUL:
        scalar = Fraction(1, 1)
        cores: List[z3.ExprRef] = []
        for child in expr.children():
            child_scalar, child_cores = _extract_product_scalars(child, allow_numeric_division)
            scalar *= child_scalar
            cores.extend(child_cores)
        return scalar, cores

    if allow_numeric_division and z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_DIV:
        numerator, denominator = expr.children()
        denominator_value = _try_arith_fraction(denominator)
        if denominator_value not in (None, 0):
            scalar, cores = _extract_product_scalars(numerator, allow_numeric_division)
            return scalar / denominator_value, cores

    return Fraction(1, 1), [expr]


def _build_product_expr(sort: z3.SortRef, expr: z3.ExprRef) -> z3.ExprRef:
    """Rebuild a multiplicative expression with compact scalar factors."""
    scalar, cores = _extract_product_scalars(
        expr=expr,
        allow_numeric_division=_is_real_sort(sort),
    )
    if scalar == 0:
        return _make_zero(sort)

    core_expr: Union[z3.ExprRef, None] = None
    if cores:
        core_expr = cores[0] if len(cores) == 1 else _build_sorted_product(cores)

    if core_expr is None:
        return _fraction_to_arith_value(scalar, sort)
    if scalar == 1:
        return core_expr
    if scalar == -1:
        return -core_expr
    return _fraction_to_arith_value(scalar, sort) * core_expr


def _normalize_bool_family(expr: z3.ExprRef) -> z3.ExprRef:
    """Normalize boolean associative families such as And, Or, and Xor."""
    if not _is_bool_sort(expr.sort()) or not z3.is_app(expr):
        return expr

    kind = expr.decl().kind()
    if kind in (z3.Z3_OP_AND, z3.Z3_OP_OR):
        identity = True if kind == z3.Z3_OP_AND else False
        annihilator = False if kind == z3.Z3_OP_AND else True
        args: List[z3.ExprRef] = []
        positive_args: List[z3.ExprRef] = []
        positive_buckets: Dict[int, List[int]] = {}
        negative_bases: List[z3.ExprRef] = []
        negative_buckets: Dict[int, List[int]] = {}

        for arg in _flatten_same_kind(expr, kind):
            if z3.is_true(arg):
                if not identity:
                    return z3.BoolVal(True)
                continue  # pragma: no cover
            if z3.is_false(arg):
                if identity:
                    return z3.BoolVal(False)
                continue  # pragma: no cover

            if z3.is_app(arg) and arg.decl().kind() == z3.Z3_OP_NOT:
                base = arg.children()[0]
                if _find_equivalent_index(base, positive_args, positive_buckets) is not None:
                    return z3.BoolVal(annihilator)
                if _find_equivalent_index(base, negative_bases, negative_buckets) is None:
                    _append_equivalent_item(base, negative_bases, negative_buckets)
                    args.append(arg)
            else:
                if _find_equivalent_index(arg, negative_bases, negative_buckets) is not None:
                    return z3.BoolVal(annihilator)
                if _find_equivalent_index(arg, positive_args, positive_buckets) is None:
                    _append_equivalent_item(arg, positive_args, positive_buckets)
                    args.append(arg)
        if not args:
            return z3.BoolVal(identity)
        if len(args) == 1:
            return args[0]
        return z3.And(*args) if kind == z3.Z3_OP_AND else z3.Or(*args)

    if kind == z3.Z3_OP_XOR:
        parity = 0
        entries: List[z3.ExprRef] = []
        active: List[bool] = []
        buckets: Dict[int, List[int]] = {}
        for arg in _flatten_same_kind(expr, kind):
            if z3.is_true(arg):
                parity ^= 1
                continue
            if z3.is_false(arg):
                continue

            index = _find_equivalent_index(arg, entries, buckets)
            if index is None:
                _append_equivalent_item(arg, entries, buckets)
                active.append(True)
            else:
                active[index] = not active[index]

        args = [
            item
            for item, is_active in zip(entries, active)
            if is_active
        ]
        if not args:
            base = z3.BoolVal(False)
        elif len(args) == 1:
            base = args[0]
        else:
            base = _build_bool_xor_chain(args)

        if parity:
            return _normalize_not(z3.Not(base))
        return base

    return expr


def _normalize_bv_bitwise_family(expr: z3.ExprRef) -> z3.ExprRef:
    """Normalize associative bitvector bitwise families."""
    if not _is_bv_sort(expr.sort()) or not z3.is_app(expr):
        return expr

    kind = expr.decl().kind()
    width = expr.sort().size()
    all_ones = (1 << width) - 1

    if kind in (z3.Z3_OP_BAND, z3.Z3_OP_BOR):
        literal = all_ones if kind == z3.Z3_OP_BAND else 0
        identity = all_ones if kind == z3.Z3_OP_BAND else 0
        annihilator = 0 if kind == z3.Z3_OP_BAND else all_ones
        args: List[z3.ExprRef] = []
        positive_args: List[z3.ExprRef] = []
        positive_buckets: Dict[int, List[int]] = {}
        negative_bases: List[z3.ExprRef] = []
        negative_buckets: Dict[int, List[int]] = {}

        for arg in _flatten_same_kind(expr, kind):
            if z3.is_bv_value(arg):
                value = arg.as_long()
                literal = (literal & value) if kind == z3.Z3_OP_BAND else (literal | value)
                if literal == annihilator:
                    return z3.BitVecVal(annihilator, width)
                continue  # pragma: no cover

            if z3.is_app(arg) and arg.decl().kind() == z3.Z3_OP_BNOT:
                base = arg.children()[0]
                if _find_equivalent_index(base, positive_args, positive_buckets) is not None:
                    return z3.BitVecVal(annihilator, width)
                if _find_equivalent_index(base, negative_bases, negative_buckets) is None:
                    _append_equivalent_item(base, negative_bases, negative_buckets)
                    args.append(arg)
            else:
                if _find_equivalent_index(arg, negative_bases, negative_buckets) is not None:
                    return z3.BitVecVal(annihilator, width)
                if _find_equivalent_index(arg, positive_args, positive_buckets) is None:
                    _append_equivalent_item(arg, positive_args, positive_buckets)
                    args.append(arg)
        if literal != identity or not args:
            args.append(z3.BitVecVal(literal, width))

        result = args[0]
        for arg in args[1:]:
            result = (result & arg) if kind == z3.Z3_OP_BAND else (result | arg)
        return result

    if kind == z3.Z3_OP_BXOR:
        literal = 0
        entries: List[z3.ExprRef] = []
        active: List[bool] = []
        buckets: Dict[int, List[int]] = {}
        for arg in _flatten_same_kind(expr, kind):
            if z3.is_bv_value(arg):
                literal ^= arg.as_long()
                literal &= all_ones
                continue

            index = _find_equivalent_index(arg, entries, buckets)
            if index is None:
                _append_equivalent_item(arg, entries, buckets)
                active.append(True)
            else:
                active[index] = not active[index]

        args = [
            item
            for item, is_active in zip(entries, active)
            if is_active
        ]
        if literal != 0 or not args:
            args.append(z3.BitVecVal(literal, width))

        result = args[0]
        for arg in args[1:]:
            result = result ^ arg
        return result

    return expr


def _normalize_arith_family(expr: z3.ExprRef) -> z3.ExprRef:
    """Normalize arithmetic additive and multiplicative families."""
    if not _is_arith_sort(expr.sort()) or not z3.is_app(expr):
        return expr

    kind = expr.decl().kind()
    if kind in (z3.Z3_OP_ADD, z3.Z3_OP_SUB, z3.Z3_OP_UMINUS):
        return _build_linear_expr(expr.sort(), expr)
    if kind == z3.Z3_OP_MUL:
        return _build_product_expr(expr.sort(), expr)
    if _is_real_sort(expr.sort()) and kind == z3.Z3_OP_DIV:
        return _build_product_expr(expr.sort(), expr)
    return expr


def _normalize_expr_once(expr: z3.ExprRef) -> z3.ExprRef:
    """Apply one round of family-based normalization to an expression."""
    for normalizer in (
        _normalize_bool_family,
        _normalize_bv_bitwise_family,
        _normalize_arith_family,
    ):
        normalized = normalizer(expr)
        if not normalized.eq(expr):
            return normalized
    return expr


def _expr_family(expr: z3.ExprRef) -> Union[str, None]:
    """Return the custom normalization family label for the expression root."""
    if not z3.is_app(expr):
        return None

    kind = expr.decl().kind()
    if _is_bool_sort(expr.sort()) and kind in (z3.Z3_OP_AND, z3.Z3_OP_OR, z3.Z3_OP_XOR):
        return f'bool:{kind}'
    if _is_bv_sort(expr.sort()) and kind in (z3.Z3_OP_BAND, z3.Z3_OP_BOR, z3.Z3_OP_BXOR):
        return f'bv:{kind}'
    if _is_arith_sort(expr.sort()) and kind in (z3.Z3_OP_ADD, z3.Z3_OP_SUB, z3.Z3_OP_UMINUS, z3.Z3_OP_MUL):
        return 'arith:add' if kind in (z3.Z3_OP_ADD, z3.Z3_OP_SUB, z3.Z3_OP_UMINUS) else 'arith:mul'
    if _is_real_sort(expr.sort()) and kind == z3.Z3_OP_DIV:
        return 'arith:mul'
    return None


def _normalize_symbolic_root(expr: z3.ExprRef) -> z3.ExprRef:
    """Normalize only the current expression root."""
    normalized = _normalize_expr_once(expr)
    if not normalized.eq(expr):
        return normalized
    return expr


def _python_literal_to_z3(value: LiteralValue, target_sort: z3.SortRef) -> z3.ExprRef:
    """
    Convert a Python literal into a Z3 literal matching ``target_sort``.

    :param value: Python literal to convert
    :type value: LiteralValue
    :param target_sort: Target Z3 sort
    :type target_sort: z3.SortRef
    :return: Converted Z3 literal
    :rtype: z3.ExprRef
    :raises TypeError: If the literal cannot be converted to the requested sort
    """
    if _is_bool_sort(target_sort):
        if not isinstance(value, bool):
            raise TypeError(
                f"Cannot substitute Python value {value!r} into Bool variable. "
                f"Expected a bool literal."
            )
        return z3.BoolVal(value)

    if isinstance(value, bool):
        raise TypeError(
            f"Cannot substitute Python bool literal {value!r} into non-Bool sort "
            f"{_sort_label(target_sort)}."
        )

    if _is_int_sort(target_sort):
        if not isinstance(value, int):
            raise TypeError(
                f"Cannot substitute Python value {value!r} into Int variable. "
                f"Expected an int literal."
            )
        return z3.IntVal(value)

    if _is_real_sort(target_sort):
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"Cannot substitute Python value {value!r} into Real variable. "
                f"Expected an int or float literal."
            )
        return z3.RealVal(value)

    if _is_bv_sort(target_sort):
        if not isinstance(value, int):
            raise TypeError(
                f"Cannot substitute Python value {value!r} into BitVec variable. "
                f"Expected an int literal."
            )
        return z3.BitVecVal(value, target_sort.size())

    raise TypeError(
        f"Cannot substitute Python literal into unsupported Z3 sort {_sort_label(target_sort)}."
    )


def _coerce_z3_expr_to_sort(expr: z3.ExprRef, target_sort: z3.SortRef) -> z3.ExprRef:
    """
    Coerce a Z3 expression to the required sort when a safe conversion exists.

    :param expr: Z3 expression to coerce
    :type expr: z3.ExprRef
    :param target_sort: Target Z3 sort
    :type target_sort: z3.SortRef
    :return: Coerced Z3 expression
    :rtype: z3.ExprRef
    :raises TypeError: If no safe coercion exists
    """
    expr_sort = expr.sort()
    if expr_sort.eq(target_sort):
        return expr

    if _is_int_sort(expr_sort) and _is_real_sort(target_sort):
        return z3.ToReal(expr)

    raise TypeError(
        f"Cannot substitute Z3 expression of sort {_sort_label(expr_sort)} into "
        f"target sort {_sort_label(target_sort)}."
    )


def _contains_unknowns(
    expr: z3.ExprRef,
    seen: Optional[Dict[int, bool]] = None,
) -> bool:
    """
    Check whether the expression still contains uninterpreted unknown symbols.

    :param expr: Z3 expression to inspect
    :type expr: z3.ExprRef
    :return: Whether any unknown symbol remains
    :rtype: bool
    """
    if seen is None:
        seen = {}

    expr_id = expr.get_id()
    if expr_id in seen:
        return seen[expr_id]

    if z3.is_const(expr) and expr.decl().kind() == z3.Z3_OP_UNINTERPRETED:
        seen[expr_id] = True
        return True

    if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_UNINTERPRETED and expr.num_args() > 0:
        seen[expr_id] = True
        return True

    result = any(_contains_unknowns(child, seen) for child in expr.children())
    seen[expr_id] = result
    return result


def _algebraic_to_float(expr: z3.AlgebraicNumRef) -> float:
    """Convert a Z3 algebraic number to a Python float approximation."""
    return float(expr.approx(20).as_decimal(20).rstrip('?'))


def _z3_expr_to_python_literal(expr: z3.ExprRef) -> LiteralValue:
    """
    Convert a fully-ground Z3 expression into a Python literal.

    :param expr: Ground Z3 expression
    :type expr: z3.ExprRef
    :return: Python literal value
    :rtype: LiteralValue
    :raises TypeError: If the expression does not simplify to a supported literal
    """
    if z3.is_true(expr):
        return True
    if z3.is_false(expr):
        return False
    if z3.is_int_value(expr):
        return expr.as_long()
    if z3.is_rational_value(expr):
        numerator = expr.numerator_as_long()
        denominator = expr.denominator_as_long()
        if denominator == 1:
            return numerator
        return float(numerator) / float(denominator)
    if z3.is_bv_value(expr):
        return expr.as_long()
    if z3.is_algebraic_value(expr):
        return _algebraic_to_float(expr)

    arith_value = _try_arith_fraction(expr)
    if arith_value is not None:
        if arith_value.denominator == 1:
            return arith_value.numerator
        return float(arith_value.numerator) / float(arith_value.denominator)

    folded = _fold_nonfamily_root(expr)
    if not folded.eq(expr):
        return _z3_expr_to_python_literal(folded)

    simplified = _basic_simplify(expr)
    if not simplified.eq(expr):
        return _z3_expr_to_python_literal(simplified)

    raise TypeError(
        f"Cannot convert simplified Z3 expression {expr!r} to a Python literal."
    )


def _resolve_substitution_value(
    name: str,
    target_sort: z3.SortRef,
    substitutions: Dict[str, SubstitutionValue],
    visiting: Set[str],
    cache: Dict[Tuple[str, str], z3.ExprRef],
    expr_cache: Dict[Tuple[int, Optional[str]], z3.ExprRef],
) -> z3.ExprRef:
    """
    Resolve one substitution entry into a Z3 expression matching ``target_sort``.

    :param name: Variable name being substituted
    :type name: str
    :param target_sort: Sort required by the original variable occurrence
    :type target_sort: z3.SortRef
    :param substitutions: User substitution mapping
    :type substitutions: Dict[str, SubstitutionValue]
    :param visiting: Current recursion stack for cycle protection
    :type visiting: Set[str]
    :param cache: Resolved substitution cache
    :type cache: Dict[Tuple[str, str], z3.ExprRef]
    :return: Resolved Z3 expression
    :rtype: z3.ExprRef
    """
    cache_key = (name, target_sort.sexpr())
    if cache_key in cache:
        return cache[cache_key]

    if name in visiting:
        return z3.Const(name, target_sort)

    value = substitutions[name]
    if _is_python_literal(value):
        resolved = _python_literal_to_z3(value, target_sort)
    elif z3.is_expr(value):
        visiting.add(name)
        try:
            resolved = _substitute_expr_to_z3(
                value,
                substitutions,
                visiting,
                cache,
                expr_cache=expr_cache,
            )
        finally:
            visiting.remove(name)
        resolved = _coerce_z3_expr_to_sort(resolved, target_sort)
    else:
        raise TypeError(
            f"Unsupported substitution value type for variable {name!r}: "
            f"{type(value).__name__}."
        )

    cache[cache_key] = resolved
    return resolved


def _substitute_expr_to_z3(
    expr: z3.ExprRef,
    substitutions: Dict[str, SubstitutionValue],
    visiting: Set[str],
    cache: Dict[Tuple[str, str], z3.ExprRef],
    parent_family: Union[str, None] = None,
    expr_cache: Optional[Dict[Tuple[int, Optional[str]], z3.ExprRef]] = None,
) -> z3.ExprRef:
    """
    Substitute known variables inside ``expr`` and simplify bottom-up.

    :param expr: Z3 expression to process
    :type expr: z3.ExprRef
    :param substitutions: User substitution mapping
    :type substitutions: Dict[str, SubstitutionValue]
    :param visiting: Current recursion stack for cycle protection
    :type visiting: Set[str]
    :param cache: Resolved substitution cache
    :type cache: Dict[Tuple[str, str], z3.ExprRef]
    :return: Simplified Z3 expression
    :rtype: z3.ExprRef
    """
    if expr_cache is None:
        expr_cache = {}

    cache_key = (expr.get_id(), parent_family)
    if cache_key in expr_cache:
        return expr_cache[cache_key]

    if z3.is_const(expr) and expr.decl().kind() == z3.Z3_OP_UNINTERPRETED:
        name = str(expr)
        if name in substitutions:
            result = _resolve_substitution_value(
                name=name,
                target_sort=expr.sort(),
                substitutions=substitutions,
                visiting=visiting,
                cache=cache,
                expr_cache=expr_cache,
            )
        else:
            result = expr
        expr_cache[cache_key] = result
        return result

    children = expr.children()
    if not children:
        expr_cache[cache_key] = expr
        return expr

    new_children = [
        _substitute_expr_to_z3(
            child,
            substitutions,
            visiting,
            cache,
            parent_family=_expr_family(expr),
            expr_cache=expr_cache,
        )
        for child in children
    ]
    replacement_pairs = [
        (old_child, new_child)
        for old_child, new_child in zip(children, new_children)
        if not old_child.eq(new_child)
    ]
    if replacement_pairs:
        expr = z3.substitute(expr, *replacement_pairs)

    family = _expr_family(expr)
    if family:
        if family != parent_family:
            expr = _normalize_symbolic_root(expr)
        expr_cache[cache_key] = expr
        return expr

    expr = _fold_nonfamily_root(expr)
    family = _expr_family(expr)
    if family and family != parent_family:
        expr = _normalize_symbolic_root(expr)

    expr_cache[cache_key] = expr
    return expr


def _substitute_and_literalize_expr(
    x: z3.ExprRef,
    substitutions: Dict[str, SubstitutionValue],
) -> Union[LiteralValue, z3.ExprRef]:
    """
    Substitute named values into one Z3 expression and literalize what becomes ground.

    Substitution values may be Python literals or Z3 expressions. Replacement Z3
    expressions are recursively expanded with the same substitution mapping. The
    result is simplified bottom-up; if no unknowns remain, a Python literal is
    returned directly.

    :param x: Z3 expression to process
    :type x: z3.ExprRef
    :param substitutions: Variable-name substitution mapping
    :type substitutions: Dict[str, SubstitutionValue]
    :return: Python literal if fully grounded, otherwise a simplified Z3 expression
    :rtype: Union[LiteralValue, z3.ExprRef]
    :raises TypeError: If ``x`` is not a Z3 expression or a substitution is invalid

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> y = z3.Int('y')
        >>> _substitute_and_literalize_expr(x + 3, {'x': y + 1, 'y': 2})
        6
    """
    if not z3.is_expr(x):
        raise TypeError(f"Expected a Z3 expression, got {type(x).__name__}.")

    simplified = _substitute_expr_to_z3(
        expr=x,
        substitutions=substitutions,
        visiting=set(),
        cache={},
        expr_cache={},
    )
    if _contains_unknowns(simplified):
        return simplified
    return _z3_expr_to_python_literal(simplified)


def substitute_and_literalize(
    x: Any,
    substitutions: Dict[str, SubstitutionValue],
) -> Any:
    """
    Recursively substitute values into Z3 expressions inside ``x``.

    This public helper preserves the outer container shape of ``x``:

    * Z3 expressions are processed with :func:`_substitute_and_literalize_expr`
    * ``list`` values stay ``list``
    * ``tuple`` values stay ``tuple``
    * ``dict`` values keep their keys unchanged and process only the values
    * Other Python objects are returned unchanged

    :param x: Object tree to process
    :type x: Any
    :param substitutions: Variable-name substitution mapping
    :type substitutions: Dict[str, SubstitutionValue]
    :return: Object tree with Z3 expressions substituted and literalized
    :rtype: Any

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> substitute_and_literalize([x + 1, {'raw': 'ok'}], {'x': 2})
        [3, {'raw': 'ok'}]
    """
    if z3.is_expr(x):
        return _substitute_and_literalize_expr(x, substitutions)
    if isinstance(x, list):
        return [substitute_and_literalize(item, substitutions) for item in x]
    if isinstance(x, tuple):
        return tuple(substitute_and_literalize(item, substitutions) for item in x)
    if isinstance(x, dict):
        return {
            key: substitute_and_literalize(value, substitutions)
            for key, value in x.items()
        }
    return x
