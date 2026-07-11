"""Inspect gating and execution helpers for verify algorithm metadata.

This module decides which raw verification algorithms are eligible for
automatic inspect runs under a bounded complexity and call-count policy.  It
also executes eligible algorithms and normalizes their raw results without
importing diagnostics presentation code.

Examples::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.verify.inspect_adapter import run_inspect_algorithms
    >>> source = '''
    ... state Root {
    ...     state A;
    ...     [*] -> A;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
    >>> machine = parse_dsl_node_to_state_machine(ast)
    >>> names = [result.algorithm_name for result in run_inspect_algorithms(machine)]
    >>> "topological_reachable_set" in names
    True
    >>> all(name in names for name in ("unreachable_states", "topological_finite"))
    True

Module map:

.. list-table::
   :header-rows: 1

   * - Entry
     - Purpose
   * - :class:`InspectRunResult`
     - Carries one normalized inspect-adapter result while preserving the raw
       verification payload.
   * - :func:`eligible_for_inspect`
     - Decides whether one metadata entry is allowed by inspect policy.
   * - :func:`iter_inspect_eligible`
     - Iterates eligible registry metadata entries in stable registry order.
   * - :func:`run_inspect_algorithms`
     - Executes eligible algorithms and returns normalized results for later
       diagnostics conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Optional, Sequence, Tuple

from .result import AlgorithmResult, ResultKind
from .taxonomy import (
    CALL_COUNT_SCALING_ORDER,
    COMPLEXITY_TIER_ORDER,
    CallCountScaling,
    ComplexityTier,
    SMTLogic,
    VerificationScope,
    VerifyAlgorithmMeta,
)


_RawResult = Any
_TRANSITION_ALGORITHMS = frozenset(
    (
        "dead_guard",
        "guard_tautology",
        "forced_guard_unsat_under_init",
        "effect_no_op_under_guard",
        "effect_contradicts_guard",
    )
)
_MACHINE_SMT_ALGORITHMS = frozenset(
    (
        "transition_shadowed_by_predecessor",
        "composite_init_guards_incomplete",
    )
)
_INDETERMINATE_KINDS = ("timeout", "unknown", "undecidable_skip")


@dataclass(frozen=True)
class InspectRunResult:
    """Normalized output for one inspect-adapter algorithm run.

    The adapter returns one instance per registry algorithm, not one instance
    per raw diagnostic. Structural algorithms keep their graph-oriented raw
    payload in :attr:`raw_result`; their :attr:`result_kind` records that the
    structural run completed rather than replacing the structural payload.
    SMT-local algorithms expose raw diagnostic dictionaries through
    :attr:`diagnostics` while preserving their original :class:`AlgorithmResult`
    or per-element result tuple.

    :param algorithm_name: Registry name of the executed algorithm.
    :type algorithm_name: str
    :param complexity_tier: Algorithm complexity tier from registry metadata.
    :type complexity_tier: ComplexityTier
    :param smt_logic: SMT logic from registry metadata, or ``None`` for
        structural algorithms.
    :type smt_logic: Optional[SMTLogic]
    :param verification_scope: Downstream boundary label from registry
        metadata.
    :type verification_scope: Optional[VerificationScope]
    :param diagnostic_codes: Diagnostic codes advertised by registry metadata.
    :type diagnostic_codes: Tuple[str, ...]
    :param result_kind: Normalized result kind for the whole algorithm run.
    :type result_kind: ResultKind
    :param diagnostics: Raw verify diagnostic dictionaries collected from
        :class:`AlgorithmResult` values.
    :type diagnostics: Tuple[dict, ...]
    :param reason: Optional reason from the raw result when the run is
        inconclusive or skipped.
    :type reason: Optional[str]
    :param raw_result: Original raw algorithm return value kept for later
        inspect or diagnostics conversion.
    :type raw_result: object

    Examples::

        >>> result = InspectRunResult(
        ...     algorithm_name="topological_reachable_set",
        ...     complexity_tier="structural",
        ...     smt_logic=None,
        ...     verification_scope="topological_only",
        ...     diagnostic_codes=(),
        ...     result_kind="sat",
        ...     diagnostics=(),
        ...     reason=None,
        ...     raw_result={"Root.A": ()},
        ... )
        >>> result.algorithm_name
        'topological_reachable_set'
    """

    algorithm_name: str
    complexity_tier: ComplexityTier
    smt_logic: Optional[SMTLogic]
    verification_scope: Optional[VerificationScope]
    diagnostic_codes: Tuple[str, ...]
    result_kind: ResultKind
    diagnostics: Tuple[dict, ...]
    reason: Optional[str]
    raw_result: _RawResult


class InspectAccessForbiddenError(ValueError):
    """Raised when a forbidden inspect complexity tier is requested.

    Examples::

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

    Examples::

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

    :param maximum: Maximum complexity tier requested by the caller.
    :type maximum: ComplexityTier
    :return: ``None``.
    :rtype: None
    :raises InspectAccessForbiddenError: If ``maximum`` is unknown.

    Examples::

        >>> _validate_max_complexity_tier("structural")
        >>> _validate_max_complexity_tier("unknown_tier")
        Traceback (most recent call last):
        ...
        pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: unknown inspect complexity tier: 'unknown_tier'
    """
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
    :raises InspectAccessForbiddenError: If ``maximum`` is unknown.

    Examples::

        >>> _validate_max_call_count_scaling("linear_in_transitions")
        >>> _validate_max_call_count_scaling("unknown_scaling")
        Traceback (most recent call last):
        ...
        pyfcstm.verify.inspect_adapter.InspectAccessForbiddenError: unknown inspect call-count scaling: 'unknown_scaling'
    """
    if maximum not in CALL_COUNT_SCALING_ORDER:
        raise InspectAccessForbiddenError(
            "unknown inspect call-count scaling: {maximum!r}".format(maximum=maximum)
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

    Examples::

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
    :param max_complexity_tier: Maximum allowed complexity tier.
    :type max_complexity_tier: ComplexityTier
    :param max_call_count_scaling: Maximum allowed inspect call-count scaling.
    :type max_call_count_scaling: CallCountScaling
    :return: ``True`` if the algorithm is eligible for inspect automation.
    :rtype: bool
    :raises InspectAccessForbiddenError: If either inspect limit is outside the
        automatic inspect ordering.

    Examples::

        >>> from dataclasses import replace
        >>> from pyfcstm.verify.registry import REGISTRY
        >>> eligible_for_inspect(REGISTRY["topological_reachable_set"])
        True
        >>> queried = replace(
        ...     REGISTRY["topological_reachable_set"], closedness="queried"
        ... )
        >>> eligible_for_inspect(queried)
        False
    """
    _validate_max_complexity_tier(max_complexity_tier)
    _validate_max_call_count_scaling(max_call_count_scaling)
    if meta.closedness != "closed":
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

    :param max_complexity_tier: Maximum complexity tier accepted by inspect.
    :type max_complexity_tier: ComplexityTier
    :param max_call_count_scaling: Maximum allowed inspect call-count scaling.
    :type max_call_count_scaling: CallCountScaling
    :return: Iterator over eligible metadata entries in registry order.
    :yield: Eligible metadata entries in registry order.
    :rtype: Iterator[VerifyAlgorithmMeta]

    Examples::

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


def _variables_for(machine) -> Tuple[object, ...]:
    """Return model variables in stable declaration order.

    :param machine: State machine whose variable definitions should be passed
        to SMT-local algorithms.
    :type machine: StateMachine
    :return: Variable definitions in source order.
    :rtype: Tuple[object, ...]

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> ast = parse_with_grammar_entry("def int x = 0; state Root;", "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> _variables_for(machine)[0].name
        'x'
    """
    return tuple(machine.defines.values())


def _iter_model_transitions(machine) -> Iterator[object]:
    """Iterate transitions from all states in model order.

    :param machine: State machine to scan.
    :type machine: StateMachine
    :return: Iterator over transitions owned by each walked state.
    :yield: Transition objects in model traversal order.
    :rtype: Iterator[object]

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     [*] -> A;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> len(tuple(_iter_model_transitions(machine)))
        1
    """
    for state in machine.walk_states():
        for transition in state.transitions:
            yield transition


def _iter_model_leaf_states(machine) -> Iterator[object]:
    """Iterate non-pseudo leaf states in model order.

    :param machine: State machine to scan.
    :type machine: StateMachine
    :return: Iterator over non-pseudo leaf states.
    :yield: Leaf state objects in model traversal order.
    :rtype: Iterator[object]

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     [*] -> A;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> [state.path[-1] for state in _iter_model_leaf_states(machine)]
        ['A']
    """
    for state in machine.walk_states():
        if state.is_leaf_state and not state.is_pseudo:
            yield state


def _missing_impl_result(meta: VerifyAlgorithmMeta) -> InspectRunResult:
    """Return a normalized skip result for an unimplemented registry entry.

    :param meta: Metadata whose implementation is absent.
    :type meta: VerifyAlgorithmMeta
    :return: Normalized skip result.
    :rtype: InspectRunResult

    Examples::

        >>> from dataclasses import replace
        >>> from pyfcstm.verify.registry import REGISTRY
        >>> meta = replace(
        ...     REGISTRY["topological_reachable_set"],
        ...     name="custom_missing",
        ...     impl=None,
        ... )
        >>> result = _missing_impl_result(meta)
        >>> result.algorithm_name
        'custom_missing'
        >>> result.result_kind
        'undecidable_skip'
    """
    reason = "algorithm implementation is not registered"
    raw_result = AlgorithmResult(kind="undecidable_skip", reason=reason)
    return InspectRunResult(
        algorithm_name=meta.name,
        complexity_tier=meta.complexity_tier,
        smt_logic=meta.smt_logic,
        verification_scope=meta.verification_scope,
        diagnostic_codes=meta.diagnostic_codes,
        result_kind=raw_result.kind,
        diagnostics=(),
        reason=raw_result.reason,
        raw_result=raw_result,
    )


def _first_indeterminate(results: Sequence[AlgorithmResult]) -> Optional[AlgorithmResult]:
    """Return the first inconclusive raw result, if any.

    :param results: Raw algorithm results to scan.
    :type results: Sequence[AlgorithmResult]
    :return: First ``timeout``, ``unknown``, or ``undecidable_skip`` result, or
        ``None`` when all results are definite.
    :rtype: Optional[AlgorithmResult]

    Examples::

        >>> _first_indeterminate((AlgorithmResult("sat"), AlgorithmResult("unknown", reason="u"))).reason
        'u'
    """
    for result in results:
        if result.kind in _INDETERMINATE_KINDS:
            return result
    return None


def _aggregate_algorithm_results(results: Sequence[AlgorithmResult]) -> AlgorithmResult:
    """Aggregate per-element raw results into one algorithm-level result.

    Inconclusive outcomes dominate deterministic outcomes because later
    diagnostics conversion must be able to disclose that at least one checked
    element could not be decided.
    When all checked elements are definite, diagnostics decide whether the
    aggregate is ``sat`` or ``unsat``: any ``unsat`` result with diagnostics
    dominates ``sat`` diagnostics, otherwise emitting algorithms use ``sat``
    according to their own raw contract.  An empty run is a successful ``sat``
    no-finding result.

    :param results: Per-element raw algorithm results.
    :type results: Sequence[AlgorithmResult]
    :return: Aggregated raw result.
    :rtype: AlgorithmResult

    Examples::

        >>> _aggregate_algorithm_results((AlgorithmResult("sat"),)).kind
        'sat'
        >>> _aggregate_algorithm_results((AlgorithmResult("timeout", reason="t"),)).reason
        't'
        >>> mixed = (
        ...     AlgorithmResult("sat", diagnostics=({"code": "I_FAKE"},)),
        ...     AlgorithmResult("unsat", diagnostics=({"code": "W_FAKE"},)),
        ... )
        >>> _aggregate_algorithm_results(mixed).kind
        'unsat'
    """
    if not results:
        return AlgorithmResult(kind="sat")

    diagnostics = tuple(
        diagnostic for result in results for diagnostic in result.diagnostics
    )
    indeterminate = _first_indeterminate(results)
    if indeterminate is not None:
        return AlgorithmResult(
            kind=indeterminate.kind,
            diagnostics=diagnostics,
            reason=indeterminate.reason,
        )

    if diagnostics:
        if any(result.kind == "unsat" and result.diagnostics for result in results):
            return AlgorithmResult(kind="unsat", diagnostics=diagnostics)
        for result in results:
            if result.diagnostics:
                return AlgorithmResult(kind=result.kind, diagnostics=diagnostics)

    if all(result.kind == "unsat" for result in results):
        return AlgorithmResult(kind="unsat")
    return AlgorithmResult(kind="sat")


def _normalize_algorithm_result(
    meta: VerifyAlgorithmMeta,
    raw_result: _RawResult,
) -> InspectRunResult:
    """Convert one raw return value into :class:`InspectRunResult`.

    :param meta: Metadata for the algorithm that produced ``raw_result``.
    :type meta: VerifyAlgorithmMeta
    :param raw_result: Raw algorithm return value.
    :type raw_result: object
    :return: Normalized inspect-adapter result.
    :rtype: InspectRunResult
    :raises TypeError: If an SMT-local algorithm returns a payload that is not
        an :class:`AlgorithmResult` or a tuple of :class:`AlgorithmResult`
        values. Structural algorithms may return plain topology payloads and
        keep them in ``raw_result``.

    Examples::

        >>> from pyfcstm.verify.registry import REGISTRY
        >>> result = _normalize_algorithm_result(
        ...     REGISTRY["dead_guard"],
        ...     AlgorithmResult("sat"),
        ... )
        >>> result.algorithm_name
        'dead_guard'
    """
    if isinstance(raw_result, AlgorithmResult):
        algorithm_result = raw_result
    elif meta.complexity_tier == "structural":
        algorithm_result = AlgorithmResult(kind="sat")
    elif isinstance(raw_result, tuple):
        for index, item in enumerate(raw_result):
            if not isinstance(item, AlgorithmResult):
                raise TypeError(
                    "algorithm {name!r} returned tuple item {index} with "
                    "unexpected type {actual!r}; expected AlgorithmResult".format(
                        name=meta.name,
                        index=index,
                        actual=type(item).__name__,
                    )
                )
        algorithm_result = _aggregate_algorithm_results(raw_result)
    else:
        raise TypeError(
            "algorithm {name!r} returned unexpected raw result type {actual!r}; "
            "expected AlgorithmResult or Tuple[AlgorithmResult, ...]".format(
                name=meta.name,
                actual=type(raw_result).__name__,
            )
        )

    return InspectRunResult(
        algorithm_name=meta.name,
        complexity_tier=meta.complexity_tier,
        smt_logic=meta.smt_logic,
        verification_scope=meta.verification_scope,
        diagnostic_codes=meta.diagnostic_codes,
        result_kind=algorithm_result.kind,
        diagnostics=algorithm_result.diagnostics,
        reason=algorithm_result.reason,
        raw_result=raw_result,
    )


def _run_smt_algorithm(meta: VerifyAlgorithmMeta, machine, smt_timeout_ms):
    """Execute one SMT-local algorithm according to its registry scope.

    :param meta: Metadata with an implementation callable.
    :type meta: VerifyAlgorithmMeta
    :param machine: State machine to verify.
    :type machine: StateMachine
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int]
    :return: Raw result value from the algorithm or per-element aggregate input.
    :rtype: object
    :raises ValueError: If an SMT-local algorithm has no inspect dispatch rule.

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.verify.registry import REGISTRY
        >>> ast = parse_with_grammar_entry("state Root;", "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> _run_smt_algorithm(REGISTRY["composite_init_guards_incomplete"], machine, None).kind
        'unsat'
    """
    variables = _variables_for(machine)
    if meta.name in _TRANSITION_ALGORITHMS:
        return tuple(
            meta.impl(
                transition,
                variables,
                smt_timeout_ms=smt_timeout_ms,
            )
            for transition in _iter_model_transitions(machine)
        )
    if meta.name == "enter_postcondition_implies_during_precondition":
        return tuple(
            meta.impl(
                state,
                variables,
                smt_timeout_ms=smt_timeout_ms,
            )
            for state in _iter_model_leaf_states(machine)
        )
    if meta.name in _MACHINE_SMT_ALGORITHMS:
        return meta.impl(
            machine,
            variables,
            smt_timeout_ms=smt_timeout_ms,
        )
    raise ValueError(
        "algorithm {name!r} has no inspect dispatch rule; register it as "
        "transition-level, lifecycle-leaf-level, or machine-level before "
        "enabling automatic inspect execution".format(name=meta.name)
    )


def _run_algorithm(meta: VerifyAlgorithmMeta, machine, smt_timeout_ms):
    """Execute one eligible algorithm and return its raw value.

    :param meta: Metadata with an implementation callable.
    :type meta: VerifyAlgorithmMeta
    :param machine: State machine to verify.
    :type machine: StateMachine
    :param smt_timeout_ms: Optional SMT timeout in milliseconds.
    :type smt_timeout_ms: Optional[int]
    :return: Raw algorithm return value.
    :rtype: object
    :raises ValueError: If an SMT-local algorithm has no inspect dispatch rule.

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.verify.registry import REGISTRY
        >>> ast = parse_with_grammar_entry("state Root;", "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> isinstance(_run_algorithm(REGISTRY["topological_reachable_set"], machine, None), dict)
        True
    """
    if meta.complexity_tier == "structural":
        return meta.impl(machine)
    return _run_smt_algorithm(meta, machine, smt_timeout_ms)


def run_inspect_algorithms(
    machine,
    *,
    max_complexity_tier: ComplexityTier = "structural",
    max_call_count_scaling: CallCountScaling = "linear_in_transitions",
    smt_timeout_ms: Optional[int] = None,
    registry: Optional[Mapping[str, VerifyAlgorithmMeta]] = None,
) -> Tuple[InspectRunResult, ...]:
    """Run inspect-eligible verify algorithms and normalize their outputs.

    The function is the execution half of the inspect adapter.  It reuses
    :func:`eligible_for_inspect` as the only admission policy, runs algorithms
    in registry order, keeps custom ``impl=None`` entries as controlled skip
    results when they are otherwise eligible, and never emits diagnostics-layer
    objects directly.

    :param machine: State machine to verify.
    :type machine: StateMachine
    :param max_complexity_tier: Maximum complexity tier allowed by the
        inspect policy, defaults to ``"structural"``.
    :type max_complexity_tier: ComplexityTier, optional
    :param max_call_count_scaling: Maximum call-count scaling allowed by the
        inspect policy, defaults to ``"linear_in_transitions"``.
    :type max_call_count_scaling: CallCountScaling, optional
    :param smt_timeout_ms: Optional solver timeout passed to SMT-local
        algorithms as ``smt_timeout_ms``.  ``None`` preserves the raw algorithm
        default of no configured solver timeout.
    :type smt_timeout_ms: Optional[int], optional
    :param registry: Optional metadata registry for tests or alternate
        consumers.  ``None`` uses :data:`pyfcstm.verify.registry.REGISTRY`.
    :type registry: Optional[Mapping[str, VerifyAlgorithmMeta]], optional
    :return: Normalized results in registry order.
    :rtype: Tuple[InspectRunResult, ...]
    :raises InspectAccessForbiddenError: If either inspect limit is outside the
        automatic inspect ordering.
    :raises TypeError: If an SMT-local algorithm returns an unexpected raw
        result payload.
    :raises ValueError: If an SMT-local algorithm has no inspect dispatch rule.

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> ast = parse_with_grammar_entry("state Root;", "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> [result.algorithm_name for result in run_inspect_algorithms(machine)][:2]
        ['topological_reachable_set', 'unreachable_states']
    """
    _validate_max_complexity_tier(max_complexity_tier)
    _validate_max_call_count_scaling(max_call_count_scaling)

    if registry is None:
        from .registry import REGISTRY

        registry = REGISTRY

    results = []
    for meta in registry.values():
        if not eligible_for_inspect(
            meta,
            max_complexity_tier=max_complexity_tier,
            max_call_count_scaling=max_call_count_scaling,
        ):
            continue
        if meta.impl is None:
            results.append(_missing_impl_result(meta))
            continue
        raw_result = _run_algorithm(meta, machine, smt_timeout_ms)
        results.append(_normalize_algorithm_result(meta, raw_result))
    return tuple(results)


__all__ = [
    "InspectRunResult",
    "InspectAccessForbiddenError",
    "eligible_for_inspect",
    "iter_inspect_eligible",
    "run_inspect_algorithms",
]
