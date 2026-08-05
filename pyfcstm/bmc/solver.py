"""Shared Z3 checking-budget primitives for the BMC pipeline.

The BMC solver uses one monotonic optional budget across primary solving,
feasibility localization, and later refinement checks.  ``None`` deliberately
means that no Z3 timeout is configured and no hidden deadline is introduced.
This module contains only the budget/check mechanics; verdict interpretation,
source provenance, and explanation policy belong to other BMC layers.

The leading underscore on the two implementation names is intentional.  They
are shared internal primitives, not part of the public BMC API.  Their exact
``check_started`` and reason semantics are documented here because later
internal modules depend on them.

This module is an extraction of primitives that previously lived inside the
witness layer, and the extraction is behavior-preserving except for one
documented point: :meth:`_SolveBudget.remaining_ms` now rounds a partial
millisecond up instead of truncating it.  A finite budget therefore performs
one more real check where the predecessor would have reported
``deadline_exhausted_before_check`` with up to a millisecond still left.

Example::

    >>> import z3
    >>> budget = _SolveBudget(None)
    >>> _check_with_budget(z3.Solver(), budget)[0]
    'sat'
"""

from __future__ import annotations

import math
import time
from typing import Optional, Tuple, cast

import z3

from .errors import BmcBuildError

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

BmcSolveStatus = Literal["sat", "unsat", "unknown", "timeout"]


class _SolveBudget:
    """Monotonic total budget shared by a sequence of Z3 checks.

    :param timeout_ms: Positive total budget in milliseconds, or ``None`` to
        leave Z3's timeout unset and allow unbounded execution.
    :type timeout_ms: Optional[int]
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``timeout_ms`` is neither
        ``None`` nor a positive integer.  ``bool`` is rejected even though it
        is an ``int`` subclass.

    Example::

        >>> print(_SolveBudget(None).remaining_ms())
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
        """Return remaining whole milliseconds, or ``None`` when unavailable.

        ``None`` covers two different situations that callers must not merge:
        an unbounded budget, where ``deadline`` is ``None``, and an exhausted
        finite budget.  :func:`_check_with_budget` separates them by also
        testing ``deadline``; a caller that only inspects this return value
        cannot tell "no limit" from "no time left".

        A partial millisecond is rounded up rather than truncated, so a finite
        budget spends its last fraction of a millisecond on a real check
        instead of reporting exhaustion.  This differs from the truncating
        predecessor this budget was extracted from, and is the one intentional
        behavior change in that extraction.

        :return: Remaining whole milliseconds, never above the configured total
            budget; ``None`` for an unbounded or already exhausted budget.
        :rtype: Optional[int]

        Example::

            >>> print(_SolveBudget(None).remaining_ms())
            None
        """
        if self.deadline is None:
            return None
        remaining_seconds = self.deadline - time.monotonic()
        if remaining_seconds <= 0:
            return None
        remaining_ms = max(1, int(math.ceil(remaining_seconds * 1000.0)))
        # Rounding up can land one millisecond above the requested total budget:
        # ``deadline`` is ``t0 + timeout_ms / 1000.0``, and that float addition
        # can round upward, so ``deadline - t0`` may exceed ``timeout_ms / 1000``
        # (with ``t0 = 1e7`` and ``timeout_ms = 1`` the ceiling above yields 2).
        # Clamping keeps a finite budget an honest upper bound for Z3.
        return min(cast(int, self.timeout_ms), remaining_ms)


def _check_with_budget(
    solver: z3.Solver, budget: _SolveBudget
) -> Tuple[
    BmcSolveStatus,
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
    :rtype: Tuple[BmcSolveStatus, Optional[z3.ModelRef], Optional[str], float, bool]

    Example::

        >>> import z3
        >>> _check_with_budget(z3.Solver(), _SolveBudget(None))[0]
        'sat'
    """
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
