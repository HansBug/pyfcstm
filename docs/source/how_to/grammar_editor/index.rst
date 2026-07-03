.. _sec-how-to-grammar-editor:

Grammar and editor tasks
========================

Use this guide when changing FCSTM syntax, syntax highlighting, or editor
support. For exact file paths, see :doc:`../../reference/grammar_tooling/index`.

Change grammar syntax
---------------------

1. Edit ``pyfcstm/dsl/grammar/GrammarParser.g4`` or
   ``pyfcstm/dsl/grammar/GrammarLexer.g4``.
2. Run the ANTLR generator:

   .. code-block:: bash

      make antlr_build

3. Update ``pyfcstm/dsl/listener.py`` and ``pyfcstm/dsl/node.py`` if the parse
   tree shape changed.
4. Add or update parser/model tests for the syntax change.
5. Update the LLM grammar guide when prompt-facing syntax changes.

Change highlighting
-------------------

After grammar changes, keep highlighters in sync:

1. Update ``pyfcstm/highlight/pygments_lexer.py`` for Python/Sphinx highlighting.
2. Update ``editors/fcstm.tmLanguage.json`` for TextMate-compatible editors.
3. Put multi-character operators before shorter prefixes.
4. Run:

   .. code-block:: bash

      python editors/validate.py

The validation command is the repository-level check for editor/highlight asset
consistency. If you only document a workflow and do not run a tool in a docs-only
PR, say so in the PR comment.

Update the VSCode extension
---------------------------

When editor behavior changes, inspect ``editors/vscode/`` and the JavaScript
frontend under ``editors/jsfcstm/``. Build the extension package with:

.. code-block:: bash

   make vscode

Use ``make vscode_clean`` when cleaning local extension build outputs.

Document the change
-------------------

Syntax changes should update the user-facing DSL reference or how-to pages,
not just the grammar files. Maintenance-only changes should update the tooling
reference and explain whether generated assets were regenerated.

Before opening review, include the commands you ran and the syntax examples that
prove the grammar, highlighting, and editor assets agree.
