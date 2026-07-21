"""Shared Z3 checking-budget primitives for the BMC pipeline.

The BMC solver uses one monotonic optional budget across primary solving,
feasibility localization, and later refinement checks.  ``None`` deliberately
means that no Z3 timeout is configured and no hidden deadline is introduced.
This module contains only the budget/check mechanics; verdict interpretation,
source provenance, and explanation policy belong to other BMC layers.

The leading underscore on the two exported implementation names is
intentional.  They are shared internal primitives, not part of the public BMC
API.  They remain documented because later internal modules depend on their
exact ``check_started`` and reason semantics.

Examples::

    >>> import z3
    >>> budget = _SolveBudget(None)
    >>> _check_with_budget(z3.Solver(), budget)[0]
    'sat'
"""

from __future__ import annotations

import math
import time
from typing import Optional, Tuple

import z3

from .errors import BmcBuildError


class _SolveBudget:
    """Monotonic total budget shared by a sequence of Z3 checks.

    :param timeout_ms: Positive total budget in milliseconds, or ``None`` to
        leave Z3's timeout unset and allow unbounded execution.
    :type timeout_ms: Optional[int]
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``timeout_ms`` is not ``None``
        or a positive integer.

    Examples::

        >>> _SolveBudget(None).remaining_ms()
        None
    """

    def __init__(self, timeout_ms: Optional[int]) -> None:
        if timeout_ms is not None and (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or timeout_ms <= 0
        ):
            raise BmcBuildError("timeout_ms must be a positive integer or None.")
        self.timeout_ms = timeout_ms
        self.deadline = (
            None if timeout_ms is None else time.monotonic() + timeout_ms / 1000.0
        )

    def remaining_ms(self) -> Optional[int]:
        """Return remaining whole milliseconds, or ``None`` when unbounded.

        :return: Remaining budget, or ``None`` for an unbounded budget.
        :rtype: Optional[int]

        Examples::

            >>> _SolveBudget(None).remaining_ms()
            None
        """
        if self.deadline is None:
            return None
        remaining_seconds = self.deadline - time.monotonic()
        if remaining_seconds <= 0:
            return None
        remaining_ms = max(1, int(math.ceil(remaining_seconds * 1000.0)))
        return min(self.timeout_ms, remaining_ms)


def _check_with_budget(
    solver: z3.Solver, budget: _SolveBudget
) -> Tuple[
    str,
    Optional[z3.ModelRef],
    Optional[str],
    float,
    bool,
]:
    """Check one solver while preserving the shared-budget contract.

    :param solver: Z3 solver to check.
    :type solver: z3.Solver
    :param budget: Shared monotonic solve budget.
    :type budget: _SolveBudget
    :return: ``(status, model, reason, elapsed_ms, check_started)``.  Status is
        ``sat``, ``unsat``, ``unknown``, or ``timeout``; a pre-check deadline
        exhaustion returns ``check_started=False``.
    :rtype: Tuple[str, Optional[z3.ModelRef], Optional[str], float, bool]
    :raises TypeError: If the solver or budget has the wrong type.

    Examples::

        >>> import z3
        >>> _check_with_budget(z3.Solver(), _SolveBudget(None))[0]
        'sat'
    """
    if not all(
        callable(getattr(solver, name, None))
        for name in ("check", "set", "model", "reason_unknown")
    ):
        raise TypeError("solver must provide the Z3 solver check interface.")
    if not callable(getattr(budget, "remaining_ms", None)) or not hasattr(
        budget, "deadline"
    ):
        raise TypeError("budget must provide the shared budget interface.")

    remaining = budget.remaining_ms()
    # ``timeout_ms=None`` leaves ``deadline`` and ``remaining`` unset, so this
    # path intentionally calls Z3 without setting a solver timeout.
    if budget.deadline is not None and remaining is None:
        return "timeout", None, "deadline_exhausted_before_check", 0.0, False
    if remaining is not None:
        solver.set(timeout=remaining)
    start = time.monotonic()
    status = solver.check()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    if status == z3.sat:
        return "sat", solver.model(), None, elapsed_ms, True
    if status == z3.unsat:
        return "unsat", None, None, elapsed_ms, True
    reason = solver.reason_unknown() or "unknown"
    if reason == "timeout":
        return "timeout", None, reason, elapsed_ms, True
    return "unknown", None, reason, elapsed_ms, True


__all__ = []
