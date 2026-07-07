/*
 * BmcQueryParser.g4
 *
 * Parser grammar for FCSTM BMC Query (``.fbmcq``) files.
 *
 * The parser stays syntax-only. Model-aware path resolution, query binding,
 * solver lowering, unsupported diagnostics, and witness replay belong to later
 * BMC layers.
 */
parser grammar BmcQueryParser;

options {
    tokenVocab = BmcQueryLexer;
}

query
    : init_clause? assume_clause* check_clause EOF
    ;

bmc_num_expression_entry
    : bmc_num_expression EOF
    ;

bmc_cond_expression_entry
    : bmc_cond_expression EOF
    ;

init_clause
    : INIT init_target init_havoc_clause? (WHERE bmc_cond_expression)? SEMI
    ;

init_target
    : COLD
    | TERMINATED
    | STATE LPAREN string_literal RPAREN
    ;

init_havoc_clause
    : HAVOC STAR
    | HAVOC LBRACE init_var_ref (COMMA init_var_ref)* RBRACE
    ;

init_var_ref
    : ID
    | string_literal
    ;

assume_clause
    : frame_assume
    | event_assume
    | cardinality_assume
    ;

frame_assume
    : ASSUME (ALWAYS | AT integer_literal) COLON bmc_cond_expression SEMI
    ;

event_assume
    : ASSUME EVENT LPAREN string_literal COMMA event_range_selector RPAREN bool_cmp_op bool_literal SEMI
    ;

cardinality_assume
    : ASSUME EVENTS CARDINALITY (ANY | AT_MOST_ONE LBRACE string_list RBRACE) SEMI
    ;

check_clause
    : CHECK property_kind LE integer_literal COLON property_body SEMI
    ;

property_kind
    : REACH
    | FORBID
    | INVARIANT
    | MUST_REACH
    | EXISTS_ALWAYS
    | RESPONSE
    | COVER
    ;

property_body
    : response_property_body
    | bmc_cond_expression
    ;

response_property_body
    : TRIGGER bmc_cond_expression ARROW WITHIN integer_literal bmc_cond_expression
    ;

string_list
    : string_literal (COMMA string_literal)*
    ;

bool_cmp_op
    : EQ
    | NE
    ;

event_range_selector
    : STAR
    | integer_literal
    | integer_literal DOTDOT integer_literal
    | RANGE_INT
    ;

event_cycle_selector
    : CURRENT
    | integer_literal
    ;

frame_selector
    : CURRENT
    | integer_literal
    ;

integer_literal
    : INT
    ;

bmc_num_expression
    : LPAREN bmc_num_expression RPAREN
        # parenExprNum
    | num_literal
        # literalExprNum
    | ID
        # idExprNum
    | math_const
        # mathConstExprNum
    | VAR LPAREN string_literal RPAREN
        # frameVarExprNum
    | CYCLE
        # cycleExprNum
    | op=(PLUS | MINUS) bmc_num_expression
        # unaryExprNum
    | <assoc=right> bmc_num_expression op=POW bmc_num_expression
        # binaryExprNum
    | bmc_num_expression op=(STAR | SLASH | PERCENT) bmc_num_expression
        # binaryExprNum
    | bmc_num_expression op=(PLUS | MINUS) bmc_num_expression
        # binaryExprNum
    | bmc_num_expression op=(SHIFT_LEFT | SHIFT_RIGHT) bmc_num_expression
        # binaryExprNum
    | bmc_num_expression op=AMP bmc_num_expression
        # binaryExprNum
    | bmc_num_expression op=CARET bmc_num_expression
        # binaryExprNum
    | bmc_num_expression op=PIPE bmc_num_expression
        # binaryExprNum
    | func_name=UFUNC_NAME LPAREN bmc_num_expression RPAREN
        # funcExprNum
    | <assoc=right> LPAREN bmc_cond_expression RPAREN QUESTION bmc_num_expression COLON bmc_num_expression
        # conditionalCStyleExprNum
    ;

bmc_cond_expression
    : LPAREN bmc_cond_expression RPAREN
        # parenExprCond
    | bool_literal
        # literalExprCond
    | bmc_boolean_atom
        # atomExprCond
    | op=(BANG | NOT_KW) bmc_cond_expression
        # unaryExprCond
    | bmc_num_expression op=(LT | GT | LE | GE) bmc_num_expression
        # binaryExprFromNumCond
    | bmc_num_expression op=(EQ | NE) bmc_num_expression
        # binaryExprFromNumCond
    | bmc_cond_expression op=(EQ | NE | IFF_KW) bmc_cond_expression
        # binaryExprFromCondCond
    | bmc_cond_expression op=(LOGICAL_AND | AND_KW) bmc_cond_expression
        # binaryExprCond
    | bmc_cond_expression op=XOR_KW bmc_cond_expression
        # binaryExprCond
    | bmc_cond_expression op=(LOGICAL_OR | OR_KW) bmc_cond_expression
        # binaryExprCond
    | <assoc=right> bmc_cond_expression op=(IMPLIES | IMPLIES_KW) bmc_cond_expression
        # binaryExprCond
    | <assoc=right> LPAREN bmc_cond_expression RPAREN QUESTION bmc_cond_expression COLON bmc_cond_expression
        # conditionalCStyleExprCond
    ;

bmc_boolean_atom
    : ACTIVE LPAREN string_literal (COMMA frame_selector)? RPAREN
    | TERMINATED LPAREN frame_selector? RPAREN
    | EVENT LPAREN string_literal COMMA event_cycle_selector RPAREN
    | CASE LPAREN string_literal (COMMA frame_selector)? RPAREN
    | CALLED LPAREN string_literal (COMMA frame_selector)? RPAREN
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

math_const
    : PI_CONST
    | E_CONST
    | TAU_CONST
    ;

string_literal
    : STRING
    ;
