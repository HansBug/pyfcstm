"""
Parse tree listener for the pyfcstm domain-specific language (DSL).

This module defines :class:`GrammarParseListener`, a concrete ANTLR4 parse tree
listener that converts DSL parse contexts into an abstract syntax tree (AST)
made of node classes from :mod:`pyfcstm.dsl.node`. The listener reacts to
``exit*`` events emitted by :class:`pyfcstm.dsl.grammar.GrammarParser` and stores
constructed nodes in an internal mapping keyed by parse contexts.

The module is intended to be used with the ANTLR4-generated parser and lexer
to build higher-level representations of:

* Numeric and conditional expressions
* Preamble and operational assignments
* State machine definitions, transitions, and events
* Import statements and import mapping rules
* Entry/exit/during operation blocks and function references

Example::

    >>> from antlr4 import CommonTokenStream, InputStream
    >>> from pyfcstm.dsl.grammar.GrammarLexer import GrammarLexer
    >>> from pyfcstm.dsl.grammar.GrammarParser import GrammarParser
    >>> from pyfcstm.dsl.listener import GrammarParseListener
    >>> from antlr4 import ParseTreeWalker
    >>>
    >>> code = "def int x = 1; state S;"
    >>> lexer = GrammarLexer(InputStream(code))
    >>> parser = GrammarParser(CommonTokenStream(lexer))
    >>> tree = parser.state_machine_dsl()
    >>> listener = GrammarParseListener()
    >>> ParseTreeWalker().walk(listener, tree)
    >>> program_node = listener.nodes[tree]
"""

import ast
from typing import Any, Dict

from .grammar import GrammarListener, GrammarParser
from .node import *
from ..utils import format_multiline_comment
from ..utils.validate import Span


_COND_BINARY_OP_ALIASES = {
    "implies": "=>",
}


def _canonical_cond_binary_op(op: str) -> str:
    return _COND_BINARY_OP_ALIASES.get(op, op)


def _ctx_span(ctx) -> Span:
    """
    Build a 1-based :class:`Span` covering an ANTLR4 parse context.

    Semantics follow common editor / LSP conventions:

    * ``line`` / ``column`` —  the 1-based start position (column points at
      the **first character** of the first token).
    * ``end_line`` / ``end_column`` — the 1-based exclusive end position
      (``end_column`` points one column **past** the last character of the
      last token, so a span covering ``[col, end_col)`` exactly contains
      the token range).

    ANTLR exposes ``token.column`` (0-based start) and ``len(token.text)``;
    we translate that into a 1-based half-open range so downstream tooling
    can highlight the matching source slice with simple substring math.

    M3 from PR-110 review: when ``stop.text`` is empty (synthetic / EOF
    tokens during ANTLR error recovery), the naive
    ``stop.column + len(stop.text) + 1`` formula would produce a
    zero-width span on a single line (``end_column == column``). Editor
    squiggles refuse to render zero-width spans, so we widen single-line
    spans by at least one column. Multi-line spans are always
    positive-width by construction.
    """
    start = ctx.start
    stop = ctx.stop if ctx.stop is not None else start
    column = start.column + 1
    end_column = stop.column + len(stop.text) + 1
    if stop.line == start.line and end_column <= column:
        end_column = column + 1
    return Span(
        line=start.line,
        column=column,
        end_line=stop.line,
        end_column=end_column,
    )


def _span_from_tokens(start, stop) -> Span:
    """Build a 1-based half-open span from two ANTLR tokens."""
    column = start.column + 1
    end_column = stop.column + len(stop.text) + 1
    if stop.line == start.line and end_column <= column:
        end_column = column + 1
    return Span(
        line=start.line,
        column=column,
        end_line=stop.line,
        end_column=end_column,
    )


def _token_start_position(token):
    return token.line, token.column + 1


def _token_end_position(token):
    return token.line, token.column + len(token.text) + 1


def _span_from_positions(start_line, start_column, end_line, end_column) -> Span:
    if end_line == start_line and end_column <= start_column:
        end_column = start_column + 1
    return Span(
        line=start_line,
        column=start_column,
        end_line=end_line,
        end_column=end_column,
    )


def _assign_combo_removal_spans(terms, term_contexts) -> None:
    if len(terms) != len(term_contexts):
        raise ValueError(
            "Combo trigger terms and term contexts must have the same length."
        )
    if len(terms) == 1:
        terms[0].removal_span = terms[0].term_span
        return

    for index, term in enumerate(terms):
        if index == 0:
            start_line, start_column = _token_start_position(term_contexts[0].start)
            end_line, end_column = _token_start_position(term_contexts[1].start)
        else:
            start_line, start_column = _token_end_position(
                term_contexts[index - 1].stop
            )
            end_line, end_column = _token_end_position(term_contexts[index].stop)
        term.removal_span = _span_from_positions(
            start_line, start_column, end_line, end_column
        )


def _parse_string_literal(raw_text: str) -> str:
    """
    Decode a DSL string literal token into a Python string.

    :param raw_text: Raw token text including surrounding quotes
    :type raw_text: str
    :return: Decoded string value
    :rtype: str
    """
    return ast.literal_eval(raw_text)


class GrammarParseListener(GrammarListener):
    """
    Parse tree listener that builds AST nodes for the pyfcstm DSL.

    The listener maintains a mapping from parse contexts to node instances.
    Each ``exit*`` method constructs the appropriate node for a grammar rule,
    linking previously created nodes for child expressions and statements.

    :ivar nodes: Mapping of parse contexts to constructed AST nodes.
    :vartype nodes: dict[object, Any]

    Example::

        >>> listener = GrammarParseListener()
        >>> listener.nodes
        {}
    """

    def __init__(self) -> None:
        """
        Initialize the listener and the internal node mapping.
        """
        super().__init__()
        self.nodes: Dict[object, Any] = {}

    def exitCondition(self, ctx: GrammarParser.ConditionContext) -> None:
        """
        Build a :class:`Condition` node from a conditional expression.

        :param ctx: Parse context for the condition rule.
        :type ctx: GrammarParser.ConditionContext
        """
        super().exitCondition(ctx)
        self.nodes[ctx] = Condition(self.nodes[ctx.cond_expression()])

    def exitUnaryExprNum(self, ctx: GrammarParser.UnaryExprNumContext) -> None:
        """
        Build a unary numeric expression node.

        :param ctx: Parse context for the unary numeric expression.
        :type ctx: GrammarParser.UnaryExprNumContext
        """
        super().exitUnaryExprNum(ctx)
        node = UnaryOp(
            op=ctx.op.text,
            expr=self.nodes[ctx.num_expression()],
        )
        self.nodes[ctx] = node

    def exitFuncExprNum(self, ctx: GrammarParser.FuncExprNumContext) -> None:
        """
        Build a unary function call numeric expression node.

        :param ctx: Parse context for the numeric function expression.
        :type ctx: GrammarParser.FuncExprNumContext
        """
        super().exitFuncExprNum(ctx)
        node = UFunc(
            func=ctx.func_name.text,
            expr=self.nodes[ctx.num_expression()],
        )
        self.nodes[ctx] = node

    def exitBinaryExprNum(self, ctx: GrammarParser.BinaryExprNumContext) -> None:
        """
        Build a binary numeric expression node.

        :param ctx: Parse context for the binary numeric expression.
        :type ctx: GrammarParser.BinaryExprNumContext
        """
        super().exitBinaryExprNum(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.num_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.num_expression(1)],
        )
        self.nodes[ctx] = node

    def exitLiteralExprNum(self, ctx: GrammarParser.LiteralExprNumContext) -> None:
        """
        Bind a numeric literal node to a numeric expression context.

        :param ctx: Parse context for the numeric literal expression.
        :type ctx: GrammarParser.LiteralExprNumContext
        """
        super().exitLiteralExprNum(ctx)
        self.nodes[ctx] = self.nodes[ctx.num_literal()]

    def exitMathConstExprNum(self, ctx: GrammarParser.MathConstExprNumContext) -> None:
        """
        Bind a math constant node to a numeric expression context.

        :param ctx: Parse context for the math constant numeric expression.
        :type ctx: GrammarParser.MathConstExprNumContext
        """
        super().exitMathConstExprNum(ctx)
        self.nodes[ctx] = self.nodes[ctx.math_const()]

    def exitParenExprNum(self, ctx: GrammarParser.ParenExprNumContext) -> None:
        """
        Wrap a numeric expression in a :class:`Paren` node.

        :param ctx: Parse context for the parenthesized numeric expression.
        :type ctx: GrammarParser.ParenExprNumContext
        """
        super().exitParenExprNum(ctx)
        node = Paren(self.nodes[ctx.num_expression()])
        self.nodes[ctx] = node

    def exitIdExprNum(self, ctx: GrammarParser.IdExprNumContext) -> None:
        """
        Build a numeric name reference node.

        :param ctx: Parse context for the identifier numeric expression.
        :type ctx: GrammarParser.IdExprNumContext
        """
        super().exitIdExprNum(ctx)
        node = Name(ctx.getText())
        self.nodes[ctx] = node

    def exitBinaryExprFromNumCond(
        self, ctx: GrammarParser.BinaryExprFromNumCondContext
    ) -> None:
        """
        Build a conditional expression node that compares numeric expressions.

        :param ctx: Parse context for the binary numeric-to-condition expression.
        :type ctx: GrammarParser.BinaryExprFromNumCondContext
        """
        super().exitBinaryExprFromNumCond(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.num_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.num_expression(1)],
        )
        self.nodes[ctx] = node

    def _exit_cond_binary_expression(self, ctx, expr1, expr2) -> None:
        self.nodes[ctx] = BinaryOp(
            expr1=expr1,
            op=_canonical_cond_binary_op(ctx.op.text),
            expr2=expr2,
        )

    def exitBinaryExprFromCondCond(
        self, ctx: GrammarParser.BinaryExprFromCondCondContext
    ) -> None:
        """
        Build a binary conditional expression node.

        :param ctx: Parse context for the binary condition-to-condition expression.
        :type ctx: GrammarParser.BinaryExprFromCondCondContext
        """
        super().exitBinaryExprFromCondCond(ctx)
        self._exit_cond_binary_expression(
            ctx,
            expr1=self.nodes[ctx.cond_expression(0)],
            expr2=self.nodes[ctx.cond_expression(1)],
        )

    def exitBinaryExprCond(self, ctx: GrammarParser.BinaryExprCondContext) -> None:
        """
        Build a binary conditional expression node.

        :param ctx: Parse context for the binary conditional expression.
        :type ctx: GrammarParser.BinaryExprCondContext
        """
        super().exitBinaryExprCond(ctx)
        self._exit_cond_binary_expression(
            ctx,
            expr1=self.nodes[ctx.cond_expression(0)],
            expr2=self.nodes[ctx.cond_expression(1)],
        )

    def exitUnaryExprCond(self, ctx: GrammarParser.UnaryExprCondContext) -> None:
        """
        Build a unary conditional expression node.

        :param ctx: Parse context for the unary conditional expression.
        :type ctx: GrammarParser.UnaryExprCondContext
        """
        super().exitUnaryExprCond(ctx)
        node = UnaryOp(
            op=ctx.op.text,
            expr=self.nodes[ctx.cond_expression()],
        )
        self.nodes[ctx] = node

    def exitParenExprCond(self, ctx: GrammarParser.ParenExprCondContext) -> None:
        """
        Wrap a conditional expression in a :class:`Paren` node.

        :param ctx: Parse context for the parenthesized conditional expression.
        :type ctx: GrammarParser.ParenExprCondContext
        """
        super().exitParenExprCond(ctx)
        node = Paren(self.nodes[ctx.cond_expression()])
        self.nodes[ctx] = node

    def exitLiteralExprCond(self, ctx: GrammarParser.LiteralExprCondContext) -> None:
        """
        Bind a boolean literal node to a conditional expression.

        :param ctx: Parse context for the boolean literal conditional expression.
        :type ctx: GrammarParser.LiteralExprCondContext
        """
        super().exitLiteralExprCond(ctx)
        self.nodes[ctx] = self.nodes[ctx.bool_literal()]

    def exitNum_literal(self, ctx: GrammarParser.Num_literalContext) -> None:
        """
        Build a numeric literal node (integer, float, or hex integer).

        :param ctx: Parse context for the numeric literal.
        :type ctx: GrammarParser.Num_literalContext
        """
        super().exitNum_literal(ctx)
        if ctx.INT():
            node = Integer(str(ctx.INT()))
        elif ctx.FLOAT():
            node = Float(str(ctx.FLOAT()))
        elif ctx.HEX_INT():
            node = HexInt(str(ctx.HEX_INT()))
        else:
            assert False, f"Should not reach this line - {ctx!r}."  # pragma: no cover
        self.nodes[ctx] = node

    def exitBool_literal(self, ctx: GrammarParser.Bool_literalContext) -> None:
        """
        Build a boolean literal node.

        :param ctx: Parse context for the boolean literal.
        :type ctx: GrammarParser.Bool_literalContext
        """
        super().exitBool_literal(ctx)
        node = Boolean(ctx.getText().lower())
        self.nodes[ctx] = node

    def exitMath_const(self, ctx: GrammarParser.Math_constContext) -> None:
        """
        Build a math constant node.

        :param ctx: Parse context for the math constant.
        :type ctx: GrammarParser.Math_constContext
        """
        super().exitMath_const(ctx)
        node = Constant(ctx.getText())
        self.nodes[ctx] = node

    def exitOperation_program(
        self, ctx: GrammarParser.Operation_programContext
    ) -> None:
        """
        Build an operation program node from operational assignments.

        :param ctx: Parse context for the operation program.
        :type ctx: GrammarParser.Operation_programContext
        """
        super().exitOperation_program(ctx)
        self.nodes[ctx] = Operation(
            [self.nodes[stat] for stat in ctx.operational_assignment()]
        )

    def exitPreamble_program(self, ctx: GrammarParser.Preamble_programContext) -> None:
        """
        Build a preamble program node from preamble statements.

        :param ctx: Parse context for the preamble program.
        :type ctx: GrammarParser.Preamble_programContext
        """
        super().exitPreamble_program(ctx)
        self.nodes[ctx] = Preamble(
            [self.nodes[stat] for stat in ctx.preamble_statement()]
        )

    def exitPreamble_statement(
        self, ctx: GrammarParser.Preamble_statementContext
    ) -> None:
        """
        Bind a preamble statement to its specific node.

        :param ctx: Parse context for the preamble statement.
        :type ctx: GrammarParser.Preamble_statementContext
        """
        super().exitPreamble_statement(ctx)
        self.nodes[ctx] = self.nodes[
            ctx.initial_assignment() or ctx.constant_definition()
        ]

    def exitInitial_assignment(
        self, ctx: GrammarParser.Initial_assignmentContext
    ) -> None:
        """
        Build an initial assignment node.

        :param ctx: Parse context for the initial assignment.
        :type ctx: GrammarParser.Initial_assignmentContext
        """
        super().exitInitial_assignment(ctx)
        self.nodes[ctx] = InitialAssignment(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.init_expression()],
        )

    def exitConstant_definition(
        self, ctx: GrammarParser.Constant_definitionContext
    ) -> None:
        """
        Build a constant definition node.

        :param ctx: Parse context for the constant definition.
        :type ctx: GrammarParser.Constant_definitionContext
        """
        super().exitConstant_definition(ctx)
        self.nodes[ctx] = ConstantDefinition(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.init_expression()],
        )

    def exitOperational_assignment(
        self, ctx: GrammarParser.Operational_assignmentContext
    ) -> None:
        """
        Build an operational (deprecated) assignment node.

        :param ctx: Parse context for the operational assignment.
        :type ctx: GrammarParser.Operational_assignmentContext
        """
        super().exitOperational_assignment(ctx)
        self.nodes[ctx] = OperationalDeprecatedAssignment(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.num_expression()],
        )

    def exitFuncExprInit(self, ctx: GrammarParser.FuncExprInitContext) -> None:
        """
        Build a function call node in initialization expressions.

        :param ctx: Parse context for the function init expression.
        :type ctx: GrammarParser.FuncExprInitContext
        """
        super().exitFuncExprInit(ctx)
        self.nodes[ctx] = UFunc(
            func=ctx.func_name.text,
            expr=self.nodes[ctx.init_expression()],
        )

    def exitUnaryExprInit(self, ctx: GrammarParser.UnaryExprInitContext) -> None:
        """
        Build a unary operation node in initialization expressions.

        :param ctx: Parse context for the unary init expression.
        :type ctx: GrammarParser.UnaryExprInitContext
        """
        super().exitUnaryExprInit(ctx)
        self.nodes[ctx] = UnaryOp(
            op=ctx.op.text,
            expr=self.nodes[ctx.init_expression()],
        )

    def exitBinaryExprInit(self, ctx: GrammarParser.BinaryExprInitContext) -> None:
        """
        Build a binary operation node in initialization expressions.

        :param ctx: Parse context for the binary init expression.
        :type ctx: GrammarParser.BinaryExprInitContext
        """
        super().exitBinaryExprInit(ctx)
        self.nodes[ctx] = BinaryOp(
            expr1=self.nodes[ctx.init_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.init_expression(1)],
        )

    def exitLiteralExprInit(self, ctx: GrammarParser.LiteralExprInitContext) -> None:
        """
        Bind a numeric literal to an initialization expression.

        :param ctx: Parse context for the literal init expression.
        :type ctx: GrammarParser.LiteralExprInitContext
        """
        super().exitLiteralExprInit(ctx)
        self.nodes[ctx] = self.nodes[ctx.num_literal()]

    def exitMathConstExprInit(
        self, ctx: GrammarParser.MathConstExprInitContext
    ) -> None:
        """
        Bind a math constant to an initialization expression.

        :param ctx: Parse context for the math constant init expression.
        :type ctx: GrammarParser.MathConstExprInitContext
        """
        super().exitMathConstExprInit(ctx)
        self.nodes[ctx] = self.nodes[ctx.math_const()]

    def exitParenExprInit(self, ctx: GrammarParser.ParenExprInitContext) -> None:
        """
        Wrap an initialization expression in a :class:`Paren` node.

        :param ctx: Parse context for the parenthesized init expression.
        :type ctx: GrammarParser.ParenExprInitContext
        """
        super().exitParenExprInit(ctx)
        self.nodes[ctx] = Paren(self.nodes[ctx.init_expression()])

    def exitConditionalCStyleExprNum(
        self, ctx: GrammarParser.ConditionalCStyleExprNumContext
    ) -> None:
        """
        Build a C-style conditional operator node for numeric expressions.

        :param ctx: Parse context for the conditional numeric expression.
        :type ctx: GrammarParser.ConditionalCStyleExprNumContext
        """
        super().exitConditionalCStyleExprNum(ctx)
        self.nodes[ctx] = ConditionalOp(
            cond=self.nodes[ctx.cond_expression()],
            value_true=self.nodes[ctx.num_expression(0)],
            value_false=self.nodes[ctx.num_expression(1)],
        )

    def exitConditionalCStyleCondNum(
        self, ctx: GrammarParser.ConditionalCStyleCondNumContext
    ) -> None:
        """
        Build a C-style conditional operator node for conditional expressions.

        :param ctx: Parse context for the conditional conditional expression.
        :type ctx: GrammarParser.ConditionalCStyleCondNumContext
        """
        super().exitConditionalCStyleCondNum(ctx)
        self.nodes[ctx] = ConditionalOp(
            cond=self.nodes[ctx.cond_expression(0)],
            value_true=self.nodes[ctx.cond_expression(1)],
            value_false=self.nodes[ctx.cond_expression(2)],
        )

    def exitDef_assignment(self, ctx: GrammarParser.Def_assignmentContext) -> None:
        """
        Build a definition assignment node.

        :param ctx: Parse context for the definition assignment.
        :type ctx: GrammarParser.Def_assignmentContext
        """
        super().exitDef_assignment(ctx)
        node = DefAssignment(
            name=str(ctx.ID()),
            type=ctx.deftype.text,
            expr=self.nodes[ctx.init_expression()],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitState_machine_dsl(
        self, ctx: GrammarParser.State_machine_dslContext
    ) -> None:
        """
        Build the root program node for a state machine DSL document.

        :param ctx: Parse context for the state machine DSL program.
        :type ctx: GrammarParser.State_machine_dslContext
        """
        super().exitState_machine_dsl(ctx)
        self.nodes[ctx] = StateMachineDSLProgram(
            definitions=[self.nodes[item] for item in ctx.def_assignment()],
            root_state=self.nodes[ctx.state_definition()],
        )

    def exitLeafStateDefinition(
        self, ctx: GrammarParser.LeafStateDefinitionContext
    ) -> None:
        """
        Build a leaf :class:`StateDefinition` node.

        :param ctx: Parse context for the leaf state definition.
        :type ctx: GrammarParser.LeafStateDefinitionContext
        """
        super().exitLeafStateDefinition(ctx)
        node = StateDefinition(
            name=str(ctx.ID()),
            extra_name=_parse_string_literal(ctx.extra_name.text)
            if ctx.extra_name
            else None,
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            is_pseudo=bool(ctx.pseudo),
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitCompositeStateDefinition(
        self, ctx: GrammarParser.CompositeStateDefinitionContext
    ) -> None:
        """
        Build a composite :class:`StateDefinition` node.

        :param ctx: Parse context for the composite state definition.
        :type ctx: GrammarParser.CompositeStateDefinitionContext
        """
        super().exitCompositeStateDefinition(ctx)
        node = StateDefinition(
            name=str(ctx.ID()),
            extra_name=_parse_string_literal(ctx.extra_name.text)
            if ctx.extra_name
            else None,
            events=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes and isinstance(self.nodes[item], EventDefinition)
            ],
            imports=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes and isinstance(self.nodes[item], ImportStatement)
            ],
            substates=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes and isinstance(self.nodes[item], StateDefinition)
            ],
            transitions=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes
                and isinstance(self.nodes[item], TransitionDefinition)
            ],
            enters=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes and isinstance(self.nodes[item], EnterStatement)
            ],
            durings=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes and isinstance(self.nodes[item], DuringStatement)
            ],
            exits=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes and isinstance(self.nodes[item], ExitStatement)
            ],
            during_aspects=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes
                and isinstance(self.nodes[item], DuringAspectStatement)
            ],
            force_transitions=[
                self.nodes[item]
                for item in ctx.state_inner_statement()
                if item in self.nodes
                and isinstance(self.nodes[item], ForceTransitionDefinition)
            ],
            is_pseudo=bool(ctx.pseudo),
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def _first_combo_event_term(self, trigger: ComboTransitionTrigger):
        for term in trigger.terms:
            if isinstance(term, ComboEventTerm):
                return term
        return None

    def _single_guard_alias_expr(self, trigger: ComboTransitionTrigger):
        if (
            trigger.scope_prefix == ":"
            and len(trigger.terms) == 1
            and isinstance(trigger.terms[0], ComboGuardTerm)
        ):
            return trigger.terms[0].condition_expr
        return None

    def _normalize_entry_combo_trigger(self, trigger: ComboTransitionTrigger) -> None:
        for term in trigger.terms:
            if (
                isinstance(term, ComboEventTerm)
                and term.event_scope == "local"
                and not term.event_id.is_absolute
            ):
                term.event_scope = "chain"

    def _build_transition_node(
        self,
        *,
        from_state,
        to_state,
        trigger_ctx,
        post_operations,
    ) -> TransitionDefinition:
        combo_trigger = self.nodes[trigger_ctx] if trigger_ctx else None
        event_id = None
        condition_expr = None
        event_scope = None
        stored_combo_trigger = None
        if combo_trigger is not None:
            if from_state is INIT_STATE:
                self._normalize_entry_combo_trigger(combo_trigger)
            condition_expr = self._single_guard_alias_expr(combo_trigger)
            event_term = self._first_combo_event_term(combo_trigger)
            if condition_expr is None and event_term is not None:
                event_id = event_term.event_id
                event_scope = event_term.event_scope
                if (
                    not combo_trigger.is_combo
                    and from_state is INIT_STATE
                    and event_scope == "local"
                ):
                    event_scope = "chain"
                if (
                    event_scope == "local"
                    and isinstance(from_state, str)
                    and not event_id.is_absolute
                    and len(event_id.path) == 1
                ):
                    event_id = ChainID([from_state, event_id.path[0]])
            if combo_trigger.is_combo or condition_expr is not None:
                stored_combo_trigger = combo_trigger

        node = TransitionDefinition(
            from_state=from_state,
            to_state=to_state,
            event_id=event_id,
            condition_expr=condition_expr,
            post_operations=post_operations,
            event_scope=event_scope,
            combo_trigger=stored_combo_trigger,
        )
        return node

    def exitEntryTransitionDefinition(
        self, ctx: GrammarParser.EntryTransitionDefinitionContext
    ) -> None:
        """
        Build an entry transition definition node.

        :param ctx: Parse context for the entry transition definition.
        :type ctx: GrammarParser.EntryTransitionDefinitionContext
        """
        super().exitEntryTransitionDefinition(ctx)
        node = self._build_transition_node(
            from_state=INIT_STATE,
            to_state=ctx.to_state.text,
            trigger_ctx=ctx.combo_transition_trigger(),
            post_operations=self.nodes[ctx.operational_statement_set()]
            if ctx.operational_statement_set()
            else [],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitNormalTransitionDefinition(
        self, ctx: GrammarParser.NormalTransitionDefinitionContext
    ) -> None:
        """
        Build a normal transition definition node.

        :param ctx: Parse context for the normal transition definition.
        :type ctx: GrammarParser.NormalTransitionDefinitionContext
        """
        super().exitNormalTransitionDefinition(ctx)
        node = self._build_transition_node(
            from_state=ctx.from_state.text,
            to_state=ctx.to_state.text,
            trigger_ctx=ctx.combo_transition_trigger(),
            post_operations=self.nodes[ctx.operational_statement_set()]
            if ctx.operational_statement_set()
            else [],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitExitTransitionDefinition(
        self, ctx: GrammarParser.ExitTransitionDefinitionContext
    ) -> None:
        """
        Build an exit transition definition node.

        :param ctx: Parse context for the exit transition definition.
        :type ctx: GrammarParser.ExitTransitionDefinitionContext
        """
        super().exitExitTransitionDefinition(ctx)
        node = self._build_transition_node(
            from_state=ctx.from_state.text,
            to_state=EXIT_STATE,
            trigger_ctx=ctx.combo_transition_trigger(),
            post_operations=self.nodes[ctx.operational_statement_set()]
            if ctx.operational_statement_set()
            else [],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitCombo_event_term(self, ctx: GrammarParser.Combo_event_termContext) -> None:
        """
        Bind a combo event term to its chain identifier.

        :param ctx: Parse context for the combo event term.
        :type ctx: GrammarParser.Combo_event_termContext
        """
        super().exitCombo_event_term(ctx)
        self.nodes[ctx] = self.nodes[ctx.chain_id()]

    def exitCombo_guard_term(self, ctx: GrammarParser.Combo_guard_termContext) -> None:
        """
        Build a combo guard term from a bracketed condition.

        :param ctx: Parse context for the combo guard term.
        :type ctx: GrammarParser.Combo_guard_termContext
        """
        super().exitCombo_guard_term(ctx)
        node = ComboGuardTerm(
            condition_expr=self.nodes[ctx.cond_expression()],
            term_span=_ctx_span(ctx),
            removal_span=_ctx_span(ctx),
            value_span=_ctx_span(ctx.cond_expression()),
        )
        self.nodes[ctx] = node

    def exitCombo_trigger_term(
        self, ctx: GrammarParser.Combo_trigger_termContext
    ) -> None:
        """
        Bind a combo trigger term to an event or guard term node.

        :param ctx: Parse context for the combo trigger term.
        :type ctx: GrammarParser.Combo_trigger_termContext
        """
        super().exitCombo_trigger_term(ctx)
        if ctx.combo_guard_term():
            self.nodes[ctx] = self.nodes[ctx.combo_guard_term()]
        else:
            self.nodes[ctx] = self.nodes[ctx.combo_event_term()]

    def _build_combo_trigger(
        self,
        ctx,
        *,
        scope_prefix: str,
        event_scope: str,
    ) -> ComboTransitionTrigger:
        terms = []
        term_contexts = list(ctx.combo_trigger_term())
        for term_ctx in term_contexts:
            term_node = self.nodes[term_ctx]
            if isinstance(term_node, ChainID):
                scoped_event_id = term_node
                scoped_event_scope = (
                    "absolute" if term_node.is_absolute else event_scope
                )
                if event_scope == "local" and not term_node.is_absolute:
                    scoped_event_id = ChainID(
                        path=list(term_node.path), is_absolute=False
                    )
                    scoped_event_scope = "local"
                term = ComboEventTerm(
                    event_id=scoped_event_id,
                    event_scope=scoped_event_scope,
                    term_span=_ctx_span(term_ctx),
                    removal_span=_ctx_span(term_ctx),
                )
            else:
                term = term_node
            terms.append(term)

        _assign_combo_removal_spans(terms, term_contexts)
        trigger = ComboTransitionTrigger(
            scope_prefix=scope_prefix,
            terms=terms,
            trigger_span=_ctx_span(ctx),
        )
        return trigger

    def exitLocal_combo_event_term(
        self, ctx: GrammarParser.Local_combo_event_termContext
    ) -> None:
        """
        Build a source-local combo event identifier from a bare event name.

        :param ctx: Parse context for the local combo event term.
        :type ctx: GrammarParser.Local_combo_event_termContext
        """
        super().exitLocal_combo_event_term(ctx)
        self.nodes[ctx] = ctx.ID().getText()

    def exitLocal_combo_trigger_term(
        self, ctx: GrammarParser.Local_combo_trigger_termContext
    ) -> None:
        """
        Bind a source-local combo continuation term.

        :param ctx: Parse context for the local combo continuation term.
        :type ctx: GrammarParser.Local_combo_trigger_termContext
        """
        super().exitLocal_combo_trigger_term(ctx)
        if ctx.local_combo_event_term():
            self.nodes[ctx] = self.nodes[ctx.local_combo_event_term()]
        else:
            self.nodes[ctx] = self.nodes[ctx.combo_guard_term()]

    def exitLocal_combo_leading_guard(
        self, ctx: GrammarParser.Local_combo_leading_guardContext
    ) -> None:
        """
        Bind a leading guard term in a source-local combo trigger.

        :param ctx: Parse context for a guard term followed by ``+``.
        :type ctx: GrammarParser.Local_combo_leading_guardContext
        """
        super().exitLocal_combo_leading_guard(ctx)
        self.nodes[ctx] = self.nodes[ctx.combo_guard_term()]

    def exitLocal_combo_trigger(
        self, ctx: GrammarParser.Local_combo_triggerContext
    ) -> None:
        """
        Build a source-local combo trigger term list.

        :param ctx: Parse context for the local combo trigger.
        :type ctx: GrammarParser.Local_combo_triggerContext
        """
        super().exitLocal_combo_trigger(ctx)
        terms = []
        term_contexts = []
        for leading_guard in ctx.local_combo_leading_guard():
            terms.append(self.nodes[leading_guard])
            term_contexts.append(leading_guard.combo_guard_term())

        event_name = self.nodes[ctx.local_combo_event_term()]
        terms.append(
            ComboEventTerm(
                event_id=ChainID([event_name]),
                event_scope="local",
                term_span=_ctx_span(ctx.local_combo_event_term()),
                removal_span=_ctx_span(ctx.local_combo_event_term()),
            )
        )
        term_contexts.append(ctx.local_combo_event_term())

        for term_ctx in ctx.local_combo_trigger_term():
            term_node = self.nodes[term_ctx]
            if isinstance(term_node, str):
                term = ComboEventTerm(
                    event_id=ChainID([term_node]),
                    event_scope="local",
                    term_span=_ctx_span(term_ctx),
                    removal_span=_ctx_span(term_ctx),
                )
            else:
                term = term_node
            terms.append(term)
            term_contexts.append(
                term_ctx.local_combo_event_term() or term_ctx.combo_guard_term()
            )

        _assign_combo_removal_spans(terms, term_contexts)
        self.nodes[ctx] = ComboTransitionTrigger(
            scope_prefix="::",
            terms=terms,
            trigger_span=_ctx_span(ctx),
        )

    def exitChain_combo_guard_alias(
        self, ctx: GrammarParser.Chain_combo_guard_aliasContext
    ) -> None:
        """
        Build the pure guard alias trigger used by ``: [guard]``.

        :param ctx: Parse context for the guard alias trigger.
        :type ctx: GrammarParser.Chain_combo_guard_aliasContext
        """
        super().exitChain_combo_guard_alias(ctx)
        self.nodes[ctx] = ComboTransitionTrigger(
            scope_prefix=":",
            terms=[self.nodes[ctx.combo_guard_term()]],
            trigger_span=_ctx_span(ctx),
        )

    def exitChain_combo_trigger(
        self, ctx: GrammarParser.Chain_combo_triggerContext
    ) -> None:
        """
        Build a chain-scope combo trigger term list.

        :param ctx: Parse context for the chain combo trigger.
        :type ctx: GrammarParser.Chain_combo_triggerContext
        """
        super().exitChain_combo_trigger(ctx)
        if ctx.chain_combo_guard_alias():
            self.nodes[ctx] = self.nodes[ctx.chain_combo_guard_alias()]
        elif ctx.combo_event_term() is not None:
            event_id = self.nodes[ctx.combo_event_term()]
            self.nodes[ctx] = ComboTransitionTrigger(
                scope_prefix=":",
                terms=[
                    ComboEventTerm(
                        event_id=event_id,
                        event_scope="absolute" if event_id.is_absolute else "chain",
                        term_span=_ctx_span(ctx.combo_event_term()),
                        removal_span=_ctx_span(ctx.combo_event_term()),
                    )
                ],
                trigger_span=_ctx_span(ctx),
            )
        else:
            self.nodes[ctx] = self._build_combo_trigger(
                ctx,
                scope_prefix=":",
                event_scope="chain",
            )

    def _guard_trigger_from_legacy_syntax(
        self, ctx: GrammarParser.Combo_transition_triggerContext
    ) -> ComboTransitionTrigger:
        cond = ctx.cond_expression()
        term_start = ctx.LBRACK().symbol
        term_stop = ctx.RBRACK().symbol
        term = ComboGuardTerm(
            condition_expr=self.nodes[cond],
            term_span=_span_from_tokens(term_start, term_stop),
            removal_span=_span_from_tokens(term_start, term_stop),
            value_span=_ctx_span(cond),
        )
        return ComboTransitionTrigger(
            scope_prefix=":",
            terms=[term],
            trigger_span=_ctx_span(ctx),
        )

    def exitCombo_transition_trigger(
        self, ctx: GrammarParser.Combo_transition_triggerContext
    ) -> None:
        """
        Build the complete transition trigger suffix.

        :param ctx: Parse context for the transition trigger suffix.
        :type ctx: GrammarParser.Combo_transition_triggerContext
        """
        super().exitCombo_transition_trigger(ctx)
        if ctx.local_combo_trigger():
            trigger = self.nodes[ctx.local_combo_trigger()]
        elif ctx.chain_combo_trigger():
            trigger = self.nodes[ctx.chain_combo_trigger()]
        else:
            trigger = self._guard_trigger_from_legacy_syntax(ctx)
        trigger.trigger_span = _ctx_span(ctx)
        self.nodes[ctx] = trigger

    def exitChain_id(self, ctx: GrammarParser.Chain_idContext) -> None:
        """
        Build a chain identifier node.

        :param ctx: Parse context for the chain identifier.
        :type ctx: GrammarParser.Chain_idContext
        """
        super().exitChain_id(ctx)
        self.nodes[ctx] = ChainID(
            path=list(map(str, ctx.ID())),
            is_absolute=bool(ctx.isabs),
        )

    def exitOperational_statement(
        self, ctx: GrammarParser.Operational_statementContext
    ) -> None:
        """
        Bind an operational statement to its concrete statement node.

        :param ctx: Parse context for the operational statement.
        :type ctx: GrammarParser.Operational_statementContext
        """
        super().exitOperational_statement(ctx)
        if ctx.operation_assignment():
            self.nodes[ctx] = self.nodes[ctx.operation_assignment()]
        elif ctx.if_statement():
            self.nodes[ctx] = self.nodes[ctx.if_statement()]

    def exitOperation_block(self, ctx: GrammarParser.Operation_blockContext) -> None:
        """
        Bind an operation block to its statement list.

        :param ctx: Parse context for the operation block.
        :type ctx: GrammarParser.Operation_blockContext
        """
        super().exitOperation_block(ctx)
        self.nodes[ctx] = self.nodes[ctx.operational_statement_set()]

    def exitIf_statement(self, ctx: GrammarParser.If_statementContext) -> None:
        """
        Build an operation-block ``if`` statement node.

        :param ctx: Parse context for the ``if`` statement.
        :type ctx: GrammarParser.If_statementContext
        """
        super().exitIf_statement(ctx)
        conditions = list(ctx.cond_expression())
        blocks = list(ctx.operation_block())

        branches = []
        for condition, block in zip(conditions, blocks[: len(conditions)]):
            branch = OperationIfBranch(
                condition=self.nodes[condition],
                statements=self.nodes[block],
            )
            # Branch spans intentionally cover the executable operation block.
            # The condition text remains covered by the parent OperationIf span;
            # expression-level guard spans are a separate diagnostic contract.
            branch._span = _ctx_span(block)
            branches.append(branch)

        if len(blocks) > len(conditions):
            branch = OperationIfBranch(
                condition=None,
                statements=self.nodes[blocks[-1]],
            )
            # Keep else-branch semantics aligned with condition branches: the
            # branch span points at the executable block, not the ``else`` token.
            branch._span = _ctx_span(blocks[-1])
            branches.append(branch)

        node = OperationIf(branches=branches)
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitOperational_statement_set(
        self, ctx: GrammarParser.Operational_statement_setContext
    ) -> None:
        """
        Build a list of operational statements from the statement set.

        :param ctx: Parse context for the operational statement set.
        :type ctx: GrammarParser.Operational_statement_setContext
        """
        super().exitOperational_statement_set(ctx)
        self.nodes[ctx] = [
            self.nodes[item]
            for item in ctx.operational_statement()
            if item in self.nodes
        ]

    def exitState_inner_statement(
        self, ctx: GrammarParser.State_inner_statementContext
    ) -> None:
        """
        Bind a state inner statement to its specific node.

        :param ctx: Parse context for the state inner statement.
        :type ctx: GrammarParser.State_inner_statementContext
        """
        super().exitState_inner_statement(ctx)
        if ctx.state_definition():
            self.nodes[ctx] = self.nodes[ctx.state_definition()]
        elif ctx.transition_definition():
            self.nodes[ctx] = self.nodes[ctx.transition_definition()]
        elif ctx.enter_definition():
            self.nodes[ctx] = self.nodes[ctx.enter_definition()]
        elif ctx.during_definition():
            self.nodes[ctx] = self.nodes[ctx.during_definition()]
        elif ctx.exit_definition():
            self.nodes[ctx] = self.nodes[ctx.exit_definition()]
        elif ctx.during_aspect_definition():
            self.nodes[ctx] = self.nodes[ctx.during_aspect_definition()]
        elif ctx.transition_force_definition():
            self.nodes[ctx] = self.nodes[ctx.transition_force_definition()]
        elif ctx.event_definition():
            self.nodes[ctx] = self.nodes[ctx.event_definition()]
        elif ctx.import_statement():
            self.nodes[ctx] = self.nodes[ctx.import_statement()]

    def exitOperation_assignment(
        self, ctx: GrammarParser.Operation_assignmentContext
    ) -> None:
        """
        Build an operation assignment node.

        :param ctx: Parse context for the operation assignment.
        :type ctx: GrammarParser.Operation_assignmentContext
        """
        super().exitOperation_assignment(ctx)
        node = OperationAssignment(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.num_expression()],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitEnterOperations(self, ctx: GrammarParser.EnterOperationsContext) -> None:
        """
        Build an enter-operations node.

        :param ctx: Parse context for the enter operations.
        :type ctx: GrammarParser.EnterOperationsContext
        """
        super().exitEnterOperations(ctx)
        node = EnterOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            operations=self.nodes[ctx.operational_statement_set()]
            if ctx.operational_statement_set()
            else [],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitEnterAbstractFunc(
        self, ctx: GrammarParser.EnterAbstractFuncContext
    ) -> None:
        """
        Build an enter abstract function node.

        :param ctx: Parse context for the enter abstract function.
        :type ctx: GrammarParser.EnterAbstractFuncContext
        """
        super().exitEnterAbstractFunc(ctx)
        node = EnterAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitEnterRefFunc(self, ctx: GrammarParser.EnterRefFuncContext) -> None:
        """
        Build an enter reference function node.

        :param ctx: Parse context for the enter reference function.
        :type ctx: GrammarParser.EnterRefFuncContext
        """
        super().exitEnterRefFunc(ctx)
        node = EnterRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            ref=self.nodes[ctx.chain_id()],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitExitOperations(self, ctx: GrammarParser.ExitOperationsContext) -> None:
        """
        Build an exit-operations node.

        :param ctx: Parse context for the exit operations.
        :type ctx: GrammarParser.ExitOperationsContext
        """
        super().exitExitOperations(ctx)
        node = ExitOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            operations=self.nodes[ctx.operational_statement_set()]
            if ctx.operational_statement_set()
            else [],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitExitAbstractFunc(self, ctx: GrammarParser.ExitAbstractFuncContext) -> None:
        """
        Build an exit abstract function node.

        :param ctx: Parse context for the exit abstract function.
        :type ctx: GrammarParser.ExitAbstractFuncContext
        """
        super().exitExitAbstractFunc(ctx)
        node = ExitAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitExitRefFunc(self, ctx: GrammarParser.ExitRefFuncContext) -> None:
        """
        Build an exit reference function node.

        :param ctx: Parse context for the exit reference function.
        :type ctx: GrammarParser.ExitRefFuncContext
        """
        super().exitExitRefFunc(ctx)
        node = ExitRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            ref=self.nodes[ctx.chain_id()],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitDuringOperations(self, ctx: GrammarParser.DuringOperationsContext) -> None:
        """
        Build a during-operations node.

        :param ctx: Parse context for the during operations.
        :type ctx: GrammarParser.DuringOperationsContext
        """
        super().exitDuringOperations(ctx)
        node = DuringOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            operations=self.nodes[ctx.operational_statement_set()]
            if ctx.operational_statement_set()
            else [],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitDuringAbstractFunc(
        self, ctx: GrammarParser.DuringAbstractFuncContext
    ) -> None:
        """
        Build a during abstract function node.

        :param ctx: Parse context for the during abstract function.
        :type ctx: GrammarParser.DuringAbstractFuncContext
        """
        super().exitDuringAbstractFunc(ctx)
        node = DuringAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitDuringRefFunc(self, ctx: GrammarParser.DuringRefFuncContext) -> None:
        """
        Build a during reference function node.

        :param ctx: Parse context for the during reference function.
        :type ctx: GrammarParser.DuringRefFuncContext
        """
        super().exitDuringRefFunc(ctx)
        node = DuringRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            ref=self.nodes[ctx.chain_id()],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitGeneric_expression(
        self, ctx: GrammarParser.Generic_expressionContext
    ) -> None:
        """
        Bind a generic expression to either a numeric or conditional node.

        :param ctx: Parse context for the generic expression.
        :type ctx: GrammarParser.Generic_expressionContext
        """
        if ctx.num_expression():
            self.nodes[ctx] = self.nodes[ctx.num_expression()]
        elif ctx.cond_expression():
            self.nodes[ctx] = self.nodes[ctx.cond_expression()]

    def exitDuringAspectOperations(
        self, ctx: GrammarParser.DuringAspectOperationsContext
    ) -> None:
        """
        Build a during-aspect operations node.

        :param ctx: Parse context for the during aspect operations.
        :type ctx: GrammarParser.DuringAspectOperationsContext
        """
        super().exitDuringAspectOperations(ctx)
        node = DuringAspectOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            operations=self.nodes[ctx.operational_statement_set()]
            if ctx.operational_statement_set()
            else [],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitDuringAspectAbstractFunc(
        self, ctx: GrammarParser.DuringAspectAbstractFuncContext
    ) -> None:
        """
        Build a during-aspect abstract function node.

        :param ctx: Parse context for the during aspect abstract function.
        :type ctx: GrammarParser.DuringAspectAbstractFuncContext
        """
        super().exitDuringAspectAbstractFunc(ctx)
        node = DuringAspectAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitDuringAspectRefFunc(
        self, ctx: GrammarParser.DuringAspectRefFuncContext
    ) -> None:
        """
        Build a during-aspect reference function node.

        :param ctx: Parse context for the during aspect reference function.
        :type ctx: GrammarParser.DuringAspectRefFuncContext
        """
        super().exitDuringAspectRefFunc(ctx)
        node = DuringAspectRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            ref=self.nodes[ctx.chain_id()],
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitNormalForceTransitionDefinition(
        self, ctx: GrammarParser.NormalForceTransitionDefinitionContext
    ) -> None:
        """
        Build a normal force transition definition node.

        :param ctx: Parse context for the normal force transition definition.
        :type ctx: GrammarParser.NormalForceTransitionDefinitionContext
        """
        super().exitNormalForceTransitionDefinition(ctx)
        event_id = None
        if ctx.chain_id():
            event_id = self.nodes[ctx.chain_id()]
            event_scope = "absolute" if event_id.is_absolute else "chain"
        elif ctx.from_id:
            event_id = ChainID([ctx.from_state.text, ctx.from_id.text])
            event_scope = "local"
        else:
            event_scope = None
        node = ForceTransitionDefinition(
            from_state=ctx.from_state.text,
            to_state=ctx.to_state.text,
            event_id=event_id,
            condition_expr=self.nodes[ctx.cond_expression()]
            if ctx.cond_expression()
            else None,
            event_scope=event_scope,
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitExitForceTransitionDefinition(
        self, ctx: GrammarParser.ExitForceTransitionDefinitionContext
    ) -> None:
        """
        Build an exit force transition definition node.

        :param ctx: Parse context for the exit force transition definition.
        :type ctx: GrammarParser.ExitForceTransitionDefinitionContext
        """
        super().exitExitForceTransitionDefinition(ctx)
        event_id = None
        if ctx.chain_id():
            event_id = self.nodes[ctx.chain_id()]
            event_scope = "absolute" if event_id.is_absolute else "chain"
        elif ctx.from_id:
            event_id = ChainID([ctx.from_state.text, ctx.from_id.text])
            event_scope = "local"
        else:
            event_scope = None
        node = ForceTransitionDefinition(
            from_state=ctx.from_state.text,
            to_state=EXIT_STATE,
            event_id=event_id,
            condition_expr=self.nodes[ctx.cond_expression()]
            if ctx.cond_expression()
            else None,
            event_scope=event_scope,
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitNormalAllForceTransitionDefinition(
        self, ctx: GrammarParser.NormalAllForceTransitionDefinitionContext
    ) -> None:
        """
        Build a force transition definition that applies to all states.

        :param ctx: Parse context for the normal all-force transition definition.
        :type ctx: GrammarParser.NormalAllForceTransitionDefinitionContext
        """
        super().exitNormalAllForceTransitionDefinition(ctx)
        node = ForceTransitionDefinition(
            from_state=ALL,
            to_state=ctx.to_state.text,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()]
            if ctx.cond_expression()
            else None,
            event_scope=(
                "absolute"
                if ctx.chain_id() and self.nodes[ctx.chain_id()].is_absolute
                else "chain"
                if ctx.chain_id()
                else None
            ),
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitExitAllForceTransitionDefinition(
        self, ctx: GrammarParser.ExitAllForceTransitionDefinitionContext
    ) -> None:
        """
        Build an all-state exit force transition definition.

        :param ctx: Parse context for the exit all-force transition definition.
        :type ctx: GrammarParser.ExitAllForceTransitionDefinitionContext
        """
        super().exitExitAllForceTransitionDefinition(ctx)
        node = ForceTransitionDefinition(
            from_state=ALL,
            to_state=EXIT_STATE,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()]
            if ctx.cond_expression()
            else None,
            event_scope=(
                "absolute"
                if ctx.chain_id() and self.nodes[ctx.chain_id()].is_absolute
                else "chain"
                if ctx.chain_id()
                else None
            ),
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitEvent_definition(self, ctx: GrammarParser.Event_definitionContext) -> None:
        """
        Build an event definition node.

        :param ctx: Parse context for the event definition.
        :type ctx: GrammarParser.Event_definitionContext
        """
        super().exitEvent_definition(ctx)
        node = EventDefinition(
            name=ctx.event_name.text,
            extra_name=_parse_string_literal(ctx.extra_name.text)
            if ctx.extra_name
            else None,
        )
        node._span = _ctx_span(ctx)
        self.nodes[ctx] = node

    def exitImport_mapping_statement(
        self, ctx: GrammarParser.Import_mapping_statementContext
    ) -> None:
        """
        Bind an import mapping statement to its specific node.

        :param ctx: Parse context for the import mapping statement.
        :type ctx: GrammarParser.Import_mapping_statementContext
        """
        super().exitImport_mapping_statement(ctx)
        if ctx.import_def_mapping():
            self.nodes[ctx] = self.nodes[ctx.import_def_mapping()]
        elif ctx.import_event_mapping():
            self.nodes[ctx] = self.nodes[ctx.import_event_mapping()]

    def exitImport_statement(self, ctx: GrammarParser.Import_statementContext) -> None:
        """
        Build an import statement node.

        :param ctx: Parse context for the import statement.
        :type ctx: GrammarParser.Import_statementContext
        """
        super().exitImport_statement(ctx)
        self.nodes[ctx] = ImportStatement(
            source_path=_parse_string_literal(ctx.import_path.text),
            alias=ctx.state_alias.text,
            extra_name=_parse_string_literal(ctx.extra_name.text)
            if ctx.extra_name
            else None,
            mappings=[
                self.nodes[item]
                for item in ctx.import_mapping_statement()
                if item in self.nodes
            ],
        )

    def exitImportDefExactSelector(
        self, ctx: GrammarParser.ImportDefExactSelectorContext
    ) -> None:
        """
        Build an exact variable selector for an import ``def`` mapping.

        :param ctx: Parse context for the exact selector.
        :type ctx: GrammarParser.ImportDefExactSelectorContext
        """
        super().exitImportDefExactSelector(ctx)
        self.nodes[ctx] = ImportDefExactSelector(name=ctx.selector_name.text)

    def exitImportDefSetSelector(
        self, ctx: GrammarParser.ImportDefSetSelectorContext
    ) -> None:
        """
        Build a set selector for an import ``def`` mapping.

        :param ctx: Parse context for the set selector.
        :type ctx: GrammarParser.ImportDefSetSelectorContext
        """
        super().exitImportDefSetSelector(ctx)
        self.nodes[ctx] = ImportDefSetSelector(
            names=[item.text for item in ctx.selector_items]
        )

    def exitImportDefPatternSelector(
        self, ctx: GrammarParser.ImportDefPatternSelectorContext
    ) -> None:
        """
        Build a wildcard pattern selector for an import ``def`` mapping.

        :param ctx: Parse context for the pattern selector.
        :type ctx: GrammarParser.ImportDefPatternSelectorContext
        """
        super().exitImportDefPatternSelector(ctx)
        self.nodes[ctx] = ImportDefPatternSelector(pattern=ctx.selector_pattern.text)

    def exitImportDefFallbackSelector(
        self, ctx: GrammarParser.ImportDefFallbackSelectorContext
    ) -> None:
        """
        Build a fallback selector for an import ``def`` mapping.

        :param ctx: Parse context for the fallback selector.
        :type ctx: GrammarParser.ImportDefFallbackSelectorContext
        """
        super().exitImportDefFallbackSelector(ctx)
        self.nodes[ctx] = ImportDefFallbackSelector()

    def exitImport_def_mapping(
        self, ctx: GrammarParser.Import_def_mappingContext
    ) -> None:
        """
        Build a variable mapping rule inside an import block.

        :param ctx: Parse context for the import ``def`` mapping.
        :type ctx: GrammarParser.Import_def_mappingContext
        """
        super().exitImport_def_mapping(ctx)
        self.nodes[ctx] = ImportDefMapping(
            selector=self.nodes[ctx.import_def_selector()],
            target_template=ImportDefTargetTemplate(
                template=ctx.import_def_target_template().target_text.text
            ),
        )

    def exitImport_event_mapping(
        self, ctx: GrammarParser.Import_event_mappingContext
    ) -> None:
        """
        Build an event mapping rule inside an import block.

        :param ctx: Parse context for the import event mapping.
        :type ctx: GrammarParser.Import_event_mappingContext
        """
        super().exitImport_event_mapping(ctx)
        self.nodes[ctx] = ImportEventMapping(
            source_event=self.nodes[ctx.source_event],
            target_event=self.nodes[ctx.target_event],
            extra_name=_parse_string_literal(ctx.extra_name.text)
            if ctx.extra_name
            else None,
        )
