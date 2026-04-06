"""
pyfcstm DSL package initialization and public API exports.

This package aggregates the public interface for the pyfcstm domain-specific
language (DSL). It re-exports parser entry points, grammar nodes, error
types, and the parse tree listener so users can import them directly from
:mod:`pyfcstm.dsl`.

The module exposes the following public components:

* :class:`~pyfcstm.dsl.listener.GrammarParseListener` - Parse tree listener that
  builds AST nodes from the grammar.
* :func:`~pyfcstm.dsl.parse.parse_condition` - Parse a conditional expression.
* :func:`~pyfcstm.dsl.parse.parse_state_machine_dsl` - Parse a complete state
  machine DSL document.
* :func:`~pyfcstm.dsl.parse.parse_preamble` - Parse a preamble program.
* :func:`~pyfcstm.dsl.parse.parse_operation` - Parse an operation program.
* :func:`~pyfcstm.dsl.parse.parse_with_grammar_entry` - Parse using a specific
  grammar rule entry.
* Error classes from :mod:`pyfcstm.dsl.error`, including
  :class:`~pyfcstm.dsl.error.GrammarParseError` and
  :class:`~pyfcstm.dsl.error.GrammarItemError`.

The grammar nodes and parser definitions are re-exported via
:mod:`pyfcstm.dsl.grammar` and :mod:`pyfcstm.dsl.node`.

Example::

    >>> from pyfcstm.dsl import parse_condition, GrammarParseError
    >>> try:
    ...     node = parse_condition("x > 1 && y < 3")
    ... except GrammarParseError as exc:
    ...     print(exc)

"""

from .error import (
    CollectingErrorListener,
    GrammarItemError,
    GrammarParseError,
    SyntaxFailError,
    AmbiguityError,
    FullContextAttemptError,
    ContextSensitivityError,
)
from .grammar import *
from .listener import GrammarParseListener
from .node import *
from .parse import (
    parse_condition,
    parse_state_machine_dsl,
    parse_preamble,
    parse_operation,
    parse_with_grammar_entry,
)
