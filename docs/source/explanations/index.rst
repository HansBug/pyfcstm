Explanation map
===============

Use this page when your question is about why pyfcstm behaves a certain way.
The global sidebar lists each explanation directly; this map helps you choose
the sibling page that owns the mechanism, ordering rule, architectural boundary,
or trade-off behind the behavior you are seeing.

Role: this page is the Explanation router. It connects conceptual questions to
architecture, DSL semantics, execution semantics, diagnostics, template
rendering, and grammar tooling without turning those explanations into tutorials
or lookup tables.

Non-goals: this page does not provide first-success commands, task recipes,
closed option lists, JSON schemas, diagnostic code tables, or API signatures.
Use :doc:`/tutorials/index` for learning paths, :doc:`/how_to/index` for tasks,
and :doc:`/reference/index` for exact facts.

What explanations promise
-------------------------

Explanations should answer why a behavior exists, what order the system follows,
which boundary a subsystem owns, and what trade-off shaped the design. They may
use traces, diagrams, or examples, but the example is evidence for reasoning
rather than a copy-paste task. When an explanation needs a precise fact, it
should link to Reference instead of duplicating the whole table.

New-user path
-------------

If you are moving from tutorials into conceptual understanding, read in this
order.

1. Start with :doc:`architecture/index` to see the pipeline from DSL text to
   model, diagnostics, rendering, simulation, and generated artifacts.
2. Read :doc:`dsl_semantics/index` when syntax examples are no longer enough and
   you need to know what the model means.
3. Read :doc:`execution_semantics/index` when a cycle, lifecycle action, or
   transition trace surprises you.
4. Read :doc:`diagnostics/index` when inspect output needs interpretation.
5. Read :doc:`template_rendering/index` when generated code behavior depends on
   renderer configuration or packaged template boundaries.
6. Read :doc:`grammar_tooling/index` only when you are maintaining syntax,
   highlighting, editor assets, or LLM-facing grammar material.

Experienced-user path
---------------------

If you already know the subsystem, choose the question.

* Where does this behavior belong in the package pipeline? Use
  :doc:`architecture/index`.
* What does this DSL construct mean after parsing and import? Use
  :doc:`dsl_semantics/index`.
* Why did a cycle produce this active-state and variable trace? Use
  :doc:`execution_semantics/index`.
* What can inspect prove, warn about, or merely report? Use
  :doc:`diagnostics/index`.
* Why does generation go through templates, expression styles, and statement
  styles? Use :doc:`template_rendering/index`.
* Why does one grammar change affect parser, highlighting, docs, and editor
  tooling? Use :doc:`grammar_tooling/index`.

Maintainer path
---------------

Use this route when reviewing explanation quality.

* Check that each explanation answers a "why" or "how it works" question rather
  than repeating a command table.
* Check that complex behavior has a trace, diagram, or concrete boundary example
  where prose alone would be vague.
* Check that risk scope is precise; for example, a generated C/C++ deployment
  warning should not be presented as a Python runtime warning.
* Check bilingual pages teach the same mechanism and do not drop diagrams,
  traces, or boundary statements in one language.

Explanation reading signals
---------------------------

When reading an explanation page, readers should not only collect terms. They
should be able to place one observed behavior into a larger causal chain: what
the input is, what the system does first, which boundary stops the behavior, and
which results are only warnings versus evidence that proves a problem exists.

If the reader needs the next command, they have left an explanation question and
should return to a how-to guide. If the reader needs a legal value, default, or
field name, they need a reference page. If they do not yet know which observed
behavior to start from, a tutorial should provide a smaller observable example.

The value of an explanation page is making later tasks and reference lookups
easier to use, not copying all of those pages into one place. If a paragraph
cannot say which later judgment it improves, it is probably ordinary directory
text and needs more substance.

Concept cards
-------------

Architecture: :doc:`architecture/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you know pyfcstm has source files, model objects, commands,
templates, diagnostics, simulation, and generated outputs, but you need the map
of how those pieces connect.

Outcome: you can place a behavior in the DSL parser, model import, inspect,
rendering, simulation, verification, visualization, or generated-asset boundary.

Non-goal: it does not teach command usage or define every class and function.
Those facts live in :doc:`/how_to/cli_workflows/index`, feature-specific how-to
pages, and :doc:`/api_doc_en`.

Next step: use the architecture trace to choose a deeper explanation, then use
Reference when you need exact public API or CLI facts.

DSL semantics: :doc:`dsl_semantics/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you can read basic FCSTM syntax and need to know what states,
transitions, event scopes, lifecycle hooks, aspects, pseudo states, or combo
forms mean after parsing.

Outcome: you can explain ownership, name resolution, composite entry, transition
forms, expression separation, lifecycle reuse, and sugar expansion at the model
level.

Non-goal: it does not replace the complete grammar reference or task recipes for
editing a model.

Next step: use :doc:`/reference/dsl/index` for exact forms and
:doc:`/how_to/dsl/index` for authoring tasks.

Execution semantics: :doc:`execution_semantics/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have a valid model or simulation trace and need to reason
about cycles, entry, during actions, exit, transition effects, hot starts,
rollback, or simulator alignment.

Outcome: you can explain why a cycle produces a particular active path and why
certain lifecycle or aspect actions run in that order.

Non-goal: it does not list every simulator command or every generated runtime
API field.

Next step: use :doc:`/how_to/simulation/index` for operations and
:doc:`/reference/simulation/index` for exact command/API facts.

Bounded model checking: :doc:`bmc_semantics/index`,
:doc:`bmc_properties/index`, and :doc:`bmc_solving/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you can read an FCSTM model and FBMCQ query but need to know why
the bounded result, property polarity, witness, and replay have their current
meaning.

Outcome: the three pages take you from allocated trace symbols and the core
transition relation, through definedness and all seven property objectives, to
dual solver checks, verdict mapping, witness projection, and runtime replay.

Non-goal: they do not teach first use or serve as field catalogs.

Next step: run tasks in :doc:`/how_to/bmc/index`; use
:doc:`/reference/bmc_query/index` and :doc:`/reference/bmc_results/index` for
exact syntax and protocol facts.

Diagnostics: :doc:`diagnostics/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have inspect output, a diagnostic-heavy model, or a question
about what static analyzers can and cannot prove.

Outcome: you can distinguish parsed structure, static diagnostics, optional
verification feedback, emit tiers, severity, and LLM repair usefulness.

Non-goal: it does not enumerate every JSON report field or diagnostic code.

Next step: use :doc:`/reference/inspect_report/index` for schema details,
:doc:`/reference/diagnostics_codes/index` for code lookup, and
:doc:`/how_to/inspect/index` for triage recipes.

Template rendering: :doc:`template_rendering/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have generated output or custom-template work and need to
understand why rendering goes through configured template directories, packaged
assets, Jinja helpers, expression styles, and statement styles.

Outcome: you can separate renderer responsibilities from target runtime
responsibilities and understand why built-in templates are packaged and tested
through public extraction paths.

Non-goal: it does not list every template config key or every built-in target
contract.

Next step: use :doc:`/how_to/templates/index` for authoring tasks,
:doc:`/reference/template_config/index` for config facts, and
:doc:`/reference/builtin_templates/index` for built-in target facts.

Grammar tooling: :doc:`grammar_tooling/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you are considering a syntax change or editor/tooling update and
need to know why parser grammar, semantic model, highlighting, documentation,
LLM guide, and VSCode assets move together.

Outcome: you can explain the difference between grammar parsing, semantic model
import, syntax highlighting, editor completion, and prompt-facing grammar
guidance.

Non-goal: it does not replace the exact command checklist for regenerating and
validating assets.

Next step: use :doc:`/how_to/grammar_editor/index` for tasks and
:doc:`/reference/grammar_tooling/index` for canonical file and command facts.

Where explanations stop
-----------------------

Leave Explanations when the question becomes operational or factual. If you need
a command to run, use How-to Guides. If you need a legal form, default value,
field name, or diagnostic code, use Reference. Explanations are successful when
they make the next operational or factual page easier to use.
