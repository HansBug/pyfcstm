"""Constant-folding diagnostics for literal-only expressions.

Numeric diagnostic refs are limited to JSON-stable values so Python and
jsfcstm agree on values that cross the JSON boundary.
"""

import math
from typing import TYPE_CHECKING, Any, List, Optional

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ...model.expr import Expr
    from ...model.model import OperationStatement, StateMachine


ConstValue = Any

_MAX_JSON_STABLE_INT = 9007199254740991
_MAX_FOLD_SHIFT_BITS = 1024
_COMPARISON_OPS = {'<', '<=', '>', '>=', '==', '!='}


def fold_numeric_expression(expr: 'Expr') -> Optional[ConstValue]:
    """Fold one numeric expression when it contains only supported constants."""
    from ...model.expr import BinaryOp, ConditionalOp, Float, Integer, UnaryOp

    if isinstance(expr, Integer):
        return expr.value
    if isinstance(expr, Float):
        return expr.value
    if isinstance(expr, UnaryOp):
        value = fold_numeric_expression(expr.x)
        if value is None:
            return None
        if expr.op == '+':
            return +value
        if expr.op == '-':
            return -value
        return None
    if isinstance(expr, BinaryOp):
        left = fold_numeric_expression(expr.x)
        right = fold_numeric_expression(expr.y)
        if left is None or right is None:
            return None
        return _fold_numeric_binary(expr.op, left, right)
    if isinstance(expr, ConditionalOp):
        condition = fold_condition_expression(expr.cond)
        if condition is None:
            return None
        return fold_numeric_expression(expr.if_true if condition else expr.if_false)
    return None


def fold_condition_expression(expr: 'Expr') -> Optional[bool]:
    """Fold one condition expression when it contains only supported constants."""
    from ...model.expr import BinaryOp, Boolean, ConditionalOp, UnaryOp

    if isinstance(expr, Boolean):
        return expr.value
    if isinstance(expr, UnaryOp):
        if expr.op != '!':
            return None
        value = fold_condition_expression(expr.x)
        return None if value is None else not value
    if isinstance(expr, BinaryOp):
        if expr.op in {'&&', '||'}:
            left = fold_condition_expression(expr.x)
            right = fold_condition_expression(expr.y)
            if left is None or right is None:
                return None
            return left and right if expr.op == '&&' else left or right
        if expr.op in _COMPARISON_OPS:
            return _fold_comparison(expr)
        return None
    if isinstance(expr, ConditionalOp):
        condition = fold_condition_expression(expr.cond)
        if condition is None:
            return None
        return fold_condition_expression(expr.if_true if condition else expr.if_false)
    return None


def collect_const_fold_warnings(
    machine: Optional['StateMachine'],
) -> List[ModelDiagnostic]:
    """Collect diagnostics that depend on constant folding."""
    if machine is None:
        return []
    diagnostics: List[ModelDiagnostic] = []
    for state in machine.walk_states():
        state_path = _state_path(state)
        for transition in state.transitions:
            folded_guard = (
                None if transition.guard is None
                else fold_condition_expression(transition.guard)
            )
            if folded_guard is True:
                diagnostics.append(_guard_const_diagnostic(transition, True))
            elif folded_guard is False:
                diagnostics.append(_guard_const_diagnostic(transition, False))
        diagnostics.extend(_during_const_assign_diagnostics(state_path, state))
    return diagnostics


def _fold_numeric_binary(
    op: str,
    left: ConstValue,
    right: ConstValue,
) -> Optional[ConstValue]:
    if op in {'<<', '>>', '&', '^', '|'}:
        if not (_is_plain_int(left) and _is_plain_int(right)):
            return None
        if op in {'<<', '>>'} and right < 0:
            return None
        if op in {'<<', '>>'} and right > _MAX_FOLD_SHIFT_BITS:
            return None
        if op == '<<':
            return left << right
        if op == '>>':
            return left >> right
        if op == '&':
            return left & right
        if op == '^':
            return left ^ right
        return left | right

    if op in {'+', '-', '*', '/', '**'} and _has_unsafe_integer_operand(left, right):
        return None

    if op == '+':
        return _stable_numeric_result(left + right)
    if op == '-':
        return _stable_numeric_result(left - right)
    if op == '*':
        return _stable_numeric_result(left * right)
    if op == '/':
        if right == 0:
            return None
        return _stable_numeric_result(left / right)
    if op == '%':
        if right == 0:
            return None
        if not (_is_plain_int(left) and _is_plain_int(right)) and _has_unsafe_integer_operand(left, right):
            return None
        return _stable_numeric_result(left % right)
    if op == '**':
        if left == 0 and right < 0:
            return None
        if (
            _is_plain_int(left)
            and _is_plain_int(right)
            and right >= 0
            and _integer_power_exceeds_json_stable_range(left, right)
        ):
            return None
        try:
            result = left ** right
        except (OverflowError, ValueError, ZeroDivisionError):
            # OverflowError: huge float exponent; ValueError: complex result
            # from fractional powers; ZeroDivisionError: 0 ** negative.
            return None
        if isinstance(result, complex):
            return None
        return _stable_numeric_result(result)
    return None


def _fold_comparison(expr) -> Optional[bool]:
    left_numeric = fold_numeric_expression(expr.x)
    right_numeric = fold_numeric_expression(expr.y)
    if left_numeric is not None and right_numeric is not None:
        return _compare_values(expr.op, left_numeric, right_numeric)

    if expr.op not in {'==', '!='}:
        return None
    left_bool = fold_condition_expression(expr.x)
    right_bool = fold_condition_expression(expr.y)
    if left_bool is None or right_bool is None:
        return None
    return left_bool == right_bool if expr.op == '==' else left_bool != right_bool


def _compare_values(op: str, left: ConstValue, right: ConstValue) -> Optional[bool]:
    comparable = _comparison_operands(left, right)
    if comparable is None:
        return None
    left, right, approximate = comparable
    if op == '<':
        return left < right
    if op == '<=':
        return left <= right
    if op == '>':
        return left > right
    if op == '>=':
        return left >= right
    if op == '==':
        if approximate:
            return float(left) == float(right)
        return left == right
    if op == '!=':
        if approximate:
            return float(left) != float(right)
        return left != right
    return False  # pragma: no cover


def _during_const_assign_diagnostics(state_path: str, state) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for action in state.on_durings:
        if action.is_abstract or action.is_ref or action.aspect is not None:
            continue
        for stmt in action.operations:
            diagnostics.extend(_during_stmt_const_assign_diagnostics(state_path, stmt))
    return diagnostics


def _during_stmt_const_assign_diagnostics(
    state_path: str,
    stmt: 'OperationStatement',
) -> List[ModelDiagnostic]:
    from ...model.model import Operation

    if not isinstance(stmt, Operation):
        return []
    value = _json_stable_number(fold_numeric_expression(stmt.expr))
    if value is None:
        return []
    return [
        ModelDiagnostic(
            code='W_DURING_CONST_ASSIGN',
            severity='warning',
            message=(
                f'During action in {state_path!r} assigns {stmt.var_name!r} '
                'to the same constant value every cycle.'
            ),
            refs={
                'state_path': state_path,
                'var_name': stmt.var_name,
                'value': value,
            },
        )
    ]


def _guard_const_diagnostic(transition, value: bool) -> ModelDiagnostic:
    code = 'W_GUARD_CONST_TRUE' if value else 'W_GUARD_CONST_FALSE'
    label = 'true' if value else 'false'
    source_label = _transition_endpoint_label(transition.from_state)
    target_label = _transition_endpoint_label(transition.to_state)
    return ModelDiagnostic(
        code=code,
        severity='warning',
        message=(
            f'Transition {source_label!r} -> {target_label!r} '
            f'has a guard that is statically {label}.'
        ),
        refs={'transition_span': None, 'folded_value': value},
    )


def _transition_endpoint_label(value) -> str:
    from ...dsl import EXIT_STATE, INIT_STATE

    if value is INIT_STATE or value is EXIT_STATE:
        return '[*]'
    return str(value)


def _state_path(state) -> str:
    return '.'.join(p for p in state.path if p is not None)


def _is_plain_int(value: ConstValue) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _has_unsafe_integer_operand(left: ConstValue, right: ConstValue) -> bool:
    return any(
        _is_plain_int(value) and abs(value) > _MAX_JSON_STABLE_INT
        for value in (left, right)
    )


def _json_stable_number(value: ConstValue) -> Optional[ConstValue]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        if abs(value) <= _MAX_JSON_STABLE_INT:
            return value
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        if value.is_integer():
            if abs(value) <= _MAX_JSON_STABLE_INT:
                return int(value)
            return None
        return value
    return None


def _stable_numeric_result(value: ConstValue) -> Optional[ConstValue]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        if abs(value) <= _MAX_JSON_STABLE_INT:
            return value
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        if value.is_integer() and abs(value) > _MAX_JSON_STABLE_INT:
            return None
        return value
    return None


def _comparison_operands(left: ConstValue, right: ConstValue):
    left_float = isinstance(left, float)
    right_float = isinstance(right, float)
    if not left_float and not right_float:
        return left, right, False
    if left_float and right_float:
        if math.isfinite(left) and math.isfinite(right):
            return left, right, True
        return None
    if _mixed_float_and_unsafe_integer(left, right):
        return None
    if left_float:
        if _is_plain_int(right) and abs(right) <= _MAX_JSON_STABLE_INT:
            return left, right, True
        normalized_left = _safe_integer_float(left)
        if normalized_left is None:
            return None
        return normalized_left, right, False
    if _is_plain_int(left) and abs(left) <= _MAX_JSON_STABLE_INT:
        return left, right, True
    normalized_right = _safe_integer_float(right)
    if normalized_right is None:
        return None
    return left, normalized_right, False


def _mixed_float_and_unsafe_integer(left: ConstValue, right: ConstValue) -> bool:
    return (
        (isinstance(left, float) and _is_plain_int(right) and abs(right) > _MAX_JSON_STABLE_INT)
        or (isinstance(right, float) and _is_plain_int(left) and abs(left) > _MAX_JSON_STABLE_INT)
    )


def _safe_integer_float(value: float) -> Optional[int]:
    if (
        math.isfinite(value)
        and value.is_integer()
        and abs(value) <= _MAX_JSON_STABLE_INT
    ):
        return int(value)
    return None


def _integer_power_exceeds_json_stable_range(base: int, exponent: int) -> bool:
    if exponent == 0:
        return False
    if base in {-1, 0, 1}:
        return False
    return exponent * math.log2(abs(base)) > math.log2(_MAX_JSON_STABLE_INT)
