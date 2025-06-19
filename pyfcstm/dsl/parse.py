"""
Grammar parsing module for processing and interpreting grammar-based input text.

This module provides functions to parse input text according to grammar rules defined
in the GrammarParser. It uses ANTLR4 for lexical analysis and parsing, and provides
specialized functions for parsing different grammar elements like conditions, preambles,
and operations.
"""

from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker

from .error import CollectingErrorListener
from .grammar import GrammarParser, GrammarLexer
from .listener import GrammarParseListener


def _parse_as_element(input_text, fn_element, force_finished: bool = True):
    """
    Parse input text using the specified grammar element function.

    This internal function handles the common parsing logic for all grammar elements,
    including error handling and parse tree walking.

    :param input_text: The text to parse
    :type input_text: str

    :param fn_element: The parser function to use for parsing
    :type fn_element: callable

    :param force_finished: Whether to check if parsing consumed all input
    :type force_finished: bool

    :return: The parsed node representation of the input
    :rtype: object

    :raises: Various parsing errors if the input doesn't match the grammar
    """
    error_listener = CollectingErrorListener()

    input_stream = InputStream(input_text)
    lexer = GrammarLexer(input_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    stream = CommonTokenStream(lexer)
    parser = GrammarParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    parse_tree = fn_element(parser)
    if force_finished:
        error_listener.check_unfinished_parsing_error(stream)
    error_listener.check_errors()

    listener = GrammarParseListener()
    walker = ParseTreeWalker()
    walker.walk(listener, parse_tree)
    return listener.nodes[parse_tree]


def parse_with_grammar_entry(input_text: str, entry_name: str, force_finished: bool = True):
    """
    Parse input text using a specified grammar entry point.

    This function allows parsing with any entry point in the grammar by name.

    :param input_text: The text to parse
    :type input_text: str

    :param entry_name: The name of the grammar rule to use as entry point
    :type entry_name: str

    :param force_finished: Whether to check if parsing consumed all input
    :type force_finished: bool

    :return: The parsed node representation of the input
    :rtype: object

    :raises: Various parsing errors if the input doesn't match the grammar

    Example::

        >>> result = parse_with_grammar_entry("x > 5", "condition")
    """
    return _parse_as_element(
        input_text=input_text,
        fn_element=getattr(GrammarParser, entry_name),
        force_finished=force_finished
    )


def parse_condition(input_text: str):
    """
    Parse input text as a condition expression.

    This function specifically parses conditional expressions according to
    the grammar's condition rule.

    :param input_text: The condition text to parse
    :type input_text: str

    :return: The parsed condition node
    :rtype: object

    :raises: Various parsing errors if the input doesn't match the condition grammar

    Example::

        >>> condition_node = parse_condition("x > 5 && y < 10")
    """
    return parse_with_grammar_entry(input_text, 'condition')


def parse_preamble(input_text: str):
    """
    Parse input text as a preamble program.

    This function specifically parses preamble programs according to
    the grammar's preamble_program rule.

    :param input_text: The preamble program text to parse
    :type input_text: str

    :return: The parsed preamble program node
    :rtype: object

    :raises: Various parsing errors if the input doesn't match the preamble grammar

    Example::

        >>> preamble_node = parse_preamble("x = 10;")
    """
    return parse_with_grammar_entry(input_text, 'preamble_program')


def parse_operation(input_text: str):
    """
    Parse input text as an operation program.

    This function specifically parses operation programs according to
    the grammar's operation_program rule.

    :param input_text: The operation program text to parse
    :type input_text: str

    :return: The parsed operation program node
    :rtype: object

    :raises: Various parsing errors if the input doesn't match the operation grammar

    Example::

        >>> operation_node = parse_operation("x := 10;")
    """
    return parse_with_grammar_entry(input_text, 'operation_program')
