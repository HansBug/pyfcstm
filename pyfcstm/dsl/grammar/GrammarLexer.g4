/*
 * GrammarLexer.g4
 *
 * Overview
 * --------
 * The FCSTM grammar is intentionally split into a standalone lexer grammar and
 * a parser grammar. The import feature needs lexer modes to keep several
 * compact forms space-sensitive, and ANTLR only allows modes inside a lexer
 * grammar. This split keeps the resulting grammar cross-language and avoids
 * target-specific hooks such as @lexer::members.
 *
 * Import-related tokenization follows a staged workflow:
 *
 * 1. DEFAULT_MODE handles the regular FCSTM language and recognizes the
 *    top-level ``import`` keyword.
 * 2. ``import`` switches into IMPORT_HEADER_MODE, which lexes the source path,
 *    alias, and optional ``named`` clause until it sees either ``;`` or ``{``.
 * 3. ``{`` switches into IMPORT_BLOCK_MODE, which lexes mapping statements
 *    inside the import block.
 * 4. ``def`` inside the block switches into IMPORT_DEF_SELECTOR_MODE, where
 *    wildcard selectors such as ``sensor_*`` or ``a_*_b_*`` must stay compact
 *    and are emitted as a single token when appropriate.
 * 5. ``->`` then switches into IMPORT_DEF_TARGET_MODE, where compact target
 *    templates such as ``left_$0`` or ``pair_${1}_${2}`` are also emitted as a
 *    single token.
 *
 * Expected behavior
 * -----------------
 * Compact selector and template spellings are enforced by tokenization rather
 * than listener-side validation. If a user inserts whitespace inside one of
 * these compact forms, the lexer no longer produces the dedicated token, which
 * lets the parser fail naturally at the exact location.
 *
 * Non-goals
 * ---------
 * - No semantic validation in the lexer beyond token boundaries.
 * - No normalization or rewriting of selector/template text here.
 * - No language-specific embedded code, so the grammar remains reusable across
 *   all ANTLR targets.
 */
lexer grammar GrammarLexer;

// Core FCSTM keywords, including the import entry point that switches modes.
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

// Numeric literals and boolean literals used by the general DSL.
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

// Strings are reused in both the main DSL and the import-specific modes.
STRING
    : '"' (~["\\\r\n] | EscapeSequence)* '"'
    | '\'' (~['\\\r\n] | EscapeSequence)* '\''
    ;

MULTILINE_COMMENT: '/*' .*? '*/';
LINE_COMMENT: '//' ~[\r\n]* -> skip;
PYTHON_COMMENT: '#' ~[\r\n]* -> skip;
WS: [ \t\n\r]+ -> skip;

// Import header mode: ``import "path" as Alias named "Display" ...``
// stays structurally simple and exits either at ``;`` or when entering a block.
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

// Import block mode: accepts only import-local mapping statements plus
// punctuation. A ``def`` mapping transitions into the selector sub-mode.
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

// Import def selector mode: keeps wildcard selectors compact. Patterns are
// emitted as a dedicated token only when the wildcard expression is contiguous;
// otherwise the input falls back to normal tokens and the parser rejects it.
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

// Import def target mode: target templates follow the same compact-token
// principle as selectors. ``;`` ends the mapping and returns to the block mode.
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
