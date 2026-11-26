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
.. cli-ref-option: command=inspect option=--max-complexity-tier choices=structural,smt_linear,smt_nonlinear_decidable,smt_undecidable_heuristic default=structural
.. cli-ref-option: command=inspect option=--max-call-count-scaling choices=none,one,linear_in_states,linear_in_transitions,linear_in_vars,linear_in_leaves,quadratic_in_outgoing_per_state,quadratic_in_states,vars_times_transitions default=linear_in_transitions
.. cli-ref-option: command=inspect option=--collect-errors
.. cli-ref-option: command=inspect option=--smt-timeout-ms
.. cli-ref-option: command=inspect option=--structure-max-transitions-per-state
.. cli-ref-option: command=inspect option=--structure-max-unreachable-leaf-rate
.. cli-ref-option: command=inspect option=--structure-max-unreachable-transition-rate
.. cli-ref-option: command=inspect option=--no-structure-thresholds
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
.. cli-ref-command: name=diagram
.. cli-ref-option: command=diagram option=-i
.. cli-ref-option: command=diagram option=-o
.. cli-ref-option: command=diagram option=--format choices=json,html,svg,png,pdf
.. cli-ref-option: command=diagram option=--scale
.. cli-ref-option: command=diagram option=--open
.. cli-ref-option: command=diagram option=--help
.. cli-ref-command: name=expand-svg
.. cli-ref-option: command=expand-svg option=-i
.. cli-ref-option: command=expand-svg option=-o
.. cli-ref-option: command=expand-svg option=--help
.. cli-ref-command: name=simulate
.. cli-ref-option: command=simulate option=-i
.. cli-ref-option: command=simulate option=--input-code
.. cli-ref-option: command=simulate option=-e
.. cli-ref-option: command=simulate option=--execute
.. cli-ref-option: command=simulate option=--no-color
.. cli-ref-option: command=simulate option=--diagnostics
.. cli-ref-option: command=simulate option=--diagnostics-format choices=text,jsonl default=text
.. cli-ref-option: command=simulate option=--param
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
.. cli-ref-boundary: command=diagram stdout stderr exit-status side-effects success-signal failure-taxonomy output-formats browser
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
     - You want parser/model facts, diagnostics, and optional structural or SMT-local verify diagnostics.
   * - ``bmc``
     - FCSTM DSL file plus one FBMCQ query file
     - Polarity-aware human property verdict or versioned JSON
     - You want bounded reachability, safety, response, coverage, or call evidence with mandatory SAT replay.
   * - ``generate``
     - FCSTM DSL file plus a built-in or custom template
     - Rendered files under an output directory
     - You want target-language runtime artifacts.
   * - ``plantuml``
     - FCSTM DSL file
     - PlantUML source text
     - You want a deterministic diagram source file.
   * - ``diagram``
     - FCSTM DSL file
     - Portable JSON, a self-contained HTML viewer, or an SVG, PNG or PDF export
     - You want the shared browser diagram without a PlantUML renderer.
   * - ``expand-svg``
     - A canonical diagram SVG
     - A self-contained SVG
     - You hold an SVG whose labels are ``<text>`` and want one that needs no installed fonts.
   * - ``visualize``
     - FCSTM DSL file or renderer check request
     - Rendered ``png``, ``svg``, or ``pdf`` diagram
     - You want pyfcstm to call a PlantUML renderer.

Common command contract
-----------------------

The CLI is intentionally split between source-producing commands and commands
that may depend on external tools:

* ``simulate``, ``inspect``, ``bmc``, ``generate``, and ``plantuml`` read DSL and use
  Python-side pyfcstm functionality. They do not require Java, a PlantUML jar,
  or a network renderer.
* ``diagram`` reads DSL and uses the packaged shared renderer assets. JSON and
  HTML generation do not require MiniRacer, Node, PlantUML, or a network renderer.
* ``visualize`` first builds PlantUML source and then calls ``plantumlcli``.
  It may require Java and a PlantUML jar for local rendering or a reachable
  PlantUML server for remote rendering.
* Most successful commands exit with status ``0``. BMC additionally uses
  property-aware exit statuses ``1``, ``3``, and ``4`` for a negative bounded
  verdict, an inconclusive result, and replay mismatch respectively. Click validation failures,
  missing files, parse errors, model validation errors, rendering failures, and
  policy violations exit non-zero.
* User-facing progress and success messages are written to standard output;
  Click-formatted errors are written to standard error.
* Commands that write files create or replace only the requested output path or
  directory. ``generate --clear`` is the only command option here that
  intentionally removes existing output-directory contents before writing.

Reference-grade command examples
--------------------------------

The examples in individual command sections use ``machine.fcstm`` as a compact
placeholder. The table below anchors the same command contracts to one concrete
repository source file so reviewers can reproduce success and failure behavior
without inventing inputs.

.. list-table:: Concrete command contracts
   :header-rows: 1

   * - Command family
     - Valid example
     - Expected success evidence
     - Common invalid example
     - Expected failure boundary
   * - ``simulate``
     - ``pyfcstm simulate -i docs/source/tutorials/quick_start/traffic_light.fcstm -e "current; cycle; current"``
     - Standard output includes ``Cycle: 1`` and ``Current State: TrafficLight.Red``; no files are written.
     - ``pyfcstm simulate -i docs/source/tutorials/quick_start/traffic_light.fcstm -e "cycle MissingEvent"``
     - Simulator-command or event handling fails after parsing/model import, not during rendering.
   * - ``inspect``
     - ``pyfcstm inspect -i docs/source/tutorials/quick_start/traffic_light.fcstm --format json -o /tmp/traffic.inspect.json``
     - The output file contains ``"root_state_path": "TrafficLight"`` and ``"diagnostics": []``.
     - ``pyfcstm inspect -i docs/source/tutorials/quick_start/traffic_light.fcstm --format xml``
     - Click rejects the closed ``--format`` choice before writing a report.
   * - ``bmc``
     - ``pyfcstm bmc -i docs/source/how_to/bmc/bmc_tasks.fcstm -q docs/source/how_to/bmc/reach.fbmcq``
     - The first line is ``BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND`` and replay is verified.
     - ``pyfcstm bmc -i docs/source/how_to/bmc/bmc_tasks.fcstm -q /tmp/missing.fbmcq``
     - Query-file reading fails before compilation and emits no partial report.
   * - ``generate``
     - ``pyfcstm generate -i docs/source/tutorials/quick_start/traffic_light.fcstm --template python -o /tmp/traffic-python --clear``
     - The output directory is replaced and populated from the packaged Python template.
     - ``pyfcstm generate -i docs/source/tutorials/quick_start/traffic_light.fcstm --template python -t ./templates/python -o /tmp/bad``
     - Command validation rejects using built-in and custom template sources together.
   * - ``plantuml``
     - ``pyfcstm plantuml -i docs/source/tutorials/quick_start/traffic_light.fcstm -o /tmp/traffic.puml``
     - The requested file starts with ``@startuml`` and is deterministic text.
     - ``pyfcstm plantuml -i /tmp/missing.fcstm -o /tmp/missing.puml``
     - Input-file reading fails before any renderer is involved.
   * - ``visualize``
     - ``pyfcstm visualize --check --renderer auto``
     - The command reports local/remote backend availability and does not read a DSL file.
     - ``pyfcstm visualize --check --renderer local``
     - On a machine without a local jar configuration, renderer availability fails without parsing a model.
   * - ``visualize``
     - ``pyfcstm visualize -i docs/source/tutorials/quick_start/traffic_light.fcstm -t svg -o /tmp/traffic.svg --no-open``
     - The requested image file exists after successful backend rendering.
     - ``pyfcstm visualize -i docs/source/tutorials/quick_start/traffic_light.fcstm -t jpg -o /tmp/traffic.jpg --no-open``
     - Click rejects the closed render-type choice before rendering.

These examples are not a replacement for the exhaustive option tables below.
They show the contract shape: a valid example, the observable success signal,
an invalid example, and the layer that owns the failure.

``bmc``
-------

The BMC command has a separate exhaustive protocol reference because SAT/UNSAT
must be translated through property polarity and every SAT result crosses a
witness/replay trust boundary. See :doc:`/reference/bmc_results/index` for all
options, color behavior, streams, property verdicts, timing, exits, JSON fields,
diagnostics, witness/replay records, and packaging. See
:doc:`/reference/bmc_query/index` for the FBMCQ language.

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
* Input, parse, and model-validation failures exit non-zero before the
  simulator command layer runs.
* Command failures, such as an unknown batch command or an unresolvable event, print a message, stop subsequent commands and return nonzero.
* Typical failures are unreadable input, parse errors, model validation errors,
  unknown simulator commands, invalid event names, or invalid hot-start state
  and variable assignments.

Typical examples:

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm
   pyfcstm simulate -i machine.fcstm -e "current; cycle; current"
   pyfcstm simulate -i machine.fcstm -e "init System.Active counter=10; cycle 5"

Diagnostic options: ``--diagnostics`` defaults off; ``--diagnostics-format text|jsonl`` defaults to ``text`` and JSONL requires ``--diagnostics`` plus ``-e``; repeatable ``--param NAME=VALUE`` sets construction parameters. ``cycle --input NAME=VALUE`` supplies each complete input vector; ``decisions`` and ``why <id|label>`` query the latest evidence. See :doc:`../simulation/diagnostics` for exact types, invalid forms and runnable examples. JSONL stdout contains only ANSI-free reports; transcripts and queries go to stderr.

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
     - ``structural``, ``smt_linear``, ``smt_nonlinear_decidable``, ``smt_undecidable_heuristic``
     - Maximum structural or SMT-local verify complexity accepted by inspect.
   * - ``--max-call-count-scaling``
     - ``linear_in_transitions``
     - ``none``, ``one``, ``linear_in_states``, ``linear_in_transitions``, ``linear_in_vars``, ``linear_in_leaves``, ``quadratic_in_outgoing_per_state``, ``quadratic_in_states``, ``vars_times_transitions``
     - Maximum model-derived verify call-count scaling accepted by inspect.
   * - ``--collect-errors``
     - off
     - flag
     - Report every model error instead of stopping at the first one. The command still exits non-zero for an invalid model.
   * - ``--smt-timeout-ms``
     - unset
     - integer ``>= 0``
     - Optional Z3 timeout in milliseconds. ``0`` means no finite timeout.
   * - ``--structure-max-transitions-per-state``
     - ``6.0``
     - float
     - Advisory maximum of authored transitions per non-pseudo state in the structure statistics.
   * - ``--structure-max-unreachable-leaf-rate``
     - ``0.1``
     - float
     - Advisory maximum rate of unreachable leaf states.
   * - ``--structure-max-unreachable-transition-rate``
     - ``0.1``
     - float
     - Advisory maximum rate of unreachable authored transitions.
   * - ``--no-structure-thresholds``
     - off
     - flag
     - Disable all advisory structure-statistics thresholds.
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

``diagram``
-----------

.. code-block:: text

   pyfcstm diagram -i <input-code> [-o <output>] [--format json|html|svg|png|pdf] [--scale <factor>] [--open]

``diagram`` converts an FCSTM file into portable JSON, a self-contained HTML
viewer, or an SVG, PNG or PDF export. With no ``-o``, JSON is written to
standard output; every other format needs ``-o``. HTML output is
written to the requested path, or, when ``--open`` is used without one, to a
fresh temporary path, one per invocation. ``--open`` blocks until
the window is closed and then removes a temporary file, so nothing accumulates;
pass ``-o`` for a viewer you want to keep.

An output suffix the command cannot produce is a usage error: use ``.json``,
``.html``, ``.htm``, ``.svg``, ``.png`` or ``.pdf``, or pass ``--format`` to
choose explicitly. When ``--open`` cannot find
a browser, a path given with ``-o`` is printed before the error and the file is
left for you to open by hand. Without ``-o`` there is no such file: the temporary
one is removed, since nothing ever opened it, and the error says to re-run with
``-o PATH``.

.. list-table:: ``diagram`` options
   :header-rows: 1

   * - Option
     - Default
     - Values
     - Meaning
   * - ``-i``
     - required
     - path
     - FCSTM DSL entry file.
   * - ``-o``
     - standard output for JSON
     - path
     - Destination ``.json``, ``.html``, ``.svg``, ``.png`` or ``.pdf`` file.
   * - ``--format``
     - inferred from suffix
     - ``json``, ``html``, ``svg``, ``png``, ``pdf``
     - Explicit output format. With ``--format`` any suffix is accepted.
   * - ``--scale``
     - ``1.0`` for PNG
     - positive float, at most ``4``
     - PNG output scale. Valid for PNG output only; any other format is a usage error (``--scale is only supported for PNG output``).
   * - ``--open``
     - off
     - flag
     - Open the HTML file in a Chromium-family app window.
   * - ``-h, --help``
     - n/a
     - flag
     - Show command help.

Output and failure facts:

* JSON output is deterministic and omits absolute paths, source ranges, and
  editor selection state.
* HTML output embeds the viewer, renderer, resvg WASM, and selected locale fonts;
  it makes no network request. Browser SVG/PNG/vector PDF downloads are
  available from the HTML viewer.
* ``--open`` requires a Chromium-family browser, blocks until the window is
  closed, and then removes the document unless ``-o`` named it. Without a browser
  -- or with one that exits without showing a window, as on a machine with no
  display -- the command reports a typed capability error; the HTML survives only
  when ``-o`` named it. Use ``--format html`` without ``--open`` for file-only
  workflows.
* With ``--open`` and no ``-o`` the viewer is written 0600 inside a directory of
  your own that no other local user may look into, because it carries the model's
  source; ``--format html`` without ``-o`` is refused instead, because HTML cannot
  go to stdout. On Windows the privacy of that directory rests on ``%TEMP%`` being
  per account, which is the default: a ``TEMP`` shared between users cannot be
  detected, and with an installer from python.org the directory's mode is applied
  only from 3.12.4 onwards.
  Use ``-o`` for a document that must not be somewhere shared.
* SVG, PNG and PDF are produced by the optional rendering runtime. A missing
  runtime, an out-of-range scale and an export that exceeds the size limits are
  reported as errors and exit non-zero. These export facts come from
  ``pyfcstm/entry/diagram.py``; the examples of this page do not
  run them, because they need the rendering assets.
* Invalid formats, unknown options, unreadable input, parse/model failures, and
  missing packaged assets exit non-zero with the corresponding error category.

``expand-svg``
--------------

.. code-block:: text

   pyfcstm expand-svg -i <canonical.svg> [-o <output>]

``expand-svg`` converts a canonical diagram SVG, whose labels are ``<text>``
elements that name the fonts they want, into a self-contained SVG whose glyphs
and markers are paths. The result renders the same without installed fonts and
is no longer editable as text. ``Diagram.to_svg()`` already returns the
expanded form; this command is for an SVG produced elsewhere, such as the editor
preview.

.. list-table:: ``expand-svg`` options
   :header-rows: 1

   * - Option
     - Default
     - Values
     - Meaning
   * - ``-i``
     - required
     - path
     - Canonical diagram SVG to expand; it must be UTF-8 and contain ``<svg``.
   * - ``-o``
     - standard output
     - path
     - Destination path.
   * - ``-h, --help``
     - n/a
     - flag
     - Show command help.

Output and failure facts: an input that does not look like an SVG document is a
usage error; an unreadable or non-UTF-8 input, an unavailable rendering runtime,
or a result above the size limit is reported as an error with a non-zero exit
status. The facts come from ``pyfcstm/entry/diagram.py``; this page does not run
the command because it needs the rendering assets.

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

.. _cli-region-models:

Models with regions
-------------------

Every subcommand accepts a model with regions. The one refusal left is
``generate`` with a template that does not declare region support. The table
lists, for each subcommand, what the command does with such a model, how the
regions appear in its output, and its exit status. The model of every example is
the interlock controller of :doc:`/tutorials/regions/index`, whose root state is
``Controller`` and whose owner ``Controller.Running`` has the regions ``Safety``
and ``Motion``.

.. list-table:: Region behavior of each subcommand
   :header-rows: 1
   :widths: 14 30 36 20

   * - Command
     - What it does with regions
     - How regions appear in the output
     - Exit status
   * - ``simulate``
     - Runs the model, cold or hot started; hot start takes a configuration text
       (see :ref:`sim-region-hot-start`).
     - The position is configuration text such as
       ``Controller.Running{Safety: Watching, Motion: Off}`` in ``current``,
       after ``cycle``, in the history table and in exported files.
     - ``0``; ``1`` when a command fails (bad ``init`` position, refused event
       name, missing input).
   * - ``inspect``
     - Reports regions and the checks that concern them; ``--enable-verify``
       judges composite states branch by branch.
     - The human summary has a ``regions:`` block; the JSON report has a
       ``regions`` list (``index`` counted from 0, ``name``, ``path``,
       ``owner_path``, ``substates``, ``initial_targets``, ``aspect_before``,
       ``aspect_after``). The order diagnostics are ``I_REGION_BACKWARD_READ``
       (info) and ``W_REGION_BLIND_OVERWRITE`` (warning).
     - ``0`` also when the report carries warnings; ``1`` when the model is
       invalid.
   * - ``bmc``
     - Checks the model with the region-aware transition relation; ``active()``
       accepts a position pattern such as
       ``active("Controller.Running{Motion: On}")``; every SAT witness is
       replayed.
     - The human trace has one line per region step and prints the position of
       each frame; the JSON witness frames carry ``configuration`` and the steps
       carry ``local_cases`` (see :doc:`/reference/bmc_results/index`).
     - The BMC statuses of :doc:`/reference/bmc_results/index`: ``0`` when the
       property holds, ``1`` for a negative verdict.
   * - ``generate``
     - Renders with ``python``, ``c``, ``c_poll``, ``cpp`` and ``cpp_poll``. A
       template directory must list ``region`` under ``features`` in its
       ``config.yaml``.
     - Generated files as for any model. A refused run writes nothing: the
       output directory is not created.
     - ``0``; ``1`` for the refusal below.
   * - ``plantuml``
     - Emits PlantUML source.
     - A region is a concurrent partition: a note ``**region N: Name**`` opens
       it (``N`` counts from 1 in written order) and ``--`` separates the
       partitions of one owner.
     - ``0``.
   * - ``diagram``
     - Emits the portable JSON, or HTML, SVG, PNG or PDF.
     - Each region is a child of its owner with ``region: true`` and an
       ``ordinal`` counted from 1 in written order.
     - ``0``.
   * - ``visualize``
     - Builds the same PlantUML source as ``plantuml`` and hands it to the
       renderer, so a model with regions is drawn like any other model.
     - The partitions and ``region N: Name`` notes of the ``plantuml`` output
       appear in the rendered image. This page does not run it: it needs Java
       and a PlantUML jar or a reachable server.
     - ``0``; non-zero when no renderer is available.

``expand-svg`` has no row because it reads an SVG file, not a model.

The refusal of ``generate``:

* A custom template whose ``config.yaml`` has no ``features`` list, or a list
  without ``region``, is refused as soon as the model declares a region, before
  any file is written. The error is written to standard error with exit status
  ``1`` and has four parts: the sentence that names the template directory, the
  count and the first region, a paragraph for the template author (list
  ``features: [region]`` only when the template really renders regions) and a
  paragraph for the model author that names the built-in templates that support
  regions and prints a command with one of them.
* The same template renders a model without regions as before. Built-in
  templates are never refused.
* Listing ``region`` is a promise made by the template author; the CLI does not
  check that the template renders regions correctly. See
  :doc:`/reference/template_config/index`.

Acceptance sequence for a model with regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The commands below run one after another on the controller, in a copy of this page's directory, so no file is left behind. Where only part of an
output matters, ``...`` stands for the rest; the BMC solver timing is never included.

The commands read these files.  The controller has two regions inside ``Running``; ``Safety`` is written first, so it runs first in each cycle and ``Motion`` sees the permission of the same cycle:

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: controller.fcstm

The swapped controller is the same model with the two regions written in the opposite order; the emphasized lines are ``Motion``, which now stands in front of ``Safety`` and so sees the permission of the previous cycle:

.. literalinclude:: /_models/controller_swapped.fcstm
   :language: fcstm
   :caption: controller_swapped.fcstm
   :emphasize-lines: 12-18

The two queries of the BMC steps:

.. literalinclude:: motor_reach.fbmcq
   :language: text

.. literalinclude:: motor_needs_permit.fbmcq
   :language: text

The template directory ``listed_template`` lists ``region`` under ``features`` and writes the number of states and of regions into one file; ``plain_template``, used in the second record, is the same directory without the ``features`` line:

.. literalinclude:: listed_template/config.yaml
   :language: yaml
   :caption: listed_template/config.yaml

.. literalinclude:: listed_template/summary.txt.j2
   :language: text
   :caption: listed_template/summary.txt.j2

The first record runs the simulator.  A fault cycle turns the motor off in the same cycle:


.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   cycle --input fault=0 --input requested=1; \
   cycle /Start --input fault=0 --input requested=1; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1"
   ...
   Cycle: 2
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   ...
   Cycle: 3
   Current State: Controller.Running{Safety: Watching, Motion: On}
   ...
   Cycle: 4
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   ...

The next record inspects the controller and then the swapped one:

.. code-block:: console

   $ pyfcstm inspect -i controller.fcstm --color never
   [WARN] FCSTM Inspect Report: controller.fcstm
   ...
     regions: 2
       Controller.Running.Safety: order 0 in Controller.Running; 1 states
       Controller.Running.Motion: order 1 in Controller.Running; 2 states
   ...
   $ pyfcstm inspect -i controller_swapped.fcstm --color never
   ...
   [INFO] I_REGION_BACKWARD_READ
     Region 'Controller.Running.Motion' reads variable 'permit', which is produced by the later region 'Controller.Running.Safety'; it sees the value from the previous cycle.
   ...

The next record asks the two BMC questions of the controller:

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q motor_reach.fbmcq
   BMC reach <= 4: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Property verdict: SATISFIED WITHIN BOUND (WITNESS FOUND)
   ...
     Replay: verified (5 frames, 4 steps).
   ...
   $ pyfcstm bmc -i controller.fcstm -q motor_needs_permit.fbmcq
   BMC forbid <= 4: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   Property verdict: SATISFIED WITHIN BOUND (NO COUNTEREXAMPLE)
   ...

The next record generates code.  ``summary.txt`` shows where ``states: 7`` and ``regions: 2`` come from: the template counts ``model.walk_states()``, which yields the six states written in ``controller.fcstm`` and the gate state that the forced transition ``!Running -> Idle`` expands into, and ``model.walk_regions()``, which yields ``Safety`` and ``Motion``:

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o out
   $ LC_ALL=C ls out
   README.md
   README_zh.md
   machine.py
   $ pyfcstm generate -i controller.fcstm -t listed_template -o listed_out
   $ cat listed_out/summary.txt
   states: 7
   regions: 2

The last record of the sequence prints the PlantUML text:

.. code-block:: console

   $ pyfcstm plantuml -i controller.fcstm
   ...
       state "Running" as controller__running <<composite>> {
           note as controller__running__safety
               **region 1: Safety**
           end note
           state "Watching" as controller__running__safety__watching
           [*] --> controller__running__safety__watching
           --
           note as controller__running__motion
               **region 2: Motion**
           end note
   ...

The ``region`` and ``ordinal`` facts of the diagram are read from the same model with the public API, because ``pyfcstm diagram`` prints the whole portable JSON on one line:

.. testcode::

   from pyfcstm.model import load_state_machine_from_file

   diagram = load_state_machine_from_file("controller.fcstm").diagram().to_dict()
   running = diagram["rootState"]["children"][1]
   for child in running["children"]:
       print(child["qualifiedName"], child["region"], child["ordinal"])

.. testoutput::

   Controller.Running.Safety True 1
   Controller.Running.Motion True 2

What each block establishes:

* ``simulate``: after ``/Start`` the position has both regions; a fault cycle
  turns the motor off in the same cycle (``Motion`` is back to ``Off``).
* ``inspect``: two regions in written order; the swapped model reports
  ``I_REGION_BACKWARD_READ``.
* ``bmc``: the motor can run, and it never runs without permission; each SAT
  result is replayed.
* ``generate``: the packaged Python template writes ``machine.py`` and two
  README files; the template directory that lists ``region`` renders both the
  region count and the state count.
* ``plantuml`` and ``diagram``: the same two regions in written order, 1-based in
  both outputs.

The sequence does not run the generated ``machine.py`` and does not render the
PlantUML text or the HTML viewer; the template tests and the diagram checks own
those.

The commands that fail or report a negative result are in a second record:

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm -t plain_template -o out_plain
   generate with template directory '...plain_template' does not support region models yet. (line 12)
   ...
   $ echo $?
   1
   $ test -e out_plain || echo "out_plain was not created"
   out_plain was not created
   $ pyfcstm bmc -i controller_swapped.fcstm -q motor_needs_permit.fbmcq
   BMC forbid <= 4: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   ...
   Property verdict: NOT SATISFIED WITHIN BOUND (COUNTEREXAMPLE FOUND)
   ...
     Replay: verified (5 frames, 4 steps).
   ...
   $ echo $?
   1

The first command is the refusal: exit status ``1`` and no output directory. The
second command checks the swapped controller (the regions written in the opposite
order) against the same property: ``Motion`` runs before ``Safety`` and sees the
permission of the previous cycle, so the motor can run with ``permit == 0``; the
negative verdict exits with ``1`` and the witness is replayed.

Command evidence cards
----------------------

The tables below are deliberately example-heavy. They show short, reproducible commands and the evidence each command produces. Use them together with the option tables above: the option tables define exact forms, while these cards show how those forms behave in normal and failing runs.

Top-level command evidence
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Successful forms
   :header-rows: 1

   * - Scenario
     - Command
     - Expected signal
     - Side effect or reason
   * - Confirm the console script
     - ``pyfcstm --help``
     - Help starts with Usage and lists all public commands.
     - None
   * - Confirm module fallback
     - ``python -m pyfcstm --help``
     - Help starts with Usage: python -m pyfcstm.
     - None
   * - Record version
     - ``pyfcstm -v``
     - Output includes Pyfcstm, version and maintainer contact.
     - None

.. list-table:: Failure and boundary forms
   :header-rows: 1

   * - Situation
     - Example
     - Expected signal
     - First repair
   * - Console script missing
     - ``pyfcstm --help``
     - Shell command-not-found before pyfcstm starts.
     - Run python -m pyfcstm --help with the intended interpreter.
   * - Unknown subcommand
     - ``pyfcstm render``
     - Click reports no such command.
     - Use pyfcstm --help and choose a public command.
   * - Option on wrong command
     - ``pyfcstm --format json inspect -i machine.fcstm``
     - Click reports unknown top-level option.
     - Move command options after the subcommand.

Evidence rule:
  Treat these examples as behavior probes. If implementation output changes, update the short signal here and keep the option marker checker green.

``simulate`` evidence
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Successful forms
   :header-rows: 1

   * - Scenario
     - Command
     - Expected signal
     - Side effect or reason
   * - Deterministic batch trace
     - ``pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"``
     - Transcript includes Cycle: 0, then Cycle: 1 and the active state.
     - No file side effect.
   * - Explicit event cycle
     - ``pyfcstm simulate -i machine.fcstm -e "cycle Start; current"``
     - Transcript records the event-bearing cycle and resulting active path.
     - No file side effect.
   * - Hot start
     - ``pyfcstm simulate -i machine.fcstm -e "init System.Active counter=10; cycle; current"``
     - Run starts from the requested active path and variable values.
     - No file side effect.

.. list-table:: Failure and boundary forms
   :header-rows: 1

   * - Situation
     - Example
     - Expected signal
     - First repair
   * - Missing input
     - ``pyfcstm simulate``
     - Click reports Missing option '-i' / '--input-code'.
     - Pass the DSL file with -i.
   * - Unknown batch command
     - ``pyfcstm simulate -i machine.fcstm -e "rewind"``
     - The simulator prints the unknown command in the transcript, stops the batch and returns nonzero.
     - Use the simulation command reference.
   * - Invalid hot-start values
     - ``pyfcstm simulate -i machine.fcstm -e "init System.Active counter=oops"``
     - Hot-start validation rejects invalid assignments.
     - Provide every required variable with a typed value.

Evidence rule:
  Treat these examples as behavior probes. If implementation output changes, update the short signal here and keep the option marker checker green.

``inspect`` evidence
~~~~~~~~~~~~~~~~~~~~

.. list-table:: Successful forms
   :header-rows: 1

   * - Scenario
     - Command
     - Expected signal
     - Side effect or reason
   * - Human report
     - ``pyfcstm inspect -i traffic_light.fcstm``
     - Output begins with [OK] FCSTM Inspect Report and count summary.
     - No file side effect.
   * - JSON report
     - ``pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json``
     - JSON includes metrics, diagnostics, states, transitions, and graph sections.
     - Writes the requested JSON file.
   * - LLM Markdown report
     - ``pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md``
     - File contains compact repair-oriented facts and diagnostics.
     - Writes the requested Markdown file.
   * - Structural and SMT-local verify report
     - ``pyfcstm inspect -i machine.fcstm --enable-verify --smt-timeout-ms 2000``
     - Report includes inspect-eligible verification diagnostics.
     - No file side effect unless -o is used.

.. list-table:: Failure and boundary forms
   :header-rows: 1

   * - Situation
     - Example
     - Expected signal
     - First repair
   * - Missing input
     - ``pyfcstm inspect``
     - Click reports Missing option '-i' / '--input-code'.
     - Pass the DSL file explicitly.
   * - Invalid format
     - ``pyfcstm inspect -i machine.fcstm --format xml``
     - Click reports xml is not one of human/json/llm-json/llm-md.
     - Choose a documented format.
   * - Suffix mismatch warning
     - ``pyfcstm inspect -i machine.fcstm --format json -o machine.txt``
     - Format remains json; suffix warning is informational.
     - Use a matching suffix for clarity.

Evidence rule:
  Treat these examples as behavior probes. If implementation output changes, update the short signal here and keep the option marker checker green.

``generate`` evidence
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Successful forms
   :header-rows: 1

   * - Scenario
     - Command
     - Expected signal
     - Side effect or reason
   * - Python built-in template
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``
     - Directory contains machine.py, README.md, README_zh.md.
     - Clears and rewrites target directory.
   * - C built-in template
     - ``pyfcstm generate -i machine.fcstm --template c -o generated/c``
     - Directory contains C artifacts described by generated README.
     - Writes files; does not compile.
   * - Custom template
     - ``pyfcstm generate -i machine.fcstm -t ./templates/my_target -o generated/my_target``
     - Files follow config.yaml and .j2 output paths.
     - Writes custom output tree.

.. list-table:: Failure and boundary forms
   :header-rows: 1

   * - Situation
     - Example
     - Expected signal
     - First repair
   * - Both template inputs
     - ``pyfcstm generate -i machine.fcstm --template python -t ./templates/python -o out``
     - Command rejects conflicting template arguments.
     - Use exactly one template source.
   * - Unknown built-in template
     - ``pyfcstm generate -i machine.fcstm --template ruby -o out``
     - Template lookup reports unavailable name.
     - Use a documented built-in name.
   * - Dangerous clear
     - ``pyfcstm generate -i machine.fcstm --template python -o . --clear``
     - Request is destructive even if accepted.
     - Use a dedicated generated directory.
   * - Broken custom template
     - ``pyfcstm generate -i machine.fcstm -t ./broken_template -o out``
     - Renderer reports config, import, Jinja, or filesystem error.
     - Debug custom template before blaming DSL.

Evidence rule:
  Treat these examples as behavior probes. If implementation output changes, update the short signal here and keep the option marker checker green.

``plantuml`` evidence
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Successful forms
   :header-rows: 1

   * - Scenario
     - Command
     - Expected signal
     - Side effect or reason
   * - Write source file
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``
     - File begins with @startuml and includes the root state block.
     - Writes requested .puml file.
   * - Print source
     - ``pyfcstm plantuml -i traffic_light.fcstm``
     - stdout begins with @startuml.
     - No file side effect unless redirected.
   * - Dense review source
     - ``pyfcstm plantuml -i machine.fcstm -l full -c max_action_lines=3 -o machine.full.puml``
     - Source includes allowed lifecycle/action details.
     - Writes source only.

.. list-table:: Failure and boundary forms
   :header-rows: 1

   * - Situation
     - Example
     - Expected signal
     - First repair
   * - Unknown config key
     - ``pyfcstm plantuml -i machine.fcstm -c typo_option=true``
     - PlantUMLOptions construction rejects the key.
     - Use the closed option list.
   * - Invalid typed value
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=abc``
     - Value parser reports the offending key.
     - Use an integer or omit the option.
   * - Expecting image output
     - ``pyfcstm plantuml -i machine.fcstm -o machine.svg``
     - Command writes source text to that path, not SVG image data.
     - Use visualize -t svg for rendered images.

Evidence rule:
  Treat these examples as behavior probes. If implementation output changes, update the short signal here and keep the option marker checker green.

``visualize`` evidence
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Successful forms
   :header-rows: 1

   * - Scenario
     - Command
     - Expected signal
     - Side effect or reason
   * - Check backend
     - ``pyfcstm visualize --check --renderer auto``
     - Reports local and/or remote renderer availability.
     - Does not parse DSL or write a diagram.
   * - Render SVG in CI
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``
     - Reports renderer and output path on success.
     - Writes SVG file.
   * - Force local renderer
     - ``pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open``
     - Uses Java plus supplied PlantUML jar.
     - Writes requested or cache output.
   * - Force remote renderer
     - ``pyfcstm visualize -i machine.fcstm --renderer remote -r http://www.plantuml.com/plantuml --no-open``
     - Sends generated PlantUML source to configured service.
     - Writes rendered artifact.

.. list-table:: Failure and boundary forms
   :header-rows: 1

   * - Situation
     - Example
     - Expected signal
     - First repair
   * - Suffix/type conflict
     - ``pyfcstm visualize -i machine.fcstm -o diagram.svg -t png --no-open``
     - Fails before rendering because .svg does not match png.
     - Align suffix and --type.
   * - Missing local jar
     - ``pyfcstm visualize --check --renderer local``
     - Local check names missing PlantUML jar or Java/path failure.
     - Set PLANTUML_JAR or pass -p.
   * - Headless open
     - ``pyfcstm visualize -i machine.fcstm --open``
     - Normal open is skipped in CI/headless; strict-open makes it fatal.
     - Use --no-open for scripts.
   * - Remote unreachable
     - ``pyfcstm visualize --check --renderer remote -r http://example.invalid/plantuml``
     - Remote check reports backend/network failure.
     - Fix network/host or use local.

Evidence rule:
  Treat these examples as behavior probes. If implementation output changes, update the short signal here and keep the option marker checker green.



Per-option decision cards
-------------------------

The command examples above show whole-command behavior. The cards below zoom in
on option-level decisions so reviewers can check whether a command line is
using the right knob. Each row includes at least one legal form, one boundary or
counterexample, and the evidence that should be inspected after the run.

.. list-table:: Top-level option decisions
   :header-rows: 1

   * - Option
     - Legal forms
     - Boundary or counterexample
     - Evidence to inspect
   * - ``-h, --help``
     - ``pyfcstm --help``; ``python -m pyfcstm --help``; ``pyfcstm generate --help``.
     - ``pyfcstm --help generate`` is not the Click form used by this CLI; put ``--help`` after the subcommand.
     - Help lists ``generate``, ``inspect``, ``plantuml``, ``visualize``, and ``simulate``.
   * - ``-v, --version``
     - ``pyfcstm -v``; ``pyfcstm --version``; ``python -m pyfcstm -v``.
     - ``pyfcstm generate -v`` is not a subcommand option.
     - Standard output contains the project version and maintainer line, then exits before any subcommand runs.

.. list-table:: ``simulate`` option decisions
   :header-rows: 1

   * - Option
     - Legal forms
     - Boundary or counterexample
     - Evidence to inspect
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``; ``--input-code machines/control.fcstm``; quoted paths with spaces.
     - Omitting it is a Click error before simulator startup.
     - The first transcript lines identify the entered command and cycle state; no output files are created.
   * - ``-e, --execute``
     - ``-e "current"``; ``-e "cycle; current"``; ``-e "init Root.Leaf timer=2; cycle Start; current"``.
     - Shell quoting errors split semicolon scripts before pyfcstm receives them.
     - Batch mode exits after the script and prints a deterministic transcript suitable for logs.
   * - ``--no-color``
     - ``--no-color`` in interactive or batch mode.
     - It does not change simulator semantics or active-state selection.
     - ANSI escape sequences should be absent from the terminal transcript.

.. list-table:: ``inspect`` option decisions
   :header-rows: 1

   * - Option
     - Legal forms
     - Boundary or counterexample
     - Evidence to inspect
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``; ``--input-code imported/root.fcstm``; a path used by an editor task.
     - Missing or unreadable paths are reported as controlled CLI errors.
     - The report names the root state or the read/parse failure before any output file is trusted.
   * - ``-o, --output``
     - ``-o report.json``; ``-o reports/model.inspect.md``; no ``-o`` for stdout.
     - Missing parent directories cause write errors; a mismatched suffix may warn but does not change the selected format.
     - The target file contains exactly the selected inspect text, while warnings go to stderr.
   * - ``--format``
     - ``human`` for terminal reading; ``json`` for full machine data; ``llm-json`` and ``llm-md`` for repair prompts.
     - Values such as ``xml`` or ``yaml`` are rejected by Click.
     - Machine formats contain no ANSI color and are stable enough for scripts to parse.
   * - ``--color``
     - ``auto`` for terminals; ``always`` for forced human stdout color; ``never`` for logs.
     - Color is ignored for ``json``, ``llm-json``, ``llm-md``, and any ``-o`` file.
     - Inspect stdout for ANSI sequences only in human stdout mode.
   * - ``--enable-verify``
     - Add it when structural or SMT-local verify facts are intentionally requested.
     - It is disabled by default; enabling it does not load :mod:`pyfcstm.bmc` or parse ``.fbmcq`` queries.
     - The diagnostic sections may include verification-derived entries, but inspect remains policy-bounded.
   * - ``--max-complexity-tier``
     - ``structural``; ``smt_linear``; ``smt_nonlinear_decidable`` when the caller accepts that cost.
     - Click rejects values outside the documented choices before model parsing.
     - CLI help lists the exact accepted tiers; successful reports contain only algorithms within the selected tier.
   * - ``--max-call-count-scaling``
     - ``none``; ``one``; ``linear_in_transitions``; other allowed finite taxonomy values.
     - Click rejects values outside the documented choices before model parsing.
     - CLI help lists the exact accepted scaling values; verify results remain within the selected call-count budget.
   * - ``--smt-timeout-ms``
     - ``--smt-timeout-ms 2000``; ``--smt-timeout-ms 0``; omit it for default solver behavior.
     - Negative values are rejected by Click's integer range validation.
     - SMT-local checks receive the timeout; structural-only runs do not become exhaustive verification.

.. list-table:: ``generate`` option decisions
   :header-rows: 1

   * - Option
     - Legal forms
     - Boundary or counterexample
     - Evidence to inspect
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``; ``--input-code machines/root.fcstm``; a file with imports resolvable by the model loader.
     - Parse or model errors stop generation before template output is authoritative.
     - The output directory should not be treated as current until the command exits successfully.
   * - ``--template``
     - ``--template python``; ``--template c``; ``--template cpp_poll``.
     - Unknown names are rejected by Click because choices come from packaged template metadata.
     - Built-in templates are extracted to a temporary directory before rendering.
   * - ``-t, --template-dir``
     - ``-t ./my_template``; ``--template-dir /abs/template``; a temporary template under test control.
     - It is mutually exclusive with ``--template``.
     - Rendering reads the directory's ``config.yaml``, ``.j2`` files, static files, and ignore rules.
   * - ``-o, --output-dir``
     - ``-o generated/python``; ``--output-dir build/fcstm``; a fresh temporary directory.
     - Permission errors or missing parents surface as filesystem/template errors.
     - The directory contains generated artifacts only after successful render completion.
   * - ``--clear, --clear-directory``
     - Use with a dedicated generated directory such as ``generated/python``.
     - Do not point it at a source tree, repository root, or hand-maintained directory.
     - Previous output is removed before rendering; reviewers should inspect the target path before accepting the command.

.. list-table:: ``plantuml`` option decisions
   :header-rows: 1

   * - Option
     - Legal forms
     - Boundary or counterexample
     - Evidence to inspect
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``; ``--input-code machines/control.fcstm``; a fixture used by docs.
     - Invalid DSL prevents PlantUML source export.
     - Successful output begins with ``@startuml`` and ends with ``@enduml``.
   * - ``-o, --output``
     - ``-o traffic_light.puml``; ``-o build/diagram.txt``; omit it to print source.
     - The suffix is not interpreted as a render type; ``machine.svg`` would still receive PlantUML text.
     - Inspect the file as text, not as an image.
   * - ``-l, --level``
     - ``minimal`` for compact structure; ``normal`` for balanced review; ``full`` for lifecycle/action review.
     - Misspelled presets are rejected by Click.
     - The generated source changes only the visible PlantUML facts, not model semantics.
   * - ``-c, --config``
     - ``-c show_events=false``; ``-c max_depth=2``; ``-c state_name_format=extra_name,name``.
     - Unknown keys, malformed ``key=value``, or invalid typed values fail before source is accepted.
     - The output source should reflect the intended option, for example hidden events or collapsed depth.

.. list-table:: ``bmc`` option decisions
   :header-rows: 1

   * - Option
     - Legal forms
     - Boundary or counterexample
     - Evidence to inspect
   * - ``--cone-slicing``
     - Explicitly enable conservative slicing; disabled by default.
     - Potentially partial arithmetic and dependencies remain; abstract models skip slicing. More variables do not guarantee a removable cone.
     - Inspect ``result.cone_slicing`` when enabled; witnesses retain all variables, and skips or fallback are reported.
   * - ``--solver-profile``
     - ``default`` keeps the generic solver; ``logic`` detects arithmetic fragments; ``tactic`` uses the fixed simplification pipeline. Default: ``default``.
     - ``--solver-profile fast`` is a usage error (exit ``2``); explanations and proofs always use the default solver.
     - JSON ``result.solver_profile``, ``result.solver_logic`` and ``result.solver_statistics``; SAT witnesses must pass replay.
   * - ``--explain-infeasibility``
     - ``none`` for the mandatory verdict alone; ``formal`` for the classification and a source core; ``proof`` for a checked step-by-step proof.
     - The depth never changes the verdict, so it cannot turn an inconclusive run into a conclusive one. ``proof`` degrades to ``formal`` when no catalog rule closes the core; a caller that treats a missing ``proof`` key as an error will misread that.
     - ``Explanation:`` names the achieved depth; an ``Explanation depth: requested proof, achieved formal`` line appears whenever the request was not met. In JSON, compare ``requested_mode`` with ``achieved_mode`` under ``result.feasibility.explanation``.
   * - ``--color``
     - ``auto`` for terminals; ``never`` in logs and CI; ``always`` to keep color through a pipe, as when paging.
     - ``auto`` produces no color through a pipe, and ``NO_COLOR`` in the environment disables it even on a TTY. JSON and ``--output`` files are never decorated, whatever this option says.
     - Piping ``--color never`` yields no escape bytes; ``--color always`` keeps them; ``NO_COLOR=1`` with ``--color auto`` yields none.

.. list-table:: ``visualize`` option decisions
   :header-rows: 1

   * - Option
     - Legal forms
     - Boundary or counterexample
     - Evidence to inspect
   * - ``-i, --input-code``
     - Required for rendering: ``-i traffic_light.fcstm``; omitted only with ``--check``.
     - ``pyfcstm visualize --renderer auto`` without ``--check`` and without ``-i`` is a controlled error.
     - Render runs first build PlantUML source from the same input path used by ``plantuml``.
   * - ``-o, --output``
     - ``-o traffic_light.svg -t svg``; ``-o traffic_light -t png``; omit it for cache output.
     - A suffix/type mismatch such as ``-o diagram.svg -t png`` is rejected before rendering.
     - Suffixless paths receive the selected suffix; omitted paths use a platform cache directory.
   * - ``-l, --level`` and ``-c, --config``
     - Same source-shaping options as ``plantuml``.
     - They do not control renderer backend, file type, cache path, or viewer behavior.
     - Compare the generated image or PlantUML source to ensure the intended facts are visible.
   * - ``-t, --type``
     - ``png`` for screenshots; ``svg`` for scalable docs; ``pdf`` for printable artifacts.
     - Values such as ``jpg`` or ``xml`` are rejected by Click.
     - The backend writes an artifact with the selected extension and format.
   * - ``--renderer``
     - ``auto`` tries local then remote; ``local`` requires Java/JAR; ``remote`` uses the configured HTTP service.
     - ``auto`` may contact a remote service if local rendering fails.
     - The success message names the effective renderer used for that run.
   * - ``-j, --java``
     - ``-j /usr/bin/java``; omit it to use ``java`` from ``PATH``.
     - It matters only for local rendering, not remote rendering.
     - Local failures mention Java/path issues when the executable cannot run PlantUML.
   * - ``-p, --plantuml, --plantuml-jar``
     - ``-p ./plantuml.jar``; ``--plantuml-jar /opt/plantuml.jar``; ``PLANTUML_JAR=/opt/plantuml.jar``.
     - A missing or invalid jar makes local rendering unavailable.
     - ``visualize --check --renderer local`` reports whether the jar path is usable.
   * - ``-r, --remote-host``
     - ``-r http://www.plantuml.com/plantuml``; ``PLANTUML_HOST=https://internal.example/plantuml``.
     - Remote rendering sends generated PlantUML source to that service.
     - Use local rendering for confidential diagrams or record the allowed host in project policy.
   * - ``--check``
     - ``pyfcstm visualize --check``; ``--check --renderer local``; ``--check --renderer remote``.
     - It does not read ``-i`` and does not prove that any particular DSL file can render.
     - Exit status reports backend availability only.
   * - ``--open / --no-open``
     - ``--no-open`` for scripts and CI; default ``--open`` for desktop preview.
     - Headless environments skip viewer launch unless ``--strict-open`` is set.
     - Rendering success is separate from viewer-launch success.
   * - ``--strict-open``
     - Pair with ``--open`` when a desktop preview is the requested artifact.
     - Do not use it in CI unless a GUI opener is intentionally available.
     - Failure changes a non-fatal GUI skip into a command error after rendering.

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
   * - Simulator command layer
     - Unknown batch command or event name after the model has loaded.
     - Error transcript in text mode and nonzero batch status; JSONL mode writes errors to stderr.
     - Fix the simulator command script using the error message; batch exit status now signals failure.
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
