.. _sec-how-to-generation:

Generation tasks
================

Use this guide when you want to generate and smoke-check built-in template
outputs. For compact template facts, see :doc:`/reference/builtin_templates/index`.

Prepare an input model
----------------------

The checked-in examples use this model:

.. literalinclude:: ../../tutorials/generation/simple_machine.fcstm
   :language: fcstm

Generate Python output and run it
---------------------------------

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

A minimal Python consumer imports the generated class from ``machine.py``:

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py
   :language: python
   :lines: 47-60

Expected smoke output:

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py.txt
   :language: text

Generate C or C++ output
------------------------

Use the packaged template names:

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template c -o generated/c --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp -o generated/cpp --clear

The generated directory contains ``README.md`` and ``README_zh.md``. Treat those
README files as the concrete integration guide for the generated machine,
including CMake skeletons and no-heap profile notes.

The docs native smoke script proves the public entry points for all native
families when ``cc``, ``c++``, and ``cmake`` are available:

.. literalinclude:: ../../tutorials/generation/native_runtime.demo.sh.txt
   :language: text
   :lines: 1-43

Generate polling outputs
------------------------

Polling templates move event detection into callbacks installed by the
integration layer:

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template c_poll -o generated/c_poll --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp_poll -o generated/cpp_poll --clear

Use ``c_poll`` when C integration code should install an ``EventChecks`` table
and let the runtime call event probes during ``cycle``. Use ``cpp_poll`` when
C++ application code should enter through ``machine.hpp`` and wrapper methods
while still installing wrapper-level ``EventChecks``.

Find generated README and extension points
------------------------------------------

Every built-in template writes generated README files next to the generated
runtime. Before integrating a generated machine into a real control loop, read
those files for:

* public entry points and hook names;
* event-check or event-id discipline;
* hot-start and lifecycle notes;
* target-language build guidance.

Do not use ``-t`` for built-in templates
----------------------------------------

Use ``-t`` / ``--template-dir`` only when you intentionally provide a custom
template directory. Built-in templates should use ``--template`` so the packaged
assets are extracted through pyfcstm's template system.
