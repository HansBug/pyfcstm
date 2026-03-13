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

import re

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

    _ANALYSIS_MASK_PATTERNS = (
        re.compile(r'(?s)R"(?P<delim>[^ ()\\\t\r\n]{0,16})\((.*?)\)(?P=delim)"'),
        re.compile(r'(?is)(?<!\w)(?:[rubf]{0,3})"""(.*?)"""'),
        re.compile(r"(?is)(?<!\w)(?:[rubf]{0,3})'''(.*?)'''"),
        re.compile(r'(?s)\br(?P<hashes>#{0,16})"(?!")(.*?)"(?P=hashes)'),
        re.compile(r'(?ms)<<[-~]?(?P<quote>[\'"]?)(?P<label>[A-Za-z_]\w*)(?P=quote)\n.*?^\s*(?P=label)\s*$'),
        re.compile(r'(?s)%(?:q|Q)(?P<delim>[^A-Za-z0-9\s])(.*?)(?P=delim)'),
        re.compile(r'(?s)`(?:\\.|[^`])*`'),
        re.compile(r'(?s)/\*.*?\*/'),
        re.compile(r'"(?:\\.|[^"\\\n])*"'),
        re.compile(r"'(?:\\.|[^'\\\n])*'"),
    )

    _ANALYSIS_NEGATIVE_PATTERNS = (
        (re.compile(r'(?m)^\s*@startuml\b|^\s*@enduml\b|^\s*allowmixing\b'), 0.45),
        (re.compile(r'(?m)^\s*(?:participant|actor|boundary|control|entity|database|annotation|object)\b'), 0.25),
        (re.compile(r'(?m)^\s*(?:abstract\s+class|class)\b'), 0.20),
        (re.compile(r'(?m)^\s*package\s+main\b|^\s*func\s+main\s*\(|^\s*package\b|^\s*func\b|^\s*var\b|^\s*type\b'), 0.25),
        (re.compile(r'(?m)^\s*fn\s+\w+\s*\(|^\s*impl\b|^\s*trait\b|^\s*pub\b'), 0.30),
        (re.compile(r'(?m)^\s*(?:public|private|protected)\b|^\s*package\s+[A-Za-z_][\w.]*\s*;|\bjava\.util\.function\b'), 0.25),
        (re.compile(r'(?m)^\s*(?:export\b|interface\b|namespace\b|type\b)|\bglobalThis\b|\bString\.raw\b|\bRecord\s*<|=>'), 0.25),
        (re.compile(r'(?m)^\s*def[^\S\n]+\w+\s*\(|^\s*from\s+\w+\s+import\b|^\s*import\s+\w+\b'), 0.25),
        (re.compile(r'(?m)^\s*#include\b|\bstd::\b|\btemplate\s*<|\busing\s+namespace\b|^\s*using\s+[A-Za-z_]\w*\s*=|\btypedef\b|^\s*struct\b|\bnullptr\b'), 0.30),
        (re.compile(r'(?m)\bmacro_rules!'), 0.35),
        (re.compile(r'(?m)\b[A-Za-z_]\w*!\s*[\(\[{]'), 0.35),
        (re.compile(r'(?m)^(?=.*\bpseudo\b)(?=.*\bnamed\b)(?=.*\babstract\b)(?=.*\bref\b)(?=.*\beffect\b).*(?:=|,|:).*$'), 0.25),
        (re.compile(r'(?m)^\s*(?:module\b|BEGIN\s*\{|end\b)|->\s*do\b'), 0.20),
        (re.compile(r'(?m)^\s*(?:const|let|var|function|try|finally)\b'), 0.20),
        (re.compile(r'(?m)^\s*(?:if|for|while|try|except|finally|class)\b.*:\s*$'), 0.15),
    )

    _ANALYSIS_STATE_BLOCK_PATTERN = re.compile(
        r'(?m)^\s*(?:pseudo[^\S\n]+)?state[^\S\n]+[A-Za-z_][A-Za-z0-9_]*\b'
        r'(?:[^\n;{]*)?(?:\{|\n[^\S\n]*\{)'
    )
    _ANALYSIS_STATE_DECL_PATTERN = re.compile(
        r'(?m)^\s*(?:pseudo[^\S\n]+)?state[^\S\n]+[A-Za-z_][A-Za-z0-9_]*\b'
        r'(?:[^\n{;]*)?;'
    )
    _ANALYSIS_EVENT_DECL_PATTERN = re.compile(
        r'(?m)^\s*event[^\S\n]+[A-Za-z_][A-Za-z0-9_]*\b(?:[^\n;{]*)?;'
    )
    _ANALYSIS_DEF_DECL_PATTERN = re.compile(
        r'(?m)^\s*def[^\S\n]+(?:int|float)[^\S\n]+[A-Za-z_][A-Za-z0-9_]*\b[^\n;]*;'
    )
    _ANALYSIS_LIFECYCLE_BLOCK_PATTERN = re.compile(
        r'(?m)^\s*(?:enter|during|exit)\b(?:[^\S\n]+[^\n{;]+)*\s*(?:\{|\n[^\S\n]*\{)'
    )
    _ANALYSIS_LIFECYCLE_DECL_PATTERN = re.compile(
        r'(?m)^\s*(?:enter|during|exit)\b(?:[^\S\n]+[^\n;{]+)+\s*;'
    )
    _ANALYSIS_LIFECYCLE_BARE_PATTERN = re.compile(
        r'(?m)^\s*(?:enter|during|exit)\s*;'
    )
    _ANALYSIS_ASPECT_PATTERN = re.compile(
        r'(?m)^\s*>>\s*(?:during|enter|exit)\b(?:[^\S\n]+[^\n{;]+)*\s*(?:\{|;)'
    )
    _ANALYSIS_TRANSITION_PATTERN = re.compile(
        r'(?m)^\s*(?P<source>!\s*\*?|!\s*[A-Za-z_][\w./]*|\[\s*\*\s*\]|[A-Za-z_][\w./]*)\s*->\s*'
        r'(?P<target>\[\s*\*\s*\]|[A-Za-z_][\w./]*)\b(?P<tail>[^\n;]*);\s*$'
    )
    _ANALYSIS_KEYWORDS = ('pseudo', 'named', 'abstract', 'ref', 'effect')

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

    @staticmethod
    def _mask_analysis_text(fragment: str) -> str:
        """Replace non-newline characters with spaces to preserve line layout."""
        return re.sub(r'[^\n]', ' ', fragment)

    @classmethod
    def _mask_disabled_preprocessor_blocks(cls, text: str) -> str:
        """Hide ``#if 0 ... #endif`` regions which are not active code."""
        lines = text.splitlines(keepends=True)
        masked = []
        disabled_depth = 0

        for line in lines:
            stripped = line.lstrip()

            if disabled_depth:
                masked.append(cls._mask_analysis_text(line))
                if re.match(r'#if(?:n?def)?\b', stripped):
                    disabled_depth += 1
                elif re.match(r'#endif\b', stripped):
                    disabled_depth -= 1
                continue

            if re.match(r'#if\s+0\b', stripped):
                disabled_depth = 1
                masked.append(cls._mask_analysis_text(line))
            else:
                masked.append(line)

        return ''.join(masked)

    @classmethod
    def _mask_plantuml_blocks(cls, text: str) -> str:
        """Hide PlantUML note and legend payload blocks."""
        lines = text.splitlines(keepends=True)
        masked = []
        block_kind = None

        for line in lines:
            stripped = line.strip().lower()

            if block_kind is not None:
                masked.append(cls._mask_analysis_text(line))
                if (block_kind == 'note' and stripped == 'end note') or (
                    block_kind == 'legend' and stripped == 'endlegend'
                ):
                    block_kind = None
                continue

            if re.match(r'(?i)^note\b', stripped):
                block_kind = 'note'
                masked.append(cls._mask_analysis_text(line))
                continue

            if re.match(r'(?i)^legend\b', stripped):
                block_kind = 'legend'
                masked.append(cls._mask_analysis_text(line))
                continue

            masked.append(line)

        return ''.join(masked)

    @classmethod
    def _strip_non_semantic_regions(cls, text: str) -> str:
        """
        Remove comment/string-like bait so scoring only sees live code structure.
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = cls._mask_disabled_preprocessor_blocks(text)
        text = cls._mask_plantuml_blocks(text)
        text = re.sub(
            r'(?ms)^[ \t]*=begin\b.*?^[ \t]*=end\b[^\n]*(?:\n|$)',
            lambda match: cls._mask_analysis_text(match.group(0)),
            text,
        )

        for pattern in cls._ANALYSIS_MASK_PATTERNS:
            text = pattern.sub(lambda match: cls._mask_analysis_text(match.group(0)), text)

        text = re.sub(r'(?m)//[^\n]*', lambda match: cls._mask_analysis_text(match.group(0)), text)
        text = re.sub(r'(?m)#[^\n]*', lambda match: cls._mask_analysis_text(match.group(0)), text)
        text = re.sub(r"(?m)^[ \t]*'[^\n]*", lambda match: cls._mask_analysis_text(match.group(0)), text)
        return text

    @classmethod
    def _analysis_has_transition(cls, text: str, *, rich: bool) -> bool:
        """Detect FCSTM-style transition statements and classify weak vs rich forms."""
        for match in cls._ANALYSIS_TRANSITION_PATTERN.finditer(text):
            source = re.sub(r'\s+', '', match.group('source'))
            target = re.sub(r'\s+', '', match.group('target'))
            tail = match.group('tail')
            is_rich = (
                '[*]' in source or '[*]' in target or source.startswith('!')
                or '::' in tail or ':' in tail or re.search(r'\beffect\b', tail) is not None
            )
            if is_rich == rich:
                return True

        return False

    @staticmethod
    def _analysis_is_valid_state_machine(text: str) -> bool:
        """
        Confirm whether the full input can be parsed and loaded as FCSTM.

        This parser-backed check covers valid FCSTM files that use aggressive
        whitespace/comment splitting which the regex heuristic alone may score
        too low. Non-FCSTM text falls back to the lightweight heuristic path.
        """
        if re.search(r'\bstate\b', text) is None:
            return False

        try:
            from ..dsl import parse_with_grammar_entry
            from ..model import parse_dsl_node_to_state_machine

            ast = parse_with_grammar_entry(text, 'state_machine_dsl')
            parse_dsl_node_to_state_machine(ast)
        except Exception:
            return False
        else:
            return True

    def analyse_text(text: str) -> float:
        """
        Analyze text to determine if it is likely FCSTM code.

        This method is used by Pygments to heuristically determine whether the
        input should be lexed by :class:`FcstmLexer`. It scans for key tokens
        and constructs a confidence score in the range ``0.0`` to ``1.0``.

        The heuristic balances recall (detecting FCSTM files) with precision
        (avoiding false positives from other languages like C++, Rust, Java).
        It first attempts a real FCSTM parse/load round-trip for strong
        confirmation, then falls back to regex heuristics for incomplete
        snippets that are still useful to highlight.

        :param text: Text content to analyze
        :type text: str
        :return: Confidence score indicating likelihood of FCSTM syntax
        :rtype: float

        Example::

            >>> # FCSTM code - should score high
            >>> fcstm_code = '''
            ... def int counter = 0;
            ... state MyState {
            ...     enter { counter = 0; }
            ...     [*] -> Active;
            ... }
            ... '''
            >>> FcstmLexer.analyse_text(fcstm_code)
            1.0

            >>> # C++ code - should score low
            >>> cpp_code = '''
            ... class MyClass {
            ...     void enter() { counter = 0; }
            ...     std::vector<int> data;
            ... };
            ... '''
            >>> FcstmLexer.analyse_text(cpp_code)
            0.0

            >>> # Python code - should score low
            >>> python_code = '''
            ... def enter():
            ...     counter = 0
            ...     state = "active"
            ... '''
            >>> FcstmLexer.analyse_text(python_code)
            0.0

            >>> # Java code - should score low
            >>> java_code = '''
            ... public class State {
            ...     private int counter = 0;
            ...     public void enter() { counter = 0; }
            ... }
            ... '''
            >>> FcstmLexer.analyse_text(java_code)
            0.0

            >>> # Rust code - should score low
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
        if FcstmLexer._analysis_is_valid_state_machine(text):
            return 1.0

        analysis_text = FcstmLexer._strip_non_semantic_regions(text)
        score = 0.0

        has_state_block = FcstmLexer._ANALYSIS_STATE_BLOCK_PATTERN.search(analysis_text) is not None
        has_state_decl = FcstmLexer._ANALYSIS_STATE_DECL_PATTERN.search(analysis_text) is not None
        has_event_decl = FcstmLexer._ANALYSIS_EVENT_DECL_PATTERN.search(analysis_text) is not None
        has_def_decl = FcstmLexer._ANALYSIS_DEF_DECL_PATTERN.search(analysis_text) is not None
        has_lifecycle_block = FcstmLexer._ANALYSIS_LIFECYCLE_BLOCK_PATTERN.search(analysis_text) is not None
        has_lifecycle_decl = FcstmLexer._ANALYSIS_LIFECYCLE_DECL_PATTERN.search(analysis_text) is not None
        has_lifecycle_bare = FcstmLexer._ANALYSIS_LIFECYCLE_BARE_PATTERN.search(analysis_text) is not None
        has_aspect = FcstmLexer._ANALYSIS_ASPECT_PATTERN.search(analysis_text) is not None
        has_rich_transition = FcstmLexer._analysis_has_transition(analysis_text, rich=True)
        has_plain_transition = FcstmLexer._analysis_has_transition(analysis_text, rich=False)

        # FCSTM structural signals. These are scored only after comments/strings
        # and similar bait regions are masked out.
        if has_state_block:
            score += 0.40
        elif has_state_decl:
            score += 0.08

        if has_event_decl:
            score += 0.06

        if has_def_decl:
            score += 0.14

        if has_lifecycle_block or has_lifecycle_decl:
            score += 0.15
        elif has_lifecycle_bare:
            score += 0.04

        if has_aspect:
            score += 0.15

        if has_rich_transition:
            score += 0.30

        if has_plain_transition:
            score += 0.08

        keyword_count = sum(
            1
            for keyword in FcstmLexer._ANALYSIS_KEYWORDS
            if re.search(rf'\b{keyword}\b', analysis_text)
        )
        if keyword_count >= 2 and any((
            has_state_block,
            has_state_decl,
            has_event_decl,
            has_def_decl,
            has_lifecycle_block,
            has_lifecycle_decl,
            has_lifecycle_bare,
            has_aspect,
            has_rich_transition,
            has_plain_transition,
        )):
            score += 0.02 * min(keyword_count - 1, 2)

        for pattern, penalty in FcstmLexer._ANALYSIS_NEGATIVE_PATTERNS:
            if pattern.search(analysis_text):
                score -= penalty

        # Ensure score stays in valid range
        return max(0.0, min(score, 1.0))
