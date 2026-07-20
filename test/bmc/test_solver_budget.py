"""Regression tests for the shared BMC solver budget primitive."""

from __future__ import annotations

import z3
import pytest

from pyfcstm.bmc.solver import _SolveBudget, _check_with_budget
from pyfcstm.bmc.errors import BmcBuildError


def test_unbounded_budget_does_not_configure_solver_timeout() -> None:
    """``None`` must call Z3 without setting a timeout."""
    solver = z3.Solver()
    budget = _SolveBudget(None)

    status, model, reason, elapsed_ms, check_started = _check_with_budget(
        solver, budget
    )

    assert status == "sat"
    assert model is not None
    assert reason is None
    assert elapsed_ms >= 0
    assert check_started is True
    assert solver.sexpr() == ""


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


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, "10"])
def test_budget_rejects_invalid_timeout(value) -> None:
    """Only ``None`` or a positive integer is accepted."""
    with pytest.raises(BmcBuildError, match="timeout_ms"):
        _SolveBudget(value)
