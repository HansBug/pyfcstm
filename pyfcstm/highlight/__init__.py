"""Syntax highlighting lexers for FCSTM languages.

The :mod:`pyfcstm.highlight` package exposes Pygments lexers used by Sphinx,
editor integrations, and command-line highlighting tools.  The lexers are
syntax highlighters only: they do not parse FCSTM models, bind BMC query paths,
or run semantic validation.

Public lexer roadmap:

.. list-table::
   :header-rows: 1

   * - Language surface
     - Public lexer
     - Purpose
   * - FCSTM model DSL
     - :class:`pyfcstm.highlight.pygments_lexer.FcstmLexer`
     - Highlight ``*.fcstm`` state-machine model files.
   * - FCSTM BMC Query
     - :class:`pyfcstm.highlight.bmc_query_lexer.FcstmBmcQueryLexer`
     - Highlight ``*.fbmcq`` bounded-model-checking query files.

Example::

    >>> from pyfcstm.highlight import FcstmBmcQueryLexer, FcstmLexer
    >>> FcstmLexer().name
    'FCSTM'
    >>> FcstmBmcQueryLexer().name
    'FCSTM BMC Query'
"""

from .bmc_query_lexer import FcstmBmcQueryLexer
from .pygments_lexer import FcstmLexer

__all__ = ["FcstmLexer", "FcstmBmcQueryLexer"]
