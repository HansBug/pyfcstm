"""
C runtime code-generation helpers for built-in native templates.

This module contains small, deterministic emitters used by the built-in
``c`` and ``c_poll`` templates. The helpers render lifecycle action,
transition-effect, and guard bodies with explicit runtime diagnostics around
DSL expression failures that would otherwise surface as native crashes or C
compile errors.

The module contains:

* :func:`render_c_action_body` - Render operation statements as a fallible C body.
* :func:`render_c_condition_body` - Render a fallible C guard/condition body.

The generated code remains C99-only and uses only helpers already emitted by
``machine.c``; it does not add third-party runtime dependencies.

Example::

    >>> from pyfcstm.dsl.node import Integer, OperationAssignment
    >>> code = render_c_action_body(
    ...     [OperationAssignment("x", Integer("1"))],
    ...     {"x": "int"},
    ...     "DemoMachine",
    ...     "DEMO_MACHINE",
    ... )
    >>> "scope->x = 1;" in code
    True
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from ..dsl import node as dsl_nodes
from ..model import IfBlock, Operation, OperationStatement
from ..utils import to_c_identifier


@dataclass(frozen=True)
class _ExprRenderResult:
    """
    Rendered C expression plus coarse DSL type metadata.

    :param text: C expression text.
    :type text: str
    :param value_type: Coarse DSL value type, such as ``"int"`` or ``"float"``.
    :type value_type: str, optional

    Example::

        >>> result = _ExprRenderResult("scope->x", "int")
        >>> result.text
        'scope->x'
    """

    text: str
    value_type: Optional[str]


@dataclass(frozen=True)
class _CNames:
    """
    Generated C naming context.

    :param machine_class_name: Generated machine class prefix.
    :type machine_class_name: str
    :param machine_macro_name: Generated macro prefix.
    :type machine_macro_name: str

    Example::

        >>> names = _CNames("RootMachine", "ROOT_MACHINE")
        >>> names.failure
        'ROOT_MACHINE_FAILURE'
    """

    machine_class_name: str
    machine_macro_name: str

    @property
    def success(self) -> str:
        """
        Return the generated success macro.

        :return: Success macro name.
        :rtype: str

        Example::

            >>> _CNames("Demo", "DEMO").success
            'DEMO_SUCCESS'
        """
        return "%s_SUCCESS" % self.machine_macro_name

    @property
    def failure(self) -> str:
        """
        Return the generated failure macro.

        :return: Failure macro name.
        :rtype: str

        Example::

            >>> _CNames("Demo", "DEMO").failure
            'DEMO_FAILURE'
        """
        return "%s_FAILURE" % self.machine_macro_name

    @property
    def set_error(self) -> str:
        """
        Return the generated internal error setter name.

        :return: Error-setter function name.
        :rtype: str

        Example::

            >>> _CNames("Demo", "DEMO").set_error
            '_Demo_set_error'
        """
        return "_%s_set_error" % self.machine_class_name


OperationalNode = Union[OperationStatement, dsl_nodes.OperationalStatement]


_MATH_FUNC_NAMES = {
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "sinh",
    "cosh",
    "tanh",
    "asinh",
    "acosh",
    "atanh",
    "sqrt",
    "cbrt",
    "exp",
    "log",
    "log10",
    "log2",
    "log1p",
    "ceil",
    "floor",
    "round",
    "trunc",
}


_INT_OPERATORS = {"<<", ">>", "&", "^", "|"}


def _quote_c_string(value: str) -> str:
    """
    Quote a string for generated C source.

    :param value: Text to quote.
    :type value: str
    :return: C string literal text.
    :rtype: str

    Example::

        >>> _quote_c_string("a'b")
        '"a\'b"'
    """
    return json.dumps(value)


def _line(lines: List[str], indent: str, level: int, text: str) -> None:
    lines.append("%s%s" % (indent * level, text))


def _normalise_var_types(var_types: Mapping[str, Any]) -> Dict[str, str]:
    """
    Convert model define metadata to a name/type mapping.

    :param var_types: Mapping of variable names to type strings or define objects.
    :type var_types: typing.Mapping[str, typing.Any]
    :return: Normalized variable type map.
    :rtype: dict

    Example::

        >>> _normalise_var_types({"x": "int"})
        {'x': 'int'}
    """
    result = {}
    for name, value in var_types.items():
        if isinstance(value, str):
            result[name] = value
        elif hasattr(value, "type"):
            result[name] = str(value.type)
        else:
            result[name] = str(value)
    return result


def _coerce_expr(expr: Any) -> dsl_nodes.Expr:
    if isinstance(expr, dsl_nodes.Expr):
        return expr
    if hasattr(expr, "to_ast_node"):
        return expr.to_ast_node()
    raise TypeError("Unsupported C expression node: %r" % (type(expr),))


def _coerce_statement(statement: OperationalNode) -> dsl_nodes.OperationalStatement:
    if isinstance(statement, dsl_nodes.OperationalStatement):
        return statement
    if isinstance(statement, (Operation, IfBlock)):
        return statement.to_ast_node()
    if hasattr(statement, "to_ast_node"):
        node = statement.to_ast_node()
        if isinstance(node, dsl_nodes.OperationalStatement):
            return node
    raise TypeError("Unsupported C operation statement: %r" % (type(statement),))


def _merge_types(type_a: Optional[str], type_b: Optional[str]) -> Optional[str]:
    known = {type_a, type_b} - {None}
    if not known:
        return None
    if "float" in known:
        return "float"
    if known == {"int"}:
        return "int"
    return next(iter(known))


def _infer_expr_type(
    expr: dsl_nodes.Expr, known_types: Mapping[str, str]
) -> Optional[str]:
    if isinstance(expr, (dsl_nodes.Integer, dsl_nodes.HexInt, dsl_nodes.Boolean)):
        return "int"
    if isinstance(expr, (dsl_nodes.Float, dsl_nodes.Constant)):
        return "float"
    if isinstance(expr, dsl_nodes.Name):
        return known_types.get(expr.name)
    if isinstance(expr, dsl_nodes.Paren):
        return _infer_expr_type(expr.expr, known_types)
    if isinstance(expr, dsl_nodes.UnaryOp):
        return _infer_expr_type(expr.expr, known_types)
    if isinstance(expr, dsl_nodes.UFunc):
        if expr.func in {"floor", "ceil", "round", "trunc", "int", "sign"}:
            return "int"
        if expr.func == "abs":
            return _infer_expr_type(expr.expr, known_types)
        return "float"
    if isinstance(expr, dsl_nodes.BinaryOp):
        if expr.op in _INT_OPERATORS:
            return "int"
        if expr.op in {
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
        }:
            return "int"
        if expr.op == "/":
            return "float"
        return _merge_types(
            _infer_expr_type(expr.expr1, known_types),
            _infer_expr_type(expr.expr2, known_types),
        )
    if isinstance(expr, dsl_nodes.ConditionalOp):
        return _merge_types(
            _infer_expr_type(expr.value_true, known_types),
            _infer_expr_type(expr.value_false, known_types),
        )
    return None


def _render_expr(
    expr: dsl_nodes.Expr,
    known_types: Mapping[str, str],
    state_names: Optional[Iterable[str]] = None,
) -> _ExprRenderResult:
    expr = _coerce_expr(expr)
    state_name_set = set(state_names if state_names is not None else known_types.keys())
    if isinstance(expr, dsl_nodes.Integer):
        return _ExprRenderResult(repr(expr.value), "int")
    if isinstance(expr, dsl_nodes.HexInt):
        return _ExprRenderResult(hex(expr.value), "int")
    if isinstance(expr, dsl_nodes.Float):
        return _ExprRenderResult(repr(expr.value), "float")
    if isinstance(expr, dsl_nodes.Boolean):
        return _ExprRenderResult("1" if expr.value else "0", "int")
    if isinstance(expr, dsl_nodes.Constant):
        return _ExprRenderResult(repr(expr.value), "float")
    if isinstance(expr, dsl_nodes.Name):
        if expr.name in known_types:
            text = (
                "scope->%s" % to_c_identifier(expr.name)
                if expr.name in state_name_set
                else to_c_identifier(expr.name)
            )
            return _ExprRenderResult(text, known_types.get(expr.name))
        return _ExprRenderResult(to_c_identifier(expr.name), None)
    if isinstance(expr, dsl_nodes.Paren):
        inner = _render_expr(expr.expr, known_types, state_name_set)
        return _ExprRenderResult("(%s)" % inner.text, inner.value_type)
    if isinstance(expr, dsl_nodes.UnaryOp):
        inner = _render_expr(expr.expr, known_types, state_name_set)
        op = "!" if expr.op == "not" else expr.op
        return _ExprRenderResult(
            "(%s%s)" % (op, inner.text), _infer_expr_type(expr, known_types)
        )
    if isinstance(expr, dsl_nodes.UFunc):
        inner = _render_expr(expr.expr, known_types, state_name_set)
        if expr.func == "sign":
            text = "(((%s) > 0) - ((%s) < 0))" % (inner.text, inner.text)
        elif expr.func == "abs":
            text = (
                "fabs(%s)" % inner.text
                if inner.value_type == "float"
                else "llabs(%s)" % inner.text
            )
        elif expr.func == "cbrt":
            text = "cbrt(%s)" % inner.text
        elif expr.func in _MATH_FUNC_NAMES:
            text = "%s(%s)" % (expr.func, inner.text)
        else:
            text = "%s(%s)" % (expr.func, inner.text)
        return _ExprRenderResult(text, _infer_expr_type(expr, known_types))
    if isinstance(expr, dsl_nodes.BinaryOp):
        left = _render_expr(expr.expr1, known_types, state_name_set)
        right = _render_expr(expr.expr2, known_types, state_name_set)
        if expr.op in _INT_OPERATORS and (
            left.value_type == "float" or right.value_type == "float"
        ):
            text = "0"
        elif expr.op == "**":
            text = "pow(%s, %s)" % (left.text, right.text)
        elif expr.op == "%" and (
            left.value_type == "float" or right.value_type == "float"
        ):
            text = "fmod(%s, %s)" % (left.text, right.text)
        elif expr.op == "/":
            text = "(((double)(%s)) / (%s))" % (left.text, right.text)
        elif expr.op == "=>":
            text = "((!(%s)) || (%s))" % (left.text, right.text)
        elif expr.op == "xor":
            text = "((%s) != (%s))" % (left.text, right.text)
        elif expr.op == "iff":
            text = "((%s) == (%s))" % (left.text, right.text)
        else:
            text = "((%s) %s (%s))" % (left.text, expr.op, right.text)
        return _ExprRenderResult(text, _infer_expr_type(expr, known_types))
    if isinstance(expr, dsl_nodes.ConditionalOp):
        cond = _render_expr(expr.cond, known_types, state_name_set)
        value_true = _render_expr(expr.value_true, known_types, state_name_set)
        value_false = _render_expr(expr.value_false, known_types, state_name_set)
        text = "((%s) ? (%s) : (%s))" % (cond.text, value_true.text, value_false.text)
        return _ExprRenderResult(text, _infer_expr_type(expr, known_types))
    raise TypeError("Unsupported C expression node: %r" % (type(expr),))


def _python_type_name(value_type: Optional[str]) -> str:
    if value_type == "float":
        return "float"
    return "int"


def _zero_division_message(
    operator_text: str, value_type: Optional[str], right_text: str
) -> str:
    if operator_text == "%":
        if value_type == "float":
            return "float modulo"
        return "integer modulo by zero"
    if value_type == "float" or "." in right_text:
        return "float division by zero"
    return "division by zero"


def _emit_error(
    lines: List[str], names: _CNames, indent: str, level: int, message: str
) -> None:
    _line(
        lines,
        indent,
        level,
        "%s(machine, %s);" % (names.set_error, _quote_c_string(message)),
    )
    _line(lines, indent, level, "return %s;" % names.failure)


def _emit_expr_checks(
    lines: List[str],
    expr: dsl_nodes.Expr,
    known_types: Mapping[str, str],
    state_names: Iterable[str],
    names: _CNames,
    usage: str,
    indent: str,
    level: int,
) -> bool:
    expr = _coerce_expr(expr)
    state_name_set = set(state_names)
    if isinstance(expr, dsl_nodes.Paren):
        return _emit_expr_checks(
            lines, expr.expr, known_types, state_name_set, names, usage, indent, level
        )
    if isinstance(expr, dsl_nodes.UnaryOp):
        return _emit_expr_checks(
            lines, expr.expr, known_types, state_name_set, names, usage, indent, level
        )
    if isinstance(expr, dsl_nodes.UFunc):
        return _emit_expr_checks(
            lines, expr.expr, known_types, state_name_set, names, usage, indent, level
        )
    if isinstance(expr, dsl_nodes.ConditionalOp):
        cond = _render_expr(expr.cond, known_types, state_name_set).text
        safe = _emit_expr_checks(
            lines, expr.cond, known_types, state_name_set, names, usage, indent, level
        )
        _line(lines, indent, level, "if (%s) {" % cond)
        safe = (
            _emit_expr_checks(
                lines,
                expr.value_true,
                known_types,
                state_name_set,
                names,
                usage,
                indent,
                level + 1,
            )
            and safe
        )
        _line(lines, indent, level, "} else {")
        safe = (
            _emit_expr_checks(
                lines,
                expr.value_false,
                known_types,
                state_name_set,
                names,
                usage,
                indent,
                level + 1,
            )
            and safe
        )
        _line(lines, indent, level, "}")
        return safe
    if isinstance(expr, dsl_nodes.BinaryOp):
        left = _render_expr(expr.expr1, known_types, state_name_set)
        right = _render_expr(expr.expr2, known_types, state_name_set)
        if expr.op == "&&":
            safe = _emit_expr_checks(
                lines,
                expr.expr1,
                known_types,
                state_name_set,
                names,
                usage,
                indent,
                level,
            )
            _line(lines, indent, level, "if (%s) {" % left.text)
            safe = (
                _emit_expr_checks(
                    lines,
                    expr.expr2,
                    known_types,
                    state_name_set,
                    names,
                    usage,
                    indent,
                    level + 1,
                )
                and safe
            )
            _line(lines, indent, level, "}")
            return safe
        if expr.op == "||":
            safe = _emit_expr_checks(
                lines,
                expr.expr1,
                known_types,
                state_name_set,
                names,
                usage,
                indent,
                level,
            )
            _line(lines, indent, level, "if (!(%s)) {" % left.text)
            safe = (
                _emit_expr_checks(
                    lines,
                    expr.expr2,
                    known_types,
                    state_name_set,
                    names,
                    usage,
                    indent,
                    level + 1,
                )
                and safe
            )
            _line(lines, indent, level, "}")
            return safe

        safe = _emit_expr_checks(
            lines, expr.expr1, known_types, state_name_set, names, usage, indent, level
        )
        safe = (
            _emit_expr_checks(
                lines,
                expr.expr2,
                known_types,
                state_name_set,
                names,
                usage,
                indent,
                level,
            )
            and safe
        )
        if expr.op in {"/", "%"}:
            _line(lines, indent, level, "if ((%s) == 0) {" % right.text)
            _emit_error(
                lines,
                names,
                indent,
                level + 1,
                "%s evaluation failed: %s"
                % (
                    usage,
                    _zero_division_message(
                        expr.op,
                        _merge_types(left.value_type, right.value_type),
                        right.text,
                    ),
                ),
            )
            _line(lines, indent, level, "}")
        if expr.op in _INT_OPERATORS:
            invalid = left.value_type == "float" or right.value_type == "float"
            if invalid:
                message = (
                    "%s evaluation failed: unsupported operand type(s) for %s: '%s' and '%s'"
                    % (
                        usage,
                        expr.op,
                        _python_type_name(left.value_type),
                        _python_type_name(right.value_type),
                    )
                )
                _emit_error(lines, names, indent, level, message)
                return False
        return safe
    return True


def _state_target(name: str, state_vars: Mapping[str, str]) -> str:
    if name in state_vars:
        return "scope->%s" % to_c_identifier(name)
    return to_c_identifier(name)


def _c_type(value_type: Optional[str]) -> str:
    if value_type == "int":
        return "PYFCSTM_GENERATED_INT64"
    return "double"


def _render_statement_sequence(
    statements: Sequence[dsl_nodes.OperationalStatement],
    state_types: Mapping[str, str],
    visible_types: Mapping[str, str],
    names: _CNames,
    indent: str,
    level: int,
) -> Tuple[List[str], Dict[str, str]]:
    lines: List[str] = []
    current_types = dict(visible_types)
    for statement in statements:
        known_types = {**state_types, **current_types}
        if isinstance(statement, dsl_nodes.OperationAssignment):
            target = _state_target(statement.name, state_types)
            expr = _render_expr(statement.expr, known_types, state_types.keys())
            checks: List[str] = []
            safe = _emit_expr_checks(
                checks,
                statement.expr,
                known_types,
                state_types.keys(),
                names,
                "operation assignment to '%s'" % statement.name,
                indent,
                level,
            )
            lines.extend(checks)
            if not safe:
                continue
            if statement.name not in state_types:
                inferred_type = _infer_expr_type(statement.expr, known_types)
                if statement.name not in current_types:
                    _line(
                        lines,
                        indent,
                        level,
                        "%s %s;"
                        % (_c_type(inferred_type), to_c_identifier(statement.name)),
                    )
                if inferred_type is not None:
                    current_types[statement.name] = inferred_type
            _line(lines, indent, level, "%s = %s;" % (target, expr.text))
            continue

        if isinstance(statement, dsl_nodes.OperationIf):

            def emit_branch_body(
                branch: dsl_nodes.OperationIfBranch, body_level: int
            ) -> None:
                """Emit one branch body with simulator-compatible local scope."""
                body, _ = _render_statement_sequence(
                    tuple(branch.statements),
                    state_types,
                    dict(current_types),
                    names,
                    indent,
                    body_level,
                )
                if body:
                    lines.extend(body)
                else:
                    _line(lines, indent, body_level, "/* no-op */")

            def emit_branch_chain(index: int, chain_level: int) -> None:
                """Nest later branch checks so earlier matched branches stay lazy."""
                branch = statement.branches[index]
                if branch.condition is None:
                    emit_branch_body(branch, chain_level)
                    return

                branch_known = {**state_types, **current_types}
                _emit_expr_checks(
                    lines,
                    branch.condition,
                    branch_known,
                    state_types.keys(),
                    names,
                    "if-block condition",
                    indent,
                    chain_level,
                )
                _line(
                    lines,
                    indent,
                    chain_level,
                    "if (%s) {"
                    % _render_expr(
                        branch.condition, branch_known, state_types.keys()
                    ).text,
                )
                emit_branch_body(branch, chain_level + 1)
                if index + 1 < len(statement.branches):
                    _line(lines, indent, chain_level, "} else {")
                    emit_branch_chain(index + 1, chain_level + 1)
                    _line(lines, indent, chain_level, "}")
                else:
                    _line(lines, indent, chain_level, "}")

            emit_branch_chain(0, level)
            continue

        raise TypeError("Unsupported C operation statement: %r" % (type(statement),))
    return lines, current_types


def render_c_action_body(
    statements: Iterable[OperationalNode],
    var_types: Mapping[str, Any],
    machine_class_name: str,
    machine_macro_name: str,
    indent: str = "    ",
) -> str:
    """
    Render a fallible generated C body for operation statements.

    :param statements: Operation statements from an action or transition effect.
    :type statements: typing.Iterable[typing.Union[pyfcstm.model.OperationStatement, pyfcstm.dsl.node.OperationalStatement]]
    :param var_types: Persistent variable type mapping or model defines mapping.
    :type var_types: typing.Mapping[str, typing.Any]
    :param machine_class_name: Generated machine class name, such as
        ``"RootMachine"``.
    :type machine_class_name: str
    :param machine_macro_name: Generated macro prefix, such as
        ``"ROOT_MACHINE"``.
    :type machine_macro_name: str
    :param indent: Indentation unit used for generated C code, defaults to four
        spaces.
    :type indent: str, optional
    :return: C statements ending in a generated success or failure return.
    :rtype: str

    Example::

        >>> from pyfcstm.dsl.node import Integer, OperationAssignment
        >>> body = render_c_action_body(
        ...     [OperationAssignment("x", Integer("1"))], {"x": "int"}, "M", "M"
        ... )
        >>> body.strip().endswith("return M_SUCCESS;")
        True
    """
    state_types = _normalise_var_types(var_types)
    nodes = tuple(_coerce_statement(statement) for statement in statements)
    names = _CNames(machine_class_name, machine_macro_name)
    lines = [
        "%s(void)machine;" % indent,
        "%s(void)scope;" % indent,
    ]
    body, _ = _render_statement_sequence(nodes, state_types, {}, names, indent, 1)
    lines.extend(body)
    lines.append("%sreturn %s;" % (indent, names.success))
    return "\n".join(lines)


def render_c_condition_body(
    expr: Any,
    var_types: Mapping[str, Any],
    machine_class_name: str,
    machine_macro_name: str,
    usage: str,
    result_name: str = "result",
    indent: str = "    ",
) -> str:
    """
    Render a fallible generated C body for a boolean condition.

    :param expr: Guard or condition expression.
    :type expr: typing.Any
    :param var_types: Persistent variable type mapping or model defines mapping.
    :type var_types: typing.Mapping[str, typing.Any]
    :param machine_class_name: Generated machine class name.
    :type machine_class_name: str
    :param machine_macro_name: Generated macro prefix.
    :type machine_macro_name: str
    :param usage: Diagnostic usage prefix, for example
        ``"transition guard"``.
    :type usage: str
    :param result_name: Pointer variable receiving the truth value, defaults to
        ``"result"``.
    :type result_name: str, optional
    :param indent: Indentation unit used for generated C code, defaults to four
        spaces.
    :type indent: str, optional
    :return: C condition body ending in generated success or failure return.
    :rtype: str

    Example::

        >>> from pyfcstm.dsl.node import Integer
        >>> body = render_c_condition_body(Integer("1"), {}, "M", "M", "guard")
        >>> "*result = !!(1);" in body
        True
    """
    state_types = _normalise_var_types(var_types)
    expr_node = _coerce_expr(expr)
    names = _CNames(machine_class_name, machine_macro_name)
    lines = [
        "%s(void)machine;" % indent,
        "%s(void)scope;" % indent,
    ]
    _emit_expr_checks(
        lines, expr_node, state_types, state_types.keys(), names, usage, indent, 1
    )
    rendered = _render_expr(expr_node, state_types, state_types.keys())
    lines.append("%s*%s = !!(%s);" % (indent, result_name, rendered.text))
    lines.append("%sreturn %s;" % (indent, names.success))
    return "\n".join(lines)
