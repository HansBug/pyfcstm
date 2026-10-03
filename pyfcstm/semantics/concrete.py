"""
Concrete execution: the runnable reference semantics on Python values.

:data:`CONCRETE` evaluates expressions with the catalog's runnable reference.
When an operation raises one of the errors its catalog entry declares, the
interpretation raises :class:`pyfcstm.semantics.errors.EvaluationError`, which names the error kind and
keeps the original exception.  Each execution chain decides what a runtime
error means for it: :meth:`pyfcstm.model.expr.Expr.__call__` re-raises the
Python exception, while the simulator reports a controlled
:class:`pyfcstm.simulate.SimulationRuntimeExpressionError`.

Persistent writeback follows one rule everywhere, implemented by
:func:`normalize_persistent`: an ``int`` variable accepts integers and
integral floats, a ``float`` variable accepts finite numbers, and booleans or
other values are rejected.

The module contains:

* :class:`ConcreteInterpretation` - The concrete interpretation.
* :data:`CONCRETE` - The shared concrete interpretation instance.
* :func:`evaluate` - Evaluate a model expression.
* :func:`normalize_persistent` - Normalize a value for a declared variable type.

Example::

    >>> from pyfcstm.model.expr import parse_expr
    >>> from pyfcstm.semantics.concrete import evaluate
    >>> from pyfcstm.semantics.errors import EvaluationError
    >>> evaluate(parse_expr("x % -2"), {"x": 7})
    -1
    >>> try:
    ...     evaluate(parse_expr("10 / x"), {"x": 0})
    ... except EvaluationError as err:
    ...     print(err.kind)
    division_by_zero
"""

import math
from typing import Any, Mapping, Sequence, Union

from . import ir
from .adapters import expression_from_model
from .engine import Interpretation, compile_expression
from .errors import EvaluationError, WritebackError

__all__ = [
    "ConcreteInterpretation",
    "CONCRETE",
    "evaluate",
    "normalize_persistent",
]


class ConcreteInterpretation(Interpretation):
    """
    Concrete interpretation: Python values and the runnable reference.

    The context argument is unused; pass ``None``.  Symbols are looked up in
    a mapping, and a missing name raises :class:`KeyError`.

    Example::

        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.adapters import expression_from_model
        >>> from pyfcstm.semantics.concrete import CONCRETE
        >>> from pyfcstm.semantics.engine import compile_expression
        >>> run = compile_expression(expression_from_model(parse_expr("x > 0 && 1 / y > 0")), CONCRETE)
        >>> run({"x": 0, "y": 0}, None)
        False
    """

    def literal(self, node: ir.Literal) -> Any:
        return node.value

    def symbol(self, node: ir.Symbol, env: Mapping[str, Any], ctx: Any) -> Any:
        return env[node.reference]

    def apply(self, node: ir.Expr, spec, args: Sequence[Any], ctx: Any) -> Any:
        try:
            return spec.concrete(*args)
        except (ArithmeticError, ValueError, TypeError, MemoryError) as err:
            # ArithmeticError: ZeroDivisionError and OverflowError from
            # arithmetic, powers and float conversion; ValueError: math domain
            # errors, negative shift counts and complex powers; TypeError:
            # operand types an operator rejects, such as ``1.5 << 1``;
            # MemoryError: shifts whose result cannot be allocated.
            rule = spec.error_rule(err)
            if rule is None:
                raise
            reported = err if rule.message is None else type(err)(rule.message)
            raise EvaluationError(rule.kind, reported, node) from err

    def unknown_operation(self, node: ir.Expr, args: Sequence[Any], ctx: Any) -> Any:
        raise KeyError(node.func if isinstance(node, ir.Call) else node.op)

    def truth(self, value: Any, node: ir.Node, ctx: Any) -> Any:
        return value

    def negate(self, condition: Any) -> bool:
        return not condition

    def decide(self, condition: Any, node: ir.Node, ctx: Any, role: str) -> bool:
        return bool(condition)

    def enter(self, ctx: Any, condition: Any, node: ir.Node, role: str, guard: bool) -> Any:
        return ctx

    def constant(self, value: bool, node: ir.Expr) -> bool:
        return value


#: Shared concrete interpretation instance.
CONCRETE = ConcreteInterpretation()


def evaluate(expr, env: Mapping[str, Any]) -> Any:
    """
    Evaluate a model expression with concrete semantics.

    :param expr: Model expression.
    :type expr: pyfcstm.model.expr.Expr
    :param env: Variable values by name.
    :type env: Mapping[str, Any]
    :return: The expression value.
    :rtype: Any
    :raises pyfcstm.semantics.errors.EvaluationError: If an operation raises
        a runtime error.
    :raises KeyError: If a variable is missing from ``env``.

    Example::

        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.concrete import evaluate
        >>> evaluate(parse_expr("cbrt(-8) + sign(x)"), {"x": -0.5})
        -3.0
    """
    return compile_expression(expression_from_model(expr), CONCRETE)(env, None)


def normalize_persistent(name: str, declared_type: str, value: Any, source: str) -> Union[int, float]:
    """
    Normalize a value written to a persistent variable.

    :param name: Variable name, used in messages.
    :type name: str
    :param declared_type: Declared variable type, ``"int"`` or ``"float"``.
    :type declared_type: str
    :param value: Candidate value.
    :type value: Any
    :param source: Human-readable origin of the value, used in messages, such
        as ``"operation block writeback"``.
    :type source: str
    :return: The value as the declared type.
    :rtype: Union[int, float]
    :raises pyfcstm.semantics.errors.WritebackError: If the value is a bool or not a number, is not
        finite, cannot be represented as a float, or is a non-integral float
        for an ``int`` variable.
    :raises ValueError: If ``declared_type`` is not ``"int"`` or ``"float"``.

    Example::

        >>> from pyfcstm.semantics.concrete import normalize_persistent
        >>> normalize_persistent("x", "int", 3.0, "example")
        3
        >>> normalize_persistent("x", "int", 3.5, "operation block writeback")
        Traceback (most recent call last):
        ...
        pyfcstm.semantics.errors.WritebackError: Variable 'x' is int type, cannot assign float 3.5; non-integer float from operation block writeback
    """
    if type(value) is bool:
        raise WritebackError("writeback_type", "%s must not be bool" % (source,))
    if type(value) not in (int, float):
        raise WritebackError(
            "writeback_type",
            "%s must be int or float, got %s" % (source, type(value).__name__),
        )
    if type(value) is float and not math.isfinite(value):
        raise WritebackError(
            "writeback_non_finite",
            "%s for variable '%s' declared %s must be finite, got %r"
            % (source, name, declared_type, value),
        )
    if declared_type == "int":
        if type(value) is float:
            if value != int(value):
                raise WritebackError(
                    "writeback_non_integral",
                    "Variable '%s' is int type, cannot assign float %r; "
                    "non-integer float from %s" % (name, value, source),
                )
            return int(value)
        return value
    if declared_type == "float":
        try:
            return float(value)
        except OverflowError as err:
            # OverflowError: ``float(value)`` cannot represent a very large
            # Python integer as a finite float.
            raise WritebackError(
                "writeback_float_range",
                "%s for variable '%s' declared float must be finite; "
                "integer is outside Python float range" % (source, name),
            ) from err
    raise ValueError("Variable '%s' has unsupported persistent type %r" % (name, declared_type))
