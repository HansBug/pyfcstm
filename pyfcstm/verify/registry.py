"""Algorithm registry for :mod:`pyfcstm.verify`."""

from types import MappingProxyType
from typing import Mapping, Tuple

from .taxonomy import CallCountScaling, FallbackUnknownRisk, VerifyAlgorithmMeta


def _structural(
    name: str,
    description: str,
    call_count_scaling: CallCountScaling,
    diagnostic_codes: Tuple[str, ...] = (),
    dominant_dim: Tuple[str, ...] = ("states", "transitions"),
) -> VerifyAlgorithmMeta:
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
        impl=None,
    )


def _smt_local(
    name: str,
    description: str,
    call_count_scaling: CallCountScaling,
    diagnostic_codes: Tuple[str, ...],
    fallback_unknown_risk: FallbackUnknownRisk = "medium",
    incremental: bool = False,
    dominant_dim: Tuple[str, ...] = ("transitions", "vars"),
) -> VerifyAlgorithmMeta:
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
        recommended_tactic="smt",
        quantifier_alternation_depth=0,
        max_bitwidth=None,
        theory_combination=("LIA", "LRA"),
        verification_scope="smt_local",
        dominant_dim=dominant_dim,
        diagnostic_codes=diagnostic_codes,
        impl=None,
    )


def _composite_init_guards_incomplete() -> VerifyAlgorithmMeta:
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
        impl=None,
    )


def _bmc_placeholder(
    name: str,
    description: str,
    call_count_scaling: CallCountScaling,
    fallback_unknown_risk: FallbackUnknownRisk = "medium",
    dominant_dim: Tuple[str, ...] = ("depth", "vars", "events", "branching"),
) -> VerifyAlgorithmMeta:
    return VerifyAlgorithmMeta(
        name=name,
        description=description,
        closedness="queried",
        complexity_tier="bmc_search",
        smt_logic="QF_LIRA",
        formula_size_scaling="linear",
        call_count_scaling=call_count_scaling,
        incremental=True,
        fallback_unknown_risk=fallback_unknown_risk,
        recommended_tactic="smt",
        quantifier_alternation_depth=0,
        max_bitwidth=None,
        theory_combination=("LIA", "LRA"),
        verification_scope="bmc_unrolled",
        dominant_dim=dominant_dim,
        diagnostic_codes=(),
        impl=None,
    )


def _build_registry() -> Mapping[str, VerifyAlgorithmMeta]:
    return {
        "topological_reachable_set": _structural(
            "topological_reachable_set",
            "Compute guard-agnostic reachable states over the transition topology.",
            "linear_in_states",
            diagnostic_codes=(),
        ),
        "unreachable_states": _structural(
            "unreachable_states",
            "Report states unreachable from the root entry topology.",
            "linear_in_states",
            diagnostic_codes=("W_UNREACHABLE_STATE",),
        ),
        "strongly_connected_components": _structural(
            "strongly_connected_components",
            "Find non-trivial strongly connected components in the topology graph.",
            "linear_in_states",
            diagnostic_codes=("I_NONTRIVIAL_SCC",),
        ),
        "topological_finite": _structural(
            "topological_finite",
            "Check whether topology has an exit path rather than a closed no-exit region.",
            "linear_in_states",
            diagnostic_codes=("W_TOPOLOGICAL_NOEXIT",),
        ),
        "topological_inevitable_terminator": _structural(
            "topological_inevitable_terminator",
            "Identify topology regions that are not forced to reach a terminator.",
            "linear_in_states",
            diagnostic_codes=("I_TOPOLOGICAL_NON_TERMINATING",),
        ),
        "event_emission_to_consumer_reachable": _structural(
            "event_emission_to_consumer_reachable",
            "Check whether each used event has a topologically reachable consumer source.",
            "linear_in_transitions",
            diagnostic_codes=("W_EVENT_UNREACHABLE_EMIT",),
            dominant_dim=("events", "transitions"),
        ),
        "dead_guard": _smt_local(
            "dead_guard",
            "Detect guards that are unsatisfiable under variable constraints.",
            "linear_in_transitions",
            ("W_DEAD_GUARD",),
        ),
        "guard_tautology": _smt_local(
            "guard_tautology",
            "Detect guards that are always true under variable constraints.",
            "linear_in_transitions",
            ("W_GUARD_TAUTOLOGY",),
        ),
        "forced_guard_unsat_under_init": _smt_local(
            "forced_guard_unsat_under_init",
            "Detect forced-transition guards unsatisfiable under initial variable values.",
            "linear_in_transitions",
            ("W_FORCED_GUARD_UNSAT",),
            fallback_unknown_risk="low",
        ),
        "effect_no_op_under_guard": _smt_local(
            "effect_no_op_under_guard",
            "Detect transition effects that are no-ops whenever the guard holds.",
            "linear_in_transitions",
            ("W_EFFECT_SMT_NO_OP",),
        ),
        "effect_contradicts_guard": _smt_local(
            "effect_contradicts_guard",
            "Detect effects whose post-state contradicts their transition guard.",
            "linear_in_transitions",
            ("I_EFFECT_GUARD_CONTRADICT",),
        ),
        "transition_shadowed_by_predecessor": _smt_local(
            "transition_shadowed_by_predecessor",
            "Detect outgoing transitions fully shadowed by earlier same-domain transitions.",
            "linear_in_transitions",
            ("W_TRANSITION_SHADOWED",),
            incremental=True,
            dominant_dim=("transitions", "vars"),
        ),
        "enter_postcondition_implies_during_precondition": _smt_local(
            "enter_postcondition_implies_during_precondition",
            "Compare entry postconditions with first-cycle during preconditions.",
            "linear_in_leaves",
            ("I_ENTER_DURING_CONTRADICT",),
            dominant_dim=("leaves", "vars"),
        ),
        "composite_init_guards_incomplete": _composite_init_guards_incomplete(),
        "bounded_reachability": _bmc_placeholder(
            "bounded_reachability",
            "Query whether a target state is reachable from a source within a bound.",
            "k_unrollings",
        ),
        "symbolic_bfs": _bmc_placeholder(
            "symbolic_bfs",
            "Build bounded symbolic BFS spaces for queried reachability algorithms.",
            "k_unrollings_times_branching",
        ),
        "bounded_safety": _bmc_placeholder(
            "bounded_safety",
            "Query whether bounded executions avoid bad states or bad conditions.",
            "k_unrollings",
        ),
        "bounded_invariant": _bmc_placeholder(
            "bounded_invariant",
            "Query whether an invariant holds over all bounded reachable frames.",
            "k_unrollings_times_branching",
            fallback_unknown_risk="high",
        ),
        "path_witness": _bmc_placeholder(
            "path_witness",
            "Decode a concrete path witness from a satisfiable symbolic frame.",
            "one",
            dominant_dim=("depth",),
        ),
    }


REGISTRY: Mapping[str, VerifyAlgorithmMeta] = MappingProxyType(dict(_build_registry()))

__all__ = ["REGISTRY"]
