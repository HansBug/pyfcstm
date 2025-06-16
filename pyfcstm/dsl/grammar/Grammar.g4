// Grammar.g4
grammar Grammar;

// program: statement+;

// for guard condition
condition: cond_expression EOF;

state_machine_dsl: def_assignment* state_definition EOF;

def_assignment: 'def' deftype=('int'|'float') ID '=' init_expression ';';

state_definition
    : 'state' state_id=ID ';'                             # leafStateDefinition
    | 'state' state_id=ID '{' state_inner_statement* '}'  # compositeStateDefinition
    ;

transition_definition
    : '[*]' '->' to_state=ID (|':' chain_id|':' 'if' '[' cond_expression ']') (';'|'post' '{' operational_statement* '}')          # entryTransitionDefinition
    | from_state=ID '->' to_state=ID (|':' chain_id|':' 'if' '[' cond_expression ']') (';'|'post' '{' operational_statement* '}')  # normalTransitionDefinition
    | from_state=ID '->' '[*]' (|':' chain_id|':' 'if' '[' cond_expression ']') (';'|'post' '{' operational_statement* '}')        # exitTransitionDefinition
    ;

operational_statement
    : operational_assignment
    | ';'
    ;

state_inner_statement
    : state_definition
    | transition_definition
    | ';'
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

initial_assignment: ID ':=' init_expression ';';
constant_definition: ID '=' init_expression ';';
operational_assignment: ID ':=' num_expression ';';

init_expression
    : '(' init_expression ')'                                # parenExprInit
    | num_literal                                            # literalExprInit
    | math_const                                             # mathConstExprInit
    | op=('+'|'-') init_expression                           # unaryExprInit
    | <assoc=right> init_expression op='**' init_expression  # binaryExprInit
    | init_expression op=('*'|'/'|'%') init_expression       # binaryExprInit
    | init_expression op=('+'|'-') init_expression           # binaryExprInit
    | init_expression op=('<<'|'>>') init_expression         # binaryExprInit
    | init_expression op=('&'|'|'|'^') init_expression       # binaryExprInit
    | function=UFUNC_NAME '(' init_expression ')'            # funcExprInit
    ;

num_expression
    : '(' num_expression ')'                               # parenExprNum
    | num_literal                                          # literalExprNum
    | ID                                                   # idExprNum
    | math_const                                           # mathConstExprNum
    | op=('+'|'-') num_expression                          # unaryExprNum
    | <assoc=right> num_expression op='**' num_expression  # binaryExprNum
    | num_expression op=('*'|'/'|'%') num_expression       # binaryExprNum
    | num_expression op=('+'|'-') num_expression           # binaryExprNum
    | num_expression op=('<<'|'>>') num_expression         # binaryExprNum
    | num_expression op=('&'|'|'|'^') num_expression       # binaryExprNum
    | function=UFUNC_NAME '(' num_expression ')'           # funcExprNum
    | <assoc=right> '(' cond_expression ')' '?' num_expression ':' num_expression  # conditionalCStyleExprNum
    ;

cond_expression
    : '(' cond_expression ')'                               # parenExprCond
    | bool_literal                                          # literalExprCond
    | op=('!'|'not') cond_expression                        # unaryExprCond
    | num_expression op=('<'|'>'|'<='|'>=') num_expression  # binaryExprFromNumCond
    | num_expression op=('=='|'!=') num_expression          # binaryExprFromNumCond
    | cond_expression op=('&&'|'and') cond_expression       # binaryExprCond
    | cond_expression op=('||'|'or') cond_expression        # binaryExprCond
    | <assoc=right> '(' cond_expression ')' '?' cond_expression ':' cond_expression  # conditionalCStyleCondNum
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

math_const: 'pi' | 'E' | 'tau';

chain_id: ID ('.' ID)*;

FLOAT: [0-9]+'.'[0-9]* ([eE][+-]?[0-9]+)?
     | '.'[0-9]+ ([eE][+-]?[0-9]+)?
     | [0-9]+ [eE][+-]?[0-9]+;
INT: [0-9]+;
HEX_INT: '0x' HexDigit+;

TRUE: 'True' | 'true' | 'TRUE';
FALSE: 'False' | 'false' | 'FALSE';

UFUNC_NAME : 'sin' | 'cos' | 'tan' | 'asin' | 'acos' | 'atan'
           | 'sinh' | 'cosh' | 'tanh' | 'asinh' | 'acosh' | 'atanh'
           | 'sqrt' | 'cbrt' | 'exp' | 'log' | 'log10' | 'log2' | 'log1p'
           | 'abs' | 'ceil' | 'floor' | 'round' | 'trunc'
           | 'sign'
           ;

ID: [a-zA-Z_][a-zA-Z0-9_]*;

STRING
    : '"' (~["\\\r\n] | EscapeSequence)* '"'
    | '\'' (~['\\\r\n] | EscapeSequence)* '\''
    ;

fragment EscapeSequence
    : '\\' [btnfr"'\\]
    | '\\' ([0-3]? [0-7])? [0-7]
    | '\\' 'u' HexDigit HexDigit HexDigit HexDigit
    | '\\' 'x' HexDigit HexDigit
    ;

fragment HexDigit
    : [0-9a-fA-F]
    ;

WS: [ \t\n\r]+ -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip;
LINE_COMMENT: '//' ~[\r\n]* -> skip;
PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
