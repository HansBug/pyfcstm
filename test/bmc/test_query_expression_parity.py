"""Strict expression-parity tests between FCSTM DSL and FBMCQ parsers."""

from typing import Any, cast

import pytest

from pyfcstm.bmc import ast as bmc_nodes
from pyfcstm.bmc.parse import parse_bmc_cond_expression, parse_bmc_num_expression
from pyfcstm.dsl import node as fcstm_nodes
from pyfcstm.dsl.parse import parse_with_grammar_entry

_NUMERIC_OPS = {"**", "*", "/", "%", "+", "-", "<<", ">>", "&", "^", "|"}
_NUMERIC_COMPARISONS = {"<", ">", "<=", ">=", "==", "!="}
_CONDITION_OPS = {"==", "!=", "iff", "&&", "xor", "||", "=>"}


def _strip_paren(expr: fcstm_nodes.Expr) -> fcstm_nodes.Expr:
    """Remove FCSTM-only parenthesis nodes for semantic-shape comparison.

    :param expr: FCSTM expression node.
    :type expr: pyfcstm.dsl.node.Expr
    :return: Expression with transparent :class:`pyfcstm.dsl.node.Paren`
        wrappers removed.
    :rtype: pyfcstm.dsl.node.Expr

    Example::

        >>> from pyfcstm.dsl.node import Integer, Paren
        >>> _strip_paren(Paren(Integer("1"))).raw
        '1'
    """
    while isinstance(expr, fcstm_nodes.Paren):
        expr = expr.expr
    return expr


def _is_fcstm_condition_expr(expr: fcstm_nodes.Expr) -> bool:
    """Return whether a FCSTM node is a condition expression in the parity subset.

    :param expr: FCSTM expression node.
    :type expr: pyfcstm.dsl.node.Expr
    :return: ``True`` when ``expr`` belongs to the condition-expression
        category.
    :rtype: bool

    Example::

        >>> from pyfcstm.dsl.node import Boolean
        >>> _is_fcstm_condition_expr(Boolean("true"))
        True
    """
    expr = _strip_paren(expr)
    if isinstance(expr, fcstm_nodes.Boolean):
        return True
    if isinstance(expr, fcstm_nodes.UnaryOp):
        return expr.op == "!" and _is_fcstm_condition_expr(expr.expr)
    if isinstance(expr, fcstm_nodes.ConditionalOp):
        return _is_fcstm_condition_expr(expr.value_true) and _is_fcstm_condition_expr(
            expr.value_false
        )
    if isinstance(expr, fcstm_nodes.BinaryOp):
        if expr.op in {"&&", "xor", "||", "=>", "iff"}:
            return True
        if expr.op in {"==", "!="}:
            return _is_fcstm_condition_expr(expr.expr1) and _is_fcstm_condition_expr(
                expr.expr2
            )
        if expr.op in {"<", ">", "<=", ">="}:
            return True
    return False


def _to_bmc_num(expr: fcstm_nodes.Expr) -> bmc_nodes.BmcNumExpr:
    """Convert a FCSTM numeric expression and narrow its type for helpers.

    :param expr: FCSTM expression known by the grammar context to be numeric.
    :type expr: pyfcstm.dsl.node.Expr
    :return: Equivalent BMC numeric expression.
    :rtype: pyfcstm.bmc.ast.BmcNumExpr

    Example::

        >>> from pyfcstm.dsl.node import Integer
        >>> _to_bmc_num(Integer("1")).to_canonical()["value"]
        1
    """
    return cast(bmc_nodes.BmcNumExpr, _fcstm_to_bmc_expr(expr, "num"))


def _to_bmc_cond(expr: fcstm_nodes.Expr) -> bmc_nodes.BmcCondExpr:
    """Convert a FCSTM condition expression and narrow its helper type.

    :param expr: FCSTM expression known by the grammar context to be a
        condition expression.
    :type expr: pyfcstm.dsl.node.Expr
    :return: Equivalent BMC condition expression.
    :rtype: pyfcstm.bmc.ast.BmcCondExpr

    Example::

        >>> from pyfcstm.dsl.node import Boolean
        >>> _to_bmc_cond(Boolean("true")).to_canonical()["value"]
        True
    """
    return cast(bmc_nodes.BmcCondExpr, _fcstm_to_bmc_expr(expr, "cond"))


def _fcstm_to_bmc_expr(expr: fcstm_nodes.Expr, category: str) -> bmc_nodes.BmcExpr:
    """Convert a FCSTM expression AST node into the matching BMC AST node.

    :param expr: FCSTM expression node parsed from ``num_expression`` or
        ``cond_expression``.
    :type expr: pyfcstm.dsl.node.Expr
    :param category: Expression category, either ``"num"`` or ``"cond"``.
    :type category: str
    :return: Equivalent BMC expression node.
    :rtype: pyfcstm.bmc.ast.BmcExpr

    Example::

        >>> from pyfcstm.dsl.node import Integer
        >>> _fcstm_to_bmc_expr(Integer("1"), "num").to_canonical()["value"]
        1
    """
    expr = _strip_paren(expr)
    if isinstance(expr, fcstm_nodes.Integer):
        return bmc_nodes.IntLiteral(expr.raw, kind="decimal")
    if isinstance(expr, fcstm_nodes.HexInt):
        return bmc_nodes.IntLiteral(expr.raw, kind="hex")
    if isinstance(expr, fcstm_nodes.Float):
        return bmc_nodes.FloatLiteral(expr.raw)
    if isinstance(expr, fcstm_nodes.Boolean):
        return bmc_nodes.BoolLiteral(expr.raw)
    if isinstance(expr, fcstm_nodes.Constant):
        return bmc_nodes.MathConst(expr.raw)
    if isinstance(expr, fcstm_nodes.Name):
        return bmc_nodes.NameRef(expr.name)
    if isinstance(expr, fcstm_nodes.UnaryOp):
        if category == "num":
            return bmc_nodes.NumUnaryOp(expr.op, _to_bmc_num(expr.expr))
        return bmc_nodes.CondUnaryOp(expr.op, _to_bmc_cond(expr.expr))
    if isinstance(expr, fcstm_nodes.UFunc):
        return bmc_nodes.UFuncCall(expr.func, _to_bmc_num(expr.expr))
    if isinstance(expr, fcstm_nodes.ConditionalOp):
        condition = _to_bmc_cond(expr.cond)
        if category == "num":
            return bmc_nodes.NumConditionalOp(
                condition,
                _to_bmc_num(expr.value_true),
                _to_bmc_num(expr.value_false),
            )
        return bmc_nodes.CondConditionalOp(
            condition,
            _to_bmc_cond(expr.value_true),
            _to_bmc_cond(expr.value_false),
        )
    if isinstance(expr, fcstm_nodes.BinaryOp):
        if category == "num" and expr.op in _NUMERIC_OPS:
            return bmc_nodes.NumBinaryOp(
                _to_bmc_num(expr.expr1),
                expr.op,
                _to_bmc_num(expr.expr2),
            )
        if expr.op in _NUMERIC_COMPARISONS and not (
            expr.op in {"==", "!="}
            and _is_fcstm_condition_expr(expr.expr1)
            and _is_fcstm_condition_expr(expr.expr2)
        ):
            return bmc_nodes.NumericComparison(
                _to_bmc_num(expr.expr1),
                expr.op,
                _to_bmc_num(expr.expr2),
            )
        if expr.op in _CONDITION_OPS:
            return bmc_nodes.CondBinaryOp(
                _to_bmc_cond(expr.expr1),
                expr.op,
                _to_bmc_cond(expr.expr2),
            )
    raise TypeError("Unsupported FCSTM parity expression: %r." % (expr,))


def _bmc_to_fcstm_expr(expr: bmc_nodes.BmcExpr) -> fcstm_nodes.Expr:
    """Convert a BMC expression AST node into the matching FCSTM AST node.

    :param expr: BMC expression node from the FCSTM-compatible subset.
    :type expr: pyfcstm.bmc.ast.BmcExpr
    :return: Equivalent FCSTM expression node.
    :rtype: pyfcstm.dsl.node.Expr

    Example::

        >>> _bmc_to_fcstm_expr(bmc_nodes.IntLiteral("1")).raw
        '1'
    """
    if isinstance(expr, bmc_nodes.IntLiteral):
        if expr.kind == "hex":
            return fcstm_nodes.HexInt(expr.raw)
        return fcstm_nodes.Integer(expr.raw)
    if isinstance(expr, bmc_nodes.FloatLiteral):
        return fcstm_nodes.Float(expr.raw)
    if isinstance(expr, bmc_nodes.BoolLiteral):
        return fcstm_nodes.Boolean(expr.raw)
    if isinstance(expr, bmc_nodes.NameRef):
        return fcstm_nodes.Name(expr.name)
    if isinstance(expr, bmc_nodes.MathConst):
        return fcstm_nodes.Constant(expr.name)
    if isinstance(expr, bmc_nodes.NumUnaryOp):
        return fcstm_nodes.UnaryOp(expr.op, _bmc_to_fcstm_expr(expr.operand))
    if isinstance(expr, bmc_nodes.NumBinaryOp):
        return fcstm_nodes.BinaryOp(
            _bmc_to_fcstm_expr(expr.left), expr.op, _bmc_to_fcstm_expr(expr.right)
        )
    if isinstance(expr, bmc_nodes.NumConditionalOp):
        return fcstm_nodes.ConditionalOp(
            _bmc_to_fcstm_expr(expr.condition),
            _bmc_to_fcstm_expr(expr.if_true),
            _bmc_to_fcstm_expr(expr.if_false),
        )
    if isinstance(expr, bmc_nodes.UFuncCall):
        return fcstm_nodes.UFunc(expr.func, _bmc_to_fcstm_expr(expr.operand))
    if isinstance(expr, bmc_nodes.CondUnaryOp):
        return fcstm_nodes.UnaryOp(expr.op, _bmc_to_fcstm_expr(expr.operand))
    if isinstance(expr, bmc_nodes.NumericComparison):
        return fcstm_nodes.BinaryOp(
            _bmc_to_fcstm_expr(expr.left), expr.op, _bmc_to_fcstm_expr(expr.right)
        )
    if isinstance(expr, bmc_nodes.CondBinaryOp):
        return fcstm_nodes.BinaryOp(
            _bmc_to_fcstm_expr(expr.left), expr.op, _bmc_to_fcstm_expr(expr.right)
        )
    if isinstance(expr, bmc_nodes.CondConditionalOp):
        return fcstm_nodes.ConditionalOp(
            _bmc_to_fcstm_expr(expr.condition),
            _bmc_to_fcstm_expr(expr.if_true),
            _bmc_to_fcstm_expr(expr.if_false),
        )
    raise TypeError("Unsupported BMC parity expression: %r." % (expr,))


def _shared_shape_from_bmc(expr: bmc_nodes.BmcExpr) -> Any:
    """Project a BMC expression to a strict JSON-like parity shape.

    :param expr: BMC expression node.
    :type expr: pyfcstm.bmc.ast.BmcExpr
    :return: Shared parity shape.  Boolean raw spelling is normalized because
        FCSTM stores boolean literals in lowercase.
    :rtype: object

    Example::

        >>> _shared_shape_from_bmc(bmc_nodes.BoolLiteral("TRUE"))["raw"]
        'true'
    """
    canonical = expr.to_canonical()
    if canonical["node"] == "bool_literal":
        canonical = dict(canonical)
        canonical["raw"] = canonical["raw"].lower()
    return canonical


def _shared_shape_from_fcstm(expr: fcstm_nodes.Expr, category: str) -> Any:
    """Project a FCSTM expression to the same shared parity shape as BMC.

    :param expr: FCSTM expression node.
    :type expr: pyfcstm.dsl.node.Expr
    :param category: Expression category, either ``"num"`` or ``"cond"``.
    :type category: str
    :return: Shared parity shape.
    :rtype: object

    Example::

        >>> _shared_shape_from_fcstm(fcstm_nodes.Integer("1"), "num")["value"]
        1
    """
    return _shared_shape_from_bmc(_fcstm_to_bmc_expr(expr, category))


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("0", id="zero"),
        pytest.param("00", id="double-zero"),
        pytest.param("01", id="leading-zero-one"),
        pytest.param("001", id="leading-zero-many"),
        pytest.param("42", id="decimal"),
        pytest.param("0x2A", id="hex-upper"),
        pytest.param("0xff", id="hex-lower"),
        pytest.param(".5", id="float-leading-dot"),
        pytest.param("1.", id="float-trailing-dot"),
        pytest.param("1e-3", id="float-exp-negative"),
        pytest.param("2.5E+7", id="float-exp-positive"),
        pytest.param("x", id="name-x"),
        pytest.param("_x", id="name-underscore"),
        pytest.param("x1", id="name-digit-suffix"),
        pytest.param("counter_value", id="name-underscore-word"),
        pytest.param("pi", id="pi"),
        pytest.param("E", id="e"),
        pytest.param("tau", id="tau"),
        pytest.param("+x", id="unary-plus"),
        pytest.param("-x", id="unary-minus"),
        pytest.param("--x", id="double-unary"),
        pytest.param("-(x + 1)", id="unary-grouped"),
        pytest.param("a + b * c", id="precedence-mul"),
        pytest.param("a ** b ** c", id="right-pow"),
        pytest.param("a << b + c", id="shift-add"),
        pytest.param("a & b ^ c | d", id="bitwise-chain"),
        pytest.param("(a + b) * (c - d)", id="explicit-groups"),
        pytest.param("sin(x)", id="sin"),
        pytest.param("cos(x)", id="cos"),
        pytest.param("tan(x)", id="tan"),
        pytest.param("asin(x)", id="asin"),
        pytest.param("acos(x)", id="acos"),
        pytest.param("atan(x)", id="atan"),
        pytest.param("sinh(x)", id="sinh"),
        pytest.param("cosh(x)", id="cosh"),
        pytest.param("tanh(x)", id="tanh"),
        pytest.param("asinh(x)", id="asinh"),
        pytest.param("acosh(x)", id="acosh"),
        pytest.param("atanh(x)", id="atanh"),
        pytest.param("sqrt(x)", id="sqrt"),
        pytest.param("cbrt(x)", id="cbrt"),
        pytest.param("exp(x)", id="exp"),
        pytest.param("log(x)", id="log"),
        pytest.param("log10(x)", id="log10"),
        pytest.param("log2(x)", id="log2"),
        pytest.param("log1p(x)", id="log1p"),
        pytest.param("abs(-x)", id="abs"),
        pytest.param("ceil(x)", id="ceil"),
        pytest.param("floor(x)", id="floor"),
        pytest.param("round(x)", id="round"),
        pytest.param("trunc(x)", id="trunc"),
        pytest.param("sign(x)", id="sign"),
        pytest.param("(x > 0) ? 1 : 2", id="conditional"),
        pytest.param("((x + 1) >= y) ? (a + b) : (c * d)", id="conditional-complex"),
    ],
)
def test_fcstm_and_fbmcq_numeric_expression_ast_shapes_are_bidirectionally_aligned(
    expression,
):
    """Numeric expressions parse to ASTs that convert strictly both ways."""
    fcstm_node = parse_with_grammar_entry(expression, "num_expression")
    bmc_node = parse_bmc_num_expression(expression)

    converted_bmc = _fcstm_to_bmc_expr(fcstm_node, "num")
    converted_fcstm = _bmc_to_fcstm_expr(bmc_node)

    assert _shared_shape_from_bmc(converted_bmc) == _shared_shape_from_bmc(bmc_node)
    assert _shared_shape_from_fcstm(converted_fcstm, "num") == _shared_shape_from_fcstm(
        fcstm_node, "num"
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("true", id="true"),
        pytest.param("True", id="true-title"),
        pytest.param("TRUE", id="true-upper"),
        pytest.param("false", id="false"),
        pytest.param("False", id="false-title"),
        pytest.param("FALSE", id="false-upper"),
        pytest.param("x < y", id="lt"),
        pytest.param("x > y", id="gt"),
        pytest.param("x <= y", id="le"),
        pytest.param("x >= y", id="ge"),
        pytest.param("x == y", id="num-eq"),
        pytest.param("x != y", id="num-ne"),
        pytest.param("!(x > 0)", id="bang"),
        pytest.param("not (x > 0)", id="not-keyword"),
        pytest.param("x > 0 && y > 0", id="and-symbol"),
        pytest.param("x > 0 and y > 0", id="and-keyword"),
        pytest.param("x > 0 xor y > 0", id="xor"),
        pytest.param("x > 0 || y > 0", id="or-symbol"),
        pytest.param("x > 0 or y > 0", id="or-keyword"),
        pytest.param("x > 0 => y > 0", id="implies-symbol"),
        pytest.param("x > 0 implies y > 0", id="implies-keyword"),
        pytest.param("x > 0 iff y > 0", id="iff"),
        pytest.param("(x > 0) == (y > 0)", id="cond-eq"),
        pytest.param("(x > 0) != (y > 0)", id="cond-ne"),
        pytest.param("x > 0 => y > 0 => z > 0", id="right-implies"),
        pytest.param("(x > 0 && y > 0) || z > 0", id="group-left"),
        pytest.param("x > 0 && (y > 0 || z > 0)", id="group-right"),
        pytest.param("(x > 0) ? true : false", id="conditional-bool"),
        pytest.param(
            "(x > 0) ? (y > 0 && z > 0) : (a <= b)",
            id="conditional-complex",
        ),
    ],
)
def test_fcstm_and_fbmcq_condition_expression_ast_shapes_are_bidirectionally_aligned(
    expression,
):
    """Condition expressions parse to ASTs that convert strictly both ways."""
    fcstm_node = parse_with_grammar_entry(expression, "cond_expression")
    bmc_node = parse_bmc_cond_expression(expression)

    converted_bmc = _fcstm_to_bmc_expr(fcstm_node, "cond")
    converted_fcstm = _bmc_to_fcstm_expr(bmc_node)

    assert _shared_shape_from_bmc(converted_bmc) == _shared_shape_from_bmc(bmc_node)
    assert _shared_shape_from_fcstm(
        converted_fcstm, "cond"
    ) == _shared_shape_from_fcstm(fcstm_node, "cond")


@pytest.mark.unittest
def test_bmc_boolean_raw_spellings_are_preserved_beyond_fcstm_parity_shape():
    """FBMCQ keeps boolean spelling even though FCSTM normalizes raw casing."""
    assert parse_bmc_cond_expression("True").to_canonical()["raw"] == "True"
    assert parse_bmc_cond_expression("TRUE").to_canonical()["raw"] == "TRUE"
    assert parse_bmc_cond_expression("False").to_canonical()["raw"] == "False"
    assert parse_bmc_cond_expression("FALSE").to_canonical()["raw"] == "FALSE"


@pytest.mark.unittest
def test_parity_projection_rejects_non_fcstm_bmc_atoms():
    """Bidirectional parity helpers intentionally reject BMC-only atoms."""
    with pytest.raises(TypeError, match="Unsupported BMC parity expression"):
        _bmc_to_fcstm_expr(bmc_nodes.Cycle())

    with pytest.raises(TypeError, match="Unsupported FCSTM parity expression"):
        _fcstm_to_bmc_expr(cast(fcstm_nodes.Expr, fcstm_nodes.ASTNode()), "num")
