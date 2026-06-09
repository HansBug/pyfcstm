"""Lifecycle-focused SMT-local verification algorithms."""

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
    """Detect first-cycle during conditions determined by enter-time values.

    :param state: State to inspect.
    :type state: State
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
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
