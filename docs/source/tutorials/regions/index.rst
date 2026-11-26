Your first model with regions
=============================

In this tutorial you run one small controller that has two **regions** in one
state, and you watch what the order of those regions does. At the end you have
simulated the controller, swapped the region order and seen the result change,
read the matching inspect diagnostic, checked the same property with bounded
model checking on both versions, generated and run a Python runtime, and
looked at the drawing of the model.

You need ``pyfcstm`` installed and the two model files in this directory.
Download :download:`controller.fcstm <controller.fcstm>` and
:download:`controller_swapped.fcstm <controller_swapped.fcstm>` into an empty
directory and run every command there. The commands use only relative file
names.

1. Read the model
-----------------

The controller is an interlock. A ``Safety`` region decides whether the motor
may run, and a ``Motion`` region switches the motor.

.. literalinclude:: controller.fcstm
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
complete input vector, so each command gives ``fault`` and ``requested`` once.
``/Start`` and ``/Stop`` are root events.

.. literalinclude:: simulate_interlock.demo.sh
   :language: bash
   :caption: ``simulate_interlock.demo.sh``

:download:`Download simulate_interlock.demo.sh <simulate_interlock.demo.sh>`
and run it, or paste the ``pyfcstm simulate`` command into your shell. The
output is:

.. literalinclude:: simulate_interlock.demo.sh.txt
   :language: text
   :caption: ``simulate_interlock.demo.sh.txt``

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
raise the fault in two consecutive cycles:

.. literalinclude:: simulate_swapped.demo.sh
   :language: bash
   :caption: ``simulate_swapped.demo.sh``

:download:`Download simulate_swapped.demo.sh <simulate_swapped.demo.sh>` and run it with ``sh simulate_swapped.demo.sh`` in the directory that holds the models.

.. literalinclude:: simulate_swapped.demo.sh.txt
   :language: text
   :caption: ``simulate_swapped.demo.sh.txt``

Compare cycle 4 with the previous run. The fault is raised, ``permit`` is
``0``, and ``motor`` is still ``1``. ``Motion`` now runs first, so it reads the
``permit`` that ``Safety`` wrote in the previous cycle. The motor turns off one
cycle later, in cycle 5. The configuration text also lists the regions in the
new order: ``{Motion: On, Safety: Watching}``.

The writing order of regions is part of the meaning of the model. Two models
that differ only in that order are different models.

4. Inspect the model
--------------------

``pyfcstm inspect`` reports regions and checks their order. The demo prints
the start of the report for ``controller.fcstm`` and only the diagnostic codes
of both models, then the full text of the one diagnostic that concerns region
order.

.. literalinclude:: inspect_regions.demo.sh
   :language: bash
   :caption: ``inspect_regions.demo.sh``

:download:`Download inspect_regions.demo.sh <inspect_regions.demo.sh>` and run it with ``sh inspect_regions.demo.sh`` in the directory that holds the models.

.. literalinclude:: inspect_regions.demo.sh.txt
   :language: text
   :caption: ``inspect_regions.demo.sh.txt``

Look at three places:

* The summary lists ``regions: 2`` with the order of each region in its owner
  (``order 0`` is the first one written).
* ``controller.fcstm`` has no region order diagnostic. It does have four
  warnings about its constant ``during`` assignments and a leaf without an
  outgoing transition. They are about this example's style, not about regions,
  and they do not affect the scenario.
* ``controller_swapped.fcstm`` adds ``I_REGION_BACKWARD_READ``. It is an
  information-level diagnostic: ``Motion`` reads ``permit``, which the later
  ``Safety`` region writes, so ``Motion`` sees the previous cycle's value. The
  message says it is the defined behavior of ordered regions, not a defect. It
  tells you to keep the order if you want the previous value, or to write the
  producing region first if you want the current one.

5. Check a property with bounded model checking
-----------------------------------------------

Write the property "when the fault is raised, the motor is off at the end of
that cycle". The property file ``fault_beat_motor_off.fbmcq`` is:

.. literalinclude:: fault_beat_motor_off.fbmcq
   :language: text
   :caption: ``fault_beat_motor_off.fbmcq``

:download:`Download fault_beat_motor_off.fbmcq <fault_beat_motor_off.fbmcq>`.
The first line assumes the fault input is non-zero in step 3, the fourth macro
step. The second line is a ``forbid`` property with bound 4: it searches for a
run of at most four macro steps in which, after step 3 (``cycle == 4``), the
motor is still on.

Run it on the interlock model:

.. literalinclude:: bmc_interlock.demo.sh
   :language: bash
   :caption: ``bmc_interlock.demo.sh``

:download:`Download bmc_interlock.demo.sh <bmc_interlock.demo.sh>` and run it with ``sh bmc_interlock.demo.sh`` in the directory that holds the models.

.. literalinclude:: bmc_interlock.demo.sh.txt
   :language: text
   :caption: ``bmc_interlock.demo.sh.txt``

The command removes the ``Solver:`` timing line so that the output stays the
same on every run. Read the verdict first: ``PROPERTY GUARANTEED WITHIN
BOUND``. The solver searched for a counterexample and found none (``UNSAT``),
so the property holds in every run of at most 4 macro steps with a fault in
step 3. The last line is the bound: it says nothing about longer runs.

Now run the same property on the swapped model. This command is expected to
fail with exit status ``1``, because the property does not hold:

.. literalinclude:: bmc_swapped.demox.sh
   :language: bash
   :caption: ``bmc_swapped.demox.sh``

:download:`Download bmc_swapped.demox.sh <bmc_swapped.demox.sh>` and run it with ``sh bmc_swapped.demox.sh``. This script ends with exit status ``1`` by design. Do not paste its lines into an interactive shell: ``set -e`` closes the shell when the check fails.

.. literalinclude:: bmc_swapped.demox.sh.txt
   :language: text
   :caption: ``bmc_swapped.demox.sh.txt``

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

Generate the built-in Python runtime for the interlock model and drive it with
the scenario of step 2:

.. literalinclude:: generate_runtime.demo.sh
   :language: bash
   :caption: ``generate_runtime.demo.sh``

:download:`Download generate_runtime.demo.sh <generate_runtime.demo.sh>` and run it with ``sh generate_runtime.demo.sh`` in the directory that holds the models.

The driver ``run_scenario.py`` supplies the inputs of each cycle in the
``inputs`` argument and prints the cycle count, ``configuration`` and the two
variables:

.. literalinclude:: run_scenario.py
   :language: python
   :caption: ``run_scenario.py``

:download:`Download run_scenario.py <run_scenario.py>` into the same directory.
The output is:

.. literalinclude:: generate_runtime.demo.sh.txt
   :language: text
   :caption: ``generate_runtime.demo.sh.txt``

The first three lines are the files ``pyfcstm generate`` wrote. The last six
lines match the six cycles of step 2: the same configurations, the same
``permit`` and ``motor``, including the motor switching off in the fault
cycle. A model with regions has no ``current_state_path``; you read the
position with ``configuration``.

7. Look at the drawing
----------------------

``pyfcstm plantuml`` prints the PlantUML text of the model:

.. literalinclude:: plantuml_regions.demo.sh.txt
   :language: text
   :caption: ``pyfcstm plantuml -i controller.fcstm``

Find the two region notes ``region 1: Safety`` and ``region 2: Motion`` inside
``Running``. A line with ``--`` separates the regions, which are drawn stacked
one above the other in the rendered picture.

``pyfcstm diagram`` writes the interactive viewer, a single self-contained HTML
file that needs no network access:

.. code-block:: bash

   pyfcstm diagram -i controller.fcstm -o viewer.html

Open ``viewer.html`` in a browser. Check that the frame of ``Running`` holds
the two regions side by side, titled ``region 1: Safety`` and
``region 2: Motion`` and separated by a dashed line. Without ``-o``, the same command prints the
portable JSON of the diagram, where each region is a node marked as a region:

.. literalinclude:: diagram_regions.demo.sh
   :language: bash
   :caption: ``diagram_regions.demo.sh``

:download:`Download diagram_regions.demo.sh <diagram_regions.demo.sh>` and run it with ``sh diagram_regions.demo.sh`` in the directory that holds the models.

.. literalinclude:: diagram_regions.demo.sh.txt
   :language: text
   :caption: ``diagram_regions.demo.sh.txt``

:download:`Download list_regions.py <list_regions.py>` to run this command.

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
