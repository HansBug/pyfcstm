.. _sec-how-to-grammar-editor:

Grammar and editor tasks
========================

Use this guide when changing FCSTM syntax, highlighting, or editor support. For
exact file maps and command lists, see :doc:`../../reference/grammar_tooling/index`.
For design rationale, see :doc:`../../explanations/grammar_tooling/index`.

Decide what kind of change this is
----------------------------------

.. list-table:: Change type
   :header-rows: 1

   * - Change
     - Must update
     - Usually also update
   * - New parseable syntax
     - ANTLR grammar, generated parser outputs, listener/AST/model import, tests, DSL docs.
     - Pygments, TextMate, VSCode diagnostics/completion/hover.
   * - New keyword or operator spelling
     - Lexer grammar, parser grammar when used in rules, highlighters, editor validation.
     - DSL reference examples and LLM grammar guide.
   * - New semantic interpretation of existing syntax
     - Model import/validation, simulator or renderer behavior, tests, semantic docs.
     - Editor diagnostics if authoring feedback changes.
   * - Highlighting-only correction
     - Pygments or TextMate assets, editor validation.
     - Documentation examples when they taught the wrong form.
   * - VSCode authoring feature change
     - VSCode TypeScript providers and focused verification suite.
     - TextMate grammar if the feature depends on token classification.

Change parser grammar
---------------------

1. Edit ``pyfcstm/dsl/grammar/GrammarParser.g4`` and/or
   ``pyfcstm/dsl/grammar/GrammarLexer.g4``.
2. Regenerate ANTLR outputs:

   .. code-block:: bash

      make antlr_build

3. Update ``pyfcstm/dsl/listener.py`` and ``pyfcstm/dsl/node.py`` when parse
   tree shape or AST node shape changes.
4. Update model import and validation if the construct has semantic meaning.
5. Add tests that prove both accepted and rejected forms.
6. Update user-facing DSL docs and the packaged LLM grammar guide when prompt
   or user syntax changes.

Operator and keyword ordering
-----------------------------

When adding operators, keep longer tokens before shorter prefixes in lexer and
highlighting rules. Examples:

* ``**`` before ``*``;
* ``<<`` before ``<``;
* ``<=`` and ``>=`` before ``<`` and ``>``;
* ``==`` and ``!=`` before ``=`` and ``!``;
* ``&&`` and ``||`` before single-character forms.

When adding keywords, update the grammar and all syntax display layers in the
same change. A keyword that parses but does not highlight creates documentation
and editor drift.

Synchronize highlighting
------------------------

After grammar or keyword changes, update both highlighter families:

1. ``pyfcstm/highlight/pygments_lexer.py`` for Sphinx and Python-side
   highlighting.
2. ``editors/fcstm.tmLanguage.json`` for TextMate-compatible editors.
3. Run the editor/highlight validation command:

   .. code-block:: bash

      python editors/validate.py

If a docs-only PR does not run the editor command, say that explicitly in the PR
comment. Grammar or editor behavior changes should not skip it silently.

Update VSCode support
---------------------

Inspect ``editors/vscode/`` when authoring behavior changes. Typical places are:

* ``src/diagnostics.ts`` for syntax diagnostics and Problems-panel feedback;
* ``src/symbols.ts`` for Outline and breadcrumbs;
* ``src/completion.ts`` for keyword and symbol completion;
* ``src/hover.ts`` for hover explanations;
* ``snippets/fcstm.code-snippets`` for user snippets.

Build the extension package when packaging behavior matters:

.. code-block:: bash

   make vscode

Use ``make vscode_clean`` only when cleaning local extension build outputs.

Verify Python and Sphinx highlighting
-------------------------------------

For Python tools, confirm the Pygments alias is visible:

.. code-block:: bash

   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

For Sphinx pages, use ``.. code-block:: fcstm`` examples and build the docs in
both languages when visible documentation changes:

.. code-block:: bash

   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=en sphinx-build -b html docs/source /tmp/pyfcstm-docs-en
   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=zh sphinx-build -b html docs/source /tmp/pyfcstm-docs-zh

If highlighting fails in Sphinx, check ``setup.py`` and ``docs/source/conf.py``
before changing examples.

Install and verify the VSCode extension
---------------------------------------

For local development, build and install the package produced by the Makefile:

.. code-block:: bash

   make vscode
   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

After installation, open a ``.fcstm`` file and verify:

1. The bottom-right language mode is ``FCSTM``.
2. Keywords, operators, comments, and literals are highlighted.
3. Outline shows variables, states, and events.
4. Typing ``state`` offers completions.
5. Hovering over keywords such as ``pseudo`` or ``effect`` shows help text.
6. A deliberately invalid file reports syntax diagnostics in Problems.

Run VSCode verification suites
------------------------------

When extension behavior changes, run focused suites before the aggregate check:

.. code-block:: bash

   cd editors/vscode
   make verify-p0.2  # parser integration
   make verify-p0.3  # syntax diagnostics
   make verify-p0.4  # document symbols
   make verify-p0.5  # completion support
   make verify-p0.6  # hover documentation
   make verify

Syntax-only documentation updates may record that Node.js-backed checks were
not run, but parser/editor changes should include the relevant suites.

Update prompt-facing grammar guide
----------------------------------

When syntax or parse rules change, update the packaged LLM grammar guide:

.. code-block:: bash

   make sha256
   SKIP_SLOW_TESTS=1 make unittest RANGE_DIR=./llm

Commit the Markdown guide and checksum together. If the grammar guide did not
change, record why it was outside the change scope.

Document and review the change
------------------------------

Before review, include:

* the syntax forms added, changed, or deliberately rejected;
* parser/model tests or docs-only validation rationale;
* highlighter and editor validation commands;
* generated parser or documentation outputs that were regenerated;
* any old examples that were removed or redirected.

A grammar change is ready only when parser behavior, model semantics,
highlighting, editor feedback, user docs, and tests all tell the same story.
