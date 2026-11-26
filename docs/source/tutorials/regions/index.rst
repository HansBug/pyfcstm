Your first model with regions
=============================

In this tutorial you run one small controller that has two **regions** in one
state, and you watch what the order of those regions does. At the end you have
simulated the controller, swapped the region order and seen the result change,
read the matching inspect diagnostic, checked the same property with bounded
model checking on both versions, generated and run a Python runtime, and
looked at the drawing of the model.

You need ``pyfcstm`` installed. Download
:download:`controller.fcstm </_models/controller.fcstm>`,
:download:`controller_swapped.fcstm </_models/controller_swapped.fcstm>` and
:download:`fault_beat_motor_off.fbmcq <fault_beat_motor_off.fbmcq>` into an
empty directory and run every command there.

1. Read the model
-----------------

The controller is an interlock. A ``Safety`` region decides whether the motor
may run, and a ``Motion`` region switches the motor.

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: ``controller.fcstm``

Notice three things before you run anything:

* ``Running`` owns two ``region`` blocks. Both are active whenever ``Running``
  is active, and each one has its own initial transition (``[*] -> Watching``
  and ``[*] -> Off``).
* In every cycle the regions of one owner run **one after another, in the
  order they are written**. ``Safety`` is written first, so it writes
  ``permit`` before ``Motion`` reads it in the same cycle.
* ``!Running -> Idle : /Stop;`` is a forced transition written on the owner.
  It leaves ``Running`` from wherever both regions are, so ``/Stop`` stops the
  whole group at once. The forced transition adds a hidden variable
  ``__forced_0``, which you will see in the output.

2. Simulate a scenario
----------------------

Run one scenario in batch mode. Every cycle that really executes needs the
complete input vector, so each ``cycle`` gives ``fault`` and ``requested``.
``/Start`` and ``/Stop`` are root events.

.. code-block:: console

   $ pyfcstm simulate -i controller.fcstm -e "\
   cycle --input fault=0 --input requested=0; \
   cycle /Start --input fault=0 --input requested=0; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1; \
   cycle --input fault=0 --input requested=1; \
   cycle /Stop --input fault=0 --input requested=1"
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
   >>> cycle /Start --input fault=0 --input requested=0
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=0 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 3
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 4
   Current State: Controller.Running{Safety: Watching, Motion: Off}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=0 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 5
   Current State: Controller.Running{Safety: Watching, Motion: On}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 1

   ────────────────────────────────────────────────────────────
   >>> cycle /Stop --input fault=0 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 6
   Current State: Controller.Idle
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 1

Read the ``Current State`` line of each cycle. A model with regions prints the
whole **configuration**: the owner followed by the position of every region in
braces, such as ``Controller.Running{Safety: Watching, Motion: Off}``.

* Cycle 1 enters ``Controller.Idle``.
* Cycle 2 handles ``/Start``. Both regions take their initial transition, and
  ``permit`` is already ``1`` because ``Safety`` ran its ``during`` in the same
  cycle.
* Cycle 3 has ``requested=1``: ``Motion`` goes to ``On`` and ``motor`` is ``1``.
* Cycle 4 has ``fault=1``. Look at ``motor``: it is ``0`` in this very cycle.
  ``Safety`` ran first and wrote ``permit = 0``, then ``Motion`` read that new
  value and switched to ``Off``.
* Cycle 5 clears the fault and the motor runs again. Cycle 6 handles
  ``/Stop``: the forced transition leaves ``Running`` and the configuration is
  ``Controller.Idle`` again.

3. Swap the region order
------------------------

``controller_swapped.fcstm`` has the same two regions, with ``Motion``
written before ``Safety``. Nothing else differs. Run the same scenario, but
raise the fault in two consecutive cycles. The first three cycles print the
same values as before and are left out here:

.. code-block:: console

   $ pyfcstm simulate -i controller_swapped.fcstm -e "\
   cycle --input fault=0 --input requested=0; \
   cycle /Start --input fault=0 --input requested=0; \
   cycle --input fault=0 --input requested=1; \
   cycle --input fault=1 --input requested=1; \
   cycle --input fault=1 --input requested=1"
   ...
   Cycle: 4
   Current State: Controller.Running{Motion: On, Safety: Watching}
   Variables:
     __forced_0 = 0
     motor = 1
     permit = 0

   ────────────────────────────────────────────────────────────
   >>> cycle --input fault=1 --input requested=1
   ────────────────────────────────────────────────────────────
   Cycle: 5
   Current State: Controller.Running{Motion: Off, Safety: Watching}
   Variables:
     __forced_0 = 0
     motor = 0
     permit = 0

Compare cycle 4 with the previous run. The fault is raised, ``permit`` is
``0``, and ``motor`` is still ``1``. ``Motion`` now runs first, so it reads the
``permit`` that ``Safety`` wrote in the previous cycle. The motor turns off one
cycle later, in cycle 5. The configuration text also lists the regions in the
new order: ``{Motion: On, Safety: Watching}``.

The writing order of regions is part of the meaning of the model. Two models
that differ only in that order are different models.

4. Inspect the model
--------------------

``pyfcstm inspect`` reports regions and checks their order. The report is
long, so only its beginning is shown:

.. code-block:: console

   $ pyfcstm inspect -i controller.fcstm
   [WARN] FCSTM Inspect Report: controller.fcstm

   Summary
     status: warning
     root: Controller
     states: 6 total / 4 leaf
     transitions: 7
     regions: 2
       Controller.Running.Safety: order 0 in Controller.Running; 1 states
       Controller.Running.Motion: order 1 in Controller.Running; 2 states
   ...

The summary lists ``regions: 2`` with the order of each region in its owner
(``order 0`` is the first one written). The rest of the report has four
warnings about the constant ``during`` assignments of this example and a leaf
without an outgoing transition. They are about this example's style, not about
regions, and they do not affect the scenario.

The swapped model gets one more diagnostic, at the end of its report:

.. code-block:: console

   $ pyfcstm inspect -i controller_swapped.fcstm
   ...
   [INFO] I_REGION_BACKWARD_READ
     Region 'Controller.Running.Motion' reads variable 'permit', which is produced by the later region 'Controller.Running.Safety'; it sees the value from the previous cycle.
     --> controller_swapped.fcstm:16:13
       |
    15 |             state On { during { motor = 1; } }
    16 |             Off -> On : if [permit != 0 && requested != 0];
       |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    17 |             On -> Off : if [permit == 0 || requested == 0];
       |
      = source: inspect-static
      = why: An earlier region reads something a later region produces in the same cycle, so it sees the previous cycle's value.
      = fix: kind: confirm_order; target: region; rationale: Keep the declaration order when reading the previous cycle's value is intended.
      = fix: kind: reorder_regions; target: region; rationale: Declare the producing region before the reading region when the current cycle's value is needed.
      = do-not: Do not treat this as a defect; it is the defined behavior of ordered regions.

``I_REGION_BACKWARD_READ`` is an information-level diagnostic: ``Motion``
reads ``permit``, which the later ``Safety`` region writes, so ``Motion`` sees
the previous cycle's value. The message says it is the defined behavior of
ordered regions, not a defect. It tells you to keep the order if you want the
previous value, or to write the producing region first if you want the current
one.

5. Check a property with bounded model checking
-----------------------------------------------

Write the property "when the fault is raised, the motor is off at the end of
that cycle". The property file ``fault_beat_motor_off.fbmcq`` is:

.. literalinclude:: fault_beat_motor_off.fbmcq
   :language: text
   :caption: ``fault_beat_motor_off.fbmcq``

The first line assumes the fault input is non-zero in step 3, the fourth macro
step. The second line is a ``forbid`` property with bound 4: it searches for a
run of at most four macro steps in which, after step 3 (``cycle == 4``), the
motor is still on.

Run it on the interlock model:

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q fault_beat_motor_off.fbmcq
   BMC forbid <= 4: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   Scenario: FEASIBLE
   Property verdict: SATISFIED WITHIN BOUND (NO COUNTEREXAMPLE)
   Semantic interpretation: The counterexample objective is unsatisfiable over the feasible bounded scenario; every admissible execution within the bound satisfies the property.
   Primary search: COUNTEREXAMPLE = UNSAT
   Conclusion: Every admissible execution within 4 macro-steps satisfies the forbid property.
   Evidence:
     Model evidence: no SAT model available.

   Solver: UNSAT in ... ms
   Feasibility: kernel=sat, initialization=sat, assumptions=sat

   This is a bounded result over at most 4 macro-steps; it does not establish behavior beyond that bound.
   Use --json for the complete witness, replay trace, and stable machine-readable diagnostics.

Read the verdict first: ``PROPERTY GUARANTEED WITHIN BOUND``. The solver
searched for a counterexample and found none (``UNSAT``), so the property
holds in every run of at most 4 macro steps with a fault in step 3. The
``Solver`` line shows the solving time, which differs from run to run. The
last lines state the bound: the result says nothing about longer runs.

Now run the same property on the swapped model. The property does not hold
there, so the command ends with exit status ``1``:

.. code-block:: console

   $ pyfcstm bmc -i controller_swapped.fcstm -q fault_beat_motor_off.fbmcq
   BMC forbid <= 4: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   Scenario: FEASIBLE
   Property verdict: NOT SATISFIED WITHIN BOUND (COUNTEREXAMPLE FOUND)
   Semantic interpretation: A counterexample execution exists within the bound; the property is not satisfied there.
   Primary search: COUNTEREXAMPLE = SAT
   Conclusion: At least one admissible execution violates the forbid property within 4 macro-steps.
   Evidence:
     Model role: PRIMARY COUNTEREXAMPLE
     Model evidence: SAT model available.
     Replay: verified (5 frames, 4 steps).

   Solver: SAT in ... ms
   Feasibility: kernel=sat, initialization=sat, assumptions=sat

   Trace
     0: init
          -> Controller.Idle [initial]
          [start] -> Controller.Idle [initial]
     1: Controller.Idle
          -> Controller.Running{Motion: Off, Safety: Watching} [transition; events=Controller.Start]
          Controller.Idle -> Controller.Running [transition]
          Running: [start] -> Motion.Off [initial]
          Running: [start] -> Safety.Watching [initial]
     2: Controller.Running{Motion: Off, Safety: Watching}
          -> Controller.Running{Motion: On, Safety: Watching} [transition]
          Motion: Off -> On [transition]
          Safety: Watching -> Watching [fallback]
     3: Controller.Running{Motion: On, Safety: Watching}
          -> Controller.Running{Motion: On, Safety: Watching} [fallback]
          Motion: On -> On [fallback]
          Safety: Watching -> Watching [fallback]

   This is a bounded result over at most 4 macro-steps; it does not establish behavior beyond that bound.
   Use --json for the complete witness, replay trace, and stable machine-readable diagnostics.
   $ echo $?
   1

The verdict is ``PROPERTY DOES NOT HOLD WITHIN BOUND`` and the solver status
is ``SAT``. The solver status describes the search for a counterexample; the
verdict is what it means for your property. ``SAT`` here is bad news, while
``UNSAT`` in the previous run was good news. The trace is the counterexample:
``Motion`` goes ``Off -> On`` in step 2 and stays ``On`` in step 3 although the
fault is raised, which is the late switch-off you saw in the simulator. The
line ``Replay: verified`` states that the simulator reproduced this trace.
Read :doc:`/reference/bmc_results/index` for every field of the result.

6. Generate and run a Python runtime
------------------------------------

Generate the built-in Python runtime for the interlock model. The command
prints nothing and writes ``machine.py`` and two README files into
``runtime_out``:

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o runtime_out

Drive the generated ``ControllerMachine`` with the scenario of step 2. Save
this script as ``run_scenario.py`` in the same directory and run it with
``python run_scenario.py``:

.. testcode::

   import sys

   sys.path.insert(0, "runtime_out")
   from machine import ControllerMachine

   # (event, fault, requested) for each cycle of the scenario.
   scenario = [
       (None, 0, 0),
       ("/Start", 0, 0),
       (None, 0, 1),
       (None, 1, 1),
       (None, 0, 1),
       ("/Stop", 0, 1),
   ]

   machine = ControllerMachine()
   for event, fault, requested in scenario:
       machine.cycle(events=event, inputs={"fault": fault, "requested": requested})
       print(
           machine.cycle_count,
           machine.configuration,
           "permit=%d" % machine.vars["permit"],
           "motor=%d" % machine.vars["motor"],
       )

It prints:

.. testoutput::

   1 Controller.Idle permit=0 motor=0
   2 Controller.Running{Safety: Watching, Motion: Off} permit=1 motor=0
   3 Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1
   4 Controller.Running{Safety: Watching, Motion: Off} permit=0 motor=0
   5 Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1
   6 Controller.Idle permit=1 motor=0

The six lines match the six cycles of step 2: the same configurations, the
same ``permit`` and ``motor``, including the motor switching off in the fault
cycle. A model with regions has no ``current_state_path``; you read the
position with ``configuration``.

7. Look at the drawing
----------------------

``pyfcstm plantuml`` prints the PlantUML text of the model. The part that
draws the two regions of ``Running`` is:

.. code-block:: console

   $ pyfcstm plantuml -i controller.fcstm
   @startuml
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
   @enduml

Find the two region notes ``region 1: Safety`` and ``region 2: Motion`` inside
``Running``. The line with ``--`` separates the regions, which are drawn
stacked one above the other:

.. figure:: /_models/controller.fcstm.puml.svg
   :alt: PlantUML drawing of the controller with the Safety region above the Motion region
   :align: center

   ``Running`` holds ``region 1: Safety`` above ``region 2: Motion``, separated
   by a dashed line.

``pyfcstm diagram`` writes the interactive viewer, a single self-contained HTML
file that needs no network access:

.. code-block:: bash

   pyfcstm diagram -i controller.fcstm -o viewer.html

Open ``viewer.html`` in a browser. Check that the frame of ``Running`` holds
the two regions side by side, titled ``region 1: Safety`` and
``region 2: Motion`` and separated by a dashed line.

8. Where to go next
-------------------

You now have a model whose regions run in written order, and you have seen
that order in the simulator, the inspect report, the checker, a generated
runtime and the drawing. Continue with the page that matches what you want to
do:

* :doc:`/how_to/regions/index` has task recipes: add a region, choose the
  order, read the configuration, hot start a model with regions.
* :doc:`/explanations/region_semantics/index` explains how one cycle runs a
  model with regions, with traces.
* :doc:`/explanations/region_design/index` explains why regions run in order.
* :doc:`/reference/region_model/index` lists the exact rules of the language
  and the model.
* :doc:`/reference/simulation/index` and :doc:`/reference/bmc_query/index`
  list the simulator and query facts used above.
