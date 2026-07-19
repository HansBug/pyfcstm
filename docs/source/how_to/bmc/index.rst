BMC Task Recipes
================

Use these recipes after completing :doc:`../../tutorials/bmc/index`.  Start in
an empty working directory and :download:`download the task model
<bmc_tasks.fcstm>` there.  Save each task's short FBMCQ block under the filename
shown by its command, then run that command from the same directory.  The model
is small on purpose:

.. literalinclude:: bmc_tasks.fcstm
   :language: text
   :caption: ``bmc_tasks.fcstm``

It has one persistent variable, one event, one abstract ``during`` action, and
one event-driven transition.  The examples below show the direct CLI command
first, then the complete short ``.fbmcq`` text to save, then the explanation,
expected output, and failure boundary.  A block that compares alternatives
labels each alternative as a separate file.

How to choose a property kind
-----------------------------

SAT has different meaning for witness properties and counterexample
properties.  Pick the query kind from the user question first, then read the
solver status through that polarity.

.. list-table:: BMC property selection guide
   :header-rows: 1
   :widths: 16 30 22 22 28

   * - Kind
     - User intent
     - Quantification
     - SAT meaning
     - Use when
   * - ``reach``
     - Find at least one bounded execution where a predicate becomes true.
     - Existential over traces and frames.
     - A witness was found; property holds for the search goal.
     - You want a concrete path to a state, value, call, or event condition.
   * - ``forbid``
     - Reject any bounded execution that reaches a bad predicate.
     - Universal safety check encoded as counterexample search.
     - A counterexample was found; property is violated.
     - You know the unsafe condition and want CI to fail when it is reachable.
   * - ``invariant``
     - Require a predicate on every searched frame.
     - Universal over frames in every bounded trace.
     - A counterexample frame was found; property is violated.
     - You need a bounded safety condition, such as ``x >= 0`` always.
   * - ``must_reach``
     - Require every bounded execution to reach a predicate.
     - Universal over traces, existential over frames per trace.
     - A trace that never reaches the predicate was found; property is violated.
     - You need guaranteed bounded progress rather than one successful example.
   * - ``exists_always``
     - Find one execution where a predicate stays true for the whole bound.
     - Existential over traces, universal over frames on that trace.
     - A witness trace was found; property holds for the search goal.
     - You want to prove a stable scenario is possible, not mandatory.
   * - ``response``
     - Check that every trigger is followed by a response within a window.
     - Universal over trigger steps and bounded successor-frame windows.
     - A violating trigger was found; property is violated.
     - You need request/acknowledge, command/effect, or alarm/clear behavior.
   * - ``cover``
     - Hit a named transition case label.
     - Existential over traces and case labels.
     - A witness hit the case label.
     - You need coverage for a specific generated transition branch.

How to handle inconclusive outcomes
-----------------------------------

Use this table when the CLI exits ``3`` or when a JSON report has an outcome
that is neither ``property_satisfied`` nor ``property_violated``.

.. list-table:: Timeout, unknown, and incomplete handling
   :header-rows: 1
   :widths: 18 24 30 30

   * - Outcome
     - Where it appears
     - Meaning
     - First response
   * - ``timeout``
     - ``result.status`` and ``result.outcome`` can both be ``timeout``.
     - Z3 did not finish a single ``check()`` within ``--timeout-ms``.
     - Raise ``--timeout-ms``, simplify assumptions, or reduce the bound; do not treat it as safe.
   * - ``unknown``
     - ``result.status`` may be ``unknown`` when the backend cannot decide.
     - The solver returned an indeterminate answer that is not SAT or UNSAT.
     - Inspect diagnostics, simplify the query, or lower the bound; do not use it as proof.
   * - ``incomplete``
     - ``result.outcome`` is ``incomplete`` and ``result.incomplete`` is true.
     - The primary objective was UNSAT, but the separate response-horizon check
       was SAT, ``unknown``, ``timeout``, or not run.
     - Inspect ``result.incomplete_status``.  Increase the bound for SAT;
       diagnose the solver or timeout for ``unknown``/``timeout``.

How to read the task cards
--------------------------

Each task card includes a direct CLI command, the relevant query snippet, a
short explanation, expected output, side effects, failure boundary, and a link
to the reference page for exhaustive syntax or result facts.  Solver verdicts
are reports, including expected nonzero verdicts.  Controlled input errors write
a short message to stderr and do not create a partial report.

1. Run the chosen property kind
-------------------------------

**CLI.** Replace ``reach.fbmcq`` with the query file for the property you chose.

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q reach.fbmcq --json

**FBMCQ.** These are seven separate query files, not seven ``check`` clauses in
one file.  Every file starts with ``init state("Root.Idle");`` and contains
exactly one row from this table:

.. list-table:: One ``check`` clause per property file
   :header-rows: 1
   :widths: 19 81

   * - File
     - Clause after the common ``init`` line
   * - ``reach.fbmcq``
     - ``check reach <= 1: active("Root.Idle");``
   * - ``forbid.fbmcq``
     - ``check forbid <= 1: active("Root.Done");``
   * - ``invariant.fbmcq``
     - ``check invariant <= 1: x == 0;``
   * - ``must_reach.fbmcq``
     - ``check must_reach <= 1: active("Root.Idle");``
   * - ``exists_always.fbmcq``
     - ``check exists_always <= 1: x == 0;``
   * - ``response.fbmcq``
     - ``check response <= 1: trigger false -> within 1 active("Root.Done");``
   * - ``cover.fbmcq``
     - ``check cover <= 1: case("Root.Idle::transition::Root.Done::0");``

**What it does.** The command asks one bounded question about the model.  The
query kind controls whether SAT means a positive witness or a counterexample.
The shared hot-start line makes frame zero ``Root.Idle``; it is required for
the bound-one ``forbid`` and ``cover`` results shown below.

**Expected output.** For the direct ``reach`` command, JSON contains
``"kind": "reach"``, ``"status": "sat"``, ``"outcome": "witness_found"``,
and ``"exit_code": 0``.  The verified fixture matrix is:

.. code-block:: text

   reach sat witness_found exit=0
   forbid sat property_violated exit=1
   invariant unsat property_satisfied exit=0
   must_reach unsat property_satisfied exit=0
   exists_always sat witness_found exit=0
   response unsat property_satisfied exit=0
   cover sat witness_found exit=0

**File side effect.** None unless you add ``-o``.

**Failure boundary.** ``cover`` accepts only a naked, known, coverable
``case("...")`` label.  A bounded result says nothing beyond the selected
bound.

**Reference.** See :doc:`../../reference/bmc_query/index` for exact property
forms and :doc:`../../explanations/bmc_properties/index` for their objectives.

2. Set a state and replace selected initializers
------------------------------------------------

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q init_havoc_where.fbmcq --json

**FBMCQ.**

.. code-block:: text

   init state("Root.Idle") havoc { x } where x == 7;
   check reach <= 1: x == 7;

**What it does.** The query starts from ``Root.Idle``, removes only ``x`` from
the initializer constraints, and constrains frame zero to ``x == 7``.

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

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q assumptions.fbmcq --json \
       -o /tmp/bmc-assumptions.json

**FBMCQ.**

.. code-block:: text

   init state("Root.Idle");
   assume always: x == 0;
   assume event("Root.Go", 0) == false;
   assume events cardinality at_most_one {"Root.Go"};
   check invariant <= 1: x == 0;

**What it does.** The assumptions constrain ``x`` on every frame, disable
``Root.Go`` at step zero, and require at most one event from the selected event
set.

**Expected output.** The payload reports ``invariant``, ``unsat``,
``property_satisfied``, and exit ``0``.  ``witness`` and ``replay`` are null
because no counterexample exists under these assumptions.

**File side effect.** ``/tmp/bmc-assumptions.json`` is atomically created or
replaced.

**Failure boundary.** Assumptions restrict the searched environment and can make
an otherwise possible behavior disappear.  Event paths are fully qualified; an
unknown path is a binding error, not an UNSAT verdict.

**Reference.** See :doc:`../../reference/bmc_query/index` for ``always``,
``at``, event selectors, ranges, and cardinality.

4. Match abstract calls and snapshots
-------------------------------------

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q calls.fbmcq --json \
       -o /tmp/bmc-calls.json

**FBMCQ.**

.. code-block:: text

   init state("Root.Idle");
   check reach <= 1:
       called("Root.Idle.Tick", step=0, role="leaf_during", where x == 0)
       && call_count("Root.Idle.Tick", step=*) == 1;

**What it does.** The query selects the ``Root.Idle.Tick`` call at step zero,
requires its runtime role, checks the call-time ``x`` snapshot, and counts the
call within the one-step bound.

**Expected output.** Exit ``0`` with ``outcome`` equal to ``witness_found``.  The
first witness step contains one ``abstract_calls`` record with ``action_name``
``Root.Idle.Tick``, ``role`` ``leaf_during``, and ``snapshot.x`` equal to ``0``.

**File side effect.** ``/tmp/bmc-calls.json`` is atomically created or replaced.

**Failure boundary.** A call ``where`` expression sees the captured call-time
variables; it cannot use frame atoms such as ``active()`` or nested
``call_count()``.  The CLI replay records abstract calls but installs no user
handler that could mutate runtime state.

**Reference.** See :doc:`../../reference/bmc_query/index` for every call filter
key and allowed ``where`` expression.

5. Audit a human witness and replay
-----------------------------------

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q calls.fbmcq

**FBMCQ.**

.. code-block:: text

   init state("Root.Idle");
   check reach <= 1:
       called("Root.Idle.Tick", step=0, role="leaf_during", where x == 0)
       && call_count("Root.Idle.Tick", step=*) == 1;

**What it does.** Human mode prints the same witness in a compact form and runs
the mandatory replay trust gate before reporting success.

**Expected output.** The first line is ``BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND``.
``Solver: SAT`` follows as diagnostic evidence, ``Replay: verified`` reports
the runtime trust gate, and the compact ``Trace`` lists source, target, selected
case, events, and calls.  The process exits ``0``.  Use ``--color always`` to
force ANSI terminal decoration or ``--color never`` for a stable plain-text
transcript.

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

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q forbid.fbmcq --json \
       -o /tmp/bmc-ci.json

**FBMCQ.**

.. code-block:: text

   init state("Root.Idle");
   check forbid <= 1: active("Root.Done");

**What it does.** This valid query intentionally finds a forbidden-state
counterexample.  It demonstrates a machine-readable report whose process exit
is nonzero because the property is violated.

**Expected output.** The command exits ``1`` and still creates JSON containing
``"status": "sat"``, ``"outcome": "property_violated"``, and
``"exit_code": 1``.  CI should fail or allow that verdict according to project
policy, but it must not confuse it with a CLI input error.

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

**CLI.**

.. code-block:: bash

   mkdir -p /tmp/pyfcstm-bmc
   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q invariant.fbmcq \
       --json -o /tmp/pyfcstm-bmc/result.json

**FBMCQ.**

.. code-block:: text

   init state("Root.Idle");
   check invariant <= 1: x == 0;

**What it does.** The CLI writes a complete JSON payload through a
same-directory temporary file, then replaces the target path.

**Expected output.** No stdout; the file contains ``"exit_code": 0``.

**File side effect.** The target is atomically created or replaced.  The parent
directory must already exist.

**Failure boundary.** Parent directories are not created by ``pyfcstm bmc``.  If
reading, compiling, solving internally, or writing fails before a complete
payload exists, the command must not claim a successful output file.

**Reference.** See :doc:`../../reference/bmc_results/index` for overwrite,
stdout, stderr, and UTF-8 rules.

8. Enforce a maximum bound policy
---------------------------------

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q reach_bound_2.fbmcq \
       --max-bound 1

**FBMCQ.**

.. code-block:: text

   check reach <= 2: active("Root.Idle");

**What it does.** The query requests bound 2, while the command-line policy
allows at most 1.

**Expected output.** stderr contains ``Failed to compile BMC query``,
``query_bound=2``, and ``max_bound=1``; the command exits ``1``.

**File side effect.** None.  With ``-o``, no report would be created or modified
because policy rejection happens before report construction.

**Failure boundary.** ``--max-bound`` is a pre-construction policy gate, not a
request to silently clamp or truncate the query.  Values below 1 are Click
usage errors with exit ``2``.

**Reference.** See :doc:`../../reference/bmc_results/index` for CLI option and
error classification details.

9. Apply a per-check solver timeout
-----------------------------------

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q reach_bound_2.fbmcq \
       --timeout-ms 1 --json -o /tmp/bmc-timeout.json

**FBMCQ.**

.. code-block:: text

   check reach <= 2: active("Root.Idle");

**What it does.** The command passes a one-millisecond timeout to each solver
``check()``.  This fixture normally reports a timeout on a loaded development
machine, but very fast machines may produce a decisive result before the limit.

**Expected output.** On the verified run, the command exited ``3`` and JSON
contained ``"timeout_ms": 1``, ``"status": "timeout"``, and
``"outcome": "timeout"``.  If the solve finishes first, the JSON still records
``"timeout_ms": 1`` and uses the ordinary decisive exit.

**File side effect.** ``/tmp/bmc-timeout.json`` contains the completed verdict.

**Failure boundary.** The timeout is not a wall-clock budget for parsing,
expansion, formula construction, or the whole CLI.  ``response`` may execute a
second incomplete-horizon check, also with the full timeout.

**Reference.** See :doc:`../../reference/bmc_results/index` for timeout fields
and :doc:`../../explanations/bmc_solving/index` for the solve sequence.

10. Distinguish response violations from an incomplete horizon
--------------------------------------------------------------

**CLI.** Run the missing-response case first; use ``response_incomplete.fbmcq``
with the same command shape when you need the short-horizon case.

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q response_missing.fbmcq --json \
       -o /tmp/bmc-response.json

**FBMCQ file:** ``response_missing.fbmcq``

.. code-block:: text

   check response <= 1: trigger true -> within 1 false;

**FBMCQ file:** ``response_incomplete.fbmcq``

.. code-block:: text

   check response <= 1: trigger true -> within 2 false;

**What it does.** The first query is a decisive violation: a trigger exists and
no response can satisfy the one-step window.  The second shape is inconclusive
at bound 1 because a two-successor response window extends beyond the checked
suffix.

**Expected output.** ``response_missing.fbmcq`` exits ``1`` with ``status``
``sat`` and ``outcome`` ``property_violated``.  ``response_incomplete.fbmcq``
exits ``3`` with primary ``status`` ``unsat``, ``outcome`` ``incomplete``,
``incomplete`` true, and ``incomplete_status`` ``sat``; witness and replay are
null.

**File side effect.** The selected output file under ``/tmp`` is atomically
created or replaced.

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

**CLI.**

.. code-block:: bash

   python -m pyfcstm bmc \
       -i bmc_tasks.fcstm \
       -q invalid_state.fbmcq

**FBMCQ.**

.. code-block:: text

   check reach <= 1: active("Root.Missing");

**What it does.** The query is syntactically valid but names a state that the
model does not contain.

**Expected output.** stderr starts with ``Failed to compile BMC query`` and
identifies ``Root.Missing``; exit ``1``.  stdout is empty.

**File side effect.** None.  Adding ``-o /tmp/invalid.json`` still must not
create a partial payload.

**Failure boundary.** A malformed ``.fbmcq`` fails during parsing; an unknown
model object path fails during binding; a parsed but unsupported expression reports an
unsupported query.  These are controlled user-input errors.  A traceback with an
internal BMC sentinel is an implementation failure and should be reported as a
bug rather than rewritten until it becomes UNSAT.

**Reference.** See :doc:`../../reference/bmc_query/index` for legal and illegal
forms and :doc:`../../reference/bmc_results/index` for error streams.
