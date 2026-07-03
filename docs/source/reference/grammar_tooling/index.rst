.. _sec-reference-grammar-tooling:

Grammar and editor tooling reference
====================================

This page is a facts-only map for FCSTM grammar, syntax highlighting, and editor
maintenance. For the update workflow, see :doc:`../../how_to/grammar_editor/index`.
For design rationale, see :doc:`../../explanations/grammar_tooling/index`.

Canonical files
---------------

.. list-table:: Grammar and editor files
   :header-rows: 1

   * - Area
     - Path
     - Notes
   * - Parser grammar
     - ``pyfcstm/dsl/grammar/GrammarParser.g4``
     - Canonical parser rules for FCSTM DSL syntax.
   * - Lexer grammar
     - ``pyfcstm/dsl/grammar/GrammarLexer.g4``
     - Canonical tokens, keywords, literals, and operators.
   * - Python parser output
     - ``pyfcstm/dsl/grammar/``
     - Generated ANTLR Python files; regenerate with ``make antlr_build``.
   * - DSL listener
     - ``pyfcstm/dsl/listener.py``
     - Converts parse events into AST nodes.
   * - DSL AST nodes
     - ``pyfcstm/dsl/node.py``
     - Syntax tree dataclasses and export helpers.
   * - Pygments lexer
     - ``pyfcstm/highlight/pygments_lexer.py``
     - Documentation and Python-side syntax highlighting.
   * - TextMate grammar
     - ``editors/fcstm.tmLanguage.json``
     - Shared editor highlighting grammar.
   * - Editor validation
     - ``editors/validate.py``
     - Repository validation command for editor/highlight assets.
   * - JavaScript frontend
     - ``editors/jsfcstm/``
     - JavaScript parser/runtime assets for editor integrations.
   * - VSCode extension
     - ``editors/vscode/``
     - VSCode packaging and extension integration.

Core commands
-------------

.. list-table:: Maintenance commands
   :header-rows: 1

   * - Command
     - Purpose
   * - ``make antlr``
     - Download/setup ANTLR support when needed.
   * - ``make antlr_build``
     - Regenerate parser outputs after editing ``GrammarParser.g4`` or
       ``GrammarLexer.g4``.
   * - ``python editors/validate.py``
     - Validate syntax highlighting and editor asset consistency.
   * - ``make vscode``
     - Build the VSCode extension package.
   * - ``make vscode_clean``
     - Remove VSCode extension build artifacts.

Operator ordering facts
-----------------------

Lexer patterns and highlighters should put multi-character operators before
single-character operators. Examples include ``**`` before ``*``, ``<<`` before
``<``, ``<=`` before ``<``, ``>=`` before ``>``, ``==`` before ``=``, ``!=``
before ``!``, and ``&&`` / ``||`` before their single-character prefixes.

Keyword update checklist
------------------------

When syntax changes add a keyword or operator, update these facts together:

1. ANTLR grammar files under ``pyfcstm/dsl/grammar/``.
2. Parser outputs via ``make antlr_build``.
3. Listener and AST handling when parse tree shape changes.
4. Pygments lexer groups.
5. TextMate grammar keyword/operator patterns.
6. Editor validation expectations.
7. DSL guide and tests when user-facing syntax changes.

Do not document a generated parser path as the source of truth. The ``.g4``
files are the source; generated parser files are outputs.
