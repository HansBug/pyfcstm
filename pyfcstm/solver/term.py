"""Direct construction of common Z3 terms.

The operators of the ``z3`` package accept Python values, probes, tactics and
terms of different sorts, and find out what they were given by inspecting
every argument: each one is cast, and its sort is fetched, wrapped and
compared.  For arguments that already are Z3 terms of the expected sort in one
context none of that changes anything, yet it costs several times the
construction itself.

The helpers here recognise that case and hand the arguments straight to the Z3
C API.  Anything else is passed to the ``z3`` operator unchanged, so every
helper returns exactly the term, of exactly the Python class, that the
``z3`` operator returns, and raises what it raises.

The module contains:

* :func:`and_terms` and :func:`or_terms` - n-ary conjunction and disjunction
* :func:`not_term` and :func:`implies_term` - negation and implication
* :func:`eq_term` - equality of two terms
* :func:`ite_term` - if-then-else
* :func:`is_int_term` - whether a value is a term of integer sort
* :func:`pyfcstm.semantics.symbolic.int_term` - integer numeral, re-exported

Example::

    >>> import z3
    >>> a, b = z3.Bools("a b")
    >>> and_terms((a, b))
    And(a, b)
    >>> z3.eq(and_terms((a, b)), z3.And(a, b))
    True
"""

from typing import Sequence

import z3
from z3 import (
    ArithRef,
    Ast,
    BoolRef,
    ExprRef,
    Z3_INT_SORT,
    Z3_get_sort,
    Z3_get_sort_kind,
    Z3_mk_and,
    Z3_mk_eq,
    Z3_mk_implies,
    Z3_mk_ite,
    Z3_mk_not,
    Z3_mk_or,
)

from ..semantics.symbolic import int_term


def _bool_array(args: Sequence[object]):
    """Return ``(context, ast_array)`` when every item is a plain Boolean term.

    :param args: Candidate operands.
    :type args: Sequence[object]
    :return: The shared context and a C array of the terms, or ``(None, None)``
        when an operand is not a :class:`z3.BoolRef` of the first one's context.
    :rtype: Tuple[Optional[z3.Context], Optional[object]]
    """
    context = None
    asts = []
    for item in args:
        # An exact class test: a quantifier is a BoolRef subclass, and a probe,
        # a Python bool or an AstVector is no BoolRef at all.
        if type(item) is not BoolRef:
            return None, None
        if context is None:
            context = item.ctx
        elif item.ctx is not context:
            return None, None
        asts.append(item.ast)
    if context is None:
        return None, None
    return context, (Ast * len(asts))(*asts)


def and_terms(args: Sequence[z3.BoolRef]) -> z3.BoolRef:
    """Return ``z3.And(*args)``.

    :param args: Conjuncts.
    :type args: Sequence[z3.BoolRef]
    :return: The conjunction, exactly as :func:`z3.And` builds it.
    :rtype: z3.BoolRef

    Example::

        >>> import z3
        >>> a, b, c = z3.Bools("a b c")
        >>> and_terms((a, b, c))
        And(a, b, c)
    """
    args = tuple(args)
    context, array = _bool_array(args)
    if context is None:
        return z3.And(*args)
    return BoolRef(Z3_mk_and(context.ref(), len(array), array), context)


def or_terms(args: Sequence[z3.BoolRef]) -> z3.BoolRef:
    """Return ``z3.Or(*args)``.

    :param args: Disjuncts.
    :type args: Sequence[z3.BoolRef]
    :return: The disjunction, exactly as :func:`z3.Or` builds it.
    :rtype: z3.BoolRef

    Example::

        >>> import z3
        >>> a, b = z3.Bools("a b")
        >>> or_terms((a, b))
        Or(a, b)
    """
    args = tuple(args)
    context, array = _bool_array(args)
    if context is None:
        return z3.Or(*args)
    return BoolRef(Z3_mk_or(context.ref(), len(array), array), context)


def not_term(arg: z3.BoolRef) -> z3.BoolRef:
    """Return ``z3.Not(arg)``.

    :param arg: Term to negate.
    :type arg: z3.BoolRef
    :return: The negation, exactly as :func:`z3.Not` builds it.
    :rtype: z3.BoolRef

    Example::

        >>> import z3
        >>> not_term(z3.Bool("a"))
        Not(a)
    """
    if type(arg) is not BoolRef:
        return z3.Not(arg)
    context = arg.ctx
    return BoolRef(Z3_mk_not(context.ref(), arg.ast), context)


def implies_term(left: z3.BoolRef, right: z3.BoolRef) -> z3.BoolRef:
    """Return ``z3.Implies(left, right)``.

    :param left: Antecedent.
    :type left: z3.BoolRef
    :param right: Consequent.
    :type right: z3.BoolRef
    :return: The implication, exactly as :func:`z3.Implies` builds it.
    :rtype: z3.BoolRef

    Example::

        >>> import z3
        >>> a, b = z3.Bools("a b")
        >>> implies_term(a, b)
        Implies(a, b)
    """
    if type(left) is not BoolRef or type(right) is not BoolRef:
        return z3.Implies(left, right)
    context = left.ctx
    if right.ctx is not context:
        return z3.Implies(left, right)
    return BoolRef(Z3_mk_implies(context.ref(), left.ast, right.ast), context)


def eq_term(left: z3.ExprRef, right: z3.ExprRef) -> z3.BoolRef:
    """Return ``left == right`` for two Z3 terms.

    :param left: Left operand.
    :type left: z3.ExprRef
    :param right: Right operand.
    :type right: z3.ExprRef
    :return: The equality, exactly as the ``==`` operator of ``left`` builds it.
    :rtype: z3.BoolRef

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> eq_term(x, x + 1)
        x == x + 1
        >>> z3.eq(eq_term(x, z3.IntVal(3)), x == z3.IntVal(3))
        True
    """
    if isinstance(left, ExprRef) and isinstance(right, ExprRef):
        context = left.ctx
        if right.ctx is context:
            ref = context.ref()
            # Sorts are unique in a context, so one sort has one address.  Terms
            # of different sorts are left to the coercion of the operator.
            if Z3_get_sort(ref, left.ast).value == Z3_get_sort(ref, right.ast).value:
                # Python asks the right operand first when its class derives
                # from the class of the left one, as a numeral does from an
                # arithmetic term; the equality then lists the operands in
                # that order.
                if type(right) is not type(left) and isinstance(right, type(left)):
                    return BoolRef(Z3_mk_eq(ref, right.ast, left.ast), context)
                return BoolRef(Z3_mk_eq(ref, left.ast, right.ast), context)
    return left == right


def ite_term(test: z3.BoolRef, if_true: z3.ExprRef, if_false: z3.ExprRef) -> z3.ExprRef:
    """Return ``z3.If(test, if_true, if_false)``.

    :param test: Condition.
    :type test: z3.BoolRef
    :param if_true: Value when the condition holds.
    :type if_true: z3.ExprRef
    :param if_false: Value when it does not.
    :type if_false: z3.ExprRef
    :return: The conditional term, exactly as :func:`z3.If` builds it.
    :rtype: z3.ExprRef

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> ite_term(x > 0, x, z3.IntVal(0))
        If(x > 0, x, 0)
    """
    if type(test) is BoolRef:
        both_bool = type(if_true) is BoolRef and type(if_false) is BoolRef
        if both_bool or (
            isinstance(if_true, ArithRef) and isinstance(if_false, ArithRef)
        ):
            context = test.ctx
            if if_true.ctx is context and if_false.ctx is context:
                ref = context.ref()
                if both_bool or (
                    Z3_get_sort(ref, if_true.ast).value
                    == Z3_get_sort(ref, if_false.ast).value
                ):
                    ast = Z3_mk_ite(ref, test.ast, if_true.ast, if_false.ast)
                    # A conditional term is an application, never a numeral, so
                    # its wrapper is the plain class of its sort.
                    return (BoolRef if both_bool else ArithRef)(ast, context)
    return z3.If(test, if_true, if_false)


def is_int_term(value: object) -> bool:
    """Return ``z3.is_int(value)``.

    :param value: Any object.
    :type value: object
    :return: Whether ``value`` is an arithmetic term of integer sort.
    :rtype: bool

    Example::

        >>> import z3
        >>> is_int_term(z3.Int("x")), is_int_term(z3.Real("r")), is_int_term(1)
        (True, False, False)
    """
    if not isinstance(value, ArithRef):
        return False
    ref = value.ctx.ref()
    return Z3_get_sort_kind(ref, Z3_get_sort(ref, value.ast)) == Z3_INT_SORT


__all__ = [
    "and_terms",
    "eq_term",
    "implies_term",
    "int_term",
    "is_int_term",
    "ite_term",
    "not_term",
    "or_terms",
]
