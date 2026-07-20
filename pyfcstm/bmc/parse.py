"""Parse ``.fbmcq`` query text into parser-independent BMC AST objects.

This module is the public parsing entry point for FCSTM BMC Query files. It is
structured after :mod:`pyfcstm.dsl.parse`: ANTLR lexer/parser classes perform
syntax recognition, :class:`pyfcstm.bmc.listener.BmcQueryParseListener` builds
query objects, and syntax-facing errors are reported through
:class:`pyfcstm.bmc.errors.BmcQueryParseError`.

The parser layer is intentionally narrow. It does not import model classes,
Z3, or verify-registry code; model-aware binding and solver lowering belong to
later BMC modules.

The module contains:

* :func:`parse_with_bmc_grammar_entry` - Parse text through one supported entry
  rule.
* :func:`build_bmc_ast_from_parse_tree` - Walk an already-created parse tree and
  return the mapped AST object.
* :func:`parse_bmc_query`, :func:`parse_bmc_num_expression`, and
  :func:`parse_bmc_cond_expression` - Convenience entry points.

Example::

    >>> from pyfcstm.bmc.parse import parse_bmc_query
    >>> query = parse_bmc_query('check reach <= 1: true;')
    >>> query.property.kind
    'reach'
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, cast

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext, Token
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Tree import ErrorNode, ParseTreeWalker

from .ast import BmcCondExpr, BmcNumExpr
from .errors import BmcQueryParseError
from .grammar.BmcQueryLexer import BmcQueryLexer
from .grammar.BmcQueryParser import BmcQueryParser
from .listener import BmcQueryParseListener
from .query import (
    BmcAssumption,
    BmcProperty,
    BmcQuery,
    InitialSpec,
    InitialVariablePolicy,
)
from pyfcstm.utils.validate import Span

_ParserEntry = Callable[[BmcQueryParser], ParserRuleContext]
_SUPPORTED_ENTRIES = {
    "query",
    "bmc_num_expression_entry",
    "bmc_cond_expression_entry",
}
_SUPPORTED_ENTRY_TEXT = ", ".join(sorted(_SUPPORTED_ENTRIES))


class _CollectingBmcErrorListener(ErrorListener):
    """Collect ANTLR syntax diagnostics for BMC query parsing.

    :ivar messages: Human-readable diagnostics reported by lexer and parser.
    :vartype messages: List[str]

    Example::

        >>> listener = _CollectingBmcErrorListener()
        >>> listener.messages
        []
    """

    def __init__(self) -> None:
        """Initialize an empty diagnostic buffer.

        :return: ``None``.
        :rtype: None
        """
        super().__init__()
        self.messages: List[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e) -> None:
        """Record an ANTLR syntax error callback.

        :param recognizer: Lexer or parser instance that reported the error.
        :type recognizer: object
        :param offendingSymbol: Token or text near the failure.
        :type offendingSymbol: object
        :param line: One-based input line number.
        :type line: int
        :param column: Zero-based input column number.
        :type column: int
        :param msg: ANTLR diagnostic message.
        :type msg: str
        :param e: Optional ANTLR recognition exception.
        :type e: object
        :return: ``None``.
        :rtype: None
        """
        symbol_text = getattr(offendingSymbol, "text", None)
        if symbol_text is None and offendingSymbol is not None:
            symbol_text = str(offendingSymbol)
        near = " near %r" % symbol_text if symbol_text is not None else ""
        self.messages.append("line %d:%d%s: %s" % (line, column, near, msg))

    def check_errors(self) -> None:
        """Raise :class:`BmcQueryParseError` if diagnostics were collected.

        :return: ``None``.
        :rtype: None
        :raises pyfcstm.bmc.errors.BmcQueryParseError: If syntax diagnostics
            were recorded.

        Example::

            >>> listener = _CollectingBmcErrorListener()
            >>> listener.check_errors()
        """
        if self.messages:
            raise BmcQueryParseError("; ".join(self.messages))

    def check_unfinished_parsing_error(self, stream: CommonTokenStream) -> None:
        """Record an error when a parse entry leaves tokens unconsumed.

        :param stream: Token stream used by the parser.
        :type stream: antlr4.CommonTokenStream
        :return: ``None``.
        :rtype: None
        """
        if stream.LA(1) != Token.EOF:
            token = cast(Any, stream.LT(1))
            self.messages.append(
                "line %d:%d near %r: parser did not consume the full input"
                % (token.line, token.column, token.text)
            )


def _build_lexer(
    input_text: str, error_listener: _CollectingBmcErrorListener
) -> BmcQueryLexer:
    """Build a BMC query lexer with the shared collecting error listener.

    :param input_text: Query or expression text.
    :type input_text: str
    :param error_listener: Error listener that receives lexer diagnostics.
    :type error_listener: _CollectingBmcErrorListener
    :return: Configured BMC query lexer.
    :rtype: pyfcstm.bmc.grammar.BmcQueryLexer.BmcQueryLexer

    Example::

        >>> listener = _CollectingBmcErrorListener()
        >>> _build_lexer('true', listener).grammarFileName
        'BmcQueryLexer.g4'
    """
    lexer = BmcQueryLexer(InputStream(input_text))
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)
    return lexer


def _build_parser(
    stream: CommonTokenStream, error_listener: _CollectingBmcErrorListener
) -> BmcQueryParser:
    """Build a BMC query parser with collecting syntax diagnostics.

    :param stream: Token stream produced by :func:`_build_lexer`.
    :type stream: antlr4.CommonTokenStream
    :param error_listener: Error listener that receives parser diagnostics.
    :type error_listener: _CollectingBmcErrorListener
    :return: Configured BMC query parser.
    :rtype: pyfcstm.bmc.grammar.BmcQueryParser.BmcQueryParser

    Example::

        >>> listener = _CollectingBmcErrorListener()
        >>> lexer = _build_lexer('true', listener)
        >>> _build_parser(CommonTokenStream(lexer), listener).grammarFileName
        'BmcQueryParser.g4'
    """
    parser = BmcQueryParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)
    return parser


def _find_error_node_text(parse_tree: ParserRuleContext) -> str:
    """Return the first ANTLR recovery marker within ``parse_tree``.

    Callers that provide their own parse trees may bypass the collecting error
    listener used by :func:`parse_with_bmc_grammar_entry`.  ANTLR can still
    recover from malformed input by inserting :class:`antlr4.tree.Tree.ErrorNode`
    objects, attaching a recognition exception to a parser context, or creating
    an empty generated child context for a missing nonterminal.  Detecting those
    recovery markers before listener walking keeps the public parse-tree builder
    from leaking low-level literal-conversion failures.

    :param parse_tree: Root parse-tree context to inspect.
    :type parse_tree: antlr4.ParserRuleContext
    :return: Text for the first recovery marker, or ``""`` when none exists.
    :rtype: str

    Example::

        >>> _find_error_node_text(ParserRuleContext())
        ''
    """
    pending = [parse_tree]
    while pending:
        node = pending.pop()
        if isinstance(node, ErrorNode):
            return "recovery node %r" % node.getText()
        if isinstance(node, ParserRuleContext):
            exception = getattr(node, "exception", None)
            if exception is not None:
                return "recovered %s after %s" % (
                    type(node).__name__,
                    type(exception).__name__,
                )
            if (
                type(node) is not ParserRuleContext
                and node.getChildCount() == 0
                and node.getText() == ""
            ):
                return "empty recovered %s" % type(node).__name__
        for index in range(node.getChildCount() - 1, -1, -1):
            pending.append(node.getChild(index))
    return ""


def _context_span(context: ParserRuleContext) -> Span:
    """Return a one-based half-open span for an ANTLR context.

    :param context: ANTLR parser context with start/stop tokens.
    :type context: antlr4.ParserRuleContext
    :return: Source span covering the context.
    :rtype: pyfcstm.utils.validate.Span
    """
    start = context.start
    stop = context.stop if context.stop is not None else start
    end_column = stop.column + len(stop.text or "") + 1
    column = start.column + 1
    if stop.line == start.line and end_column <= column:
        end_column = column + 1
    return Span(
        line=start.line,
        column=column,
        end_line=stop.line,
        end_column=end_column,
    )


def _attach_query_source_metadata(
    value: Any, parse_tree: ParserRuleContext, listener: BmcQueryParseListener,
    source_path: Optional[str],
) -> Any:
    """Attach parser spans to a query root without changing canonical data."""
    if not isinstance(value, BmcQuery):
        return value
    spans: Dict[int, Span] = {}
    pending = [parse_tree]
    while pending:
        node = pending.pop()
        mapped = listener.nodes.get(node)
        if isinstance(
            mapped,
            (
                BmcQuery,
                BmcProperty,
                BmcAssumption,
                InitialSpec,
                InitialVariablePolicy,
                BmcCondExpr,
                BmcNumExpr,
            ),
        ):
            spans.setdefault(id(mapped), _context_span(node))
        for index in range(node.getChildCount() - 1, -1, -1):
            child = node.getChild(index)
            if isinstance(child, ParserRuleContext):
                pending.append(child)
    return replace(
        value,
        _source_path=source_path,
        _source_spans=tuple(sorted(spans.items(), key=lambda item: item[0])),
    )


def build_bmc_ast_from_parse_tree(
    parse_tree: ParserRuleContext, source_path: Optional[str] = None
) -> Any:
    """Build a BMC AST object from an already-created ANTLR parse tree.

    :param parse_tree: Root parse-tree context to walk.
    :type parse_tree: antlr4.ParserRuleContext
    :param source_path: Optional source path attached to query metadata,
        defaults to ``None``.
    :type source_path: Optional[str], optional
    :return: AST or query object mapped for ``parse_tree``.
    :rtype: object
    :raises TypeError: If ``parse_tree`` is not an ANTLR parser context.
    :raises pyfcstm.bmc.errors.BmcQueryParseError: If the parse tree contains
        ANTLR recovery markers, the listener cannot map a recovered child
        context, or the listener does not map the provided root context.
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If a syntactically valid query
        parse tree fails structural query-model validation.

    Example::

        >>> from antlr4 import CommonTokenStream, InputStream
        >>> lexer = BmcQueryLexer(InputStream('1'))
        >>> parser = BmcQueryParser(CommonTokenStream(lexer))
        >>> tree = parser.bmc_num_expression_entry()
        >>> build_bmc_ast_from_parse_tree(tree).value
        1
    """
    if not isinstance(parse_tree, ParserRuleContext):
        raise TypeError("parse_tree must be ParserRuleContext.")
    error_node_text = _find_error_node_text(parse_tree)
    if error_node_text:
        raise BmcQueryParseError(
            "BMC parse tree contains ANTLR recovery marker: %s." % error_node_text
        )
    listener = BmcQueryParseListener()
    walker = ParseTreeWalker()
    try:
        walker.walk(listener, parse_tree)
    except KeyError as err:
        # KeyError: ANTLR error recovery can leave required child contexts
        # present-but-unmapped, for example ``active("S", )`` creates an empty
        # frame_selector context. Surface this as a stable parse-tree error.
        raise BmcQueryParseError(
            "BMC parse tree construction failed because a child context was not mapped."
        ) from err
    try:
        result = listener.nodes[parse_tree]
        return _attach_query_source_metadata(result, parse_tree, listener, source_path)
    except KeyError as err:
        # KeyError: listener.nodes has no root mapping when the supplied
        # parse-tree context is outside the supported BMC builder surface.
        raise BmcQueryParseError(
            "No BMC AST node was built for parse tree root %s."
            % type(parse_tree).__name__
        ) from err


def parse_with_bmc_grammar_entry(
    input_text: str,
    entry_name: str,
    force_finished: bool = True,
    source_path: Optional[str] = None,
) -> Any:
    """Parse text with a supported BMC grammar entry rule.

    :param input_text: Query or expression text.
    :type input_text: str
    :param entry_name: One of ``"query"``, ``"bmc_num_expression_entry"``, or
        ``"bmc_cond_expression_entry"``.
    :type entry_name: str
    :param force_finished: Whether the token stream must be exhausted after the
        entry rule, defaults to ``True``.
    :type force_finished: bool, optional
    :param source_path: Optional source path attached to query metadata,
        defaults to ``None``.
    :type source_path: Optional[str], optional
    :return: AST object produced by the entry rule.
    :rtype: object
    :raises pyfcstm.bmc.errors.BmcQueryParseError: If ``entry_name`` is
        unsupported or parsing fails.

    Example::

        >>> node = parse_with_bmc_grammar_entry('cycle + 1', 'bmc_num_expression_entry')
        >>> node.to_canonical()['node']
        'num_binary'

    .. note::
        The currently supported text entries already end in ``EOF`` in the
        grammar.  ``force_finished`` is kept for API parity with
        :mod:`pyfcstm.dsl.parse` and as an extra guard for future entries.
    """
    if entry_name not in _SUPPORTED_ENTRIES:
        raise BmcQueryParseError(
            "Unsupported BMC grammar entry: %r. Supported entries: %s."
            % (entry_name, _SUPPORTED_ENTRY_TEXT)
        )

    error_listener = _CollectingBmcErrorListener()
    lexer = _build_lexer(input_text, error_listener)
    stream = CommonTokenStream(lexer)
    parser = _build_parser(stream, error_listener)

    entry: Dict[str, _ParserEntry] = {
        "query": BmcQueryParser.query,
        "bmc_num_expression_entry": BmcQueryParser.bmc_num_expression_entry,
        "bmc_cond_expression_entry": BmcQueryParser.bmc_cond_expression_entry,
    }
    parse_tree = entry[entry_name](parser)
    if force_finished:
        error_listener.check_unfinished_parsing_error(stream)
    error_listener.check_errors()
    return build_bmc_ast_from_parse_tree(parse_tree, source_path=source_path)


def parse_bmc_query(
    input_text: str, source_path: Optional[str] = None
) -> BmcQuery:
    """Parse a complete ``.fbmcq`` query.

    :param input_text: Complete query text.
    :type input_text: str
    :param source_path: Optional source path attached to query metadata,
        defaults to ``None``.
    :type source_path: Optional[str], optional
    :return: Parsed query object.
    :rtype: pyfcstm.bmc.query.BmcQuery
    :raises pyfcstm.bmc.errors.BmcQueryParseError: If syntax parsing fails.
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If the parsed query is
        structurally invalid, for example ``check ... <= 0``.

    Example::

        >>> parse_bmc_query('check reach <= 1: true;').property.bound
        1
    """
    result = parse_with_bmc_grammar_entry(
        input_text, "query", source_path=source_path
    )
    if not isinstance(result, BmcQuery):
        raise BmcQueryParseError("BMC query entry did not produce BmcQuery.")
    return result


def parse_bmc_num_expression(input_text: str) -> BmcNumExpr:
    """Parse a standalone BMC numeric expression.

    :param input_text: Numeric expression text.
    :type input_text: str
    :return: Parsed numeric expression object.
    :rtype: pyfcstm.bmc.ast.BmcNumExpr
    :raises pyfcstm.bmc.errors.BmcQueryParseError: If syntax parsing fails.

    Example::

        >>> parse_bmc_num_expression('cycle + 1').to_canonical()['op']
        '+'
    """
    result = parse_with_bmc_grammar_entry(input_text, "bmc_num_expression_entry")
    if not isinstance(result, BmcNumExpr):
        raise BmcQueryParseError(
            "BMC numeric-expression entry did not produce BmcNumExpr."
        )
    return result


def parse_bmc_cond_expression(input_text: str) -> BmcCondExpr:
    """Parse a standalone BMC condition expression.

    :param input_text: Condition expression text.
    :type input_text: str
    :return: Parsed condition expression object.
    :rtype: pyfcstm.bmc.ast.BmcCondExpr
    :raises pyfcstm.bmc.errors.BmcQueryParseError: If syntax parsing fails.

    Example::

        >>> parse_bmc_cond_expression('active("Root.A")').to_canonical()['node']
        'active'
    """
    result = parse_with_bmc_grammar_entry(input_text, "bmc_cond_expression_entry")
    if not isinstance(result, BmcCondExpr):
        raise BmcQueryParseError(
            "BMC condition-expression entry did not produce BmcCondExpr."
        )
    return result


__all__ = [
    "parse_bmc_query",
    "parse_bmc_num_expression",
    "parse_bmc_cond_expression",
    "parse_with_bmc_grammar_entry",
    "build_bmc_ast_from_parse_tree",
]
