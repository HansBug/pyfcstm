First inspect report
====================

``pyfcstm inspect`` answers "what did this FCSTM model become?" It builds the
same state-machine model used by simulation, visualization, and code
generation, then reports structure, metrics, derived graphs, combo provenance,
and diagnostics.

This tutorial keeps one diagnostic-heavy first run. For CI and LLM tasks, see
:doc:`/how_to/inspect/index`. For report fields and diagnostic codes, see
:doc:`/reference/inspect_report/index` and
:doc:`/reference/diagnostics_codes/index`.

Use a diagnostic-heavy example
------------------------------

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm
   :caption: inspect_diagnostics.fcstm

Run human output first
----------------------

Human output is the default:

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm

The report starts with model identity and metrics, then prints diagnostics with
source context, provenance, suggested actions, and do-not notes:

.. literalinclude:: inspect_human.demo.sh.txt
   :language: text
   :caption: Human inspect output excerpt
   :lines: 1-40

Export structured JSON
----------------------

Use ``--format json`` when a script needs the full report:

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o report.json

The generated demo summarizes the shape:

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: JSON report summary
   :lines: 1-12

Remember the invalid-input boundary
-----------------------------------

Syntax errors and model-load failures are CLI failures. Even if you requested
``--format json``, inspect does not invent a successful ``diagnostics[]``
payload for input that could not be parsed or loaded:

.. literalinclude:: inspect_invalid.demo.sh.txt
   :language: text
   :caption: Invalid input boundary

Where to go next
----------------

* :doc:`/how_to/inspect/index` shows CI and LLM-oriented inspect tasks.
* :doc:`/reference/inspect_report/index` lists report fields and formats.
* :doc:`/reference/diagnostics_codes/index` lists common diagnostic codes.
* :doc:`/explanations/diagnostics/index` explains diagnostic boundaries.
