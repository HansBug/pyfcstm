"""
Grammar parsing utilities for the pyfcstm domain-specific language.

This module provides helper functions for parsing grammar-based input text using
ANTLR4-generated lexer/parser classes and a parse-tree listener that converts
ANTLR parse trees into internal node objects. It centralizes the parsing workflow
for different grammar entry points and exposes convenience functions for parsing
common DSL constructs such as conditions, preamble programs, and operation programs.

The module contains the following main components:

* :func:`parse_with_grammar_entry` - Parse text using an arbitrary grammar entry rule.
* :func:`parse_condition` - Parse a condition expression.
* :func:`parse_state_machine_dsl` - Parse a complete state machine DSL document.
* :func:`parse_preamble` - Parse a preamble program.
* :func:`parse_operation` - Parse an operation program.

.. note::
   All parsing relies on the ANTLR4-generated classes from
   :mod:`pyfcstm.dsl.grammar` and may raise :exc:`pyfcstm.dsl.error.GrammarParseError`
   when input does not conform to the grammar.

Example::

    >>> from pyfcstm.dsl.parse import parse_condition, parse_preamble
    >>> condition = parse_condition("x > 5 && y < 10")
    >>> preamble = parse_preamble("x := 10;")
"""

import os
from typing import Any, Callable, Optional

from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker

from .error import CollectingErrorListener
from .grammar import GrammarParser, GrammarLexer
from .listener import GrammarParseListener
from .node import StateMachineDSLProgram


def _parse_as_element(
    input_text: str,
    fn_element: Callable[[GrammarParser], Any],
    force_finished: bool = True,
) -> Any:
    """
    Parse input text using a specified parser entry method.

    This internal helper consolidates the ANTLR parsing workflow:
    it builds the lexer, parser, and parse tree, collects errors via
    :class:`~pyfcstm.dsl.error.CollectingErrorListener`, and walks the parse
    tree with :class:`~pyfcstm.dsl.listener.GrammarParseListener` to obtain
    the resulting node for the root parse tree.

    :param input_text: The text to parse.
    :type input_text: str
    :param fn_element: Parser method corresponding to the grammar entry rule.
    :type fn_element: Callable[[GrammarParser], Any]
    :param force_finished: Whether to enforce that parsing consumed all input,
        defaults to ``True``.
    :type force_finished: bool, optional
    :return: Parsed node for the grammar entry.
    :rtype: Any
    :raises pyfcstm.dsl.error.GrammarParseError: If any parsing or lexical error
        occurs, or if input is left unparsed when ``force_finished`` is ``True``.
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


def parse_with_grammar_entry(
    input_text: str, entry_name: str, force_finished: bool = True
) -> Any:
    """
    Parse input text using a specified grammar entry point.

    This function looks up a parser method on :class:`~pyfcstm.dsl.grammar.GrammarParser`
    by name and parses the provided input text using that rule.

    :param input_text: The text to parse.
    :type input_text: str
    :param entry_name: Name of the grammar rule to use as the entry point.
    :type entry_name: str
    :param force_finished: Whether to enforce that parsing consumed all input,
        defaults to ``True``.
    :type force_finished: bool, optional
    :return: Parsed node for the grammar entry.
    :rtype: Any
    :raises AttributeError: If ``entry_name`` does not exist on
        :class:`~pyfcstm.dsl.grammar.GrammarParser`.
    :raises pyfcstm.dsl.error.GrammarParseError: If parsing fails or input is left
        unparsed when ``force_finished`` is ``True``.

    Example::

        >>> result = parse_with_grammar_entry("x > 5", "condition")
    """
    return _parse_as_element(
        input_text=input_text,
        fn_element=getattr(GrammarParser, entry_name),
        force_finished=force_finished,
    )


def parse_condition(input_text: str) -> Any:
    """
    Parse input text as a condition expression.

    This function uses the grammar's ``condition`` rule as the entry point.

    :param input_text: The condition expression to parse.
    :type input_text: str
    :return: Parsed condition node.
    :rtype: Any
    :raises pyfcstm.dsl.error.GrammarParseError: If parsing fails.

    Example::

        >>> condition_node = parse_condition("x > 5 && y < 10")
    """
    return parse_with_grammar_entry(input_text, "condition")


def parse_state_machine_dsl(
    input_text: str,
    path: Optional[str] = None,
) -> StateMachineDSLProgram:
    """
    Parse input text as a complete state machine DSL document.

    This helper uses the grammar's ``state_machine_dsl`` rule and optionally
    attaches a source path string to the returned
    :class:`pyfcstm.dsl.node.StateMachineDSLProgram` node for later assembly
    phases.

    :param input_text: The state machine DSL text to parse.
    :type input_text: str
    :param path: Optional source path associated with the parsed document.
        When provided, the value is normalized via :func:`os.fspath` and stored
        on the returned AST node as ``source_path``.
    :type path: Optional[str]
    :return: Parsed state machine DSL program node.
    :rtype: StateMachineDSLProgram
    :raises pyfcstm.dsl.error.GrammarParseError: If parsing fails.

    Example::

        >>> program = parse_state_machine_dsl("state Root;", path="root.fcstm")
        >>> program.source_path
        'root.fcstm'
    """
    program = parse_with_grammar_entry(input_text, "state_machine_dsl")
    if not isinstance(program, StateMachineDSLProgram):
        raise TypeError(
            "Expected 'state_machine_dsl' to produce StateMachineDSLProgram, "
            f"got {type(program)!r}."
        )

    program.source_path = os.fspath(path) if path is not None else None
    return program


def parse_preamble(input_text: str) -> Any:
    """
    Parse input text as a preamble program.

    This function uses the grammar's ``preamble_program`` rule as the entry point.

    :param input_text: The preamble program text to parse.
    :type input_text: str
    :return: Parsed preamble program node.
    :rtype: Any
    :raises pyfcstm.dsl.error.GrammarParseError: If parsing fails.

    Example::

        >>> preamble_node = parse_preamble("x := 10;")
    """
    return parse_with_grammar_entry(input_text, "preamble_program")


def parse_operation(input_text: str) -> Any:
    """
    Parse input text as an operation program.

    This function uses the grammar's ``operation_program`` rule as the entry point.

    :param input_text: The operation program text to parse.
    :type input_text: str
    :return: Parsed operation program node.
    :rtype: Any
    :raises pyfcstm.dsl.error.GrammarParseError: If parsing fails.

    Example::

        >>> operation_node = parse_operation("x := 10;")
    """
    return parse_with_grammar_entry(input_text, "operation_program")
