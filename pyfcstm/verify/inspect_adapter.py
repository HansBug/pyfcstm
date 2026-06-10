"""Inspect gating helpers for verify algorithm metadata.

This module decides which raw verification algorithms are eligible for
automatic inspect runs under a bounded complexity and call-count policy.  It
does not execute algorithms and does not import diagnostics presentation code.

Example::

    >>> from pyfcstm.verify.inspect_adapter import iter_inspect_eligible
    >>> names = [meta.name for meta in iter_inspect_eligible()]
    >>> "topological_reachable_set" in names
    True
    >>> "bounded_reachability" in names
    False
"""

from typing import Iterator

from .taxonomy import (
    CALL_COUNT_SCALING_ORDER,
    COMPLEXITY_TIER_ORDER,
    CallCountScaling,
    ComplexityTier,
    VerifyAlgorithmMeta,
)


class InspectAccessForbiddenError(ValueError):
    """Raised when a forbidden inspect complexity tier is requested.

    Example::

        >>> raise InspectAccessForbiddenError("blocked")
        Traceback (most recent call last):
        ...
        pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: blocked
    """


def _order_allows(order, value, maximum):
    """Return whether ``value`` is at most ``maximum`` in a declared order.

    Unknown values are rejected instead of being treated as permissive.  The
    helper is shared by complexity and call-count gates so both policies keep
    the same monotone ordering behavior.

    :param order: Ordered policy values from lowest to highest cost.
    :type order: Sequence[str]
    :param value: Candidate value from algorithm metadata.
    :type value: str
    :param maximum: Maximum policy value accepted by the caller.
    :type maximum: str
    :return: ``True`` if both values are known and ``value`` is not above
        ``maximum``.
    :rtype: bool

    Example::

        >>> _order_allows(("low", "high"), "low", "high")
        True
        >>> _order_allows(("low", "high"), "high", "low")
        False
    """
    if value not in order or maximum not in order:
        return False
    return order.index(value) <= order.index(maximum)


def _validate_max_complexity_tier(maximum: ComplexityTier) -> None:
    """Validate an inspect complexity-tier limit.

    Automatic inspect runs are intentionally forbidden from enabling
    ``"bmc_search"`` through the generic limit knob.  BMC-style algorithms
    require explicit user queries because their cost depends on search depth and
    branching rather than a bounded local model dimension.

    :param maximum: Maximum complexity tier requested by the caller.
    :type maximum: ComplexityTier
    :return: ``None``.
    :rtype: None
    :raises InspectAccessForbiddenError: If ``maximum`` is unknown or requests
        the forbidden ``"bmc_search"`` tier.

    Example::

        >>> _validate_max_complexity_tier("structural")
        >>> _validate_max_complexity_tier("bmc_search")
        Traceback (most recent call last):
        ...
        pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: bmc_search algorithms are not allowed in automatic inspect runs
    """
    if maximum == "bmc_search":
        raise InspectAccessForbiddenError(
            "bmc_search algorithms are not allowed in automatic inspect runs"
        )
    if maximum not in COMPLEXITY_TIER_ORDER:
        raise InspectAccessForbiddenError(
            "unknown inspect complexity tier: {maximum!r}".format(maximum=maximum)
        )


def _validate_max_call_count_scaling(maximum: CallCountScaling) -> None:
    """Validate an inspect call-count scaling limit.

    :param maximum: Maximum call-count scaling requested by the caller.
    :type maximum: CallCountScaling
    :return: ``None``.
    :rtype: None
    :raises InspectAccessForbiddenError: If ``maximum`` is outside the automatic
        inspect ordering.

    Example::

        >>> _validate_max_call_count_scaling("linear_in_transitions")
        >>> _validate_max_call_count_scaling("k_unrollings")
        Traceback (most recent call last):
        ...
        pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: call-count scaling 'k_unrollings' is not allowed in automatic inspect runs
    """
    if maximum not in CALL_COUNT_SCALING_ORDER:
        raise InspectAccessForbiddenError(
            "call-count scaling {maximum!r} is not allowed in automatic inspect runs".format(
                maximum=maximum
            )
        )


def _call_count_allows(value: CallCountScaling, maximum: CallCountScaling) -> bool:
    """Return whether an algorithm call-count class fits an inspect limit.

    The default inspect budget treats leaf-linear SMT-local checks as part of
    the same practical budget as transition-linear checks, because both are
    expected to run once per local model element.  Stricter limits still reject
    leaf-linear algorithms.

    :param value: Algorithm call-count scaling class.
    :type value: CallCountScaling
    :param maximum: Maximum call-count scaling accepted by the caller.
    :type maximum: CallCountScaling
    :return: ``True`` if the scaling class is allowed by the inspect budget.
    :rtype: bool

    Example::

        >>> _call_count_allows("linear_in_leaves", "linear_in_transitions")
        True
        >>> _call_count_allows("linear_in_leaves", "linear_in_states")
        False
    """
    if value == "linear_in_leaves" and maximum == "linear_in_transitions":
        # The inspect matrix treats all smt_linear local checks as part of the
        # recommended default budget. Leaf-linear checks are still rejected by
        # stricter limits such as ``linear_in_states``.
        return True
    return _order_allows(CALL_COUNT_SCALING_ORDER, value, maximum)


def eligible_for_inspect(
    meta: VerifyAlgorithmMeta,
    *,
    max_complexity_tier: ComplexityTier = "structural",
    max_call_count_scaling: CallCountScaling = "linear_in_transitions",
) -> bool:
    """
    Return whether ``meta`` may run automatically from inspect.

    :param meta: Algorithm metadata to evaluate.
    :type meta: VerifyAlgorithmMeta
    :param max_complexity_tier: Maximum allowed non-BMC complexity tier.
    :type max_complexity_tier: ComplexityTier
    :param max_call_count_scaling: Maximum allowed inspect call-count scaling.
    :type max_call_count_scaling: CallCountScaling
    :return: ``True`` if the algorithm is eligible for inspect automation.
    :rtype: bool
    :raises InspectAccessForbiddenError: If ``max_complexity_tier`` is
        ``'bmc_search'`` or if either inspect limit is outside the automatic
        inspect ordering.

    Example::

        >>> from pyfcstm.verify.registry import REGISTRY
        >>> eligible_for_inspect(REGISTRY["topological_reachable_set"])
        True
        >>> eligible_for_inspect(REGISTRY["bounded_reachability"])
        False
    """
    _validate_max_complexity_tier(max_complexity_tier)
    _validate_max_call_count_scaling(max_call_count_scaling)
    if meta.closedness != "closed":
        return False
    if meta.complexity_tier == "bmc_search":
        return False
    if not _order_allows(
        COMPLEXITY_TIER_ORDER,
        meta.complexity_tier,
        max_complexity_tier,
    ):
        return False
    if not _call_count_allows(meta.call_count_scaling, max_call_count_scaling):
        return False
    return True


def iter_inspect_eligible(
    *,
    max_complexity_tier: ComplexityTier = "structural",
    max_call_count_scaling: CallCountScaling = "linear_in_transitions",
) -> Iterator[VerifyAlgorithmMeta]:
    """
    Iterate over registry algorithms eligible for inspect automation.

    :param max_complexity_tier: Maximum allowed non-BMC complexity tier.
    :type max_complexity_tier: ComplexityTier
    :param max_call_count_scaling: Maximum allowed inspect call-count scaling.
    :type max_call_count_scaling: CallCountScaling
    :return: Iterator over eligible metadata entries in registry order.
    :yield: Eligible metadata entries in registry order.
    :rtype: Iterator[VerifyAlgorithmMeta]

    Example::

        >>> names = [meta.name for meta in iter_inspect_eligible()]
        >>> names[:2]
        ['topological_reachable_set', 'unreachable_states']
    """
    from .registry import REGISTRY

    for meta in REGISTRY.values():
        if eligible_for_inspect(
            meta,
            max_complexity_tier=max_complexity_tier,
            max_call_count_scaling=max_call_count_scaling,
        ):
            yield meta


__all__ = [
    "InspectAccessForbiddenError",
    "eligible_for_inspect",
    "iter_inspect_eligible",
]
