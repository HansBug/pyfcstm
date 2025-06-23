# Generated from ./pyfcstm/dsl/grammar/Grammar.g4 by ANTLR 4.9.3
from antlr4 import *

if __name__ is not None and "." in __name__:
    from .GrammarParser import GrammarParser
else:
    from GrammarParser import GrammarParser


# This class defines a complete listener for a parse tree produced by GrammarParser.
class GrammarListener(ParseTreeListener):
    # Enter a parse tree produced by GrammarParser#condition.
    def enterCondition(self, ctx: GrammarParser.ConditionContext):
        pass

    # Exit a parse tree produced by GrammarParser#condition.
    def exitCondition(self, ctx: GrammarParser.ConditionContext):
        pass

    # Enter a parse tree produced by GrammarParser#state_machine_dsl.
    def enterState_machine_dsl(self, ctx: GrammarParser.State_machine_dslContext):
        pass

    # Exit a parse tree produced by GrammarParser#state_machine_dsl.
    def exitState_machine_dsl(self, ctx: GrammarParser.State_machine_dslContext):
        pass

    # Enter a parse tree produced by GrammarParser#def_assignment.
    def enterDef_assignment(self, ctx: GrammarParser.Def_assignmentContext):
        pass

    # Exit a parse tree produced by GrammarParser#def_assignment.
    def exitDef_assignment(self, ctx: GrammarParser.Def_assignmentContext):
        pass

    # Enter a parse tree produced by GrammarParser#leafStateDefinition.
    def enterLeafStateDefinition(self, ctx: GrammarParser.LeafStateDefinitionContext):
        pass

    # Exit a parse tree produced by GrammarParser#leafStateDefinition.
    def exitLeafStateDefinition(self, ctx: GrammarParser.LeafStateDefinitionContext):
        pass

    # Enter a parse tree produced by GrammarParser#compositeStateDefinition.
    def enterCompositeStateDefinition(
        self, ctx: GrammarParser.CompositeStateDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#compositeStateDefinition.
    def exitCompositeStateDefinition(
        self, ctx: GrammarParser.CompositeStateDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#entryTransitionDefinition.
    def enterEntryTransitionDefinition(
        self, ctx: GrammarParser.EntryTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#entryTransitionDefinition.
    def exitEntryTransitionDefinition(
        self, ctx: GrammarParser.EntryTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#normalTransitionDefinition.
    def enterNormalTransitionDefinition(
        self, ctx: GrammarParser.NormalTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#normalTransitionDefinition.
    def exitNormalTransitionDefinition(
        self, ctx: GrammarParser.NormalTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#exitTransitionDefinition.
    def enterExitTransitionDefinition(
        self, ctx: GrammarParser.ExitTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#exitTransitionDefinition.
    def exitExitTransitionDefinition(
        self, ctx: GrammarParser.ExitTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#normalForceTransitionDefinition.
    def enterNormalForceTransitionDefinition(
        self, ctx: GrammarParser.NormalForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#normalForceTransitionDefinition.
    def exitNormalForceTransitionDefinition(
        self, ctx: GrammarParser.NormalForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#exitForceTransitionDefinition.
    def enterExitForceTransitionDefinition(
        self, ctx: GrammarParser.ExitForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#exitForceTransitionDefinition.
    def exitExitForceTransitionDefinition(
        self, ctx: GrammarParser.ExitForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#normalAllForceTransitionDefinition.
    def enterNormalAllForceTransitionDefinition(
        self, ctx: GrammarParser.NormalAllForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#normalAllForceTransitionDefinition.
    def exitNormalAllForceTransitionDefinition(
        self, ctx: GrammarParser.NormalAllForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#exitAllForceTransitionDefinition.
    def enterExitAllForceTransitionDefinition(
        self, ctx: GrammarParser.ExitAllForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#exitAllForceTransitionDefinition.
    def exitExitAllForceTransitionDefinition(
        self, ctx: GrammarParser.ExitAllForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#enterOperations.
    def enterEnterOperations(self, ctx: GrammarParser.EnterOperationsContext):
        pass

    # Exit a parse tree produced by GrammarParser#enterOperations.
    def exitEnterOperations(self, ctx: GrammarParser.EnterOperationsContext):
        pass

    # Enter a parse tree produced by GrammarParser#enterAbstractFunc.
    def enterEnterAbstractFunc(self, ctx: GrammarParser.EnterAbstractFuncContext):
        pass

    # Exit a parse tree produced by GrammarParser#enterAbstractFunc.
    def exitEnterAbstractFunc(self, ctx: GrammarParser.EnterAbstractFuncContext):
        pass

    # Enter a parse tree produced by GrammarParser#exitOperations.
    def enterExitOperations(self, ctx: GrammarParser.ExitOperationsContext):
        pass

    # Exit a parse tree produced by GrammarParser#exitOperations.
    def exitExitOperations(self, ctx: GrammarParser.ExitOperationsContext):
        pass

    # Enter a parse tree produced by GrammarParser#exitAbstractFunc.
    def enterExitAbstractFunc(self, ctx: GrammarParser.ExitAbstractFuncContext):
        pass

    # Exit a parse tree produced by GrammarParser#exitAbstractFunc.
    def exitExitAbstractFunc(self, ctx: GrammarParser.ExitAbstractFuncContext):
        pass

    # Enter a parse tree produced by GrammarParser#duringOperations.
    def enterDuringOperations(self, ctx: GrammarParser.DuringOperationsContext):
        pass

    # Exit a parse tree produced by GrammarParser#duringOperations.
    def exitDuringOperations(self, ctx: GrammarParser.DuringOperationsContext):
        pass

    # Enter a parse tree produced by GrammarParser#duringAbstractFunc.
    def enterDuringAbstractFunc(self, ctx: GrammarParser.DuringAbstractFuncContext):
        pass

    # Exit a parse tree produced by GrammarParser#duringAbstractFunc.
    def exitDuringAbstractFunc(self, ctx: GrammarParser.DuringAbstractFuncContext):
        pass

    # Enter a parse tree produced by GrammarParser#duringAspectOperations.
    def enterDuringAspectOperations(
        self, ctx: GrammarParser.DuringAspectOperationsContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#duringAspectOperations.
    def exitDuringAspectOperations(
        self, ctx: GrammarParser.DuringAspectOperationsContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#duringAspectAbstractFunc.
    def enterDuringAspectAbstractFunc(
        self, ctx: GrammarParser.DuringAspectAbstractFuncContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#duringAspectAbstractFunc.
    def exitDuringAspectAbstractFunc(
        self, ctx: GrammarParser.DuringAspectAbstractFuncContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#operation_assignment.
    def enterOperation_assignment(self, ctx: GrammarParser.Operation_assignmentContext):
        pass

    # Exit a parse tree produced by GrammarParser#operation_assignment.
    def exitOperation_assignment(self, ctx: GrammarParser.Operation_assignmentContext):
        pass

    # Enter a parse tree produced by GrammarParser#operational_statement.
    def enterOperational_statement(
        self, ctx: GrammarParser.Operational_statementContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#operational_statement.
    def exitOperational_statement(
        self, ctx: GrammarParser.Operational_statementContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#state_inner_statement.
    def enterState_inner_statement(
        self, ctx: GrammarParser.State_inner_statementContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#state_inner_statement.
    def exitState_inner_statement(
        self, ctx: GrammarParser.State_inner_statementContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#operation_program.
    def enterOperation_program(self, ctx: GrammarParser.Operation_programContext):
        pass

    # Exit a parse tree produced by GrammarParser#operation_program.
    def exitOperation_program(self, ctx: GrammarParser.Operation_programContext):
        pass

    # Enter a parse tree produced by GrammarParser#preamble_program.
    def enterPreamble_program(self, ctx: GrammarParser.Preamble_programContext):
        pass

    # Exit a parse tree produced by GrammarParser#preamble_program.
    def exitPreamble_program(self, ctx: GrammarParser.Preamble_programContext):
        pass

    # Enter a parse tree produced by GrammarParser#preamble_statement.
    def enterPreamble_statement(self, ctx: GrammarParser.Preamble_statementContext):
        pass

    # Exit a parse tree produced by GrammarParser#preamble_statement.
    def exitPreamble_statement(self, ctx: GrammarParser.Preamble_statementContext):
        pass

    # Enter a parse tree produced by GrammarParser#initial_assignment.
    def enterInitial_assignment(self, ctx: GrammarParser.Initial_assignmentContext):
        pass

    # Exit a parse tree produced by GrammarParser#initial_assignment.
    def exitInitial_assignment(self, ctx: GrammarParser.Initial_assignmentContext):
        pass

    # Enter a parse tree produced by GrammarParser#constant_definition.
    def enterConstant_definition(self, ctx: GrammarParser.Constant_definitionContext):
        pass

    # Exit a parse tree produced by GrammarParser#constant_definition.
    def exitConstant_definition(self, ctx: GrammarParser.Constant_definitionContext):
        pass

    # Enter a parse tree produced by GrammarParser#operational_assignment.
    def enterOperational_assignment(
        self, ctx: GrammarParser.Operational_assignmentContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#operational_assignment.
    def exitOperational_assignment(
        self, ctx: GrammarParser.Operational_assignmentContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#generic_expression.
    def enterGeneric_expression(self, ctx: GrammarParser.Generic_expressionContext):
        pass

    # Exit a parse tree produced by GrammarParser#generic_expression.
    def exitGeneric_expression(self, ctx: GrammarParser.Generic_expressionContext):
        pass

    # Enter a parse tree produced by GrammarParser#funcExprInit.
    def enterFuncExprInit(self, ctx: GrammarParser.FuncExprInitContext):
        pass

    # Exit a parse tree produced by GrammarParser#funcExprInit.
    def exitFuncExprInit(self, ctx: GrammarParser.FuncExprInitContext):
        pass

    # Enter a parse tree produced by GrammarParser#unaryExprInit.
    def enterUnaryExprInit(self, ctx: GrammarParser.UnaryExprInitContext):
        pass

    # Exit a parse tree produced by GrammarParser#unaryExprInit.
    def exitUnaryExprInit(self, ctx: GrammarParser.UnaryExprInitContext):
        pass

    # Enter a parse tree produced by GrammarParser#binaryExprInit.
    def enterBinaryExprInit(self, ctx: GrammarParser.BinaryExprInitContext):
        pass

    # Exit a parse tree produced by GrammarParser#binaryExprInit.
    def exitBinaryExprInit(self, ctx: GrammarParser.BinaryExprInitContext):
        pass

    # Enter a parse tree produced by GrammarParser#literalExprInit.
    def enterLiteralExprInit(self, ctx: GrammarParser.LiteralExprInitContext):
        pass

    # Exit a parse tree produced by GrammarParser#literalExprInit.
    def exitLiteralExprInit(self, ctx: GrammarParser.LiteralExprInitContext):
        pass

    # Enter a parse tree produced by GrammarParser#mathConstExprInit.
    def enterMathConstExprInit(self, ctx: GrammarParser.MathConstExprInitContext):
        pass

    # Exit a parse tree produced by GrammarParser#mathConstExprInit.
    def exitMathConstExprInit(self, ctx: GrammarParser.MathConstExprInitContext):
        pass

    # Enter a parse tree produced by GrammarParser#parenExprInit.
    def enterParenExprInit(self, ctx: GrammarParser.ParenExprInitContext):
        pass

    # Exit a parse tree produced by GrammarParser#parenExprInit.
    def exitParenExprInit(self, ctx: GrammarParser.ParenExprInitContext):
        pass

    # Enter a parse tree produced by GrammarParser#unaryExprNum.
    def enterUnaryExprNum(self, ctx: GrammarParser.UnaryExprNumContext):
        pass

    # Exit a parse tree produced by GrammarParser#unaryExprNum.
    def exitUnaryExprNum(self, ctx: GrammarParser.UnaryExprNumContext):
        pass

    # Enter a parse tree produced by GrammarParser#funcExprNum.
    def enterFuncExprNum(self, ctx: GrammarParser.FuncExprNumContext):
        pass

    # Exit a parse tree produced by GrammarParser#funcExprNum.
    def exitFuncExprNum(self, ctx: GrammarParser.FuncExprNumContext):
        pass

    # Enter a parse tree produced by GrammarParser#conditionalCStyleExprNum.
    def enterConditionalCStyleExprNum(
        self, ctx: GrammarParser.ConditionalCStyleExprNumContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#conditionalCStyleExprNum.
    def exitConditionalCStyleExprNum(
        self, ctx: GrammarParser.ConditionalCStyleExprNumContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#binaryExprNum.
    def enterBinaryExprNum(self, ctx: GrammarParser.BinaryExprNumContext):
        pass

    # Exit a parse tree produced by GrammarParser#binaryExprNum.
    def exitBinaryExprNum(self, ctx: GrammarParser.BinaryExprNumContext):
        pass

    # Enter a parse tree produced by GrammarParser#literalExprNum.
    def enterLiteralExprNum(self, ctx: GrammarParser.LiteralExprNumContext):
        pass

    # Exit a parse tree produced by GrammarParser#literalExprNum.
    def exitLiteralExprNum(self, ctx: GrammarParser.LiteralExprNumContext):
        pass

    # Enter a parse tree produced by GrammarParser#mathConstExprNum.
    def enterMathConstExprNum(self, ctx: GrammarParser.MathConstExprNumContext):
        pass

    # Exit a parse tree produced by GrammarParser#mathConstExprNum.
    def exitMathConstExprNum(self, ctx: GrammarParser.MathConstExprNumContext):
        pass

    # Enter a parse tree produced by GrammarParser#parenExprNum.
    def enterParenExprNum(self, ctx: GrammarParser.ParenExprNumContext):
        pass

    # Exit a parse tree produced by GrammarParser#parenExprNum.
    def exitParenExprNum(self, ctx: GrammarParser.ParenExprNumContext):
        pass

    # Enter a parse tree produced by GrammarParser#idExprNum.
    def enterIdExprNum(self, ctx: GrammarParser.IdExprNumContext):
        pass

    # Exit a parse tree produced by GrammarParser#idExprNum.
    def exitIdExprNum(self, ctx: GrammarParser.IdExprNumContext):
        pass

    # Enter a parse tree produced by GrammarParser#binaryExprFromCondCond.
    def enterBinaryExprFromCondCond(
        self, ctx: GrammarParser.BinaryExprFromCondCondContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#binaryExprFromCondCond.
    def exitBinaryExprFromCondCond(
        self, ctx: GrammarParser.BinaryExprFromCondCondContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#binaryExprCond.
    def enterBinaryExprCond(self, ctx: GrammarParser.BinaryExprCondContext):
        pass

    # Exit a parse tree produced by GrammarParser#binaryExprCond.
    def exitBinaryExprCond(self, ctx: GrammarParser.BinaryExprCondContext):
        pass

    # Enter a parse tree produced by GrammarParser#binaryExprFromNumCond.
    def enterBinaryExprFromNumCond(
        self, ctx: GrammarParser.BinaryExprFromNumCondContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#binaryExprFromNumCond.
    def exitBinaryExprFromNumCond(
        self, ctx: GrammarParser.BinaryExprFromNumCondContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#unaryExprCond.
    def enterUnaryExprCond(self, ctx: GrammarParser.UnaryExprCondContext):
        pass

    # Exit a parse tree produced by GrammarParser#unaryExprCond.
    def exitUnaryExprCond(self, ctx: GrammarParser.UnaryExprCondContext):
        pass

    # Enter a parse tree produced by GrammarParser#parenExprCond.
    def enterParenExprCond(self, ctx: GrammarParser.ParenExprCondContext):
        pass

    # Exit a parse tree produced by GrammarParser#parenExprCond.
    def exitParenExprCond(self, ctx: GrammarParser.ParenExprCondContext):
        pass

    # Enter a parse tree produced by GrammarParser#literalExprCond.
    def enterLiteralExprCond(self, ctx: GrammarParser.LiteralExprCondContext):
        pass

    # Exit a parse tree produced by GrammarParser#literalExprCond.
    def exitLiteralExprCond(self, ctx: GrammarParser.LiteralExprCondContext):
        pass

    # Enter a parse tree produced by GrammarParser#conditionalCStyleCondNum.
    def enterConditionalCStyleCondNum(
        self, ctx: GrammarParser.ConditionalCStyleCondNumContext
    ):
        pass

    # Exit a parse tree produced by GrammarParser#conditionalCStyleCondNum.
    def exitConditionalCStyleCondNum(
        self, ctx: GrammarParser.ConditionalCStyleCondNumContext
    ):
        pass

    # Enter a parse tree produced by GrammarParser#num_literal.
    def enterNum_literal(self, ctx: GrammarParser.Num_literalContext):
        pass

    # Exit a parse tree produced by GrammarParser#num_literal.
    def exitNum_literal(self, ctx: GrammarParser.Num_literalContext):
        pass

    # Enter a parse tree produced by GrammarParser#bool_literal.
    def enterBool_literal(self, ctx: GrammarParser.Bool_literalContext):
        pass

    # Exit a parse tree produced by GrammarParser#bool_literal.
    def exitBool_literal(self, ctx: GrammarParser.Bool_literalContext):
        pass

    # Enter a parse tree produced by GrammarParser#math_const.
    def enterMath_const(self, ctx: GrammarParser.Math_constContext):
        pass

    # Exit a parse tree produced by GrammarParser#math_const.
    def exitMath_const(self, ctx: GrammarParser.Math_constContext):
        pass

    # Enter a parse tree produced by GrammarParser#chain_id.
    def enterChain_id(self, ctx: GrammarParser.Chain_idContext):
        pass

    # Exit a parse tree produced by GrammarParser#chain_id.
    def exitChain_id(self, ctx: GrammarParser.Chain_idContext):
        pass


del GrammarParser
