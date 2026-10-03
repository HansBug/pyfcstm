"""
Execution engine shared by every interpretation of FCSTM expressions.

The engine owns the control semantics of the expression language: operands
are evaluated left to right, ``&&``, ``||`` and ``=>`` evaluate their right
operand only when the left operand requires it, and a conditional expression
evaluates only the branches that can be selected.  An
:class:`Interpretation` supplies the value domain.  Concrete execution uses
Python values, symbolic execution uses Z3 terms and type inference uses
result types, but all of them run the same compiled control flow, so the
three can never disagree about which sub-expressions are evaluated.

The module contains:

* :class:`Interpretation` - The value-domain interface an execution chain implements.
* :func:`compile_expression` - Compile an IR expression into a callable.
* :func:`compile_statements` - Compile IR statements for concrete execution.

Example::

    >>> from pyfcstm.model.expr import parse_expr
    >>> from pyfcstm.semantics.adapters import expression_from_model
    >>> from pyfcstm.semantics.concrete import CONCRETE
    >>> from pyfcstm.semantics.engine import compile_expression
    >>> run = compile_expression(expression_from_model(parse_expr("x != 0 => 10 / x > 1")), CONCRETE)
    >>> run({"x": 0}, None), run({"x": 4}, None)
    (True, True)
"""

from typing import Any, Callable, Dict, Optional, Sequence

from . import ir
from .catalog import CATALOG, EAGER, SHORT_AND, SHORT_OR, lookup
from .errors import EvaluationError

__all__ = [
    "Interpretation",
    "compile_expression",
    "compile_statements",
]

#: A compiled expression: ``run(env, ctx) -> value``.
Compiled = Callable[[Any, Any], Any]

_CONDITIONAL = CATALOG["?:"]


class Interpretation:
    """
    The value domain an execution chain plugs into the engine.

    Every method receives the IR node being evaluated so that an
    interpretation can attach provenance, and the context object ``ctx`` that
    the caller passed to the compiled expression.  The engine never inspects
    values or contexts itself.

    Subclasses implement:

    * :meth:`literal` - the value of a constant;
    * :meth:`symbol` - the value of a reference in the environment ``env``;
    * :meth:`apply` - the result of a catalog entry on operand values,
      including how runtime errors are handled;
    * :meth:`missing_function` - a call to a function outside the catalog;
    * :meth:`host_atom` - a host-specific atom;
    * :meth:`truth` and :meth:`negate` - conditions in the interpretation's
      domain;
    * :meth:`decide` - whether a condition is known to hold, known not to
      hold, or undecided;
    * :meth:`enter` - the context for evaluating a lazily evaluated operand;
    * :meth:`constant` - the boolean value of a skipped short-circuit operator;
    * :meth:`no_branch` - a conditional expression none of whose branches
      can be selected.

    Example::

        >>> from pyfcstm.semantics.engine import Interpretation
        >>> Interpretation().decide(True, None, None)
        Traceback (most recent call last):
        ...
        NotImplementedError
    """

    def literal(self, node: ir.Literal) -> Any:
        """Return the value of a literal."""
        raise NotImplementedError

    def symbol(self, node: ir.Symbol, env: Any, ctx: Any) -> Any:
        """Return the value of a symbol in ``env``."""
        raise NotImplementedError

    def apply(self, node: ir.Expr, spec, args: Sequence[Any], ctx: Any) -> Any:
        """Return the result of catalog entry ``spec`` on ``args``."""
        raise NotImplementedError

    def missing_function(self, node: ir.Call, args: Sequence[Any], ctx: Any) -> Any:
        """Handle a call to a function that is not in the catalog."""
        raise NotImplementedError

    def host_atom(self, node: ir.HostAtom, args: Sequence[Any], env: Any, ctx: Any) -> Any:
        """Return the value of a host atom."""
        raise NotImplementedError

    def truth(self, value: Any, node: ir.Expr, ctx: Any) -> Any:
        """Return ``value`` as a condition."""
        raise NotImplementedError

    def negate(self, condition: Any) -> Any:
        """Return the negation of a condition."""
        raise NotImplementedError

    def decide(self, condition: Any, node: ir.Node, ctx: Any) -> Optional[bool]:
        """Return ``True`` or ``False`` when ``condition`` is known, else ``None``."""
        raise NotImplementedError

    def enter(self, ctx: Any, condition: Any, node: ir.Node, guard: bool) -> Any:
        """
        Return the context for evaluating ``node`` only when ``condition`` holds.

        ``guard`` tells whether errors raised inside must be guarded by the
        condition; it is ``False`` when the condition is already implied
        because the alternative branch cannot be selected.
        """
        raise NotImplementedError

    def constant(self, value: bool, node: ir.Expr) -> Any:
        """Return a boolean constant in the interpretation's domain."""
        raise NotImplementedError

    def no_branch(self, node: ir.Conditional, ctx: Any) -> Any:
        """Handle a conditional expression with no selectable branch."""
        raise NotImplementedError


def _compile_binary(node: ir.Binary, interp: Interpretation) -> Compiled:
    spec = lookup(node.op)
    left = compile_expression(node.left, interp)
    right = compile_expression(node.right, interp)
    apply = interp.apply
    if spec.control == EAGER:
        return lambda env, ctx: apply(node, spec, (left(env, ctx), right(env, ctx)), ctx)

    truth, decide, enter = interp.truth, interp.decide, interp.enter
    negate = spec.control == SHORT_OR
    # A skipped right operand leaves ``&&`` false, and ``||`` and ``=>`` true.
    skipped = interp.constant(spec.control != SHORT_AND, node)

    def run(env, ctx):
        left_value = left(env, ctx)
        condition = truth(left_value, node.left, ctx)
        if negate:
            condition = interp.negate(condition)
        if decide(condition, node.right, ctx) is False:
            return skipped
        right_value = right(env, enter(ctx, condition, node.right, True))
        return apply(node, spec, (left_value, right_value), ctx)

    return run


def _compile_conditional(node: ir.Conditional, interp: Interpretation) -> Compiled:
    test = compile_expression(node.test, interp)
    if_true = compile_expression(node.if_true, interp)
    if_false = compile_expression(node.if_false, interp)
    truth, negate, decide, enter, apply = (
        interp.truth,
        interp.negate,
        interp.decide,
        interp.enter,
        interp.apply,
    )

    def run(env, ctx):
        test_value = test(env, ctx)
        condition = truth(test_value, node.test, ctx)
        otherwise = negate(condition)
        # Both selectors are decided before either branch is evaluated.
        true_reachable = decide(condition, node.if_true, ctx) is not False
        false_reachable = decide(otherwise, node.if_false, ctx) is not False
        both = true_reachable and false_reachable
        if not both:
            if true_reachable:
                return if_true(env, enter(ctx, condition, node.if_true, False))
            if false_reachable:
                return if_false(env, enter(ctx, otherwise, node.if_false, False))
            return interp.no_branch(node, ctx)
        true_value = if_true(env, enter(ctx, condition, node.if_true, True))
        false_value = if_false(env, enter(ctx, otherwise, node.if_false, True))
        return apply(node, _CONDITIONAL, (test_value, true_value, false_value), ctx)

    return run


def compile_expression(node: ir.Expr, interp: Interpretation) -> Compiled:
    """
    Compile an IR expression into a callable for one interpretation.

    The result is called as ``run(env, ctx)``; ``env`` is passed to
    :meth:`Interpretation.symbol` and ``ctx`` to every interpretation hook.

    :param node: Expression to compile.
    :type node: pyfcstm.semantics.ir.Expr
    :param interp: Interpretation supplying the value domain.
    :type interp: Interpretation
    :return: Compiled expression.
    :rtype: Callable[[object, object], object]
    :raises TypeError: If ``node`` is not an IR expression.

    Example::

        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.adapters import expression_from_model
        >>> from pyfcstm.semantics.concrete import CONCRETE
        >>> from pyfcstm.semantics.engine import compile_expression
        >>> compile_expression(expression_from_model(parse_expr("x % -2")), CONCRETE)({"x": 7}, None)
        -1
    """
    if isinstance(node, ir.Literal):
        value = interp.literal(node)
        return lambda env, ctx: value
    if isinstance(node, ir.Symbol):
        symbol = interp.symbol
        return lambda env, ctx: symbol(node, env, ctx)
    if isinstance(node, ir.Binary):
        return _compile_binary(node, interp)
    if isinstance(node, ir.Unary):
        spec = lookup(node.op)
        operand = compile_expression(node.operand, interp)
        apply = interp.apply
        return lambda env, ctx: apply(node, spec, (operand(env, ctx),), ctx)
    if isinstance(node, ir.Conditional):
        return _compile_conditional(node, interp)
    if isinstance(node, ir.Call):
        args = tuple(compile_expression(arg, interp) for arg in node.args)
        spec = CATALOG.get(node.func)
        if spec is None:
            missing = interp.missing_function
            return lambda env, ctx: missing(node, tuple(arg(env, ctx) for arg in args), ctx)
        apply = interp.apply
        if len(args) == 1:
            (single,) = args
            return lambda env, ctx: apply(node, spec, (single(env, ctx),), ctx)
        return lambda env, ctx: apply(node, spec, tuple(arg(env, ctx) for arg in args), ctx)
    if isinstance(node, ir.HostAtom):
        args = tuple(compile_expression(arg, interp) for arg in node.args)
        host_atom = interp.host_atom
        return lambda env, ctx: host_atom(node, tuple(arg(env, ctx) for arg in args), env, ctx)
    raise TypeError("Unsupported IR expression: %s" % (type(node).__name__,))


def compile_statements(statements: Sequence[ir.Stmt], interp: Interpretation) -> Callable[[Dict, Any], None]:
    """
    Compile IR statements for concrete execution.

    The compiled block mutates the scope ``env`` in place.  Assignments take
    effect immediately, so later statements read earlier results.  An ``if``
    statement runs the first arm whose condition holds in a copy of the
    scope, then writes back only the names that were visible before the arm
    ran; names first assigned inside the arm are temporaries and disappear.

    An :class:`pyfcstm.semantics.errors.EvaluationError` leaving a statement
    records the innermost statement and whether the assigned value or a
    branch condition failed, so a caller can report where the error happened.

    :param statements: Statements in execution order.
    :type statements: Sequence[pyfcstm.semantics.ir.Stmt]
    :param interp: Interpretation whose :meth:`Interpretation.decide` always
        returns ``True`` or ``False``.
    :type interp: Interpretation
    :return: Compiled block called as ``run(env, ctx)``.
    :rtype: Callable[[dict, object], None]
    :raises TypeError: If a statement is not an IR statement.

    Example::

        >>> from pyfcstm.model import IfBlock, IfBlockBranch, Operation
        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.adapters import statements_from_model
        >>> from pyfcstm.semantics.concrete import CONCRETE
        >>> from pyfcstm.semantics.engine import compile_statements
        >>> block = statements_from_model([
        ...     Operation("t", parse_expr("x * 2")),
        ...     IfBlock([IfBlockBranch(parse_expr("t > 4"), [Operation("x", parse_expr("t"))])]),
        ... ])
        >>> scope = {"x": 3}
        >>> compile_statements(block, CONCRETE)(scope, None)
        >>> scope
        {'x': 6, 't': 6}
    """
    steps = tuple(_compile_statement(statement, interp) for statement in statements)

    def run(env, ctx):
        for step in steps:
            step(env, ctx)

    return run


def _compile_statement(statement: ir.Stmt, interp: Interpretation) -> Callable[[Dict, Any], None]:
    if isinstance(statement, ir.Assign):
        target = statement.target
        value = compile_expression(statement.value, interp)

        def assign(env, ctx):
            try:
                env[target] = value(env, ctx)
            except EvaluationError as err:
                # EvaluationError: the assigned expression raised a runtime
                # error; record the innermost statement for the caller.
                _locate(err, statement, "value")
                raise

        return assign
    if isinstance(statement, ir.If):
        arms = tuple(
            (
                None if arm.test is None else compile_expression(arm.test, interp),
                arm.test,
                compile_statements(arm.body, interp),
            )
            for arm in statement.arms
        )
        truth, decide = interp.truth, interp.decide

        def branch(env, ctx):
            for arm, (test, test_node, body) in zip(statement.arms, arms):
                if test is not None:
                    try:
                        selected = decide(truth(test(env, ctx), test_node, ctx), test_node, ctx)
                    except EvaluationError as err:
                        # EvaluationError: the branch condition raised a
                        # runtime error; record the branch for the caller.
                        _locate(err, arm, "test")
                        raise
                    if not selected:
                        continue
                visible = tuple(env)
                arm_env = dict(env)
                body(arm_env, ctx)
                for name in visible:
                    env[name] = arm_env[name]
                return

        return branch
    raise TypeError("Unsupported IR statement: %s" % (type(statement).__name__,))


def _locate(err: EvaluationError, node: ir.Node, role: str) -> None:
    # Bodies run outside the condition handler, so an error is located once,
    # by the innermost statement that evaluated the failing expression.
    err.statement = node
    err.role = role
