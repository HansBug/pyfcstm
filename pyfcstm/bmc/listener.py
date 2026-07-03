"""ANTLR listener that builds parser-independent FCSTM BMC query AST nodes.

The listener mirrors :mod:`pyfcstm.dsl.listener`: it walks generated ANTLR parse
contexts bottom-up and stores the constructed object in ``nodes[ctx]``. The
module intentionally performs syntax-to-AST construction only. It does not
resolve model paths, validate event scope, lower expressions to Z3, or touch the
verify registry.

The module contains:

* :class:`BmcQueryParseListener` - Context-to-node listener for ``.fbmcq`` query
  files and expression entry rules.

Example::

    >>> from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker
    >>> from pyfcstm.bmc.grammar.BmcQueryLexer import BmcQueryLexer
    >>> from pyfcstm.bmc.grammar.BmcQueryParser import BmcQueryParser
    >>> listener = BmcQueryParseListener()
    >>> lexer = BmcQueryLexer(InputStream('check reach <= 1: true;'))
    >>> parser = BmcQueryParser(CommonTokenStream(lexer))
    >>> tree = parser.query()
    >>> ParseTreeWalker().walk(listener, tree)
    >>> listener.nodes[tree].property.kind
    'reach'
"""

from __future__ import annotations

import ast as py_ast
from typing import Any, Dict, List, cast

from pyfcstm.bmc.ast import (
    Active,
    BoolLiteral,
    Called,
    Case,
    CondBinaryOp,
    CondConditionalOp,
    CondUnaryOp,
    Cycle,
    Event,
    FloatLiteral,
    FrameVar,
    IntLiteral,
    MathConst,
    NameRef,
    NumBinaryOp,
    NumConditionalOp,
    NumUnaryOp,
    NumericComparison,
    Terminated,
    UFuncCall,
)
from pyfcstm.bmc.grammar.BmcQueryParser import BmcQueryParser
from pyfcstm.bmc.grammar.BmcQueryParserListener import BmcQueryParserListener
from pyfcstm.bmc.query import (
    BmcProperty,
    BmcQuery,
    EventAssumption,
    EventCardinalityAssumption,
    FrameAssumption,
    InitialSpec,
)


def _decode_string_literal(raw_text: str) -> str:
    """Decode a grammar-accepted string literal token.

    :param raw_text: Token text including surrounding quotes.
    :type raw_text: str
    :return: Decoded Python string value.
    :rtype: str

    Example::

        >>> _decode_string_literal('"Root.A"')
        'Root.A'
    """
    return py_ast.literal_eval(raw_text)


def _int_value(raw_text: str) -> int:
    """Return the integer value for a decimal grammar literal.

    :param raw_text: Decimal literal token text.
    :type raw_text: str
    :return: Parsed integer value.
    :rtype: int

    Example::

        >>> _int_value('001')
        1
    """
    return int(raw_text, 10)


class BmcQueryParseListener(BmcQueryParserListener):
    """Build BMC query model nodes from generated ANTLR parse contexts.

    :ivar nodes: Mapping from parse context objects to AST/query nodes.
    :vartype nodes: Dict[object, object]

    Example::

        >>> listener = BmcQueryParseListener()
        >>> listener.nodes
        {}
    """

    def __init__(self) -> None:
        """Initialize the listener node mapping.

        :return: ``None``.
        :rtype: None

        Example::

            >>> BmcQueryParseListener().nodes
            {}
        """
        super().__init__()
        self.nodes: Dict[object, Any] = {}

    def _optional_frame(self, ctx: object) -> Any:
        """Return ``current`` for omitted frames or the mapped selector value."""
        if ctx is None:
            return "current"
        return self.nodes[ctx]

    def _string_value(self, ctx: object) -> str:
        """Return a decoded string literal value from a mapped context."""
        return cast(str, self.nodes[ctx])

    def exitQuery(self, ctx: BmcQueryParser.QueryContext) -> None:
        """Build the top-level :class:`pyfcstm.bmc.query.BmcQuery`.

        :param ctx: Query parse context.
        :type ctx: BmcQueryParser.QueryContext
        :return: ``None``.
        :rtype: None
        """
        initial = self.nodes[ctx.init_clause()] if ctx.init_clause() else InitialSpec()
        assumption_contexts = cast(
            List[BmcQueryParser.Assume_clauseContext], ctx.assume_clause()
        )
        assumptions = tuple(self.nodes[item] for item in assumption_contexts)
        self.nodes[ctx] = BmcQuery(
            property=self.nodes[ctx.check_clause()],
            initial=initial,
            assumptions=assumptions,
        )

    def exitBmc_num_expression_entry(
        self, ctx: BmcQueryParser.Bmc_num_expression_entryContext
    ) -> None:
        """Bind a numeric expression entry to its expression node.

        :param ctx: Numeric expression entry parse context.
        :type ctx: BmcQueryParser.Bmc_num_expression_entryContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = self.nodes[ctx.bmc_num_expression()]

    def exitBmc_cond_expression_entry(
        self, ctx: BmcQueryParser.Bmc_cond_expression_entryContext
    ) -> None:
        """Bind a condition expression entry to its expression node.

        :param ctx: Condition expression entry parse context.
        :type ctx: BmcQueryParser.Bmc_cond_expression_entryContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = self.nodes[ctx.bmc_cond_expression()]

    def exitInit_clause(self, ctx: BmcQueryParser.Init_clauseContext) -> None:
        """Build an initial clause node.

        :param ctx: Initial clause parse context.
        :type ctx: BmcQueryParser.Init_clauseContext
        :return: ``None``.
        :rtype: None
        """
        target = self.nodes[ctx.init_target()]
        predicate = self.nodes[ctx.bmc_cond_expression()] if ctx.WHERE() else None
        mode = target[0]
        state_path = target[1] if mode == "state" else None
        self.nodes[ctx] = InitialSpec(
            mode=mode, state_path=state_path, predicate=predicate
        )

    def exitInit_target(self, ctx: BmcQueryParser.Init_targetContext) -> None:
        """Build an initial-target tuple used by :meth:`exitInit_clause`.

        :param ctx: Initial-target parse context.
        :type ctx: BmcQueryParser.Init_targetContext
        :return: ``None``.
        :rtype: None
        """
        if ctx.COLD():
            self.nodes[ctx] = ("cold", None)
        elif ctx.TERMINATED():
            self.nodes[ctx] = ("terminated", None)
        else:
            self.nodes[ctx] = ("state", self.nodes[ctx.string_literal()])

    def exitAssume_clause(self, ctx: BmcQueryParser.Assume_clauseContext) -> None:
        """Bind an assumption wrapper to its concrete assumption node.

        :param ctx: Assumption wrapper parse context.
        :type ctx: BmcQueryParser.Assume_clauseContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = self.nodes[
            ctx.frame_assume() or ctx.event_assume() or ctx.cardinality_assume()
        ]

    def exitFrame_assume(self, ctx: BmcQueryParser.Frame_assumeContext) -> None:
        """Build a frame assumption node.

        :param ctx: Frame assumption parse context.
        :type ctx: BmcQueryParser.Frame_assumeContext
        :return: ``None``.
        :rtype: None
        """
        predicate = self.nodes[ctx.bmc_cond_expression()]
        if ctx.ALWAYS():
            self.nodes[ctx] = FrameAssumption("always", predicate)
        else:
            self.nodes[ctx] = FrameAssumption(
                "at", predicate, frame=self.nodes[ctx.integer_literal()]
            )

    def exitEvent_assume(self, ctx: BmcQueryParser.Event_assumeContext) -> None:
        """Build an event assumption and normalize ``!=`` polarity.

        :param ctx: Event assumption parse context.
        :type ctx: BmcQueryParser.Event_assumeContext
        :return: ``None``.
        :rtype: None
        """
        bool_value = self.nodes[ctx.bool_literal()].value
        op = self.nodes[ctx.bool_cmp_op()]
        expected = bool_value if op == "==" else not bool_value
        self.nodes[ctx] = EventAssumption(
            self.nodes[ctx.string_literal()],
            selector=self.nodes[ctx.event_range_selector()],
            expected=expected,
        )

    def exitCardinality_assume(
        self, ctx: BmcQueryParser.Cardinality_assumeContext
    ) -> None:
        """Build an event-cardinality assumption node.

        :param ctx: Event-cardinality assumption parse context.
        :type ctx: BmcQueryParser.Cardinality_assumeContext
        :return: ``None``.
        :rtype: None
        """
        if ctx.ANY():
            self.nodes[ctx] = EventCardinalityAssumption("any")
        else:
            self.nodes[ctx] = EventCardinalityAssumption(
                "at_most_one", tuple(self.nodes[ctx.string_list()])
            )

    def exitCheck_clause(self, ctx: BmcQueryParser.Check_clauseContext) -> None:
        """Build the query property from a check clause.

        :param ctx: Check clause parse context.
        :type ctx: BmcQueryParser.Check_clauseContext
        :return: ``None``.
        :rtype: None
        """
        kind = self.nodes[ctx.property_kind()]
        bound = self.nodes[ctx.integer_literal()]
        body = self.nodes[ctx.property_body()]
        if kind == "response":
            trigger, within, response = body
            self.nodes[ctx] = BmcProperty(
                kind, bound, trigger=trigger, response=response, within=within
            )
        else:
            self.nodes[ctx] = BmcProperty(kind, bound, predicate=body)

    def exitProperty_kind(self, ctx: BmcQueryParser.Property_kindContext) -> None:
        """Bind a property kind context to its text.

        :param ctx: Property-kind parse context.
        :type ctx: BmcQueryParser.Property_kindContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = ctx.getText()

    def exitProperty_body(self, ctx: BmcQueryParser.Property_bodyContext) -> None:
        """Bind a property body to a response tuple or condition predicate.

        :param ctx: Property body parse context.
        :type ctx: BmcQueryParser.Property_bodyContext
        :return: ``None``.
        :rtype: None
        """
        child = ctx.response_property_body() or ctx.bmc_cond_expression()
        self.nodes[ctx] = self.nodes[child]

    def exitResponse_property_body(
        self, ctx: BmcQueryParser.Response_property_bodyContext
    ) -> None:
        """Build a response body tuple ``(trigger, within, response)``.

        :param ctx: Response property body parse context.
        :type ctx: BmcQueryParser.Response_property_bodyContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = (
            self.nodes[ctx.bmc_cond_expression(0)],
            self.nodes[ctx.integer_literal()],
            self.nodes[ctx.bmc_cond_expression(1)],
        )

    def exitString_list(self, ctx: BmcQueryParser.String_listContext) -> None:
        """Build a tuple of decoded string literals.

        :param ctx: String-list parse context.
        :type ctx: BmcQueryParser.String_listContext
        :return: ``None``.
        :rtype: None
        """
        string_contexts = cast(
            List[BmcQueryParser.String_literalContext], ctx.string_literal()
        )
        self.nodes[ctx] = tuple(self.nodes[item] for item in string_contexts)

    def exitBool_cmp_op(self, ctx: BmcQueryParser.Bool_cmp_opContext) -> None:
        """Bind a boolean comparison operator context to its spelling.

        :param ctx: Boolean comparison operator parse context.
        :type ctx: BmcQueryParser.Bool_cmp_opContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = ctx.getText()

    def exitEvent_range_selector(
        self, ctx: BmcQueryParser.Event_range_selectorContext
    ) -> None:
        """Build an event-assumption range selector.

        :param ctx: Event range selector parse context.
        :type ctx: BmcQueryParser.Event_range_selectorContext
        :return: ``None``.
        :rtype: None
        """
        if ctx.STAR():
            self.nodes[ctx] = "*"
        elif ctx.RANGE_INT():
            self.nodes[ctx] = "".join(cast(Any, ctx.RANGE_INT()).getText().split())
        else:
            items = cast(
                List[BmcQueryParser.Integer_literalContext], ctx.integer_literal()
            )
            if len(items) == 1:
                self.nodes[ctx] = self.nodes[items[0]]
            else:
                self.nodes[ctx] = "%d..%d" % (
                    self.nodes[items[0]],
                    self.nodes[items[1]],
                )

    def exitEvent_cycle_selector(
        self, ctx: BmcQueryParser.Event_cycle_selectorContext
    ) -> None:
        """Build an event atom cycle selector.

        :param ctx: Event cycle selector parse context.
        :type ctx: BmcQueryParser.Event_cycle_selectorContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = (
            "current" if ctx.CURRENT() else self.nodes[ctx.integer_literal()]
        )

    def exitFrame_selector(self, ctx: BmcQueryParser.Frame_selectorContext) -> None:
        """Build an optional-frame atom selector.

        :param ctx: Frame selector parse context.
        :type ctx: BmcQueryParser.Frame_selectorContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = (
            "current" if ctx.CURRENT() else self.nodes[ctx.integer_literal()]
        )

    def exitInteger_literal(self, ctx: BmcQueryParser.Integer_literalContext) -> None:
        """Build an integer value for query bounds and selectors.

        :param ctx: Integer literal parse context.
        :type ctx: BmcQueryParser.Integer_literalContext
        :return: ``None``.
        :rtype: None
        """
        self.nodes[ctx] = _int_value(cast(Any, ctx.INT()).getText())

    def exitParenExprNum(self, ctx: BmcQueryParser.ParenExprNumContext) -> None:
        """Bind a parenthesized numeric expression to its inner node."""
        self.nodes[ctx] = self.nodes[ctx.bmc_num_expression()]

    def exitLiteralExprNum(self, ctx: BmcQueryParser.LiteralExprNumContext) -> None:
        """Bind a numeric literal expression to its literal node."""
        self.nodes[ctx] = self.nodes[ctx.num_literal()]

    def exitIdExprNum(self, ctx: BmcQueryParser.IdExprNumContext) -> None:
        """Build a bare numeric name reference."""
        self.nodes[ctx] = NameRef(cast(Any, ctx.ID()).getText())

    def exitMathConstExprNum(self, ctx: BmcQueryParser.MathConstExprNumContext) -> None:
        """Bind a math-constant numeric expression to its constant node."""
        self.nodes[ctx] = self.nodes[ctx.math_const()]

    def exitFrameVarExprNum(self, ctx: BmcQueryParser.FrameVarExprNumContext) -> None:
        """Build a query-level ``var("...")`` numeric atom."""
        self.nodes[ctx] = FrameVar(self._string_value(ctx.string_literal()))

    def exitCycleExprNum(self, ctx: BmcQueryParser.CycleExprNumContext) -> None:
        """Build the built-in ``cycle`` numeric atom."""
        self.nodes[ctx] = Cycle()

    def exitUnaryExprNum(self, ctx: BmcQueryParser.UnaryExprNumContext) -> None:
        """Build a numeric unary expression."""
        self.nodes[ctx] = NumUnaryOp(
            cast(Any, ctx.op).text, self.nodes[ctx.bmc_num_expression()]
        )

    def exitFuncExprNum(self, ctx: BmcQueryParser.FuncExprNumContext) -> None:
        """Build a unary math function expression."""
        self.nodes[ctx] = UFuncCall(
            cast(Any, ctx.func_name).text, self.nodes[ctx.bmc_num_expression()]
        )

    def exitBinaryExprNum(self, ctx: BmcQueryParser.BinaryExprNumContext) -> None:
        """Build a numeric binary expression."""
        self.nodes[ctx] = NumBinaryOp(
            self.nodes[ctx.bmc_num_expression(0)],
            cast(Any, ctx.op).text,
            self.nodes[ctx.bmc_num_expression(1)],
        )

    def exitConditionalCStyleExprNum(
        self, ctx: BmcQueryParser.ConditionalCStyleExprNumContext
    ) -> None:
        """Build a numeric ternary expression."""
        self.nodes[ctx] = NumConditionalOp(
            self.nodes[ctx.bmc_cond_expression()],
            self.nodes[ctx.bmc_num_expression(0)],
            self.nodes[ctx.bmc_num_expression(1)],
        )

    def exitParenExprCond(self, ctx: BmcQueryParser.ParenExprCondContext) -> None:
        """Bind a parenthesized condition expression to its inner node."""
        self.nodes[ctx] = self.nodes[ctx.bmc_cond_expression()]

    def exitLiteralExprCond(self, ctx: BmcQueryParser.LiteralExprCondContext) -> None:
        """Bind a boolean literal condition expression to its literal node."""
        self.nodes[ctx] = self.nodes[ctx.bool_literal()]

    def exitAtomExprCond(self, ctx: BmcQueryParser.AtomExprCondContext) -> None:
        """Bind a condition atom expression to its atom node."""
        self.nodes[ctx] = self.nodes[ctx.bmc_boolean_atom()]

    def exitUnaryExprCond(self, ctx: BmcQueryParser.UnaryExprCondContext) -> None:
        """Build a condition unary expression."""
        self.nodes[ctx] = CondUnaryOp(
            cast(Any, ctx.op).text, self.nodes[ctx.bmc_cond_expression()]
        )

    def exitBinaryExprFromNumCond(
        self, ctx: BmcQueryParser.BinaryExprFromNumCondContext
    ) -> None:
        """Build a numeric comparison condition expression."""
        self.nodes[ctx] = NumericComparison(
            self.nodes[ctx.bmc_num_expression(0)],
            cast(Any, ctx.op).text,
            self.nodes[ctx.bmc_num_expression(1)],
        )

    def exitBinaryExprFromCondCond(
        self, ctx: BmcQueryParser.BinaryExprFromCondCondContext
    ) -> None:
        """Build a condition equality, inequality, or ``iff`` expression."""
        self.nodes[ctx] = CondBinaryOp(
            self.nodes[ctx.bmc_cond_expression(0)],
            cast(Any, ctx.op).text,
            self.nodes[ctx.bmc_cond_expression(1)],
        )

    def exitBinaryExprCond(self, ctx: BmcQueryParser.BinaryExprCondContext) -> None:
        """Build a logical binary condition expression."""
        self.nodes[ctx] = CondBinaryOp(
            self.nodes[ctx.bmc_cond_expression(0)],
            cast(Any, ctx.op).text,
            self.nodes[ctx.bmc_cond_expression(1)],
        )

    def exitConditionalCStyleExprCond(
        self, ctx: BmcQueryParser.ConditionalCStyleExprCondContext
    ) -> None:
        """Build a condition ternary expression."""
        self.nodes[ctx] = CondConditionalOp(
            self.nodes[ctx.bmc_cond_expression(0)],
            self.nodes[ctx.bmc_cond_expression(1)],
            self.nodes[ctx.bmc_cond_expression(2)],
        )

    def exitBmc_boolean_atom(self, ctx: BmcQueryParser.Bmc_boolean_atomContext) -> None:
        """Build one BMC-only boolean atom."""
        frame = self._optional_frame(ctx.frame_selector())
        if ctx.ACTIVE():
            self.nodes[ctx] = Active(
                self._string_value(ctx.string_literal()), frame=frame
            )
        elif ctx.TERMINATED():
            self.nodes[ctx] = Terminated(frame=frame)
        elif ctx.EVENT():
            self.nodes[ctx] = Event(
                self._string_value(ctx.string_literal()),
                selector=self.nodes[ctx.event_cycle_selector()],
            )
        elif ctx.CASE():
            self.nodes[ctx] = Case(
                self._string_value(ctx.string_literal()), frame=frame
            )
        elif ctx.CALLED():
            self.nodes[ctx] = Called(
                self._string_value(ctx.string_literal()), frame=frame
            )
        else:
            raise AssertionError(
                "Unknown BMC boolean atom: %s" % ctx.getText()
            )  # pragma: no cover

    def exitNum_literal(self, ctx: BmcQueryParser.Num_literalContext) -> None:
        """Build an integer or floating-point literal expression node."""
        if ctx.INT():
            self.nodes[ctx] = IntLiteral(cast(Any, ctx.INT()).getText(), kind="decimal")
        elif ctx.HEX_INT():
            self.nodes[ctx] = IntLiteral(cast(Any, ctx.HEX_INT()).getText(), kind="hex")
        elif ctx.FLOAT():
            self.nodes[ctx] = FloatLiteral(cast(Any, ctx.FLOAT()).getText())
        else:
            raise AssertionError(
                "Unknown numeric literal: %s" % ctx.getText()
            )  # pragma: no cover

    def exitBool_literal(self, ctx: BmcQueryParser.Bool_literalContext) -> None:
        """Build a boolean literal expression node."""
        self.nodes[ctx] = BoolLiteral(ctx.getText())

    def exitMath_const(self, ctx: BmcQueryParser.Math_constContext) -> None:
        """Build a math-constant expression node."""
        self.nodes[ctx] = MathConst(ctx.getText())

    def exitString_literal(self, ctx: BmcQueryParser.String_literalContext) -> None:
        """Decode a string literal token into a Python string."""
        self.nodes[ctx] = _decode_string_literal(cast(Any, ctx.STRING()).getText())


__all__ = ["BmcQueryParseListener"]
