"""SMT-local verification algorithms for FCSTM models.

This module implements the Track A / PR-A4 algorithms from issue #114.  The
functions intentionally return lightweight dictionaries instead of
``ModelDiagnostic`` objects; PR-B1 is responsible for adapting these raw
algorithm results to the diagnostics layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence, Tuple, Union

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

import z3

if TYPE_CHECKING:  # pragma: no cover - imported only for static checkers
    from pyfcstm.model.expr import Expr
    from pyfcstm.model.model import (
        OnAspect,
        OnStage,
        OperationStatement,
        State,
        StateMachine,
        Transition,
        VarDefine,
    )
    from pyfcstm.solver.safety import SafetyCheck

ResultKind = Literal[
    "sat",
    "unsat",
    "unknown",
    "timeout",
    "unsafe_skip",
    "undecidable_skip",
]

_Z3Expr = Union[z3.ArithRef, z3.BoolRef]
_Z3Vars = Dict[str, _Z3Expr]


def _dsl_nodes():
    """Import DSL node sentinels lazily to keep registry import lightweight."""
    from pyfcstm.dsl import node as dsl_nodes

    return dsl_nodes


def _conditional_op_type():
    """Import ``ConditionalOp`` lazily for runtime ``isinstance`` checks."""
    from pyfcstm.model.expr import ConditionalOp

    return ConditionalOp


def _variable_type():
    """Import ``Variable`` lazily for runtime ``isinstance`` checks."""
    from pyfcstm.model.expr import Variable

    return Variable


def _operation_type():
    """Import ``Operation`` lazily for runtime ``isinstance`` checks."""
    from pyfcstm.model.model import Operation

    return Operation


def _if_block_type():
    """Import ``IfBlock`` lazily for runtime ``isinstance`` checks."""
    from pyfcstm.model.model import IfBlock

    return IfBlock


def create_z3_vars_from_models(models):
    """Delegate to :func:`pyfcstm.solver.expr.create_z3_vars_from_models`."""
    from pyfcstm.solver.expr import create_z3_vars_from_models as impl

    return impl(models)


def expr_to_z3(expr, z3_vars):
    """Delegate to :func:`pyfcstm.solver.expr.expr_to_z3`."""
    from pyfcstm.solver.expr import expr_to_z3 as impl

    return impl(expr, z3_vars)


def is_sat(constraints, *, timeout_ms=None, get_model=False):
    """Delegate to :func:`pyfcstm.solver.logical.is_sat`."""
    from pyfcstm.solver.logical import is_sat as impl

    return impl(constraints, timeout_ms=timeout_ms, get_model=get_model)


def execute_operations(operations, z3_vars):
    """Delegate to :func:`pyfcstm.solver.operation.execute_operations`."""
    from pyfcstm.solver.operation import execute_operations as impl

    return impl(operations, z3_vars)


def check_expr_safety(expr):
    """Delegate to :func:`pyfcstm.solver.safety.check_expr_safety`."""
    from pyfcstm.solver.safety import check_expr_safety as impl

    return impl(expr)


def check_expr_safety_for_effect(ops):
    """Delegate to :func:`pyfcstm.solver.safety.check_expr_safety_for_effect`."""
    from pyfcstm.solver.safety import check_expr_safety_for_effect as impl

    return impl(ops)


@dataclass(frozen=True)
class AlgorithmResult:
    """Result returned by one SMT-local verification algorithm.

    :param kind: Normalized solver or skip outcome.
    :type kind: ResultKind
    :param diagnostics: Raw diagnostic dictionaries produced by the algorithm.
        These stay diagnostics-layer independent until PR-B1.
    :type diagnostics: Tuple[dict, ...]
    :param reason: Optional reason for ``unknown`` / ``timeout`` / skip results,
        defaults to ``None``.
    :type reason: Optional[str], optional
    """

    kind: ResultKind
    diagnostics: Tuple[dict, ...] = ()
    reason: Optional[str] = None


def _make_diag(code: str, algorithm_name: str, **data) -> dict:
    """Create a raw verify diagnostic payload.

    :param code: Future diagnostics code.
    :type code: str
    :param algorithm_name: Algorithm that emitted the payload.
    :type algorithm_name: str
    :param data: Algorithm-specific payload fields.
    :return: Raw diagnostic dictionary.
    :rtype: dict
    """
    return {
        "code": code,
        "algorithm_name": algorithm_name,
        "data": data,
    }


def _state_path(state: Optional[State]) -> Optional[str]:
    """Return a readable state path or ``None``.

    :param state: State to format.
    :type state: Optional[State]
    :return: Dot-separated path.
    :rtype: Optional[str]
    """
    if state is None:
        return None
    return ".".join(state.path)


def _state_name(value) -> str:
    """Return a readable transition endpoint name.

    :param value: Transition endpoint value.
    :return: Endpoint name.
    :rtype: str
    """
    if value is _dsl_nodes().INIT_STATE:
        return "[*]"
    if value is _dsl_nodes().EXIT_STATE:
        return "[*]"
    return str(value)


def _event_name(transition: Transition) -> Optional[str]:
    """Return a transition event path when present.

    :param transition: Transition to inspect.
    :type transition: Transition
    :return: Event path.
    :rtype: Optional[str]
    """
    if transition.event is None:
        return None
    return transition.event.path_name


def _transition_payload(transition: Transition) -> dict:
    """Create a stable, diagnostics-layer-free transition payload.

    :param transition: Transition to describe.
    :type transition: Transition
    :return: Transition payload.
    :rtype: dict
    """
    return {
        "parent": _state_path(transition.parent),
        "from_state": _state_name(transition.from_state),
        "to_state": _state_name(transition.to_state),
        "event": _event_name(transition),
        "guard": str(transition.guard) if transition.guard is not None else None,
        "is_forced": transition.is_forced,
    }


def _skip_result(kind: ResultKind, reason: Optional[str]) -> AlgorithmResult:
    """Create a skip or indeterminate result.

    :param kind: Result kind.
    :type kind: ResultKind
    :param reason: Optional reason text.
    :type reason: Optional[str]
    :return: Algorithm result.
    :rtype: AlgorithmResult
    """
    return AlgorithmResult(kind=kind, diagnostics=(), reason=reason)


def _unsafe_result(safety: SafetyCheck) -> AlgorithmResult:
    """Create an unsafe-skip result from a safety check.

    :param safety: Safety check result.
    :type safety: SafetyCheck
    :return: Unsafe-skip result.
    :rtype: AlgorithmResult
    """
    return _skip_result("unsafe_skip", safety.reason)


def _merge_safety_checks(*checks: SafetyCheck) -> Optional[AlgorithmResult]:
    """Return the first unsafe check as an algorithm result.

    :param checks: Safety checks to inspect.
    :return: First unsafe result, or ``None`` if all checks are safe.
    :rtype: Optional[AlgorithmResult]
    """
    for check in checks:
        if not check.safe:
            return _unsafe_result(check)
    return None


def _z3_vars(variables: Sequence[VarDefine]) -> _Z3Vars:
    """Create Z3 variables from a generic sequence of variable definitions.

    :param variables: FCSTM variable definitions.
    :type variables: Sequence[VarDefine]
    :return: Variable-name to Z3 expression mapping.
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    """
    return create_z3_vars_from_models(list(variables))


def _build_type_constraints(
    variables: Sequence[VarDefine],
    z3_vars: _Z3Vars,
) -> Tuple[z3.ExprRef, ...]:
    """Build type-domain constraints for variable definitions.

    The current solver layer models ``int`` / ``float`` as unbounded
    ``z3.Int`` / ``z3.Real`` values, so no extra constraints are needed.
    The helper exists to keep PR-A4 formulas aligned with the issue #114
    pseudo-code and to give future bit-width work a single insertion point.

    :param variables: FCSTM variable definitions.
    :type variables: Sequence[VarDefine]
    :param z3_vars: Z3 variable mapping.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Type-domain constraints.
    :rtype: Tuple[z3.ExprRef, ...]
    """
    _ = variables, z3_vars
    return ()


def _expr_to_z3_or_result(
    expr: Expr,
    z3_vars: _Z3Vars,
) -> Tuple[Optional[_Z3Expr], Optional[AlgorithmResult]]:
    """Translate an expression to Z3, normalizing expected translation failures.

    :param expr: Expression to translate.
    :type expr: Expr
    :param z3_vars: Z3 variable mapping.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Pair of translated expression and optional failure result.
    :rtype: Tuple[Optional[Union[z3.ArithRef, z3.BoolRef]], Optional[AlgorithmResult]]
    """
    try:
        return expr_to_z3(expr, z3_vars), None
    except NotImplementedError as err:
        # NotImplementedError: expr_to_z3 raises this for unsupported math
        # functions such as logarithms or trigonometric functions.
        return None, _skip_result("unsafe_skip", str(err))
    except ValueError as err:
        # ValueError: expr_to_z3 raises this for unknown variables or operators.
        return None, _skip_result("undecidable_skip", str(err))
    except z3.Z3Exception as err:
        # Z3Exception: Z3 can reject otherwise parsed expressions for sort or
        # operator-domain mismatches, for example modulo over Real operands.
        return None, _skip_result("undecidable_skip", str(err))


def _execute_operations_or_result(
    operations: Sequence[OperationStatement],
    z3_vars: _Z3Vars,
) -> Tuple[Optional[_Z3Vars], Optional[AlgorithmResult]]:
    """Symbolically execute operations, normalizing expected translation failures.

    :param operations: Operation block to execute.
    :type operations: Sequence[OperationStatement]
    :param z3_vars: Starting symbolic environment.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Pair of post-state environment and optional failure result.
    :rtype: Tuple[Optional[Dict[str, Union[z3.ArithRef, z3.BoolRef]]], Optional[AlgorithmResult]]
    """
    try:
        return execute_operations(list(operations), dict(z3_vars)), None
    except NotImplementedError as err:
        # NotImplementedError: execute_operations delegates expression
        # translation to expr_to_z3, which raises this for unsupported functions.
        return None, _skip_result("unsafe_skip", str(err))
    except ValueError as err:
        # ValueError: execute_operations delegates to expr_to_z3, which raises
        # this for unknown variables or unsupported operators.
        return None, _skip_result("undecidable_skip", str(err))
    except z3.Z3Exception as err:
        # Z3Exception: Z3 can reject symbolic operation expressions because of
        # sort/operator-domain mismatches.
        return None, _skip_result("undecidable_skip", str(err))


def _build_init_constraints_or_result(
    variables: Sequence[VarDefine],
    z3_vars: _Z3Vars,
) -> Tuple[Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]]:
    """Build constraints pinning variables to their DSL initial values.

    :param variables: FCSTM variable definitions.
    :type variables: Sequence[VarDefine]
    :param z3_vars: Z3 variable mapping.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Pair of constraints and optional failure result.
    :rtype: Tuple[Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]]
    """
    constraints: List[z3.ExprRef] = []
    for variable in variables:
        init_value, result = _expr_to_z3_or_result(variable.init, z3_vars)
        if result is not None:
            return None, result
        constraints.append(z3_vars[variable.name] == init_value)
    return tuple(constraints), None


def _guard_z3_or_result(
    transition: Transition,
    variables: Sequence[VarDefine],
) -> Tuple[Optional[_Z3Expr], Optional[_Z3Vars], Optional[AlgorithmResult]]:
    """Check and translate a transition guard.

    :param transition: Transition with a non-``None`` guard.
    :type transition: Transition
    :param variables: FCSTM variable definitions.
    :type variables: Sequence[VarDefine]
    :return: Guard Z3 expression, variable mapping, and optional failure result.
    :rtype: tuple
    """
    safety = check_expr_safety(transition.guard)
    if not safety.safe:
        return None, None, _unsafe_result(safety)

    z3_vars = _z3_vars(variables)
    guard_expr, result = _expr_to_z3_or_result(transition.guard, z3_vars)
    if result is not None:
        return None, None, result
    return guard_expr, z3_vars, None


def _is_self_assign(statement: OperationStatement) -> bool:
    """Return whether a statement is a plain ``x = x`` assignment.

    :param statement: Operation statement.
    :type statement: OperationStatement
    :return: Whether the statement is a self-assignment.
    :rtype: bool
    """
    return (
        isinstance(statement, _operation_type())
        and isinstance(statement.expr, _variable_type())
        and statement.expr.name == statement.var_name
    )


def _is_syntactically_self_assign_only(
    operations: Sequence[OperationStatement],
) -> bool:
    """Return whether every statement in a block is syntactic self-assignment.

    :param operations: Operation statements.
    :type operations: Sequence[OperationStatement]
    :return: Whether the block is only self-assignments.
    :rtype: bool
    """
    return bool(operations) and all(
        _is_self_assign(statement) for statement in operations
    )


def _first_indeterminate(
    current: Optional[AlgorithmResult],
    candidate_kind: str,
    reason: Optional[str] = None,
) -> Optional[AlgorithmResult]:
    """Keep the first indeterminate result for aggregate algorithms.

    :param current: Existing aggregate result.
    :type current: Optional[AlgorithmResult]
    :param candidate_kind: Candidate kind string from a solver result.
    :type candidate_kind: str
    :param reason: Optional reason.
    :type reason: Optional[str]
    :return: Existing or new aggregate result.
    :rtype: Optional[AlgorithmResult]
    """
    if current is not None:
        return current
    if candidate_kind in {"unknown", "timeout", "unsafe_skip", "undecidable_skip"}:
        return _skip_result(candidate_kind, reason)
    return None


def dead_guard(
    transition: Transition,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = 1000,
) -> AlgorithmResult:
    """Detect a transition guard that is unsatisfiable.

    :param transition: Transition to check.
    :type transition: Transition
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds, defaults to
        ``1000``.  ``None`` is forwarded to the solver helper as no timeout.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
    """
    if transition.guard is None:
        return AlgorithmResult(kind="sat")

    guard_z3, z3_vars, result = _guard_z3_or_result(transition, variables)
    if result is not None:
        return result

    sat_result = is_sat(
        [guard_z3, *_build_type_constraints(variables, z3_vars)],
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
    smt_timeout_ms: Optional[int] = 1000,
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
    if transition.guard is None:
        return AlgorithmResult(kind="sat")

    guard_z3, z3_vars, result = _guard_z3_or_result(transition, variables)
    if result is not None:
        return result

    sat_result = is_sat(
        [z3.Not(guard_z3), *_build_type_constraints(variables, z3_vars)],
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
    smt_timeout_ms: Optional[int] = 1000,
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
    if not transition.is_forced or transition.guard is None:
        return AlgorithmResult(kind="sat")

    guard_z3, z3_vars, result = _guard_z3_or_result(transition, variables)
    if result is not None:
        return result
    init_constraints, result = _build_init_constraints_or_result(variables, z3_vars)
    if result is not None:
        return result

    sat_result = is_sat(
        [guard_z3, *init_constraints],
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
                    verification_scope="smt_local",
                ),
            ),
        )
    return AlgorithmResult(kind=sat_result.kind)


def effect_no_op_under_guard(
    transition: Transition,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = 1000,
) -> AlgorithmResult:
    """Detect transition effects that never change model variables.

    :param transition: Transition to check.
    :type transition: Transition
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
    """
    if not transition.effects:
        return AlgorithmResult(kind="sat")
    if _is_syntactically_self_assign_only(transition.effects):
        return AlgorithmResult(kind="sat")

    result = _merge_safety_checks(
        check_expr_safety(transition.guard),
        check_expr_safety_for_effect(transition.effects),
    )
    if result is not None:
        return result

    z3_vars = _z3_vars(variables)
    after_vars, result = _execute_operations_or_result(transition.effects, z3_vars)
    if result is not None:
        return result

    if transition.guard is None:
        guard_z3 = z3.BoolVal(True)
    else:
        guard_z3, result = _expr_to_z3_or_result(transition.guard, z3_vars)
        if result is not None:
            return result

    changed_disjuncts = [
        after_vars[variable.name] != z3_vars[variable.name] for variable in variables
    ]
    if not changed_disjuncts:
        return AlgorithmResult(kind="sat")

    formula = z3.And(
        guard_z3,
        z3.Or(*changed_disjuncts),
        *_build_type_constraints(variables, z3_vars),
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
    smt_timeout_ms: Optional[int] = 1000,
) -> AlgorithmResult:
    """Detect effects after which the transition guard cannot still hold.

    :param transition: Transition to check.
    :type transition: Transition
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
    """
    if transition.guard is None or not transition.effects:
        return AlgorithmResult(kind="sat")

    result = _merge_safety_checks(
        check_expr_safety(transition.guard),
        check_expr_safety_for_effect(transition.effects),
    )
    if result is not None:
        return result

    z3_vars = _z3_vars(variables)
    guard_before, result = _expr_to_z3_or_result(transition.guard, z3_vars)
    if result is not None:
        return result
    after_vars, result = _execute_operations_or_result(transition.effects, z3_vars)
    if result is not None:
        return result
    guard_after, result = _expr_to_z3_or_result(transition.guard, after_vars)
    if result is not None:
        return result
    type_constraints = _build_type_constraints(variables, z3_vars)

    guard_feasible = is_sat(
        [guard_before, *type_constraints],
        timeout_ms=smt_timeout_ms,
    )
    if guard_feasible.kind == "unsat":
        return AlgorithmResult(kind="sat")
    if guard_feasible.kind != "sat":
        return AlgorithmResult(kind=guard_feasible.kind)

    sat_result = is_sat(
        [
            guard_before,
            guard_after,
            *type_constraints,
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


def _domain_key(transition: Transition):
    """Return the transition trigger domain key.

    :param transition: Transition to inspect.
    :type transition: Transition
    :return: Domain key.
    """
    if transition.guard is not None:
        return "guard"
    if transition.event is not None:
        return ("event", transition.event.path_name)
    return "unconditional"


def _iter_ordered_outgoing(
    machine: StateMachine,
) -> Iterable[Tuple[State, List[Transition]]]:
    """Yield source states and their ordered outgoing transitions.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :yield: Source state and transitions in model order.
    :rtype: Iterable[Tuple[State, List[Transition]]]
    """
    states_by_parent_and_name: Dict[Tuple[Tuple[str, ...], str], State] = {}
    for state in machine.walk_states():
        if state.parent is not None:
            states_by_parent_and_name[(state.parent.path, state.name)] = state

    for scope in machine.walk_states():
        by_source: Dict[str, List[Transition]] = {}
        for transition in scope.transitions:
            if not isinstance(transition.from_state, str):
                continue
            by_source.setdefault(transition.from_state, []).append(transition)

        for source_name, transitions in by_source.items():
            source = states_by_parent_and_name.get((scope.path, source_name))
            if source is not None:
                yield source, transitions


def transition_shadowed_by_predecessor(
    machine: StateMachine,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = 1000,
) -> AlgorithmResult:
    """Detect outgoing transitions shadowed by earlier transitions.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
    """
    diagnostics: List[dict] = []
    first_indeterminate_result: Optional[AlgorithmResult] = None

    for source, outgoing in _iter_ordered_outgoing(machine):
        prior_unconditional: Optional[Transition] = None
        prior_events: Dict[str, Transition] = {}
        prior_guards: List[Transition] = []

        for transition in outgoing:
            if prior_unconditional is not None:
                diagnostics.append(
                    _make_diag(
                        "W_TRANSITION_SHADOWED",
                        "transition_shadowed_by_predecessor",
                        transition=_transition_payload(transition),
                        shadowed_by=(_transition_payload(prior_unconditional),),
                        reason="unconditional_catchall",
                        source=_state_path(source),
                        verification_scope="topological_only",
                    )
                )
                continue

            key = _domain_key(transition)
            if key == "unconditional":
                prior_unconditional = transition
                continue

            if isinstance(key, tuple) and key[0] == "event":
                event_name = key[1]
                if event_name in prior_events:
                    diagnostics.append(
                        _make_diag(
                            "W_TRANSITION_SHADOWED",
                            "transition_shadowed_by_predecessor",
                            transition=_transition_payload(transition),
                            shadowed_by=(
                                _transition_payload(prior_events[event_name]),
                            ),
                            reason="duplicate_event",
                            source=_state_path(source),
                            verification_scope="topological_only",
                        )
                    )
                else:
                    prior_events[event_name] = transition
                continue

            if key == "guard":
                safety = check_expr_safety(transition.guard)
                if not safety.safe:
                    first_indeterminate_result = _first_indeterminate(
                        first_indeterminate_result,
                        "unsafe_skip",
                        safety.reason,
                    )
                    prior_guards.append(transition)
                    continue

                z3_vars = _z3_vars(variables)
                current_guard, result = _expr_to_z3_or_result(transition.guard, z3_vars)
                if result is not None:
                    first_indeterminate_result = _first_indeterminate(
                        first_indeterminate_result,
                        result.kind,
                        result.reason,
                    )
                    prior_guards.append(transition)
                    continue

                predecessor_guards: List[z3.ExprRef] = []
                predecessor_payloads = []
                predecessor_unsafe = False
                for prior_guard_transition in prior_guards:
                    prior_safety = check_expr_safety(prior_guard_transition.guard)
                    if not prior_safety.safe:
                        first_indeterminate_result = _first_indeterminate(
                            first_indeterminate_result,
                            "unsafe_skip",
                            prior_safety.reason,
                        )
                        predecessor_unsafe = True
                        break
                    prior_guard, result = _expr_to_z3_or_result(
                        prior_guard_transition.guard,
                        z3_vars,
                    )
                    if result is not None:
                        first_indeterminate_result = _first_indeterminate(
                            first_indeterminate_result,
                            result.kind,
                            result.reason,
                        )
                        predecessor_unsafe = True
                        break
                    predecessor_guards.append(z3.Not(prior_guard))
                    predecessor_payloads.append(
                        _transition_payload(prior_guard_transition)
                    )

                if not predecessor_unsafe and predecessor_guards:
                    formula = z3.And(
                        current_guard,
                        *predecessor_guards,
                        *_build_type_constraints(variables, z3_vars),
                    )
                    sat_result = is_sat([formula], timeout_ms=smt_timeout_ms)
                    if sat_result.kind == "unsat":
                        diagnostics.append(
                            _make_diag(
                                "W_TRANSITION_SHADOWED",
                                "transition_shadowed_by_predecessor",
                                transition=_transition_payload(transition),
                                shadowed_by=tuple(predecessor_payloads),
                                reason="guard_shadow",
                                source=_state_path(source),
                                verification_scope="smt_local",
                            )
                        )
                    else:
                        first_indeterminate_result = _first_indeterminate(
                            first_indeterminate_result,
                            sat_result.kind,
                        )

                prior_guards.append(transition)

    if diagnostics:
        return AlgorithmResult(kind="unsat", diagnostics=tuple(diagnostics))
    if first_indeterminate_result is not None:
        return first_indeterminate_result
    return AlgorithmResult(kind="sat")


def _action_operations(
    actions: Sequence[Union[OnStage, OnAspect]],
) -> List[OperationStatement]:
    """Collect concrete operation statements from lifecycle actions.

    :param actions: Lifecycle actions.
    :type actions: Sequence[Union[OnStage, OnAspect]]
    :return: Flattened concrete operation statements.
    :rtype: List[OperationStatement]
    """
    operations: List[OperationStatement] = []
    for action in actions:
        target = action.ref if action.is_ref else action
        if target is None or target.is_abstract:
            continue
        operations.extend(target.operations)
    return operations


def _conditional_conditions_from_expr(expr: Expr) -> Iterable[Expr]:
    """Yield every ternary condition inside an expression.

    :param expr: Expression to scan.
    :type expr: Expr
    :yield: Ternary condition expressions.
    :rtype: Iterable[Expr]
    """
    if isinstance(expr, _conditional_op_type()):
        yield expr.cond
    for child in expr._iter_subs():
        yield from _conditional_conditions_from_expr(child)


def _conditional_conditions_from_operations(
    operations: Sequence[OperationStatement],
) -> Iterable[Expr]:
    """Yield conditions from ternary expressions and operation ``if`` blocks.

    :param operations: Operation statements to scan.
    :type operations: Sequence[OperationStatement]
    :yield: Conditional expressions.
    :rtype: Iterable[Expr]
    """
    for statement in operations:
        if isinstance(statement, _operation_type()):
            yield from _conditional_conditions_from_expr(statement.expr)
            continue
        if isinstance(statement, _if_block_type()):
            for branch in statement.branches:
                if branch.condition is not None:
                    yield branch.condition
                yield from _conditional_conditions_from_operations(branch.statements)


def enter_postcondition_implies_during_precondition(
    state: State,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = 1000,
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
    if not state.is_leaf_state or state.is_pseudo:
        return AlgorithmResult(kind="sat")

    enter_operations = _action_operations(state.on_enters)
    during_operations = _action_operations(state.on_durings)
    if not enter_operations or not during_operations:
        return AlgorithmResult(kind="sat")

    result = _merge_safety_checks(
        check_expr_safety_for_effect(enter_operations),
        check_expr_safety_for_effect(during_operations),
    )
    if result is not None:
        return result

    conditions = tuple(_conditional_conditions_from_operations(during_operations))
    if not conditions:
        return AlgorithmResult(kind="sat")

    z3_vars = _z3_vars(variables)
    init_constraints, result = _build_init_constraints_or_result(variables, z3_vars)
    if result is not None:
        return result
    enter_vars, result = _execute_operations_or_result(enter_operations, z3_vars)
    if result is not None:
        return result

    type_constraints = _build_type_constraints(variables, z3_vars)
    diagnostics: List[dict] = []
    first_indeterminate_result: Optional[AlgorithmResult] = None

    for condition in conditions:
        condition_z3, result = _expr_to_z3_or_result(condition, enter_vars)
        if result is not None:
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                result.kind,
                result.reason,
            )
            continue

        true_check = is_sat(
            [condition_z3, *init_constraints, *type_constraints],
            timeout_ms=smt_timeout_ms,
        )
        false_check = is_sat(
            [z3.Not(condition_z3), *init_constraints, *type_constraints],
            timeout_ms=smt_timeout_ms,
        )

        if true_check.kind == "unsat":
            diagnostics.append(
                _make_diag(
                    "I_ENTER_DURING_CONTRADICT",
                    "enter_postcondition_implies_during_precondition",
                    state=_state_path(state),
                    condition=str(condition),
                    branch_taken="false",
                    verification_scope="smt_local",
                )
            )
        elif false_check.kind == "unsat":
            diagnostics.append(
                _make_diag(
                    "I_ENTER_DURING_CONTRADICT",
                    "enter_postcondition_implies_during_precondition",
                    state=_state_path(state),
                    condition=str(condition),
                    branch_taken="true",
                    verification_scope="smt_local",
                )
            )
        else:
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                true_check.kind,
            )
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                false_check.kind,
            )

    if diagnostics:
        return AlgorithmResult(kind="unsat", diagnostics=tuple(diagnostics))
    if first_indeterminate_result is not None:
        return first_indeterminate_result
    return AlgorithmResult(kind="sat")


def _event_bool_name(transition: Transition) -> str:
    """Return a Z3-safe-ish event boolean variable name.

    :param transition: Event transition.
    :type transition: Transition
    :return: Event boolean name.
    :rtype: str
    """
    event = _event_name(transition) or "anonymous"
    return "__event__" + event.replace(".", "__")


def composite_init_guards_incomplete(
    machine: StateMachine,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = 1000,
) -> AlgorithmResult:
    """Detect composite states whose initial transitions do not cover inputs.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Algorithm result.
    :rtype: AlgorithmResult
    """
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

        unsafe_safety: Optional[SafetyCheck] = None
        for transition in init_transitions:
            safety = check_expr_safety(transition.guard)
            if not safety.safe:
                unsafe_safety = safety
                break
        if unsafe_safety is not None:
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                "unsafe_skip",
                unsafe_safety.reason,
            )
            continue

        z3_vars = _z3_vars(variables)
        event_vars: Dict[str, z3.BoolRef] = {}
        triggers: List[z3.ExprRef] = []
        per_composite_failed = False
        for transition in init_transitions:
            if transition.guard is not None:
                guard_expr, result = _expr_to_z3_or_result(transition.guard, z3_vars)
                if result is not None:
                    first_indeterminate_result = _first_indeterminate(
                        first_indeterminate_result,
                        result.kind,
                        result.reason,
                    )
                    per_composite_failed = True
                    break
                triggers.append(guard_expr)
                continue

            event_key = _event_bool_name(transition)
            event_vars.setdefault(event_key, z3.Bool(event_key))
            triggers.append(event_vars[event_key])

        if per_composite_failed or not triggers:
            continue

        no_coverage = z3.Not(z3.Or(*triggers))
        sat_result = is_sat(
            [
                no_coverage,
                *_build_type_constraints(variables, z3_vars),
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
    "AlgorithmResult",
    "ResultKind",
    "composite_init_guards_incomplete",
    "dead_guard",
    "effect_contradicts_guard",
    "effect_no_op_under_guard",
    "enter_postcondition_implies_during_precondition",
    "forced_guard_unsat_under_init",
    "guard_tautology",
    "transition_shadowed_by_predecessor",
]
