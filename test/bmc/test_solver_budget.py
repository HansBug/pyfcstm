"""Regression tests for the shared BMC solver budget primitive."""

from __future__ import annotations

import doctest

import z3
import pytest

import pyfcstm.bmc.solver as solver_module
from pyfcstm.bmc.solver import _SolveBudget, _check_with_budget
from pyfcstm.bmc.errors import BmcBuildError

pytestmark = pytest.mark.unittest


def test_unbounded_budget_does_not_configure_solver_timeout(monkeypatch) -> None:
    """``None`` must call Z3 without setting a timeout."""
    solver = z3.Solver()
    budget = _SolveBudget(None)
    set_calls = []
    original_set = solver.set

    def record_set(*args, **kwargs):
        set_calls.append((args, kwargs))
        return original_set(*args, **kwargs)

    monkeypatch.setattr(solver, "set", record_set)

    status, model, reason, elapsed_ms, check_started = _check_with_budget(
        solver, budget
    )

    assert status == "sat"
    assert model is not None
    assert reason is None
    assert elapsed_ms >= 0
    assert check_started is True
    assert set_calls == []


def test_budget_reports_deadline_exhaustion_before_check(monkeypatch) -> None:
    """An exhausted finite budget must not invoke the solver."""
    solver = z3.Solver()
    budget = _SolveBudget(1)
    monkeypatch.setattr(budget, "remaining_ms", lambda: None)

    called = False

    def fail_check():
        nonlocal called
        called = True
        raise AssertionError("solver.check must not run")

    monkeypatch.setattr(solver, "check", fail_check)
    result = _check_with_budget(solver, budget)

    assert result == (
        "timeout",
        None,
        "deadline_exhausted_before_check",
        0.0,
        False,
    )
    assert called is False


def test_budget_rounds_positive_fractional_milliseconds_up(monkeypatch) -> None:
    """A positive sub-millisecond remainder must still reach Z3 as one ms."""
    clock = iter((100.0, 100.0005))
    monkeypatch.setattr(solver_module.time, "monotonic", lambda: next(clock))

    budget = _SolveBudget(1)

    assert budget.remaining_ms() == 1


def test_budget_never_rounds_above_configured_timeout(monkeypatch) -> None:
    """Clock precision cannot make a check exceed its configured budget."""
    clock = iter((100.0, 99.9999))
    monkeypatch.setattr(solver_module.time, "monotonic", lambda: next(clock))

    budget = _SolveBudget(1)

    assert budget.remaining_ms() == 1


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, "10"])
def test_budget_rejects_invalid_timeout(value) -> None:
    """Only ``None`` or a positive integer is accepted."""
    with pytest.raises(BmcBuildError, match="timeout_ms"):
        _SolveBudget(value)


def test_solver_module_examples_are_executable() -> None:
    """Solver module and helper docstring examples remain runnable."""
    result = doctest.testmod(solver_module)

    assert result.failed == 0


_INFEASIBLE_ASSUMPTIONS = """
def int x = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B;
}
"""
_INFEASIBLE_ASSUMPTIONS_QUERY = (
    'init state("Root.A") where x == 0; '
    'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
    'check reach <= 2: active("Root.B");'
)


def _compile_formula(dsl_text: str, query_text: str):
    from pyfcstm.bmc import compile_bmc_query
    from pyfcstm.model import load_state_machine_from_text

    return compile_bmc_query(load_state_machine_from_text(dsl_text), query_text)


def _cancel_from_call(monkeypatch, first_cancelled_call: int):
    """Make ``z3.Solver.check`` raise ``canceled`` from the given call on.

    Z3 raises ``Z3Exception('canceled')`` from ``check`` when a timeout fires
    inside some engines; the earlier calls keep the real behaviour.
    """
    real_check = z3.Solver.check
    calls = []

    def check(self, *assumptions):
        calls.append(None)
        if len(calls) >= first_cancelled_call:
            raise z3.Z3Exception(b"canceled")
        return real_check(self, *assumptions)

    monkeypatch.setattr(z3.Solver, "check", check)
    return calls


def test_budget_cancellation_raised_by_z3_is_an_undecided_check(monkeypatch) -> None:
    """A budgeted check that Z3 cancels by exception reports ``unknown``."""
    _cancel_from_call(monkeypatch, 1)

    status, model, reason, elapsed_ms, check_started = _check_with_budget(
        z3.Solver(), _SolveBudget(5_000)
    )

    assert (status, model, reason, check_started) == ("unknown", None, "canceled", True)
    assert elapsed_ms >= 0


def test_cancellation_without_a_budget_is_a_real_error(monkeypatch) -> None:
    """With no timeout set, ``canceled`` cannot be a budget cut and propagates."""
    _cancel_from_call(monkeypatch, 1)

    with pytest.raises(z3.Z3Exception):
        _check_with_budget(z3.Solver(), _SolveBudget(None))


def test_other_z3_errors_propagate_under_a_budget(monkeypatch) -> None:
    """Only the cancellation message is converted; other Z3 errors still raise."""

    def check(self, *assumptions):
        raise z3.Z3Exception("invalid argument")

    monkeypatch.setattr(z3.Solver, "check", check)

    with pytest.raises(z3.Z3Exception, match="invalid argument"):
        _check_with_budget(z3.Solver(), _SolveBudget(5_000))


@pytest.mark.parametrize("first_cancelled_call", range(1, 12))
@pytest.mark.parametrize("explanation", ["none", "formal", "proof"])
def test_solving_never_raises_when_the_budget_cancels_a_check(
    monkeypatch, first_cancelled_call, explanation
) -> None:
    """Public solving returns a result wherever the budget cancels a check."""
    from pyfcstm.bmc import solve_bmc_property

    formula = _compile_formula(_INFEASIBLE_ASSUMPTIONS, _INFEASIBLE_ASSUMPTIONS_QUERY)
    _cancel_from_call(monkeypatch, first_cancelled_call)

    result = solve_bmc_property(
        formula, timeout_ms=60_000, infeasibility_explanation=explanation
    )

    assert result.status in ("sat", "unsat", "unknown", "timeout")


def test_solving_without_a_timeout_still_raises_on_cancellation(monkeypatch) -> None:
    """``timeout_ms=None`` keeps the original behaviour for a cancelled check."""
    from pyfcstm.bmc import solve_bmc_property

    formula = _compile_formula(_INFEASIBLE_ASSUMPTIONS, _INFEASIBLE_ASSUMPTIONS_QUERY)
    _cancel_from_call(monkeypatch, 1)

    with pytest.raises(z3.Z3Exception):
        solve_bmc_property(formula, timeout_ms=None)
