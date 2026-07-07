Reference map
=============

Use this page when you need exact facts rather than a learning path or a task
recipe. The global sidebar lists each reference page directly and keeps the
generated API documentation as the final API map; this page helps you choose the
right lookup target.

What reference pages promise
----------------------------

Reference pages should be dense and checkable: commands, syntax forms, report
fields, option values, configuration keys, legal and illegal forms, and links to
implementation facts. They should not become guided tutorials or broad design
essays.

Lookup by fact type
-------------------

Command names, options, and exit-facing behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :doc:`cli/index` when you need command groups, option names, aliases,
defaults, output choices, and the boundary between command failure and model
failure.

* **Use after:** a tutorial or how-to guide tells you which command family you
  need.
* **Do not expect:** a full narrative workflow; use
  :doc:`/how_to/cli_workflows/index` for that.

DSL syntax and legal forms
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :doc:`dsl/index` when you need the complete language lookup: declarations,
states, transitions, lifecycle blocks, events, expressions, comments,
unsupported forms, and examples of legal and illegal syntax.

* **Use after:** you know the construct you want to write.
* **Do not expect:** the full semantic explanation; use
  :doc:`/explanations/dsl_semantics/index` for why the construct behaves that
  way.

Inspect report fields
~~~~~~~~~~~~~~~~~~~~~

Use :doc:`inspect_report/index` when you need the shape and meaning of inspect
outputs, including human-oriented and machine-oriented report fields.

* **Use after:** ``pyfcstm inspect`` has produced a report or a tutorial showed
  you the report family.
* **Do not expect:** every diagnostic code explanation; use
  :doc:`diagnostics_codes/index` for code lookup.

Diagnostic codes
~~~~~~~~~~~~~~~~

Use :doc:`diagnostics_codes/index` when you need diagnostic identifiers,
severity, message meaning, and repair direction.

* **Use after:** inspect, validation, or a command message gives you a code.
* **Do not expect:** general modeling advice; use the DSL and diagnostics
  explanations for context.

Visualization options
~~~~~~~~~~~~~~~~~~~~~

Use :doc:`visualization_options/index` when you need exact rendering options,
output format behavior, renderer assumptions, and boundary conditions for diagram
export.

* **Use after:** you know whether you need PlantUML source or a rendered image.
* **Do not expect:** a first diagram walkthrough; use
  :doc:`/tutorials/visualization/index` for that.

Template configuration and built-in template facts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :doc:`template_config/index` for renderer configuration keys, object-loading
forms, expression and statement style settings, and invalid configuration shapes.
Use :doc:`builtin_templates/index` for packaged template names, status, emitted
artifacts, and target-family boundaries.

* **Use after:** you are generating code or maintaining a template.
* **Do not expect:** target runtime semantics beyond what the template reference
  explicitly owns; use generation how-to pages and template explanations for
  workflow and design context.

Grammar and editor tooling facts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :doc:`grammar_tooling/index` when you need the exact grammar files, generated
parser paths, highlighter assets, editor-support assets, and validation commands.

* **Use after:** a grammar or editor change is planned.
* **Do not expect:** design rationale for why the assets are coupled; use
  :doc:`/explanations/grammar_tooling/index` for that.

Generated Python API map
~~~~~~~~~~~~~~~~~~~~~~~~

Use :doc:`API Documentation </api_doc_en>` when you need the complete generated
Python API structure. The generated API map stays in the Reference area as the
last entry, and API introductions should be changed through the generator rather
than by editing generated output directly.

Current reference boundaries
----------------------------

This map only links to pages that exist in the current documentation tree. For
example, dedicated simulation reference material is not present yet; use the
simulation tutorial, how-to guide, and execution-semantics explanation until a
separate reference page exists. This map does not link to
``reference/simulation/`` while that page is absent.

If you need a different role
----------------------------

* First-success learning: :doc:`/tutorials/index`
* Concrete task recipes: :doc:`/how_to/index`
* Design and semantic reasoning: :doc:`/explanations/index`
