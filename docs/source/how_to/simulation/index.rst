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

Download :download:`controller.fcstm </_models/controller.fcstm>` into an empty directory and run:

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   cycle --input fault=0 --input requested=0; \
   events; \
   cycle /Start --input fault=0 --input requested=0; \
   history 2"
   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=0 --input requested=0
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Controller.Idle
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

   ────────────────────────────────────────────────────────────
   >>> events
   ────────────────────────────────────────────────────────────
   Available Events:
     • Controller.Start

   ────────────────────────────────────────────────────────────
   >>> cycle /Start --input fault=0 --input requested=0
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> history 2
   ────────────────────────────────────────────────────────────
    Cycle                        State                        Delta  __forced_0  motor  permit
   --------------------------------------------------------------------------------------------
      1                     Controller.Idle                   False      0         0      0
      2    Controller.Running{Safety: Watching, Motion: Off}  False      0         0      1

Every cycle that really executes needs the complete input vector, so each ``cycle`` carries ``--input`` values; ``events`` lists the events the active leaves can take.

Use the interactive REPL
------------------------

Omit ``-e`` to start the REPL. An interactive session cannot be replayed by the
documentation checks, so this command is shown without being run. Download
:download:`simple_machine.fcstm </_models/simple_machine.fcstm>`, the model of
the next few sections:

.. literalinclude:: /_models/simple_machine.fcstm
   :language: fcstm
   :caption: simple_machine.fcstm

.. code-block:: bash

   pyfcstm simulate -i simple_machine.fcstm --no-color

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

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text("""
   def int counter = 0;
   state System {
       [*] -> Idle;
       state Idle;
       state Active;
       Idle -> Active :: Start;
       Active -> Idle :: Stop;
   }
   """)
   runtime = SimulationRuntime(model)
   runtime.cycle()
   print(runtime.configuration)
   runtime.cycle(["Start"])
   print(runtime.configuration)
   runtime.cycle(["Stop"])
   print(runtime.configuration)

.. testoutput::

   System.Idle
   System.Active
   System.Idle

Event names in examples rely on DSL event scoping.  For syntax facts, use
:doc:`../../reference/dsl/index`; this page only covers how the simulator
receives events.  For supported runtime event input forms and event-accounting
fields in ``CycleResult``, use :doc:`../../reference/simulation/index`.

Hot start at a state
--------------------

Use the ``init`` command when you need to inspect a later state without
replaying all earlier cycles. On ``simple_machine.fcstm``, start in
``Running`` with ``counter=10`` and send ``Stop``:

.. code-block:: console

   $ pyfcstm simulate -i simple_machine.fcstm --no-color -e "\
   init SimpleMachine.Running counter=10; \
   cycle Stop; \
   current"
   ────────────────────────────────────────────────────────────
   >>> init SimpleMachine.Running counter=10
   ────────────────────────────────────────────────────────────
   Initialized from state: SimpleMachine.Running
   Cycle: 0
   Current State: SimpleMachine.Running
   Variables:
     counter = 10

   ────────────────────────────────────────────────────────────
   >>> cycle Stop
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Stopped
   Variables:
     counter = 11

   ────────────────────────────────────────────────────────────
   >>> current
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Stopped
   Variables:
     counter = 11

Use the Python API when embedding the same idea in tests:

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("simple_machine.fcstm")
   runtime = SimulationRuntime(
       model,
       initial_state="SimpleMachine.Running",
       initial_vars={"counter": 10},
   )
   print(runtime.configuration, dict(runtime.vars))
   runtime.cycle(["Stop"])
   print(runtime.configuration, dict(runtime.vars))

.. testoutput::

   SimpleMachine.Running {'counter': 10}
   SimpleMachine.Stopped {'counter': 11}

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

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime, abstract_handler

   model = load_state_machine_from_text("""
   def int counter = 0;
   state System {
       [*] -> Active;
       state Active {
           enter abstract Init;
           exit abstract Cleanup;
           during { counter = counter + 1; }
       }
       state Done;
       Active -> Done : if [counter >= 2];
   }
   """)


   class MyHandlers:
       @abstract_handler("System.Active.Init")
       def handle_init(self, ctx):
           print("[Init]", ctx.get_full_state_path(), ctx.get_var("counter"))

       @abstract_handler("System.Active.Cleanup")
       def handle_cleanup(self, ctx):
           print("[Cleanup]", ctx.get_var("counter"))


   runtime = SimulationRuntime(model)
   runtime.register_handlers_from_object(MyHandlers())
   for _ in range(4):
       runtime.cycle()
       print(runtime.configuration)

.. testoutput::

   [Init] System.Active 0
   System.Active
   System.Active
   [Cleanup] 2
   System.Done
   System.Done

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
unless you deliberately want to commit the exported file.
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
2. Use a short batch (shown below) to get a stable transcript.
3. Add only one event at a time.
4. Use ``history`` or ``export`` after the failure.
5. If hot start fails, first check that every variable is provided and the
   structural depth is valid. A first-cycle Delta means the target is a stable
   no-progress boundary; provide the required event to make progress.

For step 2, on ``simple_machine.fcstm`` of the REPL section:

.. code-block:: console

   $ pyfcstm simulate -i simple_machine.fcstm -e "cycle; events; current" --no-color
   ────────────────────────────────────────────────────────────
   >>> cycle
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Idle
   Variables:
     counter = 0

   ────────────────────────────────────────────────────────────
   >>> events
   ────────────────────────────────────────────────────────────
   Available Events:
     • Start (SimpleMachine.Idle.Start)

   ────────────────────────────────────────────────────────────
   >>> current
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: SimpleMachine.Idle
   Variables:
     counter = 0

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
effect**, **First failure check** and **Reference link**.  Download
:download:`controller.fcstm </_models/controller.fcstm>`,
:download:`hot_watch.fcstm`, :download:`hot_stuck.fcstm` and
:download:`leaf_events.fcstm` into an empty directory and run the examples
there.  ``controller.fcstm`` is the interlock controller of
:doc:`/tutorials/regions/index`; the modeling tasks themselves are on
:doc:`/how_to/regions/index`.

Hot start a model with regions from a position
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``controller.fcstm`` and a position to start from.  A position
is a tree: the part you write is placed without running ``enter`` actions and
the part you leave out waits for initialization.  Every variable must be
given, including the hidden ones (``__forced_0`` here) that the model
conversion adds.

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: controller.fcstm

**Command or code.** ``initial_state`` accepts five spellings of a position;
the script also shows an owner written alone:

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("controller.fcstm")
   variables = {"permit": 1, "motor": 1, "__forced_0": 0}
   # one source is shared by all runtimes below, so it holds its last value
   inputs = {
       "fault": SequenceInput([0], end="hold"),
       "requested": SequenceInput([1], end="hold"),
   }
   text = "Controller.Running{Safety: Watching, Motion: On}"
   motion_on = model.root_state.substates["Running"].regions["Motion"].substates["On"]
   forms = {
       "configuration text": text,
       "Configuration object": Configuration.parse(model, text),
       "dotted path": "Controller.Running.Motion.On",
       "tuple path": ("Controller", "Running", "Motion", "On"),
       "State object": motion_on,
       "owner only": "Controller.Running",
   }
   for label, form in forms.items():
       runtime = SimulationRuntime(
           model, initial_state=form, initial_vars=variables, input_source=inputs
       )
       print(label)
       print("  at start    ", runtime.configuration)
       runtime.cycle()
       print("  after cycle ", runtime.configuration)

.. testoutput::

   configuration text
     at start     Controller.Running{Safety: Watching, Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   Configuration object
     at start     Controller.Running{Safety: Watching, Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   dotted path
     at start     Controller.Running{Safety: [init], Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   tuple path
     at start     Controller.Running{Safety: [init], Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   State object
     at start     Controller.Running{Safety: [init], Motion: On}
     after cycle  Controller.Running{Safety: Watching, Motion: On}
   owner only
     at start     Controller.Running{Safety: [init], Motion: [init]}
     after cycle  Controller.Running{Safety: Watching, Motion: Off}

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

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("hot_watch.fcstm")
   config = Configuration.parse(
       model, "Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}"
   )
   hidden = model.active_variables(config)
   print("queries:", [(".".join(q.state_path), q.variable_name) for q in model.active_queries])
   print("hidden variables for this position:", hidden)

   runtime = SimulationRuntime(
       model,
       initial_state=config,
       initial_vars=hidden,
       input_source={"go": SequenceInput([1])},
   )
   runtime.cycle()
   print("after one cycle:", runtime.configuration)
   print("runtime.vars:", dict(runtime.vars))

.. testoutput::

   queries: [('Plant.Trigger.Fired', '__active_Plant_Trigger_Fired')]
   hidden variables for this position: {'__active_Plant_Trigger_Fired': 1}
   after one cycle: Plant{Earlier: Saw, Trigger: Fired, Later: Saw}
   runtime.vars: {'__active_Plant_Trigger_Fired': 1}

The same position with the hidden variable set to ``1`` and to ``0``.  ``Earlier``
moves to ``Saw`` only when the query is true:

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("hot_watch.fcstm")
   config = Configuration.parse(
       model, "Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}"
   )
   for value in (1, 0):
       runtime = SimulationRuntime(
           model,
           initial_state=config,
           initial_vars={"__active_Plant_Trigger_Fired": value},
           input_source={"go": SequenceInput([1])},
       )
       runtime.cycle()
       print(value, runtime.configuration)

.. testoutput::

   1 Plant{Earlier: Saw, Trigger: Fired, Later: Saw}
   0 Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}

**Expected signal.** ``model.active_queries`` lists the queries and their
variable names; ``model.active_variables(config)`` computes the values that
match a position.  The runtime accepts them as ``initial_vars`` and shows them
in ``runtime.vars``.  If you pass a value that disagrees with the position,
the runtime runs with the value you passed, as the second script shows.

**File side effect.** None.

**First failure check.** If construction names a missing variable, list
``model.active_queries`` and the model's ``__forced_*`` and ``__hist_*``
variables, and add them.

**Reference link.** :doc:`/reference/region_model/index`.

Fix three typical hot-start errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``controller.fcstm`` and the three refusals below.  The script
constructs a runtime three times and prints the ``ValueError`` each time.

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("controller.fcstm")
   full = {"permit": 1, "motor": 1, "__forced_0": 0}
   cases = [
       ("hidden variable left out", "Controller.Running{Safety: Watching, Motion: On}",
        {"permit": 1, "motor": 1}),
       ("every region done", "Controller.Running{Safety: [done], Motion: [done]}", full),
       ("unknown state", "Controller.Running{Safety: Nope, Motion: On}", full),
   ]
   for label, initial_state, variables in cases:
       try:
           SimulationRuntime(
               model,
               initial_state=initial_state,
               initial_vars=variables,
               input_source={"fault": SequenceInput([0]), "requested": SequenceInput([1])},
           )
       except ValueError as error:
           print(f"{label}: ValueError: {error}")

.. testoutput::

   hidden variable left out: ValueError: initial_vars must provide all variables. Missing: ['__forced_0']
   every region done: ValueError: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   unknown state: ValueError: Unknown configuration path: 'Controller.Running.Safety.Nope'.

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

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime
   from pyfcstm.simulate.runtime import SimulationRuntimeEventError
   from pyfcstm.utils.validate import ModelLookupError, ModelValueError

   model = load_state_machine_from_file("leaf_events.fcstm")
   config = Configuration.parse(model, "Root.P{L: X, R: Y}")
   for name in ("Go", "/Reset", "Ping", "Nope"):
       try:
           print(f"{name!r} -> {config.resolve_event(name).path_name}")
       except (ModelValueError, ModelLookupError) as error:
           print(f"{name!r} -> {type(error).__name__}: {error}")

   for events in (["Ping"], ["Root.P.L.X.Ping"], ["Root.P.L.X.Ping", "Root.P.R.Y.Ping"]):
       runtime = SimulationRuntime(model)
       runtime.cycle()
       try:
           runtime.cycle(events)
       except SimulationRuntimeEventError as error:
           print(f"cycle({events}) -> refused: {error}")
       else:
           print(f"cycle({events}) -> {runtime.configuration}")

.. testoutput::

   'Go' -> Root.P.L.X.Go
   '/Reset' -> Root.Reset
   'Ping' -> ModelValueError: Position-dependent event name 'Ping' is ambiguous: Root.P.L.X.Ping (from Root.P.L.X); Root.P.R.Y.Ping (from Root.P.R.Y); use the full event path or a root-based "/path".
   'Nope' -> ModelLookupError: Position-dependent event name 'Nope' matches no event from any active leaf (Root.P.L.X, Root.P.R.Y); use the full event path or a root-based "/path".
   cycle(['Ping']) -> refused: Position-dependent event name 'Ping' is ambiguous: Root.P.L.X.Ping (from Root.P.L.X); Root.P.R.Y.Ping (from Root.P.R.Y); use the full event path or a root-based "/path".
   cycle(['Root.P.L.X.Ping']) -> Root.P{L: X, R: Y}
   cycle(['Root.P.L.X.Ping', 'Root.P.R.Y.Ping']) -> Root.P{L: X, R: Y2}

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

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("hot_stuck.fcstm")
   for flag in (0, 1):
       runtime = SimulationRuntime(
           model,
           initial_state="Root.Pair{Left: Busy}",
           initial_vars={"flag": flag, "work": 0},
       )
       result = runtime.cycle(diagnostics=True)
       print(f"flag={flag}: delta={result.delta} outcome={result.diagnostics.outcome}")
       print(f"  {runtime.configuration} {dict(runtime.vars)}")
       for item in result.diagnostics.decisions:
           print(f"  #{item.id} {item.transition_label}")
           print(f"     {item.outcome}: {item.guard} is {item.guard_result}")

.. testoutput::

   Cycle 1 completed as Delta - State: Root.Pair{Left: Busy, Right: [init]}; no stoppable successor was committed
   flag=0: delta=True outcome=delta
     Root.Pair{Left: Busy, Right: [init]} {'flag': 0, 'work': 0}
     #1 Root.Pair.Right::0::INIT_STATE->Ready
        guard_false: flag > 0 is False
   flag=1: delta=False outcome=cycle
     Root.Pair{Left: Busy, Right: Ready} {'flag': 1, 'work': 1}
     #1 Root.Pair.Right::0::INIT_STATE->Ready
        selected: flag > 0 is True
     #2 Root.Pair.Right::0::INIT_STATE->Ready
        selected: flag > 0 is True

**Expected signal.** With ``flag=0`` the cycle is a Delta: ``delta=True``,
the configuration and the variables are unchanged, even ``Left``'s ``during``
(which would have raised ``work``) is rolled back.  The first check names the
transition that failed: ``Root.Pair.Right::0::INIT_STATE->Ready`` is the
initial transition of ``Right``, and it ends ``guard_false`` on ``flag > 0``.  With ``flag=1`` the
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

**Input.** ``controller.fcstm``.  ``init`` accepts configuration text in
braces; give every variable once.

**Command or code.**

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; \
   events; \
   init Controller.Running permit=1 motor=0 __forced_0=0"
   ────────────────────────────────────────────────────────────
   >>> init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0
   ────────────────────────────────────────────────────────────
   Initialized from state: Controller.Running{Safety: Watching, Motion: On}
   Cycle: 0
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> events
   ────────────────────────────────────────────────────────────
   Available Events:
     • Controller.Stop

   ────────────────────────────────────────────────────────────
   >>> init Controller.Running permit=1 motor=0 __forced_0=0
   ────────────────────────────────────────────────────────────
   Initialized from state: Controller.Running
   Cycle: 0
   Current State: Controller.Running{Safety: [init], Motion: [init]}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 1

**Expected signal.** ``init`` reports the position it built.  An owner written
alone is shown with ``[init]`` for every region.  ``events`` lists only events
that exist from the active leaves.  Position text is shown as configuration
text everywhere (``current``, history tables, exports).

Two refusals, both negative examples.  Each one ends with exit status 1:

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running permit=1 permit=0 motor=0 __forced_0=0"
   ────────────────────────────────────────────────────────────
   >>> init Controller.Running permit=1 permit=0 motor=0 __forced_0=0
   ────────────────────────────────────────────────────────────
   Error: variable 'permit' is assigned more than once.
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=0 __forced_0=0"
   ────────────────────────────────────────────────────────────
   >>> init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=0 __forced_0=0
   ────────────────────────────────────────────────────────────
   Initialization failed: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   $ echo $?
   1

In the interactive REPL, Tab completion offers only short event names that
would actually resolve, and it completes states inside regions.  Completion
needs a terminal, so it is not part of the checked examples; in an interactive
session on ``controller.fcstm`` after one ``cycle``, typing
``init Controller.Running.`` and pressing Tab offers
``Controller.Running.Motion.Off``, ``Controller.Running.Motion.On`` and
``Controller.Running.Safety.Watching`` as leaf states, ``cycle Co`` offers
``Controller.Start`` as an event name, and ``cycle S`` offers nothing.

``cycle S`` offers nothing because ``Start`` is declared on the owner and a
bare name does not look upward; ``cycle Co`` offers the full path.

**File side effect.** None.

**First failure check.** If ``init`` says a variable is missing, run
``current`` on a normal start: it lists every variable, hidden ones included.

**Reference link.** :doc:`/reference/simulation/index`.
