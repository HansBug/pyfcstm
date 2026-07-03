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

Verify Python and Sphinx highlighting
-------------------------------------

For Python tools, confirm that the packaged Pygments entry point is visible:

.. code-block:: bash

   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

For Sphinx pages, prefer ``.. code-block:: fcstm`` examples and build the docs
in both languages when the visible documentation changes:

.. code-block:: bash

   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=en sphinx-build -b html docs/source /tmp/pyfcstm-docs-en
   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=zh sphinx-build -b html docs/source /tmp/pyfcstm-docs-zh

If a lexer alias stops working, check ``setup.py`` and ``docs/source/conf.py``
before changing examples.

Install and verify the VSCode extension
---------------------------------------

For a released package, install the downloaded ``.vsix`` file with:

.. code-block:: bash

   code --install-extension fcstm-language-support-0.1.0.vsix

For local development, build and install the package produced by the repository
Makefile:

.. code-block:: bash

   make vscode
   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

Verifying Installation: after installation, open a ``.fcstm`` file and verify these editor behaviors:

1. The bottom-right language mode is ``FCSTM``.
2. Keywords, operators, comments, and literals are highlighted.
3. The Outline view shows document symbols for states, variables, and events.
4. Typing ``state`` offers completions.
5. Hovering over keywords such as ``pseudo`` or ``effect`` shows help text.
6. A deliberately invalid file reports syntax diagnostics in the Problems panel.

Run VSCode verification suites
------------------------------

When the extension behavior changes, run the focused suites from
``editors/vscode`` before the aggregate check:

.. code-block:: bash

   cd editors/vscode
   make verify-p0.2  # parser integration
   make verify-p0.3  # syntax diagnostics
   make verify-p0.4  # document symbols
   make verify-p0.5  # completion support
   make verify-p0.6  # hover documentation
   make verify

For syntax-only documentation updates, it is acceptable to record that these
Node.js-backed checks were not run, but grammar or editor behavior changes should
not skip them silently.

Troubleshoot editor behavior
----------------------------

Use this checklist before changing grammar or editor code:

* If Sphinx highlighting fails, verify the ``fcstm`` lexer alias and reinstall
  the package in the environment that runs Sphinx.
* If TextMate highlighting fails, confirm that ``editors/fcstm.tmLanguage.json``
  was installed in the editor-specific package location and restart the editor.
* For Sublime Text, create a ``FCSTM`` package directory under
  ``Preferences -> Browse Packages`` and copy ``fcstm.tmLanguage.json`` there.
* VS Code Extension Not Working: confirm the extension is installed, the file
  extension is ``.fcstm``, and the language mode is ``FCSTM``.
* If diagnostics do not appear, save the file, check the Problems panel, and
  inspect the ``FCSTM Language Support`` output channel.
* If completion does not appear, trigger it manually with ``Ctrl+Space`` and
  check that the cursor is not inside a comment or string.

Document the change
-------------------

Syntax changes should update the user-facing DSL reference or how-to pages,
not just the grammar files. Maintenance-only changes should update the tooling
reference and explain whether generated assets were regenerated.

Before opening review, include the commands you ran and the syntax examples that
prove the grammar, highlighting, and editor assets agree.
