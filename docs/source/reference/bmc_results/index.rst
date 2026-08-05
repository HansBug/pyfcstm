.. _sec-reference-bmc-results:

BMC CLI and Result Protocol Reference
=====================================

This page freezes the process and data contract of ``pyfcstm bmc``.  It covers
one FCSTM model and one FBMCQ query per invocation, the human report, the
structured JSON envelope, witness decoding, runtime replay, exit status,
errors, and the downloadable reference schema.  It is a bounded result
protocol: a successful bounded verdict is not an unbounded proof.

The source facts for this page are :mod:`pyfcstm.entry.bmc`, the
``bmc_cli.schema.json`` maintained beside this page's reST source,
:mod:`pyfcstm.bmc.witness`, and the entry behavior tests.  The schema is authoritative for
JSON types and required keys; the entry module is authoritative for process
ordering, streams, file effects, and exit status.

The schema is versioned by the release it ships with, not by its own field.  Its
``$id`` names a path on the ``main`` branch, which moves, and neither the schema nor
the JSON output carries a version number.  Validate against the copy that shipped
with the ``pyfcstm`` you are running: ``additionalProperties: false`` promises that
*this* version emits no undeclared field, not that the field set is the same across
versions.  A release may add one.  The bounded-model-checking explanation surface added
``explanation`` to the two definitions that close themselves to unknown fields --
``feasibility`` and ``notCheckedFeasibility`` -- and made it required in both, so an
earlier copy of this schema rejects the output of this one at either.  Everything
else it added is a definition that copy does not have at all, which no consumer was
validating against.

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
.. cli-ref-option: command=bmc option=--explain-infeasibility choices=none,formal,proof default=none
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
     - Selects the structured JSON envelope.  There is deliberately
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
   * - ``--explain-infeasibility``
     - ``none``, ``formal``, or ``proof``
     - ``none``
     - Requests the optional scenario-infeasibility explanation at the given
       depth.  ``none`` performs no additional solver work and leaves
       ``explanation`` null with ``refinement_status`` as ``not_requested``.
       ``formal`` publishes the classification and a sound source core;
       ``proof`` additionally builds a step-by-step proof and publishes it when
       every step was checked, and degrades to ``formal`` when no rule in the
       catalog closes the core.  The achieved depth is always reported, so a
       caller can tell the two apart.  The depth never changes the mandatory
       verdict.
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
   role-aware trace and replay it through ``SimulationRuntime`` with
   ``abstract_handlers=None``.  The raw-model ``decode_bmc_witness`` API omits
   the result-bound ``model_role`` and ``verdict`` fields.
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
   * - Response objective UNSAT; suffix check SAT
     - ``unsat``
     - ``incomplete``
     - object / object, replay ok
     - ``3``
     - The detached ``incomplete_suffix`` model supplies finite-prefix evidence; it does not establish a property verdict.
   * - Response objective UNSAT; suffix check unknown or timeout
     - ``unsat``
     - ``incomplete``
     - null / null
     - ``3``
     - The suffix check produced no model, so the bounded tail cannot support a definitive satisfaction verdict.
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
     - The shared solve budget was exhausted before a conclusive primary result.
   * - Any primary SAT; decode succeeds; replay returns mismatches
     - ``sat``
     - Polarity-derived value
     - object / object, replay not ok
     - ``4``
     - Replay trust gate overrides the property exit code.

Human report
------------

Human output reports the bounded property verdict before exposing solver
mechanics.  Its first line is polarity-aware and identifies whether the
result is a witness, a counterexample, a bounded guarantee, an empty scenario,
or an inconclusive check:

.. code-block:: text

   BMC <kind> <= <bound>: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   BMC <kind> <= <bound>: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS
   BMC <kind> <= <bound>: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   BMC <kind> <= <bound>: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   BMC <kind> <= <bound>: PROPERTY INCONCLUSIVE; PRIMARY CHECK UNKNOWN
   BMC <kind> <= <bound>: PROPERTY INCONCLUSIVE; PRIMARY CHECK TIMED OUT
   BMC <kind> <= <bound>: PROPERTY INCONCLUSIVE; RESPONSE HORIZON INCOMPLETE
   BMC <kind> <= <bound>: SCENARIO FEASIBILITY UNKNOWN; PROPERTY NOT EVALUATED
   BMC <kind> <= <bound>: SCENARIO FEASIBILITY TIMED OUT; PROPERTY NOT EVALUATED
   BMC <kind> <= <bound>: SCENARIO FEASIBILITY NOT CHECKED; PROPERTY NOT EVALUATED
   BMC <kind> <= <bound>: SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED
   BMC <kind> <= <bound>: EVIDENCE/REPLAY MISMATCH; RESULT UNTRUSTED

The first report block then contains ``Scenario``, ``Property verdict``,
``Semantic interpretation``, and ``Primary search``.  ``Property verdict`` is
the direct bounded conclusion:
``SATISFIED WITHIN BOUND`` means the requested property outcome was established,
``NOT SATISFIED WITHIN BOUND`` means a required witness was absent or a
counterexample was found, ``NOT EVALUATED`` means scenario feasibility did not
permit a property verdict, and ``INCONCLUSIVE`` means the bounded search did
not finish with a property verdict.  The parenthetical text preserves whether
the evidence was a witness, a missing witness, a counterexample, or an
exception state.  A
response query also contains ``Response horizon``; non-response queries omit
that line.  ``Conclusion`` states the quantifier-aware user result.  When
there is SAT evidence, ``Evidence`` identifies ``PRIMARY WITNESS``,
``PRIMARY COUNTEREXAMPLE``, or ``INCOMPLETE SUFFIX`` and reports replay.  An
empty scenario reports ``Failure boundary`` as ``KERNEL``, ``INITIALIZATION``,
``ASSUMPTIONS``, or ``NOT LOCALIZED``; this is a cumulative boundary, not an
unsat core and not proof that one source clause is internally contradictory.
For a checked feasibility timeout, ``Scenario`` is ``TIMED OUT``; for a checked
feasibility unknown it is ``UNKNOWN``.  If the shared budget expires before the
assumptions stage starts, it is ``NOT CHECKED``.  An open response horizon is a
valid SAT suffix result rather than a solver exception, and its ``Evidence``
includes a ``Horizon reason`` explaining that the response obligation extends
beyond the current bound.

For the shared-budget case, the matching property line is
``Property verdict: NOT EVALUATED (SCENARIO FEASIBILITY NOT CHECKED)``.  A
feasibility check that actually starts and times out instead keeps
``NOT EVALUATED (SCENARIO FEASIBILITY TIMED OUT)``.

``Semantic interpretation`` states the logical meaning without requiring the
reader to combine the solver status with the property polarity.  It explicitly
separates an unsatisfiable scenario from an unsatisfiable property objective:
the former means that no admissible execution exists and the property was not
evaluated; the latter is meaningful only after the scenario is feasible.  For a
counterexample-polarity objective, an unsatisfiable counterexample objective is
therefore reported as every admissible execution satisfying the property within
the bound.  For a witness-polarity objective, it is reported as no satisfying
execution existing within the bound.  This is still a bounded statement, not
an unbounded theorem.

``GOAL UNREALIZABLE WITHIN BOUND`` is reserved for a witness-polarity objective
whose feasible bounded scenario contains no satisfying execution.  Its
separate ``Property verdict: NOT SATISFIED WITHIN BOUND (NO WITNESS)`` line
records the same bounded negative verdict as ``property_satisfied: false``;
the headline identifies the evidence form and does not claim that a concrete
counterexample trace was found.  ``PROPERTY GUARANTEED WITHIN BOUND`` is
reserved for a counterexample-polarity objective with no bounded counterexample.

``Solver`` then shows the primary status and elapsed milliseconds; the
configured shared timeout budget, response horizon status/time, solver reasons,
and low-level diagnostics appear when applicable.  SAT results add a compact
trace whose rows show ``source -> target [case; events; calls]``.  Event and
call previews retain the first three values and report the omitted count.
Replay mismatches show every path and message.  ``PROPERTY GUARANTEED WITHIN
BOUND`` means that the scenario is feasible and every admissible execution in
the stated bound has no counterexample; it is not an unbounded theorem.

The final paragraph always states the bounded-result limitation and points to
``--json`` for the complete witness, runtime trace, mismatches, and stable
diagnostics.  Sections have exactly one blank line and the report has one
trailing newline.  With ``--color auto``, terminals use green for a witness or
bounded guarantee, red for a missing witness, counterexample, or replay
mismatch, yellow for an empty/unknown/incomplete scenario and the bounded
caveat, and cyan for report labels.  Color never enters JSON or files.  Scripts
and LLM integrations must consume ``--json`` rather than parse human wording,
ANSI, or live timing.

Explanation block
~~~~~~~~~~~~~~~~~

``--explain-infeasibility formal`` or ``proof`` appends an explanation block to
the human report.  ``BmcSolveResult.__str__()`` and ``to_text()`` render the same
block from the same helper, so a reader sees identical text whichever surface
they read.  A real invocation against an infeasible scenario produces:

.. code-block:: text

   Explanation: PARTIAL FORMAL DOMAIN EXPLANATION
   Classification: assumptions conflict with the feasible prefix

   Conflict constraints:
     1. r22.fbmcq:2:1-2:28
        assume at 1: var("x") == 0;
     2. r22.fbmcq:1:1-1:35
        init state("Root.A") where x == 0;
     3. r22.fcstm:1:1-1:15
        def int x = 0;
     4. generated transition constraint at step 0

   The displayed core is sufficient for UNSAT but is not proven subset-minimal.
   Core scope: assumptions_prefix
   Reduction: raw
   Reason: sound source core published without a minimality proof


``Explanation`` names the depth that was achieved and how complete it is.
``Classification`` is the reader-facing sentence for the machine
``classification`` field.  Each conflict-constraint entry gives an authored
member's location and its own source text on two lines, or a generated support
group naming the leading segment of its category -- ``domain``, ``transition``,
``initial``, ``assumption`` or ``definedness`` -- and the frame or step it
constrains.  A generated group takes one line, plus a second indented line
listing any builder metadata that is not already in the position, which the
tracked case groups do carry.

The category segment is used rather than the aggregate formula the group belongs
to because the aggregate vocabulary is too small: it offers ``domain``,
``transition``, ``initial`` and ``environment``, while the groups the builder
emits need five nouns, and two of those are not aggregate names.  An assumption
group's aggregate is ``environment``, a word that appears nowhere else in the
report, and a definedness group's aggregate is ``initial`` or ``environment``
depending on which stage emitted it, naming neither the group nor anything stable
across the two.  ``Core scope`` and ``Reduction`` describe what was proven and how
far minimization got, and ``Reason`` states why it stopped there.

An additional line appears when a deeper depth was requested than was achieved,
so a caller who asked for ``proof`` and received ``formal`` is told both:

.. code-block:: text

   Explanation depth: requested proof, achieved formal

Every core reports its scope and its reduction, whether or not minimality was
proven; the sentence above the scope is what distinguishes the two.  Granularity,
member count, a labelled minimality line and the elapsed explanation time belong
to the fuller published block, which also carries a narrative and a causal chain
this depth does not build, so they do not appear here.


Classification and core reduction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``classification`` names which part of the scenario the conflict lies in.  The
list is closed, and the report prints the reader-facing phrase rather than the
machine value:

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - ``classification``
     - Printed phrase
   * - ``kernel_conflict``
     - the model's own domain and transition rules conflict
   * - ``initialization_self_conflict``
     - initialization is internally inconsistent
   * - ``initialization_domain_conflict``
     - initialization conflicts with the frame domain
   * - ``initialization_kernel_conflict``
     - initialization conflicts with the transition relation
   * - ``assumptions_self_conflict``
     - the assumptions are internally inconsistent
   * - ``assumptions_domain_conflict``
     - the assumptions conflict with the frame domain
   * - ``assumptions_prefix_conflict``
     - assumptions conflict with the feasible prefix

The two families differ in what the reader should change.  An
``initialization_*`` conflict means the ``init`` clause cannot be satisfied at
all, or cannot be satisfied and then continued; an ``assumptions_*`` conflict
means the ``assume`` clauses are the ones that leave nothing admissible.  A
``kernel_conflict`` implicates neither, and points at the model itself.

``reduction`` says how far minimization got before the core was published:

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - ``reduction``
     - Meaning
   * - ``raw``
     - The solver's own core, sound for UNSAT but not shrunk.
   * - ``partial_minimized``
     - Some members were proven removable and dropped, but the budget ran out
       before every remaining member had been tested.
   * - ``subset_minimal``
     - Every remaining member was tested and none can be dropped.

``subset_minimality`` is the claim itself, ``proven`` or ``not_proven``, and only
``subset_minimal`` carries ``proven``.  The distinction matters to a reader
deciding what to edit: a ``raw`` core may contain members that are not part of
the conflict at all.


Proof block
~~~~~~~~~~~

The block appears at all only when there is something to explain: the scenario
must be infeasible and a depth above ``none`` must have been requested.  A
feasible scenario has no conflict, and ``none`` asked for no explanation, so
neither prints a headline -- looking for one there and finding nothing is the
expected result rather than a missing field.

When the block does appear, its headline is built from two facts rather than
chosen from a list, and the rule covers every case:

**When something was produced**, the headline names the depth that was *achieved*
and how complete it is -- ``COMPLETE`` or ``PARTIAL``, then ``FORMAL DOMAIN
EXPLANATION`` or ``VERIFIED DOMAIN PROOF``.

**When nothing was produced** -- ``achieved_mode`` of ``none`` -- there is no
achieved depth to name, so the headline names the depth that was *requested*,
followed by ``NOT ACHIEVED``.

Four runs against the benchmark corpus, covering both halves of the rule:

.. code-block:: console

   $ pyfcstm bmc -i latch.fcstm -q two_values.fbmcq \
       --explain-infeasibility proof --color never
   Explanation: COMPLETE VERIFIED DOMAIN PROOF

   $ pyfcstm bmc -i latch.fcstm -q two_values.fbmcq \
       --explain-infeasibility formal --color never
   Explanation: COMPLETE FORMAL DOMAIN EXPLANATION

   $ pyfcstm bmc -i latch.fcstm -q cross_step.fbmcq \
       --explain-infeasibility proof --color never
   Explanation: PARTIAL FORMAL DOMAIN EXPLANATION
   Explanation depth: requested proof, achieved formal
   Reason: the formal explanation is complete, but no rule in the catalog closes
   this core.

   $ pyfcstm bmc -i latch.fcstm -q two_values.fbmcq \
       --explain-infeasibility proof --color never --timeout-ms 1
   Explanation: PROOF EXPLANATION NOT ACHIEVED

   $ pyfcstm bmc -i latch.fcstm -q two_values.fbmcq \
       --explain-infeasibility formal --color never --timeout-ms 1
   Explanation: FORMAL EXPLANATION NOT ACHIEVED
   Reason: component probe did not start: budget exhausted before the probe
   started; ...

Applying the rule to the pairing not shown: a proof that was built but reported
``partial`` would open on ``PARTIAL VERIFIED DOMAIN PROOF``, since ``proof`` is
what was achieved and ``partial`` is how complete it is.

No run is shown for it because the current implementation does not produce it,
and that is a stronger statement than the corpus lacking a case.  Of the nine
places that build a ``BmcInfeasibilityExplanation``, exactly one sets
``achieved_mode="proof"``, and it sets ``status="complete"`` alongside: a proof
either closes or the result degrades to ``formal``.  So the pairing is admitted
by the frozen delivery table and named by the rule, but nothing emits it today.
Read the row as the rule's answer for a shape the depth ladder reserves, not as
an output you should expect to see.

The middle case is the one that surprises: a request for ``proof`` that degrades
shows a ``FORMAL`` headline, because ``formal`` is what was achieved.  The last
case shows ``PROOF`` in the headline while no proof exists, because nothing was
achieved and the request is all there is to name.

``Explanation depth:`` appears only when the headline leaves the pair ambiguous,
which is exactly the degrading case -- the headline names the achieved depth and
the line supplies the requested one.  It is absent from the ``NOT ACHIEVED``
shape, where the headline already names the request, and absent when the request
was met.  A consumer should therefore compare ``requested_mode`` with
``achieved_mode`` in JSON rather than looking for that line, which is present
only in one of the three shapes.

``COMPLETE`` at ``formal`` depth means the formal explanation produced everything
it promises -- a classification and a source core -- not that a proof was found.
Reading it as "the tool is done" is the mistake this table exists to prevent.

The last row is the one to read carefully.  When ``achieved_mode`` is ``none``
nothing was produced to name, so the headline reports the *requested* depth with
``NOT ACHIEVED`` -- meaning a request for ``proof`` that reaches nothing shows
``PROOF EXPLANATION NOT ACHIEVED``, even though no proof exists.  A request that
degrades to ``formal`` is the other case: something was produced, so the achieved
depth names it and a ``FORMAL`` headline appears.  Either way the
``Explanation depth:`` line reports the difference, and it is the reliable field
to branch on.


``--explain-infeasibility proof`` builds a proof and publishes it when every step
was checked.  The block opens on ``COMPLETE VERIFIED DOMAIN PROOF`` rather than
``PARTIAL FORMAL DOMAIN EXPLANATION``, and the reasoning is numbered rather than
summarized.  Against ``latch.fcstm`` and a query that pins one variable to two
values at the same frame:

.. code-block:: text

   Explanation: COMPLETE VERIFIED DOMAIN PROOF
   Classification: the assumptions are internally inconsistent

   Why no execution exists:
     1. At frame 1, retries must equal 1.
     2. At frame 1, retries must equal 2.
     3. Therefore one value cannot be two things at once. No execution satisfies
        these initialization and query requirements, and the property was not
        evaluated.

   Conflict constraints:
     1. two_values.fbmcq:1:1-1:34
        assume at 1: var("retries") == 1;
     2. two_values.fbmcq:2:1-2:34
        assume at 1: var("retries") == 2;

   The displayed core is sufficient for UNSAT and proven subset-minimal.
   Core scope: assumptions_component
   Core granularity: source_group
   Core size: 2
   Reduction: subset_minimal
   Subset minimality: proven

Three differences from the formal block are contractual rather than cosmetic.
The heading names a *verified* proof, so every step behind those sentences was
checked by one of the methods below.  ``Why no execution exists`` is the proof
read in dependency order, one sentence per step, ending on the contradiction.
And the ``Reason:`` line is absent: a complete proof has nothing to explain about
why it stopped early, whereas the formal block always says what it could not do.

The closing sentence reports that no execution exists and that the property was
therefore *not evaluated*.  An empty scenario and a violated property are
different findings; a reader must not take this block as a counterexample.


Proof vocabulary
~~~~~~~~~~~~~~~~

Each proof step is a node.  ``kind`` says what the node is for:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - ``kind``
     - Meaning
   * - ``input``
     - Restates one core member as a normalized fact.  Exactly one member, and
       every subset-minimal member has exactly one input node.
   * - ``derived``
     - Produces a new fact from facts already established.
   * - ``contradiction``
     - The single root, showing that the established facts cannot hold together.

``rule_id`` names which rule produced the node's conclusion.  The catalog is
closed; a query that needs a reading outside it degrades to ``formal`` rather
than inventing one.

The ``Reachable`` column records whether any query is currently known to produce
a node carrying that rule.  No rule is unreachable: each one fires for some query a
user can write.  Three of them waited on a fourth for a while, and what unblocked
them is set out in :doc:`/explanations/bmc_solving/index`.

The rules whose conclusion is not the contradiction itself are the ones that produce
a ``derived`` node, so a published proof over such a conflict is a chain rather than
a fan: input nodes for the subset-minimal members, one derived node per step, and the
single contradiction root.  A conflict no chain reaches still publishes the fan, and
a consumer accepts both shapes.

.. list-table::
   :header-rows: 1
   :widths: 26 14 60

   * - ``rule_id``
     - Reachable
     - What it concludes
   * - ``source_fact``
     - yes
     - An input node's own fact, taken from the core member it restates.
   * - ``case_condition_entailment``
     - yes
     - The same transition case with its condition discharged.  A case's assignment
       holds where the case applies, so the condition has to be established from the
       members before the assignment can be used -- and the solver does that, against
       the members' own constraints rather than their published facts.  The node cites
       the members that entail it and records ``solver_entailment``; the condition key
       is removed rather than emptied, because the evaluation rule reads keys.
   * - ``transition_assignment``
     - yes
     - What a transition's effect assigns to a variable at the next frame.  A step
       relation publishes that assignment as ``transition_case``, the binding proves
       it equivalent to one requirement of the group, and
       ``case_condition_entailment`` supplies the unconditional form this rule reads.
   * - ``equality_substitution``
     - yes
     - The result of substituting a known value into another fact, for an operand
       still standing as a symbol.
   * - ``arithmetic_evaluation``
     - yes
     - The value an arithmetic step leaves in a variable.  It consumes an
       ``arithmetic_expression`` fact, which ``transition_assignment`` produces.
   * - ``interval_intersection``
     - yes
     - That no value satisfies every bound required at one slot.
   * - ``state_domain_exhaustion``
     - yes
     - That a frame has no state left it could be in.
   * - ``definedness_failure``
     - yes
     - That an operation cannot stay defined on the value required of it.
   * - ``incompatible_equalities``
     - yes
     - That one slot is required to hold two different values.
   * - ``boolean_complement``
     - yes
     - That the same requirement is both demanded and ruled out.  Reached through an
       event assumption: ``assume event("Root.A.Go", 0) == true`` beside
       ``assume event("Root.A.Go", 0) == false`` publishes two ``proposition`` facts
       that agree on ``identity`` and differ in ``holds``.  The step is part of the
       identity, so the same event at two steps is two subjects rather than one.
       An opposition written over states does **not** reach it, and does not need
       to: ``assume at 1: active("Root.A")`` with ``assume at 1: !active("Root.A")``
       publishes two ``state_membership`` facts differing in ``excluded``, which
       ``excluded_state_selected`` below closes.  State assertions stay where they
       are rather than moving to ``proposition``, because the rule that exhausts a
       frame's state domain reads those exclusions and would lose its only premise
       source.
   * - ``excluded_state_selected``
     - yes
     - That a frame is required to be in a state it also rules out.  The two
       premises are one published fact kind read two ways: a state requirement that
       holds reads as an equality on the frame's slot, and one that is excluded reads
       as an exclusion.  Neither of the earlier rules applies -- an equality on a
       slot is not a second equality, and one state is not a domain.
   * - ``preceding_value_entailment``
     - yes
     - That a variable held the same value at the frame before the one a requirement
       states it at.  A step that only carries a variable forward says nothing a fact
       can restate, so this asks the solver what the members force instead, and cites
       the ones that force it.  The direction is backwards because the requirement
       that states the value is one member, which is what the citation seam can
       record; a value carried forward from a derived step would stand for however
       many members its subtree used.

Six of these rules are exercised by the checked-in benchmark corpus under
``benchmarks/bmc/infeasibility/cases/handwritten/``, and its report records which
case produced which rule.  The checked-in report was measured before
``boolean_complement`` became reachable, so it records five of them; the case that
reaches the sixth is ``event_conflict.fbmcq``, in the same corpus.  The rules of the
arithmetic chain, together with ``excluded_state_selected`` and
``preceding_value_entailment``, are reached by the queries
:doc:`/explanations/bmc_solving/index` sets out, not yet by a corpus case.  Read the
measured ratio there rather than from this page: it is a property of that corpus
at a given revision, not of the tool.

``verification_method`` says who agreed with the step, and the division is the
proof's trust boundary rather than a label:

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - ``verification_method``
     - What was checked
   * - ``core_binding``
     - The normalized fact was re-encoded and checked against the core member in
       both directions: ``group => fact`` and ``fact => group`` must each be
       refuted.  Either direction coming back unknown, timing out, or failing to
       hold keeps the proof out of ``complete``.  Used by input nodes only.
   * - ``core_binding_unit``
     - The member's group holds one requirement per case, so it is a conjunction and
       no single fact can imply the whole of it.  The fact was re-encoded and checked
       against **one** requirement of that conjunction in both directions, and the
       node names which one through ``unit_index`` beside ``unit_count``.  A fact
       equivalent to two requirements identifies neither, so the binding is refused
       rather than resolved.  Used by input nodes only.
   * - ``rule_checker``
     - An independent checker re-derived the conclusion from the premises without
       reusing the code that constructed it.  Used by derived and root nodes.
   * - ``solver_entailment``
     - The step's rule and side conditions were discharged by the solver rather
       than by a checker, because the question is about the core members'
       constraints and not about the published facts a checker sees.  The node's
       ``item_ids`` name the members the solver used, and they are a subset of the
       published core.  Used by derived and root nodes.

A proof also states what it claims about its own shape.  ``input_minimality`` is
``subset_minimal``: the inputs are exactly the subset-minimal core, one node per
member, and a missing, extra, or duplicated input is refused rather than
published.  ``graph_minimality`` is ``dependency_pruned``: every node published
is reachable from the root.  ``verification_status`` is ``verified``, which is
the only value it takes -- an unverified graph is not published at all.


Explanation types
~~~~~~~~~~~~~~~~~

A Python caller reads the same content through frozen dataclasses rather than by
parsing the report:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Type
     - What it carries
   * - :class:`~pyfcstm.bmc.BmcInfeasibilityExplanation`
     - ``requested_mode``, ``achieved_mode``, ``status``, ``reason``,
       ``classification``, ``elapsed_ms``, and the core, narrative and proof.
   * - :class:`~pyfcstm.bmc.BmcConflictCore`
     - ``scope``, ``granularity``, ``items``, ``reduction`` and
       ``subset_minimality``.
   * - :class:`~pyfcstm.bmc.BmcCoreItem`
     - One core member: its stable id, semantic role, constraint reference and
       normalized fact.
   * - :class:`~pyfcstm.bmc.BmcConstraintRef`
     - Which stage and formula a member came from.
   * - :class:`~pyfcstm.bmc.BmcSourceRef`
     - Where in which document a member was written.
   * - :class:`~pyfcstm.bmc.BmcConflictNarrative`
     - ``derivation_status``, ``headline`` and ``reasoning_steps``.
   * - :class:`~pyfcstm.bmc.BmcReasoningStep`
     - One sentence, with the core items and proof nodes it reads.
   * - :class:`~pyfcstm.bmc.BmcConflictProof`
     - ``scope``, ``root_id``, ``nodes``, ``input_minimality``,
       ``graph_minimality`` and ``verification_status``.
   * - :class:`~pyfcstm.bmc.BmcProofNode`
     - ``stable_id``, ``kind``, ``rule_id``, ``premise_ids``, ``conclusion``,
       ``item_ids``, ``human_text`` and ``verification_method``.

.. code-block:: python

    from pyfcstm.bmc import BmcConflictProof, BmcProofNode, solve_bmc_property

    result = solve_bmc_property(
        model, query_text, infeasibility_explanation="proof"
    )
    explanation = result.feasibility.explanation
    if explanation is not None and explanation.proof is not None:
        proof: BmcConflictProof = explanation.proof
        for node in proof.nodes:
            assert isinstance(node, BmcProofNode)
            print(node.stable_id, node.rule_id, node.verification_method)

The same object is reachable in JSON at
``result.feasibility.explanation``, whose ``proof`` key is ``null`` at any depth
below ``proof`` and at ``proof`` depth whenever the attempt degraded.


Explanation status and degradation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``requested_mode`` is what the caller asked for and ``achieved_mode`` is what was
produced.  ``status`` says how complete the achieved depth is:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - ``status``
     - Meaning
   * - ``complete``
     - The achieved depth produced everything it promises.
   * - ``partial``
     - Some of it was produced.  ``reason`` says what stopped there.
   * - ``unknown``
     - A check the depth depends on came back neither way.
   * - ``timeout``
     - The explanation budget ran out before the depth was reached.

Not every pairing of depth, status and payload exists.  The full set is a
fourteen-row matrix that the public constructor enforces, and rather than restate
it here -- an earlier revision of this page tried and got it wrong -- the two
facts a reader needs are these:

* ``complete`` means the depth delivered what it promises, so an
  ``achieved_mode`` of ``none`` is never ``complete``.  Constructing that pairing
  raises ``achieved_mode 'none' cannot be complete; it is partial, unknown or
  timeout``.
* ``reason`` is the exception, and it is worth knowing because it is the field a
  degraded result explains itself through: ``complete`` never carries one --
  there is nothing to explain -- and ``partial``, ``unknown`` and ``timeout``
  always do.  This holds across all fourteen signatures and all three achieved
  depths.
* Every other payload field is not something to infer.  Read ``classification``,
  ``core``, ``narrative`` and ``proof`` for presence rather than predicting it
  from ``status``; each is documented above and each is nullable.

:class:`~pyfcstm.bmc.BmcInfeasibilityExplanation` refuses a combination outside
the matrix with a message naming what is wrong, so a consumer that builds one
learns immediately, and a consumer that only reads results never needs the matrix
at all.

A request for ``proof`` that degrades therefore reports ``achieved_mode`` as
``formal``, and ``reason`` names the cause.  Against the same model and a query
whose conflict needs a transition reading:

.. code-block:: text

   Explanation: PARTIAL FORMAL DOMAIN EXPLANATION
   Explanation depth: requested proof, achieved formal
   ...
   Reason: the formal explanation is complete, but no rule in the catalog closes
   this core.

Degradation is not failure: the formal block still names the classification, the
subset-minimal core and every source location.  For some conflicts it says *more*
than a proof would -- see the boundary notes in
:doc:`/explanations/bmc_solving/index`.


Direct Python result text
-------------------------

``BmcSolveResult`` uses the same semantic vocabulary when it is printed
directly with ``str(result)`` or ``result.to_text()``.  The summary appears
before the canonical field table, so a Python caller can immediately see the
polarity, bounded conclusion, scenario status, response horizon, and available
model role without interpreting raw ``SAT``/``UNSAT`` fields:

For programmatic human-facing reports, ``result.property_verdict`` returns the
same canonical ``Property verdict`` line without parsing ``str(result)``.  It
is derived from ``result.outcome`` and preserves the evidence distinction in
parentheses; it is presentation text, not an additional JSON payload field.

.. code-block:: text

   BmcSolveResult: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND
   Scenario: FEASIBLE
   Property verdict: SATISFIED WITHIN BOUND (WITNESS FOUND)
   Semantic interpretation: A satisfying witness execution exists within the bound; this is existential evidence, not a universal guarantee.
   Primary search: WITNESS = SAT
   Conclusion: At least one admissible execution satisfies the reach objective within 1 macro-step.
   Evidence:
     Model role: PRIMARY WITNESS
     Model evidence: SAT model available.

   Details:
   BmcSolveResult
   field    value
   ...

The same mapping is used for ``NO WITNESS``, ``COUNTEREXAMPLE FOUND``,
``PROPERTY GUARANTEED``, scenario infeasibility, feasibility unknown/timeout,
primary unknown/timeout, and incomplete response horizons.  A solve result does
not own runtime replay; ``BmcReplayResult`` remains the separate object that
prints replay success or mismatch details, and the CLI combines both objects to
produce ``RESULT UNTRUSTED`` when necessary.

Inconclusive results also place the actionable cause in ``Evidence``.  A
feasibility result identifies the ``ASSUMPTIONS`` stage and prints its
``UNKNOWN``/``TIMED OUT`` status and solver reason, or explicitly says that the
stage was not checked because the shared timeout budget was already exhausted.
Primary ``unknown``/``timeout`` results print ``Primary reason``; incomplete
response results print ``Horizon reason`` for an open, unknown, timeout,
disabled, or not-checked suffix check.  This information is part of the public text
presentation used by both the CLI and ``str(result)``/``result.to_text()``; it
is not restricted to the low-level ``Details`` table.

JSON envelope
-------------

JSON is UTF-8, pretty-printed with two-space indentation, recursively sorted
keys, non-ASCII characters preserved, and one trailing newline.  Every object
in the schema rejects undeclared keys where ``additionalProperties`` is false.
Raw Z3 models and complete SMT formulas are deliberately excluded.

.. list-table:: Top-level JSON fields
   :header-rows: 1
   :widths: 20 22 15 43

   * - Field
     - Type/allowed value
     - Always present
     - Meaning
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
     - Role-aware trace for a CLI-selected primary or suffix model; null when
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

For a current result with a non-empty ``available_model_roles`` array, both the
``witness`` and ``replay`` objects must use the role-aware shape and carry
exactly the same role as the result.  An empty role array requires both objects
to be ``null``.  This keeps the external envelope from combining evidence from
different model channels even when each individual object is structurally
valid.  Current and legacy-compatible objects are distinguished by their field
sets, not by a payload version field.

Witness fields
--------------

The selected witness trace is present for a primary or suffix model. CLI-emitted
traces use the role-aware shape with root ``model_role`` and ``verdict`` fields;
the raw-model ``decode_bmc_witness`` API emits the legacy-compatible shape
without those fields. In the role-aware shape, ``model_role`` is at the trace
root, never nested under ``solver``. The required root fields are described
below.

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
``snapshot``.  ``active_leaf`` is the runtime state path where the call
executed: the active leaf state when one is active, otherwise the call's host
state path.  Entering or leaving a composite state, or running a plain
``during`` action declared on one, has no active leaf, so ``active_leaf``
equals ``state`` there.  ``named_ref`` is the named ``ref`` action at the
callsite, or null when the callsite is not a named ``ref``: only a callsite
names its own call, so a chain starting from an anonymous ``ref`` stays null
however many named actions it passes through.
The CLI records these calls during replay but supplies no user
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
       ``unconsumed_events``, ``abstract_calls``, ``delta``
     - Actual runtime event accounting, committed-only Delta result, and recorded abstract calls.
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
``result.outcome`` nor the witness trace exposes a stable machine-readable
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
     "witness": {"model_role": "primary_witness", "verdict": {"outcome": "witness_found", ...}, ...}
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
Because the suffix model is available, ``witness`` and ``replay`` are
role-aware objects with ``model_role: incomplete_suffix``; they describe only
the executable prefix and do not turn the detached result into a property
verdict.  Increase the bound if a definitive horizon is required.

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

:download:`Download the normative BMC JSON Schema
<bmc_cli.schema.json>`.

The schema is a reference artifact, not a runtime dependency.  Sphinx publishes
it through the download link above; do not infer a schema URL from this page's
rendered URL.  It deliberately is not shipped inside ``pyfcstm`` wheels, source
distributions, or standalone executables.  Consumers that need structural
validation should download or vendor this reference schema with their integration
and load that local copy:

.. code-block:: python

   import json
   from pathlib import Path

   schema = json.loads(
       Path("bmc_cli.schema.json").read_text(encoding="utf-8")
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
* When JSON exists, verify ``payload.exit_code`` equals the process exit status.
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
