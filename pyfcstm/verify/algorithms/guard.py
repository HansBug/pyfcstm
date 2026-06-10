"""Guard-focused SMT-local verification algorithms.

The functions in this module translate one transition guard at a time into a
quantifier-free Z3 formula and return a raw :class:`AlgorithmResult`.  They do
not mutate the model and do not depend on the diagnostics package.  Public
callers should normally import these functions from :mod:`pyfcstm.verify`.

Algorithm map:

.. list-table::
   :header-rows: 1

   * - Function
     - Formula shape
     - Diagnostic
   * - :func:`dead_guard`
     - Guard satisfiability under type and runtime-definedness constraints.
     - ``W_DEAD_GUARD``
   * - :func:`guard_tautology`
     - Unsatisfiability of the negated guard under the same constraints.
     - ``W_GUARD_TAUTOLOGY``
   * - :func:`forced_guard_unsat_under_init`
     - Forced-transition guard satisfiability after declaration initializers.
     - ``W_FORCED_GUARD_UNSAT``

Example::

    >>> from pyfcstm.verify import dead_guard
    >>> callable(dead_guard)
    True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

from pyfcstm.verify.result import AlgorithmResult

if TYPE_CHECKING:  # pragma: no cover - imported only for static checkers
    from pyfcstm.model.model import Transition, VarDefine


def dead_guard(
    transition: Transition,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect a transition guard that is unsatisfiable.

    This algorithm checks the existence of a runtime valuation that can make a
    transition guard true.  It is a local SMT query over the transition guard:
    it uses model variable type constraints and guard runtime-definedness
    constraints, but it deliberately does not pin variables to DSL declaration
    initializers.  Use :func:`forced_guard_unsat_under_init` for the separate
    forced-transition check that does evaluate the guard under initial values.

    Let ``V`` be the current model variables, ``T(V)`` the type-domain
    constraints, ``D_g(V)`` the runtime-definedness constraints collected while
    translating guard ``g``, and ``G(V)`` the translated guard predicate.  The
    check is:

    .. math::

       \exists V.\ T(V) \land D_g(V) \land G(V)

    Result semantics:

    * ``kind == "unsat"`` means no valuation can enable the guard and the
      result carries ``W_DEAD_GUARD``.
    * ``kind == "sat"`` means at least one valuation enables the guard, or the
      transition has no guard.
    * ``kind == "unknown"`` or ``"timeout"`` means Z3 could not finish the
      query.
    * ``kind == "undecidable_skip"`` means translation or runtime-definedness
      evidence was insufficient for a sound diagnostic.

    :param transition: Transition to check.
    :type transition: Transition
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
        ``None`` is forwarded to the solver helper as no timeout.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult

    Example::

        >>> from textwrap import dedent
        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.verify import dead_guard
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> def guarded_transition(machine):
        ...     return next(
        ...         transition
        ...         for state in machine.walk_states()
        ...         for transition in state.transitions
        ...         if transition.guard is not None
        ...     )
        >>> # Negative guard space: x cannot be both greater than 1 and below 0.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x > 1 && x < 0];
        ... }
        ... ''')
        >>> result = dead_guard(guarded_transition(machine), variables(machine))
        >>> result.kind
        'unsat'
        >>> result.diagnostics[0]["code"]
        'W_DEAD_GUARD'
        >>> # Positive guard space: x = 1 is a witness for x > 0.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x > 0];
        ... }
        ... ''')
        >>> dead_guard(guarded_transition(machine), variables(machine)).kind
        'sat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _build_type_constraints,
        _definedness_feasibility_or_result,
        _guard_z3_or_result,
        _make_diag,
        _transition_payload,
        is_sat,
    )

    if transition.guard is None:
        return AlgorithmResult(kind="sat")

    guard_z3, z3_vars, guard_domains, result = _guard_z3_or_result(
        transition,
        variables,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result
    type_constraints = _build_type_constraints(variables, z3_vars)
    if guard_domains:
        result = _definedness_feasibility_or_result(
            [*type_constraints, *guard_domains],
            reason=(
                "Transition guard runtime definedness constraints are unsatisfiable."
            ),
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return result

    sat_result = is_sat(
        [
            guard_z3,
            *type_constraints,
            *(guard_domains or ()),
        ],
        timeout_ms=smt_timeout_ms,
    )
    if sat_result.kind == "unsat":
        return AlgorithmResult(
            kind="unsat",
            diagnostics=(
                _make_diag(
                    "W_DEAD_GUARD",
                    "dead_guard",
                    transition=_transition_payload(transition),
                    verification_scope="smt_local",
                ),
            ),
    )
    return AlgorithmResult(kind=sat_result.kind)


def guard_tautology(
    transition: Transition,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect a transition guard that is valid under all assignments.

    This algorithm proves whether a guarded transition is effectively
    unguarded over the modeled variable domain.  It translates the guard once
    and asks whether the negated guard can be satisfied while type and
    runtime-definedness constraints hold.

    Let ``V`` be the current model variables, ``T(V)`` the type-domain
    constraints, ``D_g(V)`` the guard runtime-definedness constraints, and
    ``G(V)`` the translated guard predicate.  The check is:

    .. math::

       \exists V.\ T(V) \land D_g(V) \land \lnot G(V)

    Result semantics:

    * ``kind == "unsat"`` means the negated guard is impossible, so the guard
      is a tautology and the result carries ``W_GUARD_TAUTOLOGY``.
    * ``kind == "sat"`` means a counterexample valuation makes the guard
      false, or the transition has no guard.
    * ``kind == "unknown"`` or ``"timeout"`` means Z3 did not return a
      definite answer.
    * ``kind == "undecidable_skip"`` means translation or definedness failed
      before a sound tautology decision could be made.

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
        >>> from pyfcstm.verify import guard_tautology
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> def guarded_transition(machine):
        ...     return next(
        ...         transition
        ...         for state in machine.walk_states()
        ...         for transition in state.transitions
        ...         if transition.guard is not None
        ...     )
        >>> # Every integer is either non-negative or negative.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x >= 0 || x < 0];
        ... }
        ... ''')
        >>> result = guard_tautology(guarded_transition(machine), variables(machine))
        >>> result.kind
        'unsat'
        >>> result.diagnostics[0]["code"]
        'W_GUARD_TAUTOLOGY'
        >>> # x > 0 is not valid because x = 0 is a counterexample.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B : if [x > 0];
        ... }
        ... ''')
        >>> guard_tautology(guarded_transition(machine), variables(machine)).kind
        'sat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _build_type_constraints,
        _definedness_feasibility_or_result,
        _guard_z3_or_result,
        _make_diag,
        _transition_payload,
        is_sat,
        z3,
    )

    if transition.guard is None:
        return AlgorithmResult(kind="sat")

    guard_z3, z3_vars, guard_domains, result = _guard_z3_or_result(
        transition,
        variables,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result
    type_constraints = _build_type_constraints(variables, z3_vars)
    if guard_domains:
        result = _definedness_feasibility_or_result(
            [*type_constraints, *guard_domains],
            reason=(
                "Transition guard runtime definedness constraints are unsatisfiable."
            ),
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return result

    sat_result = is_sat(
        [
            z3.Not(guard_z3),
            *type_constraints,
            *(guard_domains or ()),
        ],
        timeout_ms=smt_timeout_ms,
    )
    if sat_result.kind == "unsat":
        return AlgorithmResult(
            kind="unsat",
            diagnostics=(
                _make_diag(
                    "W_GUARD_TAUTOLOGY",
                    "guard_tautology",
                    transition=_transition_payload(transition),
                    verification_scope="smt_local",
                ),
            ),
    )
    return AlgorithmResult(kind=sat_result.kind)


def forced_guard_unsat_under_init(
    transition: Transition,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect a forced-transition guard unsatisfiable under initial values.

    Forced transitions are expanded over a source state and its descendants.
    This algorithm checks only forced transitions with guards and asks whether
    the guard can hold immediately under DSL declaration initializers.  It is
    intentionally narrower than :func:`dead_guard`: a guard may be satisfiable
    in general while still impossible at the forced-transition initial point.

    Let ``I(V)`` pin every variable to its DSL initializer, ``D_i(V)`` be the
    initializer runtime-definedness constraints, ``D_g(V)`` the guard
    runtime-definedness constraints under the initialized store, and ``G(V)``
    the forced-transition guard.  The check is:

    .. math::

       \exists V.\ I(V) \land D_i(V) \land D_g(V) \land G(V)

    Result semantics:

    * ``kind == "unsat"`` means the forced guard cannot fire under the
      declaration initial values and the result carries
      ``W_FORCED_GUARD_UNSAT``.
    * ``kind == "sat"`` means the transition is not a guarded forced
      transition, or the initialized guard is feasible.
    * ``kind == "unknown"`` or ``"timeout"`` means the solver could not
      decide the query.
    * ``kind == "undecidable_skip"`` means an initializer, guard, or
      definedness constraint could not be translated soundly.

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
        >>> from pyfcstm.verify import forced_guard_unsat_under_init
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> def forced_transition(machine):
        ...     return next(
        ...         transition
        ...         for state in machine.walk_states()
        ...         for transition in state.transitions
        ...         if transition.is_forced
        ...     )
        >>> # The declaration initializer pins x to 0, so x > 0 is impossible.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     !A -> B : if [x > 0];
        ... }
        ... ''')
        >>> result = forced_guard_unsat_under_init(
        ...     forced_transition(machine),
        ...     variables(machine),
        ... )
        >>> result.kind
        'unsat'
        >>> result.diagnostics[0]["code"]
        'W_FORCED_GUARD_UNSAT'
        >>> # The same forced guard is feasible when the initializer is x = 1.
        >>> machine = parse_machine('''
        ... def int x = 1;
        ... state System {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     !A -> B : if [x > 0];
        ... }
        ... ''')
        >>> forced_guard_unsat_under_init(
        ...     forced_transition(machine),
        ...     variables(machine),
        ... ).kind
        'sat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _build_init_constraints_or_result,
        _definedness_feasibility_or_result,
        _expr_z3_and_domains_or_result,
        _make_diag,
        _transition_payload,
        _z3_vars,
        is_sat,
    )

    if not transition.is_forced or transition.guard is None:
        return AlgorithmResult(kind="sat")

    z3_vars = _z3_vars(variables)
    init_constraints, result = _build_init_constraints_or_result(
        variables,
        z3_vars,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result
    guard_z3, guard_domains, result = _expr_z3_and_domains_or_result(
        transition.guard,
        z3_vars,
        context_constraints=init_constraints,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result
    if guard_domains:
        result = _definedness_feasibility_or_result(
            [*init_constraints, *(guard_domains or ())],
            reason=(
                "Transition guard runtime definedness constraints are "
                "unsatisfiable under initial values."
            ),
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return result

    sat_result = is_sat(
        [guard_z3, *init_constraints, *(guard_domains or ())],
        timeout_ms=smt_timeout_ms,
    )
    if sat_result.kind == "unsat":
        return AlgorithmResult(
            kind="unsat",
            diagnostics=(
                _make_diag(
                    "W_FORCED_GUARD_UNSAT",
                    "forced_guard_unsat_under_init",
                    transition=_transition_payload(transition),
                    scope="dsl_def_init_only",
                    verification_scope="smt_local",
                ),
            ),
        )
    return AlgorithmResult(kind=sat_result.kind)

__all__ = [
    "dead_guard",
    "forced_guard_unsat_under_init",
    "guard_tautology",
]
