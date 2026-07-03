.. _sec-explanations-grammar-tooling:

Grammar tooling explanation
===========================

FCSTM syntax support is deliberately multi-layered. The ANTLR grammar defines
parseable syntax, the listener turns parse trees into repository AST nodes, and
separate highlighters make the same syntax readable in documentation and
editors.

Why several files must move together
------------------------------------

A grammar change is not complete when the ``.g4`` file parses. Users also see
syntax through examples, Sphinx code blocks, VSCode highlighting, and JavaScript
editor tooling. If these layers drift, a model may parse correctly while docs or
editors still teach the old syntax.

The maintenance rule is therefore:

* Parser grammar defines what is valid.
* Listener and AST nodes define what the Python model can import.
* Pygments and TextMate define how humans see the syntax.
* Editor validation checks that the editor-facing assets remain aligned.
* DSL docs and tests define what users can rely on.

Pygments and TextMate roles
---------------------------

Pygments serves Python and documentation contexts. It lets Sphinx, terminal
formatters, notebooks, and other Python tools display FCSTM snippets without
running the model importer. TextMate grammar serves editor highlighting contexts.
It is intentionally lighter than the parser: it should classify text clearly,
but it should not become a second semantic validator.

This is why examples that only need highlighting can stay in documentation or
editor tooling, while semantic examples belong in parser, model, simulator, or
verification tests.

VSCode role
-----------

The VSCode extension combines TextMate highlighting with parser-backed authoring
features such as diagnostics, document symbols, completion, hover help, snippets,
and preview support. It is an authoring aid, not the canonical execution engine.
When a syntax change affects both parseability and editor feedback, update the
Python grammar/model path first, then synchronize editor diagnostics and
completion so users see the same language that the parser accepts.

Parser and listener boundary
----------------------------

ANTLR generated files should not contain hand-written behavior. Repository logic
belongs in listener, node, model, or validation code. This keeps regeneration
safe: ``make antlr_build`` may rewrite generated parser outputs without losing
manual changes.

Highlighting boundary
---------------------

Syntax highlighting should follow grammar facts, not invent syntax. It is fine
for highlighters to be conservative around ambiguous text, but they should not
advertise keywords, operators, or block forms that the parser rejects.

Editor tooling boundary
-----------------------

The JavaScript and VSCode assets support authoring workflows. They should remain
independent from Python unit-test fixtures. When both sides need the same syntax
scenario, duplicate the minimal DSL example in the appropriate test tree instead
of making one side import the other's tests.

This separation keeps Python tests runnable without Node.js and keeps editor
tests runnable without the repository-level Python test tree.
