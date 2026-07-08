How-to roadmap
===============

Use this page when you already know the job you want pyfcstm to perform and need
a task recipe rather than a learning tour. The global sidebar lists every
how-to page directly; this roadmap helps you choose the right sibling task page,
prepare the correct input, and know which reference or explanation page to open
when a recipe deliberately stops.

Role: this page is the How-to router for repeatable tasks. It turns user goals
such as install, inspect, simulate, generate, visualize, author templates, or
maintain grammar assets into the page that owns the recipe.

Non-goals: this page is not a tutorial, not a design explanation, not a CLI
reference, and not a full schema table. It does not replace the task pages it
links to; it only tells you which one to use and what success signal to expect.

What a how-to guide promises
----------------------------

A how-to guide should start from a concrete assumption, give ordered steps,
show a short output or success signal, name common mistakes, and link away to
reference facts when the command or option list becomes too broad. If a page
only explains why behavior exists, it belongs under :doc:`/explanations/index`.
If a page primarily lists exact forms and fields, it belongs under
:doc:`/reference/index`.

New-user path
-------------

If you just finished a tutorial, choose the how-to page that repeats the task in
a less guided way.

1. After the quick start, use :doc:`cli_workflows/index` to repeat the command
   sequence with your own file.
2. After the DSL tutorial, use :doc:`dsl/index` when changing model structure.
3. After the simulation or inspect tutorial, use :doc:`simulation/index` or
   :doc:`inspect/index` for repeatable troubleshooting tasks.
4. After generation or visualization tutorials, use :doc:`generation/index`,
   :doc:`templates/index`, or :doc:`visualization/index` depending on whether
   you need output files, template authoring, or diagrams.

Experienced-user path
---------------------

If you already know the feature area, start from the task verb.

* Need to prepare an environment or CI job: open :doc:`installation/index`.
* Need a command chain: open :doc:`cli_workflows/index`.
* Need to change source language content: open :doc:`dsl/index`.
* Need runtime behavior: open :doc:`simulation/index`.
* Need structure, diagnostics, or LLM repair feedback: open :doc:`inspect/index`.
* Need generated code or templates: open :doc:`generation/index` or
  :doc:`templates/index`.
* Need diagrams or grammar/editor maintenance: open :doc:`visualization/index`
  or :doc:`grammar_editor/index`.

Maintainer path
---------------

Use this route to review how-to quality.

* Check each task has prerequisites, steps, success signal, failure boundary, and
  next links.
* Check examples are short and purpose-tied; long workflows should live in
  generated demo resources rather than in prose.
* Check task recipes do not silently become reference dumps.
* Check changed Chinese pages carry the same task, output, warning, and next-link
  coverage as the English page.

Task page usage signals
-----------------------

A good task page should tell readers what input they need before they start and
what observable signal means the task succeeded after they finish. Command tasks
usually need a short output excerpt, generated filename, or exit behavior.
Editing tasks usually need to say which file should change, how to check the
result, and how to repair common mistakes.

If a task page only says "run this command" without a success signal, it is not
yet verifiable enough. If it starts explaining broad design reasons, move that
reasoning to an explanation page. If it lists a closed set of options, move the
exact facts to a reference page.

A task page may stay concise, but every step should leave enough evidence for a
reader or reviewer to reproduce the outcome.

Task cards
----------

Installation: :doc:`installation/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you need a Python environment, a package source, or a CI image
where pyfcstm should become available.

Outcome: you can install from PyPI or the main branch, verify the Python package,
verify the CLI, and decide which optional renderer or native toolchain checks
are outside the core install.

Non-goal: it does not teach every command workflow, DSL construct, or generated
runtime behavior.

Next step: after installation, run :doc:`cli_workflows/index` or return to
:doc:`/tutorials/quick_start/index` for the first end-to-end path.

CLI workflows: :doc:`cli_workflows/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: the ``pyfcstm`` command is installed and you have an input
``.fcstm`` file or are ready to copy the small sample in the guide.

Outcome: you can choose between ``simulate``, ``inspect``, ``generate``,
``plantuml``, and ``visualize`` workflows and recognize the success signal for
each command family.

Non-goal: it does not list every option, alias, stdout/stderr boundary, or exit
status fact.

Next step: use :doc:`/reference/cli/index` for command facts and the feature
specific how-to page when a workflow becomes deep.

DSL tasks: :doc:`dsl/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you are editing an FCSTM model and know whether you are changing
states, transitions, events, guards, effects, lifecycle actions, or imports.

Outcome: you can perform common authoring tasks such as adding states, writing
event scopes, guarding transitions, using lifecycle hooks, and choosing forced
or combo forms safely.

Non-goal: it does not provide every grammar production, every invalid form, or
the full semantic reasoning behind expansion.

Next step: use :doc:`/reference/dsl/index` for exact syntax and
:doc:`/explanations/dsl_semantics/index` when a form's meaning is not obvious.

Simulation tasks: :doc:`simulation/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: your model parses and you want to execute cycles, events, hot
starts, abstract handlers, or history export.

Outcome: you can run batch commands, use the interactive REPL, inject events,
hot start at a state, implement abstract handlers, and debug a failing model.

Non-goal: it does not explain the full execution-order model or list every API
field in isolation.

Next step: use :doc:`/explanations/execution_semantics/index` for behavior
reasoning and :doc:`/reference/simulation/index` for exact command/API facts.

Inspect tasks: :doc:`inspect/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have an FCSTM file and need a human report, JSON output, an
LLM-oriented repair report, or a CI severity gate.

Outcome: you can choose report formats, save color-controlled human output,
write full JSON, fail a CI gate from severity, and navigate from diagnostics to
source spans.

Non-goal: it does not define every JSON field, every diagnostic code, or every
static-analysis limitation inline.

Next step: use :doc:`/reference/inspect_report/index` for report fields,
:doc:`/reference/diagnostics_codes/index` for codes, and
:doc:`/explanations/diagnostics/index` for diagnostic boundaries.

Generation tasks: :doc:`generation/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: your model parses and you need generated artifacts from a
packaged built-in template or a custom template directory.

Outcome: you can choose ``--template`` versus ``--template-dir``, clear output
safely, generate each built-in family, read generated README files, and
smoke-check relevant outputs.

Non-goal: it does not teach template internals in full or make native toolchain
checks automatic.

Next step: use :doc:`templates/index` for template authoring,
:doc:`/reference/builtin_templates/index` for built-in target contracts, and
:doc:`/reference/template_config/index` for config keys.

Visualization tasks: :doc:`visualization/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you have a model and need PlantUML source, rendered output,
detail presets, focused views, CI-stable diagram jobs, or Python API control.

Outcome: you can choose source versus rendered output, compare presets, render a
final artifact, and keep diagram jobs stable in headless environments.

Non-goal: it does not enumerate every visualization option or backend failure in
the task flow.

Next step: use :doc:`/reference/visualization_options/index` for exact fields and
:doc:`/tutorials/visualization/index` if you need a first diagram path.

Template author tasks: :doc:`templates/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you already know generation basics and want to create or debug a
custom template directory.

Outcome: you can build the smallest useful template, understand file mapping,
add expression and statement styles, register helpers, and validate template
behavior.

Non-goal: it does not replace the exact template configuration reference or the
built-in target contracts.

Next step: use :doc:`/reference/template_config/index` for config syntax,
:doc:`/reference/builtin_templates/index` for built-in facts, and
:doc:`/explanations/template_rendering/index` for rendering design.

Grammar and editor tasks: :doc:`grammar_editor/index`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites: you are changing syntax, highlighting, VSCode assets, the prompt
facing grammar guide, or validation suites.

Outcome: you can decide what kind of grammar change you are making, regenerate
ANTLR artifacts, synchronize Pygments and TextMate highlighting, and verify the
editor extension assets.

Non-goal: it does not explain every parser/model boundary or replace the exact
file and command reference.

Next step: use :doc:`/reference/grammar_tooling/index` for canonical files and
:doc:`/explanations/grammar_tooling/index` for why one syntax change touches
multiple layers.

How to leave the how-to area
----------------------------

After a task succeeds, use Reference when you need precise facts, Explanations
when behavior surprises you, and Tutorials when you need a smaller learning path
for another teammate. A how-to page should make that exit obvious instead of
trying to become every other role at once.
