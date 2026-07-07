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

Parse, decode, grammar, and model-validation failures are written to stderr as
``Failed to parse DSL file: ...``.  Batch and REPL command failures normally
return a user-facing message in command output instead of raising through the
CLI process.

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
   * - ``init <state_path> [var=value...]``
     - Target state plus numeric variable assignments.
     - Rebuilds the runtime as a hot start.  Every declared variable must be
       provided.  Values accept decimal, hexadecimal, binary, float, and
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

History and export formats
--------------------------

Runtime history entries are dictionaries with ``cycle``, ``state``, ``vars``,
and optional ``events`` keys.  ``history`` displays retained rows; ``export`` is
a command-layer feature and is not a :class:`pyfcstm.simulate.SimulationRuntime` method.

.. list-table:: Export formats
   :header-rows: 1

   * - Suffix
     - Shape
     - Notes
   * - ``.csv``
     - Columns ``cycle``, ``state``, ``events``, then sorted variable names.
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

Python runtime API
------------------

.. list-table:: Main runtime surface
   :header-rows: 1

   * - Surface
     - Purpose and boundary
   * - ``SimulationRuntime(state_machine, abstract_error_mode='raise', history_size=None, initial_state=None, initial_vars=None)``
     - Creates a runtime.  Default-start mode may accept partial
       ``initial_vars``; hot start requires every declared persistent variable.
   * - ``cycle(events=None) -> CycleResult``
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
   * - ``vars`` / ``cycle_count`` / ``history`` / ``history_size``
     - Public runtime state used by command display, tests, and tooling.
   * - ``current_state``
     - Current active state.  Check ``is_ended`` first; after termination this
       raises :class:`pyfcstm.simulate.SimulationRuntimeTerminalStateError`.
   * - ``brief_stack``
     - Terminal-safe stack summary as ``(state_path, mode)`` tuples.
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
   * - ``abstract_handler(action_path)``
     - Decorator that marks object methods for bulk handler registration.

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
       unresolved state path, or invalid persistent value type.
   * - ``SimulationRuntimeEventError``
     - Python API; command layer reports ``Cycle execution failed: ...``
     - Unsupported, unresolved, or foreign event input.
   * - ``SimulationRuntimeDfsError``
     - Python API; command layer reports an unbounded execution-chain message
     - Speculative validation exceeded DFS or stack-depth safety limits while
       looking for a stoppable state or termination.
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
* ``docs/source/tutorials/simulation/*.demo.*`` for checked documentation
  transcripts.
