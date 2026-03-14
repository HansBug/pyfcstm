"""
Unit tests for Z3 substitution and literalization helpers.
"""

import pytest
import z3

from pyfcstm.solver.substitute import (
    _substitute_and_literalize_expr,
    substitute_and_literalize,
)


def _assert_exprs_equivalent(left: z3.ExprRef, right: z3.ExprRef) -> None:
    """Assert that two Z3 expressions are semantically equivalent."""
    solver = z3.Solver()
    solver.add(left != right)
    assert solver.check() == z3.unsat


def _assert_result_matches(result, expected):
    """Assert either a Python literal result or a semantically equivalent Z3 result."""
    if z3.is_expr(expected):
        assert z3.is_expr(result)
        _assert_exprs_equivalent(result, expected)
    else:
        assert result == expected


X = z3.Int('x')
Y = z3.Int('y')
U = z3.Int('u')
R = z3.Real('r')
S = z3.Real('s')
A = z3.Bool('a')
B = z3.Bool('b')
FLAG = z3.Bool('flag')
OTHER = z3.Bool('other')
BX = z3.BitVec('bx', 8)
BY = z3.BitVec('by', 8)


@pytest.mark.unittest
class TestPrivateSubstituteAndLiteralizeExpr:
    """Test the internal single-expression substitution helper."""

    def test_returns_python_int_when_all_unknowns_eliminated(self):
        """Test fully-ground integer expressions become Python ints."""
        x = z3.Int('x')

        result = _substitute_and_literalize_expr(x + 2, {'x': 5, 'unused': 99})

        assert result == 7
        assert isinstance(result, int)

    def test_returns_python_bool_when_all_unknowns_eliminated(self):
        """Test fully-ground boolean expressions become Python bool values."""
        flag = z3.Bool('flag')

        result = _substitute_and_literalize_expr(z3.Not(flag), {'flag': False})

        assert result is True

    def test_recursively_expands_z3_replacement_expressions(self):
        """Test replacement expressions can trigger further substitution."""
        x = z3.Int('x')
        y = z3.Int('y')

        result = _substitute_and_literalize_expr(x + 3, {'x': y + 1, 'y': 2})

        assert result == 6

    def test_keeps_new_unknowns_but_literalizes_ground_subtrees(self):
        """Test partially-ground expressions stay symbolic after local folding."""
        flag = z3.Bool('flag')
        a = z3.Int('a')
        b = z3.Int('b')

        result = _substitute_and_literalize_expr(
            z3.If(flag, a + 1, b + 2),
            {'a': 2, 'b': 3},
        )

        assert z3.is_expr(result)
        _assert_exprs_equivalent(result, z3.If(flag, z3.IntVal(3), z3.IntVal(5)))

    def test_coerces_python_int_into_real_sort(self):
        """Test Python ints are promoted when substituted into Real variables."""
        r = z3.Real('r')

        result = _substitute_and_literalize_expr(r / 2, {'r': 1})

        assert result == pytest.approx(0.5)

    def test_cycles_do_not_cause_infinite_recursion(self):
        """Test cyclic substitution definitions stop expanding and still simplify."""
        x = z3.Int('x')
        y = z3.Int('y')

        result = _substitute_and_literalize_expr(
            x + 4,
            {'x': y + 1, 'y': x + 2},
        )

        assert z3.is_expr(result)
        _assert_exprs_equivalent(result, x + 7)

    def test_rejects_invalid_python_literal_for_target_sort(self):
        """Test incompatible Python literals are rejected explicitly."""
        x = z3.Int('x')

        with pytest.raises(TypeError, match="Expected an int literal"):
            _substitute_and_literalize_expr(x + 1, {'x': 1.5})

    def test_rejects_non_z3_input(self):
        """Test the private helper only accepts Z3 expressions."""
        with pytest.raises(TypeError, match="Expected a Z3 expression"):
            _substitute_and_literalize_expr(1, {'x': 2})

    @pytest.mark.parametrize(
        ('expr', 'substitutions', 'expected_text', 'expected'),
        [
            (X + 1 - Y * 2 - 4 + 100, {}, 'x - 2*y + 97', X - 2 * Y + 97),
            (X - Y + 3 + Y - 2, {}, 'x + 1', X + 1),
            (X + (Y + 2) - (Y + 5), {}, 'x - 3', X - 3),
            ((X - Y) - (2 - Y) + 10, {}, 'x + 8', X + 8),
            ((X + Y) + (3 - X) - 2, {}, 'y + 1', Y + 1),
            (2 * X + 3 * X - Y + Y - 4 + 9, {}, '5*x + 5', 5 * X + 5),
            ((R / 2) * 6, {}, '3*r', 3 * R),
            (((R * 2) / 4) * 6, {}, '3*r', 3 * R),
            ((((R / S) / 4) * 6), {}, '3/2*(r/s)', z3.RealVal('3/2') * (R / S)),
            (((R / S) * 6), {}, '6*(r/s)', 6 * (R / S)),
            ((((2 * R) / S) * 6), {}, '6*((2*r)/s)', 6 * ((2 * R) / S)),
            (z3.If(z3.BoolVal(True), X + 1, Y + 2), {}, 'x + 1', X + 1),
            (z3.And(A, z3.BoolVal(True), B, A), {}, 'And(a, b)', z3.And(A, B)),
            (z3.Or(A, z3.BoolVal(False), B, A), {}, 'Or(a, b)', z3.Or(A, B)),
            (z3.Xor(z3.Xor(A, B), z3.Xor(A, z3.BoolVal(True))), {}, 'Not(b)', z3.Not(B)),
            (BX & z3.BitVecVal(0xFF, 8) & BX & BY, {}, 'bx & by', BX & BY),
            (BX | z3.BitVecVal(0, 8) | BY | BX, {}, 'bx | by', BX | BY),
            (BX ^ BY ^ BX ^ z3.BitVecVal(0, 8), {}, 'by', BY),
            (X + 1 - Y * 2 - 4 + 100, {'x': U + 3, 'y': 5}, 'u + 90', U + 90),
            (z3.And(FLAG, OTHER), {'flag': z3.Or(A, z3.BoolVal(False)), 'other': True}, 'a', A),
        ],
    )
    def test_normalizes_supported_operation_families(
        self,
        expr,
        substitutions,
        expected_text,
        expected,
    ):
        """Test canonicalization across arithmetic, logical, and bitwise families."""
        result = _substitute_and_literalize_expr(expr, substitutions)

        assert z3.is_expr(result)
        assert str(result) == expected_text
        _assert_result_matches(result, expected)

    @pytest.mark.parametrize(
        ('expr', 'substitutions', 'expected'),
        [
            (z3.And(A, z3.Not(A), B), {}, False),
            (z3.Or(A, z3.Not(A), B), {}, True),
            (BX & ~BX & BY, {}, 0),
            (BX | ~BX | BY, {}, 255),
            (
                z3.BitVecVal(0x12, 8) ^ z3.BitVecVal(0x34, 8) ^ z3.BitVecVal(0x12, 8),
                {},
                0x34,
            ),
            (z3.IntVal(3) + 4 - 2 + 10, {}, 15),
        ],
    )
    def test_collapses_fully_ground_family_results(self, expr, substitutions, expected):
        """Test family normalizations that eliminate all remaining unknowns."""
        result = _substitute_and_literalize_expr(expr, substitutions)

        if z3.is_expr(expected):
            assert z3.is_expr(result)
            _assert_exprs_equivalent(result, expected)
        else:
            assert result == expected


@pytest.mark.unittest
class TestPublicSubstituteAndLiteralize:
    """Test the public recursive substitution helper."""

    def test_processes_nested_containers_without_touching_dict_keys(self):
        """Test nested lists, tuples, and dict values keep their outer shapes."""
        x = z3.Int('x')
        y = z3.Int('y')
        flag = z3.Bool('flag')
        r = z3.Real('r')
        ignored_key = ('keep', 'me')

        payload = {
            'expr': z3.If(flag, x + 1, y + 2),
            'items': [x * 2, (r / 2, True, 'raw')],
            ignored_key: {'nested': y + 3},
        }

        result = substitute_and_literalize(
            payload,
            {'x': 2, 'y': z3.IntVal(4), 'flag': True, 'r': 1},
        )

        assert isinstance(result, dict)
        assert result['expr'] == 3
        assert result['items'][0] == 4
        assert result['items'][1][0] == pytest.approx(0.5)
        assert result['items'][1][1] is True
        assert result['items'][1][2] == 'raw'
        assert result[ignored_key]['nested'] == 7

    def test_leaves_unresolved_z3_expressions_inside_containers(self):
        """Test symbolic expressions remain Z3 objects when unknowns still exist."""
        x = z3.Int('x')
        y = z3.Int('y')
        flag = z3.Bool('flag')

        payload = [
            x + 1,
            {'expr': z3.If(flag, x, 10)},
        ]

        result = substitute_and_literalize(payload, {'x': y + 2})

        assert isinstance(result, list)
        assert z3.is_expr(result[0])
        assert z3.is_expr(result[1]['expr'])
        _assert_exprs_equivalent(result[0], y + 3)
        _assert_exprs_equivalent(result[1]['expr'], z3.If(flag, y + 2, 10))

    def test_passes_python_values_through_unchanged(self):
        """Test non-Z3 Python objects are returned unchanged."""
        payload = [1, 2.5, False, 'text', {'raw': None}]

        result = substitute_and_literalize(payload, {'x': 1})

        assert result == payload

    def test_processes_complex_mixed_payload_with_family_normalization(self):
        """Test a larger nested payload with arithmetic, logical, and bitwise families."""
        payload = {
            'arith': X + 1 - Y * 2 - 4 + 100,
            'logic': z3.And(FLAG, OTHER, z3.BoolVal(True), FLAG),
            'bitwise': BX & z3.BitVecVal(0xFF, 8) & BX & BY,
            'nested': (
                z3.If(z3.BoolVal(True), X + 1, Y + 2),
                [z3.Or(A, z3.BoolVal(False), B, A), BX ^ BY ^ BX],
            ),
        }

        result = substitute_and_literalize(
            payload,
            {
                'x': U + 3,
                'y': 5,
                'flag': z3.Or(A, z3.BoolVal(False)),
                'other': True,
            },
        )

        assert isinstance(result, dict)
        assert str(result['arith']) == 'u + 90'
        _assert_exprs_equivalent(result['arith'], U + 90)
        assert str(result['logic']) == 'a'
        _assert_exprs_equivalent(result['logic'], A)
        assert str(result['bitwise']) == 'bx & by'
        _assert_exprs_equivalent(result['bitwise'], BX & BY)
        assert str(result['nested'][0]) == 'u + 4'
        _assert_exprs_equivalent(result['nested'][0], U + 4)
        assert str(result['nested'][1][0]) == 'Or(a, b)'
        _assert_exprs_equivalent(result['nested'][1][0], z3.Or(A, B))
        assert str(result['nested'][1][1]) == 'by'
        _assert_exprs_equivalent(result['nested'][1][1], BY)
