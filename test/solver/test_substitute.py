"""
Unit tests for Z3 substitution and literalization helpers.
"""

from fractions import Fraction

import pytest
import z3

from pyfcstm.solver.substitute import (
    _algebraic_to_float,
    _arith_numeral_to_fraction,
    _build_linear_expr,
    _build_product_expr,
    _build_sorted_product,
    _coerce_z3_expr_to_sort,
    _collect_additive_terms,
    _contains_unknowns,
    _expr_family,
    _extract_additive_term,
    _extract_product_scalars,
    _flatten_same_kind,
    _fraction_to_arith_value,
    _make_zero,
    _normalize_arith_family,
    _normalize_bool_family,
    _normalize_bv_bitwise_family,
    _python_literal_to_z3,
    _resolve_substitution_value,
    _sort_label,
    _substitute_and_literalize_expr,
    _z3_expr_to_python_literal,
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

    def test_processes_long_arithmetic_chain_without_losing_compaction(self):
        """Test a longer arithmetic chain still compacts to a short symbolic form."""
        expr = X
        expected = X
        constant = 0
        for index in range(1, 41):
            expr = expr + index - Y * 2 + Y * 2
            constant += index
        expr = expr - 17 + 9 - 5 + 3
        constant += -17 + 9 - 5 + 3

        result = substitute_and_literalize(expr, {})

        assert z3.is_expr(result)
        assert str(result) == f'x + {constant}'
        _assert_exprs_equivalent(result, expected + constant)


@pytest.mark.unittest
class TestSubstitutePrivateHelpers:
    """Test private helper branches directly for coverage and regression locking."""

    def test_sort_and_zero_helpers_cover_supported_and_error_paths(self):
        """Test sort labels and zero construction across supported sorts."""
        assert _sort_label(z3.BoolSort()) == 'Bool'
        assert str(_make_zero(z3.IntSort())) == '0'
        assert str(_make_zero(z3.RealSort())) == '0'
        assert str(_make_zero(z3.BitVecSort(8))) == '0'

        with pytest.raises(TypeError, match='Unsupported zero sort'):
            _make_zero(z3.BoolSort())

    def test_arithmetic_literal_conversion_helpers_cover_success_and_error_paths(self):
        """Test arithmetic numeral conversions and their defensive branches."""
        assert _arith_numeral_to_fraction(z3.RealVal('3/2')) == Fraction(3, 2)
        assert str(_fraction_to_arith_value(Fraction(3, 2), z3.RealSort())) == '3/2'

        with pytest.raises(TypeError, match='not an arithmetic numeral'):
            _arith_numeral_to_fraction(X)
        with pytest.raises(TypeError, match='non-integer fraction'):
            _fraction_to_arith_value(Fraction(3, 2), z3.IntSort())
        with pytest.raises(TypeError, match='Unsupported arithmetic sort'):
            _fraction_to_arith_value(Fraction(1, 1), z3.BoolSort())

    def test_flatten_and_product_builders_handle_nested_and_sorted_inputs(self):
        """Test flattening and sorted product rebuilding helpers."""
        flattened = _flatten_same_kind(X + Y + 1, z3.Z3_OP_ADD)
        assert [str(item) for item in flattened] == ['x', 'y', '1']
        assert str(_build_sorted_product([Y, X])) == 'x*y'

    def test_additive_helpers_cover_uminus_subtraction_zero_and_negative_paths(self):
        """Test additive helper branches that are hard to hit through public APIs."""
        terms = {}
        representatives = {}

        coeff, core = _extract_additive_term(-X)
        assert coeff == Fraction(-1, 1)
        assert str(core) == 'x'

        coeff, core = _extract_additive_term(z3.IntVal(2) * z3.IntVal(3))
        assert coeff == Fraction(6, 1)
        assert core is None

        constant = _collect_additive_terms(X - Y - 3, 1, terms, representatives)
        assert constant == Fraction(-3, 1)
        assert terms[_sort_label(X.sort()).replace('Int', X.sexpr()) if False else X.sexpr()] == Fraction(1, 1)
        assert terms[Y.sexpr()] == Fraction(-1, 1)

        terms = {}
        representatives = {}
        constant = _collect_additive_terms(-X, 1, terms, representatives)
        assert constant == 0
        assert terms[X.sexpr()] == Fraction(-1, 1)

        assert str(_build_linear_expr(z3.IntSort(), X - X + Y)) == 'y'
        assert str(_build_linear_expr(z3.IntSort(), X + Y + 1)) == 'x + y + 1'
        assert str(_build_linear_expr(z3.IntSort(), z3.IntVal(-3))) == '-3'
        assert str(_build_linear_expr(z3.IntSort(), -X - Y)) == '-x - y'
        assert str(_build_linear_expr(z3.IntSort(), z3.IntVal(0))) == '0'

    def test_product_helpers_cover_scalar_extraction_and_edge_cases(self):
        """Test multiplicative helper branches that drive lightweight compaction."""
        scalar, cores = _extract_product_scalars(-X, allow_numeric_division=False)
        assert scalar == Fraction(-1, 1)
        assert [str(item) for item in cores] == ['x']

        scalar, cores = _extract_product_scalars(R / 4, allow_numeric_division=True)
        assert scalar == Fraction(1, 4)
        assert [str(item) for item in cores] == ['r']

        assert str(_build_product_expr(z3.IntSort(), z3.IntVal(0) * X)) == '0'
        assert str(_build_product_expr(z3.IntSort(), X)) == 'x'
        assert str(_build_product_expr(z3.IntSort(), -X)) == '-x'

    @pytest.mark.parametrize(
        ('expr', 'expected_text'),
        [
            (z3.Or(A, z3.BoolVal(True), B), 'True'),
            (z3.And(A, z3.BoolVal(False), B), 'False'),
            (z3.And(z3.BoolVal(True), A), 'a'),
            (z3.Or(z3.BoolVal(False), A), 'a'),
            (z3.And(z3.Not(A), B), 'And(Not(a), b)'),
            (z3.And(z3.Not(A), A), 'False'),
            (z3.And(z3.BoolVal(True), z3.BoolVal(True)), 'True'),
            (z3.Xor(A, z3.BoolVal(False)), 'a'),
            (z3.Xor(z3.BoolVal(False), z3.BoolVal(False)), 'False'),
            (z3.Xor(A, B), 'Xor(a, b)'),
        ],
    )
    def test_boolean_family_normalizer_covers_identity_annihilator_and_xor_paths(
        self,
        expr,
        expected_text,
    ):
        """Test direct boolean family normalization branches."""
        assert str(_normalize_bool_family(expr)) == expected_text

    def test_boolean_family_normalizer_returns_input_for_unsupported_bool_ops(self):
        """Test unsupported boolean root kinds fall back to the original expression."""
        expr = X > 0

        assert _normalize_bool_family(expr).eq(expr)

    @pytest.mark.parametrize(
        ('expr', 'expected_text'),
        [
            (BX & z3.BitVecVal(0, 8), '0'),
            (~BX & BY, '~bx & by'),
            (~BX & BX, '0'),
            (BX & z3.BitVecVal(0x0F, 8), 'bx & 15'),
            (BX ^ BY, 'bx ^ by'),
            (BX + BY, 'bx + by'),
        ],
    )
    def test_bitvector_family_normalizer_covers_conflicts_literals_and_fallbacks(
        self,
        expr,
        expected_text,
    ):
        """Test direct bitvector family normalization branches."""
        assert str(_normalize_bv_bitwise_family(expr)) == expected_text

    def test_bitvector_family_normalizer_keeps_non_annihilating_literals(self):
        """Test bitvector literal factors survive when they do not collapse the result."""
        expr = BX & z3.BitVecVal(0x0F, 8) & BY

        assert str(_normalize_bv_bitwise_family(expr)) == 'bx & by & 15'

    def test_arith_family_and_family_detection_cover_non_matching_paths(self):
        """Test arithmetic family dispatch and unsupported-family fallbacks."""
        quantifier = z3.ForAll([X], X > 0)

        assert str(_normalize_arith_family(z3.BoolVal(True))) == 'True'
        assert str(_normalize_arith_family(X % 3)) == 'x%3'
        assert _expr_family(quantifier) is None

    def test_literal_coercion_unknown_detection_and_python_literalization_branches(self):
        """Test literal/coercion helpers including unsupported and algebraic cases."""
        algebraic = z3.simplify(z3.Sqrt(z3.RealVal(2)))

        assert str(_python_literal_to_z3(3, z3.IntSort())) == '3'
        assert str(_python_literal_to_z3(3, z3.RealSort())) == '3'
        assert str(_python_literal_to_z3(3, z3.BitVecSort(8))) == '3'
        assert _coerce_z3_expr_to_sort(z3.IntVal(3), z3.RealSort()).sort().eq(z3.RealSort())
        assert _contains_unknowns(z3.Function('f', z3.IntSort(), z3.IntSort())(X)) is True
        assert _algebraic_to_float(algebraic) == pytest.approx(2 ** 0.5)
        assert _z3_expr_to_python_literal(z3.RealVal(2)) == 2
        assert _z3_expr_to_python_literal(algebraic) == pytest.approx(2 ** 0.5)

        with pytest.raises(TypeError, match='Expected a bool literal'):
            _python_literal_to_z3(1, z3.BoolSort())
        with pytest.raises(TypeError, match='Cannot substitute Python bool literal'):
            _python_literal_to_z3(True, z3.IntSort())
        with pytest.raises(TypeError, match='Expected an int or float literal'):
            _python_literal_to_z3('x', z3.RealSort())
        with pytest.raises(TypeError, match='Expected an int literal'):
            _python_literal_to_z3(1.5, z3.BitVecSort(8))
        with pytest.raises(TypeError, match='unsupported Z3 sort'):
            _python_literal_to_z3(1, z3.ArraySort(z3.IntSort(), z3.IntSort()))
        with pytest.raises(TypeError, match='Cannot substitute Z3 expression of sort'):
            _coerce_z3_expr_to_sort(z3.BoolVal(True), z3.IntSort())
        with pytest.raises(TypeError, match='Cannot convert simplified Z3 expression'):
            _z3_expr_to_python_literal(X + 1)

    def test_resolve_substitution_value_rejects_unsupported_value_type(self):
        """Test substitution resolution rejects unsupported mapping values."""
        with pytest.raises(TypeError, match='Unsupported substitution value type'):
            _resolve_substitution_value(
                name='x',
                target_sort=z3.IntSort(),
                substitutions={'x': object()},
                visiting=set(),
                cache={},
            )
