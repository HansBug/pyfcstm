"""
Compatibility shim for the generated parser listener class.

The parser grammar is now generated from ``GrammarParser.g4``, which produces
``GrammarParserListener.py``. Existing repository code imports
``pyfcstm.dsl.grammar.GrammarListener.GrammarListener``, so this module
re-exports the generated listener class under the historical name.
"""

from .GrammarParserListener import GrammarParserListener as GrammarListener

__all__ = ["GrammarListener"]
