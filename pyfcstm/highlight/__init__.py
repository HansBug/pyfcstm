"""
Syntax highlighting package for the FCSTM DSL.

This package exposes Pygments lexer support for the FCSTM (Finite State
Machine) domain-specific language. It provides a public entry point to the
lexer implementation used by syntax highlighting tools and editors.

The package contains the following main components:

* :class:`pyfcstm.highlight.pygments_lexer.FcstmLexer` - Pygments lexer for FCSTM

Example::

    >>> from pyfcstm.highlight import FcstmLexer
    >>> lexer = FcstmLexer()
    >>> lexer.name
    'FCSTM'

"""

from .pygments_lexer import FcstmLexer

__all__ = ['FcstmLexer']
