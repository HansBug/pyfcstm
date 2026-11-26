First generated runtime
=======================

This tutorial is the shortest path from one FCSTM model to one usable generated
runtime. It uses the packaged Python built-in template through ``--template``;
it does not point at the repository ``templates/`` source tree.

Use :doc:`/how_to/generation/index` when you need recipes for all built-in
templates, native smoke checks, generated README entry points, or failure
handling. Use :doc:`/reference/builtin_templates/index` and
:doc:`/reference/template_config/index` when you need exact facts.

What you will run
-----------------

The input model has three leaf states and three event-triggered transitions:

.. literalinclude:: simple_machine.fcstm
   :language: fcstm

Generate Python code
--------------------

Render the packaged Python template into a fresh output directory:

.. code-block:: console

   $ pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

The important pieces of the command are:

* ``--template python`` selects the installed built-in template named
  ``python``.
* ``-o generated/python`` chooses the generated output directory.
* ``--clear`` makes the tutorial repeatable by deleting the previous output
  directory contents before rendering.

A successful run writes machine-specific files. For this model the output has
three top-level files:

.. code-block:: console

   $ LC_ALL=C ls generated/python
   README.md
   README_zh.md
   machine.py

``machine.py`` is the generated runtime. The README files are generated from
the same model and are part of the output contract: read them when integrating
that particular generated machine.

Run the generated class
-----------------------

A minimal consumer imports the generated class, constructs it, performs the
initial cycle, and then submits event paths:

.. testcode::

   import sys

   sys.path.insert(0, "generated/python")
   from machine import SimpleMachineMachine

   machine = SimpleMachineMachine()
   machine.cycle()
   print(".".join(machine.current_state_path), machine.vars["counter"])

   for event in [
       "SimpleMachine.Idle.Start",
       "SimpleMachine.Running.Stop",
       "SimpleMachine.Stopped.Reset",
   ]:
       machine.cycle(event)
       print(".".join(machine.current_state_path), machine.vars["counter"])

The script prints the state and ``counter`` value after the initial cycle and
after each event:

.. testoutput::

   SimpleMachine.Idle 0
   SimpleMachine.Running 0
   SimpleMachine.Stopped 1
   SimpleMachine.Idle 1

This proves only the first-success path: generation succeeded, the generated
Python file is importable, and a small event sequence runs. It is not a full
semantic-alignment proof for every FCSTM construct.

Where to go next
----------------

* Generate ``c``, ``c_poll``, ``cpp``, or ``cpp_poll`` outputs with
  :doc:`/how_to/generation/index`.
* Author a custom template directory with :doc:`/how_to/templates/index`.
* Understand the renderer pipeline with
  :doc:`/explanations/template_rendering/index`.
* Look up built-in template contracts in
  :doc:`/reference/builtin_templates/index`.
* Generate a runtime for a model with regions and read its position with
  ``configuration`` in :doc:`/tutorials/regions/index`.
