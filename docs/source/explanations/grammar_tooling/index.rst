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

Trace example: adding one keyword
---------------------------------

A one-word syntax change is not a one-file change. Suppose a new lifecycle-like
keyword were added. The safe reasoning path is:

1. Grammar decides whether the token can be parsed.
2. Listener and AST nodes decide where the parsed fact is stored.
3. Model import decides whether the fact has valid semantics.
4. Pygments and TextMate decide whether humans see the same token class.
5. VSCode decides whether authoring tools suggest, diagnose, and explain it.
6. Human docs and the LLM grammar guide decide whether readers and repair prompts
   learn the same rule.
7. Tests on each side prove the Python and JavaScript/editor boundaries without
   sharing test-only fixtures.

This is why the completion standard is deliberately broader than ``make
antlr_build``. Regeneration proves that generated parser code is current; it does
not prove semantic import, highlighting, editor behavior, or prompt guidance.

Mechanism trace: from syntax text to author feedback
----------------------------------------------------

The following trace shows why the documentation treats grammar tooling as a
pipeline rather than a collection of independent files. A syntax form such as a
guarded transition moves through several evidence boundaries before a user sees
it as reliable language support.

.. list-table:: Syntax-support trace
   :header-rows: 1

   * - Boundary
     - Example source fact
     - What passes through
     - What can fail here
     - Evidence that closes the boundary
   * - Tokenization.
     - ``GrammarLexer.g4`` operator and keyword rules.
     - Character sequences become tokens such as identifiers, comparison operators, and braces.
     - A longer operator can be split incorrectly when ordering is wrong.
     - Lexer/parser tests and regenerated parser output.
   * - Parse shape.
     - ``GrammarParser.g4`` transition, event, guard, and block rules.
     - Tokens become a parse tree with concrete rule names.
     - A form may parse too broadly, making a later diagnostic less precise.
     - Parser positive and negative examples.
   * - AST construction.
     - ``pyfcstm/dsl/listener.py`` and ``pyfcstm/dsl/node.py``.
     - Parse events become repository AST nodes with export behavior.
     - Listener code can drop a field even though the grammar accepted it.
     - AST round-trip or import tests.
   * - Semantic import.
     - ``pyfcstm/model/imports.py`` and model validation.
     - AST nodes become states, transitions, events, actions, and diagnostics.
     - Scope resolution, duplicate names, unresolved references, or illegal targets can fail.
     - Model tests, diagnostics examples, and inspect reports.
   * - Authoring display.
     - Pygments lexer, TextMate grammar, and VSCode providers.
     - The same syntax is colored, completed, diagnosed, and explained while editing.
     - Highlighting can teach a stale token; completion can suggest a form the parser rejects.
     - ``python editors/validate.py`` and focused VSCode verification.
   * - Human and prompt guidance.
     - User docs and ``pyfcstm/llm/fcstm_grammar_guide.md``.
     - The supported rule is presented to readers and repair prompts.
     - Examples can become stale even when code is correct.
     - Sphinx builds, Markdown/checksum updates, and example execution where relevant.

This trace also defines the troubleshooting order. If command-line parsing
rejects a file, fix grammar or model facts before touching highlighters. If the
parser accepts the file but VSCode marks it suspicious, treat the editor as
stale unless a fresh parser/model test proves otherwise.

Boundary examples: what each symptom means
------------------------------------------

The same visible symptom can come from different layers. Use concrete
reproductions and repair ownership instead of guessing.

.. list-table:: Grammar-tooling boundary examples
   :header-rows: 1

   * - Symptom
     - Minimal reproduction
     - Likely owner
     - Correct first repair
     - Incorrect shortcut
   * - A valid command-line file is not highlighted.
     - ``python -m pyfcstm inspect -i sample.fcstm`` succeeds, but the editor shows keywords as plain text.
     - Pygments, TextMate, or VSCode language registration.
     - Update syntax display assets and run editor validation.
     - Changing parser grammar just to influence colors.
   * - VSCode completion suggests invalid syntax.
     - Insert the completed snippet and run ``pyfcstm inspect``; the parser/model rejects it.
     - VSCode completion or snippets.
     - Remove or fix the suggestion and add a focused editor test.
     - Loosening parser/model validation to accept a bad suggestion.
   * - A new parser rule compiles but model import loses data.
     - Parse succeeds, but inspect output omits the new event, action, or transition fact.
     - Listener, AST node, or model importer.
     - Add an AST/model test that checks the represented fact.
     - Only updating documentation because the grammar accepts the text.
   * - Documentation example fails after a grammar change.
     - Copy the documented FCSTM block into a file and run ``pyfcstm inspect``.
     - The page and its generated example resources.
     - Update the example or explicitly mark it as an invalid counterexample.
     - Leaving the stale example because Sphinx still builds.
   * - LLM repair keeps generating old syntax.
     - The human docs are updated, but ``pyfcstm/llm/fcstm_grammar_guide.md`` still teaches the old rule.
     - Prompt-facing grammar guide and checksum.
     - Update the guide, run ``make sha256``, and include both files.
     - Treating the human documentation update as enough for prompt users.

These examples are intentionally not phrased as one universal command. The
right check depends on which boundary changed. A parser-only patch should not be
forced to run VSCode packaging, but a syntax-support patch that claims editor
parity must include editor evidence.

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
