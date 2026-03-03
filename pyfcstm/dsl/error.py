"""
ANTLR Parsing Error Collection and Reporting Utilities.

This module defines a set of exceptions and a custom ANTLR error listener for
collecting and reporting parsing errors. Instead of halting on the first error,
the listener aggregates errors and raises a single :class:`GrammarParseError`
when parsing is complete, enabling comprehensive diagnostics.

The module contains the following main components:

* :class:`GrammarItemError` - Base class for grammar-related exceptions
* :class:`SyntaxFailError` - Syntax error details for invalid input
* :class:`AmbiguityError` - Error for ambiguous grammar interpretation
* :class:`FullContextAttemptError` - Error for full-context parsing attempts
* :class:`ContextSensitivityError` - Error for context sensitivity warnings
* :class:`UnfinishedParsingError` - Error for unconsumed input after parsing
* :class:`GrammarParseError` - Aggregated exception for multiple errors
* :class:`CollectingErrorListener` - Error listener that aggregates errors

Example::

    >>> from antlr4 import CommonTokenStream
    >>> from pyfcstm.dsl.error import CollectingErrorListener
    >>> listener = CollectingErrorListener()
    >>> # ... attach listener to a parser and parse input ...
    >>> # After parsing:
    >>> listener.check_unfinished_parsing_error(token_stream)
    >>> listener.check_errors()

.. note::
   The listener stores errors in memory until :meth:`CollectingErrorListener.check_errors`
   is called. For large inputs, ensure that error accumulation is acceptable for
   your memory constraints.
"""

import os
from typing import Any, List, Optional

from antlr4 import CommonTokenStream, Token
from antlr4.error.ErrorListener import ErrorListener


class GrammarItemError(Exception):
    """
    Base class for all grammar-related errors.

    This class serves as the parent class for specific grammar error types,
    providing a common interface for error handling in the grammar parsing system.
    """
    pass


class SyntaxFailError(GrammarItemError):
    """
    Error raised when a syntax error is encountered during parsing.

    :param line: The line number where the error occurred.
    :type line: int
    :param column: The column number where the error occurred.
    :type column: int
    :param offending_symbol_text: The text of the problematic symbol, if any.
    :type offending_symbol_text: str or None
    :param msg: The error message.
    :type msg: str
    """

    def __init__(
        self,
        line: int,
        column: int,
        offending_symbol_text: Optional[str],
        msg: str,
    ) -> None:
        self.line = line
        self.column = column
        self.offending_symbol_text = offending_symbol_text
        self.msg = msg
        ctx_info = f", near '{offending_symbol_text}'" if offending_symbol_text else ""
        error_msg = f"Syntax error at line {line}, column {column}{ctx_info}: {msg}"
        super().__init__(error_msg)


class AmbiguityError(GrammarItemError):
    """
    Error raised when grammar ambiguity is detected.

    :param input_range: The range of input text where ambiguity was detected.
    :type input_range: str
    :param start_index: The starting index of the ambiguous section.
    :type start_index: int
    :param stop_index: The ending index of the ambiguous section.
    :type stop_index: int
    """

    def __init__(self, input_range: str, start_index: int, stop_index: int) -> None:
        self.input_range = input_range
        self.start_index = start_index
        self.stop_index = stop_index
        error_msg = (
            f"Grammar ambiguity at input '{input_range}' "
            f"(from index {start_index} to {stop_index})."
        )
        super().__init__(error_msg)


class FullContextAttemptError(GrammarItemError):
    """
    Error raised when the parser attempts full context interpretation.

    :param input_range: The range of input text where full context attempt occurred.
    :type input_range: str
    :param start_index: The starting index of the affected section.
    :type start_index: int
    :param stop_index: The ending index of the affected section.
    :type stop_index: int
    """

    def __init__(self, input_range: str, start_index: int, stop_index: int) -> None:
        self.input_range = input_range
        self.start_index = start_index
        self.stop_index = stop_index
        error_msg = (
            f"Parser attempting full context interpretation at input '{input_range}' "
            f"(from index {start_index} to {stop_index})."
        )
        super().__init__(error_msg)


class ContextSensitivityError(GrammarItemError):
    """
    Error raised when context sensitivity is detected.

    :param input_range: The range of input text where context sensitivity was detected.
    :type input_range: str
    :param start_index: The starting index of the sensitive section.
    :type start_index: int
    :param stop_index: The ending index of the sensitive section.
    :type stop_index: int
    """

    def __init__(self, input_range: str, start_index: int, stop_index: int) -> None:
        self.input_range = input_range
        self.start_index = start_index
        self.stop_index = stop_index
        error_msg = (
            f"Context sensitivity at input '{input_range}' "
            f"(from index {start_index} to {stop_index})."
        )
        super().__init__(error_msg)


class UnfinishedParsingError(GrammarItemError):
    """
    Error raised when the input was not completely consumed by the parser.

    :param lineno: The line number where unparsed content begins.
    :type lineno: int
    """

    def __init__(self, lineno: int) -> None:
        self.lineno = lineno
        error_msg = (
            "Failed to completely parse input text, "
            f"unparsed content at position {self.lineno}"
        )
        super().__init__(error_msg)


class GrammarParseError(Exception):
    """
    Exception raised when one or more grammar parsing errors are encountered.

    :param errors: List of grammar-related errors that occurred during parsing.
    :type errors: list[GrammarItemError]
    :ivar errors: Collected grammar-related errors.
    :vartype errors: list[GrammarItemError]
    """

    def __init__(self, errors: List[GrammarItemError]) -> None:
        self.errors = errors
        error_report = os.linesep.join(
            [f"Error {i + 1}: {error}" for i, error in enumerate(self.errors)]
        )
        error_message = (
            f"Found {len(self.errors)} errors during parsing:{os.linesep}{error_report}"
        )
        super().__init__(error_message)


class CollectingErrorListener(ErrorListener):
    """
    A custom ANTLR error listener that collects errors during parsing.

    This class extends ANTLR's :class:`antlr4.error.ErrorListener.ErrorListener`
    to provide comprehensive error collection and reporting functionality. Instead
    of immediately throwing exceptions, it accumulates errors and can report them
    collectively via :meth:`check_errors`.

    :ivar errors: List storing all encountered error messages.
    :vartype errors: list[GrammarItemError]
    """

    def __init__(self) -> None:
        """
        Initialize the error listener with an empty error collection.
        """
        super().__init__()
        self.errors: List[GrammarItemError] = []

    def syntaxError(
        self,
        recognizer: Any,
        offendingSymbol: Optional[Any],
        line: int,
        column: int,
        msg: str,
        e: Optional[Exception],
    ) -> None:
        """
        Handle and collect syntax errors encountered during parsing.

        :param recognizer: The parser that encountered the error.
        :type recognizer: Any
        :param offendingSymbol: The problematic input symbol.
        :type offendingSymbol: Any or None
        :param line: Line number where the error occurred.
        :type line: int
        :param column: Column number where the error occurred.
        :type column: int
        :param msg: The error message.
        :type msg: str
        :param e: The exception that was raised, if any.
        :type e: Exception or None
        """
        offending_text = offendingSymbol.text if offendingSymbol else None
        self.errors.append(SyntaxFailError(line, column, offending_text, msg))

    def reportAmbiguity(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: int,
        stopIndex: int,
        exact: bool,
        ambigAlts: Any,
        configs: Any,
    ) -> None:
        """
        Handle and collect grammar ambiguity issues.

        :param recognizer: The parser that encountered the ambiguity.
        :type recognizer: Any
        :param dfa: The DFA being processed.
        :type dfa: Any
        :param startIndex: Starting index of the ambiguous input.
        :type startIndex: int
        :param stopIndex: Ending index of the ambiguous input.
        :type stopIndex: int
        :param exact: Whether the ambiguity is exact.
        :type exact: bool
        :param ambigAlts: The ambiguous alternatives.
        :type ambigAlts: Any
        :param configs: The ATN configurations.
        :type configs: Any
        """
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)
        self.errors.append(AmbiguityError(input_range, startIndex, stopIndex))

    def reportAttemptingFullContext(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: int,
        stopIndex: int,
        conflictingAlts: Any,
        configs: Any,
    ) -> None:
        """
        Handle and collect full context parsing attempts.

        :param recognizer: The parser attempting full context.
        :type recognizer: Any
        :param dfa: The DFA being processed.
        :type dfa: Any
        :param startIndex: Starting index of the affected input.
        :type startIndex: int
        :param stopIndex: Ending index of the affected input.
        :type stopIndex: int
        :param conflictingAlts: The conflicting alternatives.
        :type conflictingAlts: Any
        :param configs: The ATN configurations.
        :type configs: Any
        """
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)
        self.errors.append(FullContextAttemptError(input_range, startIndex, stopIndex))

    def reportContextSensitivity(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: int,
        stopIndex: int,
        prediction: Any,
        configs: Any,
    ) -> None:
        """
        Handle and collect context sensitivity issues.

        :param recognizer: The parser that encountered the sensitivity.
        :type recognizer: Any
        :param dfa: The DFA being processed.
        :type dfa: Any
        :param startIndex: Starting index of the sensitive input.
        :type startIndex: int
        :param stopIndex: Ending index of the sensitive input.
        :type stopIndex: int
        :param prediction: The predicted alternative.
        :type prediction: Any
        :param configs: The ATN configurations.
        :type configs: Any
        """
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)
        self.errors.append(ContextSensitivityError(input_range, startIndex, stopIndex))

    def check_unfinished_parsing_error(self, stream: CommonTokenStream) -> None:
        """
        Append an :class:`UnfinishedParsingError` if the token stream is not consumed.

        This method checks whether the token stream has reached the end-of-file
        token. If not, it records an unfinished parsing error using the line
        number of the current token.

        :param stream: The token stream to inspect.
        :type stream: CommonTokenStream
        """
        if stream.LA(1) != Token.EOF:
            self.errors.append(UnfinishedParsingError(lineno=stream.get(stream.index).line))

    def check_errors(self) -> None:
        """
        Check for collected errors and raise an exception if any exist.

        This method should be called after parsing is complete to verify if any
        errors were encountered during the process.

        :raises GrammarParseError: If any errors were collected during parsing,
            with detailed error messages.
        """
        if self.errors:
            raise GrammarParseError(self.errors)
