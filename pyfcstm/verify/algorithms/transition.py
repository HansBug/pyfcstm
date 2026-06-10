"""Transition-focused SMT-local verification algorithms.

This module checks relationships between multiple transitions rather than a
single guard or effect.  The algorithms still use local, quantifier-free SMT
queries; they do not unroll runtime execution over multiple cycles.  Public
callers should normally import these functions from :mod:`pyfcstm.verify`.

Algorithm map:

.. list-table::
   :header-rows: 1

   * - Function
     - Formula shape
     - Diagnostic
   * - :func:`transition_shadowed_by_predecessor`
     - Feasibility of a later outgoing trigger while every earlier same-source
       trigger is disabled.
     - ``W_TRANSITION_SHADOWED``
   * - :func:`composite_init_guards_incomplete`
     - Existence of an input valuation not covered by any initial-transition
       trigger.
     - ``W_COMPOSITE_INIT_INCOMPLETE``

Example::

    >>> from pyfcstm.verify import transition_shadowed_by_predecessor
    >>> callable(transition_shadowed_by_predecessor)
    True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

from pyfcstm.verify.result import AlgorithmResult

if TYPE_CHECKING:  # pragma: no cover - imported only for static checkers
    from pyfcstm.model.model import StateMachine, Transition, VarDefine


def transition_shadowed_by_predecessor(
    machine: StateMachine,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect outgoing transitions shadowed by earlier transitions.

    FCSTM transition order matters for transitions with the same source state:
    an earlier enabled transition prevents later outgoing transitions from
    being selected.  This algorithm groups ordered outgoing transitions by
    source, translates each event/guard trigger into a predicate, and asks
    whether a later trigger can ever be enabled after all prior triggers are
    disabled.

    For a source state with ordered outgoing transitions
    ``t_1, ..., t_n``, let ``H_i(V, E)`` be the trigger predicate for
    transition ``t_i`` over model variables ``V`` and synthetic event booleans
    ``E``.  For candidate transition ``t_j``, the shadowing witness query is:

    .. math::

       \exists V,E.\ T(V) \land D(V,E)
       \land H_j(V,E) \land \bigwedge_{i<j} \lnot H_i(V,E)

    If the query is unsatisfiable and ``H_j`` itself is satisfiable, then every
    defined candidate valuation is covered by prior triggers and ``t_j`` is
    shadowed.  The implementation also avoids deterministic diagnostics when
    predecessor continuation through stoppable composite validation is not
    locally proven stable.

    Result semantics:

    * ``kind == "unsat"`` means one or more later transitions are shadowed and
      diagnostics carry ``W_TRANSITION_SHADOWED``.
    * ``kind == "sat"`` means every checked later transition has a remaining
      candidate valuation or there are no ordered outgoing competitors.
    * ``kind == "unknown"`` or ``"timeout"`` means at least one relevant SMT
      query was inconclusive and no deterministic diagnostic was emitted.
    * ``kind == "undecidable_skip"`` means translation, definedness, or stable
      continuation evidence was insufficient for a sound shadowing result.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult

    Example::

        >>> from textwrap import dedent
        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.verify import transition_shadowed_by_predecessor
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> # The second A-source transition is never considered after A -> B.
        >>> machine = parse_machine('''
        ... state System {
        ...     state A;
        ...     state B;
        ...     state C;
        ...     [*] -> A;
        ...     A -> B;
        ...     A -> C;
        ... }
        ... ''')
        >>> result = transition_shadowed_by_predecessor(machine, variables(machine))
        >>> result.kind
        'unsat'
        >>> result.diagnostics[0]["code"]
        'W_TRANSITION_SHADOWED'
        >>> result.diagnostics[0]["data"]["reason"]
        'unconditional_catchall'
        >>> # Disjoint guards leave a candidate valuation for each transition.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     state C;
        ...     [*] -> A;
        ...     A -> B : if [x < 0];
        ...     A -> C : if [x > 0];
        ... }
        ... ''')
        >>> transition_shadowed_by_predecessor(machine, variables(machine)).kind
        'sat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _build_type_constraints,
        _definedness_feasibility_or_result,
        _first_indeterminate,
        _iter_ordered_outgoing,
        _make_diag,
        _state_path,
        _transition_has_definite_stable_continuation,
        _transition_payload,
        _transition_trigger_or_result,
        _z3_vars,
        is_sat,
        z3,
    )

    diagnostics: List[dict] = []
    first_indeterminate_result: Optional[AlgorithmResult] = None

    for source, outgoing in _iter_ordered_outgoing(machine):
        z3_vars = _z3_vars(variables)
        event_vars: Dict[str, z3.BoolRef] = {}
        prior_triggers: List[z3.ExprRef] = []
        prior_domain_constraints: List[z3.ExprRef] = []
        prior_payloads: List[dict] = []
        prior_transitions: List[Transition] = []
        type_constraints = _build_type_constraints(variables, z3_vars)

        for transition in outgoing:
            trigger, trigger_domains, result = _transition_trigger_or_result(
                transition,
                z3_vars,
                event_vars,
                context_constraints=type_constraints,
                smt_timeout_ms=smt_timeout_ms,
            )
            if result is not None:
                first_indeterminate_result = _first_indeterminate(
                    first_indeterminate_result,
                    result.kind,
                    result.reason,
                )
                continue
            if trigger_domains:
                result = _definedness_feasibility_or_result(
                    [*type_constraints, *prior_domain_constraints, *trigger_domains],
                    reason=(
                        "Transition trigger runtime definedness constraints "
                        "are unsatisfiable in context."
                    ),
                    smt_timeout_ms=smt_timeout_ms,
                )
                if result is not None:
                    first_indeterminate_result = _first_indeterminate(
                        first_indeterminate_result,
                        result.kind,
                        result.reason,
                    )
                    break

            current_payload = _transition_payload(transition)
            if prior_triggers:
                prior_disabled = tuple(
                    z3.Not(prior_trigger) for prior_trigger in prior_triggers
                )
                formula = z3.And(
                    trigger,
                    *prior_disabled,
                    *prior_domain_constraints,
                    *type_constraints,
                )
                sat_result = is_sat([formula], timeout_ms=smt_timeout_ms)
                if sat_result.kind == "unsat":
                    loose_formula = z3.And(
                        trigger,
                        *prior_disabled,
                        *type_constraints,
                    )
                    loose_result = is_sat(
                        [loose_formula],
                        timeout_ms=smt_timeout_ms,
                    )
                    if loose_result.kind == "sat":
                        first_indeterminate_result = _first_indeterminate(
                            first_indeterminate_result,
                            "undecidable_skip",
                            (
                                "Prior transition trigger runtime definedness "
                                "constraints exclude the remaining candidate "
                                "space."
                            ),
                        )
                        prior_triggers.append(trigger)
                        prior_domain_constraints.extend(trigger_domains or ())
                        prior_payloads.append(current_payload)
                        prior_transitions.append(transition)
                        continue
                    if loose_result.kind != "unsat":
                        first_indeterminate_result = _first_indeterminate(
                            first_indeterminate_result,
                            loose_result.kind,
                            getattr(loose_result, "reason", None),
                        )
                        continue

                    trigger_sat = is_sat(
                        [trigger, *type_constraints, *(trigger_domains or ())],
                        timeout_ms=smt_timeout_ms,
                    )
                    if trigger_sat.kind == "unsat":
                        # A transition whose own trigger is unsatisfiable
                        # belongs to dead_guard, not predecessor shadowing.
                        continue
                    if trigger_sat.kind != "sat":
                        first_indeterminate_result = _first_indeterminate(
                            first_indeterminate_result,
                            trigger_sat.kind,
                        )
                        continue

                    unstable_predecessor = (
                        source.is_stoppable
                        and not all(
                            _transition_has_definite_stable_continuation(
                                source, item
                            )
                            for item in prior_transitions
                        )
                    )
                    if unstable_predecessor:
                        first_indeterminate_result = _first_indeterminate(
                            first_indeterminate_result,
                            "undecidable_skip",
                            (
                                "Prior transition trigger coverage does not "
                                "prove runtime shadowing because a predecessor "
                                "transition lacks a locally proven stable "
                                "continuation."
                            ),
                        )
                    else:
                        has_unconditional_catchall = any(
                            item["event"] is None and item["guard"] is None
                            for item in prior_payloads
                        )
                        if has_unconditional_catchall:
                            reason = "unconditional_catchall"
                        elif (
                            current_payload["event"] is not None
                            and current_payload["guard"] is None
                            and any(
                                item["event"] == current_payload["event"]
                                and item["guard"] is None
                                for item in prior_payloads
                            )
                        ):
                            reason = "duplicate_event"
                        elif current_payload["guard"] is not None and all(
                            item["event"] is None and item["guard"] is not None
                            for item in prior_payloads
                        ):
                            reason = "guard_shadow"
                        else:
                            reason = "prior_trigger_cover"
                        diagnostics.append(
                            _make_diag(
                                "W_TRANSITION_SHADOWED",
                                "transition_shadowed_by_predecessor",
                                transition=current_payload,
                                shadowed_by=tuple(prior_payloads),
                                reason=reason,
                                source=_state_path(source),
                                verification_scope="smt_local",
                            )
                        )
                else:
                    first_indeterminate_result = _first_indeterminate(
                        first_indeterminate_result,
                        sat_result.kind,
                    )

            prior_triggers.append(trigger)
            prior_domain_constraints.extend(trigger_domains or ())
            prior_payloads.append(current_payload)
            prior_transitions.append(transition)

    if diagnostics:
        return AlgorithmResult(kind="unsat", diagnostics=tuple(diagnostics))
    if first_indeterminate_result is not None:
        return first_indeterminate_result
    return AlgorithmResult(kind="sat")


def composite_init_guards_incomplete(
    machine: StateMachine,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect composite states whose initial transitions do not cover inputs.

    The result ``kind`` follows the witness query: ``'sat'`` means a coverage
    gap was found and diagnostics were emitted, while ``'unsat'`` means the
    initial-transition triggers cover all modeled inputs.

    A composite state with only guarded or event-triggered initial transitions
    may fail to choose an initial child for some valuation.  This algorithm
    checks each composite state's initial transitions and searches for a model
    variable and event input assignment that disables all initial-transition
    triggers.

    For a composite state with initial transitions ``i_1, ..., i_n``, let
    ``H_k(V, E)`` be the trigger predicate for initial transition ``i_k``.
    The gap query is:

    .. math::

       \exists V,E.\ T(V) \land \lnot \bigvee_{k=1}^{n} H_k(V,E)

    Result semantics:

    * ``kind == "sat"`` means the query found an uncovered valuation and the
      diagnostics carry ``W_COMPOSITE_INIT_INCOMPLETE`` with a witness model
      when Z3 provided one.
    * ``kind == "unsat"`` means every checked composite initial-transition set
      covers all modeled variable and event inputs.
    * ``kind == "unknown"`` or ``"timeout"`` means a query was inconclusive
      and no coverage diagnostic was emitted for that composite.
    * ``kind == "undecidable_skip"`` means trigger translation or definedness
      evidence was insufficient for a sound coverage decision.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult

    Example::

        >>> from textwrap import dedent
        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.verify import composite_init_guards_incomplete
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> # x = 0 disables both guarded initial transitions, so a gap exists.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A : if [x > 0];
        ...     [*] -> B : if [x < 0];
        ... }
        ... ''')
        >>> result = composite_init_guards_incomplete(machine, variables(machine))
        >>> result.kind
        'sat'
        >>> result.diagnostics[0]["code"]
        'W_COMPOSITE_INIT_INCOMPLETE'
        >>> # The pair x >= 0 and x < 0 covers every integer input.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A : if [x >= 0];
        ...     [*] -> B : if [x < 0];
        ... }
        ... ''')
        >>> composite_init_guards_incomplete(machine, variables(machine)).kind
        'unsat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _build_init_constraints_or_result,
        _build_type_constraints,
        _first_indeterminate,
        _make_diag,
        _state_path,
        _transition_payload,
        _transition_trigger_or_result,
        _z3_vars,
        is_sat,
        z3,
    )

    diagnostics: List[dict] = []
    first_indeterminate_result: Optional[AlgorithmResult] = None

    for state in machine.walk_states():
        if state.is_leaf_state:
            continue

        init_transitions = state.init_transitions
        if not init_transitions:
            continue
        if any(
            transition.guard is None and transition.event is None
            for transition in init_transitions
        ):
            continue

        z3_vars = _z3_vars(variables)
        event_vars: Dict[str, z3.BoolRef] = {}
        triggers: List[z3.ExprRef] = []
        per_composite_failed = False
        _, result = _build_init_constraints_or_result(
            variables,
            z3_vars,
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                result.kind,
                result.reason,
            )
            continue
        type_constraints = _build_type_constraints(variables, z3_vars)
        for transition in init_transitions:
            trigger, trigger_domains, result = _transition_trigger_or_result(
                transition,
                z3_vars,
                event_vars,
                context_constraints=type_constraints,
                smt_timeout_ms=smt_timeout_ms,
            )
            if result is not None:
                first_indeterminate_result = _first_indeterminate(
                    first_indeterminate_result,
                    result.kind,
                    result.reason,
                )
                per_composite_failed = True
                break
            if trigger_domains:
                trigger = z3.And(trigger, *trigger_domains)
            triggers.append(trigger)

        if per_composite_failed or not triggers:
            continue

        no_coverage = z3.Not(z3.Or(*triggers))
        sat_result = is_sat(
            [
                no_coverage,
                *type_constraints,
            ],
            timeout_ms=smt_timeout_ms,
            get_model=True,
        )
        if sat_result.kind == "sat":
            diagnostics.append(
                _make_diag(
                    "W_COMPOSITE_INIT_INCOMPLETE",
                    "composite_init_guards_incomplete",
                    state=_state_path(state),
                    init_transitions=tuple(
                        _transition_payload(transition)
                        for transition in init_transitions
                    ),
                    witness=str(sat_result.model)
                    if sat_result.model is not None
                    else None,
                    verification_scope="smt_local",
                )
            )
        else:
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                sat_result.kind,
            )

    if diagnostics:
        return AlgorithmResult(kind="sat", diagnostics=tuple(diagnostics))
    if first_indeterminate_result is not None:
        return first_indeterminate_result
    return AlgorithmResult(kind="unsat")

__all__ = [
    "composite_init_guards_incomplete",
    "transition_shadowed_by_predecessor",
]
