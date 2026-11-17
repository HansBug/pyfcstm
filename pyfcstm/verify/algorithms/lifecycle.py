"""Lifecycle-focused SMT-local verification algorithms.

This module checks first-cycle relationships between lifecycle actions.  The
current raw algorithm focuses on the entry path into a leaf state and the first
``during`` chain that can run immediately after entry.  Public callers should
normally import the algorithm from :mod:`pyfcstm.verify`.

Algorithm map:

.. list-table::
   :header-rows: 1

   * - Function
     - Formula shape
     - Diagnostic
   * - :func:`enter_postcondition_implies_during_precondition`
     - Branch-condition determinacy after root initial entry and concrete
       ``enter`` actions.
     - ``I_ENTER_DURING_CONTRADICT``

Example::

    >>> from pyfcstm.verify import enter_postcondition_implies_during_precondition
    >>> callable(enter_postcondition_implies_during_precondition)
    True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Sequence, Set, Tuple

from pyfcstm.verify.result import AlgorithmResult

if TYPE_CHECKING:  # pragma: no cover - imported only for static checkers
    from pyfcstm.model.model import State, VarDefine


def enter_postcondition_implies_during_precondition(
    state: State,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    r"""Detect first-cycle during conditions determined by enter-time values.

    This algorithm detects first-cycle ``during`` branch conditions whose truth
    value is already fixed by declaration initializers, root initial-transition
    effects, and concrete ``enter`` actions along every feasible root initial
    entry path into the leaf state.  It is a local first-cycle check: it does
    not unroll repeated cycles and it skips pseudo states, composite states,
    abstract lifecycle actions, and leaves without concrete ``during`` logic.

    Let ``C`` be the set of feasible initial-entry contexts for leaf state
    ``s``.  Each context ``c`` produces a post-entry symbolic store ``V_c``.
    For a first-cycle branch condition ``p``, the algorithm asks whether each
    context proves one branch direction:

    .. math::

       \forall c \in C.\quad
       \operatorname{unsat}(A_c \land \lnot p(V_c))
       \;\lor\;
       \operatorname{unsat}(A_c \land p(V_c))

    The implementation reports only conditions whose descriptor is common to
    all feasible contexts, so a diagnostic means the same condition is
    determined regardless of which root initial branch reached the state.

    Result semantics:

    * ``kind == "unsat"`` means at least one first-cycle condition has a fixed
      branch direction after entry and diagnostics carry
      ``I_ENTER_DURING_CONTRADICT``.
    * ``kind == "sat"`` means no common first-cycle condition is proven fixed,
      or the state is outside the algorithm scope.
    * ``kind == "unknown"`` or ``"timeout"`` means a solver query was
      inconclusive and no deterministic diagnostic was emitted.
    * ``kind == "undecidable_skip"`` means entry-path or operation translation
      could not provide sound first-cycle evidence.

    :param state: State to inspect.
    :type state: State
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
        >>> from pyfcstm.verify import enter_postcondition_implies_during_precondition
        >>> def parse_machine(source):
        ...     ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
        ...     return parse_dsl_node_to_state_machine(ast)
        >>> def variables(machine):
        ...     return tuple(machine.defines.values())
        >>> # A.enter sets x = 1, so the first-cycle during condition is true.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A {
        ...         enter { x = 1; }
        ...         during {
        ...             if [x > 0] { x = x + 1; } else { x = x - 1; }
        ...         }
        ...     }
        ...     [*] -> A;
        ... }
        ... ''')
        >>> state_a = machine.root_state.substates["A"]
        >>> result = enter_postcondition_implies_during_precondition(
        ...     state_a,
        ...     variables(machine),
        ... )
        >>> result.kind
        'unsat'
        >>> result.diagnostics[0]["code"]
        'I_ENTER_DURING_CONTRADICT'
        >>> result.diagnostics[0]["data"]["branch_taken"]
        'true'
        >>> # A leaf without concrete during operations is outside the scope.
        >>> machine = parse_machine('''
        ... def int x = 0;
        ... state System {
        ...     state A {
        ...         enter { x = 1; }
        ...     }
        ...     [*] -> A;
        ... }
        ... ''')
        >>> enter_postcondition_implies_during_precondition(
        ...     machine.root_state.substates["A"],
        ...     variables(machine),
        ... ).kind
        'sat'
    """
    from pyfcstm.verify.encoding._core import (
        AlgorithmResult,
        _build_init_constraints_or_result,
        _build_type_constraints,
        _concrete_during_operations,
        _enter_condition_descriptors_for_context,
        _first_indeterminate,
        _make_diag,
        _root_initial_path_contexts,
        _state_path,
        _z3_vars,
    )

    if not state.is_leaf_state or state.is_pseudo:
        return AlgorithmResult(kind="sat")

    z3_vars = _z3_vars(variables)
    init_constraints, result = _build_init_constraints_or_result(
        variables,
        z3_vars,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return result

    contexts, result = (
        _root_initial_path_contexts(
            state,
            variables,
            z3_vars,
            init_constraints,
            smt_timeout_ms=smt_timeout_ms,
        )
    )
    if result is not None:
        return result
    if contexts is None:
        return AlgorithmResult(kind="sat")

    first_cycle_operations = _concrete_during_operations(state)
    if not first_cycle_operations:
        return AlgorithmResult(kind="sat")

    type_constraints = _build_type_constraints(variables, z3_vars)
    first_indeterminate_result: Optional[AlgorithmResult] = None
    common_descriptors: Optional[Set[Tuple[str, str, str]]] = None

    for context in contexts:
        descriptors, result = _enter_condition_descriptors_for_context(
            state,
            variables,
            z3_vars,
            init_constraints,
            type_constraints,
            first_cycle_operations,
            context,
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                result.kind,
                result.reason,
            )
            common_descriptors = set()
            continue
        if common_descriptors is None:
            common_descriptors = set(descriptors or ())
        else:
            common_descriptors &= set(descriptors or ())

    diagnostics: List[dict] = []
    for condition, condition_source, branch_taken in sorted(
        common_descriptors or ()
    ):
        diagnostics.append(
            _make_diag(
                "I_ENTER_DURING_CONTRADICT",
                "enter_postcondition_implies_during_precondition",
                state=_state_path(state),
                condition=condition,
                condition_source=condition_source,
                branch_taken=branch_taken,
                verification_scope="smt_local",
            )
        )

    if diagnostics:
        return AlgorithmResult(kind="unsat", diagnostics=tuple(diagnostics))
    if first_indeterminate_result is not None:
        return first_indeterminate_result
    return AlgorithmResult(kind="sat")

__all__ = [
    "enter_postcondition_implies_during_precondition",
]
