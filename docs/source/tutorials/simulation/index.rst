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

The model is ``example1_basic.full.fcstm``. Download
:download:`example1_basic.full.fcstm <example1_basic.full.fcstm>` into an empty
directory to run the command there.

.. literalinclude:: example1_basic.full.fcstm
   :language: fcstm
   :caption: ``example1_basic.full.fcstm``

.. code-block:: console

   $ pyfcstm simulate -i example1_basic.full.fcstm --no-color \
     -e "cycle; events; cycle Go; current; cycle; history 3"
   ────────────────────────────────────────────────────────────
   >>> cycle
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Root.A
   Variables:
     counter = 1

   ────────────────────────────────────────────────────────────
   >>> events
   ────────────────────────────────────────────────────────────
   Available Events:
     • Go (Root.A.Go)

   ────────────────────────────────────────────────────────────
   >>> cycle Go
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Root.B
   Variables:
     counter = 11

   ────────────────────────────────────────────────────────────
   >>> current
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Root.B
   Variables:
     counter = 11

   ────────────────────────────────────────────────────────────
   >>> cycle
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Root.B
   Variables:
     counter = 21

   ────────────────────────────────────────────────────────────
   >>> history 3
   ────────────────────────────────────────────────────────────
    Cycle  State   Delta  counter
   -------------------------------
      1    Root.A  False     1
      2    Root.B  False    11
      3    Root.B  False    21

The first ``cycle`` initializes the machine at ``Root.A``, whose ``during``
already ran once, so ``counter`` is 1.  The ``events`` command then shows that
``Go`` is available from the current state.  After ``cycle Go`` the current
state is ``Root.B``; the plain ``cycle`` after it stays in ``Root.B`` and the
short ``history`` table shows the three recorded cycles.

Try one Python runtime loop
---------------------------

If you are embedding pyfcstm in Python tests or tools, the runtime API follows
the same model: parse DSL, build the state-machine model, construct
``SimulationRuntime``, and call ``cycle()``.  Each call returns a
``CycleResult``.  Its legacy ``value`` is currently ``None``, while
``input_events``, ``consumed_events`` and ``unconsumed_events`` tell you which
canonical event paths were supplied, used or left unused in that cycle.

.. testcode::

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   machine = load_state_machine_from_text("""
   def int counter = 0;

   state System {
       [*] -> Idle;

       state Idle {
           during {
               counter = counter + 1;
           }
       }

       state Active {
           during {
               counter = counter + 10;
           }
       }

       Idle -> Active : if [counter >= 5];
       Active -> Idle : if [counter >= 50];
   }
   """)

   runtime = SimulationRuntime(machine)
   print("Initial: state=%s, counter=%d" % (".".join(runtime.current_state.path), runtime.vars["counter"]))
   for i in range(1, 8):
       runtime.cycle()
       print("Cycle %d: state=%s, counter=%d" % (i, ".".join(runtime.current_state.path), runtime.vars["counter"]))

.. testoutput::

   Initial: state=System, counter=0
   Cycle 1: state=System.Idle, counter=1
   Cycle 2: state=System.Idle, counter=2
   Cycle 3: state=System.Idle, counter=3
   Cycle 4: state=System.Idle, counter=4
   Cycle 5: state=System.Idle, counter=5
   Cycle 6: state=System.Active, counter=15
   Cycle 7: state=System.Active, counter=25

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

Custom numeric input generators
-------------------------------

For models that read environment values each cycle, follow the executable
construction and subclass examples in :doc:`../../reference/simulation/inputs`.
They cover explicit overrides, correlated vectors, and failure-safe advancement.

Where to go next
----------------

* :doc:`/tutorials/regions/index` runs a model whose states own ordered
  parallel regions, and shows that the writing order of regions changes the
  result of a cycle.
