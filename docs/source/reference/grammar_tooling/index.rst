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

Pygments and Sphinx facts
-------------------------

The package registers :class:`pyfcstm.highlight.pygments_lexer.FcstmLexer`
through the ``pygments.lexers`` entry point in ``setup.py``. The canonical alias
is ``fcstm``; ``fcsm`` is also accepted by the lexer. Programmatic users can load
it with:

.. code-block:: python

   from pygments.lexers import get_lexer_by_name

   lexer = get_lexer_by_name("fcstm")

The documentation build also registers the lexer in ``docs/source/conf.py`` and
uses ``fcstm`` code blocks for examples. If Sphinx highlighting fails, check the
installed package entry point and the docs configuration before editing example
source.

TextMate and editor facts
-------------------------

The repository TextMate grammar is ``editors/fcstm.tmLanguage.json``. It is the
source for TextMate-compatible editor highlighting and is copied into the VSCode
extension's ``syntaxes/`` area during extension packaging.

For Sublime Text Integration, place the same file under a package directory such
as ``FCSTM`` in ``Preferences -> Browse Packages``.

VSCode extension facts
----------------------

The VSCode extension lives under ``editors/vscode/``. Its package manifest is
``package.json``; language configuration is ``language-configuration.json``;
TypeScript providers live under ``src/``; bundled output lives under ``dist/``;
and local packages are written under ``build/`` as ``.vsix`` files.

The extension provides these editor-facing capabilities:

.. list-table:: VSCode feature map
   :header-rows: 1

   * - Capability
     - Representative files
     - User-visible behavior
   * - Syntax diagnostics
     - ``src/diagnostics.ts``
     - Problems-panel diagnostics and inline squiggles.
   * - Document symbols
     - ``src/symbols.ts``
     - Outline and breadcrumb navigation for variables, states, and events.
   * - Completion
     - ``src/completion.ts``
     - IntelliSense for keywords, constants, built-ins, and document-local
       symbols.
   * - Hover Documentation
     - ``src/hover.ts``
     - Contextual help for event scopes, pseudo states, lifecycle keywords, and
       aspect syntax.
   * - Code Snippets
     - ``snippets/fcstm.code-snippets``
     - Short prefixes for common variable, state, transition, and lifecycle
       patterns.

Local VSIX installation uses the standard VSCode command-line interface:

.. code-block:: bash

   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

Verification command families
-----------------------------

The VSCode Makefile exposes focused suites as well as the aggregate
``make verify`` target. Current focused suites include:

.. list-table:: VSCode verification suites
   :header-rows: 1

   * - Command
     - Focus
   * - ``make verify-p0.2``
     - Parser integration.
   * - ``make verify-p0.3``
     - Syntax diagnostics.
   * - ``make verify-p0.4``
     - Document symbols.
   * - ``make verify-p0.5``
     - Completion support.
   * - ``make verify-p0.6``
     - Hover documentation.
   * - ``make verify``
     - Aggregate extension verification, including newer semantic, import,
       preview, and end-to-end checks.

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
