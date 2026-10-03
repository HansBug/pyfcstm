"""Tests for the operator catalog, the single definition of operator semantics."""
import math
import random

import pytest
import z3

from pyfcstm.semantics.catalog import (
    BOOL,
    CATALOG,
    COMPLEX_POWER_MESSAGE,
    EAGER,
    FLOAT,
    INT,
    MATH_DOMAIN_MESSAGE,
    NUMBER,
    SHORT_AND,
    SHORT_IMPLIES,
    SHORT_OR,
    canonical_token,
    coarse_result_type,
    lookup,
)

_BINARY_TOKENS = (
    "**", "*", "/", "%", "+", "-", "<<", ">>", "&", "^", "|",
    "<", ">", "<=", ">=", "==", "!=", "&&", "||", "=>", "xor", "iff",
)
_UNARY_TOKENS = ("unary+", "unary-", "!")
_FUNCTIONS = (
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "sqrt", "cbrt", "exp", "log", "log10", "log2", "log1p",
    "abs", "ceil", "floor", "round", "trunc", "sign",
)


def _z3_value(value):
    if isinstance(value, bool):
        return z3.BoolVal(value)
    if isinstance(value, int):
        return z3.IntVal(value)
    return z3.RealVal(value)


def _numeric_result(expr):
    value = z3.simplify(expr)
    if z3.is_int_value(value):
        return value.as_long()
    if z3.is_rational_value(value):
        return value.numerator_as_long() / value.denominator_as_long()
    if z3.is_true(value) or z3.is_false(value):
        return z3.is_true(value)
    raise AssertionError("not a numeral: %s" % (value,))


@pytest.mark.unittest
class TestCatalogInventory:
    def test_every_language_operator_and_function_is_registered_once(self):
        expected = set(_BINARY_TOKENS) | set(_UNARY_TOKENS) | set(_FUNCTIONS) | {"?:"}
        assert set(CATALOG) == expected

    @pytest.mark.parametrize("alias, token", [
        ("and", "&&"), ("or", "||"), ("not", "!"), ("implies", "=>"), ("+", "+"),
    ])
    def test_aliases_resolve_to_canonical_entries(self, alias, token):
        assert canonical_token(alias) == token
        assert lookup(alias) is CATALOG[token]

    def test_unknown_token_is_rejected(self):
        with pytest.raises(KeyError):
            lookup("hypot")

    def test_entry_kinds_and_arities(self):
        for token in _BINARY_TOKENS:
            assert (CATALOG[token].kind, CATALOG[token].arity) == ("binary", 2)
        for token in _UNARY_TOKENS:
            assert (CATALOG[token].kind, CATALOG[token].arity) == ("unary", 1)
        for token in _FUNCTIONS:
            assert (CATALOG[token].kind, CATALOG[token].arity) == ("function", 1)
        assert (CATALOG["?:"].kind, CATALOG["?:"].arity) == ("conditional", 3)


@pytest.mark.unittest
class TestEvaluationControl:
    @pytest.mark.parametrize("token, control", [
        ("&&", SHORT_AND), ("||", SHORT_OR), ("=>", SHORT_IMPLIES),
        ("xor", EAGER), ("iff", EAGER), ("+", EAGER), ("?:", EAGER),
    ])
    def test_control_strategy(self, token, control):
        assert lookup(token).control == control


@pytest.mark.unittest
class TestRunnableReference:
    @pytest.mark.parametrize("token, args, expected", [
        ("+", (1, 2), 3),
        ("-", (1, 2.5), -1.5),
        ("*", (3, 4), 12),
        ("/", (7, 2), 3.5),
        ("/", (4, 2), 2.0),
        ("%", (7, -2), -1),
        ("%", (-7, 2), 1),
        ("%", (7.5, 2), 1.5),
        ("**", (2, 3), 8),
        ("**", (2, -1), 0.5),
        ("**", (0, 0), 1),
        ("**", (-8, 2), 64),
        ("<<", (1, 3), 8),
        (">>", (-8, 1), -4),
        ("&", (6, 3), 2),
        ("|", (6, 3), 7),
        ("^", (6, 3), 5),
        ("<", (1, 2), True),
        ("==", (1, 1.0), True),
        ("&&", (True, False), False),
        ("||", (False, True), True),
        ("=>", (False, False), True),
        ("=>", (True, False), False),
        ("xor", (True, False), True),
        ("iff", (False, False), True),
        ("unary-", (3,), -3),
        ("unary+", (3,), 3),
        ("!", (0,), True),
        ("?:", (True, 1, 2), 1),
        ("?:", (False, 1, 2), 2),
        ("abs", (-3,), 3),
        ("floor", (-1.5,), -2),
        ("ceil", (-1.5,), -1),
        ("trunc", (-1.5,), -1),
        ("round", (2.5,), 2),
        ("round", (-0.5,), 0),
        ("sqrt", (9,), 3.0),
        ("exp", (0,), 1.0),
    ])
    def test_reference_values(self, token, args, expected):
        result = lookup(token).concrete(*args)
        assert result == expected
        assert type(result) is type(expected)

    @pytest.mark.parametrize("value, expected", [
        (-8, -2.0), (27, 3.0), (1000, 10.0), (0, 0.0), (-1e-300, -1e-100),
    ])
    def test_cbrt_is_the_real_cube_root(self, value, expected):
        assert lookup("cbrt").concrete(value) == expected

    def test_cbrt_keeps_non_finite_values(self):
        cbrt = lookup("cbrt").concrete
        assert cbrt(math.inf) == math.inf
        assert cbrt(-math.inf) == -math.inf
        assert math.isnan(cbrt(math.nan))

    def test_cbrt_is_exact_on_perfect_cubes_and_accurate_elsewhere(self):
        # The platform cbrt is not correctly rounded everywhere (glibc gives
        # 3.0000000000000004 for 27), so the catalog does not use it.
        cbrt = lookup("cbrt").concrete
        for n in range(-300, 301):
            assert cbrt(float(n ** 3)) == float(n)
        rng = random.Random(20261003)
        for value in [rng.uniform(-1e6, 1e6) for _ in range(200)]:
            assert cbrt(value) ** 3 == pytest.approx(value, rel=1e-12)

    def test_sign_of_nan_is_minus_one(self):
        assert lookup("sign").concrete(math.nan) == -1
        assert [lookup("sign").concrete(v) for v in (-2.5, 0.0, 3)] == [-1, 0, 1]

    @pytest.mark.parametrize("base, exponent", [(-8, 0.5), (-8.0, 1 / 3), (-1, 0.25)])
    def test_complex_power_is_a_runtime_error(self, base, exponent):
        spec = lookup("**")
        with pytest.raises(ValueError, match=COMPLEX_POWER_MESSAGE) as info:
            spec.concrete(base, exponent)
        assert spec.error_kind(info.value) == "complex_result"

    def test_negative_base_with_integral_float_exponent_is_real(self):
        assert lookup("**").concrete(-2, 2.0) == 4.0


@pytest.mark.unittest
class TestErrorRules:
    @pytest.mark.parametrize("token, args, kind", [
        ("/", (1, 0), "division_by_zero"),
        ("/", (1.0, 0.0), "division_by_zero"),
        ("%", (1, 0), "modulo_by_zero"),
        ("**", (0, -1), "zero_negative_power"),
        ("**", (10.0, 400), "overflow"),
        ("+", (10 ** 400, 1.0), "overflow"),
        ("<<", (1, -1), "negative_shift_count"),
        ("&", (1.5, 1), "invalid_operand"),
        (">>", (1.5, 1), "invalid_operand"),
        ("sqrt", (-1,), "math_domain"),
        ("log", (0,), "math_domain"),
        ("acos", (2,), "math_domain"),
        ("floor", (math.nan,), "math_domain"),
        ("floor", (math.inf,), "overflow"),
        ("exp", (1000,), "overflow"),
    ])
    def test_reference_errors_are_classified(self, token, args, kind):
        spec = lookup(token)
        with pytest.raises(BaseException) as info:
            spec.concrete(*args)
        assert spec.error_kind(info.value) == kind

    def test_unexplained_exception_has_no_kind(self):
        assert lookup("+").error_kind(KeyError("x")) is None

    def test_math_domain_rule_normalizes_message(self):
        rule = next(r for r in lookup("sqrt").errors if r.kind == "math_domain")
        assert rule.message == MATH_DOMAIN_MESSAGE == "math domain error"

    @pytest.mark.parametrize("token, args, violated", [
        ("/", (7, 0), True),
        ("/", (7, 2), False),
        ("%", (7, 0), True),
        ("**", (0, -2), True),
        ("**", (0, 2), False),
        ("**", (-8, 0.5), True),
        ("**", (-8, 2), False),
        ("**", (-8, 2.0), False),
        ("sqrt", (-1,), True),
        ("sqrt", (0,), False),
    ])
    def test_symbolic_definedness_matches_reference_errors(self, token, args, violated):
        spec = lookup(token)
        condition = z3.BoolVal(True)
        for rule in spec.errors:
            if rule.defined is not None:
                condition = z3.And(condition, rule.defined(*map(_z3_value, args)))
        assert z3.is_false(z3.simplify(condition)) is violated
        if violated:
            with pytest.raises((ZeroDivisionError, ValueError)):
                spec.concrete(*args)
        else:
            spec.concrete(*args)


@pytest.mark.unittest
class TestFormalReference:
    @pytest.mark.parametrize("token", ["+", "-", "*", "/", "%", "**"])
    def test_integer_arithmetic_agrees_with_reference(self, token):
        spec = lookup(token)
        rng = random.Random(hash(token) & 0xFFFF)
        for _ in range(300):
            left = rng.randint(-30, 30)
            right = rng.randint(-6, 6) if token == "**" else rng.randint(-30, 30)
            try:
                expected = spec.concrete(left, right)
            except (ZeroDivisionError, ValueError):
                continue
            assert _numeric_result(spec.symbolic(z3.IntVal(left), z3.IntVal(right))) == pytest.approx(expected)

    def test_floor_modulo_on_symbolic_integers(self):
        x, y = z3.Ints("x y")
        solver = z3.Solver()
        solver.add(y != 0, lookup("%").symbolic(x, y) != x - y * z3.ToInt(z3.ToReal(x) / z3.ToReal(y)))
        assert solver.check() == z3.unsat

    def test_real_modulo_takes_divisor_sign(self):
        assert _numeric_result(lookup("%").symbolic(z3.RealVal(7.5), z3.RealVal(-2))) == 7.5 % -2

    def test_true_division_of_integers_is_real(self):
        value = lookup("/").symbolic(z3.Int("x"), z3.IntVal(2))
        assert z3.is_real(value)
        assert lookup("/").symbolic(z3.Real("r"), z3.IntVal(2)).sort() == z3.RealSort()

    def test_zero_to_the_zero_is_one(self):
        x, y = z3.Ints("x y")
        solver = z3.Solver()
        solver.add(x == 0, y == 0, lookup("**").symbolic(x, y) != 1)
        assert solver.check() == z3.unsat

    def test_power_with_a_literal_operand_needs_no_zero_case(self):
        x = z3.Int("x")
        assert str(lookup("**").symbolic(x, z3.IntVal(2))) == "x**2"
        assert str(lookup("**").symbolic(z3.IntVal(2), x)) == "2**x"

    @pytest.mark.parametrize("func, value", [
        ("abs", -3), ("abs", 2.5), ("sign", -2.5), ("sign", 0), ("sign", 4),
        ("floor", -1.5), ("floor", 3), ("ceil", -1.5), ("ceil", 3),
        ("trunc", -1.5), ("trunc", 1.5), ("trunc", 3),
        ("round", 2.5), ("round", 3.5), ("round", -2.5), ("round", 2.4), ("round", 7),
        ("sqrt", 4),
    ])
    def test_exact_functions_agree_with_reference(self, func, value):
        spec = lookup(func)
        assert _numeric_result(spec.symbolic(_z3_value(value))) == pytest.approx(spec.concrete(value))

    def test_sign_is_integer_valued(self):
        assert z3.is_int(lookup("sign").symbolic(z3.Real("r")))

    def test_bool_operands_convert_for_integer_functions(self):
        assert z3.is_int(lookup("floor").symbolic(z3.Bool("b")))

    @pytest.mark.parametrize("token, args, expected", [
        ("&&", (True, False), False),
        ("||", (True, False), True),
        ("=>", (True, False), False),
        ("xor", (True, True), False),
        ("iff", (True, True), True),
        ("!", (True,), False),
        ("<", (1, 2), True),
        ("?:", (False, 1, 2), 2),
        ("unary-", (3,), -3),
        ("unary+", (3,), 3),
    ])
    def test_logic_and_comparison(self, token, args, expected):
        assert _numeric_result(lookup(token).symbolic(*map(_z3_value, args))) == expected

    @pytest.mark.parametrize("token", ["=>", "xor", "iff"])
    def test_logical_operators_reject_numeric_operands(self, token):
        with pytest.raises(ValueError, match="Boolean operands required for operator '%s'" % token):
            lookup(token).symbolic(z3.IntVal(1), z3.BoolVal(True))

    @pytest.mark.parametrize("token", ["&", "|", "^", "<<", ">>"])
    def test_bitwise_operators_have_no_default_encoding(self, token):
        spec = lookup(token)
        assert spec.symbolic is None
        assert "fixed-width" in spec.unsupported

    @pytest.mark.parametrize("func, family", [
        ("sin", "Trigonometric function"),
        ("exp", "Mathematical function"),
        ("log", "Logarithmic function"),
        ("cbrt", "Mathematical function"),
        ("atanh", "Hyperbolic function"),
    ])
    def test_transcendental_functions_have_no_encoding(self, func, family):
        spec = lookup(func)
        assert spec.symbolic is None
        assert spec.unsupported.startswith("%s '%s' is not directly supported in Z3." % (family, func))

    @pytest.mark.parametrize("base, exponent, expected", [
        (z3.Int("x"), z3.IntVal(2), "True"),
        (z3.IntVal(2), z3.Int("n"), "True"),
        (z3.Int("x"), z3.Int("n"), "Or(x != 0, n >= 0)"),
        (z3.Real("r"), z3.Int("n"), "Or(r != 0, n >= 0)"),
    ])
    def test_zero_negative_power_rule_is_static_when_operands_allow(self, base, exponent, expected):
        rule = next(r for r in lookup("**").errors if r.kind == "zero_negative_power")
        assert str(rule.defined(base, exponent)) == expected

    @pytest.mark.parametrize("base, exponent, expected", [
        (z3.Real("r"), z3.Int("n"), "True"),
        (z3.RealVal(4), z3.Real("e"), "True"),
        (z3.Real("r"), z3.RealVal(2), "True"),
        (z3.Real("r"), z3.Real("e"), "Or(r >= 0, IsInt(e))"),
    ])
    def test_complex_result_rule_is_static_when_operands_allow(self, base, exponent, expected):
        rule = next(r for r in lookup("**").errors if r.kind == "complex_result")
        assert str(rule.defined(base, exponent)) == expected


@pytest.mark.unittest
class TestTyping:
    @pytest.mark.parametrize("token, types, constants, expected", [
        ("+", (INT, INT), (None, None), INT),
        ("+", (INT, FLOAT), (None, None), FLOAT),
        ("+", (INT, NUMBER), (None, None), NUMBER),
        ("/", (INT, INT), (None, None), FLOAT),
        ("%", (INT, INT), (None, None), INT),
        ("**", (INT, INT), (None, 2), INT),
        ("**", (INT, INT), (None, -1), NUMBER),
        ("**", (INT, INT), (None, None), NUMBER),
        ("**", (FLOAT, INT), (None, 2), FLOAT),
        ("&", (INT, INT), (None, None), INT),
        ("<", (INT, FLOAT), (None, None), BOOL),
        ("=>", (BOOL, BOOL), (None, None), BOOL),
        ("unary-", (FLOAT,), (None,), FLOAT),
        ("!", (INT,), (None,), BOOL),
        ("?:", (BOOL, INT, INT), (None, None, None), INT),
        ("?:", (BOOL, INT, FLOAT), (None, None, None), NUMBER),
        ("abs", (FLOAT,), (None,), FLOAT),
        ("abs", (INT,), (None,), INT),
        ("sign", (FLOAT,), (None,), INT),
        ("trunc", (FLOAT,), (None,), INT),
        ("round", (FLOAT,), (None,), INT),
        ("sqrt", (INT,), (None,), FLOAT),
        ("cbrt", (INT,), (None,), FLOAT),
    ])
    def test_result_types(self, token, types, constants, expected):
        assert lookup(token).typing(types, constants) == expected

    def test_typing_tracks_runtime_result_types(self):
        rng = random.Random(7)
        names = {int: INT, float: FLOAT, bool: BOOL}
        for token in ("+", "-", "*", "/", "%"):
            spec = lookup(token)
            for _ in range(100):
                left = rng.choice([rng.randint(-9, 9), rng.uniform(-9, 9)])
                right = rng.choice([rng.randint(1, 9), rng.uniform(1, 9)])
                result = spec.concrete(left, right)
                assert spec.typing((names[type(left)], names[type(right)]), (None, None)) == names[type(result)]


@pytest.mark.unittest
@pytest.mark.parametrize(
    "token, operands, expected",
    [
        ("sign", ("float",), "int"),
        ("trunc", (None,), "int"),
        ("sqrt", ("int",), "float"),
        ("abs", ("int",), "int"),
        ("abs", (None,), None),
        ("+", ("int", "float"), "float"),
        ("<", ("int", "int"), "bool"),
    ],
)
def test_coarse_result_type_follows_the_catalog_typing(token, operands, expected):
    assert coarse_result_type(token, *operands) == expected
