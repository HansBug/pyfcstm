"""
Pygments lexer implementation for FCSTM DSL syntax highlighting.

This module defines :class:`FcstmLexer`, a Pygments lexer tailored for the
FCSTM (Finite State Machine) DSL. The lexer is based on the ANTLR grammar in
``Grammar.g4`` and provides syntax highlighting support for Sphinx
documentation as well as other Pygments-based tools.

The module exposes the following public component:

* :class:`FcstmLexer` - Regex-based lexer for FCSTM DSL tokens and comments

.. note::
   The lexer is designed for use with Pygments and Sphinx's ``code-block``
   directive. It does not perform parsing or validation; it only assigns
   token types based on regular expressions.

Example::

    >>> from pygments import highlight
    >>> from pygments.formatters import HtmlFormatter
    >>> from pygments.lexers import get_lexer_by_name
    >>> code = "state MyState { enter { counter = 0; } }"
    >>> lexer = get_lexer_by_name("fcstm")
    >>> html = highlight(code, lexer, HtmlFormatter())

Usage in Sphinx documentation::

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

    This lexer provides syntax highlighting for hierarchical state machine
    definitions in the FCSTM DSL. It recognizes keywords, operators, numbers,
    strings, comments (including nested multiline comments), and identifiers.
    The implementation uses stateful regular expressions via
    :class:`pygments.lexer.RegexLexer`.

    The lexer supports:

    * Variable definitions and types (``def``, ``int``, ``float``)
    * State definitions (``state``, ``pseudo``, ``named``)
    * Transitions and lifecycle actions (``enter``, ``during``, ``exit``)
    * Aspect-oriented actions (``before``, ``after``, ``>>``)
    * Guards and effects (``if``, ``effect``)
    * Logical and arithmetic expressions
    * Events and scoped references (``::``)

    Example::

        >>> from pygments.lexers import get_lexer_by_name
        >>> lexer = get_lexer_by_name("fcstm")
        >>> list(lexer.get_tokens("state A { enter { x = 1; } }"))[:5]
        [(Token.Keyword.Declaration, 'state'), ...]

    .. note::
       The lexer includes a heuristic :meth:`analyse_text` method used by
       Pygments to guess if input text is likely FCSTM code.
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

    def analyse_text(text: str) -> float:
        """
        Analyze text to determine if it is likely FCSTM code.

        This method is used by Pygments to heuristically determine whether the
        input should be lexed by :class:`FcstmLexer`. It scans for key tokens
        and constructs a confidence score in the range ``0.0`` to ``1.0``.

        The heuristic balances recall (detecting FCSTM files) with precision
        (avoiding false positives from other languages like C++, Rust, Java).

        :param text: Text content to analyze
        :type text: str
        :return: Confidence score indicating likelihood of FCSTM syntax
        :rtype: float

        Example::

            >>> # FCSTM code - should score high (0.95)
            >>> fcstm_code = '''
            ... def int counter = 0;
            ... state MyState {
            ...     enter { counter = 0; }
            ...     [*] -> Active;
            ... }
            ... '''
            >>> FcstmLexer.analyse_text(fcstm_code)
            0.95

            >>> # C++ code - should score low (0.00)
            >>> cpp_code = '''
            ... class MyClass {
            ...     void enter() { counter = 0; }
            ...     std::vector<int> data;
            ... };
            ... '''
            >>> FcstmLexer.analyse_text(cpp_code)
            0.0

            >>> # Python code - should score low (0.00)
            >>> python_code = '''
            ... def enter():
            ...     counter = 0
            ...     state = "active"
            ... '''
            >>> FcstmLexer.analyse_text(python_code)
            0.0

            >>> # Java code - should score low (0.00)
            >>> java_code = '''
            ... public class State {
            ...     private int counter = 0;
            ...     public void enter() { counter = 0; }
            ... }
            ... '''
            >>> FcstmLexer.analyse_text(java_code)
            0.0

            >>> # Rust code - should score low (0.00)
            >>> rust_code = '''
            ... struct State {
            ...     counter: i32,
            ... }
            ... impl State {
            ...     fn enter(&mut self) { self.counter = 0; }
            ... }
            ... '''
            >>> FcstmLexer.analyse_text(rust_code)
            0.0
        """
        import re

        score = 0.0

        # Very strong FCSTM-specific indicators (unique to FCSTM)
        # Pseudo-state marker [*] is highly distinctive
        if re.search(r'\[\s*\*\s*\]', text):
            score += 0.25

        # State transition with arrow (state-like keyword followed by ->)
        if re.search(r'\bstate\s+\w+\s*\{', text):
            score += 0.25

        # Variable definition with FCSTM syntax (def int/float)
        if re.search(r'\bdef\s+(int|float)\s+\w+\s*=', text):
            score += 0.25

        # Lifecycle actions with braces (enter/exit/during followed by {)
        lifecycle_pattern = r'\b(enter|exit|during)\s*(\w+\s*)?\{'
        if re.search(lifecycle_pattern, text):
            score += 0.2

        # Strong indicators (common in FCSTM, rare in other languages)
        # Aspect operator >> followed by lifecycle keyword
        if re.search(r'>>\s*(during|enter|exit)', text):
            score += 0.15

        # Event scope operator :: (but check it's not C++ scope resolution)
        if '::' in text:
            # Reduce score if it looks like C++ namespace usage
            if not re.search(r'\b(std|boost|using|namespace|template|class)\b', text):
                score += 0.1
            else:
                score += 0.02  # Small boost even if C++-like

        # Transition arrow -> (but check it's not C++ pointer dereference)
        if '->' in text:
            # Check if it's used in state transition context
            if re.search(r'\w+\s*->\s*\w+', text):
                # Reduce confidence if C++ indicators present
                if not re.search(r'\b(class|struct|template|typename|nullptr)\b', text):
                    score += 0.1
                else:
                    score += 0.02

        # Medium indicators (present in FCSTM but also in other languages)
        # Keywords that are distinctive when combined
        fcstm_keywords = ['state', 'pseudo', 'named', 'abstract', 'ref', 'effect']
        keyword_count = sum(1 for kw in fcstm_keywords if re.search(rf'\b{kw}\b', text))
        if keyword_count >= 2:
            score += 0.1 * min(keyword_count - 1, 3)  # Cap at 0.3

        # Forced transition operator ! at start of line or after whitespace
        if re.search(r'(^|\s)!\s*\*?\s*->', text, re.MULTILINE):
            score += 0.1

        # Negative indicators (reduce score if other language patterns detected)
        # C/C++/Java class definitions
        if re.search(r'\b(class|struct|interface|enum)\s+\w+\s*[:{]', text):
            score -= 0.15

        # Python-specific patterns
        if re.search(r'\b(def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import)\b', text):
            score -= 0.2

        # Rust-specific patterns
        if re.search(r'\b(fn\s+\w+|impl\s+\w+|trait\s+\w+|pub\s+struct)\b', text):
            score -= 0.2

        # JavaScript/TypeScript patterns
        if re.search(r'\b(function\s+\w+|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=)\b', text):
            score -= 0.15

        # Java-specific patterns
        if re.search(r'\b(public|private|protected)\s+(static\s+)?(void|int|String)', text):
            score -= 0.15

        # Ensure score stays in valid range
        return max(0.0, min(score, 1.0))
