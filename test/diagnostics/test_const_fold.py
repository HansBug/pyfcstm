"""Unit tests for literal-only diagnostic constant folding."""

import math

import pytest

from pyfcstm.diagnostics.analyzers import (
    fold_condition_expression,
    fold_numeric_expression,
)
from pyfcstm.model.expr import parse_expr_from_string


def _num(text):
    return parse_expr_from_string(text, mode='numeric')


def _cond(text):
    return parse_expr_from_string(text, mode='logical')


@pytest.mark.unittest
@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('1 + 2 * 3', 7),
        ('(0x0F & 10) | 1', 11),
        ('8 >> 1', 4),
        ('5 ^ 3', 6),
        ('(1 > 0) ? 10 : 20', 10),
        ('(1 < 0) ? 10 : 20', 20),
        ('+5', 5),
        ('-(2 ** 3)', -8),
        ('5 / 2', 2.5),
        ('7 % 4', 3),
    ],
)
def test_fold_numeric_literal_only_expressions(text, expected):
    assert fold_numeric_expression(_num(text)) == expected


@pytest.mark.unittest
@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('(1 + 2) == 3', True),
        ('(0x0F & 0xF0) != 0', False),
        ('1 < 2', True),
        ('1 <= 1', True),
        ('2 > 1', True),
        ('2 >= 2', True),
        ('true == false', False),
        ('true != false', True),
        ('(1 > 0) ? false : true', False),
        ('(1 < 0) ? false : true', True),
        ('!(2 < 1) && true', True),
        ('false || true', True),
        ('9007199254740993 == 9007199254740992', False),
    ],
)
def test_fold_condition_literal_only_expressions(text, expected):
    assert fold_condition_expression(_cond(text)) is expected


@pytest.mark.unittest
@pytest.mark.parametrize(
    ('text', 'mode'),
    [
        ('counter + 1', 'numeric'),
        ('sin(0)', 'numeric'),
        ('1 << -1', 'numeric'),
        ('1 / 0', 'numeric'),
        ('1 % 0', 'numeric'),
        ('10 ** 10000', 'numeric'),
        ('counter > 0', 'logical'),
        ('(counter > 0) ? 1 : 2', 'numeric'),
        ('(counter > 0) ? false : true', 'logical'),
        ('(1 / 0) == 0', 'logical'),
        ('1.5 & 1', 'numeric'),
        ('(-1) ** 0.5', 'numeric'),
    ],
)
def test_unsupported_or_runtime_dependent_expressions_do_not_fold(text, mode):
    expr = parse_expr_from_string(text, mode=mode)
    if mode == 'numeric':
        assert fold_numeric_expression(expr) is None
    else:
        assert fold_condition_expression(expr) is None


@pytest.mark.unittest
def test_float_equality_uses_tolerance():
    assert fold_condition_expression(_cond('(0.1 + 0.2) == 0.3')) is True
    assert math.isclose(fold_numeric_expression(_num('0.1 + 0.2')), 0.3)


@pytest.mark.unittest
def test_collect_const_fold_warnings_none_machine():
    from pyfcstm.diagnostics.analyzers import collect_const_fold_warnings

    assert collect_const_fold_warnings(None) == []
