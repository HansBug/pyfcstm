"""
Unit tests for reverse conversion from Z3 expressions to pyfcstm expressions.

This module verifies structural parsing of Z3 ASTs into canonical Expr
objects.
"""

import pytest
import z3

from pyfcstm.model.expr import (
    BinaryOp,
    Boolean,
    ConditionalOp,
    Float,
    Integer,
    UFunc,
    UnaryOp,
    Variable,
)
from pyfcstm.solver import z3_to_expr


@pytest.mark.unittest
class TestZ3ToExpr:
    """Test reverse conversion from Z3 expressions to Expr objects."""

    @staticmethod
    def _assert_structural_parse(z3_expr, expected_expr):
        """
        Assert structural reverse conversion for a Z3 AST.

        :param z3_expr: Z3 expression to parse.
        :param expected_expr: Expected canonical expression after reverse conversion.
        :return: ``None``.
        """
        recovered_expr = z3_to_expr(z3_expr)
        assert recovered_expr == expected_expr

    def test_structural_recovery_for_injective_z3_patterns(self):
        """Test Z3 patterns whose structure can be recovered directly."""
        i_var = z3.Int('i')
        j_var = z3.Int('j')
        r_var = z3.Real('r')
        zero_real = z3.RealVal(0)
        one_real = z3.RealVal(1)
        minus_one_real = z3.RealVal(-1)

        cases = [
            (z3.IntVal(42), Integer(42)),
            (z3.BoolVal(True), Boolean(True)),
            (i_var, Variable('i')),
            (-i_var, UnaryOp(op='-', x=Variable('i'))),
            (i_var + 5, BinaryOp(x=Variable('i'), op='+', y=Integer(5))),
            (i_var + r_var, BinaryOp(x=Variable('i'), op='+', y=Variable('r'))),
            (z3.And(
                i_var > 0,
                j_var < 10,
            ), BinaryOp(
                x=BinaryOp(x=Variable('i'), op='>', y=Integer(0)),
                op='&&',
                y=BinaryOp(x=Variable('j'), op='<', y=Integer(10)),
            )),
            (z3.If(
                i_var > 0,
                z3.ToInt(r_var + z3.RealVal('0.5')),
                i_var,
            ), ConditionalOp(
                cond=BinaryOp(x=Variable('i'), op='>', y=Integer(0)),
                if_true=UFunc(func='round', x=Variable('r')),
                if_false=Variable('i'),
            )),
            (z3.If(i_var >= 0, i_var, -i_var), UFunc(func='abs', x=Variable('i'))),
            (
                z3.If(zero_real == r_var, zero_real, z3.If(zero_real < r_var, one_real, minus_one_real)),
                UFunc(func='sign', x=Variable('r')),
            ),
            (z3.ToInt(r_var), UFunc(func='floor', x=Variable('r'))),
            (-z3.ToInt(-r_var), UFunc(func='ceil', x=Variable('r'))),
            (z3.If(zero_real <= r_var, z3.ToInt(r_var), -z3.ToInt(-r_var)), UFunc(func='trunc', x=Variable('r'))),
            (z3.ToInt(r_var + z3.RealVal('0.5')), UFunc(func='round', x=Variable('r'))),
            (z3.Sqrt(z3.ToReal(i_var)), UFunc(func='sqrt', x=Variable('i'))),
            (z3.Sqrt(r_var), UFunc(func='sqrt', x=Variable('r'))),
        ]

        for z3_expr, expected_expr in cases:
            self._assert_structural_parse(z3_expr, expected_expr)

    def test_canonicalization_for_ambiguous_z3_patterns(self):
        """Test Z3 patterns that do not have unique Expr preimages."""
        i_var = z3.Int('i')
        r_var = z3.Real('r')

        cases = [
            (z3.RealVal('3.14'), BinaryOp(x=Float(157.0), op='/', y=Float(50.0))),
            (i_var, Variable('i')),
            (z3.If(
                i_var > 0,
                z3.ToInt(r_var + z3.RealVal('0.5')),
                i_var,
            ), ConditionalOp(
                cond=BinaryOp(x=Variable('i'), op='>', y=Integer(0)),
                if_true=UFunc(func='round', x=Variable('r')),
                if_false=Variable('i'),
            )),
        ]

        for z3_expr, expected_expr in cases:
            self._assert_structural_parse(z3_expr, expected_expr)

    def test_structural_parse_for_exact_rational_literal(self):
        """Test that arbitrary rational literals fall back to division form."""
        z3_expr = z3.RealVal('1/3')
        recovered_expr = z3_to_expr(z3_expr)

        assert recovered_expr == BinaryOp(x=Float(1.0), op='/', y=Float(3.0))

    def test_unsupported_uninterpreted_function_raises_error(self):
        """Test unsupported non-variable uninterpreted applications."""
        func = z3.Function('f', z3.IntSort(), z3.IntSort())
        z3_expr = func(z3.Int('x'))

        with pytest.raises(ValueError, match='Unsupported Z3 expression'):
            z3_to_expr(z3_expr)
