"""Effect-focused SMT-local verification algorithms."""

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
    """Detect transition effects that never change model variables.

    Pure syntactic self-assignment blocks such as ``x = x`` are deliberately
    ignored as a presentation-level no-op rather than reported as SMT no-op
    diagnostics.

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
    """Detect effects after which the transition guard cannot still hold.

    The post-effect guard counts as still holding only when it is both
    runtime-defined and true.  If post-state guard definedness is not guaranteed
    under the pre-guard/effect context, the raw algorithm returns
    ``undecidable_skip`` instead of emitting a deterministic contradiction.

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
