import os

from antlr4.error.ErrorListener import ErrorListener


class CollectingErrorListener(ErrorListener):
    """Collects all errors during ANTLR parsing process and throws them collectively after parsing is complete"""

    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """Handle syntax errors"""
        error_location = f"line {line}, column {column}"

        # Try to get more context information
        ctx_info = ""
        if offendingSymbol:
            ctx_info = f", near '{offendingSymbol.text}'"

        error_msg = f"Syntax error at {error_location}{ctx_info}: {msg}"
        self.errors.append(error_msg)

    def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        """Handle grammar ambiguity"""
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)

        error_msg = f"Grammar ambiguity at input '{input_range}' (from index {startIndex} to {stopIndex})."
        self.errors.append(error_msg)

    def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
        """Handle attempts at full context parsing"""
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)

        error_msg = f"Parser attempting full context interpretation at input '{input_range}' " \
                    f"(from index {startIndex} to {stopIndex})."
        self.errors.append(error_msg)

    def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
        """Handle context sensitivity issues"""
        tokens = recognizer.getTokenStream()
        input_range = tokens.getText(startIndex, stopIndex)

        error_msg = f"Context sensitivity at input '{input_range}' (from index {startIndex} to {stopIndex})."
        self.errors.append(error_msg)

    def check_errors(self):
        """Check if there are errors and throw an exception if any exist"""
        if self.errors:
            error_report = os.linesep.join([f"Error {i + 1}: {error}" for i, error in enumerate(self.errors)])
            raise Exception(f"Found {len(self.errors)} errors during parsing:{os.linesep}{error_report}")
