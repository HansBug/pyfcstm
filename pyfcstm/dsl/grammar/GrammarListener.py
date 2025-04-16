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


del GrammarParser
