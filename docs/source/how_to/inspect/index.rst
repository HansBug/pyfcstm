.. _sec-how-to-inspect:

Inspect tasks
=============

Use this guide when you want to automate ``pyfcstm inspect`` or pass its output
to another tool.

Write a JSON report for CI
--------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

In CI, treat parse/model-load failures as command failures. Diagnostics on a
valid model can then be triaged by ``severity`` and ``code``.

Write an LLM repair report
--------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md
   pyfcstm inspect -i machine.fcstm --format llm-json -o machine.inspect.llm.json

A practical LLM loop is:

1. Run inspect and keep the report as evidence.
2. Ask for the smallest source edit that preserves intent.
3. Apply the edit.
4. Re-run inspect and any relevant tests.

The LLM report is guidance, not proof. It can carry heuristic design warnings,
deployment-profile warnings, and verify-backed results with different strengths.

Enable bounded verify checks
----------------------------

Static inspect is the default. Enable verify only when the job can afford it:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json --enable-verify \
     --max-complexity-tier smt_linear --smt-timeout-ms 1000 \
     -o machine.verify.inspect.json

Inspect deliberately rejects options that need a separately reviewed proof
budget, such as bounded-model checking depth policies.

Keep target risk wording precise
--------------------------------

Numeric deployment warnings that mention fixed-width generated integer storage
are C/C++ target-profile warnings. They apply to ``c``, ``c_poll``, ``cpp``, and
``cpp_poll`` deployment review. They are not proof that Python generated
runtimes have the same fixed-width integer carrying risk.
