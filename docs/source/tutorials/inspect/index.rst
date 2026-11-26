First inspect report
====================

This tutorial runs ``pyfcstm inspect`` on one small but diagnostic-heavy FCSTM
file. The goal is not to learn every report field; the goal is to see the three
main output styles and know where to go next.

Use a diagnostic-heavy example
------------------------------

The checked tutorial input is below. Download
:download:`inspect_diagnostics.fcstm <inspect_diagnostics.fcstm>` into an empty directory and
run the commands there:

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm
   :linenos:

It is valid DSL. The warnings are intentional teaching signals, not parser
failures.

Run human output first
----------------------

.. code-block:: console

   $ pyfcstm inspect -i inspect_diagnostics.fcstm --color never
   [WARN] FCSTM Inspect Report: inspect_diagnostics.fcstm

   Summary
     status: warning
     root: InspectDemo
   ...
   [WARN] W_DURING_CONST_ASSIGN
     During action in 'InspectDemo.Active' assigns 'counter' to the same constant value every cycle.
     --> inspect_diagnostics.fcstm:12:13
   ...

The human renderer is for reading. It includes the diagnostic code, severity,
message, source excerpt when available, and selected structured ``refs``.

Export full JSON
----------------

Use full JSON when a script needs structural facts:

.. code-block:: console

   $ pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o inspect.json

.. testcode::

   import json
   from pathlib import Path

   report = json.loads(Path("inspect.json").read_text())
   print(report["root_state_path"])
   print(len(report["states"]))
   for item in report["diagnostics"]:
       print(item["span"]["line"], item["code"])

.. testoutput::

   InspectDemo
   6
   12 W_DURING_CONST_ASSIGN
   19 W_COMBO_DUPLICATE_EVENT
   20 W_COMBO_GUARD_PREFIX_IMPLIED
   15 W_LEAF_NO_OUTGOING_TRANSITION
   16 W_LEAF_NO_OUTGOING_TRANSITION
   1 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   2 W_UNWRITTEN_READ_VAR
   3 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   4 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   5 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   20 W_GUARD_VARS_NEVER_CHANGE
   20 W_GUARD_VARS_NEVER_CHANGE
   4 W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE

Each output line after the first two is one diagnostic: the line of the model
where it points, then its code. Compare the numbers with the numbered model
above: line 12 is the constant ``during`` assignment, line 19 the repeated
``Confirm`` term, line 20 the guard terms of the combo trigger, lines 15
and 16 the two leaves without an outgoing transition, lines 1 to 5 the
variable declarations, and line 4 the literal that is too large for a C target.

This format is the complete ``ModelInspect`` contract. Its fields are described
in :doc:`../../reference/inspect_report/index`.

Export an LLM repair report
---------------------------

Use ``llm-json`` when a repair loop needs compact guidance rather than the full
structural inventory:

.. code-block:: console

   $ pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-json -o inspect.llm.json

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

.. code-block:: console

   $ pyfcstm inspect -i does-not-exist.fcstm
   Input DSL file not found: does-not-exist.fcstm
   $ echo $?
   1

When a diagnostic-code reference page marks an example as ``cli_error``, expect
the same non-zero command boundary and assert stderr/exit status instead of
``diagnostics[]``.

Next steps
----------

* Use :doc:`../../how_to/inspect/index` for CI, LLM, and verify-backed recipes.
* Use :doc:`../../explanations/diagnostics/index` to understand what inspect can and cannot prove.
* Use :doc:`../../reference/diagnostics_codes/index` when you have a specific diagnostic code.
* Use :doc:`../../tutorials/regions/index` to see the region order diagnostic ``I_REGION_BACKWARD_READ`` on a model with regions.
