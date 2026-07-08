Reference map
=============

Use this page when you need exact facts rather than a learning route, task
recipe, or design explanation. The global sidebar lists each reference page
directly and keeps generated API documentation as the final API map; this page
helps you choose the lookup target by fact type.

Role: this page is the Reference router. It points to dense pages for commands,
DSL syntax, inspect report fields, diagnostic codes, simulation facts,
visualization options, template configuration, grammar tooling, built-in
templates, and generated Python API objects.

Non-goals: this page is not a tutorial, not a how-to recipe, and not a broad
concept essay. It should not restate every table from the reference pages; it
should make the lookup boundary obvious.

What reference pages promise
----------------------------

A reference page should be accurate, searchable, and closed over the facts it
claims to cover. It should contain exact spellings, defaults, legal values,
illegal forms, field meanings, side effects, diagnostics, and links to source
facts where those details matter. It should not require readers to complete a
tutorial before they can look up a value.

New-user path
-------------

If you are new but already hit a lookup question, start with the fact family.

1. For a command option or output behavior, use :doc:`cli/index`.
2. For a syntax form, use :doc:`dsl/index`.
3. For inspect JSON or human-report fields, use :doc:`inspect_report/index`.
4. For diagnostic identifiers and repair direction, use
   :doc:`diagnostics_codes/index`.
5. For Python objects, classes, functions, or modules, use :doc:`/api_doc_en`
   after you know the object name.

Experienced-user path
---------------------

If you know the subsystem, use the shortest lookup.

* Command-facing behavior: :doc:`cli/index`.
* Language forms: :doc:`dsl/index`.
* Report shape: :doc:`inspect_report/index`.
* Diagnostic code: :doc:`diagnostics_codes/index`.
* Runtime execution interface: :doc:`simulation/index`.
* Diagram option field: :doc:`visualization_options/index`.
* Template configuration key or built-in target: :doc:`template_config/index` or
  :doc:`builtin_templates/index`.
* Grammar/editor maintenance file or command: :doc:`grammar_tooling/index`.
* Public Python API object: :doc:`/api_doc_en`.

Maintainer path
---------------

Use this route to review reference quality.

* Check each reference page has tables or structured facts for closed lists.
* Check tricky items include legal examples, illegal examples, and failure
  boundaries.
* Check every command-facing row names stdout, stderr, exit status, or file side
  effects when those behaviors matter.
* Check generated API pages remain generated and are not replaced by hand-written
  reference prose.
* Check bilingual reference pages expose the same facts, defaults, examples, and
  risk boundaries.

Lookup cards
------------

CLI commands: :doc:`cli/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you know the command family or need to choose among ``simulate``,
``inspect``, ``generate``, ``plantuml``, and ``visualize``.

Outcome: you can look up command names, option names, aliases, defaults,
accepted values, output behavior, examples, and command-facing failure
boundaries.

Non-goal: it does not teach the whole workflow or explain why the underlying
model behaves a certain way.

Next step: use :doc:`/how_to/cli_workflows/index` for recipes and the relevant
feature explanation when command output surprises you.

DSL syntax: :doc:`dsl/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you know which FCSTM construct you want to check: declarations,
imports, states, transitions, events, expressions, lifecycle blocks, forced
forms, combo forms, or comments.

Outcome: you can look up legal syntax, illegal counterexamples, expansion
quasi-specs, expression precedence, operation blocks, event scopes, and related
diagnostics.

Non-goal: it does not guide a first modeling path or fully explain semantic
motivation.

Next step: use :doc:`/how_to/dsl/index` for authoring tasks and
:doc:`/explanations/dsl_semantics/index` for semantics.

Inspect report fields: :doc:`inspect_report/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you run or plan to run ``pyfcstm inspect`` and need the shape of
human, JSON, or LLM-oriented outputs.

Outcome: you can look up report-affecting CLI options, top-level JSON fields,
nested object contracts, LLM report contracts, and invalid-input boundaries.

Non-goal: it does not list every diagnostic identifier or explain the philosophy
of diagnostics.

Next step: use :doc:`diagnostics_codes/index` for codes,
:doc:`/how_to/inspect/index` for tasks, and :doc:`/explanations/diagnostics/index`
for capability boundaries.

Diagnostic codes: :doc:`diagnostics_codes/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have a diagnostic identifier, severity, or repair hint from
inspect output and need to look up what it means.

Outcome: you can read code families, emission tiers, message meaning, repair
direction, and machine coverage checks.

Non-goal: it does not define the full inspect report schema or teach a triage
workflow.

Next step: use :doc:`inspect_report/index` for report fields and
:doc:`/how_to/inspect/index` for repeatable triage tasks.

Simulation facts: :doc:`simulation/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you need exact simulation CLI invocation, batch or REPL command
forms, event input forms, settings, history/export facts, or Python runtime API
facts.

Outcome: you can look up command syntax, setting names, accepted values, history
formats, public failures, and runtime API boundaries.

Non-goal: it does not explain the full cycle-order reasoning or teach the first
simulation run.

Next step: use :doc:`/how_to/simulation/index` for tasks and
:doc:`/explanations/execution_semantics/index` for execution reasoning.

Visualization options: :doc:`visualization_options/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you need exact diagram option fields, renderer behavior, detail
presets, suffix handling, headless behavior, or failure boundaries.

Outcome: you can look up option scenarios, PlantUML option fields, renderer
example cards, preset resolution, variable/state labels, lifecycle visibility,
and transition/event options.

Non-goal: it does not teach the first diagram workflow or explain every diagram
as a learning narrative.

Next step: use :doc:`/how_to/visualization/index` for tasks and
:doc:`/tutorials/visualization/index` for the first diagram.

Template configuration: :doc:`template_config/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you are writing or debugging a template directory and need exact
``config.yaml`` keys, object-loading forms, mapping rules, ignore behavior, or
renderer helper facts.

Outcome: you can look up expression styles, statement styles, runtime statement
renderers, Jinja helpers, validation failures, file mapping, and built-in config
examples.

Non-goal: it does not explain the rendering pipeline from first principles or
list every built-in template contract.

Next step: use :doc:`/how_to/templates/index` for authoring tasks,
:doc:`/explanations/template_rendering/index` for design, and
:doc:`builtin_templates/index` for built-in target facts.

Grammar and editor tooling: :doc:`grammar_tooling/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you need canonical grammar files, generated parser boundaries,
highlighting facts, VSCode assets, operator ordering, keyword update steps, or
validation command facts.

Outcome: you can look up source/generated file pairs, core maintenance commands,
Pygments and TextMate facts, VSCode verification suites, and update checklists.

Non-goal: it does not explain why grammar changes fan out across layers and does
not teach a beginner syntax tour.

Next step: use :doc:`/how_to/grammar_editor/index` for tasks and
:doc:`/explanations/grammar_tooling/index` for rationale.

Built-in templates: :doc:`builtin_templates/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you need to know which packaged target templates exist, how they
are discovered, what generated README files promise, or what each target family
requires.

Outcome: you can look up metadata, discovery APIs, generated README contracts,
and target-family notes for ``python``, ``c``, ``c_poll``, ``cpp``, and
``cpp_poll``.

Non-goal: it does not teach custom template authoring or explain renderer
architecture in detail.

Next step: use :doc:`/how_to/generation/index` for generation tasks,
:doc:`/how_to/templates/index` for authoring, and
:doc:`template_config/index` for config facts.

Generated API map: :doc:`/api_doc_en`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you already know the Python module, class, function, or data
object you want to inspect, or a reference page has pointed you to an API object.

Outcome: you can browse the generated module tree produced from ``pyfcstm/`` and
look up public Python API docstrings.

Non-goal: it does not replace command, DSL, report, template, or visualization
reference pages and should not be edited by hand.

Next step: use feature reference pages first when you do not yet know the API
object name; update the generator if the API reference introduction needs to
change.

If you need a different role
----------------------------

Reference is the final place for exact facts. If you are still trying to learn
the first path, return to Tutorials. If you are trying to complete an operation,
use How-to Guides. If you are trying to understand the reason behind a behavior,
use Explanations.
