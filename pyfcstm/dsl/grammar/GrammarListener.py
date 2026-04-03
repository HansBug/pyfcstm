# Generated from Grammar.g4 by ANTLR 4.9.3
from antlr4 import *

if __name__ is not None and "." in __name__:
    from .Grammar import Grammar
else:
    from Grammar import Grammar


# This class defines a complete listener for a parse tree produced by Grammar.
class GrammarListener(ParseTreeListener):
    # Enter a parse tree produced by Grammar#condition.
    def enterCondition(self, ctx: Grammar.ConditionContext):
        pass

    # Exit a parse tree produced by Grammar#condition.
    def exitCondition(self, ctx: Grammar.ConditionContext):
        pass

    # Enter a parse tree produced by Grammar#state_machine_dsl.
    def enterState_machine_dsl(self, ctx: Grammar.State_machine_dslContext):
        pass

    # Exit a parse tree produced by Grammar#state_machine_dsl.
    def exitState_machine_dsl(self, ctx: Grammar.State_machine_dslContext):
        pass

    # Enter a parse tree produced by Grammar#def_assignment.
    def enterDef_assignment(self, ctx: Grammar.Def_assignmentContext):
        pass

    # Exit a parse tree produced by Grammar#def_assignment.
    def exitDef_assignment(self, ctx: Grammar.Def_assignmentContext):
        pass

    # Enter a parse tree produced by Grammar#leafStateDefinition.
    def enterLeafStateDefinition(self, ctx: Grammar.LeafStateDefinitionContext):
        pass

    # Exit a parse tree produced by Grammar#leafStateDefinition.
    def exitLeafStateDefinition(self, ctx: Grammar.LeafStateDefinitionContext):
        pass

    # Enter a parse tree produced by Grammar#compositeStateDefinition.
    def enterCompositeStateDefinition(
        self, ctx: Grammar.CompositeStateDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#compositeStateDefinition.
    def exitCompositeStateDefinition(
        self, ctx: Grammar.CompositeStateDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#entryTransitionDefinition.
    def enterEntryTransitionDefinition(
        self, ctx: Grammar.EntryTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#entryTransitionDefinition.
    def exitEntryTransitionDefinition(
        self, ctx: Grammar.EntryTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#normalTransitionDefinition.
    def enterNormalTransitionDefinition(
        self, ctx: Grammar.NormalTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#normalTransitionDefinition.
    def exitNormalTransitionDefinition(
        self, ctx: Grammar.NormalTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#exitTransitionDefinition.
    def enterExitTransitionDefinition(
        self, ctx: Grammar.ExitTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#exitTransitionDefinition.
    def exitExitTransitionDefinition(
        self, ctx: Grammar.ExitTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#normalForceTransitionDefinition.
    def enterNormalForceTransitionDefinition(
        self, ctx: Grammar.NormalForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#normalForceTransitionDefinition.
    def exitNormalForceTransitionDefinition(
        self, ctx: Grammar.NormalForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#exitForceTransitionDefinition.
    def enterExitForceTransitionDefinition(
        self, ctx: Grammar.ExitForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#exitForceTransitionDefinition.
    def exitExitForceTransitionDefinition(
        self, ctx: Grammar.ExitForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#normalAllForceTransitionDefinition.
    def enterNormalAllForceTransitionDefinition(
        self, ctx: Grammar.NormalAllForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#normalAllForceTransitionDefinition.
    def exitNormalAllForceTransitionDefinition(
        self, ctx: Grammar.NormalAllForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#exitAllForceTransitionDefinition.
    def enterExitAllForceTransitionDefinition(
        self, ctx: Grammar.ExitAllForceTransitionDefinitionContext
    ):
        pass

    # Exit a parse tree produced by Grammar#exitAllForceTransitionDefinition.
    def exitExitAllForceTransitionDefinition(
        self, ctx: Grammar.ExitAllForceTransitionDefinitionContext
    ):
        pass

    # Enter a parse tree produced by Grammar#enterOperations.
    def enterEnterOperations(self, ctx: Grammar.EnterOperationsContext):
        pass

    # Exit a parse tree produced by Grammar#enterOperations.
    def exitEnterOperations(self, ctx: Grammar.EnterOperationsContext):
        pass

    # Enter a parse tree produced by Grammar#enterAbstractFunc.
    def enterEnterAbstractFunc(self, ctx: Grammar.EnterAbstractFuncContext):
        pass

    # Exit a parse tree produced by Grammar#enterAbstractFunc.
    def exitEnterAbstractFunc(self, ctx: Grammar.EnterAbstractFuncContext):
        pass

    # Enter a parse tree produced by Grammar#enterRefFunc.
    def enterEnterRefFunc(self, ctx: Grammar.EnterRefFuncContext):
        pass

    # Exit a parse tree produced by Grammar#enterRefFunc.
    def exitEnterRefFunc(self, ctx: Grammar.EnterRefFuncContext):
        pass

    # Enter a parse tree produced by Grammar#exitOperations.
    def enterExitOperations(self, ctx: Grammar.ExitOperationsContext):
        pass

    # Exit a parse tree produced by Grammar#exitOperations.
    def exitExitOperations(self, ctx: Grammar.ExitOperationsContext):
        pass

    # Enter a parse tree produced by Grammar#exitAbstractFunc.
    def enterExitAbstractFunc(self, ctx: Grammar.ExitAbstractFuncContext):
        pass

    # Exit a parse tree produced by Grammar#exitAbstractFunc.
    def exitExitAbstractFunc(self, ctx: Grammar.ExitAbstractFuncContext):
        pass

    # Enter a parse tree produced by Grammar#exitRefFunc.
    def enterExitRefFunc(self, ctx: Grammar.ExitRefFuncContext):
        pass

    # Exit a parse tree produced by Grammar#exitRefFunc.
    def exitExitRefFunc(self, ctx: Grammar.ExitRefFuncContext):
        pass

    # Enter a parse tree produced by Grammar#duringOperations.
    def enterDuringOperations(self, ctx: Grammar.DuringOperationsContext):
        pass

    # Exit a parse tree produced by Grammar#duringOperations.
    def exitDuringOperations(self, ctx: Grammar.DuringOperationsContext):
        pass

    # Enter a parse tree produced by Grammar#duringAbstractFunc.
    def enterDuringAbstractFunc(self, ctx: Grammar.DuringAbstractFuncContext):
        pass

    # Exit a parse tree produced by Grammar#duringAbstractFunc.
    def exitDuringAbstractFunc(self, ctx: Grammar.DuringAbstractFuncContext):
        pass

    # Enter a parse tree produced by Grammar#duringRefFunc.
    def enterDuringRefFunc(self, ctx: Grammar.DuringRefFuncContext):
        pass

    # Exit a parse tree produced by Grammar#duringRefFunc.
    def exitDuringRefFunc(self, ctx: Grammar.DuringRefFuncContext):
        pass

    # Enter a parse tree produced by Grammar#duringAspectOperations.
    def enterDuringAspectOperations(self, ctx: Grammar.DuringAspectOperationsContext):
        pass

    # Exit a parse tree produced by Grammar#duringAspectOperations.
    def exitDuringAspectOperations(self, ctx: Grammar.DuringAspectOperationsContext):
        pass

    # Enter a parse tree produced by Grammar#duringAspectAbstractFunc.
    def enterDuringAspectAbstractFunc(
        self, ctx: Grammar.DuringAspectAbstractFuncContext
    ):
        pass

    # Exit a parse tree produced by Grammar#duringAspectAbstractFunc.
    def exitDuringAspectAbstractFunc(
        self, ctx: Grammar.DuringAspectAbstractFuncContext
    ):
        pass

    # Enter a parse tree produced by Grammar#duringAspectRefFunc.
    def enterDuringAspectRefFunc(self, ctx: Grammar.DuringAspectRefFuncContext):
        pass

    # Exit a parse tree produced by Grammar#duringAspectRefFunc.
    def exitDuringAspectRefFunc(self, ctx: Grammar.DuringAspectRefFuncContext):
        pass

    # Enter a parse tree produced by Grammar#event_definition.
    def enterEvent_definition(self, ctx: Grammar.Event_definitionContext):
        pass

    # Exit a parse tree produced by Grammar#event_definition.
    def exitEvent_definition(self, ctx: Grammar.Event_definitionContext):
        pass

    # Enter a parse tree produced by Grammar#import_statement.
    def enterImport_statement(self, ctx: Grammar.Import_statementContext):
        pass

    # Exit a parse tree produced by Grammar#import_statement.
    def exitImport_statement(self, ctx: Grammar.Import_statementContext):
        pass

    # Enter a parse tree produced by Grammar#import_mapping_statement.
    def enterImport_mapping_statement(
        self, ctx: Grammar.Import_mapping_statementContext
    ):
        pass

    # Exit a parse tree produced by Grammar#import_mapping_statement.
    def exitImport_mapping_statement(
        self, ctx: Grammar.Import_mapping_statementContext
    ):
        pass

    # Enter a parse tree produced by Grammar#import_def_mapping.
    def enterImport_def_mapping(self, ctx: Grammar.Import_def_mappingContext):
        pass

    # Exit a parse tree produced by Grammar#import_def_mapping.
    def exitImport_def_mapping(self, ctx: Grammar.Import_def_mappingContext):
        pass

    # Enter a parse tree produced by Grammar#importDefFallbackSelector.
    def enterImportDefFallbackSelector(
        self, ctx: Grammar.ImportDefFallbackSelectorContext
    ):
        pass

    # Exit a parse tree produced by Grammar#importDefFallbackSelector.
    def exitImportDefFallbackSelector(
        self, ctx: Grammar.ImportDefFallbackSelectorContext
    ):
        pass

    # Enter a parse tree produced by Grammar#importDefSetSelector.
    def enterImportDefSetSelector(self, ctx: Grammar.ImportDefSetSelectorContext):
        pass

    # Exit a parse tree produced by Grammar#importDefSetSelector.
    def exitImportDefSetSelector(self, ctx: Grammar.ImportDefSetSelectorContext):
        pass

    # Enter a parse tree produced by Grammar#importDefPatternSelector.
    def enterImportDefPatternSelector(
        self, ctx: Grammar.ImportDefPatternSelectorContext
    ):
        pass

    # Exit a parse tree produced by Grammar#importDefPatternSelector.
    def exitImportDefPatternSelector(
        self, ctx: Grammar.ImportDefPatternSelectorContext
    ):
        pass

    # Enter a parse tree produced by Grammar#importDefExactSelector.
    def enterImportDefExactSelector(self, ctx: Grammar.ImportDefExactSelectorContext):
        pass

    # Exit a parse tree produced by Grammar#importDefExactSelector.
    def exitImportDefExactSelector(self, ctx: Grammar.ImportDefExactSelectorContext):
        pass

    # Enter a parse tree produced by Grammar#import_def_target_template.
    def enterImport_def_target_template(
        self, ctx: Grammar.Import_def_target_templateContext
    ):
        pass

    # Exit a parse tree produced by Grammar#import_def_target_template.
    def exitImport_def_target_template(
        self, ctx: Grammar.Import_def_target_templateContext
    ):
        pass

    # Enter a parse tree produced by Grammar#import_event_mapping.
    def enterImport_event_mapping(self, ctx: Grammar.Import_event_mappingContext):
        pass

    # Exit a parse tree produced by Grammar#import_event_mapping.
    def exitImport_event_mapping(self, ctx: Grammar.Import_event_mappingContext):
        pass

    # Enter a parse tree produced by Grammar#operation_assignment.
    def enterOperation_assignment(self, ctx: Grammar.Operation_assignmentContext):
        pass

    # Exit a parse tree produced by Grammar#operation_assignment.
    def exitOperation_assignment(self, ctx: Grammar.Operation_assignmentContext):
        pass

    # Enter a parse tree produced by Grammar#operation_block.
    def enterOperation_block(self, ctx: Grammar.Operation_blockContext):
        pass

    # Exit a parse tree produced by Grammar#operation_block.
    def exitOperation_block(self, ctx: Grammar.Operation_blockContext):
        pass

    # Enter a parse tree produced by Grammar#if_statement.
    def enterIf_statement(self, ctx: Grammar.If_statementContext):
        pass

    # Exit a parse tree produced by Grammar#if_statement.
    def exitIf_statement(self, ctx: Grammar.If_statementContext):
        pass

    # Enter a parse tree produced by Grammar#operational_statement.
    def enterOperational_statement(self, ctx: Grammar.Operational_statementContext):
        pass

    # Exit a parse tree produced by Grammar#operational_statement.
    def exitOperational_statement(self, ctx: Grammar.Operational_statementContext):
        pass

    # Enter a parse tree produced by Grammar#operational_statement_set.
    def enterOperational_statement_set(
        self, ctx: Grammar.Operational_statement_setContext
    ):
        pass

    # Exit a parse tree produced by Grammar#operational_statement_set.
    def exitOperational_statement_set(
        self, ctx: Grammar.Operational_statement_setContext
    ):
        pass

    # Enter a parse tree produced by Grammar#state_inner_statement.
    def enterState_inner_statement(self, ctx: Grammar.State_inner_statementContext):
        pass

    # Exit a parse tree produced by Grammar#state_inner_statement.
    def exitState_inner_statement(self, ctx: Grammar.State_inner_statementContext):
        pass

    # Enter a parse tree produced by Grammar#operation_program.
    def enterOperation_program(self, ctx: Grammar.Operation_programContext):
        pass

    # Exit a parse tree produced by Grammar#operation_program.
    def exitOperation_program(self, ctx: Grammar.Operation_programContext):
        pass

    # Enter a parse tree produced by Grammar#preamble_program.
    def enterPreamble_program(self, ctx: Grammar.Preamble_programContext):
        pass

    # Exit a parse tree produced by Grammar#preamble_program.
    def exitPreamble_program(self, ctx: Grammar.Preamble_programContext):
        pass

    # Enter a parse tree produced by Grammar#preamble_statement.
    def enterPreamble_statement(self, ctx: Grammar.Preamble_statementContext):
        pass

    # Exit a parse tree produced by Grammar#preamble_statement.
    def exitPreamble_statement(self, ctx: Grammar.Preamble_statementContext):
        pass

    # Enter a parse tree produced by Grammar#initial_assignment.
    def enterInitial_assignment(self, ctx: Grammar.Initial_assignmentContext):
        pass

    # Exit a parse tree produced by Grammar#initial_assignment.
    def exitInitial_assignment(self, ctx: Grammar.Initial_assignmentContext):
        pass

    # Enter a parse tree produced by Grammar#constant_definition.
    def enterConstant_definition(self, ctx: Grammar.Constant_definitionContext):
        pass

    # Exit a parse tree produced by Grammar#constant_definition.
    def exitConstant_definition(self, ctx: Grammar.Constant_definitionContext):
        pass

    # Enter a parse tree produced by Grammar#operational_assignment.
    def enterOperational_assignment(self, ctx: Grammar.Operational_assignmentContext):
        pass

    # Exit a parse tree produced by Grammar#operational_assignment.
    def exitOperational_assignment(self, ctx: Grammar.Operational_assignmentContext):
        pass

    # Enter a parse tree produced by Grammar#generic_expression.
    def enterGeneric_expression(self, ctx: Grammar.Generic_expressionContext):
        pass

    # Exit a parse tree produced by Grammar#generic_expression.
    def exitGeneric_expression(self, ctx: Grammar.Generic_expressionContext):
        pass

    # Enter a parse tree produced by Grammar#funcExprInit.
    def enterFuncExprInit(self, ctx: Grammar.FuncExprInitContext):
        pass

    # Exit a parse tree produced by Grammar#funcExprInit.
    def exitFuncExprInit(self, ctx: Grammar.FuncExprInitContext):
        pass

    # Enter a parse tree produced by Grammar#unaryExprInit.
    def enterUnaryExprInit(self, ctx: Grammar.UnaryExprInitContext):
        pass

    # Exit a parse tree produced by Grammar#unaryExprInit.
    def exitUnaryExprInit(self, ctx: Grammar.UnaryExprInitContext):
        pass

    # Enter a parse tree produced by Grammar#binaryExprInit.
    def enterBinaryExprInit(self, ctx: Grammar.BinaryExprInitContext):
        pass

    # Exit a parse tree produced by Grammar#binaryExprInit.
    def exitBinaryExprInit(self, ctx: Grammar.BinaryExprInitContext):
        pass

    # Enter a parse tree produced by Grammar#literalExprInit.
    def enterLiteralExprInit(self, ctx: Grammar.LiteralExprInitContext):
        pass

    # Exit a parse tree produced by Grammar#literalExprInit.
    def exitLiteralExprInit(self, ctx: Grammar.LiteralExprInitContext):
        pass

    # Enter a parse tree produced by Grammar#mathConstExprInit.
    def enterMathConstExprInit(self, ctx: Grammar.MathConstExprInitContext):
        pass

    # Exit a parse tree produced by Grammar#mathConstExprInit.
    def exitMathConstExprInit(self, ctx: Grammar.MathConstExprInitContext):
        pass

    # Enter a parse tree produced by Grammar#parenExprInit.
    def enterParenExprInit(self, ctx: Grammar.ParenExprInitContext):
        pass

    # Exit a parse tree produced by Grammar#parenExprInit.
    def exitParenExprInit(self, ctx: Grammar.ParenExprInitContext):
        pass

    # Enter a parse tree produced by Grammar#unaryExprNum.
    def enterUnaryExprNum(self, ctx: Grammar.UnaryExprNumContext):
        pass

    # Exit a parse tree produced by Grammar#unaryExprNum.
    def exitUnaryExprNum(self, ctx: Grammar.UnaryExprNumContext):
        pass

    # Enter a parse tree produced by Grammar#funcExprNum.
    def enterFuncExprNum(self, ctx: Grammar.FuncExprNumContext):
        pass

    # Exit a parse tree produced by Grammar#funcExprNum.
    def exitFuncExprNum(self, ctx: Grammar.FuncExprNumContext):
        pass

    # Enter a parse tree produced by Grammar#conditionalCStyleExprNum.
    def enterConditionalCStyleExprNum(
        self, ctx: Grammar.ConditionalCStyleExprNumContext
    ):
        pass

    # Exit a parse tree produced by Grammar#conditionalCStyleExprNum.
    def exitConditionalCStyleExprNum(
        self, ctx: Grammar.ConditionalCStyleExprNumContext
    ):
        pass

    # Enter a parse tree produced by Grammar#binaryExprNum.
    def enterBinaryExprNum(self, ctx: Grammar.BinaryExprNumContext):
        pass

    # Exit a parse tree produced by Grammar#binaryExprNum.
    def exitBinaryExprNum(self, ctx: Grammar.BinaryExprNumContext):
        pass

    # Enter a parse tree produced by Grammar#literalExprNum.
    def enterLiteralExprNum(self, ctx: Grammar.LiteralExprNumContext):
        pass

    # Exit a parse tree produced by Grammar#literalExprNum.
    def exitLiteralExprNum(self, ctx: Grammar.LiteralExprNumContext):
        pass

    # Enter a parse tree produced by Grammar#mathConstExprNum.
    def enterMathConstExprNum(self, ctx: Grammar.MathConstExprNumContext):
        pass

    # Exit a parse tree produced by Grammar#mathConstExprNum.
    def exitMathConstExprNum(self, ctx: Grammar.MathConstExprNumContext):
        pass

    # Enter a parse tree produced by Grammar#parenExprNum.
    def enterParenExprNum(self, ctx: Grammar.ParenExprNumContext):
        pass

    # Exit a parse tree produced by Grammar#parenExprNum.
    def exitParenExprNum(self, ctx: Grammar.ParenExprNumContext):
        pass

    # Enter a parse tree produced by Grammar#idExprNum.
    def enterIdExprNum(self, ctx: Grammar.IdExprNumContext):
        pass

    # Exit a parse tree produced by Grammar#idExprNum.
    def exitIdExprNum(self, ctx: Grammar.IdExprNumContext):
        pass

    # Enter a parse tree produced by Grammar#binaryExprFromCondCond.
    def enterBinaryExprFromCondCond(self, ctx: Grammar.BinaryExprFromCondCondContext):
        pass

    # Exit a parse tree produced by Grammar#binaryExprFromCondCond.
    def exitBinaryExprFromCondCond(self, ctx: Grammar.BinaryExprFromCondCondContext):
        pass

    # Enter a parse tree produced by Grammar#binaryExprCond.
    def enterBinaryExprCond(self, ctx: Grammar.BinaryExprCondContext):
        pass

    # Exit a parse tree produced by Grammar#binaryExprCond.
    def exitBinaryExprCond(self, ctx: Grammar.BinaryExprCondContext):
        pass

    # Enter a parse tree produced by Grammar#binaryExprFromNumCond.
    def enterBinaryExprFromNumCond(self, ctx: Grammar.BinaryExprFromNumCondContext):
        pass

    # Exit a parse tree produced by Grammar#binaryExprFromNumCond.
    def exitBinaryExprFromNumCond(self, ctx: Grammar.BinaryExprFromNumCondContext):
        pass

    # Enter a parse tree produced by Grammar#unaryExprCond.
    def enterUnaryExprCond(self, ctx: Grammar.UnaryExprCondContext):
        pass

    # Exit a parse tree produced by Grammar#unaryExprCond.
    def exitUnaryExprCond(self, ctx: Grammar.UnaryExprCondContext):
        pass

    # Enter a parse tree produced by Grammar#parenExprCond.
    def enterParenExprCond(self, ctx: Grammar.ParenExprCondContext):
        pass

    # Exit a parse tree produced by Grammar#parenExprCond.
    def exitParenExprCond(self, ctx: Grammar.ParenExprCondContext):
        pass

    # Enter a parse tree produced by Grammar#literalExprCond.
    def enterLiteralExprCond(self, ctx: Grammar.LiteralExprCondContext):
        pass

    # Exit a parse tree produced by Grammar#literalExprCond.
    def exitLiteralExprCond(self, ctx: Grammar.LiteralExprCondContext):
        pass

    # Enter a parse tree produced by Grammar#conditionalCStyleCondNum.
    def enterConditionalCStyleCondNum(
        self, ctx: Grammar.ConditionalCStyleCondNumContext
    ):
        pass

    # Exit a parse tree produced by Grammar#conditionalCStyleCondNum.
    def exitConditionalCStyleCondNum(
        self, ctx: Grammar.ConditionalCStyleCondNumContext
    ):
        pass

    # Enter a parse tree produced by Grammar#num_literal.
    def enterNum_literal(self, ctx: Grammar.Num_literalContext):
        pass

    # Exit a parse tree produced by Grammar#num_literal.
    def exitNum_literal(self, ctx: Grammar.Num_literalContext):
        pass

    # Enter a parse tree produced by Grammar#bool_literal.
    def enterBool_literal(self, ctx: Grammar.Bool_literalContext):
        pass

    # Exit a parse tree produced by Grammar#bool_literal.
    def exitBool_literal(self, ctx: Grammar.Bool_literalContext):
        pass

    # Enter a parse tree produced by Grammar#math_const.
    def enterMath_const(self, ctx: Grammar.Math_constContext):
        pass

    # Exit a parse tree produced by Grammar#math_const.
    def exitMath_const(self, ctx: Grammar.Math_constContext):
        pass

    # Enter a parse tree produced by Grammar#chain_id.
    def enterChain_id(self, ctx: Grammar.Chain_idContext):
        pass

    # Exit a parse tree produced by Grammar#chain_id.
    def exitChain_id(self, ctx: Grammar.Chain_idContext):
        pass


del Grammar
