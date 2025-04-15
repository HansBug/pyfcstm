// Grammar.g4
grammar Grammar;

// program: statement+;

// for guard condition
condition: cond_expression;

// for on_xxx operations
operation_program: operational_assignment+;

// for preamable initialization
preamble_program: preamble_statement+;
preamble_statement
    : initial_assignment
    | constant_definition
    ;

initial_assignment: ID ':=' init_expression ';';
constant_definition: ID '=' init_expression ';';
operational_assignment: ID ':=' num_expression ';';

init_expression
    : '(' init_expression ')'                           # parenExprInit
    | num_literal                                       # literalExprInit
    | math_const                                        # mathConstExprInit
    | op=('+'|'-') init_expression                      # unaryExprInit
    | init_expression op='**' init_expression           # binaryExprInit
    | init_expression op=('*'|'/'|'%') init_expression  # binaryExprInit
    | init_expression op=('+'|'-') init_expression      # binaryExprInit
    | init_expression op=('<<'|'>>') init_expression    # binaryExprInit
    | init_expression op=('&'|'|'|'^') init_expression  # binaryExprInit
    | function=ID '(' init_expression ')'               # funcExprInit
    ;

num_expression
    : '(' num_expression ')'                           # parenExprNum
    | num_literal                                      # literalExprNum
    | ID                                               # idExprNum
    | math_const                                       # mathConstExprNum
    | op=('+'|'-') num_expression                      # unaryExprNum
    | num_expression op='**' num_expression            # binaryExprNum
    | num_expression op=('*'|'/'|'%') num_expression   # binaryExprNum
    | num_expression op=('+'|'-') num_expression       # binaryExprNum
    | num_expression op=('<<'|'>>') num_expression     # binaryExprNum
    | num_expression op=('&'|'|'|'^') num_expression   # binaryExprNum
    | function=ID '(' num_expression ')'               # funcExprNum
    ;

cond_expression
    : '(' cond_expression ')'                               # parenExprCond
    | bool_literal                                          # literalExprCond
    | op='!' cond_expression                                # unaryExprCond
    | num_expression op=('<'|'>'|'<='|'>=') num_expression  # binaryExprCond
    | num_expression op=('=='|'!=') num_expression          # binaryExprCond
    | cond_expression op='&&' cond_expression               # binaryExprCond
    | cond_expression op='||' cond_expression               # binaryExprCond
    ;

num_literal
    : INT
    | FLOAT
    ;

bool_literal
    : TRUE
    | FALSE
    ;

math_const: 'pi' | 'e';

ID: [a-zA-Z_][a-zA-Z0-9_]*;
INT: [0-9]+;
FLOAT: [0-9]+'.'[0-9]* | '.'[0-9]+;

TRUE: 'True' | 'true';
FALSE: 'False' | 'false';

WS: [ \t\n\r]+ -> skip;
SL_COMMENT: '//' ~[\r\n]* -> skip;
