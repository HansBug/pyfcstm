"""Tests for solver-layer expression runtime-domain translation."""

from dataclasses import FrozenInstanceError
from typing import List, cast

import pytest
import z3

from pyfcstm.model.expr import BinaryOp, Boolean, Expr, Integer, UFunc, UnaryOp, Variable
from pyfcstm.solver.expr import expr_to_z3


def bool_expr(item) -> z3.ExprRef:
    """Cast a Z3 boolean expression through the broad upstream stubs."""
    return cast(z3.ExprRef, item)


def exprs(*items) -> List[z3.ExprRef]:
    """Cast Z3 expressions through the broad upstream stubs."""
    return [cast(z3.ExprRef, item) for item in items]


@pytest.mark.unittest
class TestDomainDataStructures:
    """Test the frozen pure-data objects exposed by solver.domain."""

    def test_domain_source_is_frozen_and_preserves_tracking_fields(self):
        """Source labels are pure metadata, not solver semantics."""
        from pyfcstm.solver.domain import DomainSource

        source = DomainSource(
            label="guard",
            step=3,
            snapshot="before",
            prefix_id="root.init",
        )

        assert source.label == "guard"
        assert source.step == 3
        assert source.snapshot == "before"
        assert source.prefix_id == "root.init"
        with pytest.raises(FrozenInstanceError):
            setattr(source, "step", 4)

    def test_translation_failure_is_pure_solver_data(self):
        """Translation failures do not carry verification or diagnostic results."""
        from pyfcstm.solver.domain import DomainSource, TranslationFailure

        source = DomainSource(label="expr")
        failure = TranslationFailure(
            kind="not_implemented",
            reason="unsupported function",
            source=source,
        )

        assert failure.kind == "not_implemented"
        assert failure.reason == "unsupported function"
        assert failure.source is source
        assert not hasattr(failure, "diagnostics")
        assert not hasattr(failure, "severity")


@pytest.mark.unittest
class TestTranslateExprDomain:
    """Test domain-aware expression translation."""

    def test_division_returns_z3_value_and_denominator_definedness(self):
        """Division is still translated while the non-zero divisor is returned."""
        from pyfcstm.solver.domain import translate_expr_domain

        x, y = z3.Ints("x y")
        expr = BinaryOp(Variable("x"), "/", Variable("y"))

        result = translate_expr_domain(expr, {"x": x, "y": y})

        assert result.failure is None
        assert result.z3_expr is not None
        assert str(result.z3_expr) == str(expr_to_z3(expr, {"x": x, "y": y}))
        assert [str(item.constraint) for item in result.definedness_constraints] == [
            "y != 0"
        ]

        solver = z3.Solver()
        solver.add(result.definedness_constraints[0].constraint, y == 0)
        assert solver.check() == z3.unsat

    def test_generated_definedness_preserves_domain_source(self):
        """Generated constraints keep pure source metadata for later callers."""
        from pyfcstm.solver.domain import DomainSource, translate_expr_domain

        x, y = z3.Ints("x y")
        source = DomainSource(label="guard", step=2, snapshot="before")
        result = translate_expr_domain(
            BinaryOp(Variable("x"), "/", Variable("y")),
            {"x": x, "y": y},
            source=source,
        )

        assert result.failure is None
        assert result.definedness_constraints[0].source is source

    def test_modulo_returns_non_zero_divisor_definedness(self):
        """Modulo has the same runtime-domain constraint as division."""
        from pyfcstm.solver.domain import translate_expr_domain

        x, y = z3.Ints("x y")
        result = translate_expr_domain(
            BinaryOp(Variable("x"), "%", Variable("y")),
            {"x": x, "y": y},
        )

        assert result.failure is None
        assert [str(item.constraint) for item in result.definedness_constraints] == [
            "y != 0"
        ]

    def test_binary_left_child_failure_short_circuits(self):
        """A failed left operand is returned before translating the right operand."""
        from pyfcstm.solver.domain import translate_expr_domain

        result = translate_expr_domain(BinaryOp(Variable("missing"), "+", Integer(1)), {})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "value_error"
        assert "missing" in result.failure.reason

    def test_binary_right_child_failure_short_circuits(self):
        """A failed right operand is returned before applying the operator."""
        from pyfcstm.solver.domain import translate_expr_domain

        result = translate_expr_domain(
            BinaryOp(Integer(1), "+", Variable("missing")),
            {},
        )

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "value_error"
        assert "missing" in result.failure.reason

    def test_unknown_binary_operator_is_structured_failure(self):
        """Unknown operators are normalized instead of leaking raw exceptions."""
        from pyfcstm.solver.domain import translate_expr_domain

        result = translate_expr_domain(BinaryOp(Integer(1), "???", Integer(2)), {})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "value_error"
        assert "???" in result.failure.reason

    def test_unary_operator_preserves_child_definedness_on_failure(self):
        """Unary failures keep child definedness constraints for caller context."""
        from pyfcstm.solver.domain import translate_expr_domain

        x, y = z3.Ints("x y")
        expr = UnaryOp("???", BinaryOp(Variable("x"), "/", Variable("y")))

        result = translate_expr_domain(expr, {"x": x, "y": y})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "value_error"
        assert [str(item.constraint) for item in result.definedness_constraints] == [
            "y != 0"
        ]

    def test_sqrt_returns_non_negative_operand_definedness(self):
        """Square root preserves the value translation and adds ``operand >= 0``."""
        from pyfcstm.solver.domain import translate_expr_domain

        x = z3.Real("x")
        expr = UFunc("sqrt", Variable("x"))

        result = translate_expr_domain(expr, {"x": x})

        assert result.failure is None
        assert result.z3_expr is not None
        assert str(result.z3_expr) == str(expr_to_z3(expr, {"x": x}))
        assert [str(item.constraint) for item in result.definedness_constraints] == [
            "x >= 0"
        ]

    def test_sqrt_rejects_boolean_operand_as_structured_failure(self):
        """Malformed sqrt operands become pure failures with no verification data."""
        from pyfcstm.solver.domain import translate_expr_domain

        result = translate_expr_domain(UFunc("sqrt", Boolean(True)), {})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind in ("type_error", "z3_error")
        assert result.definedness_constraints == ()

    def test_ufunc_child_failure_short_circuits(self):
        """A failed function operand is returned before applying the function."""
        from pyfcstm.solver.domain import translate_expr_domain

        result = translate_expr_domain(UFunc("sqrt", Variable("missing")), {})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "value_error"
        assert "missing" in result.failure.reason

    def test_round_keeps_existing_value_translation_without_definedness(self):
        """The domain layer does not redefine Python round semantics."""
        from pyfcstm.solver.domain import translate_expr_domain

        x = z3.Real("x")
        expr = UFunc("round", Variable("x"))

        result = translate_expr_domain(expr, {"x": x})

        assert result.failure is None
        assert result.z3_expr is not None
        assert str(result.z3_expr) == str(expr_to_z3(expr, {"x": x}))
        assert result.definedness_constraints == ()

    def test_unreachable_conditional_branch_is_pruned_before_translation(self):
        """Unselected value branches can contain unsupported expressions."""
        from pyfcstm.solver.domain import translate_expr_domain

        x = z3.Real("x")
        expr = Boolean(True).select(Integer(1), UFunc("sin", Variable("x")))

        result = translate_expr_domain(expr, {"x": x})

        assert result.failure is None
        assert result.z3_expr is not None
        assert str(z3.simplify(result.z3_expr)) == "1"
        assert result.definedness_constraints == ()
        assert [item.status for item in result.feasibility_checks] == ["sat", "unsat"]

    def test_pruned_conditional_stays_pruned_inside_outer_expression(self):
        """Outer expressions use pruned child Z3 values, not raw child ASTs."""
        from pyfcstm.solver.domain import translate_expr_domain

        x = z3.Real("x")
        inner = Boolean(True).select(Integer(1), UFunc("sin", Variable("x")))
        expr = BinaryOp(inner, "+", Integer(1))

        result = translate_expr_domain(expr, {"x": x})

        assert result.failure is None
        assert result.z3_expr is not None
        assert str(z3.simplify(result.z3_expr)) == "2"
        assert result.definedness_constraints == ()

    def test_pruning_can_be_disabled_for_research_callers(self):
        """Disabling pruning translates both branches and exposes branch failures."""
        from pyfcstm.solver.domain import translate_expr_domain

        x = z3.Real("x")
        expr = Boolean(True).select(Integer(1), UFunc("sin", Variable("x")))

        result = translate_expr_domain(expr, {"x": x}, prune_unreachable=False)

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "not_implemented"
        assert result.feasibility_checks == ()

    def test_only_false_conditional_branch_can_survive_pruning(self):
        """A proved-false selector returns the false value without true failures."""
        from pyfcstm.solver.domain import translate_expr_domain

        x = z3.Real("x")
        expr = Boolean(False).select(UFunc("sin", Variable("x")), Integer(3))

        result = translate_expr_domain(expr, {"x": x})

        assert result.failure is None
        assert result.z3_expr is not None
        assert str(z3.simplify(result.z3_expr)) == "3"
        assert [item.status for item in result.feasibility_checks] == ["unsat", "sat"]

    def test_reachable_conditional_branch_failure_is_structured(self):
        """Symbolic reachable branches are translated and can fail structurally."""
        from pyfcstm.solver.domain import translate_expr_domain

        flag = z3.Bool("flag")
        x = z3.Real("x")
        expr = Variable("flag").select(Integer(1), UFunc("sin", Variable("x")))

        result = translate_expr_domain(expr, {"flag": flag, "x": x})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "not_implemented"
        assert "sin" in result.failure.reason

    def test_non_boolean_conditional_condition_is_structured_failure(self):
        """Malformed ternary conditions are returned as pure translation failures."""
        from pyfcstm.solver.domain import translate_expr_domain

        result = translate_expr_domain(Integer(1).select(Integer(2), Integer(3)), {})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "z3_error"

    def test_reachable_conditional_domain_constraints_are_selector_wrapped(self):
        """Value branch domain constraints are qualified by their selector."""
        from pyfcstm.solver.domain import translate_expr_domain

        flag = z3.Bool("flag")
        x = z3.Int("x")
        expr = Variable("flag").select(
            BinaryOp(Variable("x"), "/", Integer(2)),
            Integer(0),
        )

        result = translate_expr_domain(expr, {"flag": flag, "x": x})

        assert result.failure is None
        assert [str(item.constraint) for item in result.definedness_constraints] == [
            "Implies(flag, 2 != 0)"
        ]

    def test_false_branch_domain_constraints_are_selector_wrapped(self):
        """False-branch domain constraints are guarded by the negated selector."""
        from pyfcstm.solver.domain import translate_expr_domain

        flag = z3.Bool("flag")
        x = z3.Int("x")
        expr = Variable("flag").select(
            Integer(0),
            BinaryOp(Variable("x"), "/", Integer(2)),
        )

        result = translate_expr_domain(expr, {"flag": flag, "x": x})

        assert result.failure is None
        assert [str(item.constraint) for item in result.definedness_constraints] == [
            "Implies(Not(flag), 2 != 0)"
        ]

    def test_contradictory_assumptions_report_no_reachable_branch(self):
        """If both selectors are impossible, no fake value is manufactured."""
        from pyfcstm.solver.domain import translate_expr_domain

        flag = z3.Bool("flag")
        result = translate_expr_domain(
            Variable("flag").select(Integer(1), Integer(0)),
            {"flag": flag},
            assumptions=exprs(flag, z3.Not(flag)),
        )

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "no_reachable_branch"
        assert [item.status for item in result.feasibility_checks] == ["unsat", "unsat"]

    def test_unknown_branch_feasibility_does_not_prune(self, monkeypatch):
        """Unknown branch reachability keeps branches live and records metadata."""
        from pyfcstm.solver import domain
        from pyfcstm.solver.domain import translate_expr_domain
        from pyfcstm.solver.logical import SatResult

        calls = []

        def always_unknown(constraints, *, timeout_ms=None, get_model=False):
            calls.append((tuple(constraints), timeout_ms, get_model))
            return SatResult(kind="unknown")

        monkeypatch.setattr(domain, "is_sat", always_unknown)
        flag = z3.Bool("flag")
        x = z3.Int("x")
        expr = Variable("flag").select(
            BinaryOp(Variable("x"), "/", Integer(2)),
            Integer(0),
        )

        result = translate_expr_domain(
            expr,
            {"flag": flag, "x": x},
            timeout_ms=9,
        )

        assert result.failure is None
        assert len(calls) == 2
        assert {item.status for item in result.feasibility_checks} == {"unknown"}
        assert [str(item.constraint) for item in result.definedness_constraints] == [
            "Implies(flag, 2 != 0)"
        ]

    def test_assumptions_are_preserved_but_path_conditions_are_not_stored(self):
        """Path conditions guide pruning while assumptions stay in the result."""
        from pyfcstm.solver.domain import translate_expr_domain

        flag = z3.Bool("flag")
        expr = Variable("flag").select(Integer(1), Integer(0))

        result = translate_expr_domain(
            expr,
            {"flag": flag},
            assumptions=exprs(flag == z3.BoolVal(True)),
            path_conditions=exprs(flag),
        )

        assert result.failure is None
        assert result.assumptions == (flag == z3.BoolVal(True),)
        assert not hasattr(result, "path_conditions")

    def test_expected_translation_failure_has_no_z3_value(self):
        """Failure and translated value are mutually exclusive."""
        from pyfcstm.solver.domain import translate_expr_domain

        result = translate_expr_domain(Variable("missing"), {})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "value_error"
        assert "missing" in result.failure.reason

    def test_unsupported_expression_object_is_structured_failure(self):
        """Unknown expression subclasses fail loudly as pure solver data."""
        from pyfcstm.solver.domain import translate_expr_domain

        class UnknownExpr(Expr):
            pass

        result = translate_expr_domain(UnknownExpr(), {})

        assert result.z3_expr is None
        assert result.failure is not None
        assert result.failure.kind == "value_error"
        assert "UnknownExpr" in result.failure.reason


@pytest.mark.unittest
class TestMergeDefinednessConstraints:
    """Test domain constraint collection merging."""

    def test_merge_accepts_expr_domain_and_direct_constraints(self):
        """The merge helper flattens supported inputs in order."""
        from pyfcstm.solver.domain import (
            DomainConstraint,
            DomainSource,
            ExprDomain,
            merge_definedness_constraints,
        )

        x = z3.Int("x")
        source = DomainSource(label="direct")
        direct = DomainConstraint(bool_expr(x != 0), source=source)
        from_domain = ExprDomain(
            z3_expr=x,
            definedness_constraints=(DomainConstraint(bool_expr(x >= 0)),),
        )

        merged = merge_definedness_constraints(from_domain, [direct])

        assert [str(item.constraint) for item in merged] == ["x >= 0", "x != 0"]
        assert merged[1].source is source

    def test_merge_preserves_contradictory_constraints(self):
        """Merging does not hide contradictions or run solver policy."""
        from pyfcstm.solver.domain import DomainConstraint, merge_definedness_constraints

        x = z3.Int("x")
        merged = merge_definedness_constraints(
            DomainConstraint(bool_expr(x > 0)),
            DomainConstraint(bool_expr(x < 0)),
        )

        solver = z3.Solver()
        solver.add(*[item.constraint for item in merged])
        assert solver.check() == z3.unsat

    def test_merge_rejects_unknown_input_shape(self):
        """Unsupported merge inputs fail loudly instead of being swallowed."""
        from pyfcstm.solver.domain import merge_definedness_constraints

        with pytest.raises(TypeError, match="Unsupported definedness item"):
            merge_definedness_constraints(object())

    def test_merge_rejects_unknown_nested_input_shape(self):
        """Nested iterables may contain only domain constraints."""
        from pyfcstm.solver.domain import merge_definedness_constraints

        with pytest.raises(TypeError, match="Unsupported definedness item"):
            merge_definedness_constraints([object()])
