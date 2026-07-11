Your First Bounded Model Check
================================

This tutorial takes one small FCSTM model through a complete bounded model
check.  You will run one ``reach`` query, recognize the human report, save the
same result as JSON, and confirm that the SAT witness was replayed by the
runtime.  Run every command from the repository root.

Bounded model checking (BMC) searches executions only up to the bound written
in the query.  Success here proves that the example has a replayable execution
within that bound; it is not an unbounded proof about every possible execution.

Prerequisite
------------

The command must list the BMC subcommand:

.. code-block:: bash

   python -m pyfcstm bmc --help

The first line is ``Usage: python -m pyfcstm bmc [OPTIONS]``.  If the installed
``pyfcstm`` script is current, you may use it instead of ``python -m pyfcstm``.

1. Read the model
-----------------

The tutorial model has one root state and no variables or events:

.. literalinclude:: first_check.fcstm
   :language: text
   :caption: ``docs/source/tutorials/bmc/first_check.fcstm``

There is deliberately nothing to configure.  On cold entry, the state machine
can enter ``Door``.

2. Read the property
--------------------

The query asks whether some execution reaches ``Door`` within one macro step:

.. literalinclude:: reach_door.fbmcq
   :language: text
   :caption: ``docs/source/tutorials/bmc/reach_door.fbmcq``

``reach`` is a **witness-polarity** property.  SAT therefore means that BMC
found the requested execution.  This is different from safety properties such
as ``forbid``: SAT for those means that BMC found a counterexample.

3. Run the first check
----------------------

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/tutorials/bmc/first_check.fcstm \
       -q docs/source/tutorials/bmc/reach_door.fbmcq

The checked report is verdict-first.  Timing is intentionally replaced with
``...`` because it varies by machine:

.. code-block:: text

   BMC reach <= 1: PROPERTY HOLDS
   A satisfying execution was found within the bound.

   Solver: SAT in ... ms
   Replay: verified (2 frames, 1 step).

   Trace
     0: init -> Door [initial]

The process exits with ``0``.  The first line is the property verdict; the
``Solver`` line is supporting evidence, not a conclusion that users must
translate through polarity themselves.  In an interactive terminal the CLI
colors a holding verdict green and the diagnostic labels cyan.  Redirected,
JSON, and file output remain free of ANSI escapes.

SAT reports are not emitted immediately after Z3 returns.  The CLI first
decodes the symbolic witness and replays it with ``SimulationRuntime``.  Only a
successful replay produces the ``verified`` signal.  Replay increases trust that
the trace matches current runtime semantics, but it is not a second formal
proof and the CLI does not install user abstract handlers.

4. Save machine-readable output
-------------------------------

Use ``--json`` for scripts and ``-o`` to write the completed report atomically:

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/tutorials/bmc/first_check.fcstm \
       -q docs/source/tutorials/bmc/reach_door.fbmcq \
       --json -o /tmp/first-bmc.json

When ``-o`` is present, stdout is empty.  The existing parent directory must
already exist.  Inspect only stable fields:

.. code-block:: bash

   FIRST_BMC_JSON=/tmp/first-bmc.json python - <<'PY'
   import json
   import os
   from pathlib import Path

   payload = json.loads(
       Path(os.environ["FIRST_BMC_JSON"]).read_text(encoding="utf-8")
   )
   print(payload["schema_version"])
   print(payload["result"]["outcome"])
   print(payload["replay"]["ok"])
   print(payload["exit_code"])
   PY

Expected output:

.. code-block:: text

   bmc-cli/v1
   witness_found
   True
   0

Do not snapshot ``elapsed_ms`` in CI.  It is live timing, while
``schema_version``, ``result.outcome``, ``replay.ok`` and ``exit_code`` express
the stable contract used here.

5. Re-run the checked demo
--------------------------

The standalone demo changes into its own directory, so it does not depend on
the Python test tree or another documentation fixture:

.. code-block:: bash

   bash docs/source/tutorials/bmc/first_check.demo.sh

It writes ``docs/source/tutorials/bmc/first_check.result.json`` and prints the
same four-field JSON summary.  Remove that generated result after experimenting;
the model, query, and demo script are the source fixtures.

Where to go next
----------------

Use :doc:`../../how_to/bmc/index` for task recipes covering all seven property
kinds, initial-state control, assumptions, call predicates, CI, timeouts, and
troubleshooting.  Use :doc:`../../reference/bmc_query/index` for the complete
``.fbmcq`` language and :doc:`../../reference/bmc_results/index` for every CLI,
JSON, exit-status, witness, and replay field.  The mathematical meaning of
property polarity and bounded horizons is developed in
:doc:`../../explanations/bmc_properties/index`.
