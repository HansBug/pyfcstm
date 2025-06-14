from .grammar import GrammarListener, GrammarParser
from .node import Integer, Float, Constant, Boolean, Name, Paren, BinaryOp, UnaryOp, UFunc, ConstantDefinition, \
    OperationalAssignment, InitialAssignment, Condition, Operation, Preamble, ConditionalOp


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
        self.nodes[ctx] = OperationalAssignment(
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
