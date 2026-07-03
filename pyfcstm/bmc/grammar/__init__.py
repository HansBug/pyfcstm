"""Generated ANTLR grammar package for FCSTM BMC Query files.

The source ``.g4`` grammars and generated lexer/parser modules in this package
are maintained through ``make fbmcq_antlr_build``. Hand-written code should import
these modules only for grammar-level parsing; semantic AST construction belongs
to later BMC parser layers.

Package contents:

.. list-table::
   :header-rows: 1

   * - File family
     - Owner
     - Purpose
   * - ``BmcQueryLexer.g4`` and ``BmcQueryParser.g4``
     - Hand-written grammar source
     - Define the ``.fbmcq`` lexer, parser, query entry, and expression entry
       rules.
   * - ``BmcQueryLexer.py``, ``BmcQueryParser.py``, listener, tokens, and
       interp files
     - ``make fbmcq_antlr_build``
     - Generated ANTLR artifacts committed for runtime use and packaging.
   * - ``__init__.py``
     - Hand-written package marker
     - Documents the generation boundary without importing generated modules.

Example::

    >>> from pyfcstm.bmc.grammar.BmcQueryLexer import BmcQueryLexer
    >>> BmcQueryLexer.grammarFileName
    'BmcQueryLexer.g4'
"""
