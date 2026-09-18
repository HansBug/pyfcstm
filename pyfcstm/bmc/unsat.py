"""Compatibility imports for the shared property-neutral UNSAT core API.

New integrations should import :mod:`pyfcstm.solver.unsat`. This adapter keeps
existing BMC names and timeout error behavior; it does not duplicate the kernel.
"""

from ..solver.unsat import (
    UnsatConstraint as BmcUnsatConstraint,
    UnsatQuery as BmcUnsatQuery,
    UnsatExplanation as BmcUnsatExplanation,
    CoreExtraction as CoreExtraction,
    MinimizedCore as MinimizedCore,
    ProbeRecord as ProbeRecord,
    _extract_constraint_core as _extract_constraint_core,
    _minimize_core as _minimize_core,
    _run_probe as _run_probe,
    _probe_outcome_reason as _probe_outcome_reason,
    explain_unsat_core as _explain_unsat_core,
)
from .solver import _SolveBudget

__all__ = ["BmcUnsatConstraint", "BmcUnsatQuery", "BmcUnsatExplanation", "explain_unsat_core"]


def explain_unsat_core(query, *, selected_ids=None, minimize=True, timeout_ms=None):
    """Delegate to the shared engine with the historical BMC timeout error.

    :param query: Exact formula groups and fixed background.
    :type query: BmcUnsatQuery
    :param selected_ids: Optional removable identifiers to recheck.
    :type selected_ids: Optional[Sequence[str]]
    :param minimize: Whether to shrink the verified core, defaults to True.
    :type minimize: bool
    :param timeout_ms: Positive milliseconds or None.
    :type timeout_ms: Optional[int]
    :return: Property-neutral core evidence.
    :rtype: BmcUnsatExplanation
    :raises pyfcstm.bmc.errors.BmcBuildError: For an invalid timeout.
    """
    _SolveBudget(timeout_ms)
    return _explain_unsat_core(query, selected_ids=selected_ids,
                              minimize=minimize, timeout_ms=timeout_ms)
