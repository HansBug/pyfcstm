Quick Start
===========

This page gives the shortest practical path through pyfcstm: write one FCSTM
file, simulate it, inspect the structured model report, generate code from a
built-in template, and produce a PlantUML diagram source file.

For deeper explanations, continue to the dedicated tutorials linked from each
step. This page intentionally stays small and uses the built-in template entry
point ``--template`` instead of a repository-local template directory.

1. Write a small state machine
------------------------------

Create ``traffic_light.fcstm``:

.. literalinclude:: traffic_light.fcstm
   :language: fcstm

2. Simulate the behavior
------------------------

Run a few cycles without writing Python code:

.. code-block:: console

   $ pyfcstm simulate -i traffic_light.fcstm -e "cycle; cycle; current"
   ...
   ────────────────────────────────────────────────────────────
   >>> current
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: TrafficLight.Red
   Variables:
     timer = 2

The simulator is useful for checking lifecycle actions and transition timing
before generating target-language code. See :doc:`/tutorials/simulation/index`
for interactive sessions, hot start, batch mode, and execution semantics.

3. Inspect the model
--------------------

``inspect`` is human-readable by default. Use ``--format json`` when you
want a structured report with states, transitions, metrics, derived graphs, and
diagnostics:

.. code-block:: console

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
   $ pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json

The traffic light model is intentionally simple, so diagnostics may be empty.
The dedicated :doc:`/tutorials/inspect/index` tutorial shows richer diagnostics,
source spans, suggested fixes, and how these messages can guide LLM-assisted
repairs.

4. Generate code from a built-in template
-----------------------------------------

Use ``--template`` for packaged built-in templates:

.. code-block:: console

   $ pyfcstm generate -i traffic_light.fcstm --template python -o _quick_start_python --clear
   $ LC_ALL=C ls _quick_start_python
   README.md
   README_zh.md
   machine.py

The generated directory includes runtime code and generated README files. The
full :doc:`/tutorials/generation/index` tutorial covers ``python``, ``c``,
``c_poll``, ``cpp``, and ``cpp_poll``.

Use ``-t/--template-dir`` only when you are intentionally rendering with a
custom template directory.

5. Generate a diagram source
----------------------------

For a stable, versionable diagram source file, use ``plantuml``:

.. code-block:: console

   $ pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml
   $ cat traffic_light.puml
   @startuml
   ...
   @enduml

When your environment has a PlantUML renderer available, ``visualize`` can
render a final ``png`` / ``svg`` / ``pdf`` file directly:

.. code-block:: bash

   pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open

The full visualization option matrix remains in
:doc:`/tutorials/visualization/index`.

What to expect
--------------

The commands above are intentionally independent from any external PlantUML
renderer. A successful quick-start run prints the output shown in each step above.
