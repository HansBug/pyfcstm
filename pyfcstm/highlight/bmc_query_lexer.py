"""Pygments lexer for FCSTM BMC Query files.

This module defines :class:`FcstmBmcQueryLexer`, a lightweight lexer for the
``*.fbmcq`` query language used by the FCSTM bounded-model-checking workstream.
The lexer mirrors the query grammar token surface closely enough for editor and
Sphinx highlighting, but it deliberately does not parse or semantically validate
queries.

The module contains:

* :class:`FcstmBmcQueryLexer` - Regex-based lexer for ``*.fbmcq`` query tokens.

.. note::
   :meth:`FcstmBmcQueryLexer.analyse_text` is a pure string heuristic.  It must
   not import :mod:`pyfcstm.bmc.parse`, call the ANTLR parser, resolve model
   paths, or run semantic binding.  Pygments may call language detection on
   arbitrary text, including malformed snippets.

Example::

    >>> from pyfcstm.highlight import FcstmBmcQueryLexer
    >>> lexer = FcstmBmcQueryLexer()
    >>> lexer.name
    'FCSTM BMC Query'
    >>> query = 'init cold;\\ncheck reach <= 2: active("Root.Done");'
    >>> FcstmBmcQueryLexer.analyse_text(query) >= 0.8
    True
"""

import re

from pygments.lexer import RegexLexer, include, words
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Whitespace,
)

__all__ = ["FcstmBmcQueryLexer"]


class FcstmBmcQueryLexer(RegexLexer):
    """Lexer for FCSTM BMC Query files.

    This lexer highlights the syntax-only ``*.fbmcq`` query surface used to
    express bounded model checking objectives for FCSTM models.  It recognizes
    query clauses, BMC-only atoms, FCSTM-compatible expression operators,
    literals, strings, comments, and punctuation.  It does not validate whether
    referenced states, events, variables, cases, or unsupported calls are
    meaningful for a particular :class:`pyfcstm.model.StateMachine`.

    :cvar name: Human-readable Pygments lexer name.
    :type name: str
    :cvar aliases: Pygments aliases for lookup by query-language name.
    :type aliases: list
    :cvar filenames: Filename globs recognized by Pygments.
    :type filenames: list
    :cvar mimetypes: MIME types recognized by Pygments.
    :type mimetypes: list

    Example::

        >>> from pygments import lex
        >>> from pyfcstm.highlight import FcstmBmcQueryLexer
        >>> tokens = [(kind, text) for kind, text in lex('init cold;', FcstmBmcQueryLexer()) if text.strip()]
        >>> tokens[0]
        (Token.Keyword.Declaration, 'init')
    """

    name = "FCSTM BMC Query"
    aliases = ["fbmcq", "fcstm-bmc-query"]
    filenames = ["*.fbmcq"]
    mimetypes = ["text/x-fcstm-bmc-query"]

    _CLAUSE_KEYWORDS = (
        "init",
        "state",
        "assume",
        "event",
        "events",
        "check",
    )
    _RESERVED_KEYWORDS = (
        "cold",
        "terminated",
        "where",
        "havoc",
        "always",
        "at",
        "cardinality",
        "any",
        "reach",
        "forbid",
        "invariant",
        "must_reach",
        "exists_always",
        "response",
        "cover",
        "trigger",
        "within",
        "current",
    )
    _ATOM_NAMES = (
        "var",
        "active",
        "terminated",
        "event",
        "case",
        "called",
    )
    _BARE_ATOM_NAMES = ("cycle",)
    _UFUNC_NAMES = (
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "sinh",
        "cosh",
        "tanh",
        "asinh",
        "acosh",
        "atanh",
        "sqrt",
        "cbrt",
        "exp",
        "log",
        "log10",
        "log2",
        "log1p",
        "abs",
        "ceil",
        "floor",
        "round",
        "trunc",
        "sign",
    )
    _QUERY_HINT_RE = re.compile(
        r"(?is)\b(?:init|assume|check)\b|\b(?:active|event|case|called|var|terminated)\s*\("
    )
    _CHECK_RE = re.compile(
        r"(?is)\bcheck\s+(?:reach|forbid|invariant|must_reach|exists_always|response|cover)\s*<=\s*\d+\s*:"
    )
    _ASSUME_RE = re.compile(
        r"(?is)\bassume\s+(?:always|at\s+\d+|event\s*\(|events\s+cardinality)\b"
    )
    _INIT_RE = re.compile(r"(?is)\binit\s+(?:cold|terminated|state\s*\()")

    tokens = {
        "root": [
            include("whitespace"),
            include("comments"),
            include("strings"),
            # Built-in atom/function names must come before generic keywords so
            # dual-role words such as ``event(...)`` and ``terminated()`` are
            # highlighted as calls while bare clause words stay as keywords.
            # The suffix lookahead is the disambiguation boundary: atom names
            # only match when a parenthesized call follows.
            (words(_ATOM_NAMES, suffix=r"\b(?=\s*\()"), Name.Builtin),
            (words(_BARE_ATOM_NAMES, suffix=r"\b"), Name.Builtin),
            (words(("at_most_one",), suffix=r"\b"), Name.Builtin),
            (words(_UFUNC_NAMES, suffix=r"\b(?=\s*\()"), Name.Builtin),
            (words(_CLAUSE_KEYWORDS, suffix=r"\b"), Keyword.Declaration),
            (words(_RESERVED_KEYWORDS, suffix=r"\b"), Keyword.Reserved),
            (
                words(("and", "or", "not", "implies", "xor", "iff"), suffix=r"\b"),
                Operator.Word,
            ),
            (
                words(
                    ("True", "true", "TRUE", "False", "false", "FALSE"), suffix=r"\b"
                ),
                Keyword.Constant,
            ),
            (words(("pi", "E", "tau"), suffix=r"\b"), Name.Constant),
            # Keep compact ranges such as ``0..3`` from being consumed as a
            # floating-point prefix before the range operator is reached.
            (r"[0-9]+(?=\.\.)", Number.Integer),
            include("numbers"),
            # Multi-character operators must precede shorter alternatives.
            (r"\*\*", Operator),
            (r">>|<<", Operator),
            (r"<=|>=|==|!=", Operator),
            (r"&&|\|\|", Operator),
            (r"=>|->|\.\.", Operator),
            (r"!", Operator.Word),
            (r"[+\-*/%&|^~<>]", Operator),
            (r"=|\?", Operator),
            (r"[:;,{}()\[\]./]", Punctuation),
            (r"[a-zA-Z_][a-zA-Z0-9_]*", Name),
        ],
        "whitespace": [
            (r"\s+", Whitespace),
        ],
        "comments": [
            (r"/\*", Comment.Multiline, "block-comment"),
            (r"//.*?$", Comment.Single),
            (r"#.*?$", Comment.Single),
        ],
        "block-comment": [
            (r"\*/", Comment.Multiline, "#pop"),
            (r"[^*]+", Comment.Multiline),
            (r"\*", Comment.Multiline),
        ],
        "strings": [
            (
                r'"([^"\\\r\n]|\\[btnfr"\'\\]|\\[0-7]{1,3}|\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2})*"',
                String.Double,
            ),
            (
                r"'([^'\\\r\n]|\\[btnfr\"'\\]|\\[0-7]{1,3}|\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2})*'",
                String.Single,
            ),
        ],
        "numbers": [
            (r"0x[0-9a-fA-F]+", Number.Hex),
            (r"[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?", Number.Float),
            (r"\.[0-9]+([eE][+-]?[0-9]+)?", Number.Float),
            (r"[0-9]+[eE][+-]?[0-9]+", Number.Float),
            (r"[0-9]+", Number.Integer),
        ],
    }

    # Do not decorate this with @staticmethod.  RegexLexerMeta wraps
    # ``analyse_text`` through Pygments' ``make_analysator``; pre-wrapping it
    # can make older supported Pygments releases swallow a TypeError and
    # report ``0.0`` for valid query text.
    def analyse_text(text: str) -> float:
        """Return a heuristic confidence score for ``*.fbmcq`` text.

        The score is intentionally based on lightweight regular expressions so
        editor and Pygments discovery can run on incomplete or invalid query
        snippets.  A complete query with ``init``/``assume``/``check`` clauses
        receives a high score; unrelated text receives ``0.0``.

        :param text: Candidate source text.
        :type text: str
        :return: Pygments confidence score between ``0.0`` and ``1.0``.
        :rtype: float

        Example::

            >>> FcstmBmcQueryLexer.analyse_text('check cover <= 3: case("A::B");') >= 0.70
            True
        """
        if not text or not FcstmBmcQueryLexer._QUERY_HINT_RE.search(text):
            return 0.0

        score = 0.0
        if FcstmBmcQueryLexer._CHECK_RE.search(text):
            score += 0.60
        if FcstmBmcQueryLexer._ASSUME_RE.search(text):
            score += 0.25
        if FcstmBmcQueryLexer._INIT_RE.search(text):
            score += 0.20
        if re.search(r"(?is)\b(?:active|event|case|called|var|terminated)\s*\(", text):
            score += 0.10
        if re.search(r"(?is)\bstate\s+\w+\b|\[\s*\*\s*\]\s*->", text):
            score -= 0.30

        return max(0.0, min(score, 1.0))
