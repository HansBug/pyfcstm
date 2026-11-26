.. _sec-how-to-cli-workflows:

CLI workflows
=============

Use this guide when you want a repeatable command sequence. It assumes pyfcstm
is already installed; if not, start with :doc:`/how_to/installation/index`. For
exact options and failure boundaries, use :doc:`/reference/cli/index`.

Concrete sample used below
--------------------------

The examples on this page use the checked-in quick-start source
``docs/source/tutorials/quick_start/traffic_light.fcstm``. The first command
copies it into the working directory, so every later command reads it as
``traffic_light.fcstm``. Replace that name with your own machine file in project
scripts.

Run one command first to prove that the CLI, the parser, and the model importer
all see the same source. ``...`` leaves out the statistics that this step does
not discuss:

.. code-block:: console

   $ cp docs/source/tutorials/quick_start/traffic_light.fcstm .
   $ pyfcstm inspect -i traffic_light.fcstm
   [OK] FCSTM Inspect Report: traffic_light.fcstm

   Summary
     status: ok
     root: TrafficLight
     states: 4 total / 3 leaf
     transitions: 4
   ...
     diagnostics: 0 errors / 0 warnings / 0 infos
   ...
   No diagnostics.

If the command fails before the summary, fix that layer before trying
simulation, generation, or visualization. Unreadable files, parse errors, and
model validation errors are earlier-layer problems; renderer and template
changes cannot repair them.

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

Core workflow acceptance cards
------------------------------

Use this table when turning commands into project automation. Each row gives the
minimum evidence that the step succeeded and the first thing to inspect when it
does not.

.. list-table:: CLI task acceptance cards
   :header-rows: 1

   * - Task
     - Copyable command
     - Success signal
     - File side effect
     - First troubleshooting step
   * - Simulate a short path.
     - ``pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"``
     - Output includes ``Current State: TrafficLight.Red`` after the cycle.
     - None unless stdout is redirected.
     - Run ``inspect`` first; if inspect is clean, check batch command spelling and event names.
   * - Export machine facts.
     - ``pyfcstm inspect -i traffic_light.fcstm --format json -o traffic.inspect.json``
     - JSON contains ``"root_state_path": "TrafficLight"`` and an empty ``diagnostics`` list.
     - Writes the requested report file.
     - Check ``--format`` spelling and verify-policy options before assuming the model is wrong.
   * - Generate Python files.
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o traffic-python --clear``
     - Output directory contains generated Python runtime files and generated README guidance.
     - Replaces the output directory when ``--clear`` is present.
     - Confirm exactly one of ``--template`` or ``--template-dir`` is used and that the output directory is disposable.
   * - Export PlantUML source.
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic.puml``
     - The file starts with ``@startuml`` and contains ``state "TrafficLight"``.
     - Writes only the requested ``.puml`` file.
     - If this fails, debug DSL/model errors; no renderer is involved.
   * - Check a renderer.
     - ``pyfcstm visualize --check --renderer auto``
     - Reports at least one usable renderer, or a clear backend error.
     - No DSL file is read and no diagram file is written.
     - For local failures, provide ``--plantuml-jar`` or ``PLANTUML_JAR``; for remote failures, check the remote host.
   * - Render a diagram.
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic.svg --no-open``
     - The requested SVG exists and is non-empty.
     - Writes the rendered artifact and may use renderer cache directories.
     - Run ``plantuml`` first to separate source-export failures from renderer failures.

The first four cards run as follows. The two renderer cards are not run by the
documentation checks, because they need a PlantUML renderer (Java and a jar, or
a remote service):

.. code-block:: console

   $ pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"
   ...
   Cycle: 1
   Current State: TrafficLight.Red
   ...
   $ pyfcstm inspect -i traffic_light.fcstm --format json -o traffic.inspect.json
   $ pyfcstm generate -i traffic_light.fcstm --template python -o traffic-python --clear
   $ LC_ALL=C ls traffic-python
   README.md
   README_zh.md
   machine.py
   $ pyfcstm plantuml -i traffic_light.fcstm -o traffic.puml
   $ cat traffic.puml
   @startuml
   ...
   state "TrafficLight" as traffic_light <<composite>> {
   ...
   @enduml

.. testcode::

   import json

   report = json.load(open("traffic.inspect.json"))
   print(report["root_state_path"], report["diagnostics"])

.. testoutput::

   TrafficLight []

Inspect command help
--------------------

Start with top-level help, then inspect the subcommand you intend to run:

.. code-block:: console

   $ pyfcstm --help
   Usage: pyfcstm [OPTIONS] COMMAND [ARGS]...
   ...
   $ pyfcstm inspect --help
   Usage: pyfcstm inspect [OPTIONS]
   ...
   $ pyfcstm generate --help
   Usage: pyfcstm generate [OPTIONS]
   ...
   $ python -m pyfcstm --help
   Usage: pyfcstm [OPTIONS] COMMAND [ARGS]...
   ...

Use help output as a quick sanity check for the environment. If ``pyfcstm`` is
not found, try the same environment through ``python -m pyfcstm --help``, as the
last command above does, and then return to :doc:`/how_to/installation/index`.

Run a short simulation
----------------------

Use batch mode for transcripts that belong in documentation, CI logs, or bug
reports:

.. code-block:: console

   $ pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"
   ...
   Cycle: 0
   Current State: TrafficLight
   Variables:
     timer = 0
   ...
   >>> cycle
   ...
   Cycle: 1
   Current State: TrafficLight.Red
   Variables:
     timer = 1
   ...

Use interactive mode when you are exploring manually. The documentation checks do
not run it, because it waits for a terminal:

.. code-block:: bash

   pyfcstm simulate -i traffic_light.fcstm

Practical checks:

* Start with ``current`` so the transcript records the initial active path.
* Use explicit event names in batch scripts, for example ``cycle Start``.
* Use hot start only when you can provide every required variable value.
* Do not use simulation as proof that generated target code is correct; use it
  as the reference behavior to compare against generated-runtime tests.

Export an inspect report
------------------------

Human output is useful while editing; it is the command of the first section.

Use full JSON when a script will consume metrics, diagnostics, or model facts:

.. code-block:: console

   $ pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json

.. testcode::

   import json

   report = json.load(open("traffic_light.inspect.json"))
   print("metrics" in report, "diagnostics" in report)

.. testoutput::

   True True

Use an LLM-oriented format when you plan to paste the report into a repair
prompt. The Markdown starts with the status and the diagnostic counts:

.. code-block:: console

   $ pyfcstm inspect -i traffic_light.fcstm --format llm-md -o traffic_light.inspect.md
   $ cat traffic_light.inspect.md
   # FCSTM Inspect Report

   - Status: `ok`
   - Input: `traffic_light.fcstm`
   - Diagnostics: 0 errors / 0 warnings / 0 infos
   ...

For CI-style checks, keep the command explicit and bounded. It prints nothing
and writes the report:

.. code-block:: console

   $ pyfcstm inspect -i traffic_light.fcstm \
     --format json \
     --enable-verify \
     --smt-timeout-ms 2000 \
     -o traffic_light.verify.json

If this fails before reading the model, check the verify-policy options. Inspect
parses some higher-cost taxonomy labels only to report that automatic inspect
runs are not allowed to use them.

Fix every model error in one pass
---------------------------------

By default a model error aborts the run, so a file with several of them only
ever reports the first. Add ``--collect-errors`` to get all of them in one
report. This model has two transitions to states that do not exist; the report
is cut down to its error count and the two errors:

.. code-block:: console

   $ printf '%s\n' \
     'state Machine {' \
     '    [*] -> Idle;' \
     '    state Idle;' \
     '    Idle -> Missing :: Go;' \
     '    Idle -> Absent :: Stop;' \
     '}' > two_errors.fcstm
   $ pyfcstm inspect -i two_errors.fcstm
   Invalid state machine model in two_errors.fcstm: Unknown to state 'Missing' of transition:
   Idle -> Missing :: Go; (line 4)
   $ echo $?
   1
   $ pyfcstm inspect -i two_errors.fcstm --collect-errors --color never
   ...
     diagnostics: 2 errors / 0 warnings / 0 infos
   ...
   [ERROR] E_DANGLING_TRANSITION
     Unknown to state 'Missing' of transition:
   Idle -> Missing :: Go;
     --> two_errors.fcstm:4:5
   ...
   [ERROR] E_DANGLING_TRANSITION
     Unknown to state 'Absent' of transition:
   Idle -> Absent :: Stop;
     --> two_errors.fcstm:5:5
   ...
   $ echo $?
   1

The command still exits non-zero, so it stays usable as a CI gate. The model
behind such a report may be internally inconsistent — a transition endpoint that
does not resolve, for example — so treat the report as a fix list, not as
evidence that the model is usable.

This covers model errors only. A file that does not parse has no AST to build a
model from, so a syntax error still stops the run with
``Failed to parse input DSL file`` and produces no report:

.. code-block:: console

   $ printf '%s\n' \
     'state M {' \
     '    state A;' \
     '    A -> B if [x];' \
     '}' > bad_syntax.fcstm
   $ pyfcstm inspect -i bad_syntax.fcstm --collect-errors
   Failed to parse input DSL file bad_syntax.fcstm: Found 1 errors during parsing:
   Error 1: Syntax error at line 3, column 11, near 'if': Unexpected token 'if'
   $ echo $?
   1

Generate code from a built-in template
--------------------------------------

Prefer packaged built-in templates for normal users:

.. code-block:: console

   $ pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear
   $ LC_ALL=C ls generated/python
   README.md
   README_zh.md
   machine.py

Use a custom template directory only when you intentionally maintain that
template. The documentation checks do not run this command, because it needs a
template directory of your own:

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
committed, or rendered by another tool. Choose a detail level before adding
overrides, and add narrow ``-c`` overrides only when the diagram needs them:

.. code-block:: console

   $ pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml
   $ pyfcstm plantuml -i traffic_light.fcstm -l full -o traffic_light.full.puml
   $ pyfcstm plantuml -i traffic_light.fcstm \
     -c show_events=true \
     -c max_depth=2 \
     -o traffic_light.focused.puml
   $ LC_ALL=C ls traffic_light*.puml
   traffic_light.focused.puml
   traffic_light.full.puml
   traffic_light.puml

Render a diagram artifact
-------------------------

The documentation checks do not run the commands of this section, because they
need a PlantUML renderer: Java and a jar for local rendering, or a remote
service.

Use ``visualize --check`` first when the renderer environment is uncertain:

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

Render without opening a viewer in CI or headless environments:

.. code-block:: bash

   pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open

Prefer local rendering for private diagrams:

.. code-block:: bash

   pyfcstm visualize -i traffic_light.fcstm --renderer local -p ./plantuml.jar --no-open

Use remote rendering only when the generated PlantUML source is allowed to be
sent to the configured service:

.. code-block:: bash

   pyfcstm visualize -i traffic_light.fcstm --renderer remote --no-open

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

The checks below run the commands of the table above, in the working directory
that holds ``traffic_light.fcstm``. ``...`` leaves out the terminal formatting
and the parts of the output that the success signals do not mention:

.. code-block:: console

   $ pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"
   ...
   >>> current
   ...
   Cycle: 0
   Current State: TrafficLight
   Variables:
     timer = 0
   ...
   >>> cycle
   ...
   Cycle: 1
   Current State: TrafficLight.Red
   ...
   $ pyfcstm inspect -i traffic_light.fcstm
   [OK] FCSTM Inspect Report: traffic_light.fcstm

   Summary
     status: ok
     root: TrafficLight
     states: 4 total / 3 leaf
     transitions: 4
     variables: 1
       timer: control; external supply: none
   ...
     diagnostics: 0 errors / 0 warnings / 0 infos
   ...
   No diagnostics.
   $ pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear
   $ LC_ALL=C ls generated/python
   README.md
   README_zh.md
   machine.py
   $ pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml
   $ cat traffic_light.puml
   @startuml
   hide empty description

   skinparam state {
     BackgroundColor<<pseudo>> LightGray
   ...
   }
   ...
   state "TrafficLight" as traffic_light <<composite>> {
   ...
   @enduml

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
     - ``Missing option '-i' / '--input-code'`` and exit status ``2``.
     - Click did not reach DSL parsing.
   * - Invalid inspect format.
     - ``pyfcstm inspect -i traffic_light.fcstm --format xml``
     - Click reports the allowed choices and exits with status ``2``.
     - Fix command syntax before debugging the model.
   * - Visualization suffix mismatch.
     - ``pyfcstm visualize -i traffic_light.fcstm -o traffic_light.svg -t png --no-open``
     - Output says ``Output file suffix '.svg' does not match render type 'png'.`` and the exit status is ``1``.
     - Fix output naming before debugging PlantUML.
   * - Simulator command-layer failure.
     - ``pyfcstm simulate -i traffic_light.fcstm -e "rewind"``
     - Transcript says ``Unknown command: rewind`` and batch mode exits with status ``1``.
     - Treat the transcript as the failure signal and fix the simulator command script.
   * - Renderer availability.
     - ``pyfcstm visualize --check --renderer local``
     - Reports missing Java, PlantUML jar, or backend failure when local rendering is unavailable. It depends on the machine, so the documentation checks do not run it.
     - Configure local renderer or switch to an allowed remote renderer.

The probes that do not depend on a renderer run as follows. Each failing command is followed by its exit status:

.. code-block:: console

   $ pyfcstm inspect
   Usage: pyfcstm inspect [OPTIONS]
   Try 'pyfcstm inspect --help' for help.

   Error: Missing option '-i' / '--input-code'.
   $ echo $?
   2
   $ pyfcstm inspect -i traffic_light.fcstm --format xml
   Usage: pyfcstm inspect [OPTIONS]
   Try 'pyfcstm inspect --help' for help.

   Error: Invalid value for '--format': 'xml' is not one of 'human', 'json', 'llm-json', 'llm-md'.
   $ echo $?
   2
   $ pyfcstm visualize -i traffic_light.fcstm -o traffic_light.svg -t png --no-open
   Output file suffix '.svg' does not match render type 'png'.
   $ echo $?
   1
   $ pyfcstm simulate -i traffic_light.fcstm -e "rewind"
   ...
   >>> rewind
   ...
   Unknown command: rewind. Type 'help' for available commands.
   $ echo $?
   1

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

Accept a model with regions end to end
--------------------------------------

**Input.** :download:`controller.fcstm </_models/controller.fcstm>` (the interlock
controller from :doc:`/tutorials/regions/index`) and ``region_motion.fbmcq``.  The task is
to take one model with regions through every command of the package and to
know what each step must show before you accept the model.

.. literalinclude:: region_motion.fbmcq
   :language: text
   :caption: region_motion.fbmcq

**Command or code.** The six steps run in order; each step shows only the lines that carry the
acceptance signal, and ``...`` leaves out the rest:

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   cycle --input fault=0 --input requested=1; \
   cycle /Start --input fault=0 --input requested=1; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1"
   ...
   Cycle: 1
   Current State: Controller.Idle
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
   $ pyfcstm inspect -i controller.fcstm --color never
   [WARN] FCSTM Inspect Report: controller.fcstm

   Summary
     status: warning
     root: Controller
     states: 6 total / 4 leaf
     transitions: 7
     regions: 2
       Controller.Running.Safety: order 0 in Controller.Running; 1 states
       Controller.Running.Motion: order 1 in Controller.Running; 2 states
     variables: 4
       fault: input; external supply: cycle
       requested: input; external supply: cycle
       permit: control; external supply: none
       motor: output; external supply: none
   ...
     diagnostics: 0 errors / 4 warnings / 0 infos
   ...
   [WARN] W_DURING_CONST_ASSIGN
   ...
   [WARN] W_DURING_CONST_ASSIGN
   ...
   [WARN] W_DURING_CONST_ASSIGN
   ...
   [WARN] W_LEAF_NO_OUTGOING_TRANSITION
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_motion.fbmcq --json -o bmc.json

.. testcode::

   import json

   payload = json.load(open("bmc.json", encoding="utf-8"))
   print(payload["result"]["status"], payload["result"]["outcome"], "replay ok:", payload["replay"]["ok"])
   for frame in payload["witness"]["frames"]:
       print("frame %d: %s" % (frame["index"], frame["configuration"]))

.. testoutput::

   sat witness_found replay ok: True
   frame 0: Controller.Idle
   frame 1: Controller.Running{Safety: Watching, Motion: Off}
   frame 2: Controller.Running{Safety: Watching, Motion: On}

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o generated/python --clear
   $ LC_ALL=C ls generated/python
   README.md
   README_zh.md
   machine.py
   $ pyfcstm plantuml -i controller.fcstm -o machine.puml
   $ cat machine.puml
   @startuml
   ...
           note as controller__running__safety
               **region 1: Safety**
   ...
           --
           note as controller__running__motion
               **region 2: Motion**
   ...
   $ pyfcstm diagram -i controller.fcstm -o machine.json
   machine.json

.. testcode::

   import json

   print(json.load(open("machine.json"))["summary"])

.. testoutput::

   {'actions': 4, 'events': 2, 'states': 6, 'transitions': 7, 'variables': 4}

**Expected signal.** Accept the model when each step shows what follows.

1. *simulate.* The position is printed as configuration text.  Cycle 1 is
   ``Controller.Idle``; the ``/Start`` event enters ``Running`` with both
   regions initialized in writing order (``Motion: Off``); the next cycle turns
   ``Motion`` on; ``fault=1`` turns it off in the same cycle.
2. *inspect.* The summary lists ``regions: 2`` with their order (``order 0`` is
   ``Safety``) and the variables.  ``status: warning`` comes from the four
   ordinary warnings on the ``diagnostics:`` line, three constant ``during``
   assignments and one leaf without an outgoing transition, not from the regions.
3. *bmc.* ``sat witness_found``, ``replay ok: True``, and frames whose
   configurations are the positions the simulation visited.  Every satisfying
   witness is replayed on the simulator before the verdict is reported.
4. *generate.* ``machine.py`` and the two README files exist.
5. *plantuml.* One ``--`` and two ``region N:`` notes, in writing order.
6. *diagram.* The JSON summary counts the same states and transitions as
   ``inspect`` (6 states, 7 transitions).

**File side effect.** These commands write ``bmc.json``, ``generated/python``, ``machine.puml`` and
``machine.json`` into the current directory.  In a project, ``generate`` writes the runtime into the output
directory, and the ``-o`` options write the named files.

**First failure check.** Run the steps one at a time and stop at the first one
that disagrees.  If steps 1 and 3 disagree on a position, the model changed
between runs or the query starts from a different position; if step 2 fails,
read its first error before anything else, because the other commands read the
same model.

**Reference link.** :doc:`/reference/cli/index`; the modeling tasks are on
:doc:`/how_to/regions/index`.

Next steps
----------

* :doc:`/how_to/generation/index` covers generated-runtime tasks.
* :doc:`/how_to/inspect/index` covers inspect workflows in more depth.
* :doc:`/how_to/visualization/index` covers diagram export choices.
