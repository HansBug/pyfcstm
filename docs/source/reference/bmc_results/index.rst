.. _sec-reference-bmc-results:

BMC CLI and Result Protocol Reference
=====================================

This page freezes the process and data contract of ``pyfcstm bmc``.  It covers
one FCSTM model and one FBMCQ query per invocation, the human report, the
``bmc-cli/v1`` JSON envelope, witness decoding, runtime replay, exit status,
errors, and the downloadable reference schema.  It is a bounded result
protocol: a successful bounded verdict is not an unbounded proof.

The source facts for this page are :mod:`pyfcstm.entry.bmc`, the
``bmc_cli_v1.schema.json`` maintained beside this page's reST source,
:mod:`pyfcstm.bmc.witness`, and the entry behavior tests.  The schema is authoritative for
JSON types and required keys; the entry module is authoritative for process
ordering, streams, file effects, and exit status.

Use the local contents below to look up the option surface, output transaction,
verdict matrix, human report, JSON envelope, witness, replay, errors, or
consumer rules.  For ``.fbmcq`` syntax and contextual legality, use
:doc:`../bmc_query/index` instead.

.. contents:: On this page
   :local:
   :depth: 2

The following comments are synchronization markers for the CLI reference
checker.  The English and Chinese pages intentionally carry identical marker
lines.

.. cli-ref-command: name=bmc
.. cli-ref-option: command=bmc option=-i
.. cli-ref-option: command=bmc option=--input-code
.. cli-ref-option: command=bmc option=-q
.. cli-ref-option: command=bmc option=--query-file
.. cli-ref-option: command=bmc option=-o
.. cli-ref-option: command=bmc option=--output
.. cli-ref-option: command=bmc option=--json
.. cli-ref-option: command=bmc option=--timeout-ms
.. cli-ref-option: command=bmc option=--max-bound
.. cli-ref-option: command=bmc option=--color choices=auto,always,never default=auto
.. cli-ref-option: command=bmc option=--help
.. cli-ref-boundary: command=bmc stdout stderr exit-status side-effects success-signal failure-taxonomy human json atomic-output witness replay dual-check response-cause packaging property-verdict color timing llm-consumption

Invocation and frozen option surface
------------------------------------

Both installed entry forms have the same behavior:

.. code-block:: console

   pyfcstm bmc -i machine.fcstm -q property.fbmcq [OPTIONS]
   python -m pyfcstm bmc -i machine.fcstm -q property.fbmcq [OPTIONS]

.. list-table:: Options
   :header-rows: 1
   :widths: 22 18 20 40

   * - Option
     - Value
     - Required/default
     - Exact behavior
   * - ``-i, --input-code``
     - Path text
     - Required
     - Loads one FCSTM model with the import-aware model loader.  There is no
       stdin form.
   * - ``-q, --query-file``
     - Path text
     - Required
     - Reads and auto-decodes one FBMCQ query file.  Inline query text, stdin,
       and multiple-query files are not CLI inputs.
   * - ``-o, --output``
     - Path text
     - Unset; stdout
     - Writes the completed human or JSON report to this UTF-8 file instead of
       stdout.  It atomically replaces an existing file and does not create a
       missing parent directory.
   * - ``--json``
     - Flag
     - False; human
     - Selects the stable ``bmc-cli/v1`` JSON envelope.  There is deliberately
       no overlapping ``--format`` option.
   * - ``--timeout-ms``
     - Integer, ``>= 1``
     - Unset; no Z3 timeout
     - Establishes one total budget shared by every staged Z3 ``check()`` in
       the public solve.  It does not limit loading, parsing, expansion,
       formula construction, witness decoding, or replay.
   * - ``--max-bound``
     - Integer, ``>= 1``
     - Unset; no CLI cap
     - Creates ``BmcOptions(max_bound=N)``.  A query bound above ``N`` is
       rejected before relation construction as a controlled compile error.
       It does not rewrite or clamp the query bound.
   * - ``--color``
     - ``auto``, ``always``, or ``never``
     - ``auto``
     - Controls ANSI decoration only for human output. ``auto`` requires a TTY,
       honors ``NO_COLOR``, and disables color for ``TERM=dumb``; ``always``
       may explicitly force color through a pipe. JSON and ``--output`` files
       are always ANSI-free.
   * - ``-h, --help``
     - Flag
     - Optional
     - Prints Click help and exits ``0`` without loading either input.

Zero and negative values for either numeric option are Click usage errors.
Missing required options and unknown options are also usage errors; all exit
``2``.  Paths are passed through as supplied and are also reproduced as
strings in JSON; the CLI does not canonicalize them to absolute paths.

Execution and output transaction
--------------------------------

One invocation follows this fixed order:

#. Load the import-aware FCSTM model.
#. Read and decode the FBMCQ file.
#. Compile exactly one query, applying ``--max-bound`` when supplied.
#. Solve the primary property objective.
#. When the primary result is UNSAT, check ``S_assume`` and, only when needed,
   ``S_init`` and ``K_N``.  Do not interpret an UNSAT objective as a property
   verdict until the admissible scenario is known to be feasible.
#. If the scenario is feasible and the property exposes a non-false
   incomplete-horizon formula, solve that diagnostic formula under the same
   total deadline.
#. If a SAT model is selected, decode it with the result-bound decoder into a
   ``bmc-witness/v2`` trace and replay it through ``SimulationRuntime`` with
   ``abstract_handlers=None``.  The legacy ``decode_bmc_witness`` API continues
   to emit ``bmc-witness/v1``.
#. Compute the final exit code, construct the entire report once, then write it
   to stdout or atomically replace ``--output``.
#. Exit with the same code recorded by JSON ``exit_code``.

No report is emitted before solve, mandatory SAT decode, and mandatory SAT
replay finish.  The CLI has no ``--no-replay`` or ``--no-incomplete-check``
escape hatch.  Abstract action calls are recorded, but the CLI does not inject
user handlers that mutate replay state or variables.

.. list-table:: Output routing and file effects
   :header-rows: 1
   :widths: 18 18 18 23 23

   * - Branch
     - stdout
     - stderr
     - ``--output``
     - Existing target
   * - Report-bearing verdict, no ``-o``
     - Complete report
     - Empty
     - Not used
     - Unchanged
   * - Report-bearing verdict with ``-o``
     - Empty
     - Empty
     - Complete report
     - Atomically replaced, even for exit ``1``, ``3``, or ``4``
   * - Controlled input/compile error
     - Empty
     - Concise Click error
     - Not created or modified
     - Preserved
   * - Click usage error
     - Empty
     - Usage and error text
     - Not created or modified
     - Preserved
   * - Internal solve/decode/replay failure
     - Empty
     - Unexpected-error banner and traceback
     - No partial report
     - Preserved
   * - Output write failure
     - Empty
     - Concise Click error
     - No successful payload
     - Original target is preserved when replacement was not completed

Atomic output means: create a temporary file in the target directory, encode
as UTF-8 with ``\n`` newlines, write, flush, ``fsync``, close, and call
``os.replace``.  Parent directories are not created.  On write or replacement
failure the implementation attempts to remove the temporary file; if cleanup
also fails, both failures are made observable.  Atomic replacement is a
same-filesystem file operation, not a multi-file transaction or a directory
durability guarantee.

Exit status and verdict matrix
------------------------------

Exit priority is replay mismatch ``4`` first, inconclusive ``3`` second, then
the bounded property verdict ``0`` or ``1``.  A deterministic negative result
is not a process/protocol error: it still emits a complete report.

.. list-table:: Process exit status
   :header-rows: 1
   :widths: 10 30 30 30

   * - Exit
     - Meaning
     - Report behavior
     - Repair/consumer action
   * - ``0``
     - The bounded property is satisfied and any mandatory SAT replay matched.
     - Complete human/JSON report.
     - Consume ``result.outcome``; do not generalize beyond the bound.
   * - ``1``
     - A deterministic bounded negative verdict, or a controlled input,
       compile, read, or write error, or an internal failure.
     - Negative verdict: complete report.  Controlled/internal error:
       stderr only.
     - Distinguish report-bearing ``result`` from stderr-only failure.
   * - ``2``
     - Click usage error.
     - Usage on stderr; no report.
     - Fix missing/unknown options or require positive integers.
   * - ``3``
     - Solver ``unknown``/``timeout``, feasibility inconclusive, scenario
       infeasible, or response horizon ``incomplete``.
     - Complete report.  Scenario-infeasible and inconclusive feasibility
       branches have null ``witness``/``replay``; a SAT suffix may have both.
     - Inspect ``result.outcome`` before choosing a larger timeout or bound.
   * - ``4``
     - SAT decoded successfully and replay returned a structured result with
       ``replay.ok == false``.
     - Complete result, witness, replay, and mismatches.
     - Treat the formal/runtime alignment as untrusted and inspect mismatches.

.. list-table:: Complete report-bearing branch matrix
   :header-rows: 1
   :widths: 17 14 18 22 12 17

   * - Property/objective branch
     - Primary status
     - ``result.outcome``
     - ``witness`` / ``replay``
     - Exit
     - Interpretation
   * - Witness polarity: ``reach``, ``exists_always``, ``cover``; objective SAT
     - ``sat``
     - ``witness_found``
     - object / object, replay ok
     - ``0``
     - Required bounded witness found.
   * - Witness polarity; objective UNSAT
     - ``unsat``
     - ``no_witness``
     - null / null
     - ``1``
     - No witness within the bound.
   * - Counterexample polarity: ``forbid``, ``invariant``, ``must_reach``,
       ``response``; objective SAT
     - ``sat``
     - ``property_violated``
     - object / object, replay ok
     - ``1``
     - Bounded counterexample found.
   * - Counterexample polarity, non-response; objective UNSAT
     - ``unsat``
     - ``property_satisfied``
     - null / null
     - ``0``
     - No counterexample within the bound.
   * - Response objective UNSAT; suffix check UNSAT or unnecessary
     - ``unsat``
     - ``property_satisfied``
     - null / null
     - ``0``
     - No complete-window violation and no uncovered tail trigger.
   * - Response objective UNSAT; suffix check SAT, unknown, or timeout
     - ``unsat``
     - ``incomplete``
     - null / null
     - ``3``
     - The bounded tail cannot support a definitive satisfaction verdict.
   * - Any primary objective unknown
     - ``unknown``
     - ``unknown``
     - null / null
     - ``3``
     - Solver gave no definitive result; ``reason`` explains why when available.
   * - Any primary objective timeout
     - ``timeout``
     - ``timeout``
     - null / null
     - ``3``
     - Per-check timeout reached.
   * - Any primary SAT; decode succeeds; replay returns mismatches
     - ``sat``
     - Polarity-derived value
     - object / object, replay not ok
     - ``4``
     - Replay trust gate overrides the property exit code.

Human report
------------

Human output reports the bounded property verdict before exposing solver
mechanics.  Its first line is exactly one of these shapes:

.. code-block:: text

   BMC <kind> <= <bound>: PROPERTY HOLDS
   BMC <kind> <= <bound>: PROPERTY DOES NOT HOLD
   BMC <kind> <= <bound>: PROPERTY INCONCLUSIVE
   BMC <kind> <= <bound>: REPLAY MISMATCH; PROPERTY VERDICT UNTRUSTED
   BMC <kind> <= <bound>: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED

The next sentence explains the polarity-aware outcome.  ``Solver`` then shows
the primary status and elapsed milliseconds; the configured shared timeout
budget, response horizon status/time, solver reasons, and diagnostics appear when
applicable.  SAT results add replay status and a compact trace whose rows show
``source -> target [case; events; calls]``.  Event and call previews retain the
first three values and report the omitted count.  Replay mismatches show every
path and message.

The final paragraph always states the bounded-result limitation and points to
``--json`` for the complete witness, runtime trace, mismatches, and stable
diagnostics.  Sections have exactly one blank line and the report has one
trailing newline.  With ``--color auto``, terminals use green for a holding
property, red for a non-holding property or replay mismatch, yellow for an
inconclusive result and bounded caveat, and cyan for diagnostic labels.  Color
never enters JSON or files.  Scripts and LLM integrations must consume
``--json`` rather than parse human wording, ANSI, or live timing.

JSON envelope
-------------

JSON is UTF-8, pretty-printed with two-space indentation, recursively sorted
keys, non-ASCII characters preserved, and one trailing newline.  Every object
in the schema rejects undeclared keys where ``additionalProperties`` is false.
Raw Z3 models and complete SMT formulas are deliberately excluded.

.. list-table:: Top-level ``bmc-cli/v1`` fields
   :header-rows: 1
   :widths: 20 22 15 43

   * - Field
     - Type/allowed value
     - Always present
     - Meaning
   * - ``schema_version``
     - string, exactly ``bmc-cli/v1``
     - Yes
     - Version discriminator for this envelope.
   * - ``input``
     - object
     - Yes
     - ``model_path`` and ``query_path`` are the supplied path strings.
   * - ``property``
     - object
     - Yes
     - Compiled property identity: ``kind``, ``polarity``, ``bound``, optional
       ``case_label``, and response-only ``response_window``.
   * - ``result``
     - object
     - Yes
     - Canonical ``BmcSolveResult`` summary.
   * - ``witness``
     - object or null
     - Yes
     - ``bmc-witness/v2`` for a CLI-selected primary or suffix model; null when
       no model role is available.
   * - ``replay``
     - object or null
     - Yes
     - Runtime replay result for a selected model role; null otherwise.
   * - ``exit_code``
     - one of ``0, 1, 3, 4``
     - Yes
     - Exact process exit mirror for report-bearing branches.  Usage and
       stderr-only failures do not produce an envelope.

``property.kind`` is one of ``reach``, ``forbid``, ``invariant``,
``must_reach``, ``exists_always``, ``response``, or ``cover``.
``property.polarity`` is ``witness`` or ``counterexample``.  ``bound`` is an
integer of at least 1.  ``case_label`` is string or null.  ``response_window``
is a positive integer for response and null for other kinds.

.. list-table:: ``result`` fields
   :header-rows: 1
   :widths: 24 24 52

   * - Field
     - Type/values
     - Contract
   * - ``node``
     - exactly ``bmc_solve_result``
     - Canonical node discriminator.
   * - ``schema_version``
     - exactly ``bmc-solve-result/v2`` at runtime
     - Nested result version.  The outer envelope remains ``bmc-cli/v1``.
   * - ``kind``, ``polarity``
     - same closed sets as ``property``
     - Identity copied from the solved formula.
   * - ``status``
     - ``sat``, ``unsat``, ``unknown``, ``timeout``
     - Primary objective solver status, not directly a universal success flag.
   * - ``property_satisfied``
     - boolean or null
     - Polarity-aware bounded verdict; null for inconclusive results.
   * - ``witness_found``
     - boolean
     - True exactly for SAT witness-polarity objectives.
   * - ``counterexample_found``
     - boolean
     - True exactly for SAT counterexample-polarity objectives.
   * - ``incomplete``
     - boolean
     - True for primary unknown/timeout or unresolved response horizon.
   * - ``outcome``
     - ``property_satisfied``, ``property_violated``, ``witness_found``,
       ``no_witness``, ``incomplete``, ``timeout``, ``unknown``,
       ``scenario_infeasible``, ``feasibility_timeout``,
       ``feasibility_unknown``
     - Stable consumer-facing classification; use this with ``exit_code``.
   * - ``reason``
     - string or null
     - Raw reason only for primary unknown/timeout; null for SAT/UNSAT.
   * - ``elapsed_ms``
     - finite number, ``>= 0``
     - Primary check wall time; inherently nondeterministic.
   * - ``timeout_ms``
     - positive integer or null
     - One total timeout budget shared by every staged check in this invocation.
   * - ``has_model``
     - boolean
     - True exactly when a primary SAT model existed; the raw model is absent.
   * - ``incomplete_status``
     - status enum or null
     - Separate incomplete-horizon check status.
   * - ``incomplete_reason``
     - string or null
     - Inconclusive secondary-check reason; null for secondary SAT/UNSAT.  The
       CLI always enables this check when the formula exposes it.
   * - ``has_incomplete_model``
     - boolean
     - True exactly for a secondary SAT model; the raw model is absent.
   * - ``incomplete_elapsed_ms``
     - finite number or null
     - Secondary check time, when that check actually ran.
   * - ``total_elapsed_ms``
     - finite number, ``>= 0``
     - End-to-end Python-side public-solve interval, including staged-result construction.
   * - ``feasibility``
     - object
     - Stage evidence for ``K_N``, ``S_init`` and ``S_assume``.  A checked
       ``unknown``/``timeout`` never becomes ``scenario_infeasible``.
   * - ``available_model_roles``
     - array of closed role strings
     - ``primary_witness``, ``primary_counterexample`` or
       ``incomplete_suffix``.
   * - ``diagnostics``
     - array of strings
     - Solver/formula diagnostics; may contain nondeterministic
       ``incomplete_elapsed_ms=...``.

Golden tests should fix or range-check ``elapsed_ms`` and the secondary timing
diagnostic rather than exact-comparing live time.  Key sets, enums, nullability,
and all other stable values remain suitable for exact checks.

Feasibility and model roles
---------------------------

``result.outcome == "scenario_infeasible"`` means ``S_assume`` was proven
unsatisfiable.  It is not a property failure: ``property_satisfied`` is
``null``, no model role is available, and response suffix solving is skipped.
When ``S_assume`` is satisfiable, a primary SAT model is classified as either
``primary_witness`` or ``primary_counterexample``.  A response primary UNSAT
followed by a SAT ``Psi_q`` check is classified as ``incomplete_suffix``; its
trace is useful for replaying the finite prefix but its detached verdict stays
``incomplete``.

``timeout_ms == null`` means no Z3 timeout is installed.  A finite value is a
single total budget shared by primary, feasibility, localization, and suffix
checks; a later check is not started after the budget is exhausted.

The schema preserves the evidence boundary for localized infeasibility.  An
``infeasible_stage == "initialization"`` result requires a checked SAT
``kernel`` prefix and checked UNSAT ``initialization`` evidence.  An
``infeasible_stage == "assumptions"`` result requires a SAT ``kernel`` prefix
(which may be inferred), checked SAT ``initialization`` evidence, and checked
UNSAT ``assumptions`` evidence.  ``origin == "inferred"`` therefore records a
SAT fact implied by a trusted stronger result; it cannot replace a solver check
needed to distinguish the first infeasible stage.

For a v2 result with a non-empty ``available_model_roles`` array, both the
``witness`` and ``replay`` objects must be v2 objects carrying exactly the same
role as the result.  An empty role array requires both objects to be ``null``.
This keeps the external envelope from combining evidence from different model
channels even when each individual object is structurally valid.

Witness fields
--------------

CLI-emitted ``witness`` uses ``schema_version == "bmc-witness/v2"`` and adds
root ``model_role`` and ``verdict`` fields.  The legacy
``decode_bmc_witness`` compatibility API continues to produce v1.  In v2,
``model_role`` is at the trace root, never nested under ``solver``.

.. list-table:: Witness root and nested records
   :header-rows: 1
   :widths: 24 25 51

   * - Path/record
     - Fields
     - Meaning and constraints
   * - ``witness.property``
     - ``kind``, ``polarity``, ``bound``, ``case_label``, ``response_window``
     - Same property shape as the envelope.
   * - ``witness.solver``
     - ``model_status``, ``primary_status``, ``incomplete_status``, timing and
       reason fields
     - The selected model status is SAT.  For ``incomplete_suffix``, primary is
       UNSAT and incomplete is SAT; completed SAT/UNSAT checks have null reason.
   * - ``witness.model_role`` and ``witness.verdict``
     - closed role and detached verdict objects
     - The role/verdict combination is validated together; suffix replay cannot
       be promoted to a property verdict.
   * - ``witness.initial``
     - ``mode``, ``state``, ``sentinel``, ``vars``
     - Replay initialization metadata.  State may be null; sentinel is
       ``init``, ``terminated``, or null; vars is a JSON-stable map.
   * - ``witness.frames[]``
     - ``index``, ``state_id``, ``state``, ``sentinel``, ``terminated``, ``vars``
     - Decoded symbolic frames.  Sentinel frames have null state id/path;
       ``terminated`` agrees with the sentinel.
   * - ``witness.steps[]``
     - ``index``, ``source_frame``, ``target_frame``, ``case_label``,
       ``case_kind``, ``progress``, ``source_state``, ``target_state``,
       ``delta``, ``gamma``, ``input_events``, ``event_reads``,
       ``abstract_calls``, ``consumed_events``, ``unconsumed_events``
     - One decoded macro-step.  Source/target states may be null for sentinels.
       Event consumption is ordered; unconsumed events equal replay inputs minus
       consumed events.
   * - ``witness.diagnostics``
     - array of strings
     - Decode diagnostics.

Each event object has ``path`` (qualified event path), ``reason`` (decode
provenance), and boolean ``model_value``.  Replay ``input_events`` contain only
true events with reason ``case_positive``, ``explicit_true_assumption``, or
``property_support``.  Debug ``event_reads`` use
``negative_case_read``, ``explicit_false_assumption``, or ``model_debug`` and
are not replay inputs.

Each abstract call record has ``ordinal``, ``action_name``, ``stage``, ``role``,
``state``, ``active_leaf``, nullable ``named_ref``, and pre-call variable
``snapshot``.  The CLI records these calls during replay but supplies no user
handler behavior.  JSON-stable maps permit null, booleans, finite numbers,
strings, arrays, and nested string-keyed objects; non-finite numbers and raw
Python/Z3 objects are not public JSON values.  The schema's reusable
``stringMap`` is deliberately broad, while the current witness emitters
constrain frame/runtime ``vars`` and call ``snapshot`` values to finite integers
or floats.  Consumers may rely on schema validity but should not manufacture a
trace and assume every schema-wide value is accepted by the Python constructors.

Replay fields and trust boundary
--------------------------------

``replay.ok`` is true exactly when ``mismatches`` is empty.  The complete
replay object contains:

.. list-table:: Replay records
   :header-rows: 1
   :widths: 25 28 47

   * - Path/record
     - Fields
     - Meaning
   * - ``replay``
     - ``ok``, ``runtime_trace``, ``mismatches``
     - Structured alignment verdict, runtime observations, and all mismatches.
   * - ``runtime_trace.frames[]``
     - ``index``, ``state``, ``terminated``, ``vars``
     - Public runtime frame after replay; unlike witness frames it has no
       symbolic ``state_id`` or sentinel field.
   * - ``runtime_trace.steps[]``
     - ``index``, ``input_events``, ``consumed_events``,
       ``unconsumed_events``, ``abstract_calls``
     - Actual runtime event accounting and recorded abstract calls.
   * - ``mismatches[]``
     - ``path``, ``expected``, ``actual``, ``message``, ``tolerance``
     - One comparison failure.  Expected/actual are JSON values; tolerance is a
       non-negative number or null.

Replay is a runtime-alignment oracle for the decoded bounded trace.  It is not
an independent unbounded proof, and success does not validate arbitrary user
abstract-handler implementations because the CLI uses ``abstract_handlers=None``.
Only a returned ``BmcReplayResult`` with mismatches produces exit ``4``.  An
exception before such a result exists is an internal failure, has exit ``1``,
prints a traceback, and emits no partial JSON/human report.

Dual checks and the response cause boundary
-------------------------------------------

Every property performs one primary check.  Only a formula with a non-false
incomplete-horizon observation performs a second check; this is currently the
non-trivial response case.  All staged checks consume one shared total
``--timeout-ms`` budget.  A later check receives only the remaining budget and
is not started after the deadline is exhausted.

.. list-table:: Response two-check interpretation
   :header-rows: 1
   :widths: 18 20 20 16 26

   * - Primary
     - Secondary incomplete check
     - Result
     - Exit
     - Notes
   * - SAT
     - Any/not decisive
     - ``property_violated``
     - ``1`` or replay ``4``
     - A complete counterexample already decides the property.
   * - UNSAT
     - UNSAT or formula false
     - ``property_satisfied``
     - ``0``
     - No complete violation and no uncovered suffix trigger.
   * - UNSAT
     - SAT
     - ``incomplete``
     - ``3``
     - An uncovered trigger window can extend beyond the bound.
   * - UNSAT
     - unknown or timeout
     - ``incomplete``
     - ``3``
     - The suffix diagnostic is inconclusive.
   * - unknown/timeout
     - Any
     - ``unknown``/``timeout``
     - ``3``
     - Primary objective itself is inconclusive.

A response counterexample may arise because the trigger is undefined or
because a defined trigger has no response in its complete window.  Both are
part of the same counterexample objective and both currently produce SAT,
``property_violated``, and exit ``1`` when replay matches.  Neither
``result.outcome`` nor ``bmc-witness/v2`` exposes a stable machine-readable
``cause`` discriminator.  Humans may inspect the query and trace; scripts must
not infer or depend on a cause classification that the protocol does not have.

Error taxonomy
--------------

.. list-table:: Failures and observability
   :header-rows: 1
   :widths: 22 34 28 8 8

   * - Category
     - Sources
     - Observable contract
     - Exit
     - Report
   * - Click usage
     - Missing required option, unknown option, non-integer or nonpositive
       numeric value
     - Usage/error on stderr
     - ``2``
     - No
   * - Controlled model input
     - Missing primary model, filesystem/permission error, decode error,
       FCSTM grammar error, model validation error
     - Concise stderr beginning with the controlled model operation
     - ``1``
     - No
   * - Controlled query input
     - Missing/read/decode failure for the FBMCQ file
     - Concise stderr
     - ``1``
     - No
   * - Controlled BMC compile input
     - Query parse/bind error, unsupported query, user-caused domain/encoding/
       build validation, ``max_bound`` policy rejection
     - ``Failed to compile BMC query: ...`` on stderr
     - ``1``
     - No
   * - Deterministic negative verdict
     - No witness for witness polarity, or SAT counterexample
     - Complete selected-format report; stderr empty
     - ``1``
     - Yes
   * - Inconclusive verdict
     - Solver unknown/timeout, response horizon incomplete
     - Complete selected-format report; stderr empty
     - ``3``
     - Yes
   * - Structured replay mismatch
     - Decode succeeded and replay returned one or more mismatches
     - Complete result+witness+replay report
     - ``4``
     - Yes
   * - Output failure
     - Temporary creation, UTF-8 write, flush/fsync, replace, or cleanup failure
     - ``Failed to write BMC output file ...`` on stderr
     - ``1``
     - No successful report
   * - Internal consistency failure
     - Internal BMC sentinel, solve invariant failure, witness decode exception,
       replay exception, or another unexpected exception
     - Unexpected-error banner and traceback; bug sentinel retained
     - ``1``
     - No

The recognized internal BMC text sentinels are ``internal BMC bug:``,
``internal error:``, and ``internal BMC witness consistency error``.  They are
not downgraded to user input errors.  Exit ``4`` must never be used for an
exception: it means a fully constructed, inspectable mismatch result.

Reproducible examples
---------------------

Assume ``machine.fcstm`` contains ``state Root;``.  Each command uses a query
file containing exactly the shown statement.

**Example 1: positive witness.**  Put
``check reach <= 1: active("Root");`` in ``reach.fbmcq``:

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q reach.fbmcq --json
   {
     "exit_code": 0,
     ...
     "result": {"outcome": "witness_found", "status": "sat", ...},
     "replay": {"mismatches": [], "ok": true, ...},
     "witness": {"schema_version": "bmc-witness/v2", "model_role": "primary_witness", ...}
   }

The excerpt is schematic because sorted pretty JSON places keys between these
lines and live timing varies.  The complete payload validates against the
downloadable reference schema.

**Example 2: a counterexample is a negative verdict, not a CLI error.**  Put
``check forbid <= 1: active("Root");`` in ``forbid.fbmcq``:

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q forbid.fbmcq --json > result.json
   $ echo $?
   1

``result.json`` is complete: ``status`` is ``sat``, ``outcome`` is
``property_violated``, and witness/replay are objects.  stderr is empty.

**Example 3: response horizon incomplete.**  Put
``check response <= 1: trigger true -> within 2 false;`` in
``response.fbmcq``:

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q response.fbmcq --json -o response.json
   $ echo $?
   3

stdout and stderr are empty; ``response.json`` has primary ``status: unsat``,
``incomplete_status: sat``, ``outcome: incomplete``, and ``exit_code: 3``.
Because the suffix model is available, ``witness`` and ``replay`` are objects
with ``bmc-witness/v2`` and ``model_role: incomplete_suffix``; they describe
only the executable prefix and do not turn the detached result into a
property verdict.  Increase the bound if a definitive horizon is required.

**Example 4: policy rejection is stderr-only and preserves output.**  Put
``check reach <= 2: active("Root");`` in ``large.fbmcq`` and assume
``result.json`` already exists:

.. code-block:: console

   $ pyfcstm bmc -i machine.fcstm -q large.fbmcq --max-bound 1 \
       --json -o result.json
   Error: Failed to compile BMC query: max_bound policy rejected query_bound=2 with max_bound=1. ...

The command exits ``1``; it emits no JSON and leaves the old ``result.json``
unchanged.  A missing parent directory for ``-o`` similarly fails instead of
being created.

Schema download and consumer checks
-----------------------------------

:download:`Download the normative bmc-cli/v1 JSON Schema
<bmc_cli_v1.schema.json>`.

The schema is a reference artifact, not a runtime dependency.  Sphinx publishes
it through the download link above; do not infer a schema URL from this page's
rendered URL.  It deliberately is not shipped inside ``pyfcstm`` wheels, source
distributions, or standalone executables.  Consumers that need structural
validation should download or vendor the versioned schema with their integration
and load that local copy:

.. code-block:: python

   import json
   from pathlib import Path

   schema = json.loads(
       Path("bmc_cli_v1.schema.json").read_text(encoding="utf-8")
   )

With ``jsonschema``, validate the schema itself as Draft 2020-12 and then
validate representative envelopes for all report-bearing matrix branches.
The tools-only BMC documentation check validates the artifact and rejects any
copy under ``pyfcstm/entry``.  The schema's ``$id`` is an identifier; consumers
should not require network access to fetch it at validation time.

Consumer rules
--------------

* Branch first on process exit and the presence of a JSON report.  Exit ``1``
  alone cannot distinguish a negative verdict from stderr-only failure.
* When JSON exists, require ``schema_version == "bmc-cli/v1"`` and verify
  ``payload.exit_code`` equals the process exit status.
* Use ``result.outcome`` and ``result.polarity``; never interpret SAT as a
  universal success.
* Treat exit ``3`` as one process category but distinguish timeout, unknown,
  feasibility failure, scenario infeasibility, and response incomplete before
  changing timeout or bound.  A suffix model may still be present on an
  incomplete response result.
* Treat exit ``4`` as an inspectable trust failure.  Do not conflate it with an
  exception or a property counterexample.
* Do not parse human tables, depend on live elapsed time, expect raw models or
  formulas, infer a response cause, or assume replay proves behavior beyond the
  decoded bounded trace.
