.. _sec-how-to-inspect:

Inspect tasks
=============

Use these recipes when you already know what you want inspect to do.

Write a JSON report for CI
--------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o inspect.json

A minimal CI gate usually parses the file and counts severities instead of
matching human messages:

.. code-block:: python

   import json
   from pathlib import Path

   report = json.loads(Path('inspect.json').read_text())
   errors = [item for item in report['diagnostics'] if item['severity'] == 'error']
   if errors:
       raise SystemExit('inspect reported blocking diagnostics')

Write an LLM repair report
--------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-json -o inspect.llm.json
   pyfcstm inspect -i machine.fcstm --format llm-md -o inspect.llm.md

Use the LLM formats when the consumer should see repair guidance, source
excerpts, and ``do_not`` rules. Use full JSON when the consumer needs all
states, transitions, metrics, and derived graphs.

Enable bounded verify checks
----------------------------

Default inspect is static. Add verify-backed diagnostics explicitly:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --enable-verify --format human --color never

Keep the policy bounded. ``bmc_search`` and ``k_unrollings`` labels are accepted
by Click only so inspect can reject them with a controlled policy error.

Control output files and colors
-------------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format human --color never
   pyfcstm inspect -i machine.fcstm --format json -o inspect.json
   pyfcstm inspect -i machine.fcstm --format llm-json -o repair.json

Color applies only to ``human``. Machine formats ignore ``--color``. If an
output suffix looks mismatched for the selected format, inspect can emit a
warning to stderr while still writing the requested file.

Handle invalid input and policy errors
--------------------------------------

These are CLI failures, not successful inspect reports:

.. list-table:: Failure boundary
   :header-rows: 1
   :widths: 32 68

   * - Failure
     - Meaning
   * - Missing or unreadable file
     - Inspect cannot read the input bytes.
   * - Decode failure
     - The input cannot be decoded by the supported encoding path.
   * - Grammar parse error
     - The text is not syntactically valid FCSTM DSL.
   * - Model validation error
     - The parsed DSL violates model-level contracts.
   * - Forbidden verify policy
     - The requested automatic verify policy is outside inspect's bounded envelope.

If you need machine-readable failure reporting for invalid input, wrap the CLI in
your own process-level error handling; do not expect a ``diagnostics`` array.

Keep target wording precise
---------------------------

Some warnings are target-profile warnings, not universal runtime failures. For
example, C-family integer range warnings apply to generated ``c``, ``c_poll``,
``cpp``, and ``cpp_poll`` deployment review. Do not describe them as Python
runtime overflow findings unless a Python-specific diagnostic says so.
