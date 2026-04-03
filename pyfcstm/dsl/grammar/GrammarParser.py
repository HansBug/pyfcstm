"""
Compatibility shim for the generated parser class.

The ANTLR split-grammar layout emits the parser implementation into
``Grammar.py``. Existing repository code imports
``pyfcstm.dsl.grammar.GrammarParser.GrammarParser``, so this module re-exports
the generated parser class under the historical name.
"""

from .Grammar import Grammar as GrammarParser

__all__ = ["GrammarParser"]
