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

Next steps
----------

* :doc:`/how_to/generation/index` covers generated-runtime tasks.
* :doc:`/how_to/inspect/index` covers inspect workflows in more depth.
* :doc:`/how_to/visualization/index` covers diagram export choices.
