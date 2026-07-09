First inspect report
====================

This tutorial runs ``pyfcstm inspect`` on one small but diagnostic-heavy FCSTM
file. The goal is not to learn every report field; the goal is to see the three
main output styles and know where to go next.

Use a diagnostic-heavy example
------------------------------

The checked tutorial input is:

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm

It is valid DSL. The warnings are intentional teaching signals, not parser
failures.

Run human output first
----------------------

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/inspect_diagnostics.fcstm --color never

Expected excerpt:

.. code-block:: text

   FCSTM Inspect Report
   Root state: InspectDiagnostics
   Diagnostics:

The human renderer is for reading. It includes the diagnostic code, severity,
message, source excerpt when available, and selected structured ``refs``.

Export full JSON
----------------

Use full JSON when a script needs structural facts:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/inspect_diagnostics.fcstm --format json -o /tmp/inspect.json
   python - <<'PY'
   import json
   from pathlib import Path

   report = json.loads(Path('/tmp/inspect.json').read_text())
   print(report['root_state_path'])
   print(len(report['states']))
   print([item['code'] for item in report['diagnostics']])
   PY

This format is the complete ``ModelInspect`` contract. Its fields are described
in :doc:`../../reference/inspect_report/index`.

Export an LLM repair report
---------------------------

Use ``llm-json`` when a repair loop needs compact guidance rather than the full
structural inventory:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/inspect_diagnostics.fcstm --format llm-json -o /tmp/inspect.llm.json

The LLM report includes a repair protocol, source excerpts, ``refs``, registry
summaries, recommended actions, and ``do_not`` guidance. It is intentionally
smaller than full JSON.

Remember the invalid-input boundary
-----------------------------------

Inspect reports are produced after the file can be read, parsed, and converted
to a model. Missing files, syntax errors, and hard model-construction errors
such as duplicate state names are CLI failures, not successful reports with a
``diagnostics`` array. Some registry ``E_*`` codes therefore document a
controlled validation error shape rather than an inspect JSON entry. Try a
missing file to see that boundary:

.. code-block:: bash

   pyfcstm inspect -i docs/source/tutorials/inspect/does-not-exist.fcstm

When a diagnostic-code reference page marks an example as ``cli_error``, expect
the same non-zero command boundary and assert stderr/exit status instead of
``diagnostics[]``.

Next steps
----------

* Use :doc:`../../how_to/inspect/index` for CI, LLM, and verify-backed recipes.
* Use :doc:`../../explanations/diagnostics/index` to understand what inspect can and cannot prove.
* Use :doc:`../../reference/diagnostics_codes/index` when you have a specific diagnostic code.
