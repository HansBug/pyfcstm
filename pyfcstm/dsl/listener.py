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

from typing import Any, Dict, Optional

from .grammar import GrammarListener, GrammarParser
from .node import *
from ..utils import format_multiline_comment


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
            func=ctx.function.text,
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

    def exitBinaryExprFromCondCond(
        self, ctx: GrammarParser.BinaryExprFromCondCondContext
    ) -> None:
        """
        Build a binary conditional expression node.

        :param ctx: Parse context for the binary condition-to-condition expression.
        :type ctx: GrammarParser.BinaryExprFromCondCondContext
        """
        super().exitBinaryExprFromNumCond(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.cond_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.cond_expression(1)],
        )
        self.nodes[ctx] = node

    def exitBinaryExprCond(self, ctx: GrammarParser.BinaryExprCondContext) -> None:
        """
        Build a binary conditional expression node.

        :param ctx: Parse context for the binary conditional expression.
        :type ctx: GrammarParser.BinaryExprCondContext
        """
        super().exitBinaryExprCond(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.cond_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.cond_expression(1)],
        )
        self.nodes[ctx] = node

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
            assert False, f'Should not reach this line - {ctx!r}.'  # pragma: no cover
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
        self.nodes[ctx] = Operation([self.nodes[stat] for stat in ctx.operational_assignment()])

    def exitPreamble_program(
        self, ctx: GrammarParser.Preamble_programContext
    ) -> None:
        """
        Build a preamble program node from preamble statements.

        :param ctx: Parse context for the preamble program.
        :type ctx: GrammarParser.Preamble_programContext
        """
        super().exitPreamble_program(ctx)
        self.nodes[ctx] = Preamble([self.nodes[stat] for stat in ctx.preamble_statement()])

    def exitPreamble_statement(
        self, ctx: GrammarParser.Preamble_statementContext
    ) -> None:
        """
        Bind a preamble statement to its specific node.

        :param ctx: Parse context for the preamble statement.
        :type ctx: GrammarParser.Preamble_statementContext
        """
        super().exitPreamble_statement(ctx)
        self.nodes[ctx] = self.nodes[ctx.initial_assignment() or ctx.constant_definition()]

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
            func=ctx.function.text,
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
        self.nodes[ctx] = DefAssignment(
            name=str(ctx.ID()),
            type=ctx.deftype.text,
            expr=self.nodes[ctx.init_expression()],
        )

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
        self.nodes[ctx] = StateDefinition(
            name=str(ctx.ID()),
            extra_name=eval(ctx.extra_name.text) if ctx.extra_name else None,
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            is_pseudo=bool(ctx.pseudo),
        )

    def exitCompositeStateDefinition(
        self, ctx: GrammarParser.CompositeStateDefinitionContext
    ) -> None:
        """
        Build a composite :class:`StateDefinition` node.

        :param ctx: Parse context for the composite state definition.
        :type ctx: GrammarParser.CompositeStateDefinitionContext
        """
        super().exitCompositeStateDefinition(ctx)
        self.nodes[ctx] = StateDefinition(
            name=str(ctx.ID()),
            extra_name=eval(ctx.extra_name.text) if ctx.extra_name else None,
            events=[self.nodes[item] for item in ctx.state_inner_statement()
                    if item in self.nodes and isinstance(self.nodes[item], EventDefinition)],
            substates=[self.nodes[item] for item in ctx.state_inner_statement()
                       if item in self.nodes and isinstance(self.nodes[item], StateDefinition)],
            transitions=[self.nodes[item] for item in ctx.state_inner_statement()
                         if item in self.nodes and isinstance(self.nodes[item], TransitionDefinition)],
            enters=[self.nodes[item] for item in ctx.state_inner_statement()
                    if item in self.nodes and isinstance(self.nodes[item], EnterStatement)],
            durings=[self.nodes[item] for item in ctx.state_inner_statement()
                     if item in self.nodes and isinstance(self.nodes[item], DuringStatement)],
            exits=[self.nodes[item] for item in ctx.state_inner_statement()
                   if item in self.nodes and isinstance(self.nodes[item], ExitStatement)],
            during_aspects=[self.nodes[item] for item in ctx.state_inner_statement()
                            if item in self.nodes and isinstance(self.nodes[item], DuringAspectStatement)],
            force_transitions=[self.nodes[item] for item in ctx.state_inner_statement()
                               if item in self.nodes and isinstance(self.nodes[item], ForceTransitionDefinition)],
            is_pseudo=bool(ctx.pseudo),
        )

    def exitEntryTransitionDefinition(
        self, ctx: GrammarParser.EntryTransitionDefinitionContext
    ) -> None:
        """
        Build an entry transition definition node.

        :param ctx: Parse context for the entry transition definition.
        :type ctx: GrammarParser.EntryTransitionDefinitionContext
        """
        super().exitEntryTransitionDefinition(ctx)
        self.nodes[ctx] = TransitionDefinition(
            from_state=INIT_STATE,
            to_state=ctx.to_state.text,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
            post_operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitNormalTransitionDefinition(
        self, ctx: GrammarParser.NormalTransitionDefinitionContext
    ) -> None:
        """
        Build a normal transition definition node.

        :param ctx: Parse context for the normal transition definition.
        :type ctx: GrammarParser.NormalTransitionDefinitionContext
        """
        super().exitNormalTransitionDefinition(ctx)
        event_id = None
        if ctx.chain_id():
            event_id = self.nodes[ctx.chain_id()]
        elif ctx.from_id:
            event_id = ChainID([ctx.from_state.text, ctx.from_id.text])
        self.nodes[ctx] = TransitionDefinition(
            from_state=ctx.from_state.text,
            to_state=ctx.to_state.text,
            event_id=event_id,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
            post_operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitExitTransitionDefinition(
        self, ctx: GrammarParser.ExitTransitionDefinitionContext
    ) -> None:
        """
        Build an exit transition definition node.

        :param ctx: Parse context for the exit transition definition.
        :type ctx: GrammarParser.ExitTransitionDefinitionContext
        """
        super().exitExitTransitionDefinition(ctx)
        event_id = None
        if ctx.chain_id():
            event_id = self.nodes[ctx.chain_id()]
        elif ctx.from_id:
            event_id = ChainID([ctx.from_state.text, ctx.from_id.text])
        self.nodes[ctx] = TransitionDefinition(
            from_state=ctx.from_state.text,
            to_state=EXIT_STATE,
            event_id=event_id,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
            post_operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

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
        Bind an operational statement to its assignment node.

        :param ctx: Parse context for the operational statement.
        :type ctx: GrammarParser.Operational_statementContext
        """
        super().exitOperational_statement(ctx)
        if ctx.operation_assignment():
            self.nodes[ctx] = self.nodes[ctx.operation_assignment()]

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

    def exitOperation_assignment(
        self, ctx: GrammarParser.Operation_assignmentContext
    ) -> None:
        """
        Build an operation assignment node.

        :param ctx: Parse context for the operation assignment.
        :type ctx: GrammarParser.Operation_assignmentContext
        """
        super().exitOperation_assignment(ctx)
        self.nodes[ctx] = OperationAssignment(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.num_expression()],
        )

    def exitEnterOperations(
        self, ctx: GrammarParser.EnterOperationsContext
    ) -> None:
        """
        Build an enter-operations node.

        :param ctx: Parse context for the enter operations.
        :type ctx: GrammarParser.EnterOperationsContext
        """
        super().exitEnterOperations(ctx)
        self.nodes[ctx] = EnterOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes],
        )

    def exitEnterAbstractFunc(
        self, ctx: GrammarParser.EnterAbstractFuncContext
    ) -> None:
        """
        Build an enter abstract function node.

        :param ctx: Parse context for the enter abstract function.
        :type ctx: GrammarParser.EnterAbstractFuncContext
        """
        super().exitEnterAbstractFunc(ctx)
        self.nodes[ctx] = EnterAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitEnterRefFunc(self, ctx: GrammarParser.EnterRefFuncContext) -> None:
        """
        Build an enter reference function node.

        :param ctx: Parse context for the enter reference function.
        :type ctx: GrammarParser.EnterRefFuncContext
        """
        super().exitEnterRefFunc(ctx)
        self.nodes[ctx] = EnterRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            ref=self.nodes[ctx.chain_id()],
        )

    def exitExitOperations(self, ctx: GrammarParser.ExitOperationsContext) -> None:
        """
        Build an exit-operations node.

        :param ctx: Parse context for the exit operations.
        :type ctx: GrammarParser.ExitOperationsContext
        """
        super().exitExitOperations(ctx)
        self.nodes[ctx] = ExitOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitExitAbstractFunc(
        self, ctx: GrammarParser.ExitAbstractFuncContext
    ) -> None:
        """
        Build an exit abstract function node.

        :param ctx: Parse context for the exit abstract function.
        :type ctx: GrammarParser.ExitAbstractFuncContext
        """
        super().exitExitAbstractFunc(ctx)
        self.nodes[ctx] = ExitAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitExitRefFunc(self, ctx: GrammarParser.ExitRefFuncContext) -> None:
        """
        Build an exit reference function node.

        :param ctx: Parse context for the exit reference function.
        :type ctx: GrammarParser.ExitRefFuncContext
        """
        super().exitExitRefFunc(ctx)
        self.nodes[ctx] = ExitRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            ref=self.nodes[ctx.chain_id()],
        )

    def exitDuringOperations(
        self, ctx: GrammarParser.DuringOperationsContext
    ) -> None:
        """
        Build a during-operations node.

        :param ctx: Parse context for the during operations.
        :type ctx: GrammarParser.DuringOperationsContext
        """
        super().exitDuringOperations(ctx)
        self.nodes[ctx] = DuringOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitDuringAbstractFunc(
        self, ctx: GrammarParser.DuringAbstractFuncContext
    ) -> None:
        """
        Build a during abstract function node.

        :param ctx: Parse context for the during abstract function.
        :type ctx: GrammarParser.DuringAbstractFuncContext
        """
        super().exitDuringAbstractFunc(ctx)
        self.nodes[ctx] = DuringAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitDuringRefFunc(self, ctx: GrammarParser.DuringRefFuncContext) -> None:
        """
        Build a during reference function node.

        :param ctx: Parse context for the during reference function.
        :type ctx: GrammarParser.DuringRefFuncContext
        """
        super().exitDuringRefFunc(ctx)
        self.nodes[ctx] = DuringRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            ref=self.nodes[ctx.chain_id()],
        )

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
        self.nodes[ctx] = DuringAspectOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitDuringAspectAbstractFunc(
        self, ctx: GrammarParser.DuringAspectAbstractFuncContext
    ) -> None:
        """
        Build a during-aspect abstract function node.

        :param ctx: Parse context for the during aspect abstract function.
        :type ctx: GrammarParser.DuringAspectAbstractFuncContext
        """
        super().exitDuringAspectAbstractFunc(ctx)
        self.nodes[ctx] = DuringAspectAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitDuringAspectRefFunc(
        self, ctx: GrammarParser.DuringAspectRefFuncContext
    ) -> None:
        """
        Build a during-aspect reference function node.

        :param ctx: Parse context for the during aspect reference function.
        :type ctx: GrammarParser.DuringAspectRefFuncContext
        """
        super().exitDuringAspectRefFunc(ctx)
        self.nodes[ctx] = DuringAspectRefFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            ref=self.nodes[ctx.chain_id()],
        )

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
        elif ctx.from_id:
            event_id = ChainID([ctx.from_state.text, ctx.from_id.text])
        self.nodes[ctx] = ForceTransitionDefinition(
            from_state=ctx.from_state.text,
            to_state=ctx.to_state.text,
            event_id=event_id,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
        )

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
        elif ctx.from_id:
            event_id = ChainID([ctx.from_state.text, ctx.from_id.text])
        self.nodes[ctx] = ForceTransitionDefinition(
            from_state=ctx.from_state.text,
            to_state=EXIT_STATE,
            event_id=event_id,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
        )

    def exitNormalAllForceTransitionDefinition(
        self, ctx: GrammarParser.NormalAllForceTransitionDefinitionContext
    ) -> None:
        """
        Build a force transition definition that applies to all states.

        :param ctx: Parse context for the normal all-force transition definition.
        :type ctx: GrammarParser.NormalAllForceTransitionDefinitionContext
        """
        super().exitNormalAllForceTransitionDefinition(ctx)
        self.nodes[ctx] = ForceTransitionDefinition(
            from_state=ALL,
            to_state=ctx.to_state.text,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
        )

    def exitExitAllForceTransitionDefinition(
        self, ctx: GrammarParser.ExitAllForceTransitionDefinitionContext
    ) -> None:
        """
        Build an all-state exit force transition definition.

        :param ctx: Parse context for the exit all-force transition definition.
        :type ctx: GrammarParser.ExitAllForceTransitionDefinitionContext
        """
        super().exitExitAllForceTransitionDefinition(ctx)
        # print(self.nodes[ctx.chain_id()] if ctx.chain_id() else None)
        self.nodes[ctx] = ForceTransitionDefinition(
            from_state=ALL,
            to_state=EXIT_STATE,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
        )

    def exitEvent_definition(self, ctx: GrammarParser.Event_definitionContext) -> None:
        """
        Build an event definition node.

        :param ctx: Parse context for the event definition.
        :type ctx: GrammarParser.Event_definitionContext
        """
        super().exitEvent_definition(ctx)
        self.nodes[ctx] = EventDefinition(
            name=ctx.event_name.text,
            extra_name=eval(ctx.extra_name.text) if ctx.extra_name else None,
        )
