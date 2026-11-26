.. _sec-reference-simulation:

Simulation reference
====================

Use this page when you need exact simulator facts: command forms, event input,
settings, history/export formats, Python runtime API, and public failure
boundaries.  For a first run, see :doc:`../../tutorials/simulation/index`; for
recipes, see :doc:`../../how_to/simulation/index`; for ordering semantics, see
:doc:`../../explanations/execution_semantics/index`.

CLI invocation
--------------

``pyfcstm simulate`` loads one FCSTM file, parses it into a state-machine model,
constructs a :class:`pyfcstm.simulate.SimulationRuntime`, and either starts an
interactive REPL or runs semicolon-separated batch commands.

.. list-table:: Command-line options
   :header-rows: 1

   * - Option
     - Required
     - Meaning
   * - ``-i`` / ``--input-code TEXT``
     - yes
     - Path to the FCSTM input file.
   * - ``-e`` / ``--execute TEXT``
     - no
     - Batch command string.  Commands are separated by semicolons.
   * - ``--no-color``
     - no
     - Disable ANSI color in command output.
   * - ``-h`` / ``--help``
     - no
     - Show Click help and exit.

Parse, decode, grammar, and model-validation failures are written to stderr as ``Failed to parse DSL file: ...`` and return nonzero. Batch command failures stop execution with nonzero status; interactive failures print a message and keep the REPL available.

Batch and REPL commands
-----------------------

Batch mode and the interactive REPL use the same command processor.

.. list-table:: Simulator commands
   :header-rows: 1

   * - Command
     - Parameters
     - Output and boundary
   * - ``cycle [count] [events...]``
     - Optional positive integer count followed by event inputs.  Without a
       count, one cycle is executed.
     - Runs cycle(s).  A non-positive count reports ``Error: cycle count must
       be a positive integer``.  DFS, event, and expression errors are reported
       as ``Cycle execution failed: ...``.
   * - ``current``
     - none
     - Prints current cycle, state, and persistent variables.
   * - ``events``
     - none
     - Lists events available from the current runtime state.
   * - ``history [n|all]``
     - Optional positive integer row count or ``all``.  Default is 10.
     - Prints retained history.  Empty history reports ``No execution history
       available.``.
   * - ``init <position> [var=value...]``
     - Target state, or for a model with regions a configuration text such as ``Root.Run{A: X, B: [done]}``, plus numeric variable assignments.  See :ref:`sim-region-cli`.
     - Rebuilds the runtime as a hot start.  Every persistent control/output variable must be provided, hidden ones included; inputs belong to each cycle and parameters remain fixed.  A configuration text keeps its spaces inside the braces; what it leaves out waits for initialization in the first cycle.  Values accept decimal, hexadecimal, binary, float, and
       scientific notation.
   * - ``setting [key] [value]``
     - No arguments, one key, or key/value pair.
     - Lists settings, shows one setting, or updates one setting.
   * - ``export <filename>``
     - Output path ending in ``.csv``, ``.json``, ``.yaml``, or ``.jsonl``.
     - Writes retained history.  Empty history, unsupported suffixes, and file
       write failures return explicit command messages.
   * - ``clear``
     - none
     - Rebuilds a fresh runtime while preserving session-level configuration.
   * - ``help``
     - none
     - Prints command help and keyboard shortcuts.
   * - ``quit`` / ``exit``
     - none
     - Leaves the interactive REPL or ends batch command processing.

Event input forms
-----------------

The runtime accepts model-owned :class:`pyfcstm.model.Event` objects, one event
path string, or an iterable containing those values.  A bare string is one event
input, not a sequence of characters.

.. list-table:: Event path forms
   :header-rows: 1

   * - Form
     - Example
     - Meaning
   * - Short or relative event name
     - ``Start``
     - Resolved from the current runtime state.
   * - Dot-separated full path
     - ``System.Idle.Start``
     - Resolved as a model event path.
   * - Parent-relative path
     - ``.error`` or ``..system.error``
     - Navigates relative to the current state path.
   * - Absolute path
     - ``/global.shutdown``
     - Resolved from the root state.
   * - Multiple events
     - ``cycle Start Stop`` or ``runtime.cycle(["Start", "Stop"])``
     - Makes all listed events available for the cycle.

A :class:`pyfcstm.simulate.SimulationRuntimeEventError` is raised by the Python
API, and shown as ``Cycle execution failed: ...`` by the command layer, when an
event input has an unsupported shape, cannot be resolved, or belongs to a
different state machine.

Settings
--------

Settings are command-layer session settings.  ``--no-color`` initializes
``color`` to ``False`` for that CLI session.

.. list-table:: Settings table
   :header-rows: 1

   * - Key
     - Type and legal values
     - Default
     - Effect
   * - ``table_max_rows``
     - Non-negative integer
     - ``20``
     - Controls table truncation for large command output.
   * - ``history_size``
     - Non-negative integer; ``0`` means unlimited runtime history
     - ``100``
     - Controls how many history entries the active runtime retains.
   * - ``color``
     - Boolean strings ``on`` / ``off``, ``true`` / ``false``, ``1`` / ``0``,
       ``yes`` / ``no``
     - ``True`` unless ``--no-color`` is used
     - Enables or disables ANSI color in display output.
   * - ``log_level``
     - ``debug``, ``info``, ``warning``, ``error``, or ``off``
     - ``warning``
     - Controls simulator log verbosity.

Unknown settings report ``Error: 'Unknown setting: <key>'``.  Invalid values
report an ``Error: ...`` message from the setting validator.

.. note::
   The ``history_size=0`` setting is a command-layer convention.  During
   setting synchronization, the command layer maps it to
   ``SimulationRuntime.history_size = None``.  Direct Python API use is
   different: ``SimulationRuntime(history_size=None)`` means unlimited history,
   while ``SimulationRuntime(history_size=0)`` keeps no entries.

History and export formats
--------------------------

Runtime history entries are dictionaries with ``cycle``, ``state``, ``vars``,
``events`` and boolean ``delta`` keys.  ``history`` displays retained rows; ``export`` is
a command-layer feature and is not a :class:`pyfcstm.simulate.SimulationRuntime` method.

.. list-table:: Export formats
   :header-rows: 1

   * - Suffix
     - Shape
     - Notes
   * - ``.csv``
     - Columns ``cycle``, ``state``, ``delta``, ``events``, then sorted variable names.
     - Events are joined with semicolons inside one CSV cell.
   * - ``.json``
     - JSON array of history entry objects.
     - Uses two-space indentation and UTF-8 output.
   * - ``.yaml``
     - YAML sequence of history entry mappings.
     - Uses Unicode-friendly PyYAML output.
   * - ``.jsonl``
     - One JSON history entry object per line.
     - Suitable for append-like or streaming post-processing.

.. _sim-region-event-names:

Event names with several active leaves
--------------------------------------

A model with regions has several active leaves. A full model path, such as
``Controller.Running.Stop``, and a path that starts at the root, such as
``/Running.Stop``, mean the same event wherever the machine rests. A name that
depends on the position (a short name such as ``Go`` or a name that counts levels
up with leading dots such as ``..Stop``) is resolved once for every active leaf
and the results are combined.

.. list-table:: Outcomes of a position-dependent name
   :header-rows: 1
   :widths: 24 30 46

   * - Leaves that find an event
     - Result
     - Error when refused
   * - None
     - Refused; nothing runs.
     - ``Position-dependent event name 'Nope' matches no event from any active
       leaf (<leaves>); use the full event path or a root-based "/path".``
       (``ModelLookupError`` from ``Configuration.resolve_event``,
       ``SimulationRuntimeEventError`` from ``cycle``).
   * - One or more, all the same event
     - The event is used. Several regions that find it all react to it in the
       same cycle.
     - none
   * - Different events
     - Refused as ambiguous; nothing runs.
     - ``Position-dependent event name 'Ping' is ambiguous: <event> (from
       <leaf>); <event> (from <leaf>); use the full event path or a root-based
       "/path".`` The error lists every candidate with the leaves that led to it.

Further rules:

* A bare name looks only in the namespace of each active leaf and never searches
  upward. An event of a composite owner, a region or an ancestor is reached with
  its full path, with ``/name`` from the root, or with leading dots that count the
  levels up (``..Stop`` reaches ``Controller.Running.Stop`` from the leaves of the
  regions of ``Running``).
* A region that is done and a region that still waits for initialization have no
  active leaf and do not take part in the resolution.
* ``runtime.cycle`` first tries the name as a full model path, then falls back to
  the position-dependent resolution. With a single active leaf the refusal reads
  ``Cannot resolve event path 'Reset': failed with both
  StateMachine.resolve_event and State.resolve_event. ...`` instead.
* Every name of one cycle is resolved on its own.
* ``consumed_events`` lists an event once for every transition that used it; an
  event shared by two regions appears twice.

.. literalinclude:: event_names.fcstm
   :language: fcstm

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   with open('event_names.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())

   position = 'Controller.Running{Safety: Watching, Motion: Off}'
   config = SimulationRuntime(model, initial_state=position, initial_vars={'trail': 0}).configuration
   for name in ['Trip', 'Ping', 'Nope', 'Reset', '..Stop', '/Running.Stop']:
       try:
           print(name, '->', config.resolve_event(name).path_name)
       except (ValueError, LookupError) as error:
           print(name, '!!', type(error).__name__ + ':', error)

.. testoutput::

   Trip -> Controller.Running.Safety.Watching.Trip
   Ping !! ModelValueError: Position-dependent event name 'Ping' is ambiguous: ...
   Nope !! ModelLookupError: Position-dependent event name 'Nope' matches no event from any active leaf ...
   Reset !! ModelLookupError: Position-dependent event name 'Reset' matches no event from any active leaf ...
   ..Stop -> Controller.Running.Stop
   /Running.Stop -> Controller.Running.Stop

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeEventError

   with open('event_names.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())

   for position, name in [('Controller.Running{Safety: Watching, Motion: Off}', 'Trip'),
                          ('Controller.Running{Safety: Watching, Motion: Off}', 'Ping'),
                          ('Controller.Running{Safety: [done], Motion: Off}', 'Ping'),
                          ('Controller.Idle', 'Reset')]:
       runtime = SimulationRuntime(model, initial_state=position, initial_vars={'trail': 0})
       try:
           result = runtime.cycle([name])
           print(name, 'ok', runtime.configuration, list(result.consumed_events))
       except SimulationRuntimeEventError as error:
           print(name, '!!', error)
           print('   ', runtime.configuration)

.. testoutput::

   Trip ok Controller.Running{Safety: Tripped, Motion: Off} ['Controller.Running.Safety.Watching.Trip']
   Ping !! Position-dependent event name 'Ping' is ambiguous: ...
       Controller.Running{Safety: Watching, Motion: Off}
   Ping ok Controller.Running{Safety: [done], Motion: Off} ['Controller.Running.Motion.Off.Ping']
   Reset !! Cannot resolve event path 'Reset': failed with both ...
       Controller.Idle

The first script shows the outcomes for names that depend on the position:
``Trip`` is found by one leaf, ``Ping`` is ambiguous because both leaves own a
``Ping``, and ``Nope`` and ``Reset`` are found by none, even though ``Reset``
exists on the root, because a bare name never looks upward. ``..Stop`` and
``/Running.Stop`` reach the owner's event. The second script runs ``cycle`` on a
fresh runtime for each line: the refusals leave the position unchanged, a done
region leaves ``Ping`` unambiguous, and with a single active leaf the refusal
reads ``Cannot resolve event path``. This establishes the resolution rules; it
does not show how long a name takes to resolve.

.. _sim-region-hot-start:

Hot start of a model with regions
---------------------------------

``SimulationRuntime(model, initial_state=position, initial_vars=variables,
parameters=..., input_source=...)`` starts from a position without running any
``enter`` action. A cold start (``initial_state=None``) runs the initial entry in
the first cycle.

.. list-table:: Spellings of ``initial_state``
   :header-rows: 1
   :widths: 26 34 40

   * - Spelling
     - Example
     - Position that results
   * - Configuration text
     - ``'Controller.Running{Safety: Watching, Motion: On}'``
     - Exactly what is written.
   * - ``Configuration``
     - ``Configuration.parse(model, text)``
     - Exactly that value; it must come from the same model object.
   * - Dotted path
     - ``'Controller.Running.Motion.On'``
     - The branch the path passes through; the other regions of every owner on
       the path wait for initialization.
   * - Tuple
     - ``('Controller', 'Running', 'Motion', 'On')``
     - Same as the dotted path.
   * - ``State``
     - the ``State`` object of ``On``
     - Same as the dotted path; it must belong to the same model object.

A position is a tree. What is written is put in place and no ``enter`` runs for
it; what is not written waits for initialization and runs its initial
transitions in the first cycle, in written order, while the rest works as usual.
Three things wait: a region that is left out (and every other region of the
owners on a dotted path), an owner written as a bare path (the whole group), and
a plain composite state written without a child.

.. list-table:: Position text for a hot start
   :header-rows: 1
   :widths: 40 60

   * - Text
     - Meaning
   * - ``Root.Job{A: X, B: Y}``
     - Owner ``Root.Job`` rests with region ``A`` in state ``X`` and ``B`` in
       ``Y``. A region entry names the child relative to the region; a deeper
       leaf is written ``Comp.In1``; a nested owner is written with another block,
       ``Q{A1: W1, A2: W2}``.
   * - ``Root.Job{A: X}``
     - ``B`` is left out and waits for initialization (shown as ``B: [init]``).
   * - ``Root.Job{A: [done], B: Y}``
     - ``A`` is Done: it stays done and does no work.
   * - ``Root.Job{A: X, B: [init]}``
     - ``B`` waits explicitly; same as leaving it out.
   * - ``Root.Job``
     - The whole group waits for initialization.
   * - ``Root.Idle``
     - An ordinary leaf; same as a model without regions.

The first script starts the controller of the tutorial
(:download:`controller.fcstm </_models/controller.fcstm>`) in each spelling of
the table above, then in three positions that leave something out, and prints
the resulting configuration. The second script shows that the first cycle
initializes the region that was left out.

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   with open('controller.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())
   motion_on = next(s for s in model.walk_states() if s.path == ('Controller', 'Running', 'Motion', 'On'))
   positions = [
       'Controller.Running{Safety: Watching, Motion: On}',
       Configuration.parse(model, 'Controller.Running{Safety: Watching, Motion: On}'),
       'Controller.Running.Motion.On',
       ('Controller', 'Running', 'Motion', 'On'),
       motion_on,
       'Controller.Running',
       'Controller.Running{Safety: [done], Motion: On}',
       'Controller',
   ]
   for position in positions:
       runtime = SimulationRuntime(
           model, initial_state=position,
           initial_vars={'permit': 1, 'motor': 1, '__forced_0': 0},
           input_source={'fault': 0, 'requested': 1})
       print(runtime.configuration)

.. testoutput::

   Controller.Running{Safety: Watching, Motion: On}
   Controller.Running{Safety: Watching, Motion: On}
   Controller.Running{Safety: [init], Motion: On}
   Controller.Running{Safety: [init], Motion: On}
   Controller.Running{Safety: [init], Motion: On}
   Controller.Running{Safety: [init], Motion: [init]}
   Controller.Running{Safety: [done], Motion: On}
   Controller

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   with open('controller.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())
   runtime = SimulationRuntime(
       model, initial_state='Controller.Running.Motion.On',
       initial_vars={'permit': 1, 'motor': 1, '__forced_0': 0},
       input_source={'fault': 0, 'requested': 1})
   print(runtime.configuration)
   result = runtime.cycle()
   print(runtime.configuration, result.delta)

.. testoutput::

   Controller.Running{Safety: [init], Motion: On}
   Controller.Running{Safety: Watching, Motion: On} False

Rules and refusals:

* ``initial_vars`` must give every persistent variable, hidden ones
  (``__forced_*``, ``__hist_*``, ``__active_*``) included. They are ordinary
  variables: the runtime neither derives them from the position nor checks that
  they agree with it. ``StateMachine.active_variables(config)`` and
  ``history_variables(...)`` compute values that agree with a position.
  Inputs and parameters are not part of ``initial_vars``; a hot start still needs
  complete ``parameters`` and a complete ``input_source`` (see :doc:`inputs`).
* Every region of an owner Done is refused, at any depth.
* An owner that waits for initialization and cannot reach a resting place in the
  first cycle makes that whole cycle a Delta: the position and the variables stay
  as written and ``cycle_count`` still advances.

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   with open('controller.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())
   variables = {'permit': 1, 'motor': 1, '__forced_0': 0}
   cases = [
       ('Controller.Running{Safety: [done], Motion: [done]}', variables),
       ('Controller.Running{Safety: Nowhere, Motion: On}', variables),
       ('Controller.Running.Motion', variables),
       ('Controller.Running{Safety: [*], Motion: On}', variables),
       (5, variables),
       ('Controller.Running.Motion.On', {'permit': 1, 'motor': 1}),
   ]
   for position, given in cases:
       try:
           SimulationRuntime(model, initial_state=position, initial_vars=given,
                             input_source={'fault': 0, 'requested': 1})
       except (ValueError, TypeError) as error:
           print(type(error).__name__ + ':', error)

.. testoutput::

   ValueError: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   ValueError: Unknown configuration path: 'Controller.Running.Safety.Nowhere'.
   ValueError: 'Controller.Running.Motion' names a region, not a state
   ValueError: Expected a configuration identifier at line 1, column 28, got '['.
   TypeError: initial_state must be str, tuple, State or Configuration, got int
   ValueError: initial_vars must provide all variables. Missing: ['__forced_0']

.. literalinclude:: pending_delta.fcstm
   :language: fcstm

.. testcode::

   import logging

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   logging.disable(logging.CRITICAL)  # keep the Delta warning off the output
   with open('pending_delta.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())
   for ready in (0, 1):
       runtime = SimulationRuntime(model, initial_state='Plant.Job{Count: Counting}',
                                   initial_vars={'ready': ready, 'ticks': 0})
       result = runtime.cycle()
       print('ready=%d' % ready, result.delta, runtime.configuration, runtime.vars['ticks'])

.. testoutput::

   ready=0 True Plant.Job{Count: Counting, Gate: [init]} 0
   ready=1 False Plant.Job{Count: Counting, Gate: Open} 1

The script runs the same position twice. With ``ready=0`` the cycle is a Delta:
``Count`` does no ``during`` work (the last value printed, ``ticks``, stays ``0``)
while ``Gate`` cannot start, the cycle rolled back, ``delta`` is ``True``, and the
position is the one written. With ``ready=1`` both regions work in that cycle.
Delta lines are also logged at ``warning`` level on stderr; the script turns the
logging off.

.. literalinclude:: active_flags.fcstm
   :language: fcstm

.. testcode::

   from pyfcstm.model import Configuration, load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   with open('active_flags.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())
   position = 'Root.Job{Feed: Busy, Check: Watch}'
   flags = model.active_variables(Configuration.parse(model, position))
   print(flags)
   for given in (flags, {name: 0 for name in flags}):
       runtime = SimulationRuntime(model, initial_state=position,
                                   initial_vars=dict(given, alarm=0, ticks=0))
       runtime.cycle()
       print(runtime.configuration, runtime.vars['alarm'])

.. testoutput::

   {'__active_Root_Job_Feed_Busy': 1}
   Root.Job{Feed: Busy, Check: Watch} 1
   Root.Job{Feed: Busy, Check: Watch} 0

The script prints the flag that matches the position, then runs one cycle with
it and one with the flag given as ``0``; the last value printed is ``alarm``. The
hidden flag must be given with the other variables; given as ``0`` it is what
runs, even when the position says the state is active. The check that the flag
agrees with the position is the caller's.

.. _sim-region-position-api:

Positions, results and handler context
--------------------------------------

.. list-table:: Position surface of a runtime
   :header-rows: 1
   :widths: 28 72

   * - Member
     - Behavior for a model with regions
   * - ``runtime.configuration``
     - The immutable :class:`pyfcstm.model.Configuration` of the resting
       position, for every model, with or without regions. ``str()`` gives the
       position text, ``repr()`` also shows the validation mode. After the
       runtime has ended (``is_ended``) it raises
       ``SimulationRuntimeTerminalStateError``.
   * - ``runtime.current_state``
     - For a model **with** regions it returns the same ``Configuration``; for a
       model without regions it still returns a ``State``. Check ``is_ended``
       first: after termination it raises
       ``SimulationRuntimeTerminalStateError``.
   * - ``runtime.brief_stack``
     - Raises ``SimulationRuntimeRegionQueryError`` for a model with regions:
       ``brief_stack describes a single active path, but this model has regions;
       use configuration, which shows every branch.``
   * - ``Configuration.leaves``
     - The active resting leaves, one per live region branch; Done and waiting
       branches have none.
   * - ``CycleResult``
     - Same fields as without regions. ``input_events`` are canonical paths in
       input order; ``consumed_events`` lists an event once per transition that
       used it; ``delta`` is ``True`` when the whole cycle rolled back.
   * - Delta
     - One cycle-wide concept: no region keeps a write of the cycle, the position
       and variables stay as before, and ``cycle_count`` advances.

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeRegionQueryError

   with open('controller.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())
   runtime = SimulationRuntime(model, input_source={'fault': 0, 'requested': 1})
   runtime.cycle()
   runtime.cycle('/Start')
   print(repr(runtime.configuration))
   print(type(runtime.current_state).__name__, runtime.current_state)
   print([state.path for state in runtime.configuration.leaves])
   try:
       runtime.brief_stack
   except SimulationRuntimeRegionQueryError as error:
       print(type(error).__name__ + ':', error)

.. testoutput::

   Configuration(mode='stable', position='Controller.Running{Safety: Watching, Motion: Off}')
   Configuration Controller.Running{Safety: Watching, Motion: Off}
   [('Controller', 'Running', 'Safety', 'Watching'), ('Controller', 'Running', 'Motion', 'Off')]
   SimulationRuntimeRegionQueryError: brief_stack describes a single active path, but this model has regions; use configuration, which shows every branch.

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   plain = load_state_machine_from_text('state Root { [*] -> A; state A; state B; A -> B :: Go; }')
   runtime = SimulationRuntime(plain)
   runtime.cycle()
   print(repr(runtime.configuration))
   print(type(runtime.current_state).__name__, runtime.current_state.path)
   print(runtime.brief_stack)

.. testoutput::

   Configuration(mode='stable', position='Root.A')
   State ('Root', 'A')
   [(('Root',), 'active'), (('Root', 'A'), 'active')]

Abstract handlers receive a ``ReadOnlyExecutionContext``.

.. list-table:: Handler context fields around regions
   :header-rows: 1
   :widths: 26 74

   * - Field
     - Value
   * - ``state_path``
     - The deepest state common to the range the action wraps: the leaf when the
       action wraps one branch, the owner when it wraps the whole group.
   * - ``active_leaf``
     - Follows ``state_path`` in the same way (the active leaf when exactly one
       is wrapped, otherwise the host state path).
   * - ``configuration``
     - The complete configuration at the moment of the call, as a
       ``Configuration``. A region that has not started yet is shown as
       ``[init]``; a region that already moved in the same cycle shows its new
       state.
   * - ``get_var(name)``
     - The variable snapshot, hidden variables included.

.. literalinclude:: handler_hooks.fcstm
   :language: fcstm

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   with open('handler_hooks.fcstm') as stream:
       model = load_state_machine_from_text(stream.read())
   runtime = SimulationRuntime(model, input_source={'fault': 0, 'requested': 1})


   def reporter(name):
       def show(ctx):
           print(name, '|', '.'.join(ctx.state_path), '|', ctx.configuration)
       return show


   for path in ['Controller.Tick', 'Controller.Running.GroupPre',
                'Controller.Running.Safety.Normal.Watch', 'Controller.Running.Motion.On.Drive']:
       runtime.register_abstract_handler(path, reporter(path.split('.')[-1]))
   runtime.cycle()
   runtime.cycle('/Start')
   runtime.cycle()

.. testoutput::

   Tick | Controller.Idle | Controller.Idle
   Tick | Controller.Running | Controller.Running{Safety: Normal, Motion: [init]}
   GroupPre | Controller.Running | Controller.Running{Safety: Normal, Motion: [init]}
   Watch | Controller.Running.Safety.Normal | Controller.Running{Safety: Normal, Motion: [init]}
   Tick | Controller.Running | Controller.Running{Safety: Normal, Motion: Off}
   GroupPre | Controller.Running | Controller.Running{Safety: Normal, Motion: Off}
   Watch | Controller.Running.Safety.Normal | Controller.Running{Safety: Normal, Motion: Off}
   Drive | Controller.Running.Motion.On | Controller.Running{Safety: Normal, Motion: On}

In cycle 2, ``Tick`` (an aspect of the root) and ``GroupPre`` (an aspect of the
owner) wrap the whole group, so their ``state_path`` is ``Controller.Running``;
``Watch`` wraps one branch and reports its leaf. ``Motion`` is ``[init]`` in every
call of that cycle because it has not started yet; in cycle 3 it is ``Off`` and
then ``On`` in the call of ``Drive``.

.. _sim-region-cli:

Simulate command with regions
-----------------------------

``pyfcstm simulate`` accepts models with regions in batch and interactive mode.
The position is shown as configuration text in ``current``, after ``cycle``, in
the table of several cycles, in ``history`` and in exported files.

.. list-table:: Region facts of the commands
   :header-rows: 1
   :widths: 22 78

   * - Command
     - Behavior
   * - ``init <position> var=value ...``
     - The position is a configuration text, a dotted path through regions, or a
       state path. The spaces inside the braces are kept, so
       ``init Controller.Running{Safety: Watching, Motion: On} permit=1`` is one
       position. Unbalanced braces report ``Error: the braces of the configuration
       text '...' are not balanced.`` with an example. A variable written twice
       reports ``Error: variable 'permit' is assigned more than once.`` Missing
       variables report ``Error: All variables must be provided. Missing:
       [...]`` and list the available names. Refused positions report
       ``Initialization failed: <message>`` with the messages of the table above.
   * - ``events``
     - Lists the events that can be typed as shown for the active leaves. A short
       name that two leaves use for different events is not offered; an event of
       an ancestor, owner or region is listed by its full path.
   * - ``cycle [count] [events...] [--input name=value ...]``
     - Every cycle needs a complete input vector: one ``--input`` per input
       variable. A refused event name reports ``Cycle execution failed: ...``
       with the text of the table above.
   * - ``history``, ``export``
     - The ``state`` column and field hold the configuration text.
   * - Completion
     - ``init`` completes states inside regions; ``cycle`` completes only names
       that resolve as typed.

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; \
   events; \
   cycle --input fault=1 --input requested=1; \
   history"
   ...
   >>> events
   ...
   Available Events:
     • Controller.Stop
   ...
   >>> cycle --input fault=1 --input requested=1
   ...
   Cycle: 1
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0
   ...
   >>> history
   ...
      1    Controller.Running{Safety: Watching, Motion: Off}  False      0         0      0

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   init Controller.Running.Motion.On permit=1 motor=1 __forced_0=0; \
   cycle --input fault=0 --input requested=1"
   ...
   Initialized from state: Controller.Running.Motion.On
   Cycle: 0
   Current State: Controller.Running{Safety: [init], Motion: On}
   ...
   Cycle: 1
   Current State: Controller.Running{Safety: Watching, Motion: On}
   ...

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "\
   cycle --input fault=0 --input requested=1; \
   cycle /Start --input fault=0 --input requested=1; \
   export history.json"
   ...
   $ cat history.json
   ...
       "state": "Controller.Running{Safety: Watching, Motion: Off}",
   ...

The first record hot starts the controller
(:download:`controller.fcstm </_models/controller.fcstm>`), shows that
``events`` lists only ``Controller.Stop`` for that position, and that a fault
turns the motor off in the cycle in which it is seen. The second record shows
the dotted path form: ``Safety`` waits as ``[init]`` and starts in the first
cycle. The third record shows the position in an exported file. All three
commands exit with status 0. The refusals follow with their exit statuses:
every refused command stops batch processing and returns status 1.

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm --no-color -e "init Controller.Running{Safety: Watching, Motion: On permit=1 motor=1 __forced_0=0"
   ...
   Error: the braces of the configuration text 'Controller.Running{Safety: Watching, Motion: On permit=1 motor=1 __forced_0=0' are not balanced. ...
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm --no-color -e "init Controller.Running permit=1 permit=0 motor=1 __forced_0=0"
   ...
   Error: variable 'permit' is assigned more than once.
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm --no-color -e "init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=1 __forced_0=0"
   ...
   Initialization failed: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm --no-color -e "init Controller.Running permit=1 motor=1"
   ...
   Error: All variables must be provided. Missing: ['__forced_0']
   Available variables: ['__forced_0', 'motor', 'permit']
   $ echo $?
   1
   $ pyfcstm simulate -i controller.fcstm --no-color -e "init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; cycle Stop2 --input fault=0 --input requested=1"
   ...
   Cycle execution failed: Position-dependent event name 'Stop2' matches no event ...
   $ echo $?
   1

Python runtime API
------------------

.. list-table:: Main runtime surface
   :header-rows: 1

   * - Surface
     - Purpose and boundary
   * - ``SimulationRuntime(state_machine, abstract_error_mode='raise', history_size=None, initial_state=None, initial_vars=None)``
     - Creates a runtime.  Default-start mode may accept partial
       ``initial_vars``; hot start requires every declared persistent variable.
       ``history_size=None`` keeps unlimited history, while ``history_size=0``
       keeps no entries.
   * - ``cycle(events=None, *, trace=False, inputs=None, diagnostics=False) -> CycleResult``
     - Executes one cycle, validates candidate paths, commits or rolls back, and
       records history.
   * - ``CycleResult.value``
     - Legacy return value; currently ``None``.
   * - ``CycleResult.input_events``
     - Canonical event paths supplied for the cycle, in normalized input order.
   * - ``CycleResult.consumed_events``
     - Canonical event paths for evented transitions that executed.
   * - ``CycleResult.unconsumed_events``
     - Canonical supplied event paths that did not correspond to executed
       evented transitions.
   * - ``CycleResult.delta``
     - ``True`` only for a successful no-progress step; ordinary success,
       errors, and ended no-ops keep it ``False``.
   * - ``CycleResult.trace``
     - Tuple of immutable execution entries when ``trace=True``; otherwise
       empty. Delta and ignored calls also return an empty tuple. Exceptions
       return no result or partial trace.
   * - ``vars`` / ``cycle_count`` / ``history`` / ``history_size``
     - Public runtime state used by command display, tests, and tooling.  The
       command-layer ``history_size`` setting remaps ``0`` to runtime ``None``;
       direct runtime code should pass ``None`` when it wants unlimited
       history.
   * - ``configuration``
     - Immutable :class:`pyfcstm.model.Configuration` of the resting position,
       available for every model; see :ref:`sim-region-position-api`.
   * - ``current_state``
     - Current active state.  Check ``is_ended`` first; after termination this
       raises :class:`pyfcstm.simulate.SimulationRuntimeTerminalStateError`.
       For a model with regions it returns the ``Configuration`` instead of a
       ``State``.
   * - ``brief_stack``
     - Terminal-safe stack summary as ``(state_path, mode)`` tuples.  Raises
       ``SimulationRuntimeRegionQueryError`` for a model with regions.
   * - ``is_ended``
     - ``True`` after the runtime has terminated.  Later ``cycle()`` calls are
       no-ops.
   * - ``is_error_state`` / ``error_info`` / ``abstract_handler_errors``
     - Abstract-handler diagnostic state.
   * - ``register_abstract_handler`` / ``unregister_abstract_handler``
     - Manage handlers for named abstract actions.
   * - ``clear_abstract_handler_session`` / ``clear_all_abstract_handlers``
     - Clear handlers plus related diagnostics.
   * - ``get_abstract_handlers`` / ``has_abstract_handlers``
     - Inspect handler registration state.
   * - ``register_handlers_from_object``
     - Register object methods decorated with ``@abstract_handler``.
   * - ``ReadOnlyExecutionContext``
     - Immutable handler context exposing state path, variable snapshot,
       action metadata, active leaf, abstract target, and named-ref metadata.
       ``active_leaf`` is the runtime state path where the action executes: the
       active leaf state when one is active, otherwise the action's host state
       path, which is what entering a composite state reports.  For actions
       around regions see :ref:`sim-region-position-api`; the context also
       carries ``configuration``, the whole position at the moment of the call.
   * - ``abstract_handler(action_path)``
     - Decorator that marks object methods for bulk handler registration.

Committed execution trace
-------------------------

``runtime.cycle(trace=True)`` collects observations for that call only.
Collection excludes speculative validation, rejected candidate transitions,
and rolled-back Delta attempts. It does not enable collection on subsequent
calls or add fields to ``history`` and CLI ``export``. Keep the returned
``CycleResult`` to retain its trace, independently of ``history_size``.
``trace`` is a keyword-only boolean, defaulting to ``False``. Collection
allocates one persistent-variable snapshot per entry; it performs no file I/O.

.. list-table:: ``ExecutionTraceEntry`` fields
   :header-rows: 1

   * - Field
     - Meaning and boundary
   * - ``kind``
     - ``Literal["state_enter", "state_exit", "transition", "action"]``:
       ``state_enter`` before entry actions; ``state_exit`` after exit actions;
       ``transition`` after effects; ``action`` after operations or abstract
       dispatch. Entries follow execution order, including pseudo-state chains.
   * - ``state_path``
     - Tuple of strings: immutable path of the state being entered/exited, the transition source
       (owning composite for initial transitions), or action execution location.
       An ancestor aspect action records the descendant where it executes.
   * - ``vars``
     - Read-only mapping from variable names to ``int``/``float`` values at that boundary. Local temporary
       variables are excluded. Later cycles cannot change this snapshot.
   * - ``transition_label``
     - ``source_path::index::source->target`` in BMC label format; ``None`` for
       other kinds. The zero-based index addresses the source state's initial
       or outgoing transition list. Initial sources use ``INIT_STATE``;
       exit targets use ``[*]``. The synthetic root exit has index zero.
       Forced and combo declarations address their expanded model edges,
       including combo relay states. These are model-local addresses, not
       identifiers that survive editing or reordering the model.
   * - ``action_path`` / ``resolved_action_path``
     - Callsite and final ``ref`` target as ``state::collection::index``;
       ``None`` for other kinds. Collections are ``on_enters``, ``on_durings``,
       ``on_exits``, and ``on_during_aspects``. Zero-based indices distinguish
       anonymous actions; addresses refer to the current model, so preserve
       that model alongside exported traces.
   * - ``to_dict()``
     - Detached dictionary with paths as lists and variables as a dictionary,
       suitable for JSON/YAML serialization. Editing it cannot change the entry.
   * - ``str(entry)`` / ``print(entry)``
     - Single-line human-readable summary: operation, state, applicable transition/action
       addresses, a different final reference target, and variables sorted by name.
       Large integers use compact digit-count notation. ``repr(entry)`` keeps the
       dataclass representation; use ``to_dict()`` for complete machine-readable values.

This complete example separates the transition effect from the target's entry
action. The transition snapshot sees ``x == 1``; the following action sees
``x == 2``:

.. testcode::

   import json

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text('''
   def int x = 0;
   state Root {
       state Idle;
       state Done { enter { x = x + 1; } }
       [*] -> Idle;
       Idle -> Done :: Go effect { x = x + 1; };
   }
   ''')
   runtime = SimulationRuntime(model, history_size=0)
   runtime.cycle()
   result = runtime.cycle('Root.Idle.Go', trace=True)
   print([(entry.kind, entry.vars['x']) for entry in result.trace])
   payload = json.dumps([entry.to_dict() for entry in result.trace])
   print(json.loads(payload)[1]['transition_label'])
   print(runtime.history)
   for entry in result.trace:
       print(entry)

.. testoutput::

   [('state_exit', 0), ('transition', 1), ('state_enter', 1), ('action', 2)]
   Root.Idle::0::Idle->Done
   []
   State exit Root.Idle | vars={x=0}
   Transition Root.Idle | transition=Root.Idle::0::Idle->Done | vars={x=1}
   State enter Root.Done | vars={x=1}
   Action Root.Done | action=Root.Done::on_enters::0 | vars={x=2}

An empty trace does not by itself mean Delta or termination. A stable state
without during actions or enabled transitions performs no observable operations:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   runtime = SimulationRuntime(load_state_machine_from_text('state Root { [*] -> Idle; state Idle; }'))
   runtime.cycle()
   idle = runtime.cycle(trace=True)
   print(idle.delta, idle.trace, runtime.is_ended)

.. testoutput::

   False () False

Snapshots cannot be edited in place; use ``to_dict()`` for editable data.
Supply ``trace`` by name rather than as a second positional argument:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_text(
       'def int x = 0; state Root { state Idle; state Done; [*] -> Idle; '
       'Idle -> Done :: Go effect { x = x + 1; }; }')
   runtime = SimulationRuntime(model)
   runtime.cycle()
   result = runtime.cycle('Root.Idle.Go', trace=True)
   try:
       result.trace[-1].vars['x'] = 9
   except TypeError as error:
       print(error)
   try:
       runtime.cycle(None, True)
   except TypeError as error:
       print(error)

.. testoutput::

   'mappingproxy' object does not support item assignment
   ... takes from 1 to 2 positional arguments but 3 were given

This API serializes entries, not a self-contained replay file. A caller saving
them must also retain the model, cycle number, input events, and observation
convention. CLI ``export`` still writes macro-step history.

An ``action`` entry for an abstract action means dispatch was reached. A
registered handler is not required, and ``abstract_error_mode='log'`` may
allow a failed handler to complete the cycle. Consult
``abstract_handler_errors`` for those failures. Hot start records only work
performed by subsequent cycles, without inventing entry actions that were
skipped during construction.

See :meth:`pyfcstm.simulate.runtime.SimulationRuntime.cycle` for a complete
executable example. ``test/simulate/test_execution_trace.py`` checks ordering,
snapshots, references, rejection, Delta, errors, interruption, hot start, and
pseudo/forced/combo chains. ``test/simulate/test_execution_trace_semantic_fixtures.py``
compares trace-enabled and ordinary execution against every runnable shared
simulation fixture. ``test/bmc/test_execution_trace_alignment.py`` checks edge
addresses against public BMC expansion.

Public failures and boundaries
------------------------------

.. list-table:: Failure surfaces
   :header-rows: 1

   * - Failure
     - Where it appears
     - Meaning
   * - ``ValueError`` from construction or hot start
     - Python API and ``init`` command message
     - Invalid error mode, unknown variables, missing hot-start variables,
       unresolved state path, or invalid persistent value type.  For positions
       of models with regions: a region as the position, an unknown entry, a
       duplicate region, bad position text, every region of an owner Done, a
       ``Configuration`` or ``State`` of another model (all with their texts in
       :ref:`sim-region-hot-start`); a position of the wrong type raises
       ``TypeError``.
   * - ``SimulationRuntimeEventError``
     - Python API; command layer reports ``Cycle execution failed: ...``
     - Unsupported, unresolved, or foreign event input.
   * - ``SimulationRuntimeDfsError``
     - Python API; command layer reports an unbounded execution-chain message
     - No candidate has a stable continuation and validation found a repeated
       execution path in the same cycle, or exceeded DFS/stack-depth limits.
       Loop errors include state paths and repair guidance. A cyclic candidate
       is skipped when a later candidate can reach a stoppable state or termination.
   * - ``SimulationRuntimeRegionQueryError``
     - Python API ``brief_stack``
     - The model has regions and a single stack cannot describe it; use
       ``configuration``.
   * - ``SimulationRuntimeTerminalStateError``
     - Python API ``current_state`` after termination
     - Runtime has ended and the active stack is empty.
   * - ``SimulationRuntimeExpressionError``
     - Python API; command layer reports ``Cycle execution failed: ...``
     - Runtime evaluation of a guard or action expression failed.
   * - ``SimulationRuntimeActionReferenceError``
     - Python API
     - A named action reference could not be resolved or executed safely.
   * - Abstract handler exception
     - Python API
     - In ``abstract_error_mode='raise'`` the runtime enters an error state and
       raises; in ``'log'`` mode the error is collected in
       ``abstract_handler_errors``.
   * - Unsupported export suffix or file error
     - Command layer
     - ``export`` returns a message; it is not a Python runtime method.

Source facts
------------

This reference is aligned with these implementation and test facts:

* ``pyfcstm/entry/simulate/__init__.py`` for Click options and parse failure
  handling.
* ``pyfcstm/entry/simulate/batch.py`` and ``commands.py`` for batch and REPL
  command behavior.
* ``pyfcstm/simulate/runtime.py``, ``context.py`` and ``decorators.py`` for the
  Python API surface.
* ``test/fixtures/simulate_semantics/cases/`` and
  ``test/testings/simulate_semantics.py`` for execution-order scenarios.
* ``docs/source/tutorials/simulation/``: the examples of the simulation tutorial.

.. toctree::
   :maxdepth: 1

   inputs

Candidate decision diagnostics
------------------------------------------------------------

For rejected candidates, captured Python reports, REPL queries, per-cycle inputs and JSONL output, see :doc:`diagnostics`.
