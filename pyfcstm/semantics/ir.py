"""
Canonical intermediate representation for FCSTM expressions and operations.

Adapters translate a host syntax tree, such as model expressions or FBMCQ
query expressions, into these immutable nodes.  The execution engine only
walks this representation, so every host language shares one implementation
of evaluation order, short-circuiting and branch selection.

The module contains:

* :class:`Node` - Base class carrying a stable identifier and the origin object.
* :class:`Literal`, :class:`Symbol`, :class:`Unary`, :class:`Binary`,
  :class:`Conditional`, :class:`Call`, :class:`HostAtom` - Expression nodes.
* :class:`Assign`, :class:`Arm`, :class:`If` - Operation statement nodes.

Example::

    >>> from pyfcstm.semantics.ir import Binary, Literal, Symbol
    >>> node = Binary("e", None, "+", Symbol("e.0", None, "x"), Literal("e.1", None, 1))
    >>> node.op, node.left.reference, node.right.value
    ('+', 'x', 1)
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, Union

__all__ = [
    "Node",
    "Expr",
    "Literal",
    "Symbol",
    "Unary",
    "Binary",
    "Conditional",
    "Call",
    "HostAtom",
    "Stmt",
    "Assign",
    "Arm",
    "If",
]


@dataclass(frozen=True)
class Node:
    """
    Base class of every IR node.

    :param node_id: Stable path identifier assigned by the adapter, such as
        ``"guard.1.0"``.
    :type node_id: str
    :param origin: Host object the node was built from; kept for provenance
        and never compared.
    :type origin: object
    """

    node_id: str
    origin: object = field(compare=False, repr=False)


@dataclass(frozen=True)
class Expr(Node):
    """Base class of expression nodes."""


@dataclass(frozen=True)
class Literal(Expr):
    """
    A boolean, integer or float constant.

    :param value: The constant value.
    :type value: Union[bool, int, float]
    """

    value: Union[bool, int, float] = 0


@dataclass(frozen=True)
class Symbol(Expr):
    """
    A reference resolved by the interpretation, such as a variable name.

    :param reference: Hashable host reference, a variable name for model
        expressions.
    :type reference: object
    """

    reference: object = None


@dataclass(frozen=True)
class Unary(Expr):
    """
    A unary operator application.

    :param op: Canonical catalog token: ``"unary+"``, ``"unary-"`` or ``"!"``.
    :type op: str
    :param operand: The operand.
    :type operand: Expr
    """

    op: str = ""
    operand: Optional[Expr] = None


@dataclass(frozen=True)
class Binary(Expr):
    """
    A binary operator application.

    :param op: Canonical catalog token such as ``"+"`` or ``"&&"``.
    :type op: str
    :param left: Left operand.
    :type left: Expr
    :param right: Right operand.
    :type right: Expr
    """

    op: str = ""
    left: Optional[Expr] = None
    right: Optional[Expr] = None


@dataclass(frozen=True)
class Conditional(Expr):
    """
    The conditional operator ``test ? if_true : if_false``.

    :param test: Condition.
    :type test: Expr
    :param if_true: Value when the condition holds.
    :type if_true: Expr
    :param if_false: Value when the condition does not hold.
    :type if_false: Expr
    """

    test: Optional[Expr] = None
    if_true: Optional[Expr] = None
    if_false: Optional[Expr] = None


@dataclass(frozen=True)
class Call(Expr):
    """
    A math function call.

    :param func: Function name.
    :type func: str
    :param args: Arguments.
    :type args: Tuple[Expr, ...]
    """

    func: str = ""
    args: Tuple[Expr, ...] = ()


@dataclass(frozen=True)
class HostAtom(Expr):
    """
    A host-specific leaf whose meaning a host extension supplies.

    :param key: Namespaced key such as ``"fbmcq.active"``.
    :type key: str
    :param payload: Host data needed to resolve the atom; never compared.
    :type payload: object
    :param args: Sub-expressions evaluated before the atom is resolved.
    :type args: Tuple[Expr, ...]
    """

    key: str = ""
    payload: object = field(default=None, compare=False, repr=False)
    args: Tuple[Expr, ...] = ()


@dataclass(frozen=True)
class Stmt(Node):
    """Base class of operation statement nodes."""


@dataclass(frozen=True)
class Assign(Stmt):
    """
    Assignment of an expression to a variable.

    :param target: Assigned variable name.
    :type target: str
    :param value: Assigned expression.
    :type value: Expr
    """

    target: str = ""
    value: Optional[Expr] = None


@dataclass(frozen=True)
class Arm(Node):
    """
    One branch of an ``if`` statement.

    :param test: Branch condition, or ``None`` for ``else``.
    :type test: Optional[Expr]
    :param body: Statements executed when the branch is selected.
    :type body: Tuple[Stmt, ...]
    """

    test: Optional[Expr] = None
    body: Tuple[Stmt, ...] = ()


@dataclass(frozen=True)
class If(Stmt):
    """
    An ``if`` / ``else if`` / ``else`` statement; the first matching arm runs.

    :param arms: Branches in source order.
    :type arms: Tuple[Arm, ...]
    """

    arms: Tuple[Arm, ...] = ()
