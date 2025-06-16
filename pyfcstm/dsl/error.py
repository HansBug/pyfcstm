"""
ANTLR Error Collection and Handling Module

This module provides functionality for collecting and handling errors during ANTLR parsing processes.
It implements a custom error listener that accumulates errors instead of throwing them immediately,
allowing for comprehensive error reporting after the parsing is complete.
"""

import os
from typing import List

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

    :param line: The line number where the error occurred
    :type line: int
    :param column: The column number where the error occurred
    :type column: int
    :param offending_symbol_text: The text of the problematic symbol
    :type offending_symbol_text: str
    :param msg: The error message
    :type msg: str
    """

    def __init__(self, line, column, offending_symbol_text, msg):
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

    :param input_range: The range of input text where ambiguity was detected
    :type input_range: str
    :param start_index: The starting index of the ambiguous section
    :type start_index: int
    :param stop_index: The ending index of the ambiguous section
    :type stop_index: int
    """

    def __init__(self, input_range, start_index, stop_index):
        self.input_range = input_range
        self.start_index = start_index
        self.stop_index = stop_index
        error_msg = f"Grammar ambiguity at input '{input_range}' (from index {start_index} to {stop_index})."
        super().__init__(error_msg)


class FullContextAttemptError(GrammarItemError):
    """
    Error raised when the parser attempts full context interpretation.

    :param input_range: The range of input text where full context attempt occurred
    :type input_range: str
    :param start_index: The starting index of the affected section
    :type start_index: int
    :param stop_index: The ending index of the affected section
    :type stop_index: int
    """

    def __init__(self, input_range, start_index, stop_index):
        self.input_range = input_range
        self.start_index = start_index
        self.stop_index = stop_index
        error_msg = (f"Parser attempting full context interpretation at input '{input_range}' "
                     f"(from index {start_index} to {stop_index}).")
        super().__init__(error_msg)


class ContextSensitivityError(GrammarItemError):
    """
    Error raised when context sensitivity is detected.

    :param input_range: The range of input text where context sensitivity was detected
    :type input_range: str
    :param start_index: The starting index of the sensitive section
    :type start_index: int
    :param stop_index: The ending index of the sensitive section
    :type stop_index: int
    """

    def __init__(self, input_range, start_index, stop_index):
        self.input_range = input_range
        self.start_index = start_index
        self.stop_index = stop_index
        error_msg = f"Context sensitivity at input '{input_range}' (from index {start_index} to {stop_index})."
        super().__init__(error_msg)


class UnfinishedParsingError(GrammarItemError):
    def __init__(self, lineno):
        self.lineno = lineno
        error_msg = f"Failed to completely parse input text, unparsed content at position {self.lineno}"
        super().__init__(error_msg)


class GrammarParseError(Exception):
    """
    Exception raised when one or more grammar parsing errors are encountered.

    :param errors: List of grammar-related errors that occurred during parsing
    :type errors: List[GrammarItemError]
    """

    def __init__(self, errors: List[GrammarItemError]):
        self.errors = errors
        error_report = os.linesep.join([f"Error {i + 1}: {error}" for i, error in enumerate(self.errors)])
        error_message = f"Found {len(self.errors)} errors during parsing:{os.linesep}{error_report}"
        super().__init__(error_message)


class CollectingErrorListener(ErrorListener):
    """
    A custom ANTLR error listener that collects errors during parsing.

    This class extends ANTLR's ErrorListener to provide comprehensive error collection
    and reporting functionality. Instead of immediately throwing exceptions, it
    accumulates errors and can report them collectively.

    :ivar errors: List storing all encountered error messages
    :type errors: list[GrammarItemError]
    """

    def __init__(self):
        """
        Initialize the error listener with an empty error collection.
        """
        super().__init__()
        self.errors: List[GrammarItemError] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """
        Handle and collect syntax errors encountered during parsing.

        :param recognizer: The parser that encountered the error
        :param offendingSymbol: The problematic input symbol
        :param line: Line number where the error occurred
        :param column: Column number where the error occurred
        :param msg: The error message
        :param e: The exception that was raised
        """
        offending_text = offendingSymbol.text if offendingSymbol else None
        self.errors.append(SyntaxFailError(line, column, offending_text, msg))

    def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        """
        Handle and collect grammar ambiguity issues.

        :param recognizer: The parser that encountered the ambiguity
        :param dfa: The DFA being processed
        :param startIndex: Starting index of the ambiguous input
        :param stopIndex: Ending index of the ambiguous input
        :param exact: Whether the ambiguity is exact
        :param ambigAlts: The ambiguous alternatives
        :param configs: The ATN configurations
        """
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)
        self.errors.append(AmbiguityError(input_range, startIndex, stopIndex))

    def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
        """
        Handle and collect full context parsing attempts.

        :param recognizer: The parser attempting full context
        :param dfa: The DFA being processed
        :param startIndex: Starting index of the affected input
        :param stopIndex: Ending index of the affected input
        :param conflictingAlts: The conflicting alternatives
        :param configs: The ATN configurations
        """
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)
        self.errors.append(FullContextAttemptError(input_range, startIndex, stopIndex))

    def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
        """
        Handle and collect context sensitivity issues.

        :param recognizer: The parser that encountered the sensitivity
        :param dfa: The DFA being processed
        :param startIndex: Starting index of the sensitive input
        :param stopIndex: Ending index of the sensitive input
        :param prediction: The predicted alternative
        :param configs: The ATN configurations
        """
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)
        self.errors.append(ContextSensitivityError(input_range, startIndex, stopIndex))

    def check_unfinished_parsing_error(self, stream: CommonTokenStream):
        if stream.LA(1) != Token.EOF:
            self.errors.append(UnfinishedParsingError(lineno=stream.get(stream.index).line))

    def check_errors(self):
        """
        Check for collected errors and raise an exception if any exist.

        This method should be called after parsing is complete to verify if any
        errors were encountered during the process.

        :raises GrammarParseError: If any errors were collected during parsing, with detailed error messages
        """
        if self.errors:
            raise GrammarParseError(self.errors)
