.. _sec-reference-cli:

CLI reference
=============

This page is the exact command reference for the public ``pyfcstm`` command.
It records option names, accepted values, output channels, side effects, and
failure boundaries. Use :doc:`/how_to/cli_workflows/index` for task recipes and
:doc:`/reference/visualization_options/index` for the shared PlantUML option
schema.

The synchronization markers below are comments consumed by
``tools/check_cli_reference_docs.py``. They keep this reference aligned with the
Click command tree and with the documented human-only boundary facts.

.. cli-ref-command: name=generate
.. cli-ref-option: command=generate option=-i
.. cli-ref-option: command=generate option=--input-code
.. cli-ref-option: command=generate option=-t
.. cli-ref-option: command=generate option=--template-dir
.. cli-ref-option: command=generate option=--template choices=c,c_poll,cpp,cpp_poll,python
.. cli-ref-option: command=generate option=-o
.. cli-ref-option: command=generate option=--output-dir
.. cli-ref-option: command=generate option=--clear
.. cli-ref-option: command=generate option=--clear-directory
.. cli-ref-option: command=generate option=--help
.. cli-ref-command: name=inspect
.. cli-ref-option: command=inspect option=-i
.. cli-ref-option: command=inspect option=--input-code
.. cli-ref-option: command=inspect option=-o
.. cli-ref-option: command=inspect option=--output
.. cli-ref-option: command=inspect option=--format choices=human,json,llm-json,llm-md default=human
.. cli-ref-option: command=inspect option=--color choices=auto,always,never default=auto
.. cli-ref-option: command=inspect option=--enable-verify
.. cli-ref-option: command=inspect option=--max-complexity-tier choices=structural,smt_linear,smt_nonlinear_decidable,smt_undecidable_heuristic,bmc_search default=structural
.. cli-ref-option: command=inspect option=--max-call-count-scaling choices=none,one,linear_in_states,linear_in_transitions,linear_in_vars,linear_in_leaves,quadratic_in_outgoing_per_state,quadratic_in_states,vars_times_transitions,k_unrollings,k_unrollings_times_branching default=linear_in_transitions
.. cli-ref-option: command=inspect option=--smt-timeout-ms
.. cli-ref-option: command=inspect option=--help
.. cli-ref-command: name=plantuml
.. cli-ref-option: command=plantuml option=-i
.. cli-ref-option: command=plantuml option=--input-code
.. cli-ref-option: command=plantuml option=-o
.. cli-ref-option: command=plantuml option=--output
.. cli-ref-option: command=plantuml option=-l choices=minimal,normal,full default=normal
.. cli-ref-option: command=plantuml option=--level choices=minimal,normal,full default=normal
.. cli-ref-option: command=plantuml option=-c
.. cli-ref-option: command=plantuml option=--config
.. cli-ref-option: command=plantuml option=--help
.. cli-ref-command: name=simulate
.. cli-ref-option: command=simulate option=-i
.. cli-ref-option: command=simulate option=--input-code
.. cli-ref-option: command=simulate option=-e
.. cli-ref-option: command=simulate option=--execute
.. cli-ref-option: command=simulate option=--no-color
.. cli-ref-option: command=simulate option=--help
.. cli-ref-command: name=visualize
.. cli-ref-option: command=visualize option=-i
.. cli-ref-option: command=visualize option=--input-code
.. cli-ref-option: command=visualize option=-o
.. cli-ref-option: command=visualize option=--output
.. cli-ref-option: command=visualize option=-l choices=minimal,normal,full default=normal
.. cli-ref-option: command=visualize option=--level choices=minimal,normal,full default=normal
.. cli-ref-option: command=visualize option=-c
.. cli-ref-option: command=visualize option=--config
.. cli-ref-option: command=visualize option=-t choices=png,svg,pdf default=png
.. cli-ref-option: command=visualize option=--type choices=png,svg,pdf default=png
.. cli-ref-option: command=visualize option=--renderer choices=local,remote,auto default=auto
.. cli-ref-option: command=visualize option=-j
.. cli-ref-option: command=visualize option=--java
.. cli-ref-option: command=visualize option=-p
.. cli-ref-option: command=visualize option=--plantuml
.. cli-ref-option: command=visualize option=--plantuml-jar
.. cli-ref-option: command=visualize option=-r
.. cli-ref-option: command=visualize option=--remote-host
.. cli-ref-option: command=visualize option=--check
.. cli-ref-option: command=visualize option=--open
.. cli-ref-option: command=visualize option=--no-open
.. cli-ref-option: command=visualize option=--strict-open
.. cli-ref-option: command=visualize option=--help
.. cli-ref-option: command=top-level option=--version
.. cli-ref-option: command=top-level option=--help
.. cli-ref-boundary: command=generate stdout stderr exit-status side-effects success-signal failure-taxonomy clear
.. cli-ref-boundary: command=inspect stdout stderr exit-status side-effects success-signal failure-taxonomy output-formats verify-policy
.. cli-ref-boundary: command=plantuml stdout stderr exit-status side-effects success-signal failure-taxonomy source-only
.. cli-ref-boundary: command=simulate stdout stderr exit-status side-effects success-signal failure-taxonomy interactive batch
.. cli-ref-boundary: command=visualize stdout stderr exit-status side-effects success-signal failure-taxonomy cache suffix open headless check-mode

Top-level command
-----------------

.. code-block:: text

   pyfcstm [OPTIONS] COMMAND [ARGS]...

.. list-table:: Top-level options
   :header-rows: 1

   * - Option
     - Meaning
     - Notes
   * - ``-v, --version``
     - Show pyfcstm version information.
     - Read-only, exits after printing version text.
   * - ``-h, --help``
     - Show help and exit.
     - Available on the top-level command and every subcommand.

.. list-table:: Commands
   :header-rows: 1

   * - Command
     - Primary input
     - Primary output
     - Use when
   * - ``simulate``
     - FCSTM DSL file
     - Interactive console transcript or batch transcript
     - You want to execute model semantics without generating target code.
   * - ``inspect``
     - FCSTM DSL file
     - Human text, JSON, LLM JSON, or LLM Markdown
     - You want parser/model facts, diagnostics, and optional bounded verify diagnostics.
   * - ``generate``
     - FCSTM DSL file plus a built-in or custom template
     - Rendered files under an output directory
     - You want target-language runtime artifacts.
   * - ``plantuml``
     - FCSTM DSL file
     - PlantUML source text
     - You want a deterministic diagram source file.
   * - ``visualize``
     - FCSTM DSL file or renderer check request
     - Rendered ``png``, ``svg``, or ``pdf`` diagram
     - You want pyfcstm to call a PlantUML renderer.

Common command contract
-----------------------

The CLI is intentionally split between source-producing commands and commands
that may depend on external tools:

* ``simulate``, ``inspect``, ``generate``, and ``plantuml`` read DSL and use
  Python-side pyfcstm functionality. They do not require Java, a PlantUML jar,
  or a network renderer.
* ``visualize`` first builds PlantUML source and then calls ``plantumlcli``.
  It may require Java and a PlantUML jar for local rendering or a reachable
  PlantUML server for remote rendering.
* A successful command exits with status ``0``. Click validation failures,
  missing files, parse errors, model validation errors, rendering failures, and
  policy violations exit non-zero.
* User-facing progress and success messages are written to standard output;
  Click-formatted errors are written to standard error.
* Commands that write files create or replace only the requested output path or
  directory. ``generate --clear`` is the only command option here that
  intentionally removes existing output-directory contents before writing.

``simulate``
------------

.. code-block:: text

   pyfcstm simulate -i <input-code> [-e "current; cycle; current"] [--no-color]

``simulate`` constructs the model and runs the Python simulator. Without
``-e`` it starts the interactive console. With ``-e`` it executes a
semicolon-separated command script and exits.

.. list-table:: ``simulate`` options
   :header-rows: 1

   * - Option
     - Required
     - Value
     - Meaning
   * - ``-i, --input-code``
     - yes
     - path
     - FCSTM DSL entry file.
   * - ``-e, --execute``
     - no
     - string
     - Batch simulator commands such as ``"current; cycle Start; current"``.
   * - ``--no-color``
     - no
     - flag
     - Disable color in interactive/human console output.
   * - ``-h, --help``
     - no
     - flag
     - Show command help.

Output and failure facts:

* Interactive mode prints prompts and state/runtime information to standard
  output and waits for user commands.
* Batch mode prints the command results to standard output and returns after
  the script finishes.
* The command has no file side effects unless invoked from shell redirection.
* Typical failures are unreadable input, parse errors, model validation errors,
  unknown simulator commands, invalid event names, or invalid hot-start state
  and variable assignments.

Typical examples:

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm
   pyfcstm simulate -i machine.fcstm -e "current; cycle; current"
   pyfcstm simulate -i machine.fcstm -e "init System.Active counter=10; cycle 5"

``inspect``
-----------

.. code-block:: text

   pyfcstm inspect -i <input-code> [-o <output>] [--format human|json|llm-json|llm-md]

``inspect`` reports what the parser and model importer know about a DSL file.
It is diagnostic and fact-oriented: it does not execute a simulator trace and it
does not prove generated target code.

.. list-table:: ``inspect`` options
   :header-rows: 1

   * - Option
     - Default
     - Values
     - Meaning
   * - ``-i, --input-code``
     - required
     - path
     - FCSTM DSL entry file.
   * - ``-o, --output``
     - standard output
     - path
     - Output file. A suffix mismatch may produce a warning, not a different format.
   * - ``--format``
     - ``human``
     - ``human``, ``json``, ``llm-json``, ``llm-md``
     - Output format. Use ``json`` for the complete machine-readable report.
   * - ``--color``
     - ``auto``
     - ``auto``, ``always``, ``never``
     - ANSI color policy for ``human`` output only.
   * - ``--enable-verify``
     - off
     - flag
     - Include inspect-eligible verification diagnostics.
   * - ``--max-complexity-tier``
     - ``structural``
     - ``structural``, ``smt_linear``, ``smt_nonlinear_decidable``, ``smt_undecidable_heuristic``, ``bmc_search``
     - Maximum verify complexity accepted by inspect. ``bmc_search`` is parsed only to report the policy error.
   * - ``--max-call-count-scaling``
     - ``linear_in_transitions``
     - ``none``, ``one``, ``linear_in_states``, ``linear_in_transitions``, ``linear_in_vars``, ``linear_in_leaves``, ``quadratic_in_outgoing_per_state``, ``quadratic_in_states``, ``vars_times_transitions``, ``k_unrollings``, ``k_unrollings_times_branching``
     - Maximum inspect-eligible verify call-count scaling. ``k_unrollings`` labels are parsed only to report the policy error.
   * - ``--smt-timeout-ms``
     - unset
     - integer ``>= 0``
     - Optional Z3 timeout in milliseconds. ``0`` means no finite timeout.
   * - ``-h, --help``
     - n/a
     - flag
     - Show command help.

Output and failure facts:

* ``human`` is for terminals and humans; ``json`` is the full structured report;
  ``llm-json`` and ``llm-md`` are stable, compact repair-oriented views.
* Machine formats never include ANSI color. Human output written to a file is
  also colorless even if ``--color always`` is requested.
* Successful file output writes exactly the requested report file. Standard
  output is used when ``-o`` is omitted.
* Verify policy knobs are validated before the input file is parsed. This makes
  forbidden expensive modes fail fast instead of doing hidden heavy work.

Typical examples:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm
   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json
   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md
   pyfcstm inspect -i machine.fcstm --enable-verify --smt-timeout-ms 2000

``generate``
------------

.. code-block:: text

   pyfcstm generate -i <input-code> --template <name> -o <output-dir> [--clear]
   pyfcstm generate -i <input-code> -t <template-dir> -o <output-dir> [--clear]

``generate`` renders target artifacts from the semantic model. It accepts either
a packaged built-in template name or an explicit custom template directory.
Do not pass both ``--template`` and ``--template-dir``.

.. list-table:: ``generate`` options
   :header-rows: 1

   * - Option
     - Required
     - Values
     - Meaning
   * - ``-i, --input-code``
     - yes
     - path
     - FCSTM DSL entry file.
   * - ``--template``
     - one of template name or template directory
     - ``python``, ``c``, ``c_poll``, ``cpp``, ``cpp_poll``
     - Packaged built-in template.
   * - ``-t, --template-dir``
     - one of template name or template directory
     - path
     - Custom template directory maintained by the caller.
   * - ``-o, --output-dir``
     - yes
     - path
     - Destination directory for rendered files.
   * - ``--clear, --clear-directory``
     - no
     - flag
     - Remove existing output-directory contents before rendering.
   * - ``-h, --help``
     - no
     - flag
     - Show command help.

Output and failure facts:

* Standard output is normally limited to CLI progress/errors from Click and the
  renderer; the generated artifacts are written under ``--output-dir``.
* Built-in templates are extracted from packaged template assets first, then
  rendered through the same renderer path as custom templates.
* ``--clear`` is destructive for the output directory. Use it only for a
  generated directory that is safe to replace.
* Typical failures are missing input, parse/model errors, a missing or invalid
  template, Jinja rendering errors, invalid output permissions, or mutually
  inconsistent template arguments.

Typical examples:

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated/python --clear
   pyfcstm generate -i machine.fcstm --template c -o generated/c
   pyfcstm generate -i machine.fcstm -t ./my_template -o generated/custom --clear

``plantuml``
------------

.. code-block:: text

   pyfcstm plantuml -i <input-code> [-o <output>] [-l minimal|normal|full] [-c key=value]

``plantuml`` emits PlantUML source text only. It does not render images, does
not call Java, and does not contact a remote PlantUML service.

.. list-table:: ``plantuml`` options
   :header-rows: 1

   * - Option
     - Default
     - Values
     - Meaning
   * - ``-i, --input-code``
     - required
     - path
     - FCSTM DSL entry file.
   * - ``-o, --output``
     - standard output
     - path
     - Output file for PlantUML source.
   * - ``-l, --level``
     - ``normal``
     - ``minimal``, ``normal``, ``full``
     - Detail preset shared with ``visualize``.
   * - ``-c, --config``
     - none
     - ``key=value``; repeatable
     - Fine-grained PlantUML option override.
   * - ``-h, --help``
     - n/a
     - flag
     - Show command help.

Output and failure facts:

* With ``-o``, the command writes PlantUML source to the requested file. Without
  ``-o``, it prints source to standard output.
* ``-c`` accepts the typed value grammar in
  :doc:`/reference/visualization_options/index`.
* Typical failures are unreadable input, parse/model errors, unknown PlantUML
  option keys, value parsing errors, or invalid ``PlantUMLOptions`` values.

Typical examples:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml
   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml
   pyfcstm plantuml -i machine.fcstm -c show_events=true -c max_depth=2

``visualize``
-------------

.. code-block:: text

   pyfcstm visualize -i <input-code> [-o <output>] [-t png|svg|pdf] [--renderer auto|local|remote]
   pyfcstm visualize --check [--renderer auto|local|remote]

``visualize`` builds PlantUML source and asks ``plantumlcli`` to render a final
file. Use it for local preview or documentation artifacts when the renderer
backend is part of the workflow.

.. list-table:: ``visualize`` options
   :header-rows: 1

   * - Option
     - Default
     - Values
     - Meaning
   * - ``-i, --input-code``
     - required unless ``--check`` is used
     - path
     - FCSTM DSL entry file.
   * - ``-o, --output``
     - cache path
     - path
     - Rendered output file. If omitted, pyfcstm writes under its visualize cache directory.
   * - ``-l, --level``
     - ``normal``
     - ``minimal``, ``normal``, ``full``
     - Detail preset shared with ``plantuml``.
   * - ``-c, --config``
     - none
     - ``key=value``; repeatable
     - Fine-grained PlantUML option override.
   * - ``-t, --type``
     - ``png``
     - ``png``, ``svg``, ``pdf``
     - Rendered diagram type.
   * - ``--renderer``
     - ``auto``
     - ``local``, ``remote``, ``auto``
     - Backend selection. ``auto`` tries local, then remote.
   * - ``-j, --java``
     - ``java`` from ``PATH``
     - path
     - Java executable for local rendering.
   * - ``-p, --plantuml, --plantuml-jar``
     - ``PLANTUML_JAR`` or unset
     - path
     - PlantUML jar path for local rendering.
   * - ``-r, --remote-host``
     - ``PLANTUML_HOST`` or public PlantUML server
     - URL
     - Remote PlantUML server base URL.
   * - ``--check``
     - off
     - flag
     - Check renderer availability and exit without reading a DSL file.
   * - ``--open / --no-open``
     - ``--open``
     - flag pair
     - Open or do not open the rendered file with the system default viewer.
   * - ``--strict-open``
     - off
     - flag
     - Treat viewer-launch failure as an error.
   * - ``-h, --help``
     - n/a
     - flag
     - Show command help.

Output and failure facts:

* A successful render prints the effective renderer and output path.
* If ``-o`` is omitted, the output file is created in a platform cache directory:
  ``$XDG_CACHE_HOME/pyfcstm/visualize`` or ``~/.cache/pyfcstm/visualize`` on
  Linux, ``~/Library/Caches/pyfcstm/visualize`` on macOS, and
  ``%LOCALAPPDATA%\\pyfcstm\\visualize`` on Windows.
* If ``-o`` has a suffix, the suffix must match ``--type``. A suffixless output
  path receives the selected suffix automatically.
* ``--check`` exits ``0`` when the requested backend is available. For
  ``--renderer auto``, either local or remote availability is enough.
* ``--open`` is skipped automatically in headless environments such as CI,
  ``PYFCSTM_NO_GUI`` truthy environments, or Linux sessions without display
  variables. With ``--strict-open``, that skip becomes a command failure.
* Remote rendering sends generated PlantUML text to the configured PlantUML
  server. Use ``--renderer local`` for diagrams that must not leave the machine.

Typical examples:

.. code-block:: bash

   pyfcstm visualize --check --renderer auto
   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open
   pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open
   pyfcstm visualize -i machine.fcstm --renderer remote -r http://www.plantuml.com/plantuml --no-open

Failure taxonomy
----------------

.. list-table:: Common failures
   :header-rows: 1

   * - Area
     - Example cause
     - Typical signal
     - First fix
   * - Input file
     - File path does not exist or cannot be read.
     - Non-zero exit with a Click error or Python parse/read error.
     - Check the path and working directory.
   * - DSL syntax
     - Invalid FCSTM grammar.
     - Grammar parse diagnostics with source location.
     - Run ``inspect`` for a diagnostic report and fix the DSL.
   * - Model import
     - Duplicate state names, invalid transitions, unresolved refs, or invalid declarations.
     - Model validation diagnostics.
     - Fix semantic issues in the DSL before rendering/generation.
   * - Output path
     - Permission denied, suffix mismatch, or unsafe ``--clear`` target.
     - Non-zero exit before or during file write.
     - Use a writable path and align ``visualize -o`` suffix with ``--type``.
   * - Template rendering
     - Missing template, bad ``config.yaml``, or Jinja rendering error.
     - Non-zero ``generate`` exit.
     - Prefer built-in ``--template`` first; debug custom templates separately.
   * - Verify policy
     - ``inspect`` requested a forbidden complexity or unrolling budget.
     - Policy error before model parsing.
     - Keep automatic inspect checks within structural/linear budgets.
   * - Renderer backend
     - Missing ``plantumlcli``, Java, PlantUML jar, or network service.
     - ``visualize --check`` or render failure.
     - Configure local rendering or use an allowed remote renderer.
