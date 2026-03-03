"""
Pygments lexer for FCSTM DSL syntax highlighting.

This lexer is based on the ANTLR grammar defined in Grammar.g4 and provides
syntax highlighting for Sphinx documentation and other Pygments-based tools.

Usage in Sphinx documentation:
    .. code-block:: fcstm

        def int counter = 0;
        state MyState {
            enter { counter = 0; }
        }
"""

from pygments.lexer import RegexLexer, words, include
from pygments.token import (
    Comment, Operator, Keyword, Name, String, Number,
    Punctuation, Whitespace
)

__all__ = ['FcstmLexer']


class FcstmLexer(RegexLexer):
    """
    Lexer for FCSTM (Finite State Machine) DSL.

    Based on the ANTLR grammar in Grammar.g4, this lexer provides syntax
    highlighting for hierarchical state machine definitions with support for:
    - Variable definitions (int, float)
    - State definitions (leaf, composite, pseudo)
    - Transitions (normal, forced, entry, exit)
    - Lifecycle actions (enter, during, exit)
    - Aspect-oriented actions (>> during before/after)
    - Guard conditions and effects
    - Expressions (arithmetic, bitwise, logical, conditional)
    - Events and references
    """

    name = 'FCSTM'
    aliases = ['fcstm', 'fcsm']
    filenames = ['*.fcstm']
    mimetypes = ['text/x-fcstm']

    tokens = {
        'root': [
            include('whitespace'),
            include('comments'),

            # Keywords - state machine structure
            (words((
                'state', 'pseudo', 'named', 'def', 'event',
            ), suffix=r'\b'), Keyword.Declaration),

            # Keywords - lifecycle actions
            (words((
                'enter', 'during', 'exit', 'before', 'after',
            ), suffix=r'\b'), Keyword.Reserved),

            # Keywords - modifiers
            (words((
                'abstract', 'ref', 'effect',
            ), suffix=r'\b'), Keyword.Namespace),

            # Keywords - types
            (words((
                'int', 'float',
            ), suffix=r'\b'), Keyword.Type),

            # Keywords - control flow
            (words((
                'if',
            ), suffix=r'\b'), Keyword.Reserved),

            # Keywords - logical operators (word form)
            (words((
                'and', 'or', 'not',
            ), suffix=r'\b'), Operator.Word),

            # Boolean literals
            (words((
                'True', 'true', 'TRUE', 'False', 'false', 'FALSE',
            ), suffix=r'\b'), Keyword.Constant),

            # Math constants
            (words((
                'pi', 'E', 'tau',
            ), suffix=r'\b'), Name.Constant),

            # Built-in functions (from UFUNC_NAME)
            (words((
                'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
                'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
                'sqrt', 'cbrt', 'exp', 'log', 'log10', 'log2', 'log1p',
                'abs', 'ceil', 'floor', 'round', 'trunc', 'sign',
            ), suffix=r'\b'), Name.Builtin),

            # Aspect operator
            (r'>>', Operator.Word),

            # Transition arrow
            (r'->', Operator),

            # Pseudo-state markers
            (r'\[\*\]', Keyword.Pseudo),

            # Event scope operators
            (r'::', Operator),
            (r':', Punctuation),

            # Absolute path marker (in chain_id)
            (r'/', Operator),

            # Numbers - must come before operators to avoid conflicts
            # Hexadecimal
            (r'0x[0-9a-fA-F]+', Number.Hex),
            # Float with exponent
            (r'[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?', Number.Float),
            (r'\.[0-9]+([eE][+-]?[0-9]+)?', Number.Float),
            (r'[0-9]+[eE][+-]?[0-9]+', Number.Float),
            # Integer
            (r'[0-9]+', Number.Integer),

            # Operators - multi-character operators must come before single-character ones
            # Power operator (must come before *)
            (r'\*\*', Operator),
            # Bit shift operators (must come before < and >)
            (r'<<', Operator),
            # Comparison operators (must come before single < and >)
            (r'<=|>=|==|!=', Operator),
            # Logical operators (must come before single !)
            (r'&&|\|\|', Operator),

            # Forced transition operator (after != and && to avoid conflicts)
            (r'!', Operator.Word),

            # Single-character operators
            (r'[+\-*/%&|^~<>]', Operator),

            # Operators - assignment and ternary
            (r'=|\?', Operator),

            # Punctuation
            (r'[{}()\[\];,.]', Punctuation),

            # Strings
            (r'"([^"\\]|\\[btnfr"\'\\]|\\[0-7]{1,3}|\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2})*"', String.Double),
            (r"'([^'\\]|\\[btnfr\"'\\]|\\[0-7]{1,3}|\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2})*'", String.Single),

            # Identifiers (must come after keywords)
            (r'[a-zA-Z_][a-zA-Z0-9_]*', Name),
        ],

        'whitespace': [
            (r'\s+', Whitespace),
        ],

        'comments': [
            # Multiline comments (not skipped - used for documentation)
            (r'/\*', Comment.Multiline, 'comment-multiline'),
            # Single-line comments
            (r'//[^\r\n]*', Comment.Single),
            # Python-style comments
            (r'#[^\r\n]*', Comment.Single),
        ],

        'comment-multiline': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),  # Nested comments
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
    }

    def analyse_text(text):
        """
        Analyze text to determine if it's likely FCSTM code.

        Returns a score between 0.0 and 1.0 indicating confidence.
        """
        score = 0.0

        # Strong indicators
        if 'state ' in text:
            score += 0.3
        if '->' in text:
            score += 0.2
        if 'def int' in text or 'def float' in text:
            score += 0.2

        # Medium indicators
        if '::' in text:
            score += 0.1
        if 'enter {' in text or 'exit {' in text or 'during {' in text:
            score += 0.1
        if '[*]' in text:
            score += 0.1

        return min(score, 1.0)
