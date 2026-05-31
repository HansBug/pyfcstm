"""Inspect gating helpers for verify algorithm metadata."""

from typing import Iterator

from .taxonomy import (
    CALL_COUNT_SCALING_ORDER,
    COMPLEXITY_TIER_ORDER,
    CallCountScaling,
    ComplexityTier,
    VerifyAlgorithmMeta,
)


class InspectAccessForbiddenError(ValueError):
    """Raised when a forbidden inspect complexity tier is requested."""


def _order_allows(order, value, maximum):
    if value not in order or maximum not in order:
        return False
    return order.index(value) <= order.index(maximum)


def _validate_max_complexity_tier(maximum: ComplexityTier) -> None:
    if maximum == "bmc_search":
        raise InspectAccessForbiddenError(
            "bmc_search algorithms are not allowed in automatic inspect runs"
        )
    if maximum not in COMPLEXITY_TIER_ORDER:
        raise InspectAccessForbiddenError(
            "unknown inspect complexity tier: {maximum!r}".format(maximum=maximum)
        )


def _validate_max_call_count_scaling(maximum: CallCountScaling) -> None:
    if maximum not in CALL_COUNT_SCALING_ORDER:
        raise InspectAccessForbiddenError(
            "call-count scaling {maximum!r} is not allowed in automatic inspect runs".format(
                maximum=maximum
            )
        )


def _call_count_allows(value: CallCountScaling, maximum: CallCountScaling) -> bool:
    if value == "linear_in_leaves" and maximum == "linear_in_transitions":
        # PR-A1's inspect matrix treats all smt_linear local checks as part of
        # the recommended default budget. Leaf-linear checks are still rejected
        # by stricter limits such as ``linear_in_states``.
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
    :yield: Eligible metadata entries in registry order.
    :rtype: Iterator[VerifyAlgorithmMeta]
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
