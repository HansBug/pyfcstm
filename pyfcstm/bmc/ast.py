"""Typed expression data model for FCSTM BMC queries.

This module defines the parser-independent expression objects used by
``*.fbmcq`` queries.  The core expression nodes intentionally mirror the
current FCSTM numeric and condition expression split, while BMC-only nodes add
frame, cycle, active-state, event, case, and abstract-call atoms.  The objects
are frozen dataclasses and expose :meth:`BmcExpr.to_canonical` so later parser
parity tests can compare FCSTM and FBMCQ expressions through a stable,
language-neutral shape.

Design contracts:

* Expression nodes are data-only; they do not bind names, inspect models, or
  lower anything to Z3.
* :func:`str` on every concrete expression returns canonical ``.fbmcq`` DSL
  text.  This is the object-to-text half of the query round-trip contract.
* :func:`repr` stays the dataclass-generated debugging representation and must
  not be rewritten into DSL text.
* Numeric and condition expression categories stay separate at construction
  time, matching FCSTM ``num_expression`` and ``cond_expression``.

The module contains:

* :class:`BmcNumExpr` and :class:`BmcCondExpr` - Typed numeric and condition
  expression bases.
* FCSTM-compatible nodes such as :class:`IntLiteral`, :class:`NameRef`,
  :class:`NumBinaryOp`, :class:`NumericComparison`, and :class:`CondBinaryOp`.
* BMC-only extension nodes such as :class:`FrameVar`, :class:`Cycle`,
  :class:`Active`, :class:`Event`, :class:`Case`, and :class:`Called`.

Example::

    >>> from pyfcstm.bmc.ast import Active, IntLiteral, NameRef, NumericComparison
    >>> expr = NumericComparison(NameRef("x"), "<=", IntLiteral("3"))
    >>> expr.to_canonical()["op"]
    '<='
    >>> isinstance(Active("Root.Idle"), BmcCondExpr)
    True
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Union

from pyfcstm.bmc.errors import InvalidBmcQuery

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

FrameSelector = Union[int, Literal["current"]]
CanonicalDict = Dict[str, Any]

_DECIMAL_INT_RE = re.compile(r"^[0-9]+$")
_HEX_INT_RE = re.compile(r"^0x[0-9a-fA-F]+$")
_FLOAT_RE = re.compile(
    r"^(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"
    r"|^[0-9]+[eE][+-]?[0-9]+$"
)
_ID_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_FCSTM_RESERVED_NAMES = {
    "import",
    "def",
    "event",
    "as",
    "named",
    "pseudo",
    "state",
    "enter",
    "exit",
    "during",
    "before",
    "after",
    "abstract",
    "ref",
    "effect",
    "if",
    "else",
    "int",
    "float",
    "pi",
    "E",
    "tau",
    "and",
    "or",
    "not",
    "xor",
    "implies",
    "iff",
    "True",
    "true",
    "TRUE",
    "False",
    "false",
    "FALSE",
}
_FBMCQ_RESERVED_NAMES = {
    "init",
    "cold",
    "terminated",
    "assume",
    "always",
    "at",
    "events",
    "cardinality",
    "any",
    "at_most_one",
    "check",
    "reach",
    "forbid",
    "invariant",
    "must_reach",
    "exists_always",
    "response",
    "cover",
    "trigger",
    "within",
    "current",
    "var",
    "cycle",
    "active",
    "case",
    "called",
}
_BARE_NAME_RESERVED = _FCSTM_RESERVED_NAMES | _FBMCQ_RESERVED_NAMES

_NUM_UNARY_OPS = {"+", "-"}
_NUM_BINARY_OPS = {"**", "*", "/", "%", "+", "-", "<<", ">>", "&", "^", "|"}
_NUM_COMPARISON_OPS = {"<", ">", "<=", ">=", "==", "!="}
_COND_UNARY_ALIASES = {"not": "!"}
_COND_UNARY_OPS = {"!"}
_COND_BINARY_ALIASES = {
    "and": "&&",
    "or": "||",
    "implies": "=>",
}
_COND_BINARY_OPS = {"==", "!=", "iff", "&&", "xor", "||", "=>"}
_MATH_CONSTANTS = {"pi", "E", "tau"}
_UFUNC_NAMES = {
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
    "abs",
    "ceil",
    "floor",
    "round",
    "trunc",
    "sign",
}


class BmcExpr:
    """Base class for every BMC query expression node.

    Concrete subclasses provide a stable canonical form for tests, parser
    handoff, and later binder diagnostics.  The canonical form contains only
    plain dictionaries, tuples, strings, booleans, integers, floats, and
    ``None`` so it can be serialized or compared without importing grammar
    classes.

    :cvar _node_name: Canonical node tag emitted by
        :meth:`BmcExpr.to_canonical`.
    :type _node_name: str

    Example::

        >>> from pyfcstm.bmc.ast import IntLiteral
        >>> IntLiteral("7").to_canonical()["node"]
        'int_literal'
    """

    _node_name: ClassVar[str] = "expr"

    def to_canonical(self) -> CanonicalDict:
        """Return a language-neutral canonical expression shape.

        :return: Canonical dictionary for this node.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.ast import BoolLiteral
            >>> BoolLiteral("true").to_canonical()["value"]
            True
        """
        result = {"node": self._node_name}
        result.update(self._canonical_payload())
        return result

    def __str__(self) -> str:
        """Return the canonical ``.fbmcq`` DSL spelling for this expression.

        :return: Query DSL text that can be parsed back into this expression
            shape.
        :rtype: str

        Example::

            >>> from pyfcstm.bmc.ast import IntLiteral
            >>> str(IntLiteral("7"))
            '7'
        """
        return self._to_dsl()

    def _canonical_payload(self) -> CanonicalDict:
        raise NotImplementedError  # pragma: no cover

    def _to_dsl(self) -> str:
        raise NotImplementedError  # pragma: no cover


class BmcNumExpr(BmcExpr):
    """Base class for numeric BMC expressions.

    Numeric expressions follow FCSTM ``num_expression`` shape and represent
    integer, float, variable, frame-variable, cycle, and arithmetic operator
    values.

    Example::

        >>> from pyfcstm.bmc.ast import BmcNumExpr, Cycle
        >>> isinstance(Cycle(), BmcNumExpr)
        True
    """


class BmcCondExpr(BmcExpr):
    """Base class for condition BMC expressions.

    Condition expressions follow FCSTM ``cond_expression`` shape and represent
    boolean literals, comparisons, logical operators, active-state atoms, event
    atoms, selected-case atoms, and abstract-call atoms.

    Example::

        >>> from pyfcstm.bmc.ast import Active, BmcCondExpr
        >>> isinstance(Active("Root.A"), BmcCondExpr)
        True
    """


def _canonical_expr(expr: BmcExpr) -> CanonicalDict:
    return expr.to_canonical()


def _require_instance(value: object, expected_type: type, field_name: str) -> None:
    if not isinstance(value, expected_type):
        raise TypeError(f"{field_name} must be {expected_type.__name__}.")


def _validate_choice(value: str, choices: set, field_name: str) -> None:
    if value not in choices:
        raise ValueError(f"Unsupported {field_name}: {value!r}.")


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string.")


def _normalize_frame(frame: FrameSelector, field_name: str = "frame") -> FrameSelector:
    if frame == "current":
        return frame
    if isinstance(frame, bool) or not isinstance(frame, int):
        raise InvalidBmcQuery(
            f"{field_name} must be a non-negative integer or 'current'."
        )
    if frame < 0:
        raise InvalidBmcQuery(
            f"{field_name} must be a non-negative integer or 'current'."
        )
    return frame


def _quote_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _frame_to_dsl(frame: FrameSelector) -> str:
    return "current" if frame == "current" else str(frame)


def _call_args_to_dsl(*args: str) -> str:
    return ", ".join(args)


def _optional_frame_call_to_dsl(name: str, first_arg: str, frame: FrameSelector) -> str:
    if frame == "current":
        return "%s(%s)" % (name, first_arg)
    return "%s(%s)" % (name, _call_args_to_dsl(first_arg, _frame_to_dsl(frame)))


def _optional_unit_frame_call_to_dsl(name: str, frame: FrameSelector) -> str:
    if frame == "current":
        return "%s()" % name
    return "%s(%s)" % (name, _frame_to_dsl(frame))


def _grouped(text: str) -> str:
    return "(%s)" % text


def _num_operand_to_dsl(expr: BmcNumExpr) -> str:
    if isinstance(
        expr,
        (IntLiteral, FloatLiteral, NameRef, MathConst, UFuncCall, FrameVar, Cycle),
    ):
        return str(expr)
    return _grouped(str(expr))


def _cond_operand_to_dsl(expr: BmcCondExpr) -> str:
    if isinstance(
        expr,
        (
            BoolLiteral,
            NumericComparison,
            CondUnaryOp,
            Active,
            Terminated,
            Event,
            Case,
            Called,
        ),
    ):
        return str(expr)
    return _grouped(str(expr))


def _cond_unary_operand_to_dsl(expr: BmcCondExpr) -> str:
    if isinstance(expr, (BoolLiteral, Active, Terminated, Event, Case, Called)):
        return str(expr)
    return _grouped(str(expr))


@dataclass(frozen=True)
class IntLiteral(BmcNumExpr):
    """Integer literal preserving raw token, numeric value, and literal kind.

    :param raw: Raw integer token text such as ``"42"`` or ``"0x2A"``.
    :type raw: str
    :param kind: Literal kind, either ``"decimal"`` or ``"hex"``. If the raw
        value starts with ``0x``, the kind is normalized to ``"hex"``.
    :type kind: str, optional

    Example::

        >>> IntLiteral("0x2A").to_canonical()["kind"]
        'hex'
    """

    _node_name: ClassVar[str] = "int_literal"

    raw: str
    kind: str = "decimal"

    def __post_init__(self) -> None:
        _require_non_empty_string(self.raw, "raw")
        kind = "hex" if self.raw.startswith("0x") else self.kind
        _validate_choice(kind, {"decimal", "hex"}, "integer literal kind")
        if kind == "hex":
            if not _HEX_INT_RE.match(self.raw):
                raise ValueError(
                    f"Invalid FCSTM hexadecimal integer literal: {self.raw!r}."
                )
        elif not _DECIMAL_INT_RE.match(self.raw):
            raise ValueError(f"Invalid FCSTM decimal integer literal: {self.raw!r}.")
        object.__setattr__(self, "kind", kind)

    @property
    def value(self) -> int:
        """Return the integer value represented by ``raw``.

        :return: Parsed integer value.
        :rtype: int

        Example::

            >>> IntLiteral("0x10").value
            16
        """
        return int(self.raw, 16 if self.kind == "hex" else 10)

    def _canonical_payload(self) -> CanonicalDict:
        return {"kind": self.kind, "raw": self.raw, "value": self.value}

    def _to_dsl(self) -> str:
        return self.raw


@dataclass(frozen=True)
class FloatLiteral(BmcNumExpr):
    """Floating-point literal preserving the raw token text.

    :param raw: Raw floating-point token text.
    :type raw: str

    Example::

        >>> FloatLiteral("1e2").to_canonical()["value"]
        100.0
    """

    _node_name: ClassVar[str] = "float_literal"

    raw: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.raw, "raw")
        if not _FLOAT_RE.match(self.raw):
            raise ValueError(f"Invalid FCSTM floating-point literal: {self.raw!r}.")

    @property
    def value(self) -> float:
        """Return the floating-point value represented by ``raw``.

        :return: Parsed float value.
        :rtype: float

        Example::

            >>> FloatLiteral("3.5").value
            3.5
        """
        return float(self.raw)

    def _canonical_payload(self) -> CanonicalDict:
        return {"kind": "float", "raw": self.raw, "value": self.value}

    def _to_dsl(self) -> str:
        return self.raw


@dataclass(frozen=True)
class BoolLiteral(BmcCondExpr):
    """Boolean literal preserving raw spelling and normalized value.

    :param raw: Raw boolean token text such as ``"true"`` or ``"FALSE"``.
    :type raw: str

    Example::

        >>> BoolLiteral("FALSE").to_canonical()["value"]
        False
    """

    _node_name: ClassVar[str] = "bool_literal"

    raw: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.raw, "raw")
        if self.raw not in {"true", "True", "TRUE", "false", "False", "FALSE"}:
            raise ValueError(f"Unsupported FCSTM boolean literal: {self.raw!r}.")

    @property
    def value(self) -> bool:
        """Return the boolean value represented by ``raw``.

        :return: Parsed boolean value.
        :rtype: bool

        Example::

            >>> BoolLiteral("True").value
            True
        """
        return self.raw.lower() == "true"

    def _canonical_payload(self) -> CanonicalDict:
        return {"kind": "bool", "raw": self.raw, "value": self.value}

    def _to_dsl(self) -> str:
        return self.raw


@dataclass(frozen=True)
class NameRef(BmcNumExpr):
    """Bare FCSTM variable reference used as a numeric expression.

    :param name: Variable name from the query expression.
    :type name: str

    Example::

        >>> NameRef("counter").to_canonical()
        {'node': 'name', 'name': 'counter'}
    """

    _node_name: ClassVar[str] = "name"

    name: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.name, "name")
        if not _ID_RE.match(self.name):
            raise ValueError(f"Invalid FCSTM identifier: {self.name!r}.")
        if self.name in _BARE_NAME_RESERVED or self.name in _UFUNC_NAMES:
            raise ValueError(f"Reserved bare expression name: {self.name!r}.")

    def _canonical_payload(self) -> CanonicalDict:
        return {"name": self.name}

    def _to_dsl(self) -> str:
        return self.name


@dataclass(frozen=True)
class MathConst(BmcNumExpr):
    """FCSTM mathematical constant expression.

    :param name: Constant name, one of ``"pi"``, ``"E"``, or ``"tau"``.
    :type name: str

    Example::

        >>> MathConst("pi").to_canonical()["name"]
        'pi'
    """

    _node_name: ClassVar[str] = "math_const"

    name: str

    def __post_init__(self) -> None:
        _validate_choice(self.name, _MATH_CONSTANTS, "math constant")

    def _canonical_payload(self) -> CanonicalDict:
        return {"name": self.name}

    def _to_dsl(self) -> str:
        return self.name


@dataclass(frozen=True)
class NumUnaryOp(BmcNumExpr):
    """Numeric unary operator expression.

    :param op: Unary operator, either ``"+"`` or ``"-"``.
    :type op: str
    :param operand: Numeric operand.
    :type operand: BmcNumExpr

    Example::

        >>> NumUnaryOp("-", NameRef("x")).to_canonical()["op"]
        '-'
    """

    _node_name: ClassVar[str] = "num_unary"

    op: str
    operand: BmcNumExpr

    def __post_init__(self) -> None:
        _validate_choice(self.op, _NUM_UNARY_OPS, "numeric unary operator")
        _require_instance(self.operand, BmcNumExpr, "operand")

    def _canonical_payload(self) -> CanonicalDict:
        return {"op": self.op, "operand": _canonical_expr(self.operand)}

    def _to_dsl(self) -> str:
        return "%s%s" % (self.op, _num_operand_to_dsl(self.operand))


@dataclass(frozen=True)
class NumBinaryOp(BmcNumExpr):
    """Numeric binary operator expression.

    :param left: Left numeric operand.
    :type left: BmcNumExpr
    :param op: Numeric operator following FCSTM grammar spelling.
    :type op: str
    :param right: Right numeric operand.
    :type right: BmcNumExpr

    Example::

        >>> NumBinaryOp(NameRef("x"), "+", IntLiteral("1")).to_canonical()["op"]
        '+'
    """

    _node_name: ClassVar[str] = "num_binary"

    left: BmcNumExpr
    op: str
    right: BmcNumExpr

    def __post_init__(self) -> None:
        _require_instance(self.left, BmcNumExpr, "left")
        _require_instance(self.right, BmcNumExpr, "right")
        _validate_choice(self.op, _NUM_BINARY_OPS, "numeric binary operator")

    def _canonical_payload(self) -> CanonicalDict:
        return {
            "op": self.op,
            "left": _canonical_expr(self.left),
            "right": _canonical_expr(self.right),
        }

    def _to_dsl(self) -> str:
        return "%s %s %s" % (
            _num_operand_to_dsl(self.left),
            self.op,
            _num_operand_to_dsl(self.right),
        )


@dataclass(frozen=True)
class NumConditionalOp(BmcNumExpr):
    """Numeric conditional expression with a condition selector.

    :param condition: Condition deciding which branch is selected.
    :type condition: BmcCondExpr
    :param if_true: Numeric expression used when ``condition`` is true.
    :type if_true: BmcNumExpr
    :param if_false: Numeric expression used when ``condition`` is false.
    :type if_false: BmcNumExpr

    Example::

        >>> NumConditionalOp(BoolLiteral("true"), IntLiteral("1"), IntLiteral("0")).to_canonical()["node"]
        'num_conditional'
    """

    _node_name: ClassVar[str] = "num_conditional"

    condition: BmcCondExpr
    if_true: BmcNumExpr
    if_false: BmcNumExpr

    def __post_init__(self) -> None:
        _require_instance(self.condition, BmcCondExpr, "condition")
        _require_instance(self.if_true, BmcNumExpr, "if_true")
        _require_instance(self.if_false, BmcNumExpr, "if_false")

    def _canonical_payload(self) -> CanonicalDict:
        return {
            "condition": _canonical_expr(self.condition),
            "if_true": _canonical_expr(self.if_true),
            "if_false": _canonical_expr(self.if_false),
        }

    def _to_dsl(self) -> str:
        return "(%s) ? %s : %s" % (
            self.condition,
            _num_operand_to_dsl(self.if_true),
            _num_operand_to_dsl(self.if_false),
        )


@dataclass(frozen=True)
class UFuncCall(BmcNumExpr):
    """FCSTM unary math function call.

    :param func: Function name from FCSTM ``UFUNC_NAME``.
    :type func: str
    :param operand: Numeric function argument.
    :type operand: BmcNumExpr

    Example::

        >>> UFuncCall("sqrt", NameRef("x")).to_canonical()["func"]
        'sqrt'
    """

    _node_name: ClassVar[str] = "ufunc"

    func: str
    operand: BmcNumExpr

    def __post_init__(self) -> None:
        _validate_choice(self.func, _UFUNC_NAMES, "ufunc")
        _require_instance(self.operand, BmcNumExpr, "operand")

    def _canonical_payload(self) -> CanonicalDict:
        return {"func": self.func, "operand": _canonical_expr(self.operand)}

    def _to_dsl(self) -> str:
        return "%s(%s)" % (self.func, self.operand)


@dataclass(frozen=True)
class CondUnaryOp(BmcCondExpr):
    """Condition unary operator expression.

    :param op: Unary condition operator, ``"!"`` or alias ``"not"``.
    :type op: str
    :param operand: Condition operand.
    :type operand: BmcCondExpr

    Example::

        >>> CondUnaryOp("not", BoolLiteral("true")).to_canonical()["op"]
        '!'
    """

    _node_name: ClassVar[str] = "cond_unary"

    op: str
    operand: BmcCondExpr

    def __post_init__(self) -> None:
        op = _COND_UNARY_ALIASES.get(self.op, self.op)
        _validate_choice(op, _COND_UNARY_OPS, "condition unary operator")
        _require_instance(self.operand, BmcCondExpr, "operand")
        object.__setattr__(self, "op", op)

    def _canonical_payload(self) -> CanonicalDict:
        return {"op": self.op, "operand": _canonical_expr(self.operand)}

    def _to_dsl(self) -> str:
        return "%s%s" % (self.op, _cond_unary_operand_to_dsl(self.operand))


@dataclass(frozen=True)
class NumericComparison(BmcCondExpr):
    """Comparison between two numeric expressions.

    :param left: Left numeric operand.
    :type left: BmcNumExpr
    :param op: Comparison operator.
    :type op: str
    :param right: Right numeric operand.
    :type right: BmcNumExpr

    Example::

        >>> NumericComparison(NameRef("x"), "<", IntLiteral("2")).to_canonical()["op"]
        '<'
    """

    _node_name: ClassVar[str] = "numeric_comparison"

    left: BmcNumExpr
    op: str
    right: BmcNumExpr

    def __post_init__(self) -> None:
        _require_instance(self.left, BmcNumExpr, "left")
        _require_instance(self.right, BmcNumExpr, "right")
        _validate_choice(self.op, _NUM_COMPARISON_OPS, "numeric comparison operator")

    def _canonical_payload(self) -> CanonicalDict:
        return {
            "op": self.op,
            "left": _canonical_expr(self.left),
            "right": _canonical_expr(self.right),
        }

    def _to_dsl(self) -> str:
        return "%s %s %s" % (
            _num_operand_to_dsl(self.left),
            self.op,
            _num_operand_to_dsl(self.right),
        )


@dataclass(frozen=True)
class CondBinaryOp(BmcCondExpr):
    """Condition binary operator expression.

    :param left: Left condition operand.
    :type left: BmcCondExpr
    :param op: Condition operator or FCSTM alias.
    :type op: str
    :param right: Right condition operand.
    :type right: BmcCondExpr

    Example::

        >>> CondBinaryOp(BoolLiteral("true"), "and", BoolLiteral("false")).to_canonical()["op"]
        '&&'
    """

    _node_name: ClassVar[str] = "cond_binary"

    left: BmcCondExpr
    op: str
    right: BmcCondExpr

    def __post_init__(self) -> None:
        op = _COND_BINARY_ALIASES.get(self.op, self.op)
        _require_instance(self.left, BmcCondExpr, "left")
        _require_instance(self.right, BmcCondExpr, "right")
        _validate_choice(op, _COND_BINARY_OPS, "condition binary operator")
        object.__setattr__(self, "op", op)

    def _canonical_payload(self) -> CanonicalDict:
        return {
            "op": self.op,
            "left": _canonical_expr(self.left),
            "right": _canonical_expr(self.right),
        }

    def _to_dsl(self) -> str:
        return "%s %s %s" % (
            _cond_operand_to_dsl(self.left),
            self.op,
            _cond_operand_to_dsl(self.right),
        )


@dataclass(frozen=True)
class CondConditionalOp(BmcCondExpr):
    """Condition conditional expression.

    :param condition: Condition deciding which branch is selected.
    :type condition: BmcCondExpr
    :param if_true: Condition expression used when ``condition`` is true.
    :type if_true: BmcCondExpr
    :param if_false: Condition expression used when ``condition`` is false.
    :type if_false: BmcCondExpr

    Example::

        >>> CondConditionalOp(BoolLiteral("true"), BoolLiteral("true"), BoolLiteral("false")).to_canonical()["node"]
        'cond_conditional'
    """

    _node_name: ClassVar[str] = "cond_conditional"

    condition: BmcCondExpr
    if_true: BmcCondExpr
    if_false: BmcCondExpr

    def __post_init__(self) -> None:
        _require_instance(self.condition, BmcCondExpr, "condition")
        _require_instance(self.if_true, BmcCondExpr, "if_true")
        _require_instance(self.if_false, BmcCondExpr, "if_false")

    def _canonical_payload(self) -> CanonicalDict:
        return {
            "condition": _canonical_expr(self.condition),
            "if_true": _canonical_expr(self.if_true),
            "if_false": _canonical_expr(self.if_false),
        }

    def _to_dsl(self) -> str:
        return "(%s) ? %s : %s" % (
            self.condition,
            _cond_operand_to_dsl(self.if_true),
            _cond_operand_to_dsl(self.if_false),
        )


@dataclass(frozen=True)
class FrameVar(BmcNumExpr):
    """Numeric reference produced by the query-level ``var("...")`` atom.

    The query AST is frame-relative rather than solver-frame-indexed.  Later
    binder and lowering phases decide which concrete frame a ``var("x")``
    expression reads from.  The spelling field distinguishes this explicit
    query atom from a bare :class:`NameRef` that still follows FCSTM ``ID``
    lexical rules.

    :param name: Persistent variable name carried by ``var("...")``.
    :type name: str
    :param spelling: Query spelling family, defaults to ``"var_call"``.
    :type spelling: str, optional

    Example::

        >>> FrameVar("x").to_canonical()["spelling"]
        'var_call'
    """

    _node_name: ClassVar[str] = "frame_var"

    name: str
    spelling: str = "var_call"

    def __post_init__(self) -> None:
        _require_non_empty_string(self.name, "name")
        _validate_choice(self.spelling, {"var_call"}, "frame variable spelling")

    def _canonical_payload(self) -> CanonicalDict:
        return {"name": self.name, "spelling": self.spelling}

    def _to_dsl(self) -> str:
        return "var(%s)" % _quote_string(self.name)


@dataclass(frozen=True)
class Cycle(BmcNumExpr):
    """Built-in numeric cycle expression for query predicates.

    Example::

        >>> Cycle().to_canonical()
        {'node': 'cycle'}
    """

    _node_name: ClassVar[str] = "cycle"

    def _canonical_payload(self) -> CanonicalDict:
        return {}

    def _to_dsl(self) -> str:
        return "cycle"


@dataclass(frozen=True)
class Active(BmcCondExpr):
    """Boolean atom stating that a state is active at a frame.

    :param state_path: Fully qualified or query-local state path string.
    :type state_path: str
    :param frame: Frame index or ``"current"``, defaults to ``"current"``.
    :type frame: int or str, optional

    Example::

        >>> Active("Root.Idle").to_canonical()["frame"]
        'current'
    """

    _node_name: ClassVar[str] = "active"

    state_path: str
    frame: FrameSelector = "current"

    def __post_init__(self) -> None:
        _require_non_empty_string(self.state_path, "state_path")
        object.__setattr__(self, "frame", _normalize_frame(self.frame))

    def _canonical_payload(self) -> CanonicalDict:
        return {"state_path": self.state_path, "frame": self.frame}

    def _to_dsl(self) -> str:
        return _optional_frame_call_to_dsl(
            "active", _quote_string(self.state_path), self.frame
        )


@dataclass(frozen=True)
class Terminated(BmcCondExpr):
    """Boolean atom stating that execution is terminated at a frame.

    :param frame: Frame index or ``"current"``, defaults to ``"current"``.
    :type frame: int or str, optional

    Example::

        >>> Terminated().to_canonical()["node"]
        'terminated'
    """

    _node_name: ClassVar[str] = "terminated"

    frame: FrameSelector = "current"

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame", _normalize_frame(self.frame))

    def _canonical_payload(self) -> CanonicalDict:
        return {"frame": self.frame}

    def _to_dsl(self) -> str:
        return _optional_unit_frame_call_to_dsl("terminated", self.frame)


@dataclass(frozen=True)
class Event(BmcCondExpr):
    """Boolean atom stating that an event is selected for a query cycle.

    :param event_path: Fully qualified or query-local event path string.
    :type event_path: str
    :param selector: Concrete cycle index or ``"current"``, defaults to
        ``"current"``.
    :type selector: int or str, optional

    Example::

        >>> Event("Root.Idle.Start", selector=0).to_canonical()["event_path"]
        'Root.Idle.Start'
    """

    _node_name: ClassVar[str] = "event"

    event_path: str
    selector: FrameSelector = "current"

    def __post_init__(self) -> None:
        _require_non_empty_string(self.event_path, "event_path")
        object.__setattr__(
            self, "selector", _normalize_frame(self.selector, "selector")
        )

    def _canonical_payload(self) -> CanonicalDict:
        return {"event_path": self.event_path, "selector": self.selector}

    def _to_dsl(self) -> str:
        return "event(%s)" % _call_args_to_dsl(
            _quote_string(self.event_path), _frame_to_dsl(self.selector)
        )


@dataclass(frozen=True)
class Case(BmcCondExpr):
    """Boolean atom stating that a macro-step case is selected at a frame.

    :param label: Canonical macro-step case label.
    :type label: str
    :param frame: Frame index or ``"current"``, defaults to ``"current"``.
    :type frame: int or str, optional

    Example::

        >>> Case("Root.A::fallback::Root.A::0", frame=1).to_canonical()["frame"]
        1
    """

    _node_name: ClassVar[str] = "case"

    label: str
    frame: FrameSelector = "current"

    def __post_init__(self) -> None:
        _require_non_empty_string(self.label, "label")
        object.__setattr__(self, "frame", _normalize_frame(self.frame))

    def _canonical_payload(self) -> CanonicalDict:
        return {"label": self.label, "frame": self.frame}

    def _to_dsl(self) -> str:
        return _optional_frame_call_to_dsl(
            "case", _quote_string(self.label), self.frame
        )


@dataclass(frozen=True)
class Called(BmcCondExpr):
    """Boolean atom for future abstract-call tracking.

    :param name: Abstract action or hook name.
    :type name: str
    :param frame: Frame index or ``"current"``, defaults to ``"current"``.
    :type frame: int or str, optional

    Example::

        >>> Called("Check", frame=2).to_canonical()["name"]
        'Check'
    """

    _node_name: ClassVar[str] = "called"

    name: str
    frame: FrameSelector = "current"

    def __post_init__(self) -> None:
        _require_non_empty_string(self.name, "name")
        object.__setattr__(self, "frame", _normalize_frame(self.frame))

    def _canonical_payload(self) -> CanonicalDict:
        return {"name": self.name, "frame": self.frame}

    def _to_dsl(self) -> str:
        return _optional_frame_call_to_dsl(
            "called", _quote_string(self.name), self.frame
        )


__all__ = [
    "BmcExpr",
    "BmcNumExpr",
    "BmcCondExpr",
    "IntLiteral",
    "FloatLiteral",
    "BoolLiteral",
    "NameRef",
    "MathConst",
    "NumUnaryOp",
    "NumBinaryOp",
    "NumConditionalOp",
    "UFuncCall",
    "CondUnaryOp",
    "NumericComparison",
    "CondBinaryOp",
    "CondConditionalOp",
    "FrameVar",
    "Cycle",
    "Active",
    "Terminated",
    "Event",
    "Case",
    "Called",
]
