"""
Symbolic execution: the formal reference semantics on Z3 terms.

The symbolic interpretation evaluates expressions to Z3 terms with the
catalog's formal reference.  It never raises for a runtime error.  Every
operation records the condition under which it is well defined as a
:class:`DefinednessFact`, guarded by the conditions under which the operation
is actually evaluated: the right operand of ``x != 0 && 10 / x > 1`` records
``Implies(x != 0, x != 0)``-shaped facts, so short-circuiting is respected.
What a fact means is the caller's decision.  The solver and verify treat the
facts as definedness constraints, while BMC turns their negation into a
runtime-error state.

When asked, the interpretation also checks whether a lazily evaluated branch
can be reached and skips branches proved unreachable, recording every check
as a :class:`FeasibilityCheck`.

The module contains:

* :class:`SymbolicFailure` - Translation cannot continue.
* :class:`DefinednessFact` - The well-definedness condition of one operation.
* :class:`FeasibilityCheck` - One reachability check of a lazy branch.
* :class:`ConditionObservation` - A condition tested by a conditional expression.
* :class:`SymbolicSession` - Options and records of one translation.
* :class:`SymbolicContext` - The guards and path of the current evaluation point.
* :class:`SymbolicInterpretation` - The symbolic interpretation.
* :data:`SYMBOLIC` - The shared symbolic interpretation instance.
* :func:`translate` - Translate an IR expression in a new session.

Example::

    >>> import z3
    >>> from pyfcstm.model.expr import parse_expr
    >>> from pyfcstm.semantics.adapters import expression_from_model
    >>> from pyfcstm.semantics.symbolic import translate
    >>> x = z3.Int("x")
    >>> value, session = translate(expression_from_model(parse_expr("x == 0 || 10 / x > 1")), {"x": x})
    >>> value
    Or(0 == x, ToReal(1) < 10/ToReal(x))
    >>> [str(fact.constraint) for fact in session.definedness]
    ['Implies(Not(0 == x), x != 0)']
"""

import os
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

import z3

from . import ir
from .engine import OPERAND, Interpretation, compile_expression

__all__ = [
    "SymbolicFailure",
    "DefinednessFact",
    "FeasibilityCheck",
    "ConditionObservation",
    "SymbolicSession",
    "SymbolicContext",
    "SymbolicInterpretation",
    "SYMBOLIC",
    "translate",
]

#: Checker signature: ``check(facts, timeout_ms) -> "sat" | "unsat" | "unknown"``.
Checker = Callable[[Sequence[z3.ExprRef], Optional[int]], str]


class SymbolicFailure(Exception):
    """
    Translation cannot continue.

    :param kind: Failure kind: ``"not_implemented"``, ``"value_error"``,
        ``"type_error"``, ``"z3_error"`` or ``"no_reachable_branch"``.
    :type kind: str
    :param reason: Human-readable reason.
    :type reason: str
    :param error: Underlying exception, or ``None``.
    :type error: Optional[BaseException]
    :param node: IR node whose translation failed, or ``None``.
    :type node: Optional[pyfcstm.semantics.ir.Node]

    :ivar kind: Failure kind.
    :vartype kind: str
    :ivar reason: Human-readable reason.
    :vartype reason: str
    :ivar error: Underlying exception, or ``None``.
    :vartype error: Optional[BaseException]
    :ivar node: IR node whose translation failed, or ``None``.
    :vartype node: Optional[pyfcstm.semantics.ir.Node]

    Example::

        >>> from pyfcstm.semantics.symbolic import SymbolicFailure
        >>> SymbolicFailure("value_error", "bad").kind
        'value_error'
    """

    def __init__(
        self,
        kind: str,
        reason: str,
        error: Optional[BaseException] = None,
        node: Optional[ir.Node] = None,
    ):
        super().__init__(reason)
        self.kind = kind
        self.reason = reason
        self.error = error
        self.node = node


def _failure_from(error: BaseException, node: Optional[ir.Node] = None) -> SymbolicFailure:
    if isinstance(error, NotImplementedError):
        kind = "not_implemented"
    elif isinstance(error, ValueError):
        kind = "value_error"
    elif isinstance(error, TypeError):
        kind = "type_error"
    else:
        kind = "z3_error"
    return SymbolicFailure(kind, str(error), error, node)


@dataclass(frozen=True)
class DefinednessFact:
    """
    The well-definedness condition of one operation.

    :param constraint: :attr:`condition` guarded by every condition under
        which the operation is evaluated, as nested ``Implies``.
    :type constraint: z3.BoolRef
    :param condition: Condition under which the operation does not raise.
    :type condition: z3.BoolRef
    :param guards: Conditions under which the operation is evaluated, outer
        first.
    :type guards: Tuple[z3.BoolRef, ...]
    :param kind: Catalog error kind the condition rules out.
    :type kind: str
    :param node: IR node of the operation.
    :type node: pyfcstm.semantics.ir.Expr

    Example::

        >>> import z3
        >>> from pyfcstm.semantics.symbolic import DefinednessFact
        >>> x = z3.Int("x")
        >>> DefinednessFact(x != 0, x != 0, (), "division_by_zero", None).kind
        'division_by_zero'
    """

    constraint: z3.BoolRef
    condition: z3.BoolRef
    guards: Tuple[z3.BoolRef, ...]
    kind: str
    node: Any = field(compare=False, repr=False)


@dataclass(frozen=True)
class FeasibilityCheck:
    """
    One reachability check of a lazily evaluated branch.

    :param selector: Condition under which the branch is evaluated.
    :type selector: z3.BoolRef
    :param status: ``"sat"``, ``"unsat"`` or ``"unknown"``.
    :type status: str

    Example::

        >>> import z3
        >>> from pyfcstm.semantics.symbolic import FeasibilityCheck
        >>> FeasibilityCheck(z3.BoolVal(True), "sat").status
        'sat'
    """

    selector: z3.BoolRef
    status: str


@dataclass(frozen=True)
class ConditionObservation:
    """
    A condition tested by a conditional expression.

    :param node: IR node of the conditional expression.
    :type node: pyfcstm.semantics.ir.Conditional
    :param condition: Translated condition.
    :type condition: z3.BoolRef
    :param path: Conditions of the lazy regions enclosing the test.
    :type path: Tuple[z3.BoolRef, ...]
    :param definedness: Definedness constraints recorded before the test,
        including those of the condition itself, defaults to ``()``.
    :type definedness: Tuple[z3.BoolRef, ...], optional

    Example::

        >>> import z3
        >>> from pyfcstm.semantics.symbolic import ConditionObservation
        >>> ConditionObservation(None, z3.Bool("c"), ()).path
        ()
    """

    node: Any = field(compare=False, repr=False)
    condition: z3.BoolRef = None
    path: Tuple[z3.BoolRef, ...] = ()
    definedness: Tuple[z3.BoolRef, ...] = ()


@dataclass
class SymbolicSession:
    """
    Options and records of one symbolic translation.

    :param assumptions: Facts that hold for the whole translation, used by
        reachability checks, defaults to ``()``.
    :type assumptions: Sequence[z3.ExprRef], optional
    :param path_conditions: Conditions holding where the translation starts,
        used by reachability checks, defaults to ``()``.
    :type path_conditions: Sequence[z3.ExprRef], optional
    :param checker: Satisfiability checker for reachability, or ``None`` to
        evaluate every branch, defaults to ``None``.
    :type checker: Optional[Callable[[Sequence[z3.ExprRef], Optional[int]], str]], optional
    :param timeout_ms: Timeout passed to ``checker``, defaults to ``None``.
    :type timeout_ms: Optional[int], optional
    :param observe_conditions: Whether to record
        :class:`ConditionObservation` items, defaults to ``False``.
    :type observe_conditions: bool, optional
    :param track_definedness: Whether to record :class:`DefinednessFact`
        items; callers that only need values switch it off, defaults to
        ``True``.
    :type track_definedness: bool, optional

    :ivar definedness: Recorded definedness facts in evaluation order.
    :vartype definedness: List[DefinednessFact]
    :ivar checks: Recorded reachability checks in evaluation order.
    :vartype checks: List[FeasibilityCheck]
    :ivar conditions: Recorded condition observations in evaluation order.
    :vartype conditions: List[ConditionObservation]

    Example::

        >>> from pyfcstm.semantics.symbolic import SymbolicSession
        >>> SymbolicSession().definedness
        []
    """

    assumptions: Sequence[z3.ExprRef] = ()
    path_conditions: Sequence[z3.ExprRef] = ()
    checker: Optional[Checker] = None
    timeout_ms: Optional[int] = None
    observe_conditions: bool = False
    track_definedness: bool = True
    definedness: List[DefinednessFact] = field(default_factory=list)
    checks: List[FeasibilityCheck] = field(default_factory=list)
    conditions: List[ConditionObservation] = field(default_factory=list)

    def facts(self, path: Sequence[z3.ExprRef]) -> Tuple[z3.ExprRef, ...]:
        """
        Return every fact known at an evaluation point.

        :param path: Conditions of the lazy regions enclosing the point.
        :type path: Sequence[z3.ExprRef]
        :return: Assumptions, starting path conditions, ``path`` and every
            definedness constraint recorded so far.
        :rtype: Tuple[z3.ExprRef, ...]

        Example::

            >>> import z3
            >>> from pyfcstm.semantics.symbolic import SymbolicSession
            >>> SymbolicSession(assumptions=(z3.Bool("a"),)).facts((z3.Bool("p"),))
            (a, p)
        """
        return (
            *self.assumptions,
            *self.path_conditions,
            *path,
            *(fact.constraint for fact in self.definedness),
        )


@dataclass(frozen=True)
class SymbolicContext:
    """
    The guards and path of the current evaluation point.

    :param session: Session the evaluation belongs to.
    :type session: SymbolicSession
    :param guards: Conditions guarding definedness facts recorded here, outer
        first, defaults to ``()``.
    :type guards: Tuple[z3.BoolRef, ...], optional
    :param path: Conditions of every enclosing lazy region, outer first,
        defaults to ``()``.
    :type path: Tuple[z3.BoolRef, ...], optional

    Example::

        >>> from pyfcstm.semantics.symbolic import SymbolicContext, SymbolicSession
        >>> SymbolicContext(SymbolicSession()).guards
        ()
    """

    session: SymbolicSession
    guards: Tuple[z3.BoolRef, ...] = ()
    path: Tuple[z3.BoolRef, ...] = ()


def _guarded(condition: z3.BoolRef, guards: Sequence[z3.BoolRef]) -> z3.BoolRef:
    for guard in reversed(guards):
        condition = z3.Implies(guard, condition)
    return condition


def _skips(condition: z3.BoolRef) -> bool:
    # A literal false selector, or the negation of a literal true left operand
    # of ``||``, means the right operand is never evaluated.
    return z3.is_false(condition) or (z3.is_not(condition) and z3.is_true(condition.arg(0)))


class SymbolicInterpretation(Interpretation):
    """
    Symbolic interpretation: Z3 terms and the formal reference.

    Symbols are looked up in a mapping from names to Z3 terms.  The context
    passed to compiled expressions is a :class:`SymbolicContext`.  Host atoms
    are not supported; a host language subclasses the interpretation and
    overrides :meth:`host_atom`.

    Example::

        >>> import z3
        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.adapters import expression_from_model
        >>> from pyfcstm.semantics.symbolic import translate
        >>> translate(expression_from_model(parse_expr("x % -2")), {"x": z3.Int("x")})[0]
        If(-2 > 0, x%-2, If(x%-2 == 0, x%-2, x%-2 + -2))
    """

    def literal(self, node: ir.Literal) -> z3.ExprRef:
        value = node.value
        if isinstance(value, bool):
            return z3.BoolVal(value)
        if isinstance(value, int):
            return z3.IntVal(value)
        return z3.RealVal(value)

    def symbol(self, node: ir.Symbol, env: Mapping[str, z3.ExprRef], ctx: SymbolicContext) -> z3.ExprRef:
        if node.reference not in env:
            raise _failure_from(
                ValueError("Variable '%s' not found in z3_vars dictionary" % (node.reference,))
            )
        return env[node.reference]

    def apply(self, node: ir.Expr, spec, args: Sequence[z3.ExprRef], ctx: SymbolicContext) -> z3.ExprRef:
        if spec.symbolic is None:
            raise _failure_from(NotImplementedError(spec.unsupported), node)
        try:
            for rule in spec.errors if ctx.session.track_definedness else ():
                if rule.defined is not None:
                    condition = rule.defined(*args)
                    if not z3.is_true(condition):
                        ctx.session.definedness.append(
                            DefinednessFact(
                                _guarded(condition, ctx.guards),
                                condition,
                                ctx.guards,
                                rule.kind,
                                node,
                            )
                        )
            if spec.token == "**":
                _warn_power(node)
            return spec.symbolic(*args)
        except (NotImplementedError, ValueError, TypeError, z3.Z3Exception) as err:
            # NotImplementedError: an encoding that is intentionally absent;
            # ValueError: a logical operator received a non-Boolean operand;
            # TypeError and Z3Exception: Python or Z3 operators reject the
            # operand sorts, for example comparing a Bool with an Int.
            raise _failure_from(err, node) from err

    def unknown_operation(self, node: ir.Expr, args: Sequence[z3.ExprRef], ctx: SymbolicContext) -> z3.ExprRef:
        if isinstance(node, ir.Call):
            raise _failure_from(
                NotImplementedError(
                    "Mathematical function '%s' is not supported in Z3 conversion." % (node.func,)
                )
            )
        kind = "unary" if isinstance(node, ir.Unary) else "binary"
        raise _failure_from(ValueError("Unsupported %s operator: %s" % (kind, node.op)))

    def host_atom(self, node: ir.HostAtom, args, env, ctx: SymbolicContext) -> z3.ExprRef:
        raise _failure_from(ValueError("Unsupported host atom: %s" % (node.key,)))

    def truth(self, value: z3.ExprRef, node: ir.Node, ctx: SymbolicContext) -> z3.BoolRef:
        if isinstance(node, ir.Binary):
            if not z3.is_bool(value):
                raise _failure_from(
                    TypeError("Logical operator %r requires a Boolean left operand." % (node.op,))
                )
            return value
        # The test of a conditional expression.
        try:
            z3.Not(value)
        except (TypeError, z3.Z3Exception) as err:
            # TypeError and Z3Exception: a conditional test that is not a
            # Boolean term cannot select a branch.
            raise _failure_from(err) from err
        session = ctx.session
        if session.observe_conditions:
            session.conditions.append(
                ConditionObservation(
                    node,
                    value,
                    ctx.path,
                    tuple(fact.constraint for fact in session.definedness),
                )
            )
        return value

    def negate(self, condition: z3.BoolRef) -> z3.BoolRef:
        return z3.Not(condition)

    def decide(self, condition: z3.BoolRef, node: ir.Node, ctx: SymbolicContext, role: str) -> Optional[bool]:
        session = ctx.session
        if role == OPERAND and _skips(condition):
            return False
        if session.checker is None:
            return None
        status = session.checker((*session.facts(ctx.path), condition), session.timeout_ms)
        status = status if status in ("sat", "unsat") else "unknown"
        session.checks.append(FeasibilityCheck(condition, status))
        return False if status == "unsat" else None

    def enter(self, ctx: SymbolicContext, condition: z3.BoolRef, node: ir.Node, role: str, guard: bool) -> SymbolicContext:
        guards = ctx.guards
        if guard and not (role == OPERAND and z3.is_true(condition)):
            guards = (*guards, condition)
        return SymbolicContext(ctx.session, guards, (*ctx.path, condition))

    def constant(self, value: bool, node: ir.Expr) -> z3.BoolRef:
        return z3.BoolVal(value)

    def no_branch(self, node: ir.Conditional, ctx: SymbolicContext) -> z3.ExprRef:
        raise SymbolicFailure(
            "no_reachable_branch",
            "Conditional expression has no reachable value branch.",
        )


_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep


def _caller_stacklevel() -> int:
    # Point the warning at the first frame outside pyfcstm, the code that
    # asked for the translation, however deep the compiled closures nest.
    frame, level = sys._getframe(1), 1
    while frame is not None and os.path.abspath(frame.f_code.co_filename).startswith(_PACKAGE_ROOT):
        frame, level = frame.f_back, level + 1
    return level


def _warn_power(node: ir.Expr) -> None:
    # Z3's nonlinear arithmetic copes with ``x ** constant`` but struggles
    # with variable exponents, so callers are warned about the slow shapes.
    left_is_symbol = isinstance(node.left, ir.Symbol)
    right_is_symbol = isinstance(node.right, ir.Symbol)
    if left_is_symbol and right_is_symbol:
        message = (
            "Power operation with two variables (x ** y) may be very slow in Z3. "
            "Z3's nonlinear arithmetic solver has limited support for this pattern. "
            "Consider using alternative formulations or constraints if possible."
        )
    elif right_is_symbol:
        message = (
            "Power operation with variable exponent (constant ** x) may be slow in Z3. "
            "Performance depends on the solver's ability to handle exponential constraints."
        )
    else:
        return
    warnings.warn(message, UserWarning, stacklevel=_caller_stacklevel())


#: Shared symbolic interpretation instance.
SYMBOLIC = SymbolicInterpretation()


def translate(
    node: ir.Expr,
    env: Mapping[str, z3.ExprRef],
    session: Optional[SymbolicSession] = None,
    interpretation: Optional[SymbolicInterpretation] = None,
) -> Tuple[z3.ExprRef, SymbolicSession]:
    """
    Translate an IR expression to a Z3 term.

    :param node: Expression to translate.
    :type node: pyfcstm.semantics.ir.Expr
    :param env: Z3 terms by variable name.
    :type env: Mapping[str, z3.ExprRef]
    :param session: Session holding options and receiving records, defaults to
        a new session that evaluates every branch.
    :type session: Optional[SymbolicSession], optional
    :param interpretation: Interpretation to use, defaults to :data:`SYMBOLIC`.
    :type interpretation: Optional[SymbolicInterpretation], optional
    :return: The Z3 term and the session.
    :rtype: Tuple[z3.ExprRef, SymbolicSession]
    :raises SymbolicFailure: If the expression cannot be translated.

    Example::

        >>> import z3
        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.adapters import expression_from_model
        >>> from pyfcstm.semantics.symbolic import translate
        >>> translate(expression_from_model(parse_expr("7 / 2")), {})[0]
        7/2
    """
    session = SymbolicSession() if session is None else session
    interpretation = SYMBOLIC if interpretation is None else interpretation
    value = compile_expression(node, interpretation)(env, SymbolicContext(session))
    return value, session
