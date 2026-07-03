PyFCSTM Command Line Interface Guide
===============================================

pyfcstm is a powerful state machine DSL tool that provides a command-line interface for parsing, visualizing, and generating code from hierarchical finite state machines.

The most common documentation-facing commands are:

- ``pyfcstm simulate``: Run an interactive or batch simulator
- ``pyfcstm plantuml``: Generate raw PlantUML text
- ``pyfcstm visualize``: Render a final diagram file directly
- ``pyfcstm inspect``: Emit human-readable diagnostics by default, with explicit structured JSON available through ``--format json``
- ``pyfcstm generate``: Generate source code from templates

Installation
---------------------------------------

Installation Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. pip Installation** (Recommended):

.. code-block:: bash

   pip install pyfcstm

After installation, you can use the ``pyfcstm`` command directly.

**2. Module Execution**:

.. code-block:: bash

   python -m pyfcstm

**3. Pre-compiled Executable**:

Download pre-compiled versions from GitHub Releases:
https://github.com/HansBug/pyfcstm/releases

Verifying Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the installed version:

.. code-block:: bash

   pyfcstm --version

A successful installation prints the package version and maintainer metadata.

Getting Help
---------------------

The CLI provides concise help for the top-level command and every subcommand:

.. code-block:: bash

   pyfcstm --help
   pyfcstm simulate --help
   pyfcstm plantuml --help
   pyfcstm generate --help
   pyfcstm visualize --help

Use the subcommand help when you need exact option names for scripts. The
examples below keep only the stable, short command shapes; generated demo output
is refreshed by the docs resource build when full command transcripts are
needed.

Command Reference
-------------------------------------


simulate Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run a state machine directly from a DSL file. Use interactive mode for manual
exploration, or pass a semicolon-separated command chain with ``-e`` for
repeatable examples and scripts.

**Syntax**:

.. code-block:: bash

   pyfcstm simulate -i <input_file> [-e "current; cycle Start; current"] [--no-color]

**Parameters**:

- ``-i, --input-code``: Path to input state machine DSL file (required)
- ``-e, --execute``: Batch commands to execute and then exit
- ``--no-color``: Disable ANSI color output

**Examples**:

.. code-block:: bash

   # Start the interactive REPL
   pyfcstm simulate -i simple_machine.fcstm

   # Run a small batch command chain
   pyfcstm simulate -i simple_machine.fcstm -e "current; cycle; current"

The full runtime walkthrough lives in :doc:`/tutorials/simulation/index`.

plantuml Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert state machine DSL code to PlantUML format for visualization.

**Syntax**:

.. code-block:: bash

   pyfcstm plantuml -i <input_file> [-o <output_file>]

**Parameters**:

- ``-i, --input-code``: Path to input state machine DSL file (required)
- ``-o, --output``: Path to output PlantUML file (optional, outputs to stdout if not specified)

**Example 1: Simple State Machine**

Let's start with a simple state machine:

.. literalinclude:: simple_machine.fcstm
   :language: fcstm
   :caption: simple_machine.fcstm

Generate PlantUML diagram:

.. code-block:: bash

   pyfcstm plantuml -i simple_machine.fcstm -o simple_machine.puml

The generated PlantUML file can be rendered using:

- **Online**: Visit https://www.plantuml.com/plantuml/uml/ and paste the code
- **Local**: Install PlantUML (https://plantuml.com/) and run:

  .. code-block:: bash

     plantuml simple_machine.puml

**Generated State Diagram**:

.. image:: simple_machine.fcstm.puml.svg
   :alt: Simple Machine State Diagram
   :align: center

**Example 2: File Download Manager**

Here's a more complex example with hierarchical states, retry logic, and error handling:

.. literalinclude:: file_download.fcstm
   :language: fcstm
   :caption: file_download.fcstm

This example demonstrates:

- **Hierarchical states**: ``Downloading`` contains nested substates (``Connecting``, ``Transferring``, ``Paused``)
- **Retry logic**: Automatic retry with counter tracking when errors occur
- **Guard conditions**: ``Downloading -> Retrying : if [error_code != 0 && retry_count < 3]`` with complex conditional logic
- **Lifecycle actions**: ``enter`` and ``during`` actions for state initialization and continuous processing
- **Forced transitions**: ``!* -> Failed :: CriticalError`` creates emergency exit paths from all substates
- **Progress tracking**: Variables track download progress, data size, and error states

Generate the diagram:

.. code-block:: bash

   pyfcstm plantuml -i file_download.fcstm -o file_download.puml

**Generated State Diagram**:

.. image:: file_download.fcstm.puml.svg
   :alt: File Download Manager State Diagram
   :align: center
   :width: 100%

**Output to Console**

You can also output PlantUML directly to the console for quick inspection:

.. code-block:: bash

   pyfcstm plantuml -i simple_machine.fcstm

This is useful for:

- Quick verification of DSL syntax
- Piping output to other tools
- Integration with CI/CD pipelines

inspect Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inspect a state machine DSL file and emit a human-readable report by default.
Use ``--format json`` when scripts, CI jobs, or editor integrations need the
full structured model report. The JSON shape matches
``inspect_model(model).to_json()`` and includes states, transitions, variables,
metrics, derived graphs, and diagnostics. When a model uses combo transition
triggers, the report also exposes ``combo_transitions`` and ``combo_origins``
so tools can relate generated pseudo-chain edges back to the original trigger
terms.

For combo trigger diagnostics, ``inspect`` reports source-level warning codes
against the original combo terms rather than the generated pseudo states:

- ``W_COMBO_DUPLICATE_EVENT``: the same event appears more than once in one
  combo trigger. The diagnostic ``span`` points at the repeated term, and
  ``refs.first_term_span`` points at the first occurrence.
- ``W_COMBO_GUARD_CONST_TRUE`` / ``W_COMBO_GUARD_CONST_FALSE``: a combo guard is
  proven always true or always false by the Python Z3-backed analyzer. The
  diagnostic ``span`` points at the bracketed guard term, and
  ``refs.value_span`` points at the expression inside the brackets.
- ``W_COMBO_GUARD_PREFIX_IMPLIED`` / ``W_COMBO_GUARD_PREFIX_CONTRADICTS``: the
  preceding guard prefix already implies the current guard, or makes it
  impossible. The diagnostic ``span`` points at the current guard, and
  ``refs.prior_term_span`` points at the decisive earlier guard.

All combo warning ``refs`` include ``origin_id``, ``term_index``,
``transition_span``, ``trigger_span``, and the relevant term spans so editor and
UI integrations can map warnings back to the author-written DSL range.
Solver-backed guard warnings are intentionally Python-inspect diagnostics;
JavaScript-side tools should consume these JSON diagnostics instead of
re-implementing local solver approximations.

**Syntax**:

.. code-block:: bash

   pyfcstm inspect -i <input_file> [-o <output_file>] [--format human|json|llm-json|llm-md] \
     [--color auto|always|never] \
     [--enable-verify] \
     [--max-complexity-tier structural|smt_linear|smt_nonlinear_decidable|smt_undecidable_heuristic] \
     [--max-call-count-scaling linear_in_transitions] [--smt-timeout-ms <ms>]

**Parameters**:

- ``-i, --input-code``: Path to input state machine DSL file (required)
- ``-o, --output``: Path to output file (optional, outputs to stdout when not specified)
- ``--format``: Output format. ``human`` is the default; use ``json`` for the full machine-readable report. ``llm-json`` and ``llm-md`` are stable LLM-oriented repair formats using schema ``pyfcstm.inspect.llm.v1``.
- ``--color``: ANSI color policy for human output only. ``auto`` enables color only for interactive stdout, ``always`` forces color on stdout, and ``never`` disables color. ``-o`` files and machine formats are always ANSI-free.
- ``--enable-verify``: Run inspect-eligible ``pyfcstm.verify`` algorithms and append their diagnostics
- ``--max-complexity-tier``: Highest verify tier allowed by the inspect adapter; default is ``structural``
- ``--max-call-count-scaling``: Highest call-count scaling allowed by the inspect adapter; default is ``linear_in_transitions``
- ``--smt-timeout-ms``: Optional SMT timeout forwarded to SMT-local verify algorithms; ``0`` is forwarded unchanged and follows Z3 semantics, where no finite timeout is configured

**Default human output and explicit JSON**

.. code-block:: bash

   pyfcstm inspect -i simple_machine.fcstm
   pyfcstm inspect -i simple_machine.fcstm --color always
   pyfcstm inspect -i simple_machine.fcstm --format json -o simple_machine.inspect.json

By default, ``inspect`` emits a checker-style human-readable report and does not run
verify-backed checks. Human output and the stable ``llm-json`` / ``llm-md`` formats include a small source context window around each diagnostic so nearby state and transition structure remains visible; the LLM formats also include provenance, repair guidance, and do-not notes for repair loops. Use ``--format json`` for the full JSON contract aligned
with ``inspect_model(model).to_json()`` and with the existing cross-end default
diagnostics contract. If an output filename suffix looks mismatched, such as
writing the default human report to ``.json``, the CLI emits a warning on
stderr without changing the requested format. Color is purely visual: ``NO_COLOR``
with any non-empty value, ``TERM=dumb``, pipe output, and ``-o`` output all keep
human text plain, while ``json``, ``llm-json``, and ``llm-md`` never receive ANSI
escape sequences even if ``--color always`` is passed.

**Opt in to verify-backed diagnostics**

.. code-block:: bash

   pyfcstm inspect -i simple_machine.fcstm \
     --enable-verify --max-complexity-tier smt_linear --smt-timeout-ms 1000

The automatic inspect path still rejects ``bmc_search`` because BMC requires an
explicit query depth and is not a bounded local diagnostic pass. It also rejects
``k_unrollings`` and ``k_unrollings_times_branching`` call-count policies. The
CLI parses those values only to return a controlled policy error instead of
silently letting them enter automatic inspection.

visualize Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Render a state machine DSL file directly into a final diagram file and optionally open it with the system default viewer.

Compared with ``plantuml``:

- ``pyfcstm plantuml`` emits PlantUML source text and is better when you want to inspect, version, or post-process the ``.puml`` output
- ``pyfcstm visualize`` renders the final artifact directly through ``plantumlcli`` and is better for local preview or quick export to images and PDF

**Syntax**:

.. code-block:: bash

   pyfcstm visualize -i <input_file> [-o <output_file>] [-t png|svg|pdf] \
     [--renderer auto|local|remote] [--open/--no-open] [--check]

**Parameters**:

- ``-i, --input-code``: Path to input state machine DSL file (required unless ``--check`` is used)
- ``-o, --output``: Rendered diagram output path (optional, uses a cache directory when omitted)
- ``-l, --level``: PlantUML detail preset shared with ``plantuml`` (``minimal``/``normal``/``full``)
- ``-c, --config``: PlantUML option overrides in ``key=value`` format, can be specified multiple times
- ``-t, --type``: Rendered output type, one of ``png``, ``svg``, or ``pdf``
- ``--renderer``: Backend selection, one of ``auto``, ``local``, or ``remote``
- ``--check``: Check backend availability and exit without rendering
- ``--open/--no-open``: Enable or disable automatic opening after rendering
- ``--strict-open``: Treat viewer launch failure as an error
- ``-j, --java``: Java executable path for the local renderer
- ``-p, --plantuml-jar``: PlantUML jar path for the local renderer, also readable from ``PLANTUML_JAR``
- ``-r, --remote-host``: Remote PlantUML service host, also readable from ``PLANTUML_HOST``

**Examples**:

.. code-block:: bash

   # Render a PNG and let pyfcstm open it when GUI is available
   pyfcstm visualize -i simple_machine.fcstm

   # Export an SVG file without opening a viewer
   pyfcstm visualize -i simple_machine.fcstm -t svg -o simple_machine.svg --no-open

   # Check whether local or remote backends are available
   pyfcstm visualize --check --renderer auto

**Renderer behavior**

- ``auto`` tries the local PlantUML backend first and falls back to the remote backend
- ``local`` uses Java plus a PlantUML jar file
- ``remote`` uses a PlantUML server, which is useful on machines without Java

If the process runs in a headless environment such as CI, rendering still works but automatic viewer launch is skipped.

``visualize`` reuses the same ``-l/--level`` and ``-c/--config`` PlantUML output configuration as ``plantuml``. For the full option reference and rendered examples, see :doc:`/tutorials/visualization/index`.

generate Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate executable code from state machine DSL. For packaged built-in
templates, prefer ``--template``:

.. code-block:: bash

   pyfcstm generate -i <input_file> --template <python|c|c_poll|cpp|cpp_poll> \
     -o <output_dir> [--clear]

Use ``-t/--template-dir`` only when you intentionally provide a custom template
directory:

.. code-block:: bash

   pyfcstm generate -i <input_file> -t <custom_template_dir> -o <output_dir>

**Parameters**:

- ``-i, --input-code``: Path to input state machine DSL file (required)
- ``--template``: Packaged built-in template name
- ``-t, --template-dir``: Custom template directory path
- ``-o, --output-dir``: Output directory for generated code (required)
- ``--clear``: Clear output directory before generation (optional)

**Built-in template example**:

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o ./output --clear

**Custom template directory example**:

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm -t ./my_template -o ./output

The complete built-in template walkthrough lives in
:doc:`/tutorials/generation/index`. Template-author details remain in
:doc:`/tutorials/render/index`.

Common Use Cases
-------------------------------------

Workflow 1: DSL to Diagram
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Visualize your state machine design:

.. code-block:: bash

   # 1. Write your state machine DSL
   vim my_machine.fcstm

   # 2. Render a preview directly
   pyfcstm visualize -i my_machine.fcstm -t svg -o my_machine.svg --no-open

   # 3. Or generate raw PlantUML when you need the source text
   pyfcstm plantuml -i my_machine.fcstm -o my_machine.puml

The same workflow also applies to multi-file machines:

.. code-block:: bash

   pyfcstm plantuml -i ./docs/source/tutorials/dsl/import_host_mapped.fcstm \
     -o import_host_mapped.puml

Workflow 2: DSL to Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate executable code for embedded systems:

.. code-block:: bash

   # 1. Design state machine
   vim controller.fcstm

   # 2. Generate packaged C code
   pyfcstm generate -i controller.fcstm --template c -o ./src/generated --clear

   # 3. Integrate with your project
   make build

Workflow 3: Validation and Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validate DSL syntax before committing:

.. code-block:: bash

   # Quick syntax check plus human-readable diagnostics
   pyfcstm inspect -i machine.fcstm

   # Full structured JSON for CI artifacts or editor tooling
   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

   # Optional verify-backed diagnostics for CI runs that can afford SMT checks
   pyfcstm inspect -i machine.fcstm --format json --enable-verify \
     --max-complexity-tier smt_linear --smt-timeout-ms 1000 \
     -o machine.verify.inspect.json

   # Generate code from a custom test template directory when your project owns one
   pyfcstm generate -i machine.fcstm -t ./my_test_template -o ./tests/generated

For import-based projects, validate the entry file only:

.. code-block:: bash

   pyfcstm inspect -i ./docs/source/tutorials/dsl/import_host_directory.fcstm \
     --format json -o import_project.inspect.json

Workflow 4: CI/CD Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automate code generation in your build pipeline:

.. code-block:: bash

   #!/bin/bash
   # build.sh

   # Validate all DSL files
   for file in src/machines/*.fcstm; do
       echo "Validating $file..."
       pyfcstm plantuml -i "$file" > /dev/null || exit 1
   done

   # Generate code from a packaged template
   pyfcstm generate -i src/machines/main.fcstm --template python -o generated/ --clear

   # Build project
   make all

Best Practices
-------------------------------------

DSL File Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Use descriptive filenames: ``traffic_light.fcstm``, ``user_auth.fcstm``
- Keep related state machines in a dedicated directory: ``src/machines/``
- Version control your ``.fcstm`` files alongside code

Template Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Maintain separate template directories for each target language
- Use ``config.yaml`` to define language-specific expression styles
- Test templates with sample state machines before production use

Code Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Always use ``--clear`` flag in automated builds to ensure clean output
- Review generated code before committing (add to ``.gitignore`` if regenerated)
- Document which DSL files generate which output files
