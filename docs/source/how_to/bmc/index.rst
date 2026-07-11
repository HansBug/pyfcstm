BMC Task Recipes
================

Use these recipes after completing :doc:`../../tutorials/bmc/index`.  Every
task uses the independent fixtures in this directory and can be run from the
repository root.  The model is:

.. literalinclude:: bmc_tasks.fcstm
   :language: text
   :caption: ``docs/source/how_to/bmc/bmc_tasks.fcstm``

It has one persistent variable, one event, one abstract ``during`` action, and
one event-driven transition.  These are enough to exercise the public BMC CLI
without importing resources from ``test/``.

How to read the task cards
--------------------------

Each card states its input, command, expected output, file side effect, first
failure boundary, and reference destination.  Solver verdicts are reports,
including expected nonzero verdicts.  Controlled input errors instead write a
short message to stderr and do not create a partial report.

1. Choose among the seven property kinds
-----------------------------------------

**Input.** ``bmc_tasks.fcstm`` and the seven query fixtures named after
``reach``, ``forbid``, ``invariant``, ``must_reach``, ``exists_always``,
``response``, and ``cover``.

**Command.** Run the checked demo and keep its first seven summaries:

.. code-block:: bash

   bash docs/source/how_to/bmc/bmc_tasks.demo.sh | sed -n '1,7p'

**Expected output.**

.. code-block:: text

   reach sat witness_found exit=0
   forbid sat property_violated exit=1
   invariant unsat property_satisfied exit=0
   must_reach unsat property_satisfied exit=0
   exists_always sat witness_found exit=0
   response unsat property_satisfied exit=0
   cover sat witness_found exit=0

The first, fifth, and seventh kinds have witness polarity; the other four have
counterexample polarity.  SAT therefore does not have one universal meaning.

**File side effect.** The demo uses ``.bmc_tasks.tmp`` beside itself and removes
it on exit.

**Failure boundary.** ``cover`` accepts only a naked, known, coverable
``case("...")`` label.  A transition edit can change that label.  A bounded
success or failure says nothing beyond the selected bound.

**Reference.** See :doc:`../../reference/bmc_query/index` for exact property
forms and :doc:`../../explanations/bmc_properties/index` for their objectives.

2. Set a state and replace selected initializers
------------------------------------------------

**Input.** ``init_havoc_where.fbmcq``, which starts at ``Root.Idle``, removes
only ``x`` from the initializer constraints, and constrains frame zero to
``x == 7``.

.. literalinclude:: init_havoc_where.fbmcq
   :language: text

**Command.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/init_havoc_where.fbmcq --json

**Expected output.** JSON contains ``"kind": "reach"``,
``"outcome": "witness_found"``, and a witness frame whose ``vars.x`` is ``7``;
the exit status is ``0``.

**File side effect.** None; the report goes to stdout.

**Failure boundary.** ``where`` constrains initialization; it does not override
an initializer.  Without ``havoc { x }``, this model's ``x = 0`` and
``where x == 7`` make the trace formula UNSAT.  ``havoc *`` removes every
persistent initializer, so prefer a named set when possible.

**Reference.** See :doc:`../../reference/bmc_query/index` for ``cold``,
``state(...)``, ``terminated``, ``havoc``, and ``where`` legality.

3. Constrain frames and event inputs
------------------------------------

**Input.** ``assumptions.fbmcq`` constrains ``x`` on every frame, disables
``Root.Go`` at step zero, and requests at-most-one cardinality for the event
set.

.. literalinclude:: assumptions.fbmcq
   :language: text

**Command.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/assumptions.fbmcq --json \
       -o /tmp/bmc-assumptions.json

**Expected output.** The payload reports ``invariant``, ``unsat``,
``property_satisfied``, and exit ``0``.  ``witness`` and ``replay`` are null
because no counterexample exists under these assumptions.

**File side effect.** ``/tmp/bmc-assumptions.json`` is atomically created or
replaced.

**Failure boundary.** Assumptions restrict the searched environment and can
make an otherwise possible behavior disappear.  Event paths are fully
qualified; an unknown path is a binding error, not an UNSAT verdict.

**Reference.** See :doc:`../../reference/bmc_query/index` for ``always``,
``at``, event selectors, ranges, and cardinality.

4. Match abstract calls and snapshots
-------------------------------------

**Input.** ``calls.fbmcq`` selects the ``Root.Idle.Tick`` call at step zero,
requires its runtime role, checks the call-time ``x`` snapshot, and counts it.

.. literalinclude:: calls.fbmcq
   :language: text

**Command.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/calls.fbmcq --json \
       -o /tmp/bmc-calls.json

**Expected output.** Exit ``0`` with ``outcome`` equal to ``witness_found``.
The first witness step contains one ``abstract_calls`` record with
``action_name`` ``Root.Idle.Tick``, ``role`` ``leaf_during``, and ``snapshot.x``
equal to ``0``.

**File side effect.** ``/tmp/bmc-calls.json`` is atomically created or replaced.

**Failure boundary.** A call ``where`` expression sees the captured call-time
variables; it cannot use frame atoms such as ``active()`` or nested
``call_count()``.  The CLI replay records abstract calls but installs no user
handler that could mutate runtime state.

**Reference.** See :doc:`../../reference/bmc_query/index` for every call filter
key and allowed ``where`` expression.

5. Audit a human witness and replay
-----------------------------------

**Input.** The model and ``calls.fbmcq``.

**Command.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/calls.fbmcq

**Expected output.** The first line is
``BMC reach <= 3: PROPERTY HOLDS``.  ``Solver: SAT`` follows as diagnostic
evidence, ``Replay: verified`` reports the runtime trust gate, and the compact
``Trace`` lists source, target, selected case, events, and calls.  The process
exits ``0``.  Use ``--color always`` to force ANSI terminal decoration or
``--color never`` for a stable plain-text transcript.

**File side effect.** None; the human summary goes to stdout.  Use ``--json``
for the complete witness and replay records.

**Failure boundary.** A SAT decode or replay exception is an internal failure:
it retains a traceback and exit ``1`` instead of emitting a partial report.  A
successfully constructed replay mismatch emits the complete report and exit
``4``.  Replay checks runtime alignment; it is not an unbounded proof.

**Reference.** See :doc:`../../reference/bmc_results/index` for report sections,
witness columns, replay mismatches, and exit precedence.

6. Gate CI with JSON and exit status
------------------------------------

**Input.** ``forbid.fbmcq`` intentionally finds a forbidden-state
counterexample, so this card demonstrates a valid report with nonzero exit.

**Command.**

.. code-block:: bash

   set +e
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/forbid.fbmcq --json \
       -o /tmp/bmc-ci.json
   rc=$?
   set -e
   BMC_RC="$rc" BMC_JSON=/tmp/bmc-ci.json python - <<'PY'
   import json
   import os
   from pathlib import Path

   payload = json.loads(Path(os.environ["BMC_JSON"]).read_text(encoding="utf-8"))
   assert payload["exit_code"] == int(os.environ["BMC_RC"])
   print(payload["result"]["outcome"], payload["exit_code"])
   PY

**Expected output.** ``property_violated 1``.  CI should fail or allow this
according to project policy, but it must not confuse the report with a CLI
input error.

**File side effect.** ``/tmp/bmc-ci.json`` is created even though the verdict
exit is ``1``.

**Failure boundary.** Exit ``0`` means a satisfied property or positive witness;
``1`` also covers controlled errors, distinguishable because those have stderr
and no report; ``2`` is Click usage; ``3`` is inconclusive; ``4`` is a
structured replay mismatch.  Always inspect JSON when a report exists.

**Reference.** See :doc:`../../reference/bmc_results/index` for the full branch
matrix and stable JSON schema.

7. Write a completed report atomically
--------------------------------------

**Input.** Any valid single query; this example uses ``invariant.fbmcq`` and an
already existing parent directory.

**Command.**

.. code-block:: bash

   mkdir -p /tmp/pyfcstm-bmc
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/invariant.fbmcq \
       --json -o /tmp/pyfcstm-bmc/result.json
   test -s /tmp/pyfcstm-bmc/result.json

**Expected output.** No stdout; ``test`` exits ``0`` and the file contains
``"exit_code": 0``.

**File side effect.** The target is atomically replaced using a same-directory
temporary file.

**Failure boundary.** Parent directories are not created by ``pyfcstm bmc``.
If reading, compiling, solving internally, or writing fails before a complete
payload exists, the command must not claim a successful output file.

**Reference.** See :doc:`../../reference/bmc_results/index` for overwrite,
stdout, stderr, and UTF-8 rules.

8. Enforce a maximum bound policy
---------------------------------

**Input.** ``reach_bound_2.fbmcq`` requests bound 2 while the command policy
allows at most 1.

**Command.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/reach_bound_2.fbmcq \
       --max-bound 1

**Expected output.** A concise ``Failed to compile BMC query`` message on
stderr containing ``query_bound=2`` and ``max_bound=1``; exit ``1``.

**File side effect.** None.  With ``-o``, no report would be created or modified
because policy rejection happens before report construction.

**Failure boundary.** ``--max-bound`` is a pre-construction policy gate, not a
request to silently clamp or truncate the query.  Values below 1 are Click
usage errors with exit ``2``.

**Reference.** See :doc:`../../reference/bmc_results/index` for CLI option and
error classification details.

9. Apply a per-check solver timeout
-----------------------------------

**Input.** A valid query.  The small fixture may finish before the one
millisecond timeout; the task verifies propagation rather than forcing a
machine-dependent timeout.

**Command.**

.. code-block:: bash

   set +e
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/reach_bound_2.fbmcq \
       --timeout-ms 1 --json -o /tmp/bmc-timeout.json
   rc=$?
   set -e
   BMC_JSON=/tmp/bmc-timeout.json python - <<'PY'
   import json
   import os
   from pathlib import Path

   payload = json.loads(Path(os.environ["BMC_JSON"]).read_text(encoding="utf-8"))
   print("timeout_ms:", payload["result"]["timeout_ms"])
   print("outcome:", payload["result"]["outcome"])
   PY

**Expected output.** ``timeout_ms: 1`` followed by either a decisive outcome or
``outcome: timeout``.  A real timeout exits ``3``; a fast decisive solve keeps
its ordinary exit.

**File side effect.** ``/tmp/bmc-timeout.json`` contains the completed verdict.

**Failure boundary.** The value applies independently to each Z3 ``check()``;
it is not a wall-clock budget for parsing, expansion, formula construction, or
the whole CLI.  ``response`` may execute a second incomplete-horizon check,
also with the full timeout.

**Reference.** See :doc:`../../reference/bmc_results/index` for timeout fields
and :doc:`../../explanations/bmc_solving/index` for the solve sequence.

10. Distinguish response violations from an incomplete horizon
--------------------------------------------------------------

**Input.** ``response_missing.fbmcq`` has a defined trigger and no response;
``response_trigger_undefined.fbmcq`` divides by ``x == 0`` in its trigger;
``response_incomplete.fbmcq`` has bound 1 but asks for a response within 2
successor frames.

.. literalinclude:: response_incomplete.fbmcq
   :language: text

**Command.**

.. code-block:: bash

   set +e
   for name in response_missing response_trigger_undefined; do
       python -m pyfcstm bmc \
           -i docs/source/how_to/bmc/bmc_tasks.fcstm \
           -q "docs/source/how_to/bmc/$name.fbmcq" --json \
           -o "/tmp/$name.json"
       echo "$name exit=$?"
   done
   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/response_incomplete.fbmcq --json \
       -o /tmp/bmc-incomplete.json
   echo "response_incomplete exit=$?"
   set -e

**Expected output.** The first two lines end in ``exit=1``; both JSON reports
have ``status`` ``sat`` and ``outcome`` ``property_violated``.  The last line is
``response_incomplete exit=3``.  Its JSON has primary ``status`` ``unsat``, but
``outcome`` ``incomplete``, ``incomplete`` true, and ``incomplete_status``
``sat``; witness and replay are null.

**File side effect.** Three complete JSON reports are created under ``/tmp``.

**Failure boundary.** Current outcome and witness schemas do not classify
whether a decisive response counterexample came from an undefined trigger or
from a defined trigger with no response; inspect the query and trace manually.
Do not interpret primary UNSAT as satisfied until the suffix is closed.  Raise
the query bound for horizon coverage; timeout does not repair a short horizon.

**Reference.** See :doc:`../../explanations/bmc_properties/index` for strict
successor windows and :doc:`../../reference/bmc_results/index` for incomplete
fields.

11. Diagnose parse, binding, and unsupported input
--------------------------------------------------

**Input.** ``invalid_state.fbmcq`` is syntactically valid but names the missing
state ``Root.Missing``.

**Command.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i docs/source/how_to/bmc/bmc_tasks.fcstm \
       -q docs/source/how_to/bmc/invalid_state.fbmcq

**Expected output.** stderr starts with ``Failed to compile BMC query`` and
identifies ``Root.Missing``; exit ``1``.  stdout is empty.

**File side effect.** None.  Adding ``-o /tmp/invalid.json`` still must not
create a partial payload.

**Failure boundary.** A malformed ``.fbmcq`` fails during parsing; an unknown
model path fails during binding; a parsed but unsupported expression reports
an unsupported query.  These are controlled user-input errors.  A traceback
with an internal BMC sentinel is an implementation failure and should be
reported as a bug rather than rewritten until it becomes UNSAT.

**Reference.** See :doc:`../../reference/bmc_query/index` for legal and illegal
forms and :doc:`../../reference/bmc_results/index` for error streams.

12. Re-run the primary fixture matrix after an upgrade
------------------------------------------------------

**Input.** The model, the query fixtures, and ``bmc_tasks.demo.sh`` in this
directory.  The script owns its expected exit matrix.

**Command.**

.. code-block:: bash

   bash docs/source/how_to/bmc/bmc_tasks.demo.sh

**Expected output.** Eleven verdict summaries ending with
``response unsat incomplete exit=3``, followed by
``invalid_state controlled_error exit=1``.  The script itself exits ``0`` only
when every nested command matches the frozen expectation.

**File side effect.** Temporary JSON reports are created under
``docs/source/how_to/bmc/.bmc_tasks.tmp`` and removed by the exit trap.

**Failure boundary.** Live ``elapsed_ms`` values are never compared.  If the
script fails, run the named query directly in human mode, then compare its
property polarity, outcome, replay status, and process exit before changing an
expectation.

**Reference.** See :doc:`../../reference/bmc_results/index` for stable versus
non-deterministic fields.  The script is a documentation smoke check, not a
replacement for the repository BMC unit tests.
