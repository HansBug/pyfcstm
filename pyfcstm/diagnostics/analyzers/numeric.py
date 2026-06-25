"""
C/C++ deployment-profile numeric diagnostics.

This module implements the lightweight numeric analyzer used by
:func:`pyfcstm.diagnostics.inspect.inspect_model`. The analyzer is target
profile aware: each warning describes a risk for the default C/C++ generated
runtime profile rather than a target-independent FCSTM model error.

The module contains:

* :func:`collect_numeric_warnings` - Collect deterministic numeric warnings
  from a state-machine model.

.. note::
   The analyzer deliberately avoids variable range solving, cross-statement
   propagation, SMT checks, and generated-code policy changes. Those belong
   to the verify and code-generation tracks.
"""

from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple

from ...utils.validate import ModelDiagnostic, Span
from .const_fold import fold_numeric_expression

if TYPE_CHECKING:  # pragma: no cover - type-checking imports only.
    from ...model.expr import Expr
    from ...model.model import OperationStatement, StateMachine


_TARGET_FAMILY = "c_family"
_TARGET_TEMPLATES = ["c", "c_poll", "cpp", "cpp_poll"]
_TARGET_BITS = 64
_MIN_SIGNED_INT64 = -(2**63)
_MAX_SIGNED_INT64 = 2**63 - 1
_MIN_SIGNED_INT64_TEXT = str(_MIN_SIGNED_INT64)
_MAX_SIGNED_INT64_TEXT = str(_MAX_SIGNED_INT64)
_BITWISE_OPERATORS = {"&", "^", "|", "<<", ">>"}
_ZERO_OPERATORS = {"/", "%"}
_C_FAMILY_INTEGER_UFUNCS = {"ceil", "floor", "int", "round", "sign", "trunc"}
_C_FAMILY_CONDITION_OPERATORS = {
    "&&",
    "||",
    "=>",
    "xor",
    "iff",
    "==",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
}
_SHIFT_OPERATORS = {"<<", ">>"}
_RUNTIME_NOTES = {
    "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE": (
        "C/C++ deployment profile risk: the default C-family templates use "
        "PYFCSTM_GENERATED_INT64, while Python generated runtimes may not have "
        "the same fixed-width integer carrying risk."
    ),
    "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO": (
        "C/C++ deployment profile risk: generated C/C++ code needs an explicit "
        "division-by-zero or modulo-by-zero policy, while Python generated "
        "runtimes use different exception semantics."
    ),
    "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE": (
        "C/C++ deployment profile risk: the default C-family integer width is "
        "64 bits, while Python generated runtimes may not have the same "
        "fixed-width shift risk."
    ),
    "W_NUMERIC_FLOAT_BITWISE": (
        "C/C++ integer-operation profile risk: bitwise and shift operators are "
        "integer operations in the generated C-family templates; Python "
        "generated runtimes may fail for a different reason."
    ),
}


class _Context:
    """One expression location scanned by the numeric analyzer."""

    def __init__(
        self,
        expr: "Expr",
        context: str,
        span: Optional[Span],
        statement_kind: Optional[str] = None,
        var_name: Optional[str] = None,
    ) -> None:
        self.expr = expr
        self.context = context
        self.span = span
        self.statement_kind = statement_kind
        self.var_name = var_name


def collect_numeric_warnings(
    machine: Optional["StateMachine"],
) -> List[ModelDiagnostic]:
    """
    Collect C/C++ deployment-profile numeric warnings for a model.

    :param machine: State-machine model to inspect. ``None`` is accepted so
        callers can mirror other analyzer entry points during defensive
        composition.
    :type machine: Optional[pyfcstm.model.StateMachine]
    :return: Numeric warnings in model traversal order.
    :rtype: List[pyfcstm.utils.validate.ModelDiagnostic]

    Examples::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... def int too_large = 9223372036854775808;
        ... state Root { state A; [*] -> A; }
        ... '''
        >>> ast = parse_with_grammar_entry(source, 'state_machine_dsl')
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> collect_numeric_warnings(machine)[0].code
        'W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE'
    """
    if machine is None:
        return []
    var_types = {name: var_define.type for name, var_define in machine.defines.items()}
    diagnostics: List[ModelDiagnostic] = []
    for context in _iter_expression_contexts(machine):
        diagnostics.extend(_diagnostics_for_expr(context, var_types))
    return diagnostics


def _diagnostics_for_expr(
    context: _Context,
    var_types: Dict[str, str],
) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    signed_literal_children = _signed_literal_child_ids(context.expr)
    for expr in _walk_expressions(context.expr):
        if id(expr) not in signed_literal_children:
            diagnostics.extend(_literal_range_diagnostic(context, expr))
        diagnostics.extend(_constant_zero_division_diagnostic(context, expr))
        diagnostics.extend(_shift_count_diagnostic(context, expr))
        diagnostics.extend(_float_bitwise_diagnostic(context, expr, var_types))
    return diagnostics


def _iter_expression_contexts(machine: "StateMachine") -> Iterable[_Context]:
    for var_name, var_define in machine.defines.items():
        yield _Context(
            var_define.init,
            "var_initializer",
            getattr(var_define, "_span", None),
            var_name=var_name,
        )

    for state in machine.walk_states():
        for transition in state.transitions:
            if transition.guard is not None:
                yield _Context(
                    transition.guard,
                    "guard",
                    getattr(transition, "_span", None),
                )
            for stmt in transition.effects:
                yield from _iter_statement_expression_contexts(
                    stmt,
                    "transition_effect",
                )
        for action in _iter_concrete_actions(state):
            for stmt in action.operations:
                yield from _iter_statement_expression_contexts(
                    stmt,
                    "lifecycle_action",
                )


def _iter_concrete_actions(state):
    for collection in (
        state.on_enters,
        state.on_durings,
        state.on_exits,
        state.on_during_aspects,
    ):
        for action in collection:
            if action.is_abstract or action.is_ref:
                continue
            yield action


def _iter_statement_expression_contexts(
    stmt: "OperationStatement",
    context: str,
) -> Iterable[_Context]:
    from ...model.model import IfBlock, Operation

    if isinstance(stmt, Operation):
        yield _Context(
            stmt.expr,
            context,
            getattr(stmt, "_span", None),
            statement_kind="operation_assignment",
            var_name=stmt.var_name,
        )
        return
    if isinstance(stmt, IfBlock):
        for branch in stmt.branches:
            if branch.condition is not None:
                yield _Context(
                    branch.condition,
                    context,
                    getattr(branch, "_span", None),
                )
            for inner in branch.statements:
                yield from _iter_statement_expression_contexts(inner, context)


def _walk_expressions(expr: "Expr") -> Iterable["Expr"]:
    yield expr
    for child in expr._iter_subs():
        yield from _walk_expressions(child)


def _signed_literal_child_ids(expr: "Expr") -> set:
    from ...model.expr import Integer, UnaryOp

    out = set()
    for item in _walk_expressions(expr):
        if (
            isinstance(item, UnaryOp)
            and item.op in {"+", "-"}
            and isinstance(item.x, Integer)
        ):
            out.add(id(item.x))
    return out


def _literal_range_diagnostic(
    context: _Context,
    expr: "Expr",
) -> List[ModelDiagnostic]:
    literal = _signed_integer_literal(expr)
    if literal is None:
        return []
    literal_text, literal_value = literal
    if _MIN_SIGNED_INT64 <= literal_value <= _MAX_SIGNED_INT64:
        return []
    refs = _base_refs(
        "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
        context,
        _expr_text(expr),
    )
    refs.update(
        {
            "literal_text": literal_text,
            "target_bits": _TARGET_BITS,
            "signed": True,
            "min_value_text": _MIN_SIGNED_INT64_TEXT,
            "max_value_text": _MAX_SIGNED_INT64_TEXT,
        }
    )
    if context.var_name is not None:
        refs["var_name"] = context.var_name
    return [
        _diagnostic(
            "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
            (
                "C/C++ default deployment profile risk: integer literal "
                f"{literal_text} is outside the PYFCSTM_GENERATED_INT64 range "
                f"[{_MIN_SIGNED_INT64_TEXT}, {_MAX_SIGNED_INT64_TEXT}]; "
                "Python generated runtimes may not have the same fixed-width risk."
            ),
            context.span,
            refs,
        )
    ]


def _constant_zero_division_diagnostic(
    context: _Context,
    expr: "Expr",
) -> List[ModelDiagnostic]:
    from ...model.expr import BinaryOp

    if not isinstance(expr, BinaryOp) or expr.op not in _ZERO_OPERATORS:
        return []
    rhs_value = fold_numeric_expression(expr.y)
    if rhs_value is None or rhs_value != 0:
        return []
    refs = _base_refs(
        "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
        context,
        _expr_text(expr),
    )
    refs.update(
        {
            "operator": expr.op,
            "rhs_text": _expr_text(expr.y),
        }
    )
    return [
        _diagnostic(
            "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
            (
                "C/C++ default deployment profile risk: the RHS of operator "
                f"{expr.op!r} folds to 0; generated C/C++ code needs an explicit "
                "failure policy, while Python runtime exception semantics differ."
            ),
            context.span,
            refs,
        )
    ]


def _shift_count_diagnostic(
    context: _Context,
    expr: "Expr",
) -> List[ModelDiagnostic]:
    from ...model.expr import BinaryOp

    if not isinstance(expr, BinaryOp) or expr.op not in _SHIFT_OPERATORS:
        return []
    rhs_value = fold_numeric_expression(expr.y)
    if (
        rhs_value is None
        or not _plain_number(rhs_value)
        or not (rhs_value < 0 or rhs_value >= _TARGET_BITS)
    ):
        return []
    refs = _base_refs(
        "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
        context,
        _expr_text(expr),
    )
    refs.update(
        {
            "operator": expr.op,
            "target_bits": _TARGET_BITS,
            "shift_count_text": _number_text(rhs_value),
        }
    )
    return [
        _diagnostic(
            "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
            (
                "C/C++ default deployment profile risk: the shift count of "
                f"operator {expr.op!r} folds to {_number_text(rhs_value)}, "
                f"outside 0 <= count < {_TARGET_BITS}; Python generated runtimes "
                "do not represent the same fixed-width shift contract."
            ),
            context.span,
            refs,
        )
    ]


def _float_bitwise_diagnostic(
    context: _Context,
    expr: "Expr",
    var_types: Dict[str, str],
) -> List[ModelDiagnostic]:
    from ...model.expr import BinaryOp

    if not isinstance(expr, BinaryOp) or expr.op not in _BITWISE_OPERATORS:
        return []
    left = _infer_numeric_type(expr.x, var_types)
    right = _infer_numeric_type(expr.y, var_types)
    if left[0] != "float" and right[0] != "float":
        return []
    refs = _base_refs(
        "W_NUMERIC_FLOAT_BITWISE",
        context,
        _expr_text(expr),
    )
    refs.update(
        {
            "operator": expr.op,
            "operand_types": [left[0], right[0]],
            "operand_type_sources": [left[1], right[1]],
        }
    )
    return [
        _diagnostic(
            "W_NUMERIC_FLOAT_BITWISE",
            (
                "C/C++ default deployment profile risk: a float-shaped operand "
                f"participates in integer bitwise or shift operator {expr.op!r}; "
                "C-family templates generate integer operations, while Python "
                "runtime failures have different semantics."
            ),
            context.span,
            refs,
        )
    ]


def _infer_numeric_type(
    expr: "Expr",
    var_types: Dict[str, str],
) -> Tuple[str, str]:
    from ...model.expr import BinaryOp, Boolean, ConditionalOp, Float, Integer
    from ...model.expr import UnaryOp, UFunc, Variable

    if isinstance(expr, (Boolean, Integer)):
        return "int", "literal"
    if isinstance(expr, Float):
        return "float", "literal"
    if isinstance(expr, Variable):
        declared = var_types.get(expr.name)
        if declared == "float":
            return "float", "declared_var"
        if declared == "int":
            return "int", "declared_var"
        return "unknown", "declared_var"
    if isinstance(expr, UnaryOp):
        inner_type, inner_source = _infer_numeric_type(expr.x, var_types)
        if inner_type in {"int", "float"}:
            return inner_type, inner_source
        return "unknown", "local_expression"
    if isinstance(expr, UFunc):
        if expr.func in _C_FAMILY_INTEGER_UFUNCS:
            return "int", "local_expression"
        if expr.func == "abs":
            inner_type, _inner_source = _infer_numeric_type(expr.x, var_types)
            if inner_type in {"int", "float"}:
                return inner_type, "local_expression"
            return "unknown", "local_expression"
        return "float", "local_expression"
    if isinstance(expr, BinaryOp):
        if expr.op in _BITWISE_OPERATORS or expr.op in _C_FAMILY_CONDITION_OPERATORS:
            return "int", "local_expression"
        if expr.op == "/":
            return "float", "local_expression"
        left_type, _left_source = _infer_numeric_type(expr.x, var_types)
        right_type, _right_source = _infer_numeric_type(expr.y, var_types)
        return _merge_numeric_types(left_type, right_type), "local_expression"
    if isinstance(expr, ConditionalOp):
        true_type, _true_source = _infer_numeric_type(expr.if_true, var_types)
        false_type, _false_source = _infer_numeric_type(expr.if_false, var_types)
        return _merge_numeric_types(true_type, false_type), "local_expression"
    return "unknown", "local_expression"


def _merge_numeric_types(type_a: str, type_b: str) -> str:
    known = {type_a, type_b} - {"unknown"}
    if "float" in known:
        return "float"
    if known == {"int"}:
        return "int"
    return "unknown"


def _signed_integer_literal(expr: "Expr") -> Optional[Tuple[str, int]]:
    from ...model.expr import Integer, UnaryOp

    if isinstance(expr, Integer):
        return str(expr.value), expr.value
    if isinstance(expr, UnaryOp) and isinstance(expr.x, Integer):
        if expr.op == "-":
            return "-" + str(expr.x.value), -expr.x.value
        if expr.op == "+":
            return "+" + str(expr.x.value), expr.x.value
    return None


def _base_refs(
    code: str,
    context: _Context,
    expr_text: Optional[str],
) -> Dict[str, object]:
    refs: Dict[str, object] = {
        "target_family": _TARGET_FAMILY,
        "target_templates": list(_TARGET_TEMPLATES),
        "runtime_note": _RUNTIME_NOTES[code],
        "context": context.context,
        "expr_text": expr_text or "",
    }
    if context.statement_kind is not None:
        refs["statement_kind"] = context.statement_kind
    return refs


def _diagnostic(
    code: str,
    message: str,
    span: Optional[Span],
    refs: Dict[str, object],
) -> ModelDiagnostic:
    return ModelDiagnostic(
        code=code,
        severity="warning",
        message=message,
        span=span,
        refs=refs,
    )


def _expr_text(expr: Optional["Expr"]) -> Optional[str]:
    from ..inspect import _expr_text as render_expr_text

    return render_expr_text(expr)


def _plain_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _number_text(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
