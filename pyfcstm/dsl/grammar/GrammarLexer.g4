// GrammarLexer.g4
lexer grammar GrammarLexer;

IMPORT: 'import' -> mode(IMPORT_HEADER_MODE);
DEF: 'def';
EVENT: 'event';
AS: 'as';
NAMED: 'named';

PSEUDO: 'pseudo';
STATE: 'state';
ENTER: 'enter';
EXIT: 'exit';
DURING: 'during';
BEFORE: 'before';
AFTER: 'after';
ABSTRACT: 'abstract';
REF: 'ref';
EFFECT: 'effect';
IF: 'if';
ELSE: 'else';

INT_TYPE: 'int';
FLOAT_TYPE: 'float';
PI_CONST: 'pi';
E_CONST: 'E';
TAU_CONST: 'tau';
AND_KW: 'and';
OR_KW: 'or';
NOT_KW: 'not';

INIT_MARKER: '[*]';
POW: '**';
SHIFT_RIGHT: '>>';
SHIFT_LEFT: '<<';
LE: '<=';
GE: '>=';
EQ: '==';
NE: '!=';
LOGICAL_AND: '&&';
LOGICAL_OR: '||';
DECLARE_ASSIGN: ':=';
COLONCOLON: '::';
ARROW: '->';

SEMI: ';';
COMMA: ',';
LBRACE: '{';
RBRACE: '}';
LBRACK: '[';
RBRACK: ']';
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
ASSIGN: '=';

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

MULTILINE_COMMENT: '/*' .*? '*/';
LINE_COMMENT: '//' ~[\r\n]* -> skip;
PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
WS: [ \t\n\r]+ -> skip;

mode IMPORT_HEADER_MODE;

IMPORT_HEADER_WS: [ \t\n\r]+ -> skip;
IMPORT_HEADER_MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
IMPORT_HEADER_LINE_COMMENT: '//' ~[\r\n]* -> skip;
IMPORT_HEADER_PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
IMPORT_HEADER_STRING
    : (
        '"' (~["\\\r\n] | EscapeSequence)* '"'
        | '\'' (~['\\\r\n] | EscapeSequence)* '\''
      ) -> type(STRING)
    ;
IMPORT_HEADER_AS: 'as' -> type(AS);
IMPORT_HEADER_NAMED: 'named' -> type(NAMED);
IMPORT_HEADER_ID: [a-zA-Z_][a-zA-Z0-9_]* -> type(ID);
IMPORT_HEADER_LBRACE: '{' -> type(LBRACE), mode(IMPORT_BLOCK_MODE);
IMPORT_HEADER_SEMI: ';' -> type(SEMI), mode(DEFAULT_MODE);

mode IMPORT_BLOCK_MODE;

IMPORT_BLOCK_WS: [ \t\n\r]+ -> skip;
IMPORT_BLOCK_MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
IMPORT_BLOCK_LINE_COMMENT: '//' ~[\r\n]* -> skip;
IMPORT_BLOCK_PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
IMPORT_BLOCK_DEF: 'def' -> type(DEF), mode(IMPORT_DEF_SELECTOR_MODE);
IMPORT_BLOCK_EVENT: 'event' -> type(EVENT);
IMPORT_BLOCK_NAMED: 'named' -> type(NAMED);
IMPORT_BLOCK_ARROW: '->' -> type(ARROW);
IMPORT_BLOCK_SEMI: ';' -> type(SEMI);
IMPORT_BLOCK_RBRACE: '}' -> type(RBRACE), mode(DEFAULT_MODE);
IMPORT_BLOCK_DOT: '.' -> type(DOT);
IMPORT_BLOCK_SLASH: '/' -> type(SLASH);
IMPORT_BLOCK_ID: [a-zA-Z_][a-zA-Z0-9_]* -> type(ID);
IMPORT_BLOCK_STRING
    : (
        '"' (~["\\\r\n] | EscapeSequence)* '"'
        | '\'' (~['\\\r\n] | EscapeSequence)* '\''
      ) -> type(STRING)
    ;

mode IMPORT_DEF_SELECTOR_MODE;

IMPORT_DEF_SELECTOR_WS: [ \t\n\r]+ -> skip;
IMPORT_DEF_SELECTOR_MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
IMPORT_DEF_SELECTOR_LINE_COMMENT: '//' ~[\r\n]* -> skip;
IMPORT_DEF_SELECTOR_PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
IMPORT_DEF_SELECTOR_LBRACE: '{' -> type(LBRACE);
IMPORT_DEF_SELECTOR_RBRACE: '}' -> type(RBRACE);
IMPORT_DEF_SELECTOR_COMMA: ',' -> type(COMMA);
IMPORT_DEF_SELECTOR_STAR: '*' -> type(STAR);
IMPORT_DEF_SELECTOR_PATTERN
    : [a-zA-Z_][a-zA-Z0-9_]* '*' [a-zA-Z0-9_*]*
    | '*' [a-zA-Z0-9_]+ [a-zA-Z0-9_*]*
    ;
IMPORT_DEF_SELECTOR_ID: [a-zA-Z_][a-zA-Z0-9_]* -> type(ID);
IMPORT_DEF_SELECTOR_ARROW: '->' -> type(ARROW), mode(IMPORT_DEF_TARGET_MODE);

mode IMPORT_DEF_TARGET_MODE;

IMPORT_DEF_TARGET_WS: [ \t\n\r]+ -> skip;
IMPORT_DEF_TARGET_MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
IMPORT_DEF_TARGET_LINE_COMMENT: '//' ~[\r\n]* -> skip;
IMPORT_DEF_TARGET_PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
IMPORT_DEF_TARGET_TEMPLATE
    : [a-zA-Z_][a-zA-Z0-9_]* ('$' | '*') [a-zA-Z0-9_*${}]*
    | '*' [a-zA-Z0-9_${}]+
    | '$' [0-9] [a-zA-Z0-9_*${}]*
    | '$' '{' [0-9]+ '}' [a-zA-Z0-9_*${}]*
    ;
IMPORT_DEF_TARGET_ID: [a-zA-Z_][a-zA-Z0-9_]* -> type(ID);
IMPORT_DEF_TARGET_STAR: '*' -> type(STAR);
IMPORT_DEF_TARGET_SEMI: ';' -> type(SEMI), mode(IMPORT_BLOCK_MODE);

fragment EscapeSequence
    : '\\' [btnfr"'\\]
    | '\\' ([0-3]? [0-7])? [0-7]
    | '\\' 'u' HexDigit HexDigit HexDigit HexDigit
    | '\\' 'x' HexDigit HexDigit
    ;

fragment HexDigit
    : [0-9a-fA-F]
    ;
