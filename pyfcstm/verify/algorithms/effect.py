"""Effect-focused SMT-local verification algorithms.

This module contains local SMT checks for transition effect blocks.  Each
algorithm executes a transition effect symbolically under its guard context and
then asks a focused post-state question.  Public callers should normally import
these functions from :mod:`pyfcstm.verify`.

Algorithm map:

.. list-table::
   :header-rows: 1

   * - Function
     - Formula shape
     - Diagnostic
   * - :func:`effect_no_op_under_guard`
     - Existence of a guarded execution that changes any model variable.
     - ``W_EFFECT_SMT_NO_OP``
   * - :func:`effect_contradicts_guard`
     - Existence of a guarded execution whose post-state still satisfies the
       same guard.
     - ``I_EFFECT_GUARD_CONTRADICT``

Example::

    >>> from pyfcstm.verify import effect_no_op_under_guard
    >>> callable(effect_no_op_under_guard)
    True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

from pyfcstm.verify.result import AlgorithmResult

if TYPE_CHECKING:  # pragma: no cover - imported only for static checkers
    from pyfcstm.model.model import Transition, VarDefine


def effect_no_op_under_guard(
    transition: Transition,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect transition effects that never change model variables.

    Pure syntactic self-assignment blocks such as ``x = x`` are deliberately
    ignored as a presentation-level no-op rather than reported as SMT no-op
    diagnostics.

    The algorithm first builds the transition guard context, then executes the
    effect block over symbolic variables.  It asks whether any model variable
    can differ between the pre-state and the post-state.  Temporary block-local
    variables are ignored at the public model boundary.

    Let ``V`` be the model variables before the effect, ``V'`` the symbolic
    store after executing the effect, ``T(V)`` the type-domain constraints,
    ``G(V)`` the guard predicate, and ``D_e(V)`` the runtime-definedness
    constraints introduced by the effect.  The witness query is:

    .. math::

       \exists V.\ G(V) \land T(V) \land D_e(V)
       \land \bigvee_{v \in V} v' \ne v

    Result semantics:

    * ``kind == "unsat"`` means every guarded, defined execution leaves all
      model variables unchanged and the result carries ``W_EFFECT_SMT_NO_OP``.
    * ``kind == "sat"`` means at least one guarded execution changes a model
      variable, the transition has no effect block, or the block is only a
      syntactic self-assignment.
    * ``kind == "unknown"`` or ``"timeout"`` means Z3 could not finish the
      query.
    * ``kind == "undecidable_skip"`` means guard or effect translation did not
      produce enough definedness evidence for a sound no-op diagnostic.

    :param transition: Transition to check.
    :type transition: Transition
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
        >>> from pyfcstm.verify import effect_no_op_under_guard
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> def effect_transition(machine):
        ...     return next(
        ...         transition
        ...         for state in machine.walk_states()
        ...         for transition in state.transitions
        ...         if transition.effects
        ...     )
        >>> # Adding zero is semantically a no-op for every guarded execution.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x >= 0] effect { x = x + 0; };
        ... }
        ... ''')
        >>> result = effect_no_op_under_guard(
        ...     effect_transition(machine),
        ...     variables(machine),
        ... )
        >>> result.kind
        'unsat'
        >>> result.diagnostics[0]["code"]
        'W_EFFECT_SMT_NO_OP'
        >>> # Incrementing x gives the solver a concrete changing execution.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x >= 0] effect { x = x + 1; };
        ... }
        ... ''')
        >>> effect_no_op_under_guard(
        ...     effect_transition(machine),
        ...     variables(machine),
        ... ).kind
        'sat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _effect_guard_context_or_result,
        _execute_effects_under_guard_or_result,
        _is_syntactically_self_assign_only,
        _make_diag,
        _skip_result,
        _transition_payload,
        _z3_vars,
        is_sat,
        z3,
    )

    if not transition.effects:
        return AlgorithmResult(kind="sat")
    if _is_syntactically_self_assign_only(transition.effects):
        return AlgorithmResult(kind="sat")

    z3_vars = _z3_vars(variables)
    guard_z3, type_constraints, result = _effect_guard_context_or_result(
        transition,
        variables,
        z3_vars,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result
    after_vars, effect_domain_constraints, result = (
        _execute_effects_under_guard_or_result(
            transition,
            z3_vars,
            guard_z3,
            type_constraints or (),
            smt_timeout_ms=smt_timeout_ms,
        )
    )
    if result is not None:
        return result

    try:
        changed_disjuncts = [
            after_vars[variable.name] != z3_vars[variable.name]
            for variable in variables
        ]
    except KeyError as err:
        # KeyError: the symbolic executor should preserve all model variables;
        # a missing variable means the effect state cannot be compared.
        return _skip_result("undecidable_skip", str(err))
    if not changed_disjuncts:
        return AlgorithmResult(kind="sat")

    formula = z3.And(
        guard_z3,
        z3.Or(*changed_disjuncts),
        *(type_constraints or ()),
        *(effect_domain_constraints or ()),
    )
    sat_result = is_sat([formula], timeout_ms=smt_timeout_ms)
    if sat_result.kind == "unsat":
        return AlgorithmResult(
            kind="unsat",
            diagnostics=(
                _make_diag(
                    "W_EFFECT_SMT_NO_OP",
                    "effect_no_op_under_guard",
                    transition=_transition_payload(transition),
                    verification_scope="smt_local",
                ),
            ),
    )
    return AlgorithmResult(kind=sat_result.kind)


def effect_contradicts_guard(
    transition: Transition,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect effects after which the transition guard cannot still hold.

    The post-effect guard counts as still holding only when it is both
    runtime-defined and true.  If post-state guard definedness is not guaranteed
    under the pre-guard/effect context, the raw algorithm returns
    ``undecidable_skip`` instead of emitting a deterministic contradiction.

    The algorithm is useful for finding transition effects that immediately
    invalidate the same guard that enabled the transition.  It does not claim
    that such an effect is always wrong; the diagnostic is informational and
    points reviewers to a potentially intentional latch, reset, or one-shot
    transition pattern.

    Let ``V`` be the pre-state variables, ``V'`` the post-state variables after
    symbolic effect execution, ``G(V)`` the pre-state guard, ``G(V')`` the
    post-state guard translated against the post-state store, ``T(V)`` the
    type-domain constraints, and ``D(V, V')`` the effect and post-guard
    runtime-definedness constraints.  The witness query is:

    .. math::

       \exists V.\ G(V) \land G(V') \land T(V) \land D(V, V')

    Result semantics:

    * ``kind == "unsat"`` means no defined guarded execution can leave the
      guard true after the effect and the result carries
      ``I_EFFECT_GUARD_CONTRADICT``.
    * ``kind == "sat"`` means some guarded execution can still satisfy the
      post-state guard, or the transition has no guard/effects.
    * ``kind == "unknown"`` or ``"timeout"`` means the solver could not decide
      the formula.
    * ``kind == "undecidable_skip"`` means the post-state guard is not
      guaranteed to be runtime-defined or translation failed.

    :param transition: Transition to check.
    :type transition: Transition
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
        >>> from pyfcstm.verify import effect_contradicts_guard
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> def effect_transition(machine):
        ...     return next(
        ...         transition
        ...         for state in machine.walk_states()
        ...         for transition in state.transitions
        ...         if transition.effects
        ...     )
        >>> # Whenever x > 0 enables the transition, setting x to 0 falsifies it.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x > 0] effect { x = 0; };
        ... }
        ... ''')
        >>> result = effect_contradicts_guard(
        ...     effect_transition(machine),
        ...     variables(machine),
        ... )
        >>> result.kind
        'unsat'
        >>> result.diagnostics[0]["code"]
        'I_EFFECT_GUARD_CONTRADICT'
        >>> # Incrementing x preserves x > 0 for every positive pre-state.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x > 0] effect { x = x + 1; };
        ... }
        ... ''')
        >>> effect_contradicts_guard(
        ...     effect_transition(machine),
        ...     variables(machine),
        ... ).kind
        'sat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _definedness_feasibility_or_result,
        _effect_guard_context_or_result,
        _execute_effects_under_guard_or_result,
        _expr_z3_and_domains_or_result,
        _make_diag,
        _skip_result,
        _transition_payload,
        _z3_vars,
        is_sat,
        z3,
    )

    if transition.guard is None or not transition.effects:
        return AlgorithmResult(kind="sat")

    z3_vars = _z3_vars(variables)
    guard_before, type_constraints, result = _effect_guard_context_or_result(
        transition,
        variables,
        z3_vars,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result
    after_vars, effect_domain_constraints, result = (
        _execute_effects_under_guard_or_result(
            transition,
            z3_vars,
            guard_before,
            type_constraints or (),
            smt_timeout_ms=smt_timeout_ms,
        )
    )
    if result is not None:
        return result
    guard_after, guard_after_domains, result = _expr_z3_and_domains_or_result(
        transition.guard,
        after_vars,
        context_constraints=[
            guard_before,
            *(type_constraints or ()),
            *(effect_domain_constraints or ()),
        ],
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result
    if guard_after_domains:
        post_context = [
            guard_before,
            *(type_constraints or ()),
            *(effect_domain_constraints or ()),
        ]
        result = _definedness_feasibility_or_result(
            [*post_context, *guard_after_domains],
            reason=(
                "Post-effect transition guard runtime definedness "
                "constraints are unsatisfiable."
            ),
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return result

        undefined_post_guard = is_sat(
            [*post_context, z3.Not(z3.And(*guard_after_domains))],
            timeout_ms=smt_timeout_ms,
        )
        if undefined_post_guard.kind == "sat":
            return _skip_result(
                "undecidable_skip",
                (
                    "Post-effect transition guard runtime definedness "
                    "constraints are not guaranteed."
                ),
            )
        if undefined_post_guard.kind != "unsat":
            return _skip_result(
                undefined_post_guard.kind,
                getattr(undefined_post_guard, "reason", None),
            )

    sat_result = is_sat(
        [
            guard_before,
            guard_after,
            *(type_constraints or ()),
            *(effect_domain_constraints or ()),
            *(guard_after_domains or ()),
        ],
        timeout_ms=smt_timeout_ms,
    )
    if sat_result.kind == "unsat":
        return AlgorithmResult(
            kind="unsat",
            diagnostics=(
                _make_diag(
                    "I_EFFECT_GUARD_CONTRADICT",
                    "effect_contradicts_guard",
                    transition=_transition_payload(transition),
                    verification_scope="smt_local",
                ),
            ),
        )
    return AlgorithmResult(kind=sat_result.kind)

__all__ = [
    "effect_contradicts_guard",
    "effect_no_op_under_guard",
]
