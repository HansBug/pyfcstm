"""The direct term constructors build exactly the terms the ``z3`` operators build."""

from __future__ import annotations

import itertools

import pytest
import z3

from pyfcstm.solver.term import (
    and_terms,
    eq_term,
    implies_term,
    int_term,
    is_int_term,
    ite_term,
    not_term,
    or_terms,
)

pytestmark = pytest.mark.unittest


def _same(left, right) -> bool:
    """Same term, same Python class."""
    return type(left) is type(right) and z3.eq(left, right)


a, b, c = z3.Bools("a b c")
x, y = z3.Ints("x y")
r = z3.Real("r")
other = z3.Context()
oa = z3.Bool("a", other)
ox = z3.Int("x", other)


def _quantifier():
    return z3.ForAll([x], x > y)


def _bool_operand_sets():
    return [
        (a,),
        (a, b),
        (a, b, c),
        (a, z3.BoolVal(True)),
        (z3.BoolVal(False), z3.BoolVal(True)),
        (x > 0, y < 3),
        (a, _quantifier()),
        (a, True),
        (False, True),
    ]


@pytest.mark.parametrize("operands", _bool_operand_sets())
def test_conjunction_and_disjunction_match_the_operators(operands) -> None:
    assert _same(and_terms(operands), z3.And(*operands))
    assert _same(or_terms(operands), z3.Or(*operands))


def test_conjunction_of_nothing_and_of_foreign_operands_is_left_to_the_operators() -> (
    None
):
    assert _same(and_terms(()), z3.And())
    assert _same(or_terms(()), z3.Or())
    with pytest.raises(z3.Z3Exception):
        and_terms((a, oa))
    with pytest.raises(z3.Z3Exception):
        or_terms((a, oa))
    assert _same(and_terms([a, b]), z3.And(a, b))


@pytest.mark.parametrize("operand", [a, x > 0, z3.BoolVal(True), True, _quantifier()])
def test_negation_matches_the_operator(operand) -> None:
    assert _same(not_term(operand), z3.Not(operand))


@pytest.mark.parametrize(
    ("left", "right"),
    list(itertools.product([a, z3.BoolVal(True), True, x > 0], repeat=2)),
)
def test_implication_matches_the_operator(left, right) -> None:
    assert _same(implies_term(left, right), z3.Implies(left, right))


def test_implication_across_contexts_raises_like_the_operator() -> None:
    with pytest.raises(z3.Z3Exception):
        implies_term(a, oa)
    with pytest.raises(z3.Z3Exception):
        z3.Implies(a, oa)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (x, y),
        (x, x + 1),
        (x, z3.IntVal(3)),
        (z3.IntVal(3), x),
        (z3.IntVal(3), z3.IntVal(3)),
        (x, 3),
        (3, x),
        (x, r),
        (r, x),
        (a, b),
        (a, z3.BoolVal(True)),
        (z3.BoolVal(True), a),
        (r, z3.RealVal(2)),
        (z3.RealVal(2), r),
    ],
)
def test_equality_matches_the_operator(left, right) -> None:
    assert _same(eq_term(left, right), left == right)


def test_equality_across_contexts_raises_like_the_operator() -> None:
    with pytest.raises(z3.Z3Exception):
        eq_term(x, ox)
    with pytest.raises(z3.Z3Exception):
        x == ox


@pytest.mark.parametrize(
    ("test", "if_true", "if_false"),
    [
        (a, x, y),
        (a, x, z3.IntVal(0)),
        (a, z3.IntVal(1), z3.IntVal(0)),
        (a, b, c),
        (a, z3.BoolVal(True), b),
        (a, x, r),
        (a, r, x),
        (a, r, z3.RealVal(1)),
        (a, x, 0),
        (a, 1, x),
        (a, 1, 2),
        (True, x, y),
        (x > 0, x, y),
        (a, x, x),
        (a, z3.IntVal(4), z3.IntVal(4)),
    ],
)
def test_conditional_matches_the_operator(test, if_true, if_false) -> None:
    assert _same(ite_term(test, if_true, if_false), z3.If(test, if_true, if_false))


def test_conditional_with_mixed_contexts_raises_like_the_operator() -> None:
    with pytest.raises(z3.Z3Exception):
        ite_term(a, x, ox)
    with pytest.raises(z3.Z3Exception):
        z3.If(a, x, ox)


@pytest.mark.parametrize(
    "value", [x, x + 1, z3.IntVal(1), r, r + 1, a, 1, 1.5, "x", None, z3.IntSort()]
)
def test_integer_sort_test_matches_the_operator(value) -> None:
    assert is_int_term(value) == z3.is_int(value)


def test_integer_numerals_are_shared_and_equal_to_the_operator() -> None:
    assert z3.eq(int_term(7), z3.IntVal(7))
    assert int_term(7) is int_term(7)
    assert type(int_term(7)) is type(z3.IntVal(7))
    assert int_term(-3).as_long() == -3


@pytest.mark.parametrize("value", [True, 2.5, "9", z3.IntVal(4)])
def test_integer_numerals_of_other_values_go_to_the_operator(value) -> None:
    try:
        expected = z3.IntVal(value)
    except (z3.Z3Exception, TypeError, ValueError) as error:
        with pytest.raises(type(error)):
            int_term(value)
    else:
        assert _same(int_term(value), expected)


def test_the_numeral_table_is_emptied_when_it_is_full() -> None:
    first = int_term(10**9)
    for value in range(10**9 + 1, 10**9 + 1 + 4097):
        int_term(value)
    assert z3.eq(int_term(10**9), first)
    assert int_term(10**9) is not first
