BMC Task Recipes
================

Use these recipes after completing :doc:`../../tutorials/bmc/index`.  Start in
an empty working directory and :download:`download the task model
<bmc_tasks.fcstm>` there.  Save each query file shown in a task under the
filename in its caption, then run the commands from the same directory.  The
model is small on purpose:

.. literalinclude:: bmc_tasks.fcstm
   :language: text
   :caption: ``bmc_tasks.fcstm``

It has one persistent variable, one event, one abstract ``during`` action, and
one event-driven transition.  Each task below gives the command with a real
terminal record, then the complete short ``.fbmcq`` file it reads, then the
explanation, expected output, and failure boundary.  A line that only says
``...`` in a terminal record stands for report lines the task does not discuss,
such as the solver time.  A task that compares alternatives shows each
alternative as a separate file.

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
   * - ``runtime_safety_unknown`` / ``runtime_safety_timeout``
     - ``result.runtime_safety.status`` is ``unknown`` or ``timeout``.
     - The check that runs before the property could not decide whether a
       runtime error is reachable, so the property was not evaluated.
     - Raise ``--timeout-ms`` or lower the bound; nonlinear operations such as
       ``sqrt`` make the check harder.  See task 17 for reachable errors.

How to read the task cards
--------------------------

Each task card includes a direct CLI command, the relevant query snippet, a
short explanation, expected output, side effects, failure boundary, and a link
to the reference page for exhaustive syntax or result facts.  Solver verdicts
are reports, including expected nonzero verdicts.  Controlled input errors write
a short message to stderr and do not create a partial report.

1. Run the chosen property kind
-------------------------------

**FBMCQ.** These are seven separate query files, not seven ``check`` clauses in
one file.  Every file starts with ``init state("Root.Idle");`` and contains
exactly one ``check`` clause.  The shared hot-start line makes frame zero
``Root.Idle``; it is required for the bound-one ``forbid`` and ``cover``
results shown below.

.. literalinclude:: reach.fbmcq
   :language: text
   :caption: reach.fbmcq

.. literalinclude:: forbid.fbmcq
   :language: text
   :caption: forbid.fbmcq

.. literalinclude:: invariant.fbmcq
   :language: text
   :caption: invariant.fbmcq

.. literalinclude:: must_reach.fbmcq
   :language: text
   :caption: must_reach.fbmcq

.. literalinclude:: exists_always.fbmcq
   :language: text
   :caption: exists_always.fbmcq

.. literalinclude:: response.fbmcq
   :language: text
   :caption: response.fbmcq

.. literalinclude:: cover.fbmcq
   :language: text
   :caption: cover.fbmcq

**CLI.** Replace ``reach.fbmcq`` with the query file for the property you
chose.  The direct ``reach`` command with ``--json``:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --json
   {
     "exit_code": 0,
   ...
       "kind": "reach",
   ...
       "outcome": "witness_found",
   ...
       "status": "sat",
   ...

**What it does.** The command asks one bounded question about the model.  The
query kind controls whether SAT means a positive witness or a counterexample.

**Expected output.** For the direct ``reach`` command, JSON contains
``"kind": "reach"``, ``"status": "sat"``, ``"outcome": "witness_found"``,
and ``"exit_code": 0``, as the record above shows.  Run each of the seven files
in human mode to see the verdict on the first line of its report; only
``forbid`` exits ``1``, because its counterexample means the property is
violated:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q forbid.fbmcq
   BMC forbid <= 1: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invariant.fbmcq
   BMC invariant <= 1: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q must_reach.fbmcq
   BMC must_reach <= 1: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q exists_always.fbmcq
   BMC exists_always <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q response.fbmcq
   BMC response <= 1: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q cover.fbmcq
   BMC cover <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...

**File side effect.** None unless you add ``-o``.

**Failure boundary.** ``cover`` accepts only a naked, known, coverable
``case("...")`` label.  A bounded result says nothing beyond the selected
bound.

**Reference.** See :doc:`../../reference/bmc_query/index` for exact property
forms and :doc:`../../explanations/bmc_properties/index` for their objectives.

2. Set a state and replace selected initializers
------------------------------------------------

**CLI.** The witness frame zero carries the state and the value the query
asked for:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q init_havoc_where.fbmcq --json
   {
     "exit_code": 0,
   ...
       "outcome": "witness_found",
   ...
     "witness": {
       "diagnostics": [],
       "frames": [
         {
           "index": 0,
           "sentinel": null,
           "state": "Root.Idle",
           "state_id": 2,
           "terminated": false,
           "vars": {
             "x": 7
           }
         },
   ...

**FBMCQ.**

.. literalinclude:: init_havoc_where.fbmcq
   :language: text
   :caption: init_havoc_where.fbmcq

**What it does.** The query starts from ``Root.Idle``, removes only ``x`` from
the initializer constraints, and constrains frame zero to ``x == 7``.

**Expected output.** JSON contains ``"kind": "reach"``,
``"outcome": "witness_found"``, and a witness frame whose ``vars.x`` is ``7``;
the exit status is ``0``.

**File side effect.** None; the report goes to stdout.

**Failure boundary.** ``where`` constrains initialization; it does not override
an initializer.  Without ``havoc { x }``, this model's ``x = 0`` and
``where x == 7`` make the trace formula UNSAT:

.. literalinclude:: init_where_only.fbmcq
   :language: text
   :caption: init_where_only.fbmcq

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q init_where_only.fbmcq
   BMC reach <= 1: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
     Failure boundary: INITIALIZATION
   ...
   $ echo $?
   3

``havoc *`` removes every persistent initializer, so prefer a named set when
possible.

**Reference.** See :doc:`../../reference/bmc_query/index` for ``cold``,
``state(...)``, ``terminated``, ``havoc``, and ``where`` legality.

3. Constrain frames and event inputs
------------------------------------

**CLI.** The command writes the report to a file and prints nothing; the file
shows the verdict, and that ``witness`` and ``replay`` are null:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q assumptions.fbmcq --json -o assumptions.json
   $ cat assumptions.json
   {
     "exit_code": 0,
   ...
     "replay": null,
   ...
       "kind": "invariant",
   ...
       "outcome": "property_satisfied",
   ...
       "status": "unsat",
   ...
     "witness": null
   }

**FBMCQ.**

.. literalinclude:: assumptions.fbmcq
   :language: text
   :caption: assumptions.fbmcq

**What it does.** The assumptions constrain ``x`` on every frame, disable
``Root.Go`` at step zero, and require at most one event from the selected event
set.

**Expected output.** The payload reports ``invariant``, ``unsat``,
``property_satisfied``, and exit ``0``.  ``witness`` and ``replay`` are null
because no counterexample exists under these assumptions.

**File side effect.** ``assumptions.json`` is atomically created or replaced in
the current directory.

**Failure boundary.** Assumptions restrict the searched environment and can make
an otherwise possible behavior disappear.  Event paths are fully qualified; an
unknown path is a binding error, not an UNSAT verdict.

**Reference.** See :doc:`../../reference/bmc_query/index` for ``always``,
``at``, event selectors, ranges, and cardinality.

4. Match abstract calls and snapshots
-------------------------------------

**CLI.**

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q calls.fbmcq --json
   {
     "exit_code": 0,
   ...
       "outcome": "witness_found",
   ...
     "witness": {
   ...
       "steps": [
         {
           "abstract_calls": [
             {
               "action_name": "Root.Idle.Tick",
               "active_leaf": "Root.Idle",
               "named_ref": null,
               "ordinal": 0,
               "role": "leaf_during",
               "snapshot": {
                 "x": 0
               },
   ...

**FBMCQ.**

.. literalinclude:: calls.fbmcq
   :language: text
   :caption: calls.fbmcq

**What it does.** The query selects the ``Root.Idle.Tick`` call at step zero,
requires its runtime role, checks the call-time ``x`` snapshot, and counts the
call within the one-step bound.

**Expected output.** Exit ``0`` with ``outcome`` equal to ``witness_found``.  The
first witness step contains one ``abstract_calls`` record with ``action_name``
``Root.Idle.Tick``, ``role`` ``leaf_during``, and ``snapshot.x`` equal to ``0``.

**File side effect.** None; add ``-o`` to write the payload atomically to a file.

**Failure boundary.** A call ``where`` expression sees the captured call-time
variables; it cannot use frame atoms such as ``active()`` or nested
``call_count()``.  The CLI replay records abstract calls but installs no user
handler that could mutate runtime state.

**Reference.** See :doc:`../../reference/bmc_query/index` for every call filter
key and allowed ``where`` expression.

5. Audit a human witness and replay
-----------------------------------

**CLI.** The lines that vary from run to run (the solver time) or that this
card does not discuss are left out:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q calls.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
     Replay: verified (2 frames, 1 step).
   ...
   Solver: SAT in ... ms
   ...
   Trace
     0: Root.Idle -> Root.Idle [fallback; calls=Root.Idle.Tick]
   ...

**FBMCQ.** The same ``calls.fbmcq`` as task 4:

.. literalinclude:: calls.fbmcq
   :language: text
   :caption: calls.fbmcq

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

**CLI.** The command exits ``1`` and still writes the report:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q forbid.fbmcq --json -o ci.json
   $ echo $?
   1
   $ cat ci.json
   {
     "exit_code": 1,
   ...
       "outcome": "property_violated",
   ...
       "status": "sat",
   ...

**FBMCQ.** The same ``forbid.fbmcq`` as task 1:

.. literalinclude:: forbid.fbmcq
   :language: text
   :caption: forbid.fbmcq

**What it does.** This valid query intentionally finds a forbidden-state
counterexample.  It demonstrates a machine-readable report whose process exit
is nonzero because the property is violated.

**Expected output.** The command exits ``1`` and still creates JSON containing
``"status": "sat"``, ``"outcome": "property_violated"``, and
``"exit_code": 1``.  CI should fail or allow that verdict according to project
policy, but it must not confuse it with a CLI input error.

**File side effect.** ``ci.json`` is created even though the verdict exit is
``1``.

**Failure boundary.** Exit ``0`` means a satisfied property or positive witness;
``1`` also covers controlled errors, distinguishable because those have stderr
and no report; ``2`` is Click usage; ``3`` is inconclusive; ``4`` is a
structured replay mismatch.  Always inspect JSON when a report exists.

**Reference.** See :doc:`../../reference/bmc_results/index` for the full branch
matrix and stable JSON schema.

7. Write a completed report atomically
--------------------------------------

**CLI.** The parent directory must already exist; a missing one is refused:

.. code-block:: console

   $ mkdir reports
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invariant.fbmcq --json -o reports/result.json
   $ cat reports/result.json
   {
     "exit_code": 0,
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invariant.fbmcq --json -o missing/result.json
   Failed to write BMC output file missing/result.json: [Errno 2] No such file or directory: 'missing/.result.json...tmp'
   $ echo $?
   1

**FBMCQ.** The same ``invariant.fbmcq`` as task 1:

.. literalinclude:: invariant.fbmcq
   :language: text
   :caption: invariant.fbmcq

**What it does.** The CLI writes a complete JSON payload through a
same-directory temporary file, then replaces the target path.  The error
message above names that temporary file.

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

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach_bound_2.fbmcq --max-bound 1
   Failed to compile BMC query: max_bound policy rejected query_bound=2 with max_bound=1.
   $ echo $?
   1

**FBMCQ.**

.. literalinclude:: reach_bound_2.fbmcq
   :language: text
   :caption: reach_bound_2.fbmcq

**What it does.** The query requests bound 2, while the command-line policy
allows at most 1.

**Expected output.** stderr contains ``Failed to compile BMC query``,
``query_bound=2``, and ``max_bound=1``; the command exits ``1``, as the block
above shows.

**File side effect.** None.  With ``-o``, no report would be created or modified
because policy rejection happens before report construction.

**Failure boundary.** ``--max-bound`` is a pre-construction policy gate, not a
request to silently clamp or truncate the query.  Values below 1 are Click
usage errors with exit ``2``.

**Reference.** See :doc:`../../reference/bmc_results/index` for CLI option and
error classification details.

9. Apply a per-check solver timeout
-----------------------------------

**CLI.** This command is not run in the documentation check, because whether
one millisecond is enough depends on the speed of the machine:

.. code-block:: bash

   pyfcstm bmc -i bmc_tasks.fcstm -q reach_bound_2.fbmcq \
       --timeout-ms 1 --json -o bmc-timeout.json

**FBMCQ.** The same ``reach_bound_2.fbmcq`` as task 8:

.. literalinclude:: reach_bound_2.fbmcq
   :language: text
   :caption: reach_bound_2.fbmcq

**What it does.** The command passes a one-millisecond timeout to each solver
``check()``.  Whether this fixture times out depends on the machine: a loaded or
slow machine can exceed the limit, while a fast one decides first.

**Expected output.** If the limit is exceeded, the command exits ``3`` and JSON
contains ``"timeout_ms": 1``, ``"status": "timeout"``, and
``"outcome": "timeout"``.  If the solve finishes first, the JSON still records
``"timeout_ms": 1`` and uses the ordinary decisive exit; when this page was
written, repeated runs on a development machine finished first, exited ``0``, and
reported ``"outcome": "witness_found"``.

**File side effect.** ``bmc-timeout.json`` contains the completed verdict.

**Failure boundary.** The timeout is not a wall-clock budget for parsing,
expansion, formula construction, or the whole CLI.  ``response`` may execute a
second incomplete-horizon check, also with the full timeout.

**Reference.** See :doc:`../../reference/bmc_results/index` for timeout fields
and :doc:`../../explanations/bmc_solving/index` for the solve sequence.

10. Distinguish response violations from an incomplete horizon
--------------------------------------------------------------

**CLI.** Run the missing-response case first, then the short-horizon case.  The
first line of the human report already tells them apart, and so do the exit
codes:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_missing.fbmcq
   BMC response <= 1: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_incomplete.fbmcq
   BMC response <= 1: PROPERTY INCONCLUSIVE; RESPONSE HORIZON INCOMPLETE
   ...
   $ echo $?
   3

The JSON of each run says the same thing in fields:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_missing.fbmcq --json
   {
     "exit_code": 1,
   ...
       "outcome": "property_violated",
   ...
       "status": "sat",
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q response_incomplete.fbmcq --json
   {
     "exit_code": 3,
   ...
     "replay": {
       "mismatches": [],
       "model_role": "incomplete_suffix",
       "ok": true,
   ...
       "incomplete": true,
   ...
       "incomplete_status": "sat",
   ...
       "outcome": "incomplete",
   ...
       "status": "unsat",
   ...
     "witness": {
   ...
       "model_role": "incomplete_suffix",
   ...
   $ echo $?
   3

Add ``-o bmc-response.json`` to either command to write the result to a file
instead.

**FBMCQ file:** ``response_missing.fbmcq``

.. literalinclude:: response_missing.fbmcq
   :language: text

**FBMCQ file:** ``response_incomplete.fbmcq``

.. literalinclude:: response_incomplete.fbmcq
   :language: text

**What it does.** The first query is a decisive violation: a trigger exists and
no response can satisfy the one-step window.  The second shape is inconclusive
at bound 1 because a two-successor response window extends beyond the checked
suffix.

**Expected output.** ``response_missing.fbmcq`` exits ``1`` with ``status``
``sat`` and ``outcome`` ``property_violated`` in JSON.  ``response_incomplete.fbmcq``
exits ``3`` with primary ``status`` ``unsat``, ``outcome`` ``incomplete``,
``incomplete`` true, and ``incomplete_status`` ``sat``.  Its ``witness`` is not
null: it is the incomplete suffix (``model_role`` ``incomplete_suffix``) that
could still violate the property, and ``replay`` confirms it with ``ok`` true.
Treat that witness as the reason the result is inconclusive, not as a
counterexample.

**File side effect.** None unless you add ``-o``; then the output file is
atomically created or replaced.

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

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q invalid_state.fbmcq
   Failed to compile BMC query: unknown_state at property.predicate: Unknown state path: 'Root.Missing'.
   $ echo $?
   1
   $ pyfcstm bmc -i bmc_tasks.fcstm -q invalid_state.fbmcq --json -o invalid.json
   Failed to compile BMC query: unknown_state at property.predicate: Unknown state path: 'Root.Missing'.
   $ echo $?
   1
   $ test -e invalid.json
   $ echo $?
   1

**FBMCQ.**

.. literalinclude:: invalid_state.fbmcq
   :language: text
   :caption: invalid_state.fbmcq

**What it does.** The query is syntactically valid but names a state that the
model does not contain.

**Expected output.** stderr starts with ``Failed to compile BMC query`` and
identifies ``Root.Missing``; exit ``1``.  stdout is empty.

**File side effect.** None.  Adding ``-o invalid.json`` still creates no
partial payload: the last two commands above show that the file does not exist.

**Failure boundary.** A malformed ``.fbmcq`` fails during parsing; an unknown
model object path fails during binding; a parsed but unsupported expression reports an
unsupported query.  These are controlled user-input errors.  A traceback with an
internal BMC sentinel is an implementation failure and should be reported as a
bug rather than rewritten until it becomes UNSAT.

**Reference.** See :doc:`../../reference/bmc_query/index` for legal and illegal
forms and :doc:`../../reference/bmc_results/index` for error streams.

12. Choose an explanation depth
-------------------------------

**CLI.** Run the same query at each depth.  Both runs exit ``3``, because an
infeasible scenario is a report and not a failure:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility formal --color never
   BMC reach <= 2: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: COMPLETE FORMAL DOMAIN EXPLANATION
   Classification: the assumptions are internally inconsistent
   ...
   Conflict constraints:
     1. infeasible_two_values.fbmcq:1:1-1:28
        assume at 1: var("x") == 1;
     2. infeasible_two_values.fbmcq:2:1-2:28
        assume at 1: var("x") == 2;
   ...
   $ echo $?
   3
   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --color never
   BMC reach <= 2: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: COMPLETE VERIFIED DOMAIN PROOF
   Classification: the assumptions are internally inconsistent
   ...
   Why no execution exists:
     1. At frame 1, x must equal 1.
     2. At frame 1, x must equal 2.
     3. Therefore one value cannot be two things at once. No execution satisfies these query requirements, and the property was not evaluated.
   ...
   $ echo $?
   3

**FBMCQ.**

.. literalinclude:: infeasible_two_values.fbmcq
   :language: text
   :caption: infeasible_two_values.fbmcq

**What it does.** ``--explain-infeasibility`` asks why an infeasible scenario is
infeasible.  ``none`` (the default) does no extra solver work.  ``formal`` adds a
classification and a source core.  ``proof`` additionally builds a checked
step-by-step derivation.  The depth never changes the verdict, so raising it
cannot turn an inconclusive run into a conclusive one -- it only adds diagnosis.

**Expected output.** ``formal`` reports ``COMPLETE FORMAL DOMAIN EXPLANATION``
with the classification, the core members and their source positions.  Re-running
the same query with ``--explain-infeasibility proof`` reports
``COMPLETE VERIFIED DOMAIN PROOF`` and a numbered derivation.  Both exit ``3``.

The headline names the depth *and* how complete it is, so ``COMPLETE`` at
``formal`` depth means the formal explanation produced everything it promises --
not that a proof was found.  The four headlines are listed in
:doc:`../../reference/bmc_results/index`.

**File side effect.** None without ``-o``.

**Failure boundary.** ``proof`` costs extra solver checks: each input node is
verified in both directions and each derived step is re-derived independently.
On this fixture the extra cost is small (the report prints ``Explanation time``
in milliseconds), but a large core with many members will cost more.  Use
``none`` in a CI gate that only needs the verdict, ``formal`` when a human will
read the failure, and ``proof`` when the reasoning itself has to be auditable.

**Next diagnostic step.** If ``proof`` returns ``achieved_mode`` as ``formal``,
go to task 15.

**Reference.** See :doc:`../../reference/bmc_results/index` for the option
contract and the block layouts.


13. Read a conflict core and act on it
--------------------------------------

**CLI.**

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_cross_step.fbmcq \
       --explain-infeasibility formal --color never
   BMC reach <= 2: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: COMPLETE FORMAL DOMAIN EXPLANATION
   Classification: assumptions conflict with the feasible prefix
   ...
   Conflict constraints:
     1. infeasible_cross_step.fbmcq:2:1-2:28
        assume at 1: var("x") == 3;
     2. infeasible_cross_step.fbmcq:1:1-1:38
        init state("Root.Idle") where x == 0;
     3. bmc_tasks.fcstm:1:1-1:15
        def int x = 0;
     4. generated transition constraint at step 0
   ...
   Reduction: subset_minimal
   ...
   $ echo $?
   3

**FBMCQ.**

.. literalinclude:: infeasible_cross_step.fbmcq
   :language: text
   :caption: infeasible_cross_step.fbmcq

**What it does.** The core is the set of clauses that together make the scenario
infeasible, each with the position it was written at.

**Expected output.** Read it as: the classification says which file to open, and
the members say which lines.  Here the assumption at frame 1 disagrees with what
the initializer and the declaration force, so either the ``assume`` value or the
initial value has to change.

Member 4 has no source position because nobody wrote it: the builder generates
the transition constraint that carries frame 0's values forward.  A generated
member names its category and the step it constrains, and is not something you
can edit -- it tells you *why* the authored members conflict, not what to
change.

**File side effect.** None without ``-o``.

**Failure boundary.** A core is only guaranteed *sufficient* unless the report
says otherwise.  Check the ``Reduction:`` line: ``raw`` may include members that
are not part of the conflict, ``partial_minimized`` was cut short, and only
``subset_minimal`` guarantees every listed member is load bearing, as it does in
the record above.  Editing a member of a ``raw`` core may change nothing.

**Next diagnostic step.** For the reasoning that links the members, raise the
depth to ``proof`` and read task 14.

**Reference.** See :doc:`../../explanations/bmc_solving/index` for why sufficient
is not minimal.


14. Read a proof and trace a sentence to a clause
-------------------------------------------------

**CLI.** The JSON keeps the narrative and the proof graph side by side.  Each
narrative sentence lists the ``proof_node_ids`` behind it, and each node has a
``stable_id`` that those lists point to:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --json
   {
     "exit_code": 3,
   ...
           "narrative": {
   ...
                 "proof_node_ids": [
                   "proof.input.0000"
                 ],
                 "text": "At frame 1, x must equal 1."
   ...
           "proof": {
             "graph_minimality": "dependency_pruned",
             "input_minimality": "subset_minimal",
   ...
                 "rule_id": "source_fact",
                 "stable_id": "proof.input.0000",
                 "verification_method": "core_binding"
   ...
                 "rule_id": "source_fact",
                 "stable_id": "proof.input.0001",
                 "verification_method": "core_binding"
   ...
                 "rule_id": "incompatible_equalities",
                 "stable_id": "proof.step.0002",
                 "verification_method": "rule_checker"
               }
             ],
             "root_id": "proof.step.0002",
   ...
             "verification_status": "verified"
   ...
   $ echo $?
   3

**FBMCQ.** The same ``infeasible_two_values.fbmcq`` as task 12:

.. literalinclude:: infeasible_two_values.fbmcq
   :language: text
   :caption: infeasible_two_values.fbmcq

**What it does.** At ``proof`` depth the narrative is the proof read in
dependency order, and every sentence names the node behind it.  The JSON keeps
both, so a sentence and its checked step can be reached from each other.

**Expected output.** The JSON at ``result.feasibility.explanation.proof`` carries
the graph shown above: two ``input`` nodes, one per core member, each verified
against the member it restates by ``core_binding``; and one root
(``proof.step.0002``), re-derived by an independent ``rule_checker``.
``input_minimality`` is ``subset_minimal``, ``graph_minimality`` is
``dependency_pruned``, and ``verification_status`` is ``verified``.

**File side effect.** None without ``-o``; add ``-o`` to write the whole result
to a file instead of stdout.

**Failure boundary.** A verified proof says each step follows from the clauses
named beside it.  It does not say the encoding matches what you meant -- that is
the same boundary replay draws for a witness.  And the closing sentence reports
that the property was *not evaluated*; it is not a counterexample.

**Next diagnostic step.** If ``proof`` was requested but the block says
``achieved formal``, read task 15.

**Reference.** See :doc:`../../reference/bmc_results/index` for the node
vocabulary and what each verification method checks.


15. Handle a degraded or timed-out explanation
----------------------------------------------

**Starting files.** This task uses ``controller.fcstm`` (:download:`download
</_models/controller.fcstm>`), the same model as the region tasks below, and a
query that assumes a value for ``motor`` at frame 1.  ``Idle`` writes ``motor``
in its ``during`` action, so the value at frame 1 comes from an executed
transition and not from a declaration:

.. literalinclude:: infeasible_after_write.fbmcq
   :language: text
   :caption: infeasible_after_write.fbmcq

**CLI.**

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q infeasible_after_write.fbmcq \
       --explain-infeasibility proof --color never
   BMC reach <= 1: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
   Explanation: PARTIAL FORMAL DOMAIN EXPLANATION
   Explanation depth: requested proof, achieved formal
   Classification: assumptions conflict with the feasible prefix
   ...
   Reason: the formal explanation is complete, but no rule in the catalog closes this core.
   ...
   $ echo $?
   3
   $ pyfcstm bmc -i controller.fcstm -q infeasible_after_write.fbmcq \
       --explain-infeasibility proof --json
   {
     "exit_code": 3,
   ...
           "achieved_mode": "formal",
   ...
           "proof": null,
           "reason": "the formal explanation is complete, but no rule in the catalog closes this core.",
           "requested_mode": "proof",
           "status": "partial"
   ...
   $ echo $?
   3

**What it does.** The explanation reports the depth it reached, not the depth
that was asked for.  The conflict here runs through a transition that writes
``motor``, and no rule in the proof catalog closes a core of that shape, so the
report keeps the formal explanation and says so.  The conflict in task 14, which
involves only two ``assume`` clauses, does close.

**Expected output.** As the records above show: the human report says
``requested proof, achieved formal`` under a ``PARTIAL`` headline, and in JSON
``requested_mode`` is ``proof``, ``achieved_mode`` is ``formal``, ``status`` is
``partial``, and ``proof`` is ``null``.

**File side effect.** None without ``-o``.

**Failure boundary.** Degradation is not an error and does not change the exit
status, so a consumer must compare ``requested_mode`` with ``achieved_mode``
rather than assume ``proof`` is present.  A missing ``proof`` key means the depth
was not reached, not that the run failed.  The formal explanation of a degraded
run is still complete: it names the initial state, the transition constraint and
both conflicting values, as the ``Why no execution exists`` block shows.

**Next diagnostic step.** Read ``reason``.  ``no rule in the catalog closes this
core`` is a capability boundary and will not change by retrying.  ``timeout`` or
``unknown`` in ``status`` is a budget problem: retry with a larger
``--timeout-ms``, or drop to ``formal``.

**Reference.** See :doc:`../../explanations/bmc_solving/index` for why some
conflicts have no proof.


16. Gate CI on an explanation without scraping text
---------------------------------------------------

**CLI.** An infeasible scenario exits ``3``, which is a report and not a
failure.  The first command writes the JSON, and a short script reads it:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --color never \
       --json -o gate.json
   $ echo $?
   3

.. testcode::

   import json

   with open("gate.json") as handle:
       report = json.load(handle)
   explanation = report["result"]["feasibility"]["explanation"]
   print(explanation["requested_mode"], explanation["achieved_mode"])
   print(explanation["status"], explanation["classification"])

.. testoutput::

   proof proof
   complete assumptions_self_conflict

In a CI step that runs under ``set -e`` -- which GitHub Actions uses for every
``run:`` step -- an unguarded invocation would abort the step at the exit ``3``
and never reach the inspection.  Guard the command the way this shell snippet
does; it is not run in the documentation check, because it is a CI step and not
a terminal record:

.. code-block:: bash

   pyfcstm bmc -i bmc_tasks.fcstm -q infeasible_two_values.fbmcq \
       --explain-infeasibility proof --color never \
       --json -o gate.json && status=0 || status=$?
   test "$status" -eq 3

**FBMCQ.** The same ``infeasible_two_values.fbmcq`` as task 12:

.. literalinclude:: infeasible_two_values.fbmcq
   :language: text
   :caption: infeasible_two_values.fbmcq

**What it does.** Reads the explanation through the versioned JSON contract
instead of the human report, which is what a gate should depend on.

**Expected output.** ``proof proof`` then ``complete
assumptions_self_conflict``, as the script prints.

**File side effect.** ``gate.json`` is written atomically.

**Failure boundary.** The exit status is part of the contract a gate has to
handle: ``3`` means the scenario was infeasible and the property was not
evaluated, which for this query is the expected result rather than an error.  A
step that lets ``set -e`` abort on it never reads the explanation it asked for.

``explanation`` is ``null`` at ``none`` depth, so a gate
must handle that rather than index into it.  Human wording and ``elapsed_ms`` are
not contracts and must not be asserted on; the enumerated fields are.  ANSI
decoration never reaches JSON or ``--output`` files regardless of ``--color``.

**Next diagnostic step.** To fail a build only on a specific conflict family,
compare ``classification`` against the closed list rather than matching the
printed phrase.

**Reference.** See :doc:`../../reference/bmc_results/index` for JSON nullability
and the schema.

17. Handle a runtime error in the model
---------------------------------------

**Starting files.** Save this model as ``runtime_error.fcstm``: the second
guard divides by the input ``d`` whenever the first guard fails.

.. code-block:: fcstm

   input int d;
   state Root {
       [*] -> A;
       state A;
       state B;
       state C;
       A -> B : if [d == 1];
       A -> C : if [10 / d > 1];
   }

The commands below write the same model on one line (whitespace carries no
meaning in FCSTM), together with the query ``check reach <= 2:
active("Root.B");`` and a variant of it that first assumes ``d != 0``.

**CLI.** The reachable error exits ``5``.  The report names the operation and
the step, and replay confirms the simulator raises the same error:

.. code-block:: console

   $ echo 'input int d; state Root { [*] -> A; state A; state B; state C; A -> B : if [d == 1]; A -> C : if [10 / d > 1]; }' > runtime_error.fcstm
   $ echo 'check reach <= 2: active("Root.B");' > runtime_error.fbmcq
   $ pyfcstm bmc -i runtime_error.fcstm -q runtime_error.fbmcq
   BMC reach <= 2: RUNTIME ERROR REACHABLE WITHIN BOUND; PROPERTY NOT EVALUATED
   ...
     Runtime error: division_by_zero at step 1
     Runtime error location: guard g1 in transition Root.A::1::A->C
   ...
     Replay: runtime error reproduced: transition guard evaluation failed: division by zero
   ...
   $ echo $?
   5

**Failure boundary.** The property was not evaluated at all: no execution that
reaches the error can continue, so neither "holds" nor "violated" is claimed.
A replay that does not reproduce the error exits ``4`` instead.

**Next step.** Choose by what the requirement says:

- If the environment guarantees ``d != 0``, state it.  With
  ``assume always: d != 0;`` before the ``check`` line the run exits ``0`` with
  ``PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND``.
- If ``d`` can really be zero, the model is wrong: guard the division, for
  example ``d != 0 && 10 / d > 1``, which ``&&`` evaluates only when ``d`` is
  non-zero.
- To evaluate the property only over executions that raise no error, add
  ``--no-runtime-safety``; this run also exits ``0`` with a witness.  The error
  is still reachable; the report just no longer looks for it.

.. code-block:: console

   $ printf 'assume always: d != 0;\ncheck reach <= 2: active("Root.B");\n' > runtime_error_assumed.fbmcq
   $ pyfcstm bmc -i runtime_error.fcstm -q runtime_error_assumed.fbmcq
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i runtime_error.fcstm -q runtime_error.fbmcq --no-runtime-safety
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...

**Reference.** See :doc:`../../reference/bmc_results/index` for the
``runtime_safety`` result, the ``runtime_error_prefix`` witness and exit ``5``.

Tasks for models with regions
-----------------------------

These cards use ``controller.fcstm``, the interlock controller of
:doc:`/tutorials/regions/index` (``Safety`` before ``Motion`` inside
``Running``); download it
(:download:`controller.fcstm </_models/controller.fcstm>`) next to the query
files named in each card.  A bounded result says nothing beyond its bound, and
SAT or UNSAT is read through the property kind, as in the cards above.  The
cards run ``pyfcstm bmc`` in human mode and read the trace; a line that only
says ``...`` stands for report lines the card does not discuss, such as the
solver time.  The same facts are in the JSON result (``witness.frames``,
``witness.steps``), whose fields are listed in
:doc:`/reference/bmc_results/index`.

18. Check a property from a given position
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``controller.fcstm`` and ``region_start.fbmcq``.  ``init
state(...)`` accepts configuration text, a state path through regions, or an
owner written alone.  Persistent variables keep their initializers unless you
``havoc`` them, so ``permit`` and ``motor`` are released and constrained.

.. literalinclude:: region_start.fbmcq
   :language: text
   :caption: region_start.fbmcq

**CLI.**

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_start.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: Watching, Motion: On}
          -> Controller.Idle [transition; events=Controller.Stop]
          Safety: Watching -> [done] [transition]
          Motion: On -> [done] [transition]
          Running: [start] -> Controller.Idle [transition]
   ...

**Expected output.** Frame 0 is exactly the configuration you wrote.  The
query asks for ``Controller.Idle`` within one step, and the only way out of
``Running`` is the ``Stop`` forced transition, so the trace ends in
``Controller.Idle``.  Step 0 lists one local case per region that did
something: ``Safety`` and ``Motion`` each take their transition to ``[done]``
(the ``__region_done__`` transition), then the owner takes its transition to
``Idle``; the next card explains these entries.
Without ``havoc { permit, motor }`` the same ``where`` clause makes the scenario
infeasible, because the initializers ``permit = 0`` and ``motor = 0`` contradict
it.  The query is the same as ``region_start.fbmcq`` minus the ``havoc`` part:

.. literalinclude:: region_start_no_havoc.fbmcq
   :language: text
   :caption: region_start_no_havoc.fbmcq

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_start_no_havoc.fbmcq
   BMC reach <= 1: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   ...
     Failure boundary: INITIALIZATION
   ...
   $ echo $?
   3

**File side effect.** None; the report goes to stdout.

**First failure check.** If the verdict is ``SCENARIO INFEASIBLE``, read the
``Failure boundary`` line of the human report and compare the ``where`` clause
with the variable initializers.  If compilation stops with
``invalid_start_position``, the start text is wrong.  These are negative
examples: ``region_bad_start.fbmcq`` names a state that does not exist and
``region_all_done.fbmcq`` marks every region of an owner ``[done]``, which is
never a resting position.  Both commands exit with code 1:

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_bad_start.fbmcq
   Failed to compile BMC query: invalid_start_position at initial.state_path: Unknown configuration path: 'Controller.Running.Safety.Nope'.
   $ echo $?
   1
   $ pyfcstm bmc -i controller.fcstm -q region_all_done.fbmcq
   Failed to compile BMC query: invalid_start_position at initial.state_path: all regions are done at 'Controller.Running'; a finished owner cannot be hot-started.
   $ echo $?
   1

**Reference.** :doc:`/reference/bmc_query/index`.

19. Match a position with an ``active`` configuration pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** Three queries over the same model.  ``init state(...)``
*constructs* a position, so a region it leaves out waits for initialization.
``active("...{...}")`` *matches* one, so a region it leaves out is free.

.. literalinclude:: region_pattern_construct.fbmcq
   :language: text
   :caption: region_pattern_construct.fbmcq

.. literalinclude:: region_pattern_match.fbmcq
   :language: text
   :caption: region_pattern_match.fbmcq

.. literalinclude:: region_pattern_construct_miss.fbmcq
   :language: text
   :caption: region_pattern_construct_miss.fbmcq

**CLI.** Each command prints frame 0 only (the ``0:`` line of the trace): the
property already holds there, and later frames are free choices of the solver.

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_pattern_construct.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: [init], Motion: On}
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_pattern_match.fbmcq
   BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: Watching, Motion: On}
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_pattern_construct_miss.fbmcq
   BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1

**Expected output.** The first
query leaves ``Safety`` out of the start text: frame 0 shows ``Safety:
[init]``, and the pattern that writes ``[init]`` matches it.  The second query
starts with both regions written and the pattern leaves ``Safety`` out, so
``Watching`` does not matter.  The third query
starts with ``Safety: Watching`` and asks for ``Safety: [init]``: no witness
(exit 1).  The pattern holds exactly where the written regions
agree, and the ``[init]`` marker also holds for a region that has not started
in a call made while its owner is being entered.

**File side effect.** None.

**First failure check.** If a pattern is rejected, compilation stops with
``invalid_active_pattern`` (negative example ``region_bad_pattern.fbmcq``):

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_bad_pattern.fbmcq
   Failed to compile BMC query: invalid_active_pattern at property.predicate: Unknown state path: 'Controller.Running.Safety.Nope'.
   $ echo $?
   1

If a pattern matches too much, check which regions you left out.

**Reference.** :doc:`/reference/bmc_query/index`.

20. Read ``local_cases`` and ``case_label``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``region_cases.fbmcq`` and ``region_cover.fbmcq``.  Each witness
step is one whole cycle.  ``case_label`` is the label of the case that runs
outside every region, or ``null`` if there is none.  ``local_cases`` lists, in
execution order, one entry per scope that did something: ``scope`` (a state
path, or ``null`` outside every region), ``kind`` and ``label``.

.. literalinclude:: region_cases.fbmcq
   :language: text
   :caption: region_cases.fbmcq

.. literalinclude:: region_cover.fbmcq
   :language: text
   :caption: region_cover.fbmcq

**CLI.** The human trace prints each step on the line that starts with its
index, followed by one line per case with its scope relative to the owner.  The
second command covers one local case:

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Idle
          -> Controller.Running{Safety: Watching, Motion: Off} [transition; events=Controller.Start]
          Controller.Idle -> Controller.Running [transition]
          Running: [start] -> Safety.Watching [initial]
          Running: [start] -> Motion.Off [initial]
     1: Controller.Running{Safety: Watching, Motion: Off}
          -> Controller.Running{Safety: Watching, Motion: On} [transition]
          Safety: Watching -> Watching [fallback]
          Motion: Off -> On [transition]
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_cover.fbmcq
   BMC cover <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   Trace
     0: Controller.Running{Safety: Watching, Motion: Off}
          -> Controller.Running{Safety: Watching, Motion: On} [transition]
          Safety: Watching -> Watching [fallback]
          Motion: Off -> On [transition]
   ...

The same cases are the ``case_label`` and ``local_cases`` fields of each witness
step in JSON:

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq --json
   {
     "exit_code": 0,
   ...
           "case_label": "Controller.Idle::transition::Controller.Running::0",
   ...
           "local_cases": [
             {
               "kind": "transition",
               "label": "Controller.Idle::transition::Controller.Running::0",
               "scope": null
             },
   ...
           "case_kind": "transition",
           "case_label": null,
   ...
           "local_cases": [
             {
               "kind": "fallback",
               "label": "Controller.Running.Safety.Watching::fallback::Controller.Running.Safety.Watching::0",
               "scope": "Controller.Running.Safety"
             },
             {
               "kind": "transition",
               "label": "Controller.Running.Motion.Off::transition::Controller.Running.Motion.On::2",
               "scope": "Controller.Running.Motion"
             }
           ],
   ...

**Expected output.** Step 0 enters ``Running``: the line under ``0:`` is the
outer transition (``case_label`` in JSON), the first case is outside every
region, and the owner scope shows one ``initial`` case per region.  Step 1 has
no outer case because every case ran inside a region: ``Safety`` stays
(``fallback``) and ``Motion`` moves (``transition``).  In JSON the same cases
are ``local_cases``, with ``case_label`` set to ``null`` for step 1.  A
``cover`` query takes a naked ``case("label")``; copy the label from a
witness.  The ``::2`` at the end of a label is the case's ordinal among the
expanded cases, not a count of anything you wrote.

**File side effect.** None.

**First failure check.** If ``cover`` says the label is unknown, the message is
``Failed to compile BMC query: cover case label is unknown``: copy the label
from a witness of a ``reach`` query on the same model.

**Reference.** :doc:`/reference/bmc_results/index`.

21. Handle ``max_group_reentries`` being exceeded
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** A state that owns regions can be entered again inside one cycle
(``Owner -> Owner``).  When the values change on each lap, the relation unrolls
the laps one by one, at most ``BmcOptions.max_group_reentries`` times (16 by
default), and raises ``BmcBuildError`` beyond that instead of approximating.
``region_reentry_six.fcstm`` needs six laps; ``region_reentry_loop.fcstm``
has a guard (``n < limit``) that no value can stop.

.. literalinclude:: region_reentry_six.fcstm
   :language: fcstm
   :caption: region_reentry_six.fcstm

**Command or code.** The CLI has no option for the limit, so raise it in
Python:

.. testcode::

   from pyfcstm.bmc import BmcBuildError, BmcOptions, compile_bmc_query
   from pyfcstm.model import load_state_machine_from_file

   query = "check reach <= 1: terminated();"
   for name, limit in [("region_reentry_six", 7), ("region_reentry_six", 6), ("region_reentry_loop", 64)]:
       model = load_state_machine_from_file(name + ".fcstm")
       options = BmcOptions(max_group_reentries=limit)
       try:
           compile_bmc_query(model, query, options=options)
           print(name, limit, "compiled")
       except BmcBuildError as error:
           print(name, limit, "refused:", error)

.. testoutput::

   region_reentry_six 7 compiled
   region_reentry_six 6 refused: state 'Root.Owner' re-enters its own group more than 6 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.
   region_reentry_loop 64 refused: state 'Root.Owner' re-enters its own group more than 64 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.

Compare with the CLI on the same two models:

.. code-block:: console

   $ pyfcstm bmc -i region_reentry_six.fcstm -q region_reentry.fbmcq
   BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i region_reentry_loop.fcstm -q region_reentry.fbmcq
   ...
   Traceback (most recent call last):
   ...
   _BmcCliInternalError: state 'Root.Owner' re-enters its own group more than 16 times inside one cycle, so the relation cannot be bounded; raise BmcOptions.max_group_reentries to unroll it deeper.
   $ echo $?
   1

**Expected output.** The six-lap model compiles with a limit of 16 (the
default) or 7 and is refused with 6; the message names the state and the option.
The unbounded loop is refused at every limit: a larger number never helps there
(the same message appears with the default limit of 16 in the CLI run above).

The command-line output above is not the way to read this limit.  The
six-lap model builds, and its exit code 1 is an ordinary verdict:
``reach terminated()`` has no witness within one step (``GOAL UNREALIZABLE
WITHIN BOUND``), which says nothing about the build.  For the unbounded loop
the CLI currently stops with exit code 1 and a Python traceback; only its last
line, the same message, is useful.  The CLI has no option for the limit, which
is why this card works through the Python API.

**File side effect.** None.

**First failure check.** First ask whether the loop is meant to stop: make the
guard depend on a counter or a constant so some value stops it.  Raise the
limit only when the loop is bounded and just longer than 16.

**Reference.** :doc:`/reference/bmc_results/index`.

22. Make a query affordable
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** A query that is slow or times out.  The cost grows with the number
of variables the transitions write, with the bound ``k`` and with the number of
states and regions; regions add up rather than multiply, but regions that
exclude each other can grow exponentially when the solver must prove that
something is impossible.  The measurements behind this are on synthetic models
and are not a promise: :doc:`/explanations/bmc_scaling/index` has the data and
the reasoning, ``tools/measure_bmc_scaling.py`` regenerates it, and `issue #600
<https://github.com/HansBug/pyfcstm/issues/600>`_ tracks the optimization ideas.

**CLI.** Raise the bound one step at a time, classify the verdict instead of
assuming SAT or UNSAT, and enforce a ceiling with ``--max-bound``.  The query
for ``k=1`` is ``region_reach_k1.fbmcq``, and ``region_cases.fbmcq`` is the same
query with ``k=2``:

.. literalinclude:: region_reach_k1.fbmcq
   :language: text
   :caption: region_reach_k1.fbmcq

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q region_reach_k1.fbmcq
   BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   ...
   $ echo $?
   1
   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq
   BMC reach <= 2: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   ...
   $ pyfcstm bmc -i controller.fcstm -q region_cases.fbmcq --max-bound 1
   Failed to compile BMC query: max_bound policy rejected query_bound=2 with max_bound=1.
   $ echo $?
   1

**Expected output.** ``k=1`` has no witness yet (exit 1) and ``k=2`` is the
first bound with a witness, so a deeper bound adds nothing for this question;
the policy ``--max-bound 1`` rejects the ``k=2`` query with exit 1 before
solving.  Treat ``unknown`` and
``timeout`` as *inconclusive* results with their own expected exit handling in
CI (exit 3); pass ``--timeout-ms`` to bound each ``check()``.  These runs did
not time out, so none of them shows a ``timeout`` verdict.

Steps to shrink a query that is too slow:

1. Reduce the variables the regions write: ``havoc`` only what the property
   needs and ``where``-constrain the rest.
2. Start from a position (task 18) instead of the cold start, so the first
   bound is not spent walking there.
3. Ask for the smallest ``k`` that can show the behavior, then deepen it.
4. Query one property at a time; do not combine unrelated predicates.
5. If regions are mutually exclusive (one can only run when another does
   not), expect proofs of impossibility to be the slow case and keep ``k``
   small there.

**File side effect.** None.

**First failure check.** Read ``result.status``.  ``timeout`` means one
solver ``check()`` did not finish within ``--timeout-ms``; it is not a
verdict.

**Reference.** :doc:`/reference/bmc_results/index`.

Choose and compare a solver profile
-----------------------------------

Use this page's ``bmc_tasks.fcstm`` and ``reach.fbmcq`` from the same
directory. Run each choice explicitly:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile default --json
   {
     "exit_code": 0,
   ...
       "ok": true,
   ...
       "property_satisfied": true,
   ...
       "solver_profile": "default",
   ...
       "status": "sat",
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile logic --json
   {
     "exit_code": 0,
   ...
       "ok": true,
   ...
       "property_satisfied": true,
   ...
       "solver_logic": "QF_LIA",
       "solver_profile": "logic",
   ...
       "status": "sat",
   ...
   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile tactic --json
   {
     "exit_code": 0,
   ...
       "ok": true,
   ...
       "property_satisfied": true,
   ...
       "solver_profile": "tactic",
   ...
       "status": "sat",
   ...

Each command exits ``0`` and prints ``result.status="sat"``,
``result.property_satisfied=true`` and ``replay.ok=true``. The requested
choice appears in ``result.solver_profile``. With no ``-o``, only stdout is
written; no file is created. Inspect ``result.solver_logic`` to distinguish
fragment selection from a fallback after no probe matched; above, the ``logic``
profile selected ``QF_LIA``.

Compare verdicts and replay before comparing cost. Different strategies can
choose different valid witnesses. Context-wide counters in
``solver_statistics`` are not per-query work. To measure your own model,
keep inputs and Python/Z3 versions fixed and repeat in fresh processes;
one faster invocation is not enough to change a default. The repository's
``benchmarks/bmc/solving/`` supplies four comparison arms, immutable raw
records and pre-registered performance thresholds.

``--solver-profile fast`` exits ``2``; use one of the three lowercase
choices:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --solver-profile fast
   Usage: pyfcstm bmc [OPTIONS]
   Try 'pyfcstm bmc --help' for help.

   Error: Invalid value for '--solver-profile': 'fast' is not one of 'default', 'logic', 'tactic'.
   $ echo $?
   2

If an optional profile returns an inconclusive answer, rerun with
``default`` and inspect ``reason`` rather than counting it as a property
pass. ``--explain-infeasibility formal`` or ``proof`` can accompany any
profile; explanation checks still use the default solver.

See :doc:`../../reference/bmc_results/index` for fields, fallback and budget
boundaries.

Try conservative slicing for one query
--------------------------------------

Slicing requires an explicit option.  This page's model has the abstract action
``Root.Idle.Tick``, so slicing skips the whole model and drops nothing:

.. code-block:: console

   $ pyfcstm bmc -i bmc_tasks.fcstm -q reach.fbmcq --cone-slicing --json
   {
     "exit_code": 0,
   ...
       "cone_slicing": {
         "dropped_variables": [],
         "enabled": true,
         "fallback": false,
         "retained_count": 1,
         "skipped_reason": "abstract_actions"
       },
   ...

Python compilation uses ``compile_bmc_query(model, query,
options=BmcOptions(cone_slicing=True))``; the file API accepts
``build_bmc_output(..., cone_slicing=True)``. Only bool values are accepted.

Slicing retains query references, guards, ordered operation conditions and
their dependencies. Assignments whose evaluation is not known total remain,
including division, modulo, powers, functions and floating-point arithmetic.
An integer declaration does not justify removing calculations that depend on
a temporary non-integer value inside an action. Any abstract action skips the
whole model. Unread outputs therefore cannot erase a dangerous calculation
and change scenario feasibility, including UNSAT results with no SAT witness
to replay.

Initial values and all variable symbols remain intact. Decoding completes
removed values through the original runtime, so every frame still contains
all variables. Deterministic traces with fixed initial values and events stay
equal; queries with multiple solutions may select another legal path. Both
the primary witness and a response incomplete suffix are verified before
solving returns. Verification failure retries the full model at most once
using the same remaining solver budget. Verification and rebuilding consume
that budget, but timeout does not forcibly interrupt those Python operations.

When enabled, inspect ``result.cone_slicing`` for removals, skip reasons and
``fallback``. Disabled results omit this field. ``total_elapsed_ms`` includes
internal verification and fallback; performance comparisons must also measure
compilation and external decoding/replay rather than excluding completion cost.

The measured correctness gate passes, but the 6.09% formula reduction misses
T3's 20% requirement, so slicing remains disabled by default. A query regresses
131.73% in solve time; compare compilation, solving and external replay costs
together. See :ref:`sec-bmc-cone-measurements` for the measured results.
