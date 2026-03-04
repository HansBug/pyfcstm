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

        # Enhance error message with actionable suggestions
        enhanced_msg = self._enhance_error_message(msg, offending_symbol_text)

        ctx_info = f", near '{offending_symbol_text}'" if offending_symbol_text else ""
        error_msg = f"Syntax error at line {line}, column {column}{ctx_info}: {enhanced_msg}"
        super().__init__(error_msg)

    @staticmethod
    def _enhance_error_message(msg: str, offending_symbol: Optional[str]) -> str:
        """
        Enhance ANTLR error messages with actionable suggestions.

        :param msg: Original ANTLR error message.
        :type msg: str
        :param offending_symbol: The problematic symbol text.
        :type offending_symbol: str or None
        :return: Enhanced error message with suggestions.
        :rtype: str
        """
        # Pattern matching for common errors with actionable suggestions
        if "missing ';'" in msg:
            # Determine context based on offending symbol
            if offending_symbol == 'def':
                return "Missing semicolon after variable definition"
            elif offending_symbol == 'state':
                return "Missing semicolon after previous statement"
            elif offending_symbol == '}':
                return "Missing semicolon after operation statement"
            elif offending_symbol and offending_symbol.isidentifier():
                return "Missing semicolon after previous statement"
            return "Missing semicolon"

        elif "missing '}'" in msg:
            if offending_symbol == '<EOF>':
                return "Missing closing brace - check for unclosed state definitions or action blocks"
            return "Missing closing brace"

        elif "missing '{'" in msg:
            return "Missing opening brace for block"

        elif "missing ']'" in msg:
            return "Missing closing bracket in guard condition"

        elif "missing '['" in msg:
            return "Missing opening bracket for guard condition"

        elif "missing '->'" in msg:
            return "Missing transition arrow '->'"

        elif "missing '='" in msg:
            return "Missing equals sign in assignment or definition"

        elif "extraneous input" in msg:
            if offending_symbol == '<EOF>':
                return "Unexpected end of file - missing closing brace"
            elif offending_symbol == '}':
                return "Extra closing brace - check for mismatched braces"
            elif offending_symbol == 'during':
                return "Unexpected 'during' keyword - missing closing brace before this line"
            return f"Unexpected token '{offending_symbol}'"

        elif "mismatched input" in msg:
            if "expecting ';'" in msg:
                if offending_symbol == 'state':
                    return "Missing semicolon after previous state definition"
                elif offending_symbol == '}':
                    return "Missing semicolon before closing brace"
                return "Missing semicolon on previous line"
            elif "expecting '='" in msg:
                return "Missing equals sign in variable definition"
            elif "expecting {';', 'named'}" in msg:
                return "Missing semicolon after event definition"
            return f"Unexpected token '{offending_symbol}'"

        elif "no viable alternative at input" in msg:
            # Analyze the offending symbol to provide better context
            if offending_symbol:
                # Check for common patterns
                symbol_lower = offending_symbol.lower()

                # Pattern: stateXXXstate (missing semicolon between states)
                if 'state' in symbol_lower and symbol_lower.count('state') >= 2:
                    return "Missing semicolon between state definitions"

                # Pattern: stateXXXenter/exit/during (missing brace or semicolon)
                if 'state' in symbol_lower and any(kw in symbol_lower for kw in ['enter', 'exit', 'during']):
                    return "Missing opening brace or semicolon before lifecycle action"

                # Pattern: stateXXXID (missing semicolon after state, before transition/next statement)
                if 'state' in symbol_lower and len(offending_symbol) > 10:
                    return "Missing semicolon after state definition"

                # Pattern: Active= (wrong arrow operator)
                if '=' in offending_symbol:
                    return "Invalid operator - use '->' for transitions, not '=>'"

                # Pattern: enterabstractXXX} (missing semicolon after abstract)
                if any(kw in symbol_lower for kw in ['abstract', 'ref']) and '}' in offending_symbol:
                    return "Missing semicolon after abstract function or reference definition"

            return "Invalid syntax - check for missing semicolons, braces, or operators"

        elif "token recognition error" in msg:
            if '"' in str(offending_symbol):
                return "Unclosed string literal - add closing quote"
            return "Invalid character or token"

        # Return original message if no pattern matches
        return msg


class AmbiguityError(GrammarItemError):
    """
    Error raised when grammar ambiguity is detected.

    This error indicates that the parser found multiple valid ways to interpret
    the input, which may suggest a grammar design issue or ambiguous syntax.

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

        # Enhance error message with user-friendly explanation
        enhanced_msg = self._enhance_ambiguity_message(input_range)

        error_msg = (
            f"Ambiguous syntax at '{input_range}' (index {start_index}-{stop_index}): {enhanced_msg}"
        )
        super().__init__(error_msg)

    @staticmethod
    def _enhance_ambiguity_message(input_range: str) -> str:
        """
        Enhance ambiguity error messages with actionable suggestions.

        :param input_range: The ambiguous input text.
        :type input_range: str
        :return: Enhanced error message.
        :rtype: str
        """
        # Analyze the input to provide context-specific suggestions
        if not input_range or not input_range.strip():
            return "The parser found multiple ways to interpret this syntax"

        input_lower = input_range.lower().strip()

        # Check for common ambiguous patterns
        if 'state' in input_lower:
            return "Multiple interpretations possible - check for missing semicolons or braces around state definitions"
        elif any(kw in input_lower for kw in ['enter', 'exit', 'during']):
            return "Lifecycle action syntax is ambiguous - verify correct placement of braces and keywords"
        elif '->' in input_range or ':' in input_range:
            return "Transition syntax is ambiguous - check event scoping and guard condition syntax"
        elif any(op in input_range for op in ['=', '+', '-', '*', '/']):
            return "Expression syntax is ambiguous - consider adding parentheses for clarity"

        return "The parser found multiple ways to interpret this syntax - consider simplifying or adding explicit delimiters"


class FullContextAttemptError(GrammarItemError):
    """
    Error raised when the parser attempts full context interpretation.

    This error indicates that the parser needed to use a more expensive parsing
    strategy to resolve ambiguity. While not necessarily an error in user code,
    it may suggest complex or ambiguous syntax that could be simplified.

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

        # Enhance error message with user-friendly explanation
        enhanced_msg = self._enhance_full_context_message(input_range)

        error_msg = (
            f"Complex syntax at '{input_range}' (index {start_index}-{stop_index}): {enhanced_msg}"
        )
        super().__init__(error_msg)

    @staticmethod
    def _enhance_full_context_message(input_range: str) -> str:
        """
        Enhance full context error messages with actionable suggestions.

        :param input_range: The input text requiring full context parsing.
        :type input_range: str
        :return: Enhanced error message.
        :rtype: str
        """
        if not input_range or not input_range.strip():
            return "The parser needed extra analysis to understand this syntax"

        input_lower = input_range.lower().strip()

        # Check for common patterns that require full context
        if 'state' in input_lower and any(kw in input_lower for kw in ['enter', 'exit', 'during']):
            return "Complex state definition - consider breaking into smaller parts or adding explicit delimiters"
        elif '->' in input_range and ':' in input_range:
            return "Complex transition syntax - consider simplifying event scoping or guard conditions"
        elif any(op in input_range for op in ['&&', '||', 'and', 'or']):
            return "Complex logical expression - consider adding parentheses for clarity"

        return "The parser needed extra analysis to understand this syntax - consider simplifying"


class ContextSensitivityError(GrammarItemError):
    """
    Error raised when context sensitivity is detected.

    This error indicates that the parser's decision depends on the surrounding
    context in a way that may make the grammar harder to understand or maintain.
    While not necessarily an error, it suggests the syntax could be clearer.

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

        # Enhance error message with user-friendly explanation
        enhanced_msg = self._enhance_context_sensitivity_message(input_range)

        error_msg = (
            f"Context-dependent syntax at '{input_range}' (index {start_index}-{stop_index}): {enhanced_msg}"
        )
        super().__init__(error_msg)

    @staticmethod
    def _enhance_context_sensitivity_message(input_range: str) -> str:
        """
        Enhance context sensitivity error messages with actionable suggestions.

        :param input_range: The context-sensitive input text.
        :type input_range: str
        :return: Enhanced error message.
        :rtype: str
        """
        if not input_range or not input_range.strip():
            return "The meaning of this syntax depends on surrounding context"

        input_lower = input_range.lower().strip()

        # Check for common context-sensitive patterns
        if any(kw in input_lower for kw in ['before', 'after']):
            return "Aspect action placement is context-dependent - ensure correct use of 'before' and 'after' keywords"
        elif ':' in input_range or '::' in input_range:
            return "Event scoping is context-dependent - verify correct use of ':' vs '::' for event scope"
        elif 'ref' in input_lower:
            return "Reference syntax is context-dependent - ensure the referenced action exists in the correct scope"

        return "The meaning of this syntax depends on surrounding context - consider making it more explicit"
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
        errors were encountered during the process. It filters out cascading errors
        to provide clearer diagnostics.

        :raises GrammarParseError: If any errors were collected during parsing,
            with detailed error messages.
        """
        if self.errors:
            # Filter out cascading errors to provide clearer diagnostics
            filtered_errors = self._filter_cascading_errors(self.errors)
            raise GrammarParseError(filtered_errors)

    @staticmethod
    def _filter_cascading_errors(errors: List[GrammarItemError]) -> List[GrammarItemError]:
        """
        Filter out cascading errors that are likely caused by earlier syntax errors.

        This method identifies and removes secondary errors that occur as a result
        of the parser's error recovery mechanism, keeping only the root cause errors.

        :param errors: List of all collected errors.
        :type errors: List[GrammarItemError]
        :return: Filtered list containing only primary errors.
        :rtype: List[GrammarItemError]
        """
        if not errors:
            return errors

        # Only filter SyntaxFailError instances
        syntax_errors = [e for e in errors if isinstance(e, SyntaxFailError)]
        other_errors = [e for e in errors if not isinstance(e, SyntaxFailError)]

        if len(syntax_errors) <= 1:
            return errors

        # Sort errors by line and column
        syntax_errors.sort(key=lambda e: (e.line, e.column))

        # Classify errors
        primary_errors = []
        cascading_errors = []

        for error in syntax_errors:
            # Primary errors are those that indicate a missing syntax element
            is_primary = (
                "missing ';'" in error.msg or
                "missing ']'" in error.msg or
                "missing '}'" in error.msg or
                "missing '{'" in error.msg or
                "missing '['" in error.msg or
                "missing '->'" in error.msg or
                "missing '='" in error.msg or
                "token recognition error" in error.msg
            )

            if is_primary:
                primary_errors.append(error)
            else:
                cascading_errors.append(error)

        # Filter cascading errors based on proximity to primary errors
        filtered = list(primary_errors)  # Always keep all primary errors

        for cascading in cascading_errors:
            # Check if this cascading error is likely caused by a nearby primary error
            is_likely_cascading = False

            for primary in primary_errors:
                # If there's a primary error within 5 lines before this cascading error
                line_diff = cascading.line - primary.line
                if 0 < line_diff <= 5:
                    # This is likely a cascading error caused by the primary error
                    is_likely_cascading = True
                    break

            # Only keep cascading errors that don't have a nearby primary cause
            if not is_likely_cascading:
                filtered.append(cascading)

        # Add back non-syntax errors
        filtered.extend(other_errors)

        # Sort by line number for better readability
        filtered.sort(key=lambda e: (e.line if isinstance(e, SyntaxFailError) else 0,
                                     e.column if isinstance(e, SyntaxFailError) else 0))

        return filtered
