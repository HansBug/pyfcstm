.. _sec-explanations-diagnostics:

Diagnostics explanation
=======================

Inspect diagnostics are designed to answer three questions:

1. What does the current model contain?
2. Which parts look invalid, risky, unused, unreachable, redundant, or
   target-sensitive?
3. What structured context should a human, CI job, IDE, or LLM repair loop use
   next?

This page explains the mechanism. It is not the field catalog; use
:doc:`../../reference/inspect_report/index` for report schemas and
:doc:`../../reference/diagnostics_codes/index` for the complete code registry.
Use :doc:`../../how_to/inspect/index` when you need a copyable command.

The inspect pipeline in one pass
--------------------------------

``pyfcstm inspect`` is a report pipeline wrapped around normal FCSTM loading.
A successful run has already passed the read, decode, parse, and model-building
boundary. Only then can inspect build the structural report and attach
``diagnostics``.

.. list-table:: Pipeline stages and boundaries
   :header-rows: 1
   :widths: 20 36 24 20

   * - Stage
     - What happens
     - Successful output
     - Failure boundary
   * - Read and decode
     - The CLI reads bytes and decodes source text.
     - Source text for excerpts.
     - Missing file, permission error, or decode failure exits non-zero.
   * - Parse and build model
     - The DSL parser and model importer resolve states, variables, events,
       imports, transitions, and lifecycle actions.
     - ``StateMachine`` object.
     - Grammar or model-validation errors exit non-zero.
   * - Inspect structure
     - ``inspect_model`` walks the model and builds states, transitions,
       variables, events, metrics, and derived graphs.
     - ``ModelInspect`` core fields.
     - Internal bugs should surface; they are not diagnostic entries.
   * - Static analyzers
     - Analyzer modules add warnings and infos from structural, combo, numeric,
       data-flow, type-shape, redundancy, and design-health facts.
     - Static ``diagnostics[]`` entries.
     - Internal analyzer bugs surface as failures; lookup-only registry codes
       are not analyzer failures.
   * - Optional verify adapter
     - With ``--enable-verify``, bounded eligible verification algorithms run
       and their results are normalized.
     - Additional verify-backed entries.
     - Forbidden policies exit non-zero before a report is produced.
   * - Renderer
     - The selected renderer emits human text, full JSON, ``llm-json``, or
       ``llm-md``.
     - stdout or output file.
     - Write errors exit non-zero.

The important design point is that diagnostics are report facts, not parser
errors. A syntax error does not become ``diagnostics[0]``; it prevents the report
from existing.

What the static analyzers can see
---------------------------------

Default inspect is static. It sees the model graph, authored and expanded
transitions, resolved events, variables, lifecycle actions, action references,
combo provenance, and lightweight expression facts. It does not execute the
runtime and it does not ask an external event source what will happen in
production.

.. list-table:: Analyzer families
   :header-rows: 1
   :widths: 22 38 40

   * - Source family
     - Examples of facts it can see
     - Typical diagnostic shape
   * - ``structural.py``
     - Reachable states, leaf exits, initial targets, hierarchy shape.
     - Missing entry, unreachable state, deadlock leaf, deep hierarchy.
   * - ``combo.py``
     - Authored combo trigger terms and generated relay provenance.
     - Duplicate events, implied or contradictory guard prefixes, relay naming.
   * - ``numeric.py``
     - Literal ranges, float-bitwise operations, constant division or shift
       risks for target profiles.
     - Target-specific C/C++ deployment warnings.
   * - ``data_flow.py`` and ``use_def.py``
     - Reads, writes, guard-affect paths, abstract-action uncertainty.
     - Unreferenced, unwritten-read, write-only, or never-changing variables.
   * - ``design_health.py``
     - Ratios, large composites, aspect coverage, dead named actions.
     - Maintainability warnings rather than semantic proof failures.
   * - ``type_shape.py``
     - Arithmetic-vs-boolean expression category facts.
     - Type-shape errors or partial static warnings.
   * - ``transition_info.py``
     - Self assignments, unconditional transitions, redundant transition keys.
     - No-op, redundant, or unconditional fall-through diagnostics.

The analyzers attach ``span`` when they can point to a concrete source object
and attach ``refs`` when a consumer needs structured follow-up data. That is
why a good repair loop should branch on ``code`` and ``refs`` rather than scrape
English messages.

Figure-guided trace of the demo model
-------------------------------------

.. figure:: ../../tutorials/inspect/inspect_diagnostics.fcstm.puml.svg
   :alt: Inspect demo expanded PlantUML diagram
   :width: 88%

   The diagram shows the expansion that source prose alone hides. ``Confirm +
   Confirm`` and ``[ready > 0] + [ready > -1]`` become relay pseudo states. The
   diagnostics still point back to the authored line and carry combo origin
   references so a repair can edit the source trigger, not the generated relay.

Trace 1: repeated combo event
-----------------------------

Authored source:

.. code-block:: fcstm

   Active -> ComboDone :: Confirm + Confirm;

The model importer expands the combo trigger into two generated edges. That is
legal: a combo trigger is an ordered chain, so two terms produce two hops. The
static combo analyzer then compares resolved event identities and sees that term
0 and term 1 both resolve to ``InspectDemo.Active.Confirm``.

The resulting diagnostic is ``W_COMBO_DUPLICATE_EVENT``. Its ``span`` points at
the second ``Confirm`` term. Its ``refs`` include ``origin_id``, term indexes,
term text, trigger span, transition span, and the span of the first matching
term. The human renderer uses the same span to print:

.. code-block:: text

   Active -> ComboDone :: Confirm + Confirm;
                                      ^^^^^^^

The recommendation is not “delete generated pseudo states.” The smallest source
repair is to inspect whether the second term was meant to be another event, and
only then reduce or replace the duplicated term.

Trace 2: target-specific numeric range
--------------------------------------

Authored source:

.. code-block:: fcstm

   def int too_large = 9223372036854775808;

The literal is valid FCSTM source, and Python can represent that integer. The
numeric analyzer is not claiming the Python generated runtime overflows. It is
checking the C-family deployment profile used by default generated C and C++
templates, where the carrying type is ``PYFCSTM_GENERATED_INT64``.

The diagnostic ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` therefore carries
``refs.target_templates`` with ``c``, ``c_poll``, ``cpp``, and ``cpp_poll``. It
also carries the minimum and maximum range text and a runtime note. A CI gate
that deploys only the Python template may record this warning as irrelevant to
that target; a release gate that ships C or C++ output should treat it as a real
portability risk.

Trace 3: optional topological verify feedback
---------------------------------------------

The tutorial model has leaf states with no outgoing edge. Default inspect
already reports ``W_DEADLOCK_LEAF`` from static structure. When the command adds
``--enable-verify``, the inspect adapter can also run closed structural topology
algorithms. The same model then reports facts such as ``W_TOPOLOGICAL_NOEXIT``
and ``I_TOPOLOGICAL_NON_TERMINATING``.

This does not mean inspect ran an unbounded state-space search. The adapter
iterates registry metadata, keeps only closed algorithms within the selected
complexity and call-count policy, and rejects ``bmc_search`` and
``k_unrollings`` labels before any report is produced. The result is useful
extra topology feedback, not a proof over all event schedules and abstract
handlers.

Severity, risk, and emit tier
-----------------------------

Severity answers how the current diagnostic should be prioritized. Emit tier
answers where the diagnostic can come from. They are related but not the same.

.. list-table:: Reading severity and tier together
   :header-rows: 1
   :widths: 20 40 40

   * - Fact
     - What it means
     - What it does not mean
   * - ``error``
     - The model cannot be safely constructed or used for the requested path.
     - Every error appears inside a successful JSON report.
   * - ``warning``
     - The report is successful, but a structural, design, numeric, or verify
       fact needs review.
     - The warning is automatically a release blocker for every target.
   * - ``info``
     - A non-blocking observation may help explain intent or topology.
     - The model is necessarily healthy or unhealthy.
   * - ``static_pipeline``
     - Default inspect can emit the code from static facts.
     - The code was proven by an SMT solver.
   * - ``verify_pipeline``
     - Optional verify integration may emit the code.
     - It runs without ``--enable-verify`` or despite policy rejection.
   * - ``lookup_api``
     - Explicit resolver APIs own the code.
     - It is expected in ordinary CLI inspect output.
   * - ``catalog_only``
     - The registry preserves a compatibility contract.
     - Current normal pyfcstm paths should emit it.

This split keeps CI filters honest. A filter can decide to fail on all
``error`` diagnostics, fail on target-relevant warnings, and merely record infos;
it can also decide not to expect verify-only codes in a default static report.

Why diagnostics help LLM repair loops
-------------------------------------

An LLM prompt that contains only prose has to guess the edit target. An inspect
LLM report gives it a safer packet:

* a stable ``code`` that selects a known repair strategy;
* a ``severity`` that helps prioritize;
* a precise ``location`` and source excerpt when source text is available;
* ``refs`` that carry the state, variable, event, guard, target profile, or
  provenance object;
* registry ``recommended_actions`` and ``do_not`` rules;
* a global repair protocol that asks for the smallest source edit.

The packet is guidance, not permission for broad rewrites. If two diagnostics
point to the same line, the repair loop should inspect provenance first and
avoid stacking every suggested action mechanically.

Counterexamples and limits
--------------------------

These examples are intentionally negative. They keep the boundary between
inspect, verify, generated code, and repair tooling clear.

.. list-table:: What inspect does not promise
   :header-rows: 1
   :widths: 28 72

   * - Counterexample
     - Correct interpretation
   * - Invalid DSL file
     - A missing brace exits with ``Failed to parse input DSL file``. There is
       no successful report and no ``diagnostics`` array to inspect.
   * - Duplicate state name
     - Model validation exits with ``Invalid state machine model``. Treat it as
       a process failure, even if the registry contains related ``E_*`` codes.
   * - C-family numeric warning
     - It can be a real C/C++ deployment risk while remaining non-applicable to
       Python generated runtimes.
   * - ``W_GUARD_VARS_NEVER_CHANGE``
     - The static data-flow analyzer found no DSL write path. It did not prove
       an abstract handler will never mutate external state.
   * - ``--enable-verify``
     - The command can add bounded topology or bounded SMT findings. It does
       not silently enable BMC search or unbounded path exploration.
   * - LLM repair report
     - The report makes a repair prompt more grounded. It does not prove that
       the LLM's patch is correct without tests or human review.

Operational boundary summary
----------------------------

Use this matrix when deciding where to handle an outcome.

.. list-table:: Outcome ownership
   :header-rows: 1
   :widths: 24 24 28 24

   * - Outcome
     - Where it appears
     - Owner
     - First response
   * - Missing input file
     - stderr and exit status
     - CLI wrapper or calling process
     - Fix path or working directory.
   * - Parse or model error
     - stderr and exit status
     - DSL author or importer
     - Fix source before expecting a report.
   * - Static warning
     - ``diagnostics[]`` in a successful report
     - Model author or reviewer
     - Inspect ``code``, ``span``, and ``refs``.
   * - Verify policy rejection
     - stderr and exit status
     - CI or command author
     - Use allowed policy or a separate explicit verification workflow.
   * - Target warning
     - ``diagnostics[]`` plus target refs
     - Deployment owner
     - Decide relevance by generated target family.
   * - LLM repair guidance
     - ``llm-json`` or ``llm-md``
     - Repair loop and reviewer
     - Apply smallest justified edit and verify afterwards.

A good inspect workflow therefore has two gates: first prove the command
produced a report, then decide what the report's diagnostics mean for the
specific human, CI, IDE, LLM, or deployment consumer.

Practical reading order
-----------------------

Read each diagnostic in a fixed order: start with ``code`` for the category,
then ``severity`` for priority, then ``span`` or ``location`` for the source,
then ``refs`` for target, variable, event, or provenance scope. Read natural
language guidance last. This prevents two common mistakes: acting on message
text without checking target scope, or applying a suggested edit without
checking author intent.

The same order is useful when reviewing an LLM patch. A patch that cannot name
the ``code``, source range, and ``refs`` field it used has not really followed
the inspect report.
