# Generated from ./pyfcstm/bmc/grammar/BmcQueryParser.g4 by ANTLR 4.9.3
from antlr4 import *

if __name__ is not None and "." in __name__:
    from .BmcQueryParser import BmcQueryParser
else:
    from BmcQueryParser import BmcQueryParser


# This class defines a complete listener for a parse tree produced by BmcQueryParser.
class BmcQueryParserListener(ParseTreeListener):
    # Enter a parse tree produced by BmcQueryParser#query.
    def enterQuery(self, ctx: BmcQueryParser.QueryContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#query.
    def exitQuery(self, ctx: BmcQueryParser.QueryContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#bmc_num_expression_entry.
    def enterBmc_num_expression_entry(
        self, ctx: BmcQueryParser.Bmc_num_expression_entryContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#bmc_num_expression_entry.
    def exitBmc_num_expression_entry(
        self, ctx: BmcQueryParser.Bmc_num_expression_entryContext
    ):
        pass

    # Enter a parse tree produced by BmcQueryParser#bmc_cond_expression_entry.
    def enterBmc_cond_expression_entry(
        self, ctx: BmcQueryParser.Bmc_cond_expression_entryContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#bmc_cond_expression_entry.
    def exitBmc_cond_expression_entry(
        self, ctx: BmcQueryParser.Bmc_cond_expression_entryContext
    ):
        pass

    # Enter a parse tree produced by BmcQueryParser#init_clause.
    def enterInit_clause(self, ctx: BmcQueryParser.Init_clauseContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#init_clause.
    def exitInit_clause(self, ctx: BmcQueryParser.Init_clauseContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#init_target.
    def enterInit_target(self, ctx: BmcQueryParser.Init_targetContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#init_target.
    def exitInit_target(self, ctx: BmcQueryParser.Init_targetContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#init_havoc_clause.
    def enterInit_havoc_clause(self, ctx: BmcQueryParser.Init_havoc_clauseContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#init_havoc_clause.
    def exitInit_havoc_clause(self, ctx: BmcQueryParser.Init_havoc_clauseContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#init_var_ref.
    def enterInit_var_ref(self, ctx: BmcQueryParser.Init_var_refContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#init_var_ref.
    def exitInit_var_ref(self, ctx: BmcQueryParser.Init_var_refContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#assume_clause.
    def enterAssume_clause(self, ctx: BmcQueryParser.Assume_clauseContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#assume_clause.
    def exitAssume_clause(self, ctx: BmcQueryParser.Assume_clauseContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#frame_assume.
    def enterFrame_assume(self, ctx: BmcQueryParser.Frame_assumeContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#frame_assume.
    def exitFrame_assume(self, ctx: BmcQueryParser.Frame_assumeContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#event_assume.
    def enterEvent_assume(self, ctx: BmcQueryParser.Event_assumeContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#event_assume.
    def exitEvent_assume(self, ctx: BmcQueryParser.Event_assumeContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#cardinality_assume.
    def enterCardinality_assume(self, ctx: BmcQueryParser.Cardinality_assumeContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#cardinality_assume.
    def exitCardinality_assume(self, ctx: BmcQueryParser.Cardinality_assumeContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#check_clause.
    def enterCheck_clause(self, ctx: BmcQueryParser.Check_clauseContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#check_clause.
    def exitCheck_clause(self, ctx: BmcQueryParser.Check_clauseContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#property_kind.
    def enterProperty_kind(self, ctx: BmcQueryParser.Property_kindContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#property_kind.
    def exitProperty_kind(self, ctx: BmcQueryParser.Property_kindContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#property_body.
    def enterProperty_body(self, ctx: BmcQueryParser.Property_bodyContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#property_body.
    def exitProperty_body(self, ctx: BmcQueryParser.Property_bodyContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#response_property_body.
    def enterResponse_property_body(
        self, ctx: BmcQueryParser.Response_property_bodyContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#response_property_body.
    def exitResponse_property_body(
        self, ctx: BmcQueryParser.Response_property_bodyContext
    ):
        pass

    # Enter a parse tree produced by BmcQueryParser#string_list.
    def enterString_list(self, ctx: BmcQueryParser.String_listContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#string_list.
    def exitString_list(self, ctx: BmcQueryParser.String_listContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#bool_cmp_op.
    def enterBool_cmp_op(self, ctx: BmcQueryParser.Bool_cmp_opContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#bool_cmp_op.
    def exitBool_cmp_op(self, ctx: BmcQueryParser.Bool_cmp_opContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#event_range_selector.
    def enterEvent_range_selector(
        self, ctx: BmcQueryParser.Event_range_selectorContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#event_range_selector.
    def exitEvent_range_selector(self, ctx: BmcQueryParser.Event_range_selectorContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#event_cycle_selector.
    def enterEvent_cycle_selector(
        self, ctx: BmcQueryParser.Event_cycle_selectorContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#event_cycle_selector.
    def exitEvent_cycle_selector(self, ctx: BmcQueryParser.Event_cycle_selectorContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#frame_selector.
    def enterFrame_selector(self, ctx: BmcQueryParser.Frame_selectorContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#frame_selector.
    def exitFrame_selector(self, ctx: BmcQueryParser.Frame_selectorContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#integer_literal.
    def enterInteger_literal(self, ctx: BmcQueryParser.Integer_literalContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#integer_literal.
    def exitInteger_literal(self, ctx: BmcQueryParser.Integer_literalContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#frameVarExprNum.
    def enterFrameVarExprNum(self, ctx: BmcQueryParser.FrameVarExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#frameVarExprNum.
    def exitFrameVarExprNum(self, ctx: BmcQueryParser.FrameVarExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#cycleExprNum.
    def enterCycleExprNum(self, ctx: BmcQueryParser.CycleExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#cycleExprNum.
    def exitCycleExprNum(self, ctx: BmcQueryParser.CycleExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#unaryExprNum.
    def enterUnaryExprNum(self, ctx: BmcQueryParser.UnaryExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#unaryExprNum.
    def exitUnaryExprNum(self, ctx: BmcQueryParser.UnaryExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#funcExprNum.
    def enterFuncExprNum(self, ctx: BmcQueryParser.FuncExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#funcExprNum.
    def exitFuncExprNum(self, ctx: BmcQueryParser.FuncExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#conditionalCStyleExprNum.
    def enterConditionalCStyleExprNum(
        self, ctx: BmcQueryParser.ConditionalCStyleExprNumContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#conditionalCStyleExprNum.
    def exitConditionalCStyleExprNum(
        self, ctx: BmcQueryParser.ConditionalCStyleExprNumContext
    ):
        pass

    # Enter a parse tree produced by BmcQueryParser#binaryExprNum.
    def enterBinaryExprNum(self, ctx: BmcQueryParser.BinaryExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#binaryExprNum.
    def exitBinaryExprNum(self, ctx: BmcQueryParser.BinaryExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#literalExprNum.
    def enterLiteralExprNum(self, ctx: BmcQueryParser.LiteralExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#literalExprNum.
    def exitLiteralExprNum(self, ctx: BmcQueryParser.LiteralExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#mathConstExprNum.
    def enterMathConstExprNum(self, ctx: BmcQueryParser.MathConstExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#mathConstExprNum.
    def exitMathConstExprNum(self, ctx: BmcQueryParser.MathConstExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#parenExprNum.
    def enterParenExprNum(self, ctx: BmcQueryParser.ParenExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#parenExprNum.
    def exitParenExprNum(self, ctx: BmcQueryParser.ParenExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#idExprNum.
    def enterIdExprNum(self, ctx: BmcQueryParser.IdExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#idExprNum.
    def exitIdExprNum(self, ctx: BmcQueryParser.IdExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#callCountExprNum.
    def enterCallCountExprNum(self, ctx: BmcQueryParser.CallCountExprNumContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#callCountExprNum.
    def exitCallCountExprNum(self, ctx: BmcQueryParser.CallCountExprNumContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#conditionalCStyleExprCond.
    def enterConditionalCStyleExprCond(
        self, ctx: BmcQueryParser.ConditionalCStyleExprCondContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#conditionalCStyleExprCond.
    def exitConditionalCStyleExprCond(
        self, ctx: BmcQueryParser.ConditionalCStyleExprCondContext
    ):
        pass

    # Enter a parse tree produced by BmcQueryParser#atomExprCond.
    def enterAtomExprCond(self, ctx: BmcQueryParser.AtomExprCondContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#atomExprCond.
    def exitAtomExprCond(self, ctx: BmcQueryParser.AtomExprCondContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#binaryExprFromCondCond.
    def enterBinaryExprFromCondCond(
        self, ctx: BmcQueryParser.BinaryExprFromCondCondContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#binaryExprFromCondCond.
    def exitBinaryExprFromCondCond(
        self, ctx: BmcQueryParser.BinaryExprFromCondCondContext
    ):
        pass

    # Enter a parse tree produced by BmcQueryParser#binaryExprCond.
    def enterBinaryExprCond(self, ctx: BmcQueryParser.BinaryExprCondContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#binaryExprCond.
    def exitBinaryExprCond(self, ctx: BmcQueryParser.BinaryExprCondContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#binaryExprFromNumCond.
    def enterBinaryExprFromNumCond(
        self, ctx: BmcQueryParser.BinaryExprFromNumCondContext
    ):
        pass

    # Exit a parse tree produced by BmcQueryParser#binaryExprFromNumCond.
    def exitBinaryExprFromNumCond(
        self, ctx: BmcQueryParser.BinaryExprFromNumCondContext
    ):
        pass

    # Enter a parse tree produced by BmcQueryParser#unaryExprCond.
    def enterUnaryExprCond(self, ctx: BmcQueryParser.UnaryExprCondContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#unaryExprCond.
    def exitUnaryExprCond(self, ctx: BmcQueryParser.UnaryExprCondContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#parenExprCond.
    def enterParenExprCond(self, ctx: BmcQueryParser.ParenExprCondContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#parenExprCond.
    def exitParenExprCond(self, ctx: BmcQueryParser.ParenExprCondContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#literalExprCond.
    def enterLiteralExprCond(self, ctx: BmcQueryParser.LiteralExprCondContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#literalExprCond.
    def exitLiteralExprCond(self, ctx: BmcQueryParser.LiteralExprCondContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#bmc_boolean_atom.
    def enterBmc_boolean_atom(self, ctx: BmcQueryParser.Bmc_boolean_atomContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#bmc_boolean_atom.
    def exitBmc_boolean_atom(self, ctx: BmcQueryParser.Bmc_boolean_atomContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#call_arguments.
    def enterCall_arguments(self, ctx: BmcQueryParser.Call_argumentsContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#call_arguments.
    def exitCall_arguments(self, ctx: BmcQueryParser.Call_argumentsContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#call_argument.
    def enterCall_argument(self, ctx: BmcQueryParser.Call_argumentContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#call_argument.
    def exitCall_argument(self, ctx: BmcQueryParser.Call_argumentContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#call_step_selector.
    def enterCall_step_selector(self, ctx: BmcQueryParser.Call_step_selectorContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#call_step_selector.
    def exitCall_step_selector(self, ctx: BmcQueryParser.Call_step_selectorContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#call_step_point.
    def enterCall_step_point(self, ctx: BmcQueryParser.Call_step_pointContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#call_step_point.
    def exitCall_step_point(self, ctx: BmcQueryParser.Call_step_pointContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#num_literal.
    def enterNum_literal(self, ctx: BmcQueryParser.Num_literalContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#num_literal.
    def exitNum_literal(self, ctx: BmcQueryParser.Num_literalContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#bool_literal.
    def enterBool_literal(self, ctx: BmcQueryParser.Bool_literalContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#bool_literal.
    def exitBool_literal(self, ctx: BmcQueryParser.Bool_literalContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#math_const.
    def enterMath_const(self, ctx: BmcQueryParser.Math_constContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#math_const.
    def exitMath_const(self, ctx: BmcQueryParser.Math_constContext):
        pass

    # Enter a parse tree produced by BmcQueryParser#string_literal.
    def enterString_literal(self, ctx: BmcQueryParser.String_literalContext):
        pass

    # Exit a parse tree produced by BmcQueryParser#string_literal.
    def exitString_literal(self, ctx: BmcQueryParser.String_literalContext):
        pass


del BmcQueryParser
