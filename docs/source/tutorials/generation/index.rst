First generated runtime
=======================

This tutorial shows the shortest generated-runtime path with a packaged
built-in template. It intentionally uses ``--template`` rather than a repository
``templates/`` path.

Use :doc:`/how_to/generation/index` when you need task recipes for all built-in
templates, native smoke builds, or generated README entry points. Use
:doc:`/reference/builtin_templates/index` when you need a compact template fact
table.

Example model
-------------

All examples use this small event-driven machine:

.. literalinclude:: simple_machine.fcstm
   :language: fcstm

Generate Python code
--------------------

Render the packaged Python template:

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

The output directory contains ``machine.py`` plus generated README files. The
runtime itself is self-contained; users of the generated output do not import
``pyfcstm`` at runtime.

Run the generated class
-----------------------

A minimal consumer imports the generated class, creates a machine, and calls
``cycle(...)``:

.. literalinclude:: python_runtime.demo.py
   :language: python
   :lines: 47-60

The demo output proves the generated public API is usable:

.. literalinclude:: python_runtime.demo.py.txt
   :language: text

What this tutorial leaves out
-----------------------------

The native templates and polling templates need additional integration context.
Continue to :doc:`/how_to/generation/index` for:

* generating ``python``, ``c``, ``c_poll``, ``cpp``, and ``cpp_poll`` outputs;
* compiling native outputs through the generated directory guidance;
* finding generated README files and extension points;
* choosing the right template family for your application.
