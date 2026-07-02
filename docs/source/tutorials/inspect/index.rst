Inspect and Diagnostics
=======================

This page is a temporary entry point for the dedicated inspect tutorial. A
later documentation update will expand it into a complete guide.

For now, use ``pyfcstm inspect`` to emit a structured JSON report:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm -o machine.inspect.json

The report includes model structure, metrics, derived graphs, and diagnostics.
Diagnostics are intended to be precise enough for humans and LLM-assisted repair
workflows, but inspect is not a replacement for simulation, target hardware
testing, or complete formal verification.

Optional verify-backed checks are enabled explicitly with ``--enable-verify``;
they are not part of the default quick path.
