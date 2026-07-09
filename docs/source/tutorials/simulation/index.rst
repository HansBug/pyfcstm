FCSTM simulation first run
==========================

This page is the short first-run path for the FCSTM simulator.  It shows the
minimum concepts you need, one reproducible batch command, and where to go next
for task recipes or execution-order details.

What the simulator checks
-------------------------

The simulator executes the parsed model directly, before you generate target
code.  In a simulation run:

* a **leaf state** can be the current stoppable state;
* a **composite state** contains child states and chooses an initial child;
* a **pseudo state** is an automatic routing state, not a normal stopping point;
* lifecycle actions such as ``enter``, ``during`` and ``exit`` update variables
  while transitions move between states.

For full execution-order details, see
:doc:`../../explanations/execution_semantics/index`.  For concrete simulator
commands, see :doc:`../../how_to/simulation/index`.  For exact command, export
and Python API facts, see :doc:`../../reference/simulation/index`.

Run one batch transcript
------------------------

Batch mode uses the same command processor as the interactive REPL.  Commands
are separated by semicolons, so a short transcript is enough to verify initial
entry, available events, event-driven transition, current state display and
history output:

.. code-block:: bash

   pyfcstm simulate -i ../cli/simple_machine.fcstm \
     -e "cycle; events; cycle Start; current; cycle Stop; history 3" \
     --no-color

The documentation keeps this transcript generated from a real demo script:

.. literalinclude:: cli_batch.demo.sh.txt
   :language: text

The first ``cycle`` initializes the machine at ``SimpleMachine.Idle``.  The
``events`` command then shows that ``Start`` is available from the current
state.  After ``cycle Start`` the current state is ``SimpleMachine.Running``;
``cycle Stop`` reaches ``SimpleMachine.Stopped`` and the short ``history`` table
shows the three recorded cycles.

Try one Python runtime loop
---------------------------

If you are embedding pyfcstm in Python tests or tools, the runtime API follows
the same model: parse DSL, build the state-machine model, construct
``SimulationRuntime``, and call ``cycle()``.  Each call returns a
``CycleResult``.  Its legacy ``value`` is currently ``None``, while
``input_events``, ``consumed_events`` and ``unconsumed_events`` tell you which
canonical event paths were supplied, used or left unused in that cycle.

.. literalinclude:: basic_usage.demo.py
   :language: python
   :caption: Minimal Python simulation loop

Output:

.. literalinclude:: basic_usage.demo.py.txt
   :language: text

The example only prints state and variables.  If you need the exact
``CycleResult`` fields, event input forms, export formats or public runtime
exceptions, use :doc:`../../reference/simulation/index`.

Old topic map
-------------

The previous long simulation guide mixed tutorial, how-to and explanation
material.  The main topics now live here:

.. list-table:: Simulation topic destinations
   :header-rows: 1

   * - Old topic
     - New location
   * - Python API loops and event injection
     - :doc:`../../how_to/simulation/index`
   * - Batch mode, REPL commands, ``export`` and output formats
     - :doc:`../../how_to/simulation/index`
   * - Hot start task usage
     - :doc:`../../how_to/simulation/index`
   * - Abstract handlers
     - :doc:`../../how_to/simulation/index`
   * - Configuration settings and command-line facts
     - :doc:`../../reference/simulation/index`
   * - Testing, debugging and best-practice notes
     - :doc:`../../how_to/simulation/index`
   * - Business examples and long semantic walkthroughs
     - :doc:`../../explanations/execution_semantics/index`
   * - Execution order, composite entry, aspect actions and pseudo states
     - :doc:`../../explanations/execution_semantics/index`
   * - DSL syntax used by examples
     - :doc:`../../reference/dsl/index`
   * - DSL semantic background
     - :doc:`../../explanations/dsl_semantics/index`

The legacy example resources remain in this directory so old links and
source-output pairs stay stable. The migration log records each resource and
the final cleanup audit explains why these compatibility resources remain.
