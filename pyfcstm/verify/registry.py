"""Algorithm registry for :mod:`pyfcstm.verify`.

The registry maps stable algorithm names to
:class:`pyfcstm.verify.taxonomy.VerifyAlgorithmMeta` entries. Every registered
structural or SMT-local algorithm carries an executable callable.

Example::

    >>> from pyfcstm.verify.registry import REGISTRY
    >>> REGISTRY["dead_guard"].impl.__name__
    'dead_guard'
    >>> all(callable(meta.impl) for meta in REGISTRY.values())
    True
"""

from types import MappingProxyType
from typing import Callable, Mapping, Optional, Tuple

from . import topology
from .algorithms.effect import effect_contradicts_guard, effect_no_op_under_guard
from .algorithms.guard import (
    dead_guard,
    forced_guard_unsat_under_init,
    guard_tautology,
)
from .algorithms.lifecycle import enter_postcondition_implies_during_precondition
from .algorithms.transition import (
    composite_init_guards_incomplete,
    transition_shadowed_by_predecessor,
)
from .taxonomy import CallCountScaling, FallbackUnknownRisk, VerifyAlgorithmMeta


def _structural(
    name: str,
    description: str,
    call_count_scaling: CallCountScaling,
    diagnostic_codes: Tuple[str, ...] = (),
    dominant_dim: Tuple[str, ...] = ("states", "transitions"),
) -> VerifyAlgorithmMeta:
    """Build metadata for a closed structural topology algorithm.

    Structural algorithms do not use SMT and are safe for automatic inspect
    gating when their call-count scaling fits the selected budget.  The
    implementation callable is resolved from :mod:`pyfcstm.verify.topology`
    using ``name``.

    :param name: Registry key and topology function name.
    :type name: str
    :param description: Human-readable algorithm summary.
    :type description: str
    :param call_count_scaling: Inspect call-count scaling class.
    :type call_count_scaling: CallCountScaling
    :param diagnostic_codes: Diagnostic codes emitted by integration layers,
        defaults to ``()``.
    :type diagnostic_codes: Tuple[str, ...], optional
    :param dominant_dim: Dominant model dimensions for cost explanations,
        defaults to ``("states", "transitions")``.
    :type dominant_dim: Tuple[str, ...], optional
    :return: Fully populated metadata entry.
    :rtype: VerifyAlgorithmMeta

    Example::

        >>> meta = _structural(
        ...     "topological_reachable_set",
        ...     "Compute reachable leaves.",
        ...     "linear_in_states",
        ... )
        >>> meta.complexity_tier
        'structural'
        >>> meta.smt_logic is None
        True
    """
    return VerifyAlgorithmMeta(
        name=name,
        description=description,
        closedness="closed",
        complexity_tier="structural",
        smt_logic=None,
        formula_size_scaling="none",
        call_count_scaling=call_count_scaling,
        incremental=False,
        fallback_unknown_risk="none",
        recommended_tactic=None,
        quantifier_alternation_depth=0,
        max_bitwidth=None,
        theory_combination=(),
        verification_scope="topological_only",
        dominant_dim=dominant_dim,
        diagnostic_codes=diagnostic_codes,
        impl=getattr(topology, name),
    )


def _smt_local(
    name: str,
    description: str,
    call_count_scaling: CallCountScaling,
    diagnostic_codes: Tuple[str, ...],
    fallback_unknown_risk: FallbackUnknownRisk = "medium",
    incremental: bool = False,
    dominant_dim: Tuple[str, ...] = ("E", "vars"),
    impl: Optional[Callable] = None,
) -> VerifyAlgorithmMeta:
    """Build metadata for a closed local-SMT verification algorithm.

    Local-SMT algorithms translate bounded per-element FCSTM facts into
    quantifier-free linear integer/real arithmetic.  They are closed algorithms:
    callers do not need to supply a target query, but the solver may still
    return ``unknown`` or ``timeout`` for individual formulas.

    :param name: Registry key and public algorithm name.
    :type name: str
    :param description: Human-readable algorithm summary.
    :type description: str
    :param call_count_scaling: Inspect call-count scaling class.
    :type call_count_scaling: CallCountScaling
    :param diagnostic_codes: Diagnostic codes emitted by the raw algorithm.
    :type diagnostic_codes: Tuple[str, ...]
    :param fallback_unknown_risk: Risk of an inconclusive fallback, defaults to
        ``"medium"``.
    :type fallback_unknown_risk: FallbackUnknownRisk, optional
    :param incremental: Whether the implementation can reuse solver context,
        defaults to ``False``.
    :type incremental: bool, optional
    :param dominant_dim: Dominant model dimensions for cost explanations,
        defaults to ``("E", "vars")``.
    :type dominant_dim: Tuple[str, ...], optional
    :param impl: Implementation callable, defaults to ``None``.
    :type impl: Optional[Callable], optional
    :return: Fully populated metadata entry.
    :rtype: VerifyAlgorithmMeta

    Example::

        >>> meta = _smt_local(
        ...     "dead_guard",
        ...     "Detect unreachable guards.",
        ...     "linear_in_transitions",
        ...     ("W_DEAD_GUARD",),
        ... )
        >>> meta.smt_logic
        'QF_LIRA'
        >>> meta.verification_scope
        'smt_local'
    """
    return VerifyAlgorithmMeta(
        name=name,
        description=description,
        closedness="closed",
        complexity_tier="smt_linear",
        smt_logic="QF_LIRA",
        formula_size_scaling="constant",
        call_count_scaling=call_count_scaling,
        incremental=incremental,
        fallback_unknown_risk=fallback_unknown_risk,
        recommended_tactic="qflia",
        quantifier_alternation_depth=0,
        max_bitwidth=None,
        theory_combination=("LIA", "LRA"),
        verification_scope="smt_local",
        dominant_dim=dominant_dim,
        diagnostic_codes=diagnostic_codes,
        impl=impl,
    )


def _composite_init_guards_incomplete(
    impl: Optional[Callable] = None,
) -> VerifyAlgorithmMeta:
    """Build metadata for composite initial-transition coverage.

    This factory is separate from :func:`_smt_local` because the composite
    coverage formula grows linearly with the number of initial transitions in a
    composite state, while most other local-SMT entries use constant-size
    formulas per checked transition.

    :param impl: Implementation callable, defaults to ``None``.
    :type impl: Optional[Callable], optional
    :return: Fully populated metadata entry for
        :func:`pyfcstm.verify.composite_init_guards_incomplete`.
    :rtype: VerifyAlgorithmMeta

    Example::

        >>> meta = _composite_init_guards_incomplete()
        >>> meta.formula_size_scaling
        'linear'
        >>> meta.diagnostic_codes
        ('W_COMPOSITE_INIT_INCOMPLETE',)
    """
    return VerifyAlgorithmMeta(
        name="composite_init_guards_incomplete",
        description=(
            "Detect composite states whose initial transitions do not jointly "
            "cover all variable and event inputs."
        ),
        closedness="closed",
        complexity_tier="smt_linear",
        smt_logic="QF_LIRA",
        formula_size_scaling="linear",
        call_count_scaling="linear_in_states",
        incremental=True,
        fallback_unknown_risk="medium",
        recommended_tactic="qflia",
        quantifier_alternation_depth=0,
        max_bitwidth=None,
        theory_combination=("LIA", "LRA"),
        verification_scope="smt_local",
        dominant_dim=("V", "vars", "events"),
        diagnostic_codes=("W_COMPOSITE_INIT_INCOMPLETE",),
        impl=impl,
    )


def _build_registry() -> Mapping[str, VerifyAlgorithmMeta]:
    """Build the immutable verify algorithm metadata mapping.

    The returned mapping keeps structural algorithms first, implemented
    local-SMT algorithms next. Registry order is intentionally stable because
    inspect adapters iterate over the mapping in declaration order.

    :return: Mapping from algorithm name to metadata.
    :rtype: Mapping[str, VerifyAlgorithmMeta]

    Example::

        >>> registry = _build_registry()
        >>> "dead_guard" in registry
        True
        >>> len(registry), all(callable(meta.impl) for meta in registry.values())
        (14, True)
    """
    return {
        "topological_reachable_set": _structural(
            "topological_reachable_set",
            "Compute guard-agnostic reachable states over the transition topology.",
            "linear_in_states",
            diagnostic_codes=(),
            dominant_dim=("V", "E", "depth"),
        ),
        "unreachable_states": _structural(
            "unreachable_states",
            "Report states unreachable from the root entry topology.",
            "linear_in_states",
            diagnostic_codes=("W_UNREACHABLE_STATE",),
            dominant_dim=("V_leaf", "depth"),
        ),
        "strongly_connected_components": _structural(
            "strongly_connected_components",
            "Find non-trivial strongly connected components in the topology graph.",
            "linear_in_states",
            diagnostic_codes=("I_NONTRIVIAL_SCC",),
            dominant_dim=("V", "E"),
        ),
        "topological_finite": _structural(
            "topological_finite",
            "Check whether topology has an exit path rather than a closed no-exit region.",
            "linear_in_states",
            diagnostic_codes=("W_TOPOLOGICAL_NOEXIT",),
            dominant_dim=("V", "E"),
        ),
        "topological_inevitable_terminator": _structural(
            "topological_inevitable_terminator",
            "Identify topology regions that are not forced to reach a terminator.",
            "linear_in_states",
            diagnostic_codes=("I_TOPOLOGICAL_NON_TERMINATING",),
            dominant_dim=("V", "E"),
        ),
        "event_emission_to_consumer_reachable": _structural(
            "event_emission_to_consumer_reachable",
            "Check whether each used event has a topologically reachable consumer source.",
            "linear_in_transitions",
            diagnostic_codes=("W_EVENT_UNREACHABLE_EMIT",),
            dominant_dim=("events", "E"),
        ),
        "dead_guard": _smt_local(
            "dead_guard",
            "Detect guards that are unsatisfiable under variable constraints.",
            "linear_in_transitions",
            ("W_DEAD_GUARD",),
            impl=dead_guard,
        ),
        "guard_tautology": _smt_local(
            "guard_tautology",
            "Detect guards that are always true under variable constraints.",
            "linear_in_transitions",
            ("W_GUARD_TAUTOLOGY",),
            impl=guard_tautology,
        ),
        "forced_guard_unsat_under_init": _smt_local(
            "forced_guard_unsat_under_init",
            "Detect forced-transition guards unsatisfiable under initial variable values.",
            "linear_in_transitions",
            ("W_FORCED_GUARD_UNSAT",),
            fallback_unknown_risk="low",
            dominant_dim=("forced_transitions", "vars"),
            impl=forced_guard_unsat_under_init,
        ),
        "effect_no_op_under_guard": _smt_local(
            "effect_no_op_under_guard",
            "Detect transition effects that are no-ops whenever the guard holds.",
            "linear_in_transitions",
            ("W_EFFECT_SMT_NO_OP",),
            impl=effect_no_op_under_guard,
        ),
        "effect_contradicts_guard": _smt_local(
            "effect_contradicts_guard",
            "Detect effects whose post-state contradicts their transition guard.",
            "linear_in_transitions",
            ("I_EFFECT_GUARD_CONTRADICT",),
            impl=effect_contradicts_guard,
        ),
        "transition_shadowed_by_predecessor": _smt_local(
            "transition_shadowed_by_predecessor",
            "Detect outgoing transitions fully shadowed by earlier same-domain transitions.",
            "linear_in_transitions",
            ("W_TRANSITION_SHADOWED",),
            incremental=True,
            impl=transition_shadowed_by_predecessor,
        ),
        "enter_postcondition_implies_during_precondition": _smt_local(
            "enter_postcondition_implies_during_precondition",
            "Compare entry postconditions with first-cycle during preconditions.",
            "linear_in_leaves",
            ("I_ENTER_DURING_CONTRADICT",),
            incremental=True,
            dominant_dim=("V_leaf", "vars"),
            impl=enter_postcondition_implies_during_precondition,
        ),
        "composite_init_guards_incomplete": _composite_init_guards_incomplete(
            impl=composite_init_guards_incomplete
        ),
    }


REGISTRY: Mapping[str, VerifyAlgorithmMeta] = MappingProxyType(dict(_build_registry()))

__all__ = ["REGISTRY"]
