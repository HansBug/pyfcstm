"""A monotonic budget distinguishes exhaustion from an unlimited request."""

import time

import pytest


pytestmark = pytest.mark.unittest


def test_unlimited_and_finite_deadlines_have_distinct_state():
    from pyfcstm.solver.budget import SolveBudget

    unlimited = SolveBudget(None)
    assert unlimited.deadline is None
    assert unlimited.remaining_ms() is None
    finite = SolveBudget(10000)
    assert finite.deadline is not None
    assert 0 < finite.remaining_ms() <= 10000


def test_expired_budget_cannot_be_mistaken_for_unlimited():
    from pyfcstm.solver.budget import SolveBudget

    budget = SolveBudget(1)
    time.sleep(0.005)
    assert budget.deadline is not None
    assert budget.remaining_ms() is None


@pytest.mark.parametrize('value', [0, -1, True, 1.2, '100'])
def test_invalid_budget_is_rejected(value):
    from pyfcstm.solver.budget import SolveBudget

    with pytest.raises(ValueError):
        SolveBudget(value)
