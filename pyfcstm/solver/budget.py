"""Monotonic deadline shared by symbolic solving and optional explanations."""

import math
import time
from typing import Optional, cast

__all__ = ["SolveBudget"]


class SolveBudget:
    """Monotonic total budget shared by a sequence of Z3 checks.

    :param timeout_ms: Positive total budget in milliseconds, or ``None`` to
        leave Z3's timeout unset and allow unbounded execution.
    :type timeout_ms: Optional[int]
    :raises ValueError: If ``timeout_ms`` is neither
        ``None`` nor a positive integer.  ``bool`` is rejected even though it
        is an ``int`` subclass.

    Example::

        >>> print(SolveBudget(None).remaining_ms())
        None
    """

    def __init__(self, timeout_ms: Optional[int]) -> None:
        if timeout_ms is not None and (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or timeout_ms <= 0
        ):
            raise ValueError("timeout_ms must be a positive integer or None.")
        self.timeout_ms = timeout_ms
        self.deadline = (
            None if timeout_ms is None else time.monotonic() + timeout_ms / 1000.0
        )

    def remaining_ms(self) -> Optional[int]:
        """Return remaining whole milliseconds, or ``None`` when unavailable.

        ``None`` covers two different situations that callers must not merge:
        an unbounded budget, where ``deadline`` is ``None``, and an exhausted
        finite budget.  the caller separates them by also
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

            >>> print(SolveBudget(None).remaining_ms())
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
