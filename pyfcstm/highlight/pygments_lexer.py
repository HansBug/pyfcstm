"""
Pygments lexer implementation for FCSTM DSL syntax highlighting.

This module defines :class:`FcstmLexer`, a Pygments lexer tailored for the
FCSTM (Finite State Machine) DSL. The lexer mirrors the FCSTM surface syntax
defined by ``Grammar.g4`` and provides highlighting support for Sphinx
documentation as well as other Pygments-based tools.

The module exposes the following public component:

* :class:`FcstmLexer` - Regex-based lexer for FCSTM DSL tokens and comments

.. note::
   The lexer is designed for use with Pygments and Sphinx's ``code-block``
   directive. It does not parse or validate DSL input. In particular,
   :meth:`FcstmLexer.analyse_text` must remain a pure string/token heuristic
   and must not call the FCSTM parser/model loader, so malformed but still
   recognizably FCSTM snippets can continue to be detected.

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
from typing import List, Tuple

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
        (re.compile(r'(?m)^\s*@startuml\b|^\s*@enduml\b|^\s*allowmixing\s*$'), 0.45),
        (
            re.compile(
                r'(?m)^\s*(?:participant|actor|boundary|control|entity|database|annotation|object)\s+'
                r'(?:\"[^\"]+\"|[A-Za-z_][\w.]*)(?:\s+as\s+[A-Za-z_]\w*)?(?:\s*\{|$)'
            ),
            0.25,
        ),
        (re.compile(r'(?m)^\s*(?:abstract\s+class|class)\s+[A-Za-z_][\w.]*\b(?!\s*(?:=|->))'), 0.20),
        (
            re.compile(
                r'(?m)^\s*package\s+[A-Za-z_]\w*\b|^\s*func\s+\w+\s*\(|^\s*var\s+\w+\b|^\s*type\s+\w+\b'
            ),
            0.25,
        ),
        (
            re.compile(
                r'(?m)^\s*fn\s+\w+\s*\(|^\s*impl(?:\s*<[^>]+>)?\s+\w|^\s*trait\s+\w|'
                r'^\s*pub(?:\s*\([^)]*\))?\s+(?:fn|struct|enum|mod|trait|type|use|const|static|impl)\b'
            ),
            0.30,
        ),
        (
            re.compile(
                r'(?m)^\s*(?:public|private|protected)\s+(?:class|interface|enum|record|static|final|abstract|'
                r'synchronized|void|[A-Za-z_]\w*(?:<[^>]+>)?)\b|^\s*package\s+[A-Za-z_][\w.]*\s*;|(?<!/)\bjava\.util\.function\b'
            ),
            0.25,
        ),
        (
            re.compile(
                r'(?m)^\s*export\s+(?:default\b|const\b|let\b|var\b|function\b|class\b|interface\b|type\b|namespace\b|\{)|'
                r'^\s*interface\s+\w|^\s*namespace\s+\w|^\s*type\s+\w+\s*=|(?<!/)\bglobalThis\s*(?:\.|=)|'
                r'(?<!/)\bString\.raw\b|\bRecord\s*<|=>'
            ),
            0.25,
        ),
        (re.compile(r'(?m)^\s*def[^\S\n]+\w+\s*\(|^\s*from\s+\w+\s+import\b|^\s*import\s+\w+\b'), 0.25),
        (
            re.compile(
                r'(?m)^\s*#include\b|\bstd::\w|\btemplate\s*<|^\s*using\s+namespace\b|^\s*using\s+[A-Za-z_]\w*\s*=|'
                r'^\s*typedef\b(?!\s*=)|^\s*struct\s+[A-Za-z_]\w*|\bnullptr\b(?!\s*=)'
            ),
            0.30,
        ),
        (re.compile(r'(?m)\bmacro_rules!'), 0.35),
        (re.compile(r'(?m)\b[A-Za-z_]\w*!\s*[\(\[{]'), 0.35),
        (
            re.compile(
                r'(?m)^(?=.*\bpseudo\b)(?=.*\bnamed\b)(?=.*\babstract\b)(?=.*\bref\b)(?=.*\beffect\b)'
                r'(?!.*\bstate\b)(?!.*->).*(?:=|,|:).*$'
            ),
            0.25,
        ),
        (
            re.compile(
                r'(?m)^\s*pseudo\s*=.*\bnamed\s*=.*\babstract\s*=.*\bref\s*=.*\beffect\s*=.*$'
            ),
            0.30,
        ),
        (re.compile(r'(?m)^\s*module\s+[A-Za-z_]\w*\b|^\s*BEGIN\s*\{|^\s*end\s*$|->\s*do\b(?!\s*[;:])'), 0.20),
        (
            re.compile(
                r'(?m)^\s*const\s+\w+\s*=|^\s*let\s+\w+\s*=|^\s*var\s+\w+\s*=|^\s*function\s+\w+\s*\(|'
                r'^\s*try\b(?:\s*\{|$)|^\s*finally\b(?!.*->)(?:\s*:|\s*\{|$)'
            ),
            0.20,
        ),
        (re.compile(r'(?m)^\s*(?:if|for|while|try|except|finally|class)\b(?!.*->).*:\s*$'), 0.15),
    )

    _ANALYSIS_TOKEN_PATTERN = re.compile(
        r'\[\s*\*\s*\]|->|::|>>|<=|>=|==|!=|&&|\|\||\*\*|'
        r'[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\.[0-9]+)?|[{}()\[\];,./:+\-*!=?<>]'
    )
    _ANALYSIS_IDENTIFIER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
    _ANALYSIS_RESERVED_WORDS = frozenset((
        'abstract', 'after', 'before', 'def', 'during', 'effect', 'enter',
        'else', 'event', 'exit', 'float', 'if', 'int', 'named', 'pseudo', 'ref',
        'state',
    ))
    _ANALYSIS_LIFECYCLE_KEYWORDS = frozenset(('enter', 'during', 'exit'))
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
                'if', 'else',
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
    def _analysis_tokenize(cls, text: str) -> List[str]:
        """Tokenize live code into a lightweight FCSTM-oriented token stream."""
        return cls._ANALYSIS_TOKEN_PATTERN.findall(text)

    @classmethod
    def _analysis_is_identifier(cls, token: str) -> bool:
        """Return whether token is a non-keyword identifier-like symbol."""
        return bool(cls._ANALYSIS_IDENTIFIER_PATTERN.match(token)) and token not in cls._ANALYSIS_RESERVED_WORDS

    @classmethod
    def _analysis_collect_state_spans(cls, tokens: List[str]) -> List[Tuple[int, int, bool, bool]]:
        """
        Collect spans for ``state`` declarations/blocks in the token stream.

        The scan is intentionally tolerant to missing alias string literals,
        because string payload is masked out during bait removal.
        """
        spans = []
        index = 0

        while index < len(tokens):
            start = index
            if tokens[index] == 'pseudo':
                if index + 1 >= len(tokens) or tokens[index + 1] != 'state':
                    index += 1
                    continue
                state_index = index + 1
            else:
                state_index = index

            if (
                tokens[state_index] != 'state'
                or state_index + 1 >= len(tokens)
                or not cls._analysis_is_identifier(tokens[state_index + 1])
            ):
                index += 1
                continue

            tail_index = state_index + 2
            if tail_index < len(tokens) and tokens[tail_index] == 'named':
                tail_index += 1
                if tail_index < len(tokens) and tokens[tail_index] not in {';', '{', '}'}:
                    tail_index += 1

            if tail_index < len(tokens) and tokens[tail_index] in {';', '{'}:
                spans.append((start, tail_index, tokens[tail_index] == '{', tokens[tail_index] == ';'))
                index = tail_index + 1
            else:
                index += 1

        return spans

    @classmethod
    def _analysis_collect_event_spans(cls, tokens: List[str]) -> List[Tuple[int, int]]:
        """Collect spans for ``event`` declarations."""
        spans = []

        for index, token in enumerate(tokens[:-2]):
            if token != 'event' or not cls._analysis_is_identifier(tokens[index + 1]):
                continue

            tail_index = index + 2
            if tail_index < len(tokens) and tokens[tail_index] == 'named':
                tail_index += 1
                if tail_index < len(tokens) and tokens[tail_index] != ';':
                    tail_index += 1

            if tail_index < len(tokens) and tokens[tail_index] == ';':
                spans.append((index, tail_index))

        return spans

    @classmethod
    def _analysis_collect_def_spans(cls, tokens: List[str]) -> List[Tuple[int, int]]:
        """Collect spans for ``def int/float`` declarations."""
        spans = []

        for index, token in enumerate(tokens[:-2]):
            if (
                token == 'def'
                and index + 2 < len(tokens)
                and tokens[index + 1] in {'int', 'float'}
                and cls._analysis_is_identifier(tokens[index + 2])
            ):
                tail_index = index + 3
                while tail_index < len(tokens) and tokens[tail_index] != ';' and tail_index - index <= 24:
                    tail_index += 1

                if tail_index < len(tokens) and tokens[tail_index] == ';':
                    spans.append((index, tail_index))

        return spans

    @classmethod
    def _analysis_collect_lifecycle_spans(
        cls,
        tokens: List[str],
    ) -> List[Tuple[int, int, bool, bool]]:
        """Collect spans for ``enter``/``during``/``exit`` handler-like constructs."""
        spans = []

        for index, token in enumerate(tokens):
            if token not in cls._ANALYSIS_LIFECYCLE_KEYWORDS:
                continue
            if index > 0 and tokens[index - 1] == '>>':
                continue

            tail_index = index + 1
            if tail_index < len(tokens) and tokens[tail_index] in {'before', 'after'}:
                tail_index += 1

            if tail_index < len(tokens) and tokens[tail_index] == 'abstract':
                tail_index += 1

            if tail_index < len(tokens) and cls._analysis_is_identifier(tokens[tail_index]):
                tail_index += 1
                if tail_index < len(tokens) and tokens[tail_index] == 'ref':
                    tail_index += 1
                    while (
                        tail_index < len(tokens)
                        and tokens[tail_index] not in {';', '{', '}'}
                        and tail_index - index <= 16
                    ):
                        tail_index += 1

            if tail_index < len(tokens) and tokens[tail_index] in {';', '{', '}'} and tail_index - index <= 16:
                spans.append((index, tail_index, tokens[tail_index] == '{', tail_index == index + 1))

        return spans

    @classmethod
    def _analysis_collect_aspect_spans(cls, tokens: List[str]) -> List[Tuple[int, int, bool]]:
        """Collect spans for ``>>`` aspect handlers."""
        spans = []

        for index, token in enumerate(tokens[:-1]):
            if token != '>>' or tokens[index + 1] not in cls._ANALYSIS_LIFECYCLE_KEYWORDS:
                continue

            tail_index = index + 2
            if tail_index < len(tokens) and tokens[tail_index] in {'before', 'after'}:
                tail_index += 1

            if tail_index < len(tokens) and tokens[tail_index] == 'abstract':
                tail_index += 1

            if tail_index < len(tokens) and cls._analysis_is_identifier(tokens[tail_index]):
                tail_index += 1
                if tail_index < len(tokens) and tokens[tail_index] == 'ref':
                    tail_index += 1
                    while (
                        tail_index < len(tokens)
                        and tokens[tail_index] not in {';', '{', '}'}
                        and tail_index - index <= 18
                    ):
                        tail_index += 1

            if tail_index < len(tokens) and tokens[tail_index] in {';', '{', '}'} and tail_index - index <= 18:
                spans.append((index, tail_index, tokens[tail_index] == '{'))

        return spans

    @classmethod
    def _analysis_collect_transition_spans(cls, tokens: List[str]) -> List[Tuple[int, int, bool]]:
        """
        Collect spans for FCSTM-like transitions.

        This is intentionally shallow: it only looks for plausible source/target
        shapes and a nearby statement terminator or effect block end.
        """
        spans = []

        for index, token in enumerate(tokens):
            if token != '->' or index == 0 or index + 1 >= len(tokens):
                continue

            if tokens[index - 1] == '*' and index >= 2 and tokens[index - 2] == '!':
                start = index - 2
                forced = True
            elif cls._analysis_is_identifier(tokens[index - 1]) and index >= 2 and tokens[index - 2] == '!':
                start = index - 2
                forced = True
            elif tokens[index - 1] == '[*]':
                start = index - 1
                forced = False
            elif cls._analysis_is_identifier(tokens[index - 1]):
                start = index - 1
                forced = False
            else:
                continue

            if tokens[index + 1] not in {'[*]'} and not cls._analysis_is_identifier(tokens[index + 1]):
                continue

            rich = forced or tokens[index - 1] == '[*]' or tokens[index + 1] == '[*]'
            saw_effect_block = False
            tail_index = index + 2

            while tail_index < len(tokens) and tail_index - start <= 32:
                if tokens[tail_index] in {'::', ':', 'effect'}:
                    rich = True
                    if tokens[tail_index] == 'effect' and tail_index + 1 < len(tokens) and tokens[tail_index + 1] == '{':
                        saw_effect_block = True

                if tokens[tail_index] == ';':
                    spans.append((start, tail_index, rich))
                    break

                if tokens[tail_index] == '}' and saw_effect_block:
                    spans.append((start, tail_index, rich))
                    break

                tail_index += 1

        return spans

    @classmethod
    def _analysis_has_leading_construct(cls, tokens: List[str]) -> bool:
        """Check whether the file starts like a top-level FCSTM declaration."""
        if len(tokens) >= 3 and tokens[0] == 'state' and cls._analysis_is_identifier(tokens[1]):
            return tokens[2] in {';', '{'} or (
                len(tokens) >= 4 and tokens[2] == 'named' and tokens[3] in {';', '{'}
            )

        if len(tokens) >= 4 and tokens[0] == 'pseudo' and tokens[1] == 'state' and cls._analysis_is_identifier(tokens[2]):
            return tokens[3] in {';', '{'} or (
                len(tokens) >= 5 and tokens[3] == 'named' and tokens[4] in {';', '{'}
            )

        if len(tokens) >= 4 and tokens[0] == 'def' and tokens[1] in {'int', 'float'} and cls._analysis_is_identifier(tokens[2]):
            return ';' in tokens[3:]

        if len(tokens) >= 3 and tokens[0] == 'event' and cls._analysis_is_identifier(tokens[1]):
            return tokens[2] == ';' or (len(tokens) >= 4 and tokens[2] == 'named' and tokens[3] == ';')

        return False

    @staticmethod
    def _analysis_span_density(token_count: int, spans: List[Tuple[int, int, object]]) -> float:
        """Compute coverage ratio of recognised FCSTM spans over the token stream."""
        covered = set()
        for span in spans:
            start, end = span[:2]
            covered.update(range(start, end + 1))

        return len(covered) / max(token_count, 1)

    def analyse_text(text: str) -> float:
        """
        Analyze text to determine if it is likely FCSTM code.

        This method is used by Pygments to heuristically determine whether the
        input should be lexed by :class:`FcstmLexer`. It scans for key tokens
        and constructs a confidence score in the range ``0.0`` to ``1.0``.

        The heuristic balances recall (detecting FCSTM files) with precision
        (avoiding false positives from other languages like C++, Rust, Java).
        It deliberately uses only string and token-stream operations. This
        keeps detection tolerant of incomplete or slightly broken FCSTM input
        without depending on a successful DSL parse/load round-trip.

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
        analysis_text = FcstmLexer._strip_non_semantic_regions(text)
        tokens = FcstmLexer._analysis_tokenize(analysis_text)
        if not tokens:
            return 0.0

        state_spans = FcstmLexer._analysis_collect_state_spans(tokens)
        event_spans = FcstmLexer._analysis_collect_event_spans(tokens)
        def_spans = FcstmLexer._analysis_collect_def_spans(tokens)
        lifecycle_spans = FcstmLexer._analysis_collect_lifecycle_spans(tokens)
        aspect_spans = FcstmLexer._analysis_collect_aspect_spans(tokens)
        transition_spans = FcstmLexer._analysis_collect_transition_spans(tokens)

        state_blocks = sum(1 for _, _, is_block, _ in state_spans if is_block)
        state_decls = sum(1 for _, _, _, is_decl in state_spans if is_decl)
        state_named = sum(
            1 for start, _, _, _ in state_spans
            if 'named' in tokens[start:min(len(tokens), start + 5)]
        )
        event_named = sum(
            1 for start, _ in event_spans
            if 'named' in tokens[start:min(len(tokens), start + 5)]
        )
        lifecycle_blocks = sum(1 for _, _, is_block, _ in lifecycle_spans if is_block)
        lifecycle_bare = sum(1 for _, _, _, is_bare in lifecycle_spans if is_bare)
        lifecycle_abstract = sum(
            1 for start, _, _, _ in lifecycle_spans
            if 'abstract' in tokens[start:min(len(tokens), start + 6)]
        )
        lifecycle_ref = sum(
            1 for start, _, _, _ in lifecycle_spans
            if 'ref' in tokens[start:min(len(tokens), start + 12)]
        )
        lifecycle_before_after = sum(
            1 for start, _, _, _ in lifecycle_spans
            if any(token in {'before', 'after'} for token in tokens[start:min(len(tokens), start + 5)])
        )
        rich_transitions = sum(1 for _, _, is_rich in transition_spans if is_rich)
        plain_transitions = len(transition_spans) - rich_transitions

        score = 0.0

        # Structural FCSTM signals from the token stream.
        score += min(state_blocks * 0.26 + state_decls * 0.18, 0.46)
        score += min(len(event_spans) * 0.10, 0.14)
        score += min(len(def_spans) * 0.16, 0.20)
        score += min(
            lifecycle_blocks * 0.16 + lifecycle_bare * 0.08 + max(len(lifecycle_spans) - lifecycle_blocks - lifecycle_bare, 0) * 0.12,
            0.24,
        )
        score += min(len(aspect_spans) * 0.18, 0.18)
        score += min(rich_transitions * 0.24 + plain_transitions * 0.14, 0.32)
        score += min((state_named + event_named + lifecycle_abstract + lifecycle_ref + lifecycle_before_after) * 0.04, 0.12)

        has_leading_construct = FcstmLexer._analysis_has_leading_construct(tokens)
        if has_leading_construct:
            score += 0.45

        span_density = FcstmLexer._analysis_span_density(
            len(tokens),
            state_spans + event_spans + def_spans + lifecycle_spans + aspect_spans + transition_spans,
        )

        for pattern, penalty in FcstmLexer._ANALYSIS_NEGATIVE_PATTERNS:
            if pattern.search(analysis_text):
                score -= penalty

        if has_leading_construct and score > 0.0:
            if score >= 0.45:
                score += 0.32 * span_density
            elif span_density >= 0.75:
                score += 0.18 * span_density

        # Ensure score stays in valid range
        return max(0.0, min(score, 1.0))
