.. _sec-how-to-simulation:

Simulation tasks
================

Use this page when you already have an FCSTM model and need to run a concrete
simulation task.  For the first guided run, start with
:doc:`../../tutorials/simulation/index`.  For execution-order reasoning, see
:doc:`../../explanations/execution_semantics/index`.

CLI options and command facts
-----------------------------

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
   * - ``init <state_path> [var=value...]``
     - Rebuild the runtime as a hot start at a state with explicit variables.
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
receives events.

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
* a composite hot-start target must have a valid path to a stoppable leaf, or
  the runtime reports a DFS validation error.

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

Use JSON or JSONL for machine processing, CSV for spreadsheets, and YAML for
human-readable snapshots.  Keep exported files outside the source tree
unless the file is a checked-in demo output regenerated by the docs build.

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
``--no-color`` option.

Debug a failing model
---------------------

A compact debugging loop is:

1. Run ``pyfcstm inspect`` first if parsing or diagnostics are suspicious.
2. Use ``pyfcstm simulate -i docs/source/tutorials/cli/simple_machine.fcstm -e "cycle; events; current" --no-color``
   to get a stable transcript.
3. Add only one event at a time.
4. Use ``history`` or ``export`` after the failure.
5. If hot start fails, check that every variable is provided and that the target
   composite can reach a stoppable leaf without requiring a missing event.

Do not use simulation output as a substitute for target-runtime tests.  It is a
fast model-level check that should be paired with generated-runtime tests when
you depend on target-language behavior.
