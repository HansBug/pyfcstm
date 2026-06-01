"""SMT-local verification algorithms for FCSTM models.

This module implements the Track A / PR-A4 algorithms from issue #114.  Raw
verify algorithms are full-power by default: they do not consult
``pyfcstm.solver.safety`` or diagnostics/inspect policy gates, and
``smt_timeout_ms=None`` leaves the underlying solver timeout unset.  Callers
that need product-level limits can pass optional budgets or apply policy in an
adapter layer.

The functions intentionally return lightweight dictionaries instead of
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

ResultKind = Literal[
    "sat",
    "unsat",
    "unknown",
    "timeout",
    "undecidable_skip",
]

_Z3Expr = Union[z3.ArithRef, z3.BoolRef]
_Z3Vars = Dict[str, _Z3Expr]


@dataclass(frozen=True)
class _ConditionPoint:
    """Condition expression with its symbolic store and path predicates."""

    condition: "Expr"
    z3_vars: _Z3Vars
    path_conditions: Tuple[z3.ExprRef, ...] = ()
    source: str = "expression"
    z3_condition: Optional[z3.ExprRef] = None


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


def python_round_to_z3(operand):
    """Delegate to :func:`pyfcstm.solver.expr.python_round_to_z3`."""
    from pyfcstm.solver.expr import python_round_to_z3 as impl

    return impl(operand)


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
        return None, _skip_result("undecidable_skip", str(err))
    except ValueError as err:
        # ValueError: expr_to_z3 raises this for unknown variables or operators.
        return None, _skip_result("undecidable_skip", str(err))
    except TypeError as err:
        # TypeError: expr_to_z3 may delegate unsupported Python/Z3 operators
        # before Z3 creates an expression, for example Int left-shift.
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
        return None, _skip_result("undecidable_skip", str(err))
    except ValueError as err:
        # ValueError: execute_operations delegates to expr_to_z3, which raises
        # this for unknown variables or unsupported operators.
        return None, _skip_result("undecidable_skip", str(err))
    except TypeError as err:
        # TypeError: execute_operations delegates to expr_to_z3 and can also
        # surface unsupported Python/Z3 operator combinations before Z3 wraps
        # them in Z3Exception.
        return None, _skip_result("undecidable_skip", str(err))
    except z3.Z3Exception as err:
        # Z3Exception: Z3 can reject symbolic operation expressions because of
        # sort/operator-domain mismatches.
        return None, _skip_result("undecidable_skip", str(err))


def _binary_z3_or_result(
    op: str,
    left: _Z3Expr,
    right: _Z3Expr,
) -> Tuple[Optional[_Z3Expr], Optional[AlgorithmResult]]:
    """Apply a binary operator to already translated Z3 operands.

    This mirrors :func:`pyfcstm.solver.expr.expr_to_z3` for expression trees
    whose children were translated path-sensitively.

    :param op: DSL binary operator.
    :type op: str
    :param left: Left Z3 operand.
    :type left: Union[z3.ArithRef, z3.BoolRef]
    :param right: Right Z3 operand.
    :type right: Union[z3.ArithRef, z3.BoolRef]
    :return: Translated Z3 expression and optional normalized failure.
    :rtype: Tuple[Optional[Union[z3.ArithRef, z3.BoolRef]], Optional[AlgorithmResult]]
    """
    try:
        if op == "+":
            return left + right, None
        if op == "-":
            return left - right, None
        if op == "*":
            return left * right, None
        if op == "/":
            return left / right, None
        if op == "%":
            return left % right, None
        if op == "**":
            return left**right, None
        if op == "&":
            return left & right, None
        if op == "|":
            return left | right, None
        if op == "^":
            return left ^ right, None
        if op == "<<":
            return left << right, None
        if op == ">>":
            return left >> right, None
        if op == "<":
            return left < right, None
        if op == "<=":
            return left <= right, None
        if op == ">":
            return left > right, None
        if op == ">=":
            return left >= right, None
        if op == "==":
            return left == right, None
        if op == "!=":
            return left != right, None
        if op in ("&&", "and"):
            return z3.And(left, right), None
        if op in ("||", "or"):
            return z3.Or(left, right), None
        return None, _skip_result(
            "undecidable_skip", f"Unsupported binary operator: {op}"
        )
    except TypeError as err:
        # TypeError: Python/Z3 operator overloads reject unsupported operand
        # combinations, for example bitwise Int expressions.
        return None, _skip_result("undecidable_skip", str(err))
    except z3.Z3Exception as err:
        # Z3Exception: Z3 rejects sort/operator-domain mismatches.
        return None, _skip_result("undecidable_skip", str(err))


def _unary_z3_or_result(
    op: str,
    operand: _Z3Expr,
) -> Tuple[Optional[_Z3Expr], Optional[AlgorithmResult]]:
    """Apply a unary operator to an already translated Z3 operand.

    :param op: DSL unary operator.
    :type op: str
    :param operand: Z3 operand.
    :type operand: Union[z3.ArithRef, z3.BoolRef]
    :return: Translated Z3 expression and optional normalized failure.
    :rtype: Tuple[Optional[Union[z3.ArithRef, z3.BoolRef]], Optional[AlgorithmResult]]
    """
    try:
        if op == "-":
            return -operand, None
        if op == "+":
            return operand, None
        if op == "~":
            return ~operand, None
        if op in ("!", "not"):
            return z3.Not(operand), None
        return None, _skip_result(
            "undecidable_skip", f"Unsupported unary operator: {op}"
        )
    except TypeError as err:
        # TypeError: Python/Z3 operator overloads reject unsupported operand
        # combinations, for example bitwise NOT on arithmetic references.
        return None, _skip_result("undecidable_skip", str(err))
    except z3.Z3Exception as err:
        # Z3Exception: Z3 rejects sort/operator-domain mismatches.
        return None, _skip_result("undecidable_skip", str(err))


def _ufunc_z3_or_result(
    func: str,
    operand: _Z3Expr,
) -> Tuple[Optional[_Z3Expr], Optional[AlgorithmResult]]:
    """Apply a supported unary math function to a Z3 operand.

    :param func: Function name.
    :type func: str
    :param operand: Z3 operand.
    :type operand: Union[z3.ArithRef, z3.BoolRef]
    :return: Translated Z3 expression and optional normalized failure.
    :rtype: Tuple[Optional[Union[z3.ArithRef, z3.BoolRef]], Optional[AlgorithmResult]]
    """
    try:
        if func == "abs":
            return z3.If(operand >= 0, operand, -operand), None
        if func == "sign":
            zero = z3.IntVal(0) if z3.is_int(operand) else z3.RealVal(0)
            one = z3.IntVal(1) if z3.is_int(operand) else z3.RealVal(1)
            minus_one = z3.IntVal(-1) if z3.is_int(operand) else z3.RealVal(-1)
            return z3.If(
                operand == zero, zero, z3.If(operand > zero, one, minus_one)
            ), None
        if func == "floor":
            return (z3.ToInt(operand) if z3.is_real(operand) else operand), None
        if func == "ceil":
            return (-z3.ToInt(-operand) if z3.is_real(operand) else operand), None
        if func == "trunc":
            if z3.is_real(operand):
                zero = z3.RealVal(0)
                return z3.If(
                    operand >= zero, z3.ToInt(operand), -z3.ToInt(-operand)
                ), None
            return operand, None
        if func == "sqrt":
            if z3.is_real(operand):
                return z3.Sqrt(operand), None
            if z3.is_int(operand):
                return z3.Sqrt(z3.ToReal(operand)), None
            return None, _skip_result(
                "undecidable_skip",
                f"sqrt requires Real or Int operand, got {operand.sort()}.",
            )
        if func == "round":
            return python_round_to_z3(operand), None
        return None, _skip_result(
            "undecidable_skip",
            "Mathematical function {func!r} is not supported in Z3 conversion.".format(
                func=func
            ),
        )
    except TypeError as err:
        # TypeError: Python/Z3 operator overloads reject unsupported operand
        # combinations during function expansion.
        return None, _skip_result("undecidable_skip", str(err))
    except z3.Z3Exception as err:
        # Z3Exception: Z3 rejects sort/operator-domain mismatches.
        return None, _skip_result("undecidable_skip", str(err))


def _expr_conditions_and_z3_or_result(
    expr: Expr,
    z3_vars: _Z3Vars,
    path_conditions: Sequence[z3.ExprRef] = (),
    *,
    context_constraints: Optional[Sequence[z3.ExprRef]] = None,
    smt_timeout_ms: Optional[int] = None,
    domain_constraints: Optional[List[z3.ExprRef]] = None,
) -> Tuple[
    Optional[Tuple[_ConditionPoint, ...]],
    Optional[_Z3Expr],
    Optional[AlgorithmResult],
]:
    """Translate an expression while pruning unreachable ternary branches.

    Expression-level ternaries have runtime short-circuit semantics: only the
    selected value branch is evaluated.  When the caller supplies a symbolic
    context, this helper avoids translating value branches that are unreachable
    in that context, matching the path-sensitive handling used for operation
    ``if`` blocks.

    :param expr: Expression to translate.
    :type expr: Expr
    :param z3_vars: Symbolic environment at this expression point.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param path_conditions: Predicates needed to reach this expression.
    :type path_conditions: Sequence[z3.ExprRef]
    :param context_constraints: Optional surrounding execution context.
    :type context_constraints: Optional[Sequence[z3.ExprRef]], optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :param domain_constraints: Optional accumulator for runtime definedness
        constraints, such as non-zero divisors.  These constraints align Z3's
        total arithmetic operators with FCSTM runtime evaluation, where numeric
        domain errors abort the execution path instead of choosing an arbitrary
        model value.
    :type domain_constraints: Optional[List[z3.ExprRef]], optional
    :return: Condition points, translated expression, or normalized failure.
    :rtype: Tuple[Optional[Tuple[_ConditionPoint, ...]], Optional[Union[z3.ArithRef, z3.BoolRef]], Optional[AlgorithmResult]]
    """
    from pyfcstm.model.expr import BinaryOp, Boolean, Float, Integer, UFunc, UnaryOp

    if domain_constraints is None:
        domain_constraints = []

    if isinstance(expr, (Integer, Float, Boolean, _variable_type())):
        z3_expr, result = _expr_to_z3_or_result(expr, z3_vars)
        return (), z3_expr, result

    if isinstance(expr, _conditional_op_type()):
        points: List[_ConditionPoint] = []
        condition_domains: List[z3.ExprRef] = []
        cond_points, condition_z3, result = _expr_conditions_and_z3_or_result(
            expr.cond,
            z3_vars,
            path_conditions,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
            domain_constraints=condition_domains,
        )
        if result is not None:
            return None, None, result
        domain_constraints.extend(condition_domains)
        points.extend(cond_points or ())
        points.append(
            _ConditionPoint(
                expr.cond,
                dict(z3_vars),
                (*path_conditions, *condition_domains),
                z3_condition=condition_z3,
            )
        )

        true_path = (*path_conditions, *condition_domains, condition_z3)
        false_path = (*path_conditions, *condition_domains, z3.Not(condition_z3))
        true_reachable, result = _path_reachability_or_result(
            context_constraints,
            true_path,
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return None, None, result
        false_reachable, result = _path_reachability_or_result(
            context_constraints,
            false_path,
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return None, None, result

        true_expr = false_expr = None
        true_domains: List[z3.ExprRef] = []
        false_domains: List[z3.ExprRef] = []
        if true_reachable is not False:
            true_points, true_expr, result = _expr_conditions_and_z3_or_result(
                expr.if_true,
                z3_vars,
                true_path,
                context_constraints=context_constraints,
                smt_timeout_ms=smt_timeout_ms,
                domain_constraints=true_domains,
            )
            if result is not None:
                return None, None, result
            points.extend(true_points or ())
        if false_reachable is not False:
            false_points, false_expr, result = _expr_conditions_and_z3_or_result(
                expr.if_false,
                z3_vars,
                false_path,
                context_constraints=context_constraints,
                smt_timeout_ms=smt_timeout_ms,
                domain_constraints=false_domains,
            )
            if result is not None:
                return None, None, result
            points.extend(false_points or ())

        if true_reachable is False and false_reachable is False:
            return (
                None,
                None,
                _skip_result(
                    "undecidable_skip",
                    "Conditional expression has no reachable value branch.",
                ),
            )
        if true_reachable is False:
            domain_constraints.extend(false_domains)
            return tuple(points), false_expr, None
        if false_reachable is False:
            domain_constraints.extend(true_domains)
            return tuple(points), true_expr, None
        for item in true_domains:
            domain_constraints.append(z3.Implies(condition_z3, item))
        for item in false_domains:
            domain_constraints.append(z3.Implies(z3.Not(condition_z3), item))
        try:
            return tuple(points), z3.If(condition_z3, true_expr, false_expr), None
        except z3.Z3Exception as err:
            # Z3Exception: Z3 rejects If branches with incompatible sorts.
            return None, None, _skip_result("undecidable_skip", str(err))

    if isinstance(expr, BinaryOp):
        points: List[_ConditionPoint] = []
        left_points, left, result = _expr_conditions_and_z3_or_result(
            expr.x,
            z3_vars,
            path_conditions,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
            domain_constraints=domain_constraints,
        )
        if result is not None:
            return None, None, result
        points.extend(left_points or ())

        right_points, right, result = _expr_conditions_and_z3_or_result(
            expr.y,
            z3_vars,
            path_conditions,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
            domain_constraints=domain_constraints,
        )
        if result is not None:
            return None, None, result
        points.extend(right_points or ())
        if expr.op in ("/", "%"):
            try:
                domain_constraints.append(right != 0)
            except (TypeError, z3.Z3Exception) as err:
                # TypeError/Z3Exception: malformed arithmetic expressions can
                # produce a denominator that Z3 cannot compare against zero.
                return None, None, _skip_result("undecidable_skip", str(err))
        z3_expr, result = _binary_z3_or_result(expr.op, left, right)
        return tuple(points), z3_expr, result

    if isinstance(expr, UnaryOp):
        points, operand, result = _expr_conditions_and_z3_or_result(
            expr.x,
            z3_vars,
            path_conditions,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
            domain_constraints=domain_constraints,
        )
        if result is not None:
            return None, None, result
        z3_expr, result = _unary_z3_or_result(expr.op, operand)
        return points, z3_expr, result

    if isinstance(expr, UFunc):
        points, operand, result = _expr_conditions_and_z3_or_result(
            expr.x,
            z3_vars,
            path_conditions,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
            domain_constraints=domain_constraints,
        )
        if result is not None:
            return None, None, result
        if expr.func == "sqrt":
            try:
                domain_constraints.append(operand >= 0)
            except (TypeError, z3.Z3Exception) as err:
                # TypeError/Z3Exception: malformed operands can be rejected
                # before the Z3 sqrt expression is built.
                return None, None, _skip_result("undecidable_skip", str(err))
        z3_expr, result = _ufunc_z3_or_result(expr.func, operand)
        return points, z3_expr, result

    return (
        None,
        None,
        _skip_result(
            "undecidable_skip",
            f"Unsupported expression type: {type(expr).__name__}",
        ),
    )


def _expr_z3_and_domains_or_result(
    expr: Expr,
    z3_vars: _Z3Vars,
    path_conditions: Sequence[z3.ExprRef] = (),
    *,
    context_constraints: Optional[Sequence[z3.ExprRef]] = None,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[
    Optional[_Z3Expr],
    Optional[Tuple[z3.ExprRef, ...]],
    Optional[AlgorithmResult],
]:
    """Translate an expression and return runtime-definedness constraints.

    Z3 arithmetic is total for operators such as division and modulo, while the
    FCSTM runtime aborts expression evaluation on invalid numeric domains.  Raw
    guard and trigger algorithms therefore need both the translated expression
    and the side constraints that make evaluating it well-defined.

    :param expr: Expression to translate.
    :type expr: Expr
    :param z3_vars: Symbolic environment at this expression point.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param path_conditions: Predicates needed to reach this expression.
    :type path_conditions: Sequence[z3.ExprRef]
    :param context_constraints: Optional surrounding execution context.
    :type context_constraints: Optional[Sequence[z3.ExprRef]], optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Z3 expression, runtime-definedness constraints, or a normalized
        algorithm result.
    :rtype: Tuple[Optional[Union[z3.ArithRef, z3.BoolRef]], Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]]
    """
    domain_constraints: List[z3.ExprRef] = []
    _, z3_expr, result = _expr_conditions_and_z3_or_result(
        expr,
        z3_vars,
        path_conditions,
        context_constraints=context_constraints,
        smt_timeout_ms=smt_timeout_ms,
        domain_constraints=domain_constraints,
    )
    if result is not None:
        return None, None, result
    return z3_expr, tuple(domain_constraints), None


def _definedness_feasibility_or_result(
    constraints: Sequence[z3.ExprRef],
    *,
    reason: str,
    smt_timeout_ms: Optional[int] = None,
) -> Optional[AlgorithmResult]:
    """Return an indeterminate result when runtime-definedness is infeasible.

    :param constraints: Context plus definedness constraints to check.
    :type constraints: Sequence[z3.ExprRef]
    :param reason: Reason to use when the context is unsatisfiable.
    :type reason: str
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: ``None`` when feasible, otherwise an algorithm result.
    :rtype: Optional[AlgorithmResult]
    """
    sat_result = is_sat(constraints, timeout_ms=smt_timeout_ms)
    if sat_result.kind == "sat":
        return None
    if sat_result.kind == "unsat":
        return _skip_result("undecidable_skip", reason)
    return _skip_result(sat_result.kind, getattr(sat_result, "reason", None))


def _path_reachability_or_result(
    context_constraints: Optional[Sequence[z3.ExprRef]],
    path_conditions: Sequence[z3.ExprRef],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[Optional[bool], Optional[AlgorithmResult]]:
    """Check whether a symbolic operation path is reachable.

    ``context_constraints=None`` disables pruning for helper-level callers that
    only want syntax-local prefix collection.  Raw verification algorithms pass
    their already-built first-cycle context so unreachable branches can be
    skipped before translating branch bodies.

    :param context_constraints: Outer constraints for the analyzed execution
        context, or ``None`` to disable pruning.
    :type context_constraints: Optional[Sequence[z3.ExprRef]]
    :param path_conditions: Branch predicates needed to reach the path.
    :type path_conditions: Sequence[z3.ExprRef]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Reachability flag, or an indeterminate algorithm result.
    :rtype: Tuple[Optional[bool], Optional[AlgorithmResult]]
    """
    if context_constraints is None:
        return True, None

    sat_result = is_sat(
        [*context_constraints, *path_conditions],
        timeout_ms=smt_timeout_ms,
    )
    if sat_result.kind == "sat":
        return True, None
    if sat_result.kind == "unsat":
        return False, None
    return None, _skip_result(sat_result.kind, getattr(sat_result, "reason", None))


def _append_expr_domain_constraints(
    source_constraints: Sequence[z3.ExprRef],
    target_constraints: List[z3.ExprRef],
) -> None:
    """Append expression-definedness constraints visible in ``z3_vars``.

    :param source_constraints: Candidate constraints collected while
        translating the expression assigned to one name.
    :type source_constraints: Sequence[z3.ExprRef]
    :param target_constraints: Mutable block-level domain constraint list.
    :type target_constraints: List[z3.ExprRef]
    :return: ``None``.
    :rtype: None
    """
    if source_constraints:
        target_constraints.extend(source_constraints)


def _execute_operation_prefix_conditions_and_vars_or_result(
    operations: Sequence[OperationStatement],
    z3_vars: _Z3Vars,
    path_conditions: Sequence[z3.ExprRef] = (),
    *,
    context_constraints: Optional[Sequence[z3.ExprRef]] = None,
    smt_timeout_ms: Optional[int] = None,
    domain_constraints: Optional[Sequence[z3.ExprRef]] = None,
) -> Tuple[
    Optional[Tuple[_ConditionPoint, ...]],
    Optional[_Z3Vars],
    Optional[Tuple[z3.ExprRef, ...]],
    Optional[AlgorithmResult],
]:
    """Collect prefix conditions and execute operations path-sensitively.

    When ``context_constraints`` are supplied, branch bodies whose path is
    unsatisfiable in that context are not translated.  This preserves later
    reachable diagnostics instead of letting dead branch expressions force the
    entire algorithm into ``undecidable_skip``.

    :param operations: Operation statements to scan in execution order.
    :type operations: Sequence[OperationStatement]
    :param z3_vars: Starting symbolic environment before the operation block.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param path_conditions: Predicates that must hold before this block is run.
    :type path_conditions: Sequence[z3.ExprRef]
    :param context_constraints: Optional outer constraints used to prune
        unreachable branch paths.
    :type context_constraints: Optional[Sequence[z3.ExprRef]], optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :param domain_constraints: Runtime definedness constraints already known
        before this operation block.
    :type domain_constraints: Optional[Sequence[z3.ExprRef]], optional
    :return: Condition points, post-state variables, accumulated domain
        constraints, or an algorithm result when symbolic prefix execution
        cannot be expressed.
    :rtype: Tuple[Optional[Tuple[_ConditionPoint, ...]], Optional[Dict[str, Union[z3.ArithRef, z3.BoolRef]]], Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]]
    """
    points: List[_ConditionPoint] = []
    current_vars = dict(z3_vars)
    current_path = tuple(path_conditions)
    current_domains: List[z3.ExprRef] = list(domain_constraints or ())

    for statement in operations:
        if isinstance(statement, _operation_type()):
            expression_path = (*current_path, *current_domains)
            expression_domains: List[z3.ExprRef] = []
            expression_points, expression_value, result = (
                _expr_conditions_and_z3_or_result(
                    statement.expr,
                    current_vars,
                    expression_path,
                    context_constraints=context_constraints,
                    smt_timeout_ms=smt_timeout_ms,
                    domain_constraints=expression_domains,
                )
            )
            if result is not None:
                return None, None, None, result
            if context_constraints is not None and expression_domains:
                result = _definedness_feasibility_or_result(
                    [
                        *context_constraints,
                        *expression_path,
                        *expression_domains,
                    ],
                    reason=(
                        "Operation expression runtime definedness constraints "
                        "are unsatisfiable in context."
                    ),
                    smt_timeout_ms=smt_timeout_ms,
                )
                if result is not None:
                    return None, None, None, result
            points.extend(expression_points or ())
            current_vars[statement.var_name] = expression_value
            _append_expr_domain_constraints(
                expression_domains,
                current_domains,
            )
            continue

        if isinstance(statement, _if_block_type()):
            prior_not_taken: List[z3.ExprRef] = []
            branch_results = []
            visible_names = tuple(current_vars.keys())
            for branch in statement.branches:
                evaluation_path = [*current_path, *current_domains, *prior_not_taken]
                evaluation_reachable, result = _path_reachability_or_result(
                    context_constraints,
                    evaluation_path,
                    smt_timeout_ms=smt_timeout_ms,
                )
                if result is not None:
                    return None, None, None, result
                if evaluation_reachable is False:
                    break

                branch_condition = None
                branch_path = list(evaluation_path)
                evaluation_selector = (
                    z3.And(*prior_not_taken) if prior_not_taken else None
                )
                branch_selector = evaluation_selector
                if branch.condition is not None:
                    branch_condition_domains: List[z3.ExprRef] = []
                    condition_points, branch_condition, result = (
                        _expr_conditions_and_z3_or_result(
                            branch.condition,
                            current_vars,
                            evaluation_path,
                            context_constraints=context_constraints,
                            smt_timeout_ms=smt_timeout_ms,
                            domain_constraints=branch_condition_domains,
                        )
                    )
                    if result is not None:
                        return None, None, None, result
                    if context_constraints is not None and branch_condition_domains:
                        result = _definedness_feasibility_or_result(
                            [
                                *context_constraints,
                                *evaluation_path,
                                *branch_condition_domains,
                            ],
                            reason=(
                                "Branch condition runtime definedness "
                                "constraints are unsatisfiable in context."
                            ),
                            smt_timeout_ms=smt_timeout_ms,
                        )
                        if result is not None:
                            return None, None, None, result
                    points.extend(condition_points or ())
                    for item in branch_condition_domains:
                        if evaluation_selector is None:
                            current_domains.append(item)
                        else:
                            current_domains.append(
                                z3.Implies(evaluation_selector, item)
                            )
                    points.append(
                        _ConditionPoint(
                            branch.condition,
                            dict(current_vars),
                            (*evaluation_path, *branch_condition_domains),
                            "branch",
                            branch_condition,
                        )
                    )
                    branch_path.extend(branch_condition_domains)
                    branch_path.append(branch_condition)
                    branch_selector = (
                        z3.And(*prior_not_taken, branch_condition)
                        if prior_not_taken
                        else branch_condition
                    )
                    prior_not_taken.extend(branch_condition_domains)
                    prior_not_taken.append(z3.Not(branch_condition))

                branch_reachable, result = _path_reachability_or_result(
                    context_constraints,
                    branch_path,
                    smt_timeout_ms=smt_timeout_ms,
                )
                if result is not None:
                    return None, None, None, result
                if branch_reachable is False:
                    continue

                branch_domains: List[z3.ExprRef] = []
                branch_points, branch_vars, branch_domains, result = (
                    _execute_operation_prefix_conditions_and_vars_or_result(
                        branch.statements,
                        current_vars,
                        branch_path,
                        context_constraints=context_constraints,
                        smt_timeout_ms=smt_timeout_ms,
                        domain_constraints=branch_domains,
                    )
                )
                if result is not None:
                    return None, None, None, result
                points.extend(branch_points or ())
                branch_results.append(
                    (
                        branch_condition,
                        branch_selector,
                        branch_vars or current_vars,
                        tuple(branch_domains or ()),
                    )
                )

                if branch.condition is None:
                    break

            merged_vars = dict(current_vars)
            for name in visible_names:
                merged_value = current_vars[name]
                for branch_condition, _, branch_vars, _ in reversed(branch_results):
                    if branch_condition is None:
                        merged_value = branch_vars[name]
                    else:
                        merged_value = z3.If(
                            branch_condition,
                            branch_vars[name],
                            merged_value,
                        )
                merged_vars[name] = merged_value
            for _, branch_selector, _, branch_domains in branch_results:
                for item in branch_domains:
                    if branch_selector is None:
                        current_domains.append(item)
                    else:
                        current_domains.append(z3.Implies(branch_selector, item))
            current_vars = merged_vars
            continue

        return (
            None,
            None,
            None,
            _skip_result(
                "undecidable_skip",
                f"Unknown operation statement type {type(statement)!r}.",
            ),
        )

    return tuple(points), current_vars, tuple(current_domains), None


def _execute_operation_prefix_conditions_or_result(
    operations: Sequence[OperationStatement],
    z3_vars: _Z3Vars,
    path_conditions: Sequence[z3.ExprRef] = (),
    *,
    context_constraints: Optional[Sequence[z3.ExprRef]] = None,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[Optional[Tuple[_ConditionPoint, ...]], Optional[AlgorithmResult]]:
    """Collect condition expressions with point-in-time path predicates.

    The collected path predicates model the branch-selection predicates needed
    to reach the condition point.  They let callers skip diagnostics for
    syntactic conditions inside branches that are unreachable in the surrounding
    first-cycle context.

    :param operations: Operation statements to scan in execution order.
    :type operations: Sequence[OperationStatement]
    :param z3_vars: Starting symbolic environment before the operation block.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param path_conditions: Predicates that must hold before this block is run.
    :type path_conditions: Sequence[z3.ExprRef]
    :param context_constraints: Optional outer constraints used to prune
        unreachable branch paths.
    :type context_constraints: Optional[Sequence[z3.ExprRef]], optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Condition points, or an algorithm result when symbolic prefix
        execution cannot be expressed.
    :rtype: Tuple[Optional[Tuple[_ConditionPoint, ...]], Optional[AlgorithmResult]]
    """
    points, _, _, result = _execute_operation_prefix_conditions_and_vars_or_result(
        operations,
        z3_vars,
        path_conditions,
        context_constraints=context_constraints,
        smt_timeout_ms=smt_timeout_ms,
    )
    return points, result


def _transition_trigger_or_result(
    transition: Transition,
    z3_vars: _Z3Vars,
    event_vars: Optional[Dict[str, z3.BoolRef]] = None,
    *,
    context_constraints: Optional[Sequence[z3.ExprRef]] = None,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[
    Optional[z3.ExprRef],
    Optional[Tuple[z3.ExprRef, ...]],
    Optional[AlgorithmResult],
]:
    """Build a transition trigger expression in the supplied environment.

    :param transition: Transition whose event and guard should be encoded.
    :type transition: Transition
    :param z3_vars: Symbolic variable environment at the trigger point.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param event_vars: Optional shared event boolean variable mapping.
    :type event_vars: Optional[Dict[str, z3.BoolRef]], optional
    :param context_constraints: Optional context used to prune guard ternary
        branches while translating.
    :type context_constraints: Optional[Sequence[z3.ExprRef]], optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Trigger expression, runtime-definedness constraints, and optional
        failure result.
    :rtype: Tuple[Optional[z3.ExprRef], Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]]
    """
    parts: List[z3.ExprRef] = []
    domain_constraints: List[z3.ExprRef] = []
    event_expr = None
    if transition.event is not None:
        event_key = _event_bool_name(transition)
        if event_vars is None:
            event_expr = z3.Bool(event_key)
        else:
            event_expr = event_vars.setdefault(event_key, z3.Bool(event_key))
        parts.append(event_expr)

    if transition.guard is not None:
        guard_expr, guard_domains, result = _expr_z3_and_domains_or_result(
            transition.guard,
            z3_vars,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return None, None, result
        domain_constraints.extend(guard_domains or ())
        parts.extend(guard_domains or ())
        parts.append(guard_expr)

    if event_expr is not None:
        trigger_domains = tuple(
            z3.Implies(event_expr, item) for item in domain_constraints
        )
    else:
        trigger_domains = tuple(domain_constraints)

    if not parts:
        return z3.BoolVal(True), trigger_domains, None
    if len(parts) == 1:
        return parts[0], trigger_domains, None
    return z3.And(*parts), trigger_domains, None


def _root_initial_path_context(
    state: State,
    variables: Sequence[VarDefine],
    z3_vars: _Z3Vars,
    base_constraints: Sequence[z3.ExprRef],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[
    Optional[Tuple[Transition, ...]],
    Optional[Tuple[z3.ExprRef, ...]],
    Optional[List[OperationStatement]],
    Optional[AlgorithmResult],
]:
    """Build the runtime first-enabled initial path context for a leaf.

    :param state: Candidate root-initial leaf state.
    :type state: State
    :param variables: FCSTM variable definitions.
    :type variables: Sequence[VarDefine]
    :param z3_vars: Root symbolic variables.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param base_constraints: Constraints that hold before root entry, usually
        DSL declaration initializers.
    :type base_constraints: Sequence[z3.ExprRef]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Initial transitions, path constraints, entry operation stream, and
        optional algorithm result.  A ``None`` transition tuple without a result
        means the state is not selected by the root first-enabled initial path.
    :rtype: Tuple[Optional[Tuple[Transition, ...]], Optional[Tuple[z3.ExprRef, ...]], Optional[List[OperationStatement]], Optional[AlgorithmResult]]
    """
    path = _state_path_from_root(state)
    if len(path) <= 1:
        return (), (), _action_operations(state.on_enters), None

    selected: List[Transition] = []
    constraints: List[z3.ExprRef] = []
    domain_constraints: List[z3.ExprRef] = []
    operations: List[OperationStatement] = []
    current_vars: _Z3Vars = dict(z3_vars)
    type_constraints = _build_type_constraints(variables, z3_vars)

    for index, path_state in enumerate(path[:-1]):
        child = path[index + 1]
        enter_ops = _action_operations(path_state.on_enters)
        operations.extend(enter_ops)
        _, current_vars, new_domains, result = (
            _execute_operation_prefix_conditions_and_vars_or_result(
                enter_ops,
                current_vars,
                context_constraints=[
                    *base_constraints,
                    *constraints,
                    *domain_constraints,
                    *type_constraints,
                ],
                smt_timeout_ms=smt_timeout_ms,
                domain_constraints=domain_constraints,
            )
        )
        if result is not None:
            return None, None, None, result
        domain_constraints = list(new_domains or ())

        if not path_state.is_leaf_state:
            during_before_ops = _action_operations(
                path_state.list_on_durings(aspect="before")
            )
            operations.extend(during_before_ops)
            _, current_vars, new_domains, result = (
                _execute_operation_prefix_conditions_and_vars_or_result(
                    during_before_ops,
                    current_vars,
                    context_constraints=[
                        *base_constraints,
                        *constraints,
                        *domain_constraints,
                        *type_constraints,
                    ],
                    smt_timeout_ms=smt_timeout_ms,
                    domain_constraints=domain_constraints,
                )
            )
            if result is not None:
                return None, None, None, result
            domain_constraints = list(new_domains or ())

        target_transition = None
        selected_constraints = None
        selected_guard_domains = None
        prior_triggers: List[z3.ExprRef] = []
        prior_guard_domains: List[z3.ExprRef] = []
        for transition in path_state.init_transitions:
            trigger, guard_domains, result = _transition_trigger_or_result(
                transition,
                current_vars,
                context_constraints=[
                    *base_constraints,
                    *constraints,
                    *domain_constraints,
                    *prior_guard_domains,
                    *type_constraints,
                ],
                smt_timeout_ms=smt_timeout_ms,
            )
            if result is not None:
                return None, None, None, result
            if guard_domains:
                result = _definedness_feasibility_or_result(
                    [
                        *base_constraints,
                        *constraints,
                        *domain_constraints,
                        *prior_guard_domains,
                        *guard_domains,
                        *type_constraints,
                    ],
                    reason=(
                        "Initial transition guard runtime definedness "
                        "constraints are unsatisfiable in context."
                    ),
                    smt_timeout_ms=smt_timeout_ms,
                )
                if result is not None:
                    return None, None, None, result
            if transition.to_state == child.name:
                candidate_constraints = [
                    *constraints,
                    *prior_guard_domains,
                    *(z3.Not(prior_trigger) for prior_trigger in prior_triggers),
                    *(guard_domains or ()),
                    trigger,
                ]
                context_check = is_sat(
                    [
                        *base_constraints,
                        *candidate_constraints,
                        *domain_constraints,
                        *type_constraints,
                    ],
                    timeout_ms=smt_timeout_ms,
                )
                if context_check.kind in {"unknown", "timeout"}:
                    return (
                        None,
                        None,
                        None,
                        _skip_result(
                            context_check.kind,
                            getattr(context_check, "reason", None),
                        ),
                    )
                if context_check.kind == "sat":
                    target_transition = transition
                    selected_constraints = candidate_constraints
                    selected_guard_domains = guard_domains
                    break
            prior_guard_domains.extend(guard_domains or ())
            prior_triggers.append(trigger)

        if (
            target_transition is None
            or selected_constraints is None
            or selected_guard_domains is None
        ):
            return None, None, None, None
        constraints = selected_constraints

        selected.append(target_transition)
        operations.extend(target_transition.effects)
        _, current_vars, new_domains, result = (
            _execute_operation_prefix_conditions_and_vars_or_result(
                target_transition.effects,
                current_vars,
                context_constraints=[
                    *base_constraints,
                    *constraints,
                    *domain_constraints,
                    *type_constraints,
                ],
                smt_timeout_ms=smt_timeout_ms,
                domain_constraints=domain_constraints,
            )
        )
        if result is not None:
            return None, None, None, result
        domain_constraints = list(new_domains or ())

    leaf_enter_ops = _action_operations(state.on_enters)
    operations.extend(leaf_enter_ops)

    return tuple(selected), tuple(constraints), operations, None


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
    *,
    context_constraints: Optional[Sequence[z3.ExprRef]] = None,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[
    Optional[_Z3Expr],
    Optional[_Z3Vars],
    Optional[Tuple[z3.ExprRef, ...]],
    Optional[AlgorithmResult],
]:
    """Translate a transition guard.

    :param transition: Transition with a non-``None`` guard.
    :type transition: Transition
    :param variables: FCSTM variable definitions.
    :type variables: Sequence[VarDefine]
    :param context_constraints: Optional context used to prune guard ternary
        branches while translating.
    :type context_constraints: Optional[Sequence[z3.ExprRef]], optional
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Guard Z3 expression, variable mapping, runtime-definedness
        constraints, and optional failure result.
    :rtype: tuple
    """
    z3_vars = _z3_vars(variables)
    if context_constraints is None:
        context_constraints = _build_type_constraints(variables, z3_vars)
    guard_expr, guard_domains, result = _expr_z3_and_domains_or_result(
        transition.guard,
        z3_vars,
        context_constraints=context_constraints,
        smt_timeout_ms=smt_timeout_ms,
    )
    if result is not None:
        return None, None, None, result
    return guard_expr, z3_vars, guard_domains, None


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
    if candidate_kind in {"unknown", "timeout", "undecidable_skip"}:
        return _skip_result(candidate_kind, reason)
    return None


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
    if not transition.is_forced or transition.guard is None:
        return AlgorithmResult(kind="sat")

    z3_vars = _z3_vars(variables)
    init_constraints, result = _build_init_constraints_or_result(variables, z3_vars)
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


def _effect_guard_context_or_result(
    transition: Transition,
    variables: Sequence[VarDefine],
    z3_vars: _Z3Vars,
    *,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[
    Optional[_Z3Expr], Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]
]:
    """Build a feasible guard context for transition-effect algorithms.

    :param transition: Transition whose effect context is analyzed.
    :type transition: Transition
    :param variables: Variable definitions available to the model.
    :type variables: Sequence[VarDefine]
    :param z3_vars: Initial Z3 variable environment.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Guard expression, type constraints, or an algorithm result.
    :rtype: Tuple[Optional[Union[z3.ArithRef, z3.BoolRef]], Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]]
    """
    if transition.guard is None:
        guard_z3 = z3.BoolVal(True)
        guard_domains: Tuple[z3.ExprRef, ...] = ()
    else:
        guard_z3, guard_domains, result = _expr_z3_and_domains_or_result(
            transition.guard,
            z3_vars,
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return None, None, result

    type_constraints = _build_type_constraints(variables, z3_vars)
    guard_feasible = is_sat(
        [guard_z3, *type_constraints, *(guard_domains or ())],
        timeout_ms=smt_timeout_ms,
    )
    if guard_feasible.kind == "unsat":
        if guard_domains:
            return (
                None,
                None,
                _skip_result(
                    "undecidable_skip",
                    (
                        "Transition guard runtime definedness constraints are "
                        "unsatisfiable."
                    ),
                ),
            )
        return None, None, AlgorithmResult(kind="sat")
    if guard_feasible.kind != "sat":
        return None, None, AlgorithmResult(kind=guard_feasible.kind)
    return guard_z3, (*type_constraints, *(guard_domains or ())), None


def _execute_effects_under_guard_or_result(
    transition: Transition,
    z3_vars: _Z3Vars,
    guard_z3: _Z3Expr,
    type_constraints: Sequence[z3.ExprRef],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> Tuple[
    Optional[_Z3Vars], Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]
]:
    """Execute transition effects with guard-pruned ternary semantics.

    Transition effects run only when the transition trigger is enabled.  This
    helper passes that guard context into the raw path-sensitive operation
    executor so expression-level ternary value branches that the guard makes
    unreachable are not translated.

    :param transition: Transition whose effects should be executed.
    :type transition: Transition
    :param z3_vars: Initial Z3 variable environment.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param guard_z3: Z3 guard expression for the transition.
    :type guard_z3: Union[z3.ArithRef, z3.BoolRef]
    :param type_constraints: Type/domain constraints for model variables.
    :type type_constraints: Sequence[z3.ExprRef]
    :param smt_timeout_ms: Optional solver timeout in milliseconds.
    :type smt_timeout_ms: Optional[int], optional
    :return: Post-effect variables, runtime definedness constraints, or an
        algorithm result when execution cannot be expressed.
    :rtype: Tuple[Optional[Dict[str, Union[z3.ArithRef, z3.BoolRef]]], Optional[Tuple[z3.ExprRef, ...]], Optional[AlgorithmResult]]
    """
    _, after_vars, effect_domain_constraints, result = (
        _execute_operation_prefix_conditions_and_vars_or_result(
            transition.effects,
            z3_vars,
            context_constraints=[guard_z3, *type_constraints],
            smt_timeout_ms=smt_timeout_ms,
        )
    )
    if result is not None:
        return None, None, result

    defined_effect_context = [
        guard_z3,
        *type_constraints,
        *(effect_domain_constraints or ()),
    ]
    defined_effect_feasible = is_sat(
        defined_effect_context,
        timeout_ms=smt_timeout_ms,
    )
    if defined_effect_feasible.kind == "unsat":
        result = _skip_result(
            "undecidable_skip",
            "Transition effect runtime definedness constraints are unsatisfiable under guard.",
        )
        return None, None, result
    if defined_effect_feasible.kind != "sat":
        return None, None, AlgorithmResult(kind=defined_effect_feasible.kind)
    return after_vars, tuple(effect_domain_constraints or ()), None


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
    runtime-defined and true.  If post-state guard definedness is itself
    infeasible under the pre-guard/effect context, the raw algorithm returns
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
        result = _definedness_feasibility_or_result(
            [
                guard_before,
                *(type_constraints or ()),
                *(effect_domain_constraints or ()),
                *guard_after_domains,
            ],
            reason=(
                "Post-effect transition guard runtime definedness "
                "constraints are unsatisfiable."
            ),
            smt_timeout_ms=smt_timeout_ms,
        )
        if result is not None:
            return result

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
    smt_timeout_ms: Optional[int] = None,
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
        z3_vars = _z3_vars(variables)
        event_vars: Dict[str, z3.BoolRef] = {}
        prior_triggers: List[z3.ExprRef] = []
        prior_domain_constraints: List[z3.ExprRef] = []
        prior_payloads: List[dict] = []
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

    if diagnostics:
        return AlgorithmResult(kind="unsat", diagnostics=tuple(diagnostics))
    if first_indeterminate_result is not None:
        return first_indeterminate_result
    return AlgorithmResult(kind="sat")


def _action_operations(
    actions: Sequence[Union[OnStage, OnAspect]],
) -> List[OperationStatement]:
    """Collect concrete operation statements from lifecycle actions.

    Abstract actions cannot be symbolically executed in this raw solver layer,
    so they are treated as identity and omitted from the collected operation
    stream.

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


def _concrete_during_operations(state: State) -> List[OperationStatement]:
    """Collect the complete concrete first-cycle during chain in run order.

    This mirrors :meth:`pyfcstm.model.State.iter_on_during_aspect_recursively`,
    including ancestor ``>> during before`` actions, leaf ``during`` actions,
    and ancestor ``>> during after`` actions.  Abstract actions are omitted
    because raw SMT-local verification has no implementation body for them.

    :param state: Leaf state whose first-cycle during chain is inspected.
    :type state: State
    :return: Flattened concrete operation statements.
    :rtype: List[OperationStatement]
    """
    return _action_operations(
        [action for _, action in state.iter_on_during_aspect_recursively()]
    )


def _state_path_from_root(state: State) -> Tuple[State, ...]:
    """Return the state path from the root to ``state``.

    :param state: State whose ancestry should be collected.
    :type state: State
    :return: Root-to-state path.
    :rtype: Tuple[State, ...]
    """
    path = []
    current = state
    while current is not None:
        path.append(current)
        current = current.parent
    return tuple(reversed(path))


def _root_initial_path_transitions(state: State) -> Optional[Tuple[Transition, ...]]:
    """Return the root-to-leaf initial-transition chain for ``state``.

    ``enter_postcondition_implies_during_precondition`` reasons about first
    cycle entry from the global root.  This helper returns the concrete
    declaration-order transition chain that reaches ``state`` when every
    ancestor follows an initial transition.  A missing initial edge means the
    leaf is not a root-initial leaf and should be ignored by this algorithm.

    :param state: Leaf state to inspect.
    :type state: State
    :return: Initial transition chain, or ``None`` when no such chain exists.
    :rtype: Optional[Tuple[Transition, ...]]
    """
    path = _state_path_from_root(state)
    transitions: List[Transition] = []
    for parent, child in zip(path, path[1:]):
        transition = next(
            (item for item in parent.init_transitions if item.to_state == child.name),
            None,
        )
        if transition is None:
            return None
        transitions.append(transition)
    return tuple(transitions)


def _is_root_initial_leaf(state: State) -> bool:
    """Return whether a leaf is reachable through initial transitions.

    :param state: Leaf state to inspect.
    :type state: State
    :return: Whether the root-to-leaf path is initial-transition-only.
    :rtype: bool
    """
    return _root_initial_path_transitions(state) is not None


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
    if not state.is_leaf_state or state.is_pseudo:
        return AlgorithmResult(kind="sat")

    z3_vars = _z3_vars(variables)
    init_constraints, result = _build_init_constraints_or_result(variables, z3_vars)
    if result is not None:
        return result

    init_transitions, entry_constraints, entry_operations, result = (
        _root_initial_path_context(
            state,
            variables,
            z3_vars,
            init_constraints,
            smt_timeout_ms=smt_timeout_ms,
        )
    )
    if result is not None:
        return result
    if init_transitions is None:
        return AlgorithmResult(kind="sat")

    first_cycle_operations = _concrete_during_operations(state)
    if not first_cycle_operations:
        return AlgorithmResult(kind="sat")

    type_constraints = _build_type_constraints(variables, z3_vars)
    context_constraints = [
        *init_constraints,
        *(entry_constraints or ()),
        *type_constraints,
    ]
    _, entry_vars, entry_domain_constraints, result = (
        _execute_operation_prefix_conditions_and_vars_or_result(
            entry_operations or (),
            z3_vars,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
        )
    )
    if result is not None:
        return result
    context_constraints.extend(entry_domain_constraints or ())

    condition_points, _, _, result = (
        _execute_operation_prefix_conditions_and_vars_or_result(
            first_cycle_operations,
            entry_vars,
            context_constraints=context_constraints,
            smt_timeout_ms=smt_timeout_ms,
        )
    )
    if result is not None:
        return result
    if not condition_points:
        return AlgorithmResult(kind="sat")

    diagnostics: List[dict] = []
    first_indeterminate_result: Optional[AlgorithmResult] = None

    context_check = is_sat(
        context_constraints,
        timeout_ms=smt_timeout_ms,
    )
    if context_check.kind in {"unknown", "timeout"}:
        first_indeterminate_result = _first_indeterminate(
            first_indeterminate_result,
            context_check.kind,
            getattr(context_check, "reason", None),
        )
    if context_check.kind == "unsat":
        return AlgorithmResult(kind="sat")

    for condition_point in condition_points:
        condition = condition_point.condition
        condition_z3 = condition_point.z3_condition
        if condition_z3 is None:
            condition_z3, result = _expr_to_z3_or_result(
                condition,
                condition_point.z3_vars,
            )
            if result is not None:
                first_indeterminate_result = _first_indeterminate(
                    first_indeterminate_result,
                    result.kind,
                    result.reason,
                )
                continue

        point_context = [
            *init_constraints,
            *(entry_constraints or ()),
            *condition_point.path_conditions,
            *type_constraints,
        ]
        reachability_check = is_sat(
            point_context,
            timeout_ms=smt_timeout_ms,
        )
        if reachability_check.kind == "unsat":
            continue
        if reachability_check.kind in {"unknown", "timeout"}:
            first_indeterminate_result = _first_indeterminate(
                first_indeterminate_result,
                reachability_check.kind,
                getattr(reachability_check, "reason", None),
            )
            continue

        true_check = is_sat(
            [condition_z3, *point_context],
            timeout_ms=smt_timeout_ms,
        )
        false_check = is_sat(
            [z3.Not(condition_z3), *point_context],
            timeout_ms=smt_timeout_ms,
        )

        if true_check.kind == "unsat":
            diagnostics.append(
                _make_diag(
                    "I_ENTER_DURING_CONTRADICT",
                    "enter_postcondition_implies_during_precondition",
                    state=_state_path(state),
                    condition=str(condition),
                    condition_source=condition_point.source,
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
                    condition_source=condition_point.source,
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
    """Return an injective internal event boolean variable name.

    FCSTM identifiers may contain underscores, so replacing ``.`` with ``__``
    is not injective: ``S.A__B`` and ``S.A.B`` would collide.  Length-prefix
    each path component instead so separate events always get separate Z3
    symbols while diagnostics continue to expose the original event path.

    :param transition: Event transition.
    :type transition: Transition
    :return: Event boolean name.
    :rtype: str
    """
    if transition.event is None:
        return "__event__anonymous"
    return "__event__" + "".join(
        f"{len(part)}:{part}" for part in transition.event.path
    )


def composite_init_guards_incomplete(
    machine: StateMachine,
    variables: Sequence[VarDefine],
    *,
    smt_timeout_ms: Optional[int] = None,
) -> AlgorithmResult:
    """Detect composite states whose initial transitions do not cover inputs.

    The result ``kind`` follows the witness query: ``'sat'`` means a coverage
    gap was found and diagnostics were emitted, while ``'unsat'`` means the
    initial-transition triggers cover all modeled inputs.

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

        z3_vars = _z3_vars(variables)
        event_vars: Dict[str, z3.BoolRef] = {}
        triggers: List[z3.ExprRef] = []
        per_composite_failed = False
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
