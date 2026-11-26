.. _sec-how-to-simulation:

Simulation tasks
================

Use this page when you already have an FCSTM model and need to run a concrete
simulation task.  For the first guided run, start with
:doc:`../../tutorials/simulation/index`.  For execution-order reasoning, see
:doc:`../../explanations/execution_semantics/index`.  For exact command forms,
settings, export formats and Python API boundaries, see
:doc:`../../reference/simulation/index`.

Quick command reminder
----------------------

This section is a task reminder.  The complete lookup tables live in
:doc:`../../reference/simulation/index`.

``pyfcstm simulate`` currently exposes a small CLI surface:

.. list-table:: ``pyfcstm simulate`` options
   :header-rows: 1

   * - Option
     - Meaning
   * - ``-i`` / ``--input-code TEXT``
     - Entry FCSTM file.  This option is required.
   * - ``-e`` / ``--execute TEXT``
     - Run semicolon-separated batch commands instead of starting the REPL.
   * - ``--no-color``
     - Disable ANSI color in command output.
   * - ``-h`` / ``--help``
     - Show the CLI help text.

The batch string and the REPL share the same command names.  The most useful
commands are:

.. list-table:: Simulator commands
   :header-rows: 1

   * - Command
     - Use it for
   * - ``cycle [count] [events...]``
     - Execute one or more cycles.  Omit ``count`` for one cycle; event names
       such as ``cycle Start`` are passed to that cycle.
   * - ``current``
     - Show the current cycle, current state and persistent variables.
   * - ``events``
     - Show events available from the current state.
   * - ``history [n|all]``
     - Show recent history rows or the full retained history.
   * - ``init <position> [var=value...]``
     - Rebuild the runtime as a hot start at a state, or at a configuration text for a model with regions, with explicit variables.
   * - ``setting [key] [value]``
     - Show or change display/history/logging settings.
   * - ``export <path>``
     - Export history; the format is inferred from the file extension.
   * - ``clear``
     - Reset the runtime using the current settings.
   * - ``help``
     - Show command help.
   * - ``quit`` / ``exit``
     - Leave the REPL.

Run batch commands
------------------

Use ``-e`` when you want a reproducible transcript in CI, docs or bug reports.
Separate commands with semicolons:

.. code-block:: bash

   pyfcstm simulate -i docs/source/tutorials/cli/simple_machine.fcstm \
     -e "cycle; events; cycle Start; current; cycle Stop; history 3" \
     --no-color

The generated transcript used by the short tutorial is kept here:

.. literalinclude:: ../../tutorials/simulation/cli_batch.demo.sh.txt
   :language: text

Use the interactive REPL
------------------------

Omit ``-e`` to start the REPL:

.. code-block:: bash

   pyfcstm simulate -i docs/source/tutorials/cli/simple_machine.fcstm --no-color

Then type commands one at a time:

.. code-block:: text

   cycle
   events
   cycle Start
   current
   history 3
   quit

Interactive mode adds command history, completion and suggestions, but command
semantics are the same as batch mode.

Inject events
-------------

A command such as ``cycle Start`` injects an event into that cycle.  In Python,
pass the event list to ``SimulationRuntime.cycle``:

.. literalinclude:: ../../tutorials/simulation/event_triggering.demo.py
   :language: python
   :caption: Event injection through the Python runtime

Output:

.. literalinclude:: ../../tutorials/simulation/event_triggering.demo.py.txt
   :language: text

Event names in examples rely on DSL event scoping.  For syntax facts, use
:doc:`../../reference/dsl/index`; this page only covers how the simulator
receives events.  For supported runtime event input forms and event-accounting
fields in ``CycleResult``, use :doc:`../../reference/simulation/index`.

Hot start at a state
--------------------

Use the REPL ``init`` command when you need to inspect a later state without
replaying all earlier cycles:

.. code-block:: text

   init System.Active counter=10 flag=1
   cycle
   current

Use the Python API when embedding the same idea in tests:

.. code-block:: python

   runtime = SimulationRuntime(
       sm,
       initial_state="System.Active",
       initial_vars={"counter": 10, "flag": 1},
   )

Hot start has deliberate boundaries:

* ``initial_vars`` must provide every declared persistent variable.
* enter actions are skipped for the pre-built path.
* during actions run normally after the first cycle starts.
* hot-start construction performs only structural checks. A first cycle with
  no committable stoppable successor is a successful Delta step; expression,
  event, and DFS errors are still reported on that cycle.

Implement abstract handlers
---------------------------

Abstract lifecycle actions are implemented by registering Python handlers.  Use
``@abstract_handler`` on methods whose names can be arbitrary; the decorator
argument names the DSL action path:

.. literalinclude:: ../../tutorials/simulation/abstract_handlers.demo.py
   :language: python
   :caption: Abstract handlers in a simulation runtime

Output:

.. literalinclude:: ../../tutorials/simulation/abstract_handlers.demo.py.txt
   :language: text

Handler context is read-only.  Typical helpers are ``ctx.get_full_state_path()``,
``ctx.get_var(name)``, ``ctx.has_var(name)``, ``ctx.active_leaf`` and
``ctx.action_stage``.

Export history
--------------

Use ``history`` when you only need terminal output.  Use ``export <path>`` when
you want a file for later analysis.  The simulator infers the format from the
extension; current task docs should prefer small examples such as:

.. code-block:: text

   cycle
   cycle Start
   history 2
   export run.json

Use JSON or JSONL for machine processing, CSV (with its explicit ``delta``
column) for spreadsheets, and YAML for
human-readable snapshots.  Keep exported files outside the source tree
unless the file is a checked-in demo output regenerated by the docs build.
The exact per-format fields are listed in
:doc:`../../reference/simulation/index`.

Tune display settings
---------------------

``setting`` without arguments lists current settings.  ``setting key value``
changes one value for the current session.  Common examples are:

.. code-block:: text

   setting table_max_rows 10
   setting history_size 200
   setting log_level info
   setting color off

``history_size`` controls retained rows.  ``color`` is also affected by the CLI
``--no-color`` option.  The complete setting table, defaults and accepted value
forms are in :doc:`../../reference/simulation/index`.

Debug a failing model
---------------------

A compact debugging loop is:

1. Run ``pyfcstm inspect`` first if parsing or diagnostics are suspicious.
2. Use ``pyfcstm simulate -i docs/source/tutorials/cli/simple_machine.fcstm -e "cycle; events; current" --no-color``
   to get a stable transcript.
3. Add only one event at a time.
4. Use ``history`` or ``export`` after the failure.
5. If hot start fails, first check that every variable is provided and the
   structural depth is valid. A first-cycle Delta means the target is a stable
   no-progress boundary; provide the required event to make progress.

Do not use simulation output as a substitute for target-runtime tests.  It is a
fast model-level check that should be paired with generated-runtime tests when
you depend on target-language behavior.

Bind a custom environment source
--------------------------------

Use ``SimulationRuntime(..., input_source=...)`` for external numeric inputs.
Inherit ``BaseScalarInputPattern`` and implement ``_sample(step)`` for a scalar,
or use ``BaseIntegratedInputPattern`` for correlated vectors. See
:doc:`../../reference/simulation/inputs` for runnable examples and the exact
sampling, override, exhaustion, and error contracts.

Candidate decision diagnostics
------------------------------------------------------------

For rejected candidates, captured Python reports, REPL queries, per-cycle inputs and JSONL output, see :doc:`diagnostics`.

Tasks for models with regions
-----------------------------

The cards below use a model with regions.  Each one states the same six
facts: **Input**, **Command or code**, **Expected signal**, **File side
effect**, **First failure check** and **Reference link**.  Run them from this
directory.  ``hot_controller.fcstm`` is the interlock controller of
:doc:`/tutorials/regions/index`; the modeling tasks themselves are on
:doc:`/how_to/regions/index`.

Hot start a model with regions from a position
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``hot_controller.fcstm`` and a position to start from.  A position
is a tree: the part you write is placed without running ``enter`` actions and
the part you leave out waits for initialization.  Every variable must be
given, including the hidden ones (``__forced_0`` here) that the model
conversion adds.

.. literalinclude:: hot_controller.fcstm
   :language: fcstm
   :caption: hot_controller.fcstm

**Command or code.** ``initial_state`` accepts five spellings of a position;
the script also shows an owner written alone:

.. literalinclude:: hot_start_forms.demo.py
   :language: python
   :caption: hot_start_forms.demo.py

.. literalinclude:: hot_start_forms.demo.py.txt
   :language: text

**Expected signal.** The configuration text and the ``Configuration`` object
place every region.  A dotted path, a tuple path and a ``State`` object name
one leaf: the regions they do not pass through wait (``[init]``) and take their
initial transition in the first cycle.  An owner written alone waits as a
whole, and its regions start in writing order.  No ``enter`` action runs for
the part that is placed.

**File side effect.** None.

**First failure check.** If the start position is not what you expected, print
``runtime.configuration`` before the first cycle; it shows exactly what was
placed and what waits.

**Reference link.** :doc:`/reference/region_model/index` for position text and
validation modes, :doc:`/reference/simulation/index` for the constructor.

Supply every variable, including the hidden ones
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** A model whose conversion adds hidden variables: ``__forced_*`` for
forced transitions, ``__hist_*`` for history and ``__active_*`` for
``active()`` queries.  They are ordinary variables; the runtime neither
derives nor checks them against the position.  ``hot_watch.fcstm`` uses
``active()``.

**Command or code.**

.. literalinclude:: hot_active_variables.demo.py
   :language: python
   :caption: hot_active_variables.demo.py

.. literalinclude:: hot_active_variables.demo.py.txt
   :language: text

**Expected signal.** ``model.active_queries`` lists the queries and their
variable names; ``model.active_variables(config)`` computes the values that
match a position.  The runtime accepts them as ``initial_vars`` and shows them
in ``runtime.vars``.  If you pass a value that disagrees with the position,
the runtime runs with the value you passed.

**File side effect.** None.

**First failure check.** If construction names a missing variable, list
``model.active_queries`` and the model's ``__forced_*`` and ``__hist_*``
variables, and add them.

**Reference link.** :doc:`/reference/region_model/index`.

Fix three typical hot-start errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``hot_controller.fcstm`` and the three refusals below.  The script
``hot_start_errors.demo.py`` constructs a runtime three times and prints the
``ValueError`` each time.

.. literalinclude:: hot_start_errors.demo.py.txt
   :language: text

**Command or code and fix.**

* *Hidden variable left out* (first line): add ``__forced_0`` to
  ``initial_vars``.  Do not drop it because it is not in your source text.
* *Every region done* (second line): a configuration in which every region of an
  owner is ``[done]`` cannot be a resting position, at any depth.  Leave one
  region alive, or start at the state the owner continues to.
* *Unknown state* (third line): the path does not exist.  Print
  ``[s.path for s in model.walk_states()]`` and copy a path from there.

**Expected signal.** Each refusal raises ``ValueError`` before any cycle runs.

**File side effect.** None.

**First failure check.** Read the message: each one names the missing
variable, the owner with all regions done, or the unknown path.

**Reference link.** :doc:`/reference/simulation/index`.

Resolve an ambiguous event name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``leaf_events.fcstm``: two leaves each declare an event named
``Ping``, and one leaf declares ``Go``.  The full path and ``/Name`` mean the
same wherever the machine rests.  A short name is resolved once for every
active leaf: no match is an error, one distinct event is used, and different
events are an ambiguity.

.. literalinclude:: leaf_events.fcstm
   :language: fcstm
   :caption: leaf_events.fcstm

**Command or code.**

.. literalinclude:: event_names.demo.py
   :language: python
   :caption: event_names.demo.py

.. literalinclude:: event_names.demo.py.txt
   :language: text

**Expected signal.** ``Go`` resolves to one event; ``/Reset`` resolves from
anywhere; ``Ping`` raises an ambiguity error that lists each candidate and the
leaf it came from; ``Nope`` raises a lookup error that lists the leaves it
tried.  ``cycle(['Ping'])`` is refused with the same ambiguity, while the full
path moves one region and two full paths move both.  A bare name never looks
upward, and a finished region or one that waits for initialization takes no
part.

**File side effect.** None.

**First failure check.** Copy the full path from the error text into the
call or the model.

**Reference link.** :doc:`/reference/simulation/index`.

Find out why nothing happened in a cycle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``hot_stuck.fcstm``: ``Right`` can only start when ``flag > 0``.
Started at ``Root.Pair{Left: Busy}`` with ``flag=0``, the waiting region cannot
reach a resting position.

.. literalinclude:: hot_stuck.fcstm
   :language: fcstm
   :caption: hot_stuck.fcstm

**Command or code.**

.. literalinclude:: hot_delta.demo.py
   :language: python
   :caption: hot_delta.demo.py

.. literalinclude:: hot_delta.demo.py.txt
   :language: text

**Expected signal.** With ``flag=0`` the cycle is a Delta: ``delta=True``,
the configuration and the variables are unchanged, even ``Left``'s ``during``
(which would have raised ``work``) is rolled back.  The first check names the
transition that failed (``guard_false``, ``flag > 0``).  With ``flag=1`` the
same call places ``Right`` and runs ``Left``'s ``during``.  A Delta is a whole
cycle that did not commit; a cycle in which every region simply stays put is
not a Delta.  The CLI shows the same evidence with
``pyfcstm simulate --diagnostics`` and ``why``; see :doc:`diagnostics`.

**File side effect.** None; a Delta warning goes to standard error.

**First failure check.** Read the first check whose outcome is
``guard_false`` or ``successor_rejected`` and look at its ``vars``: those are
values at the check, not final values.

**Reference link.** :doc:`/reference/simulation/diagnostics`.

Type a configuration into ``init`` and read ``events`` in the REPL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``hot_controller.fcstm``.  ``init`` accepts configuration text in
braces; give every variable once.

**Command or code.**

.. literalinclude:: repl_init.demo.sh
   :language: bash

.. literalinclude:: repl_init.demo.sh.txt
   :language: text

**Expected signal.** ``init`` reports the position it built.  An owner written
alone is shown with ``[init]`` for every region.  ``events`` lists only events
that exist from the active leaves.  Position text is shown as configuration
text everywhere (``current``, history tables, exports).

Two refusals, both negative examples:

.. literalinclude:: repl_init_duplicate.demox.sh.txt
   :language: text

(A variable assigned twice; the exit code in ``repl_init_duplicate.demox.sh.exitcode`` is 1.)

.. literalinclude:: repl_init_done.demox.sh.txt
   :language: text

(All regions done; exit code 1 in ``repl_init_done.demox.sh.exitcode``.)

In the interactive REPL, Tab completion offers only short event names that
would actually resolve, and it completes states inside regions.  The completer
used by the REPL gives:

.. literalinclude:: repl_completion.demo.py.txt
   :language: text

``cycle S`` offers nothing because ``Start`` is declared on the owner and a
bare name does not look upward; ``cycle Co`` offers the full path.

**File side effect.** None.

**First failure check.** If ``init`` says a variable is missing, run
``current`` on a normal start: it lists every variable, hidden ones included.

**Reference link.** :doc:`/reference/simulation/index`.
