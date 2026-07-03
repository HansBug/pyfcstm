/*
 * BmcQueryLexer.g4
 *
 * Lexer grammar for FCSTM BMC Query (``.fbmcq``) files.
 *
 * This grammar is intentionally independent from the main FCSTM DSL grammar.
 * It repeats the FCSTM-compatible expression token surface needed by query
 * files and adds query-only keywords for bounded-model-checking predicates.
 */
lexer grammar BmcQueryLexer;

INIT: 'init';
COLD: 'cold';
TERMINATED: 'terminated';
STATE: 'state';
WHERE: 'where';
ASSUME: 'assume';
ALWAYS: 'always';
AT: 'at';
EVENT: 'event';
EVENTS: 'events';
CARDINALITY: 'cardinality';
ANY: 'any';
AT_MOST_ONE: 'at_most_one';
CHECK: 'check';
REACH: 'reach';
FORBID: 'forbid';
INVARIANT: 'invariant';
MUST_REACH: 'must_reach';
EXISTS_ALWAYS: 'exists_always';
RESPONSE: 'response';
COVER: 'cover';
TRIGGER: 'trigger';
WITHIN: 'within';
VAR: 'var';
CYCLE: 'cycle';
ACTIVE: 'active';
CASE: 'case';
CALLED: 'called';
CURRENT: 'current';

PI_CONST: 'pi';
E_CONST: 'E';
TAU_CONST: 'tau';
AND_KW: 'and';
OR_KW: 'or';
NOT_KW: 'not';
IMPLIES_KW: 'implies';
IFF_KW: 'iff';
XOR_KW: 'xor';

POW: '**';
SHIFT_RIGHT: '>>';
SHIFT_LEFT: '<<';
LE: '<=';
GE: '>=';
EQ: '==';
NE: '!=';
LOGICAL_AND: '&&';
LOGICAL_OR: '||';
IMPLIES: '=>';
ARROW: '->';
RANGE_INT: [0-9]+ '..' [ \t]* [0-9]+;
DOTDOT: '..';

SEMI: ';';
COMMA: ',';
LBRACE: '{';
RBRACE: '}';
LPAREN: '(';
RPAREN: ')';
QUESTION: '?';
COLON: ':';
DOT: '.';
SLASH: '/';
STAR: '*';
BANG: '!';
PLUS: '+';
MINUS: '-';
PERCENT: '%';
AMP: '&';
CARET: '^';
PIPE: '|';
LT: '<';
GT: '>';

FLOAT
    : [0-9]+ '.' [0-9]* ([eE][+-]?[0-9]+)?
    | '.' [0-9]+ ([eE][+-]?[0-9]+)?
    | [0-9]+ [eE][+-]?[0-9]+
    ;

HEX_INT: '0x' HexDigit+;
INT: [0-9]+;

TRUE: 'True' | 'true' | 'TRUE';
FALSE: 'False' | 'false' | 'FALSE';

UFUNC_NAME
    : 'sin' | 'cos' | 'tan' | 'asin' | 'acos' | 'atan'
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

MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
LINE_COMMENT: '//' ~[\r\n]* -> skip;
PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
WS: [ \t\n\r]+ -> skip;

fragment EscapeSequence
    : '\\' [btnfr"'\\]
    | '\\' ([0-3]? [0-7])? [0-7]
    | '\\' 'u' HexDigit HexDigit HexDigit HexDigit
    | '\\' 'x' HexDigit HexDigit
    ;

fragment HexDigit
    : [0-9a-fA-F]
    ;
