from .grammar import GrammarListener, GrammarParser
from .node import *
from ..utils import format_multiline_comment


class GrammarParseListener(GrammarListener):
    def __init__(self):
        super().__init__()
        self.nodes = {}

    def exitCondition(self, ctx: GrammarParser.ConditionContext):
        super().exitCondition(ctx)
        self.nodes[ctx] = Condition(self.nodes[ctx.cond_expression()])

    def exitUnaryExprNum(self, ctx: GrammarParser.UnaryExprNumContext):
        super().exitUnaryExprNum(ctx)
        node = UnaryOp(
            op=ctx.op.text,
            expr=self.nodes[ctx.num_expression()],
        )
        self.nodes[ctx] = node

    def exitFuncExprNum(self, ctx: GrammarParser.FuncExprNumContext):
        super().exitFuncExprNum(ctx)
        node = UFunc(
            func=ctx.function.text,
            expr=self.nodes[ctx.num_expression()],
        )
        self.nodes[ctx] = node

    def exitBinaryExprNum(self, ctx: GrammarParser.BinaryExprNumContext):
        super().exitBinaryExprNum(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.num_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.num_expression(1)],
        )
        self.nodes[ctx] = node

    def exitLiteralExprNum(self, ctx: GrammarParser.LiteralExprNumContext):
        super().exitLiteralExprNum(ctx)
        self.nodes[ctx] = self.nodes[ctx.num_literal()]

    def exitMathConstExprNum(self, ctx: GrammarParser.MathConstExprNumContext):
        super().exitMathConstExprNum(ctx)
        self.nodes[ctx] = self.nodes[ctx.math_const()]

    def exitParenExprNum(self, ctx: GrammarParser.ParenExprNumContext):
        super().exitParenExprNum(ctx)
        node = Paren(self.nodes[ctx.num_expression()])
        self.nodes[ctx] = node

    def exitIdExprNum(self, ctx: GrammarParser.IdExprNumContext):
        super().exitIdExprNum(ctx)
        node = Name(ctx.getText())
        self.nodes[ctx] = node

    def exitBinaryExprFromNumCond(self, ctx: GrammarParser.BinaryExprFromNumCondContext):
        super().exitBinaryExprFromNumCond(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.num_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.num_expression(1)],
        )
        self.nodes[ctx] = node

    def exitBinaryExprFromCondCond(self, ctx: GrammarParser.BinaryExprFromCondCondContext):
        super().exitBinaryExprFromNumCond(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.cond_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.cond_expression(1)],
        )
        self.nodes[ctx] = node

    def exitBinaryExprCond(self, ctx: GrammarParser.BinaryExprCondContext):
        super().exitBinaryExprCond(ctx)
        node = BinaryOp(
            expr1=self.nodes[ctx.cond_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.cond_expression(1)],
        )
        self.nodes[ctx] = node

    def exitUnaryExprCond(self, ctx: GrammarParser.UnaryExprCondContext):
        super().exitUnaryExprCond(ctx)
        node = UnaryOp(
            op=ctx.op.text,
            expr=self.nodes[ctx.cond_expression()],
        )
        self.nodes[ctx] = node

    def exitParenExprCond(self, ctx: GrammarParser.ParenExprCondContext):
        super().exitParenExprCond(ctx)
        node = Paren(self.nodes[ctx.cond_expression()])
        self.nodes[ctx] = node

    def exitLiteralExprCond(self, ctx: GrammarParser.LiteralExprCondContext):
        super().exitLiteralExprCond(ctx)
        self.nodes[ctx] = self.nodes[ctx.bool_literal()]

    def exitNum_literal(self, ctx: GrammarParser.Num_literalContext):
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

    def exitBool_literal(self, ctx: GrammarParser.Bool_literalContext):
        super().exitBool_literal(ctx)
        node = Boolean(ctx.getText().lower())
        self.nodes[ctx] = node

    def exitMath_const(self, ctx: GrammarParser.Math_constContext):
        super().exitMath_const(ctx)
        node = Constant(ctx.getText())
        self.nodes[ctx] = node

    def exitOperation_program(self, ctx: GrammarParser.Operation_programContext):
        super().exitOperation_program(ctx)
        self.nodes[ctx] = Operation([self.nodes[stat] for stat in ctx.operational_assignment()])

    def exitPreamble_program(self, ctx: GrammarParser.Preamble_programContext):
        super().exitPreamble_program(ctx)
        self.nodes[ctx] = Preamble([self.nodes[stat] for stat in ctx.preamble_statement()])

    def exitPreamble_statement(self, ctx: GrammarParser.Preamble_statementContext):
        super().exitPreamble_statement(ctx)
        self.nodes[ctx] = self.nodes[ctx.initial_assignment() or ctx.constant_definition()]

    def exitInitial_assignment(self, ctx: GrammarParser.Initial_assignmentContext):
        super().exitInitial_assignment(ctx)
        self.nodes[ctx] = InitialAssignment(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.init_expression()],
        )

    def exitConstant_definition(self, ctx: GrammarParser.Constant_definitionContext):
        super().exitConstant_definition(ctx)
        self.nodes[ctx] = ConstantDefinition(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.init_expression()],
        )

    def exitOperational_assignment(self, ctx: GrammarParser.Operational_assignmentContext):
        super().exitOperational_assignment(ctx)
        self.nodes[ctx] = OperationalDeprecatedAssignment(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.num_expression()],
        )

    def exitFuncExprInit(self, ctx: GrammarParser.FuncExprInitContext):
        super().exitFuncExprInit(ctx)
        self.nodes[ctx] = UFunc(
            func=ctx.function.text,
            expr=self.nodes[ctx.init_expression()],
        )

    def exitUnaryExprInit(self, ctx: GrammarParser.UnaryExprInitContext):
        super().exitUnaryExprInit(ctx)
        self.nodes[ctx] = UnaryOp(
            op=ctx.op.text,
            expr=self.nodes[ctx.init_expression()],
        )

    def exitBinaryExprInit(self, ctx: GrammarParser.BinaryExprInitContext):
        super().exitBinaryExprInit(ctx)
        self.nodes[ctx] = BinaryOp(
            expr1=self.nodes[ctx.init_expression(0)],
            op=ctx.op.text,
            expr2=self.nodes[ctx.init_expression(1)],
        )

    def exitLiteralExprInit(self, ctx: GrammarParser.LiteralExprInitContext):
        super().exitLiteralExprInit(ctx)
        self.nodes[ctx] = self.nodes[ctx.num_literal()]

    def exitMathConstExprInit(self, ctx: GrammarParser.MathConstExprInitContext):
        super().exitMathConstExprInit(ctx)
        self.nodes[ctx] = self.nodes[ctx.math_const()]

    def exitParenExprInit(self, ctx: GrammarParser.ParenExprInitContext):
        super().exitParenExprInit(ctx)
        self.nodes[ctx] = Paren(self.nodes[ctx.init_expression()])

    def exitConditionalCStyleExprNum(self, ctx: GrammarParser.ConditionalCStyleExprNumContext):
        super().exitConditionalCStyleExprNum(ctx)
        self.nodes[ctx] = ConditionalOp(
            cond=self.nodes[ctx.cond_expression()],
            value_true=self.nodes[ctx.num_expression(0)],
            value_false=self.nodes[ctx.num_expression(1)],
        )

    def exitConditionalCStyleCondNum(self, ctx: GrammarParser.ConditionalCStyleCondNumContext):
        super().exitConditionalCStyleCondNum(ctx)
        self.nodes[ctx] = ConditionalOp(
            cond=self.nodes[ctx.cond_expression(0)],
            value_true=self.nodes[ctx.cond_expression(1)],
            value_false=self.nodes[ctx.cond_expression(2)],
        )

    def exitDef_assignment(self, ctx: GrammarParser.Def_assignmentContext):
        super().exitDef_assignment(ctx)
        self.nodes[ctx] = DefAssignment(
            name=str(ctx.ID()),
            type=ctx.deftype.text,
            expr=self.nodes[ctx.init_expression()],
        )

    def exitState_machine_dsl(self, ctx: GrammarParser.State_machine_dslContext):
        super().exitState_machine_dsl(ctx)
        self.nodes[ctx] = StateMachineDSLProgram(
            definitions=[self.nodes[item] for item in ctx.def_assignment()],
            root_state=self.nodes[ctx.state_definition()],
        )

    def exitLeafStateDefinition(self, ctx: GrammarParser.LeafStateDefinitionContext):
        super().exitLeafStateDefinition(ctx)
        self.nodes[ctx] = StateDefinition(
            name=str(ctx.ID()),
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
        )

    def exitCompositeStateDefinition(self, ctx: GrammarParser.CompositeStateDefinitionContext):
        super().exitCompositeStateDefinition(ctx)
        self.nodes[ctx] = StateDefinition(
            name=str(ctx.ID()),
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
        )

    def exitEntryTransitionDefinition(self, ctx: GrammarParser.EntryTransitionDefinitionContext):
        super().exitEntryTransitionDefinition(ctx)
        self.nodes[ctx] = TransitionDefinition(
            from_state=INIT_STATE,
            to_state=ctx.to_state.text,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
            post_operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitNormalTransitionDefinition(self, ctx: GrammarParser.NormalTransitionDefinitionContext):
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

    def exitExitTransitionDefinition(self, ctx: GrammarParser.ExitTransitionDefinitionContext):
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

    def exitChain_id(self, ctx: GrammarParser.Chain_idContext):
        super().exitChain_id(ctx)
        self.nodes[ctx] = ChainID(
            path=list(map(str, ctx.ID())),
            is_absolute=bool(ctx.isabs),
        )

    def exitOperational_statement(self, ctx: GrammarParser.Operational_statementContext):
        super().exitOperational_statement(ctx)
        if ctx.operation_assignment():
            self.nodes[ctx] = self.nodes[ctx.operation_assignment()]

    def exitState_inner_statement(self, ctx: GrammarParser.State_inner_statementContext):
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

    def exitOperation_assignment(self, ctx: GrammarParser.Operation_assignmentContext):
        super().exitOperation_assignment(ctx)
        self.nodes[ctx] = OperationAssignment(
            name=str(ctx.ID()),
            expr=self.nodes[ctx.num_expression()],
        )

    def exitEnterOperations(self, ctx: GrammarParser.EnterOperationsContext):
        super().exitEnterOperations(ctx)
        self.nodes[ctx] = EnterOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes],
        )

    def exitEnterAbstractFunc(self, ctx: GrammarParser.EnterAbstractFuncContext):
        super().exitEnterAbstractFunc(ctx)
        self.nodes[ctx] = EnterAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitExitOperations(self, ctx: GrammarParser.ExitOperationsContext):
        super().exitExitOperations(ctx)
        self.nodes[ctx] = ExitOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitExitAbstractFunc(self, ctx: GrammarParser.ExitAbstractFuncContext):
        super().exitExitAbstractFunc(ctx)
        self.nodes[ctx] = ExitAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitDuringOperations(self, ctx: GrammarParser.DuringOperationsContext):
        super().exitDuringOperations(ctx)
        self.nodes[ctx] = DuringOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitDuringAbstractFunc(self, ctx: GrammarParser.DuringAbstractFuncContext):
        super().exitDuringAbstractFunc(ctx)
        self.nodes[ctx] = DuringAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitGeneric_expression(self, ctx: GrammarParser.Generic_expressionContext):
        if ctx.num_expression():
            self.nodes[ctx] = self.nodes[ctx.num_expression()]
        elif ctx.cond_expression():
            self.nodes[ctx] = self.nodes[ctx.cond_expression()]

    def exitDuringAspectOperations(self, ctx: GrammarParser.DuringAspectOperationsContext):
        super().exitDuringAspectOperations(ctx)
        self.nodes[ctx] = DuringAspectOperations(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            operations=[self.nodes[item] for item in ctx.operational_statement() if item in self.nodes]
        )

    def exitDuringAspectAbstractFunc(self, ctx: GrammarParser.DuringAspectAbstractFuncContext):
        super().exitDuringAspectAbstractFunc(ctx)
        self.nodes[ctx] = DuringAspectAbstractFunction(
            name=ctx.func_name.text if ctx.func_name else None,
            aspect=ctx.aspect.text if ctx.aspect else None,
            doc=format_multiline_comment(ctx.raw_doc.text) if ctx.raw_doc else None,
        )

    def exitNormalForceTransitionDefinition(self, ctx: GrammarParser.NormalForceTransitionDefinitionContext):
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

    def exitExitForceTransitionDefinition(self, ctx: GrammarParser.ExitForceTransitionDefinitionContext):
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

    def exitNormalAllForceTransitionDefinition(self, ctx: GrammarParser.NormalAllForceTransitionDefinitionContext):
        super().exitNormalAllForceTransitionDefinition(ctx)
        self.nodes[ctx] = ForceTransitionDefinition(
            from_state=ALL,
            to_state=ctx.to_state.text,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
        )

    def exitExitAllForceTransitionDefinition(self, ctx: GrammarParser.ExitAllForceTransitionDefinitionContext):
        super().exitExitAllForceTransitionDefinition(ctx)
        # print(self.nodes[ctx.chain_id()] if ctx.chain_id() else None)
        self.nodes[ctx] = ForceTransitionDefinition(
            from_state=ALL,
            to_state=EXIT_STATE,
            event_id=self.nodes[ctx.chain_id()] if ctx.chain_id() else None,
            condition_expr=self.nodes[ctx.cond_expression()] if ctx.cond_expression() else None,
        )
