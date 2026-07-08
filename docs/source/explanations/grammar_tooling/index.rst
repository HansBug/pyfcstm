.. _sec-explanations-grammar-tooling:

Grammar tooling explanation
===========================

FCSTM syntax support is deliberately multi-layered. ANTLR defines parseable
syntax, listener code turns parse trees into repository AST nodes, model import
gives those nodes semantic meaning, and separate highlighters/editors make the
same syntax usable in documents and authoring tools.

Why one syntax change touches several layers
--------------------------------------------

A grammar change is not complete when a ``.g4`` file accepts new text. Users see
syntax through command errors, model diagnostics, rendered documentation, VSCode
highlighting, completion suggestions, hover text, snippets, and LLM-facing
prompts. If one layer is updated and another layer is stale, the project teaches
contradictory language rules.

The maintenance invariant is therefore:

* grammar decides what can parse;
* listener and AST nodes decide what syntax shape is represented;
* model import decides what the syntax means;
* diagnostics decide how invalid or risky forms are explained;
* Pygments and TextMate decide how humans visually recognize syntax;
* editor features decide how authors discover and repair syntax while typing;
* documentation and tests decide what users can rely on.

Parser grammar versus semantic model
------------------------------------

The parser should remain a syntactic recognizer. It can reject malformed token
orders and missing punctuation, but it should not own every semantic rule. For
example, resolving whether a transition target exists depends on the state tree,
so that belongs in model import and validation rather than in a parser rule.

This separation keeps grammar readable and makes diagnostics more useful:
syntax errors can point to malformed text, while semantic diagnostics can point
to resolved model facts such as duplicate states, illegal transitions, or
unresolved references.

Generated parser boundary
-------------------------

ANTLR-generated files are regeneration outputs. Hand-editing them creates a
fork that disappears on the next ``make antlr_build``. Manual behavior belongs
in listener, node, model, diagnostics, or editor code. This makes regeneration a
safe maintenance step instead of a risky rewrite.

Highlighting is not validation
------------------------------

Pygments and TextMate highlighters classify text for human readability. They
should track grammar facts, but they should not become a second parser. A
highlighter may conservatively color ambiguous text; it must not advertise a
keyword, operator, or block form that the parser rejects.

The practical rule is: highlighters help a reader see the structure, while
parser/model tests prove that the structure is accepted and meaningful.

Why Pygments and TextMate both exist
------------------------------------

Pygments serves Python and documentation contexts: Sphinx pages, terminal
formatters, notebooks, and other Python tools. TextMate serves editor contexts:
VSCode and other TextMate-compatible editors. Their consumers and syntax formats
are different, so both need explicit maintenance even when they represent the
same language.

VSCode role
-----------

The VSCode extension combines TextMate highlighting with parser-backed and
metadata-backed authoring features: diagnostics, symbols, completion, hover,
snippets, and preview support. It is an authoring aid, not the canonical runtime
or model importer. When VSCode disagrees with Python parsing, Python grammar and
model behavior remain authoritative, but the editor must be fixed so authors do
not learn the wrong language.

Documentation and LLM guide role
--------------------------------

User documentation explains the supported language in four roles: tutorial,
how-to, explanation, and reference. The packaged LLM grammar guide is a compact
prompt-facing grammar source. Syntax changes that matter to users should update
both the human docs and the prompt-facing guide so human readers and LLM repair
flows receive the same rule set.

Test boundary rationale
-----------------------

Python and JavaScript/editor tests stay independent. If both sides need the same
syntax scenario, duplicate the minimal DSL fixture in each side's own test tree.
This avoids a Python unit test depending on Node.js and avoids a JavaScript
editor test depending on repository-level Python fixtures.

Drift examples
--------------

.. list-table:: Common drift patterns
   :header-rows: 1

   * - Drift
     - Why it is harmful
     - Correct response
   * - Parser accepts a new keyword but highlighters do not color it.
     - Documentation and editor views make valid syntax look suspicious or plain.
     - Update Pygments, TextMate, and editor validation.
   * - Highlighter advertises an operator the parser rejects.
     - Users copy examples that cannot parse.
     - Remove or correct the highlighter pattern and add a negative example if needed.
   * - VSCode completion suggests a syntax form that model import rejects.
     - Authors receive false confidence before command-line validation fails.
     - Update completion and diagnostics to match parser/model behavior.
   * - LLM guide omits a new syntax form.
     - LLM-assisted repair keeps generating older or incomplete DSL.
     - Update the guide and checksum with the syntax docs.
   * - Generated parser output is edited by hand.
     - The fix is lost at the next regeneration.
     - Move behavior to source files and regenerate outputs.

Completion standard
-------------------

A grammar/tooling change is complete when each affected surface tells the same
story:

1. the grammar parses the intended syntax;
2. AST/model import represents the intended meaning;
3. diagnostics reject invalid forms with useful messages;
4. highlighters and editor tooling recognize the visible syntax;
5. user docs and the LLM guide teach the same rule;
6. tests or explicit validation commands cover the changed surfaces.
