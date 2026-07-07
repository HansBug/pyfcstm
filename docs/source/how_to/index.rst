How-to roadmap
==============

Use this page when you already know the job you want to finish. The global
sidebar lists each how-to guide directly; this roadmap helps you choose the
right sibling page by input, output, success signal, and the place to go when a
recipe needs exact reference facts.

What a how-to guide promises
----------------------------

A how-to guide starts with a concrete task and ends with an observable result.
It should not teach every concept from scratch and should not duplicate option
or schema tables. Use tutorials for first learning, explanations for design
reasoning, and reference pages for exact lookup.

Choose by task
--------------

Install or check the environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open :doc:`installation/index` when your input is a fresh Python environment or
a machine where ``pyfcstm`` may not be installed yet.

* **Output:** a working command-line entry point.
* **Success signal:** commands such as ``pyfcstm --help`` run in the intended
  environment.
* **If it fails:** use the installation page for package and platform checks;
  use :doc:`/reference/cli/index` only after the command exists.

Run command-line workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~

Open :doc:`cli_workflows/index` when the job is to combine existing commands:
parse a file, simulate it, inspect it, generate output, or produce diagrams.

* **Output:** a repeatable command sequence with files in known locations.
* **Success signal:** the command exits successfully and the documented output
  file or terminal result appears.
* **If it fails:** check exact options in :doc:`/reference/cli/index`, then use
  diagnostics references when the failure comes from model content.

Author or change a model
~~~~~~~~~~~~~~~~~~~~~~~~

Open :doc:`dsl/index` when you need a recipe for writing variables, states,
transitions, guards, actions, or modeling patterns.

* **Output:** a source file that parses and expresses the intended behavior.
* **Success signal:** parse, inspect, or simulate commands accept the file.
* **If it fails:** look up exact syntax in :doc:`/reference/dsl/index` and the
  modeling semantics in :doc:`/explanations/dsl_semantics/index`.

Run simulation tasks
~~~~~~~~~~~~~~~~~~~~

Open :doc:`simulation/index` when you need interactive or batch execution,
cycles, events, hot starts, or state-history-oriented checks.

* **Output:** visible active-state and variable evolution.
* **Success signal:** the simulated state path matches the behavior you expected
  from the model.
* **If it fails:** use :doc:`/explanations/execution_semantics/index` for
  lifecycle ordering, then return to the simulation tutorial or task guide for
  runnable troubleshooting.

Inspect and diagnose a model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open :doc:`inspect/index` when you need a structured report, LLM-friendly
feedback, or diagnostic evidence before editing a model.

* **Output:** human-readable output, JSON, or LLM-oriented report text.
* **Success signal:** the report contains the expected metrics, diagnostics, and
  source locations for the model under review.
* **If it fails:** use :doc:`/reference/inspect_report/index` for report shape
  and :doc:`/reference/diagnostics_codes/index` for diagnostic codes.

Generate code
~~~~~~~~~~~~~

Open :doc:`generation/index` when the job is to run ``pyfcstm generate`` with a
packaged built-in template or a custom template directory.

* **Output:** generated files in a chosen output directory.
* **Success signal:** the generated directory contains the expected artifacts and
  README guidance.
* **If it fails:** use :doc:`/reference/builtin_templates/index` for built-in
  template facts and :doc:`/reference/template_config/index` for configuration
  keys and renderer boundaries.

Visualize a model
~~~~~~~~~~~~~~~~~

Open :doc:`visualization/index` when you need PlantUML source or rendered images
for a model.

* **Output:** diagram source or image artifacts.
* **Success signal:** the diagram file exists and shows the state structure you
  intended to communicate.
* **If it fails:** use :doc:`/reference/visualization_options/index` for exact
  renderer options and environment assumptions.

Maintain templates
~~~~~~~~~~~~~~~~~~

Open :doc:`templates/index` when you are authoring, packaging, or reviewing a
template rather than just using one.

* **Output:** a template directory or packaged template asset that goes through
  the public renderer path.
* **Success signal:** generated artifacts come from ``pyfcstm.template`` or the
  renderer entry points, not from direct test shortcuts into repository template
  sources.
* **If it fails:** read :doc:`/explanations/template_rendering/index` for design
  boundaries and :doc:`/reference/template_config/index` for exact config facts.

Update grammar and editor assets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open :doc:`grammar_editor/index` when you touch grammar files, syntax
highlighting, or editor-support assets.

* **Output:** parser, highlighter, and editor assets that remain aligned.
* **Success signal:** the documented validation commands pass and no generated
  parser output is edited by hand.
* **If it fails:** use :doc:`/reference/grammar_tooling/index` for commands and
  asset paths, then read :doc:`/explanations/grammar_tooling/index` for coupling
  rationale.

How to leave the how-to area
----------------------------

* Need a first learning path? Go to :doc:`/tutorials/index`.
* Need the reason behind an ordering or boundary? Go to
  :doc:`/explanations/index`.
* Need exact values, fields, defaults, or legal forms? Go to
  :doc:`/reference/index`.
