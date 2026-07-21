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


def test_check_rejects_an_object_without_the_solver_interface() -> None:
    """The internal check helper reports an invalid solver object explicitly."""
    with pytest.raises(TypeError, match="solver must provide"):
        _check_with_budget(object(), _SolveBudget(None))


def test_check_rejects_an_object_without_the_budget_interface() -> None:
    """The internal check helper reports an invalid budget object explicitly."""

    class InvalidBudget:
        pass

    with pytest.raises(TypeError, match="budget must provide"):
        _check_with_budget(z3.Solver(), InvalidBudget())


def test_solver_module_examples_are_executable() -> None:
    """Solver module and helper docstring examples remain runnable."""
    result = doctest.testmod(solver_module)

    assert result.failed == 0
