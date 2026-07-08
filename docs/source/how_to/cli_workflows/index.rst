.. _sec-how-to-cli-workflows:

CLI workflows
=============

Use this guide when you want a repeatable command sequence. It assumes pyfcstm
is already installed; if not, start with :doc:`/how_to/installation/index`. For
exact options and failure boundaries, use :doc:`/reference/cli/index`.

Choose the right command first
------------------------------

.. list-table:: Command selection
   :header-rows: 1

   * - Goal
     - Command
     - Main output
     - Follow-up reference
   * - Run the model without generated code
     - ``simulate``
     - active state and variable trace
     - :doc:`/reference/simulation/index`
   * - Read model facts and diagnostics
     - ``inspect``
     - human, JSON, or LLM-oriented report
     - :doc:`/reference/inspect_report/index`
   * - Generate target-language files
     - ``generate``
     - output directory
     - :doc:`/reference/builtin_templates/index`
   * - Export diagram source
     - ``plantuml``
     - ``.puml`` text
     - :doc:`/reference/visualization_options/index`
   * - Render diagram artifacts
     - ``visualize``
     - ``.png``, ``.svg``, or ``.pdf``
     - :doc:`/reference/visualization_options/index`

Inspect command help
--------------------

Start with top-level help, then inspect the subcommand you intend to run:

.. code-block:: bash

   pyfcstm --help
   pyfcstm inspect --help
   pyfcstm generate --help

Use help output as a quick sanity check for the environment. If ``pyfcstm`` is
not found, try the same environment through ``python -m pyfcstm --help`` and
then return to :doc:`/how_to/installation/index`.

Run a short simulation
----------------------

Use batch mode for transcripts that belong in documentation, CI logs, or bug
reports:

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm -e "current; cycle; current"

Use interactive mode when you are exploring manually:

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm

Practical checks:

* Start with ``current`` so the transcript records the initial active path.
* Use explicit event names in batch scripts, for example ``cycle Start``.
* Use hot start only when you can provide every required variable value.
* Do not use simulation as proof that generated target code is correct; use it
  as the reference behavior to compare against generated-runtime tests.

Export an inspect report
------------------------

Human output is useful while editing:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm

Use full JSON when a script will consume metrics, diagnostics, or model facts:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

Use an LLM-oriented format when you plan to paste the report into a repair
prompt:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md

For CI-style checks, keep the command explicit and bounded:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm \
     --format json \
     --enable-verify \
     --smt-timeout-ms 2000 \
     -o machine.inspect.json

If this fails before reading the model, check the verify-policy options. Inspect
parses some higher-cost taxonomy labels only to report that automatic inspect
runs are not allowed to use them.

Generate code from a built-in template
--------------------------------------

Prefer packaged built-in templates for normal users:

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated/python --clear

Use a custom template directory only when you intentionally maintain that
template:

.. code-block:: bash

   pyfcstm generate -i machine.fcstm -t ./templates/my_target -o generated/my_target --clear

Generation checklist:

* Keep the DSL source and generation command together in project notes or build
  rules.
* Use ``--clear`` only for an output directory that is safe to replace.
* Review generated files before committing them.
* If generated outputs are rebuilt on demand, put the generated directory in
  ``.gitignore`` instead of committing stale artifacts.
* Use the generated README as the next entry point for runtime-specific
  integration and smoke checks.

Export PlantUML source
----------------------

Use ``plantuml`` when you want deterministic source that can be reviewed,
committed, or rendered by another tool:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

Choose a detail level before adding overrides:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

Add narrow configuration overrides only when the diagram needs them:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c max_depth=2 \
     -o machine.focused.puml

Render a diagram artifact
-------------------------

Use ``visualize --check`` first when the renderer environment is uncertain:

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

Render without opening a viewer in CI or headless environments:

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

Prefer local rendering for private diagrams:

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open

Use remote rendering only when the generated PlantUML source is allowed to be
sent to the configured service:

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm --renderer remote --no-open

Make command runs reproducible
------------------------------

A repository that depends on pyfcstm commands should make the input/output
relationship obvious:

* Put source machines under a stable directory such as ``machines/`` or
  ``src/machines/``.
* Name generated output directories by target, for example ``generated/python``
  or ``generated/c_poll``.
* Record command lines in a Makefile, CI job, or project README.
* Keep inspection reports and diagrams either clearly generated or clearly
  committed as review artifacts.
* Use ``plantuml`` source export when a rendered image is not necessary.
* Use ``visualize --no-open`` in scripts so GUI availability does not affect the
  build result.

Troubleshoot by layer
---------------------

.. list-table:: Troubleshooting route
   :header-rows: 1

   * - Symptom
     - First command
     - Next page
   * - ``pyfcstm`` command is missing
     - ``python -m pyfcstm --help``
     - :doc:`/how_to/installation/index`
   * - DSL does not parse
     - ``pyfcstm inspect -i machine.fcstm``
     - :doc:`/reference/dsl/index`
   * - Model parses but behavior is surprising
     - ``pyfcstm simulate -i machine.fcstm -e "current; cycle; current"``
     - :doc:`/explanations/execution_semantics/index`
   * - Diagnostics need interpretation
     - ``pyfcstm inspect -i machine.fcstm --format json``
     - :doc:`/reference/diagnostics_codes/index`
   * - Generation fails
     - ``pyfcstm generate ... --template python``
     - :doc:`/reference/builtin_templates/index`
   * - Rendering fails
     - ``pyfcstm visualize --check --renderer auto``
     - :doc:`/reference/visualization_options/index`

Worked command examples with expected signals
---------------------------------------------

Use the examples below as copyable patterns. They intentionally show only short output excerpts; full command output may include richer terminal formatting.

.. list-table:: Command inputs and success signals
   :header-rows: 1

   * - Task
     - Starting input
     - Command
     - Success signal
     - File side effect
   * - Simulate one cold-entry cycle.
     - ``traffic_light.fcstm`` from the quick-start tutorial.
     - ``pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"``
     - Transcript contains ``Cycle: 0`` followed by ``Cycle: 1`` and ``Current State: TrafficLight.Red``.
     - None.
   * - Export a human inspect report.
     - Any parseable ``.fcstm`` file.
     - ``pyfcstm inspect -i traffic_light.fcstm``
     - Output begins with ``[OK] FCSTM Inspect Report`` and ends with ``No diagnostics.`` for a clean model.
     - None.
   * - Export JSON inspect data.
     - Any parseable ``.fcstm`` file.
     - ``pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json``
     - JSON contains ``metrics`` and ``diagnostics`` keys.
     - Writes ``traffic_light.inspect.json``.
   * - Generate the Python built-in template.
     - Any parseable ``.fcstm`` file.
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``
     - Output directory contains ``machine.py``, ``README.md``, and ``README_zh.md``.
     - Clears and rewrites ``generated/python``.
   * - Export PlantUML source.
     - Any parseable ``.fcstm`` file.
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``
     - File begins with ``@startuml`` and includes the root state.
     - Writes ``traffic_light.puml``.
   * - Check visualization backend.
     - No DSL input required.
     - ``pyfcstm visualize --check --renderer auto``
     - Output reports local and/or remote renderer status.
     - None.
   * - Render an SVG artifact.
     - Any parseable ``.fcstm`` file and a working renderer.
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``
     - Command reports the renderer and output path on success.
     - Writes ``traffic_light.svg``.

Short output excerpts
~~~~~~~~~~~~~~~~~~~~~

Simulation batch output should look like this, with formatting possibly changing by terminal:

.. code-block:: text

   >>> current
   Cycle: 0
   Current State: TrafficLight
   Variables:
     timer = 0
   >>> cycle
   Cycle: 1
   Current State: TrafficLight.Red

Inspect human output for the same clean model is intentionally compact:

.. code-block:: text

   [OK] FCSTM Inspect Report: traffic_light.fcstm
   Summary
     status: ok
     root: TrafficLight
     states: 4 total / 3 leaf
     diagnostics: 0 errors / 0 warnings / 0 infos

A generated Python output directory should have this minimum shape:

.. code-block:: text

   README.md
   README_zh.md
   machine.py

PlantUML source begins as text, not as an image:

.. code-block:: text

   @startuml
   hide empty description
   skinparam state {
     BackgroundColor<<pseudo>> LightGray
   }

Failure probes
~~~~~~~~~~~~~~

Use these probes when a workflow fails and you need to locate the layer quickly:

.. list-table:: Failure probes
   :header-rows: 1

   * - Probe
     - Command
     - Expected failure signal
     - Meaning
   * - Missing input option.
     - ``pyfcstm inspect``
     - ``Missing option '-i' / '--input-code'``.
     - Click did not reach DSL parsing.
   * - Invalid inspect format.
     - ``pyfcstm inspect -i traffic_light.fcstm --format xml``
     - Click reports allowed choices.
     - Fix command syntax before debugging the model.
   * - Visualization suffix mismatch.
     - ``pyfcstm visualize -i traffic_light.fcstm -o traffic_light.svg -t png --no-open``
     - Output says suffix ``.svg`` does not match ``png``.
     - Fix output naming before debugging PlantUML.
   * - Renderer availability.
     - ``pyfcstm visualize --check --renderer local``
     - Reports missing Java, PlantUML jar, or backend failure when local rendering is unavailable.
     - Configure local renderer or switch to an allowed remote renderer.



End-to-end acceptance cards
---------------------------

Use these cards when a project README, CI job, or bug report needs more than a
single command. Each card connects the command sequence to an acceptance signal
and a first repair path.

.. list-table:: Workflow acceptance cards
   :header-rows: 1

   * - Workflow
     - Commands
     - Accept when
     - Repair first
   * - Reproduce a user's current state
     - ``pyfcstm simulate -i machine.fcstm -e "current; cycle Start; current"``.
     - The transcript names the starting active path, the cycle count changes, and variables are visible.
     - If the event has no effect, inspect whether the event scope and source state match the model.
   * - Hand a model to an LLM for repair
     - ``pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md``.
     - The Markdown report includes status, metrics, diagnostics, source excerpts, and suggested repair facts.
     - If the report is empty or lacks diagnostics, rerun with human format to confirm the file being inspected.
   * - Capture a machine-readable regression artifact
     - ``pyfcstm inspect -i machine.fcstm --format json -o reports/machine.inspect.json``.
     - JSON parses successfully and contains metrics plus diagnostics arrays.
     - If a suffix warning appears, rename the target so humans do not confuse the format.
   * - Refresh generated Python code
     - ``pyfcstm generate -i machine.fcstm --template python -o generated/python --clear``.
     - ``machine.py``, ``README.md``, and ``README_zh.md`` exist, and the target directory contains only expected generated files.
     - If stale files remain, check that ``--clear`` targeted the generated directory you inspected.
   * - Produce reviewable diagram source
     - ``pyfcstm plantuml -i machine.fcstm -l normal -o diagrams/machine.puml``.
     - The file is text, begins with ``@startuml``, and can be diffed in code review.
     - If reviewers expected an image, either render with ``visualize`` or state that source review is intentional.
   * - Produce a rendered documentation image
     - ``pyfcstm visualize -i machine.fcstm -t svg -o docs/_static/machine.svg --no-open``.
     - The SVG exists and a visual inspection confirms labels are readable.
     - If rendering fails, run ``visualize --check`` before changing diagram options.

Next steps
----------

* :doc:`/how_to/generation/index` covers generated-runtime tasks.
* :doc:`/how_to/inspect/index` covers inspect workflows in more depth.
* :doc:`/how_to/visualization/index` covers diagram export choices.
