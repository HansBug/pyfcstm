"""Guard-focused SMT-local verification algorithms."""

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
    """Detect a transition guard that is unsatisfiable.

    This pure-guard variant does not pin variables to DSL declaration
    initializers.  Use :func:`forced_guard_unsat_under_init` for the separate
    forced-transition check that additionally evaluates guards under DSL
    initial values.

    :param transition: Transition to check.
    :type transition: Transition
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
        ``None`` is forwarded to the solver helper as no timeout.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
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
    """Detect a transition guard that is valid under all assignments.

    :param transition: Transition to check.
    :type transition: Transition
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
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
    """Detect a forced-transition guard unsatisfiable under initial values.

    :param transition: Transition to check.
    :type transition: Transition
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
