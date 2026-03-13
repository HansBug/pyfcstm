"""
Unit tests for reverse conversion from Z3 expressions to pyfcstm expressions.

This module verifies structural parsing of Z3 ASTs into canonical Expr
objects and directly exercises internal helper branches to keep coverage
complete for the reverse conversion module.
"""

import pytest
import z3

import pyfcstm.solver.reverse_expr as reverse_expr
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

    @pytest.mark.parametrize(
        ('z3_expr', 'expected_expr'),
        [
            (z3.IntVal(42), Integer(42)),
            (z3.BoolVal(True), Boolean(True)),
            (z3.BoolVal(False), Boolean(False)),
            (z3.RealVal('2.0'), Float(2.0)),
            (z3.RealVal('3.14'), BinaryOp(x=Float(157.0), op='/', y=Float(50.0))),
            (z3.RealVal('1/3'), BinaryOp(x=Float(1.0), op='/', y=Float(3.0))),
            (z3.Int('i'), Variable('i')),
            (-z3.Int('i'), UnaryOp(op='-', x=Variable('i'))),
            (z3.Int('i') + 5, BinaryOp(x=Variable('i'), op='+', y=Integer(5))),
            (z3.Int('i') - z3.Int('j'), BinaryOp(x=Variable('i'), op='-', y=Variable('j'))),
            (z3.Int('i') * z3.Int('j'), BinaryOp(x=Variable('i'), op='*', y=Variable('j'))),
            (z3.Int('i') / z3.Int('j'), BinaryOp(x=Variable('i'), op='/', y=Variable('j'))),
            (z3.Int('i') % z3.Int('j'), BinaryOp(x=Variable('i'), op='%', y=Variable('j'))),
            (z3.Int('i') ** z3.Int('j'), BinaryOp(x=Variable('i'), op='**', y=Variable('j'))),
            (z3.Int('i') < z3.Int('j'), BinaryOp(x=Variable('i'), op='<', y=Variable('j'))),
            (z3.Int('i') <= z3.Int('j'), BinaryOp(x=Variable('i'), op='<=', y=Variable('j'))),
            (z3.Int('i') > z3.Int('j'), BinaryOp(x=Variable('i'), op='>', y=Variable('j'))),
            (z3.Int('i') >= z3.Int('j'), BinaryOp(x=Variable('i'), op='>=', y=Variable('j'))),
            (z3.Int('i') == z3.Int('j'), BinaryOp(x=Variable('i'), op='==', y=Variable('j'))),
            (z3.Distinct(z3.Int('i'), z3.Int('j')), BinaryOp(x=Variable('i'), op='!=', y=Variable('j'))),
            (
                z3.And(z3.Int('i') > 0, z3.Int('j') < 10),
                BinaryOp(
                    x=BinaryOp(x=Variable('i'), op='>', y=Integer(0)),
                    op='&&',
                    y=BinaryOp(x=Variable('j'), op='<', y=Integer(10)),
                ),
            ),
            (
                z3.Or(z3.Int('i') > 0, z3.Int('j') < 10),
                BinaryOp(
                    x=BinaryOp(x=Variable('i'), op='>', y=Integer(0)),
                    op='||',
                    y=BinaryOp(x=Variable('j'), op='<', y=Integer(10)),
                ),
            ),
            (
                z3.Not(z3.Int('i') > 0),
                UnaryOp(op='!', x=BinaryOp(x=Variable('i'), op='>', y=Integer(0))),
            ),
            (
                z3.If(z3.Int('i') > 0, z3.Int('i'), z3.Int('j')),
                ConditionalOp(
                    cond=BinaryOp(x=Variable('i'), op='>', y=Integer(0)),
                    if_true=Variable('i'),
                    if_false=Variable('j'),
                ),
            ),
            (z3.ToReal(z3.Int('i')), Variable('i')),
            (
                z3.Int('i') + z3.Real('r'),
                BinaryOp(x=Variable('i'), op='+', y=Variable('r')),
            ),
            (
                z3.If(z3.Int('i') >= 0, z3.Int('i'), -z3.Int('i')),
                UFunc(func='abs', x=Variable('i')),
            ),
            (
                z3.If(
                    z3.RealVal(0) == z3.Real('r'),
                    z3.RealVal(0),
                    z3.If(z3.RealVal(0) < z3.Real('r'), z3.RealVal(1), z3.RealVal(-1)),
                ),
                UFunc(func='sign', x=Variable('r')),
            ),
            (z3.ToInt(z3.Real('r')), UFunc(func='floor', x=Variable('r'))),
            (-z3.ToInt(-z3.Real('r')), UFunc(func='ceil', x=Variable('r'))),
            (
                z3.If(
                    z3.RealVal(0) <= z3.Real('r'),
                    z3.ToInt(z3.Real('r')),
                    -z3.ToInt(-z3.Real('r')),
                ),
                UFunc(func='trunc', x=Variable('r')),
            ),
            (
                z3.ToInt(z3.Real('r') + z3.RealVal('0.5')),
                UFunc(func='round', x=Variable('r')),
            ),
            (
                z3.ToInt(z3.RealVal('0.5') + z3.Real('r')),
                UFunc(func='round', x=Variable('r')),
            ),
            (
                z3.Sqrt(z3.ToReal(z3.Int('i'))),
                UFunc(func='sqrt', x=Variable('i')),
            ),
            (
                z3.Sqrt(z3.Real('r')),
                UFunc(func='sqrt', x=Variable('r')),
            ),
        ],
    )
    def test_public_structural_parse(self, z3_expr, expected_expr):
        """Test canonical public structural parsing across supported Z3 forms."""
        self._assert_structural_parse(z3_expr, expected_expr)

    @pytest.mark.parametrize(
        ('z3_expr', 'expected_expr'),
        [
            (
                z3.BitVec('bx', 8) & z3.BitVec('by', 8),
                BinaryOp(x=Variable('bx'), op='&', y=Variable('by')),
            ),
            (
                z3.BitVec('bx', 8) | z3.BitVec('by', 8),
                BinaryOp(x=Variable('bx'), op='|', y=Variable('by')),
            ),
            (
                z3.BitVec('bx', 8) ^ z3.BitVec('by', 8),
                BinaryOp(x=Variable('bx'), op='^', y=Variable('by')),
            ),
            (
                z3.BitVec('bx', 8) << z3.BitVec('by', 8),
                BinaryOp(x=Variable('bx'), op='<<', y=Variable('by')),
            ),
            (
                z3.BitVec('bx', 8) >> z3.BitVec('by', 8),
                BinaryOp(x=Variable('bx'), op='>>', y=Variable('by')),
            ),
            (
                z3.LShR(z3.BitVec('bx', 8), z3.BitVec('by', 8)),
                BinaryOp(x=Variable('bx'), op='>>', y=Variable('by')),
            ),
            (
                ~z3.BitVec('bx', 8),
                UnaryOp(op='~', x=Variable('bx')),
            ),
        ],
    )
    def test_public_structural_parse_for_bitvector_forms(self, z3_expr, expected_expr):
        """Test bit-vector specific structural parsing branches."""
        self._assert_structural_parse(z3_expr, expected_expr)

    def test_public_structural_parse_for_complex_z3_forms(self):
        """Test many deeply nested and high-arity Z3 expressions."""
        i = Variable('i')
        j = Variable('j')
        k = Variable('k')
        m = Variable('m')
        r = Variable('r')
        s = Variable('s')
        t = Variable('t')
        bx = Variable('bx')
        by = Variable('by')
        bz = Variable('bz')
        bw = Variable('bw')
        bs = Variable('bs')

        complex_cases = [
            (
                z3.Sum(z3.Int('i'), z3.Int('j'), z3.Int('k'), z3.Int('m'), 5, 7),
                i + j + k + m + 5 + 7,
            ),
            (
                (z3.Int('i') + 1) * (z3.Int('j') - 2) * (z3.Int('k') + 3),
                (i + 1) * (j - 2) * (k + 3),
            ),
            (
                z3.And(
                    z3.Int('i') > 0,
                    z3.Int('j') < 10,
                    z3.Or(z3.Int('k') == 1, z3.Distinct(z3.Int('m'), 2)),
                    z3.Not(z3.Real('r') < 0),
                ),
                (i > 0).and_(j < 10).and_(k.eq(1).or_(m.ne(2))).and_((r < 0.0).not_()),
            ),
            (
                z3.If(
                    z3.And(z3.Int('i') > 0, z3.Or(z3.Int('j') < 3, z3.Int('k') > 5)),
                    z3.Sum(z3.Int('i'), z3.Int('j'), z3.Int('k')),
                    z3.Int('m') - 1,
                ),
                (i > 0).and_((j < 3).or_(k > 5)).select(i + j + k, m - 1),
            ),
            (
                z3.If(
                    z3.Int('i') > z3.Int('j'),
                    z3.If(z3.Int('k') > z3.Int('m'), z3.Int('i') + z3.Int('k'), z3.Int('j') + z3.Int('m')),
                    z3.If(z3.Real('r') > 0, z3.ToInt(z3.Real('r') + z3.RealVal('0.5')), z3.Int('i') - z3.Int('m')),
                ),
                (i > j).select((k > m).select(i + k, j + m), (r > 0.0).select(UFunc(func='round', x=r), i - m)),
            ),
            (
                z3.If(
                    z3.RealVal(0) <= z3.Real('r') + z3.Real('s'),
                    z3.ToInt(z3.Real('r') + z3.Real('s')),
                    -z3.ToInt(-(z3.Real('r') + z3.Real('s'))),
                ),
                UFunc(func='trunc', x=r + s),
            ),
            (
                -z3.ToInt(-(z3.Real('r') + z3.Real('s') + z3.Real('t'))),
                UFunc(func='ceil', x=r + s + t),
            ),
            (
                z3.If(
                    z3.RealVal(0) == z3.Real('r') + z3.Real('s'),
                    z3.RealVal(0),
                    z3.If(z3.RealVal(0) < z3.Real('r') + z3.Real('s'), z3.RealVal(1), z3.RealVal(-1)),
                ),
                UFunc(func='sign', x=r + s),
            ),
            (
                z3.If(z3.Int('i') - z3.Int('j') >= 0, z3.Int('i') - z3.Int('j'), -(z3.Int('i') - z3.Int('j'))),
                UFunc(func='abs', x=i - j),
            ),
            (
                z3.Sqrt(z3.ToReal((z3.Int('i') + 1) * (z3.Int('j') - 2))),
                UFunc(func='sqrt', x=(i + 1) * (j - 2)),
            ),
            (
                z3.ToInt((z3.Real('r') + z3.Real('s')) + z3.RealVal('0.5')),
                UFunc(func='round', x=r + s),
            ),
            (
                z3.And(
                    (z3.Int('i') + z3.Int('j')) > (z3.Int('k') - z3.Int('m')),
                    z3.Int('m') % 3 == 1,
                    z3.Not((z3.Int('j') / 2) < 1),
                ),
                ((i + j) > (k - m)).and_(((m % 3).eq(1))).and_((((j / 2) < 1).not_())),
            ),
            (
                z3.Or(
                    z3.And(z3.Int('i') > 0, z3.Int('j') > 0),
                    z3.And(z3.Int('k') < 0, z3.Int('m') < 0),
                    z3.Real('r') > 0,
                ),
                ((i > 0).and_(j > 0)).or_((k < 0).and_(m < 0)).or_(r > 0.0),
            ),
            (
                ((z3.BitVec('bx', 8) & z3.BitVec('by', 8)) ^ (~z3.BitVec('bz', 8))) | (z3.BitVec('bw', 8) << z3.BitVec('bs', 8)),
                ((bx & by) ^ UnaryOp(op='~', x=bz)) | (bw << bs),
            ),
            (
                (z3.BitVec('bx', 8) + z3.BitVec('by', 8)) * (z3.BitVec('bz', 8) - z3.BitVec('bw', 8)),
                (bx + by) * (bz - bw),
            ),
            (
                z3.UDiv(z3.BitVec('bx', 8), z3.BitVec('by', 8)) + z3.URem(z3.BitVec('bz', 8), z3.BitVec('bw', 8)),
                (bx / by) + (bz % bw),
            ),
            (
                z3.ToReal(z3.Int('i') + z3.Int('j')) + z3.Real('r'),
                (i + j) + r,
            ),
            (
                (z3.Int('i') + 1) ** (z3.Int('j') + 2),
                (i + 1) ** (j + 2),
            ),
            (
                z3.Or(
                    z3.Int('i') == 1,
                    z3.Int('j') == 2,
                    z3.Int('k') == 3,
                    z3.Int('m') == 4,
                    z3.And(z3.Real('r') > 0, z3.Real('s') < 0),
                ),
                i.eq(1).or_(j.eq(2)).or_(k.eq(3)).or_(m.eq(4)).or_((r > 0.0).and_(s < 0.0)),
            ),
            (
                z3.If(
                    z3.And(z3.Int('i') > 0, z3.Int('j') > 0),
                    z3.Sqrt(z3.ToReal((z3.Int('i') * z3.Int('j')) + z3.Int('k'))),
                    z3.If(
                        z3.Real('r') > z3.Real('s'),
                        z3.ToInt((z3.Real('r') - z3.Real('s')) + z3.RealVal('0.5')),
                        z3.If(
                            z3.RealVal(0) <= z3.Real('r') + z3.Real('s'),
                            z3.ToInt(z3.Real('r') + z3.Real('s')),
                            -z3.ToInt(-(z3.Real('r') + z3.Real('s'))),
                        ),
                    ),
                ),
                (i > 0).and_(j > 0).select(
                    UFunc(func='sqrt', x=(i * j) + k),
                    (r > s).select(UFunc(func='round', x=r - s), UFunc(func='trunc', x=r + s)),
                ),
            ),
            (
                z3.If(
                    z3.Distinct(z3.Int('i'), z3.Int('j')),
                    (z3.Int('i') + z3.Int('j')) * (z3.Int('k') - 1),
                    (z3.Int('m') + 2) ** (z3.Int('k') + 1),
                ),
                i.ne(j).select((i + j) * (k - 1), (m + 2) ** (k + 1)),
            ),
            (
                z3.LShR((z3.BitVec('bx', 8) ^ z3.BitVec('by', 8)) & z3.BitVec('bz', 8), z3.BitVec('bs', 8)),
                ((bx ^ by) & bz) >> bs,
            ),
            (
                z3.And(
                    z3.Or(z3.Int('i') + z3.Int('j') > z3.Int('k'), z3.Int('m') < 0),
                    z3.Or(z3.Real('r') > z3.Real('s'), z3.Real('t') < 0),
                    z3.Not(z3.Distinct(z3.Int('i') % 2, 0)),
                ),
                ((i + j) > k).or_(m < 0).and_((r > s).or_(t < 0.0)).and_(((i % 2).ne(0)).not_()),
            ),
            (
                z3.If(
                    z3.Real('r') + z3.Real('s') > z3.Real('t'),
                    z3.If(z3.Int('i') + z3.Int('j') > z3.Int('k'), z3.Int('i') - z3.Int('m'), z3.Int('j') + z3.Int('k')),
                    z3.If(z3.Int('m') > 0, z3.Int('m') % 3, z3.Int('k') / 2),
                ),
                ((r + s) > t).select(
                    ((i + j) > k).select(i - m, j + k),
                    (m > 0).select(m % 3, k / 2),
                ),
            ),
            (
                z3.If(
                    z3.And(z3.RealVal(0) <= z3.Real('r'), z3.RealVal(0) <= z3.Real('s')),
                    z3.ToInt((z3.Real('r') + z3.Real('s') + z3.Real('t')) + z3.RealVal('0.5')),
                    -z3.ToInt(-(z3.Real('r') + z3.Real('s') + z3.Real('t'))),
                ),
                (Float(0.0) <= r).and_(Float(0.0) <= s).select(
                    UFunc(func='round', x=r + s + t),
                    UFunc(func='ceil', x=r + s + t),
                ),
            ),
        ]

        assert len(complex_cases) >= 20
        for z3_expr, expected_expr in complex_cases:
            self._assert_structural_parse(z3_expr, expected_expr)

    def test_public_errors_for_unsupported_inputs(self):
        """Test public unsupported-shape errors."""
        func = z3.Function('f', z3.IntSort(), z3.IntSort())

        with pytest.raises(ValueError, match='Unsupported Z3 expression'):
            z3_to_expr(func(z3.Int('x')))

        with pytest.raises(ValueError, match='Unsupported n-ary distinct expression'):
            z3_to_expr(z3.Distinct(z3.Int('x'), z3.Int('y'), z3.Int('z')))

    def test_internal_helper_edge_cases(self):
        """Test internal helper edge cases that are awkward to hit via the public API."""
        x_var = z3.Int('x')

        assert reverse_expr._is_numeric_literal(-z3.IntVal(5), -5) is True
        assert reverse_expr._extract_zero_compare_operand(-x_var, z3.Z3_OP_GE) is None

        with pytest.raises(ValueError, match='Cannot fold an empty Z3 expression sequence'):
            reverse_expr._fold_binary_expr('+', [])

        with pytest.raises(ValueError, match='Unsupported non-expression Z3 value'):
            reverse_expr._z3_to_expr_impl(123)

    def test_internal_matcher_reject_paths(self):
        """Test matcher reject branches directly to cover all negative paths."""
        x_int = z3.Int('x')
        y_int = z3.Int('y')
        x_real = z3.Real('xr')
        y_real = z3.Real('yr')

        assert reverse_expr._match_abs(z3.If(x_int >= 0, x_int, z3.IntVal(0))) is None
        assert reverse_expr._match_abs(z3.If(x_int >= 0, x_int, -y_int)) is None

        assert reverse_expr._match_sign(
            z3.If(x_real == z3.RealVal(1), z3.RealVal(0), z3.If(x_real > 0, z3.RealVal(1), z3.RealVal(-1)))
        ) is None
        assert reverse_expr._match_sign(
            z3.If(x_real == z3.RealVal(0), z3.RealVal(0), z3.If(y_real > 0, z3.RealVal(1), z3.RealVal(-1)))
        ) is None
        assert reverse_expr._match_sign(
            z3.If(x_real == z3.RealVal(0), z3.RealVal(0), z3.If(x_real > 0, z3.RealVal(2), z3.RealVal(-1)))
        ) is None

        assert reverse_expr._match_trunc(
            z3.If(x_real >= z3.RealVal(0), x_real, -z3.ToInt(-x_real))
        ) is None
        assert reverse_expr._match_trunc(
            z3.If(x_real >= z3.RealVal(0), z3.ToInt(y_real), -z3.ToInt(-x_real))
        ) is None
        assert reverse_expr._match_trunc(
            z3.If(x_real >= z3.RealVal(0), z3.ToInt(x_real), z3.ToInt(-x_real))
        ) is None
        assert reverse_expr._match_trunc(
            z3.If(x_real >= z3.RealVal(0), z3.ToInt(x_real), -z3.Int('k'))
        ) is None
        assert reverse_expr._match_trunc(
            z3.If(x_real >= z3.RealVal(0), z3.ToInt(x_real), -z3.ToInt(x_real))
        ) is None
        assert reverse_expr._match_trunc(
            z3.If(x_real >= z3.RealVal(0), z3.ToInt(x_real), -z3.ToInt(-y_real))
        ) is None

        assert reverse_expr._match_ceil(-z3.ToInt(x_real)) is None

        assert reverse_expr._match_round(
            z3.ToInt(x_real + y_real)
        ) is None
        assert reverse_expr._match_round(
            z3.ToInt(x_real + z3.RealVal('1/3'))
        ) is None

        assert reverse_expr._match_sqrt(x_int ** y_int) is None
        assert reverse_expr._match_sqrt(x_int ** z3.RealVal('1/3')) is None
