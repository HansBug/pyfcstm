"""
Adapters from the FCSTM model layer to the canonical IR.

The adapter only maps structure: which child is the left operand, which
statement belongs to which branch.  It never decides what an operator means,
so model expressions and operation blocks get their semantics from the
catalog through the engine like every other host language.

The module contains:

* :func:`expression_from_model` - Translate a model expression.
* :func:`statements_from_model` - Translate a model operation block.

Example::

    >>> from pyfcstm.model.expr import parse_expr
    >>> from pyfcstm.semantics.adapters import expression_from_model
    >>> node = expression_from_model(parse_expr("x > 0 and not (y > 0)"))
    >>> node.op, node.right.op
    ('&&', '!')
"""

from typing import Iterable, Tuple

from . import ir
from .catalog import canonical_token

__all__ = [
    "expression_from_model",
    "statements_from_model",
]


def expression_from_model(expr, node_id: str = "e") -> ir.Expr:
    """
    Translate a model expression into an IR expression.

    Subclasses of the model expression classes are accepted, matching the
    behaviour of the solver translator; any other object is rejected.

    :param expr: Model expression to translate.
    :type expr: pyfcstm.model.expr.Expr
    :param node_id: Identifier of the root node; child identifiers append the
        child position, defaults to ``"e"``.
    :type node_id: str, optional
    :return: Equivalent IR expression.
    :rtype: pyfcstm.semantics.ir.Expr
    :raises TypeError: If ``expr`` is not a model expression.

    Example::

        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.adapters import expression_from_model
        >>> node = expression_from_model(parse_expr("-x ** 2"), "guard")
        >>> node.node_id, node.op, node.left.node_id
        ('guard', '**', 'guard.0')
    """
    from ..model.expr import (
        Boolean,
        BinaryOp,
        ConditionalOp,
        Float,
        Integer,
        UFunc,
        UnaryOp,
        Variable,
    )

    if isinstance(expr, (Integer, Float, Boolean)):
        return ir.Literal(node_id, expr, expr.value)
    if isinstance(expr, Variable):
        return ir.Symbol(node_id, expr, expr.name)
    if isinstance(expr, UnaryOp):
        return ir.Unary(
            node_id,
            expr,
            expr.op_mark,
            expression_from_model(expr.x, node_id + ".0"),
        )
    if isinstance(expr, BinaryOp):
        return ir.Binary(
            node_id,
            expr,
            canonical_token(expr.op),
            expression_from_model(expr.x, node_id + ".0"),
            expression_from_model(expr.y, node_id + ".1"),
        )
    if isinstance(expr, ConditionalOp):
        return ir.Conditional(
            node_id,
            expr,
            expression_from_model(expr.cond, node_id + ".0"),
            expression_from_model(expr.if_true, node_id + ".1"),
            expression_from_model(expr.if_false, node_id + ".2"),
        )
    if isinstance(expr, UFunc):
        return ir.Call(
            node_id,
            expr,
            expr.func,
            (expression_from_model(expr.x, node_id + ".0"),),
        )
    raise TypeError("Unsupported expression type: %s" % (type(expr).__name__,))


def statements_from_model(operations: Iterable, node_id: str = "s") -> Tuple[ir.Stmt, ...]:
    """
    Translate a model operation block into IR statements.

    :param operations: Model operation statements in execution order.
    :type operations: Iterable[pyfcstm.model.OperationStatement]
    :param node_id: Identifier prefix of the block, defaults to ``"s"``.
    :type node_id: str, optional
    :return: Equivalent IR statements.
    :rtype: Tuple[pyfcstm.semantics.ir.Stmt, ...]
    :raises TypeError: If a statement is neither an assignment nor an ``if``
        block, or an expression is not a model expression.

    Example::

        >>> from pyfcstm.model import Operation
        >>> from pyfcstm.model.expr import parse_expr
        >>> from pyfcstm.semantics.adapters import statements_from_model
        >>> (stmt,) = statements_from_model([Operation("x", parse_expr("x + 1"))])
        >>> stmt.target, stmt.value.op
        ('x', '+')
    """
    from ..model.model import IfBlock, Operation

    statements = []
    for index, statement in enumerate(operations):
        statement_id = "%s.%d" % (node_id, index)
        if isinstance(statement, Operation):
            statements.append(
                ir.Assign(
                    statement_id,
                    statement,
                    statement.var_name,
                    expression_from_model(statement.expr, statement_id + ".value"),
                )
            )
        elif isinstance(statement, IfBlock):
            arms = []
            for arm_index, branch in enumerate(statement.branches):
                arm_id = "%s.%d" % (statement_id, arm_index)
                test = (
                    None
                    if branch.condition is None
                    else expression_from_model(branch.condition, arm_id + ".test")
                )
                arms.append(
                    ir.Arm(
                        arm_id,
                        branch,
                        test,
                        statements_from_model(branch.statements, arm_id + ".body"),
                    )
                )
            statements.append(ir.If(statement_id, statement, tuple(arms)))
        else:
            raise TypeError(
                "Unknown operation statement type %r." % (type(statement),)
            )
    return tuple(statements)
