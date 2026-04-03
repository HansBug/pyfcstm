// Grammar.g4
parser grammar Grammar;

options {
    tokenVocab = GrammarLexer;
}

// program: statement+;

// for guard condition
condition: cond_expression EOF;

state_machine_dsl: def_assignment* state_definition EOF;

def_assignment: DEF deftype=(INT_TYPE | FLOAT_TYPE) ID ASSIGN init_expression SEMI;

state_definition
    : pseudo=PSEUDO? STATE state_id=ID (NAMED extra_name=STRING)? SEMI                             # leafStateDefinition
    | pseudo=PSEUDO? STATE state_id=ID (NAMED extra_name=STRING)? LBRACE state_inner_statement* RBRACE  # compositeStateDefinition
    ;

transition_definition
    : INIT_MARKER ARROW to_state=ID (|(COLON | COLONCOLON) chain_id | COLON IF LBRACK cond_expression RBRACK) (SEMI | EFFECT LBRACE operational_statement_set RBRACE)                   # entryTransitionDefinition
    | from_state=ID ARROW to_state=ID (|COLONCOLON from_id=ID | COLON chain_id | COLON IF LBRACK cond_expression RBRACK) (SEMI | EFFECT LBRACE operational_statement_set RBRACE)  # normalTransitionDefinition
    | from_state=ID ARROW INIT_MARKER (|COLONCOLON from_id=ID | COLON chain_id | COLON IF LBRACK cond_expression RBRACK) (SEMI | EFFECT LBRACE operational_statement_set RBRACE)        # exitTransitionDefinition
    ;

transition_force_definition
    : BANG from_state=ID ARROW to_state=ID (|COLONCOLON from_id=ID | COLON chain_id | COLON IF LBRACK cond_expression RBRACK) SEMI  # normalForceTransitionDefinition
    | BANG from_state=ID ARROW INIT_MARKER (|COLONCOLON from_id=ID | COLON chain_id | COLON IF LBRACK cond_expression RBRACK) SEMI        # exitForceTransitionDefinition
    | BANG STAR ARROW to_state=ID (|(COLONCOLON | COLON) chain_id | COLON IF LBRACK cond_expression RBRACK) SEMI                     # normalAllForceTransitionDefinition
    | BANG STAR ARROW INIT_MARKER (|(COLONCOLON | COLON) chain_id | COLON IF LBRACK cond_expression RBRACK) SEMI                           # exitAllForceTransitionDefinition
    ;

enter_definition
    : ENTER (func_name=ID)? LBRACE operational_statement_set RBRACE        # enterOperations
    | ENTER ABSTRACT func_name=ID SEMI                           # enterAbstractFunc
    | ENTER ABSTRACT (func_name=ID)? raw_doc=MULTILINE_COMMENT  # enterAbstractFunc
    | ENTER (func_name=ID)? REF chain_id SEMI                    # enterRefFunc
    ;

exit_definition
    : EXIT (func_name=ID)? LBRACE operational_statement_set RBRACE        # exitOperations
    | EXIT ABSTRACT func_name=ID SEMI                           # exitAbstractFunc
    | EXIT ABSTRACT (func_name=ID)? raw_doc=MULTILINE_COMMENT  # exitAbstractFunc
    | EXIT (func_name=ID)? REF chain_id SEMI                    # exitRefFunc
    ;

during_definition
    : DURING aspect=(BEFORE | AFTER)? (func_name=ID)? LBRACE operational_statement_set RBRACE        # duringOperations
    | DURING aspect=(BEFORE | AFTER)? ABSTRACT func_name=ID SEMI                           # duringAbstractFunc
    | DURING aspect=(BEFORE | AFTER)? ABSTRACT (func_name=ID)? raw_doc=MULTILINE_COMMENT  # duringAbstractFunc
    | DURING aspect=(BEFORE | AFTER)? (func_name=ID)? REF chain_id SEMI                    # duringRefFunc
    ;

during_aspect_definition
    : SHIFT_RIGHT DURING aspect=(BEFORE | AFTER) (func_name=ID)? LBRACE operational_statement_set RBRACE        # duringAspectOperations
    | SHIFT_RIGHT DURING aspect=(BEFORE | AFTER) ABSTRACT func_name=ID SEMI                           # duringAspectAbstractFunc
    | SHIFT_RIGHT DURING aspect=(BEFORE | AFTER) ABSTRACT (func_name=ID)? raw_doc=MULTILINE_COMMENT  # duringAspectAbstractFunc
    | SHIFT_RIGHT DURING aspect=(BEFORE | AFTER) (func_name=ID)? REF chain_id SEMI                    # duringAspectRefFunc
    ;

event_definition: EVENT event_name=ID (NAMED extra_name=STRING)? SEMI;

import_statement
    : IMPORT import_path=STRING AS state_alias=ID (NAMED extra_name=STRING)?
      (LBRACE import_mapping_statement* RBRACE | SEMI)
    ;

import_mapping_statement
    : import_def_mapping
    | import_event_mapping
    | SEMI
    ;

import_def_mapping
    : DEF import_def_selector ARROW import_def_target_template SEMI
    ;

import_def_selector
    : STAR                                                           # importDefFallbackSelector
    | LBRACE selector_items+=ID (COMMA selector_items+=ID)* RBRACE   # importDefSetSelector
    | selector_pattern=IMPORT_DEF_SELECTOR_PATTERN                   # importDefPatternSelector
    | selector_name=ID                                               # importDefExactSelector
    ;

import_def_target_template
    : target_text=ID
    | target_text=IMPORT_DEF_TARGET_TEMPLATE
    | target_text=STAR
    ;

import_event_mapping
    : EVENT source_event=chain_id ARROW target_event=chain_id (NAMED extra_name=STRING)? SEMI
    ;

operation_assignment: ID ASSIGN num_expression SEMI;

operation_block
    : LBRACE operational_statement_set RBRACE
    ;

if_statement
    : IF LBRACK cond_expression RBRACK operation_block
      (ELSE IF LBRACK cond_expression RBRACK operation_block)*
      (ELSE operation_block)?
    ;

operational_statement
    : operation_assignment
    | if_statement
    | SEMI
    ;

operational_statement_set
    : operational_statement*
    ;

state_inner_statement
    : state_definition
    | transition_definition
    | transition_force_definition
    | enter_definition
    | during_definition
    | exit_definition
    | during_aspect_definition
    | event_definition
    | import_statement
    | SEMI
    ;

// basic configs for the previous design
// for on_xxx operations
operation_program: operational_assignment* EOF;

// for preamable initialization
preamble_program: preamble_statement* EOF;
preamble_statement
    : initial_assignment
    | constant_definition
    ;

initial_assignment: ID DECLARE_ASSIGN init_expression SEMI;
constant_definition: ID ASSIGN init_expression SEMI;
operational_assignment: ID DECLARE_ASSIGN num_expression SEMI;

generic_expression
    : num_expression
    | cond_expression
    ;

init_expression
    : LPAREN init_expression RPAREN                                # parenExprInit
    | num_literal                                            # literalExprInit
    | math_const                                             # mathConstExprInit
    | op=(PLUS | MINUS) init_expression                           # unaryExprInit
    | <assoc=right> init_expression op=POW init_expression  # binaryExprInit
    | init_expression op=(STAR | SLASH | PERCENT) init_expression       # binaryExprInit
    | init_expression op=(PLUS | MINUS) init_expression           # binaryExprInit
    | init_expression op=(SHIFT_LEFT | SHIFT_RIGHT) init_expression         # binaryExprInit
    | init_expression op=AMP init_expression                 # binaryExprInit
    | init_expression op=CARET init_expression                 # binaryExprInit
    | init_expression op=PIPE init_expression                 # binaryExprInit
    | func_name=UFUNC_NAME LPAREN init_expression RPAREN           # funcExprInit
    ;

num_expression
    : LPAREN num_expression RPAREN                               # parenExprNum
    | num_literal                                          # literalExprNum
    | ID                                                   # idExprNum
    | math_const                                           # mathConstExprNum
    | op=(PLUS | MINUS) num_expression                          # unaryExprNum
    | <assoc=right> num_expression op=POW num_expression  # binaryExprNum
    | num_expression op=(STAR | SLASH | PERCENT) num_expression       # binaryExprNum
    | num_expression op=(PLUS | MINUS) num_expression           # binaryExprNum
    | num_expression op=(SHIFT_LEFT | SHIFT_RIGHT) num_expression         # binaryExprNum
    | num_expression op=AMP num_expression                 # binaryExprNum
    | num_expression op=CARET num_expression                 # binaryExprNum
    | num_expression op=PIPE num_expression                 # binaryExprNum
    | func_name=UFUNC_NAME LPAREN num_expression RPAREN          # funcExprNum
    | <assoc=right> LPAREN cond_expression RPAREN QUESTION num_expression COLON num_expression  # conditionalCStyleExprNum
    ;

cond_expression
    : LPAREN cond_expression RPAREN                               # parenExprCond
    | bool_literal                                          # literalExprCond
    | op=(BANG | NOT_KW) cond_expression                        # unaryExprCond
    | num_expression op=(LT | GT | LE | GE) num_expression  # binaryExprFromNumCond
    | num_expression op=(EQ | NE) num_expression          # binaryExprFromNumCond
    | cond_expression op=(EQ | NE) cond_expression        # binaryExprFromCondCond
    | cond_expression op=(LOGICAL_AND | AND_KW) cond_expression       # binaryExprCond
    | cond_expression op=(LOGICAL_OR | OR_KW) cond_expression        # binaryExprCond
    | <assoc=right> LPAREN cond_expression RPAREN QUESTION cond_expression COLON cond_expression  # conditionalCStyleCondNum
    ;

num_literal
    : INT
    | FLOAT
    | HEX_INT
    ;

bool_literal
    : TRUE
    | FALSE
    ;

math_const: PI_CONST | E_CONST | TAU_CONST;

chain_id: isabs=SLASH? ID (DOT ID)*;
