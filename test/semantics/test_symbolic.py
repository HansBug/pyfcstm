"""Tests for the engine with the symbolic interpretation."""
import random
import warnings

import pytest
import z3

from pyfcstm.model.expr import BinaryOp, Boolean, ConditionalOp, Integer, Variable, parse_expr
from pyfcstm.semantics import ir
from pyfcstm.semantics.adapters import expression_from_model
from pyfcstm.semantics.concrete import evaluate
from pyfcstm.semantics.errors import EvaluationError
from pyfcstm.semantics.symbolic import (
    SYMBOLIC,
    SymbolicFailure,
    SymbolicInterpretation,
    SymbolicSession,
    translate,
)

X, Y = z3.Ints("x y")
R = z3.Real("r")
ENV = {"x": X, "y": Y, "r": R}


def _checker(facts, timeout_ms):
    solver = z3.Solver()
    solver.add(*facts)
    return str(solver.check())


def _translate(text, **options):
    session = SymbolicSession(**options)
    value, session = translate(expression_from_model(parse_expr(text)), ENV, session)
    return value, session


def _constraints(session):
    return [str(fact.constraint) for fact in session.definedness]


@pytest.mark.unittest
class TestSymbolicValues:
    def test_true_division_is_real(self):
        value, _ = _translate("x / 2")
        assert value.sort() == z3.RealSort()

    def test_literals(self):
        node = ir.Literal("e", None, True)
        assert z3.is_true(translate(node, {})[0])
        assert translate(ir.Literal("e", None, 2), {})[0].sort() == z3.IntSort()
        assert translate(ir.Literal("e", None, 2.5), {})[0].sort() == z3.RealSort()

    def test_missing_variable_is_a_value_error(self):
        with pytest.raises(SymbolicFailure) as info:
            _translate("z + 1")
        assert info.value.kind == "value_error"
        assert "Variable 'z' not found" in info.value.reason
        assert isinstance(info.value.error, ValueError)

    @pytest.mark.parametrize("text, kind", [
        ("x & 1", "not_implemented"),
        ("sin(r)", "not_implemented"),
    ])
    def test_operations_without_encoding_fail(self, text, kind):
        with pytest.raises(SymbolicFailure) as info:
            _translate(text)
        assert info.value.kind == kind

    def test_sqrt_of_a_boolean_is_rejected(self):
        node = ir.Call("e", None, "sqrt", (ir.Literal("e.0", None, True),))
        with pytest.raises(SymbolicFailure, match="sqrt requires Real or Int operand") as info:
            translate(node, {}, SymbolicSession(track_definedness=False))
        assert info.value.kind == "not_implemented"
        assert info.value.node is node

    def test_operand_sort_errors_fail(self):
        node = ir.Binary("e", None, "&&", ir.Literal("e.0", None, True), ir.Literal("e.1", None, 1))
        with pytest.raises(SymbolicFailure) as info:
            translate(node, {})
        assert info.value.kind in ("type_error", "z3_error")

    @pytest.mark.parametrize("node, kind, message", [
        (ir.Call("e", None, "hypot", (ir.Literal("e.0", None, 1),)), "not_implemented", "'hypot' is not supported"),
        (ir.Unary("e", None, "~", ir.Literal("e.0", None, 1)), "value_error", "Unsupported unary operator: ~"),
        (
            ir.Binary("e", None, "<=>", ir.Literal("e.0", None, 1), ir.Literal("e.1", None, 2)),
            "value_error",
            "Unsupported binary operator: <=>",
        ),
        (ir.HostAtom("e", None, "test.atom"), "value_error", "Unsupported host atom: test.atom"),
    ])
    def test_unknown_operations_fail(self, node, kind, message):
        with pytest.raises(SymbolicFailure, match=message) as info:
            translate(node, {})
        assert info.value.kind == kind

    def test_non_boolean_short_circuit_operand_fails(self):
        node = expression_from_model(BinaryOp(Integer(1), "&&", Boolean(True)))
        with pytest.raises(SymbolicFailure, match="requires a Boolean left operand") as info:
            translate(node, {})
        assert info.value.kind == "type_error"

    def test_non_boolean_conditional_test_fails(self):
        node = expression_from_model(ConditionalOp(Integer(1), Integer(2), Integer(3)))
        with pytest.raises(SymbolicFailure) as info:
            translate(node, {})
        assert info.value.kind in ("type_error", "z3_error")

    def test_symbolic_and_concrete_agree_on_random_integer_expressions(self):
        # Integer arithmetic must agree exactly.  True division produces
        # floats, where IEEE rounding and exact reals may legitimately differ
        # (``4 % (-2 / 3)``), so it is covered by the catalog tests instead.
        rng = random.Random(522)
        operators = ["+", "-", "*", "%", "**"]

        def build(depth):
            if depth == 0 or rng.random() < 0.3:
                return rng.choice([Variable("x"), Variable("y"), Integer(rng.randint(-5, 5))])
            op = rng.choice(operators)
            right = Integer(rng.randint(0, 3)) if op == "**" else build(depth - 1)
            return BinaryOp(build(depth - 1), op, right)

        checked = 0
        for _ in range(300):
            expr = build(3)
            value, session = translate(expression_from_model(expr), ENV)
            for x in (-4, 0, 3):
                for y in (-2, 0, 5):
                    try:
                        expected = evaluate(expr, {"x": x, "y": y})
                    except EvaluationError:
                        defined = z3.substitute(
                            z3.And(*[fact.constraint for fact in session.definedness] or [z3.BoolVal(True)]),
                            (X, z3.IntVal(x)),
                            (Y, z3.IntVal(y)),
                        )
                        assert z3.is_false(z3.simplify(defined))
                        continue
                    result = z3.simplify(z3.substitute(value, (X, z3.IntVal(x)), (Y, z3.IntVal(y))))
                    if z3.is_int_value(result):
                        actual = result.as_long()
                    else:
                        actual = result.numerator_as_long() / result.denominator_as_long()
                    assert actual == pytest.approx(expected)
                    checked += 1
        assert checked > 1000


@pytest.mark.unittest
class TestDefinedness:
    def test_eager_operations_record_unguarded_facts(self):
        _, session = _translate("10 / x + y % 3")
        assert _constraints(session) == ["x != 0", "3 != 0"]
        assert [fact.kind for fact in session.definedness] == ["division_by_zero", "modulo_by_zero"]
        assert session.definedness[0].guards == ()

    def test_short_circuit_operands_are_guarded(self):
        _, session = _translate("x == 0 || 10 / x > 1")
        assert _constraints(session) == ["Implies(Not(0 == x), x != 0)"]
        _, session = _translate("x != 0 && 10 / x > 1")
        assert _constraints(session) == ["Implies(0 != x, x != 0)"]
        _, session = _translate("x != 0 => 10 / x > 1")
        assert _constraints(session) == ["Implies(0 != x, x != 0)"]

    def test_nested_guards_nest_implications(self):
        _, session = _translate("x > 0 && (y > 0 && 10 / y > x)")
        assert _constraints(session) == ["Implies(0 < x, Implies(0 < y, y != 0))"]
        assert [str(guard) for guard in session.definedness[0].guards] == ["0 < x", "0 < y"]

    def test_eager_logical_operators_do_not_guard(self):
        _, session = _translate("(x == 0) xor (10 / x > 1)")
        assert _constraints(session) == ["x != 0"]

    def test_conditional_branches_are_guarded_even_by_literal_conditions(self):
        _, session = _translate("(x > 0) ? 10 / x : 20 / y")
        assert _constraints(session) == ["Implies(0 < x, x != 0)", "Implies(Not(0 < x), y != 0)"]
        _, session = _translate("(true) ? 10 / x : 1")
        assert _constraints(session) == ["Implies(True, x != 0)"]

    def test_power_and_sqrt_facts(self):
        _, session = _translate("x ** y + sqrt(r)")
        assert _constraints(session) == ["Or(x != 0, y >= 0)", "r >= 0"]
        _, session = _translate("r ** r")
        assert _constraints(session) == ["Or(r != 0, r >= 0)", "Or(r >= 0, IsInt(r))"]

    def test_tracking_can_be_switched_off(self):
        _, session = _translate("10 / x", track_definedness=False)
        assert session.definedness == []


@pytest.mark.unittest
class TestReachability:
    def test_unreachable_short_circuit_operand_is_skipped(self):
        value, session = _translate("x > 0 && x < 0 && 10 / y > 1", checker=_checker)
        assert _constraints(session) == []
        assert [check.status for check in session.checks] == ["sat", "unsat"]
        assert z3.is_false(z3.simplify(value)) or "And" in str(value)

    def test_literal_false_operand_needs_no_check(self):
        value, session = _translate("false && 10 / x > 1", checker=_checker)
        assert z3.is_false(value)
        assert session.checks == []
        value, session = _translate("true || 10 / x > 1", checker=_checker)
        assert z3.is_true(value)
        assert session.checks == []

    def test_literal_true_operand_is_still_checked(self):
        _, session = _translate("true && 10 / x > 1", checker=_checker)
        assert [str(check.selector) for check in session.checks] == ["True"]
        assert _constraints(session) == ["x != 0"]

    def test_conditional_with_one_reachable_branch_is_unguarded(self):
        value, session = _translate(
            "(x > 0) ? 10 / x : 20 / y",
            checker=_checker,
            assumptions=(X == 3,),
        )
        assert str(value) == "10/ToReal(x)"
        assert _constraints(session) == ["x != 0"]
        assert [check.status for check in session.checks] == ["sat", "unsat"]

    def test_conditional_without_reachable_branch_fails(self):
        with pytest.raises(SymbolicFailure) as info:
            _translate("(x > 0) ? 1 : 2", checker=_checker, assumptions=(z3.BoolVal(False),))
        assert info.value.kind == "no_reachable_branch"

    def test_earlier_definedness_prunes_later_branches(self):
        # 10 / x requires x != 0, so the conditional's x == 0 branch is dead.
        value, session = _translate("10 / x + ((x == 0) ? 1 : 2)", checker=_checker)
        assert z3.simplify(value - 10 / z3.ToReal(X)).eq(z3.simplify(z3.IntVal(2) + 0)) or "If" not in str(value)
        assert "unsat" in [check.status for check in session.checks]

    def test_unknown_status_keeps_the_branch(self):
        _, session = _translate("(x > 0) ? 1 : 2", checker=lambda facts, timeout: "timeout")
        assert [check.status for check in session.checks] == ["unknown", "unknown"]

    def test_conditions_are_observed_with_their_path(self):
        _, session = _translate("x > 0 && ((y > 0) ? 1 : 2) > 0", observe_conditions=True)
        (observation,) = session.conditions
        assert str(observation.condition) == "0 < y"
        assert [str(item) for item in observation.path] == ["0 < x"]
        assert isinstance(observation.node, ir.Conditional)


@pytest.mark.unittest
class TestWarnings:
    def test_variable_exponent_warns_at_the_caller(self):
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            _translate("2 ** x")
        assert len(records) == 1
        assert "variable exponent" in str(records[0].message)
        assert records[0].filename == __file__

    def test_two_variable_power_warns(self):
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            _translate("x ** y")
        assert "two variables" in str(records[0].message)

    def test_constant_exponent_does_not_warn(self):
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            _translate("x ** 2")
        assert records == []


@pytest.mark.unittest
class TestHostExtension:
    def test_host_atoms_are_resolved_by_subclasses(self):
        class Host(SymbolicInterpretation):
            def host_atom(self, node, args, env, ctx):
                return env["x"] + args[0]

        node = ir.Binary(
            "e",
            None,
            "/",
            ir.Literal("e.0", None, 1),
            ir.HostAtom("e.1", None, "test.shift", None, (ir.Literal("e.1.0", None, 2),)),
        )
        value, session = translate(node, ENV, interpretation=Host())
        assert str(value) == "1/ToReal(x + 2)"
        assert _constraints(session) == ["x + 2 != 0"]

    def test_shared_instance(self):
        assert isinstance(SYMBOLIC, SymbolicInterpretation)
