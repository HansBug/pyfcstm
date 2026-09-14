.. _sec-reference-inspect-report:

Inspect report reference
========================

``pyfcstm inspect`` has four output formats:

.. list-table:: Output formats
   :header-rows: 1
   :widths: 18 32 50

   * - Format
     - Contract
     - Use case
   * - ``human``
     - Text renderer for people.
     - Local debugging, tutorials, and review comments.
   * - ``json``
     - Full ``ModelInspect`` JSON payload.
     - CI checks, dashboards, and exact structural inventory.
   * - ``llm-json``
     - Stable compact JSON for repair prompts.
     - Automated LLM repair loops and bug-report attachments.
   * - ``llm-md``
     - Stable Markdown presentation of the LLM report.
     - Human-readable repair handoff.

The full JSON schema lives in ``pyfcstm/diagnostics/schema.json``. The LLM
report schema lives in ``pyfcstm/diagnostics/inspect_llm_report_schema.json``.
Invalid input is not represented as a successful report: syntax errors, unreadable
files, decode failures, model-validation errors, and forbidden verify policy are
CLI failures.

CLI options affecting reports
-----------------------------

.. list-table:: Inspect CLI controls
   :header-rows: 1
   :widths: 28 22 50

   * - Option
     - Applies to
     - Contract
   * - ``--format human``
     - stdout or ``-o``
     - Default renderer. ANSI color follows ``--color`` and terminal detection.
   * - ``--format json``
     - stdout or ``-o``
     - Emits full ``ModelInspect`` JSON with sorted keys and a trailing newline.
   * - ``--format llm-json``
     - stdout or ``-o``
     - Emits stable LLM-oriented JSON, not the full structural report.
   * - ``--format llm-md``
     - stdout or ``-o``
     - Emits the same repair-oriented content as Markdown.
   * - ``--color auto|always|never``
     - ``human`` only
     - Ignored by machine-readable formats.
   * - ``--enable-verify``
     - report diagnostics
     - Adds inspect-eligible verify algorithms within the configured policy.
   * - ``--max-complexity-tier``
     - verify policy
     - Selects the highest structural or SMT-local complexity tier accepted by inspect.
   * - ``--max-call-count-scaling``
     - verify policy
     - Selects the highest model-derived call-count scaling accepted by inspect.
   * - ``--smt-timeout-ms``
     - solver-backed verify
     - ``None`` leaves no CLI timeout override; ``0`` is forwarded to Z3 as no finite timeout.

Full JSON top-level fields
--------------------------

The full JSON report is produced from ``ModelInspect.to_json()`` and contains
these required top-level fields.

.. list-table:: Full report top-level fields
   :header-rows: 1
   :widths: 28 72

   * - Field
     - Meaning
   * - ``root_state_path``
     - Dotted path of the root state.
   * - ``states``
     - Array of ``StateInfo`` objects for leaf, composite, and pseudo states.
   * - ``transitions``
     - Array of normal and expanded transition summaries.
   * - ``variables``
     - Array of variable summaries, including read/write and guard-affect facts.
   * - ``events``
     - Event declarations and usage summaries.
   * - ``actions``
     - Lifecycle, aspect, abstract, and ref action summaries.
   * - ``forced_transitions``
     - Authored forced transitions and expansion counts.
   * - ``combo_transitions``
     - Generated combo transitions copied from ``transitions`` for direct consumers.
   * - ``combo_origins``
     - Authored combo trigger provenance grouped by stable origin id.
   * - ``metrics``
     - Aggregate counts, hierarchy depth, ratios, and inventories.
   * - ``structure_statistics``
     - Descriptive LLM structure counts and rates. Initial edges are excluded;
       generated combo edges and forced expansions are folded to authored
       transitions. This section does not emit warnings or a health score.
   * - ``reachability_graph``
     - Default inspect graph: guards ignored, composite initial edges followed.
   * - ``event_emission_map``
     - Event name to source states that can emit it.
   * - ``var_dataflow``
     - Variable name to read/write state paths.
   * - ``aspect_impact_map``
     - Composite path to descendant leaves reached by aspect actions.
   * - ``action_ref_graph``
     - Named-action signature to referenced named-action signatures.
   * - ``verification``
     - Verification-provider support, requested policy, execution coverage,
       and one result record per registered algorithm.
   * - ``diagnostics``
     - Array of ``ModelDiagnostic`` objects.

Nested object contracts
-----------------------

.. list-table:: Main nested objects
   :header-rows: 1
   :widths: 24 76

   * - Object
     - Required fields and notes
   * - ``StateInfo``
     - ``path``, ``name``, ``parent_path``, ``is_leaf``, ``is_pseudo``, ``is_composite``, ``substates``, ``initial_targets``, lifecycle action arrays, aspect arrays, and ``has_abstract_action``.
   * - ``TransitionInfo``
     - ``from_path``, ``to_path``, ``event``, ``event_scope``, ``guard``, ``effect``, ``effect_self_assigns``, ``is_forced``, ``forced_origin``, ``transition_index``, and combo projection/provenance fields.
   * - ``ComboOriginInfo``
     - ``origin_id``, ``transition_span``, ``trigger_span``, and ordered ``terms``.
   * - ``ComboOriginTermInfo``
     - Term index, role, consumed term flag, text, and transition/trigger/term/value/removal spans.
   * - ``ComboOriginRefInfo``
     - Term index, role, consumed term flag, text, transition/trigger/term/value/removal spans, and authored endpoint provenance: ``source_kind`` (``state``/``init``), ``source_path``, ``selection_owner_path`` for init selections, ``target_kind`` (``state``/``exit``), and ``target_path`` (``[*]`` for exit).
   * - ``VariableInfo``
     - Name, type, initial value, read/write state paths, guard-affect flags, abstract-action scope, and float-literal assignments.
   * - ``EventInfo``
     - Qualified name, declaration scope, use sites, and declared/used booleans.
   * - ``ActionInfo``
     - Signature, state path, name, stage, aspect, ref target, and attachment flag.
   * - ``ForcedTransitionInfo``
     - Owning state, source/target, trigger facts, original raw text, and expansion count.
   * - ``ModelMetrics``
     - State/transition/event/variable counts, hierarchy depth, var-to-leaf ratio, aspect coverage, and abstract-action inventory.
   * - ``StructureStatistics``
     - Authored transition count, ``transitions_per_state`` (``T / S``),
       unreachable counts/rates, and guard/effect/eventless rates. ``S`` is the
       non-pseudo state count; rates include numerator and denominator fields
       and are ``null`` when their population is empty. Advisory defaults are
       ``T / S <= 6.0``, unreachable leaf-state rate ``<= 0.10``, and
       unreachable transition rate ``<= 0.10``; exceeded names are metadata,
       not diagnostics.
   * - ``ModelDiagnostic``
     - ``code``, ``severity``, ``message``, ``span``, ``refs``, and optional ``suggested_fix``.
   * - ``Span``
     - ``line``, ``column``, ``end_line``, and ``end_column``.

Verification execution metadata
-------------------------------

``verification`` records what verification work was available and executed.
It is execution metadata, not another diagnostic collection.  An algorithm
that was disabled, excluded by policy, or returned an indeterminate result does
not create a diagnostic merely because of that execution outcome.  In
particular, partial diagnostics from an indeterminate result are counted but
their payloads are not published.

.. list-table:: Verification report fields
   :header-rows: 1
   :widths: 28 72

   * - Field
     - Meaning
   * - ``supported`` / ``provider``
     - Whether this implementation has a verification provider and its stable
       name.  jsfcstm reports ``supported=false`` and ``provider=null``.
   * - ``enabled`` / ``reason_code``
     - Whether verification was requested.  ``verification_disabled`` and
       ``provider_unsupported`` distinguish the two non-running top-level
       states.
   * - ``requested_policy``
     - Requested maximum complexity tier, call-count scaling, and SMT timeout.
       An unsupported provider reports all three values as ``null``.
   * - ``summary``
     - ``registered``, ``executed``, ``not_run``, and ``indeterminate`` counts.
       When verification is disabled, the registry stays lazy, so
       ``registered`` is ``null`` and ``not_run`` is zero rather than a
       fabricated registry-sized count.
   * - ``algorithms``
     - Ordered algorithm-level metadata including the declared diagnostic
       codes, raw ``result_kind``, exclusion reason, and
       ``partial_diagnostic_count``.

Algorithm ``result_kind`` preserves ``sat``, ``unsat``, ``timeout``,
``unknown``, or ``undecidable_skip`` exactly; an algorithm excluded before
execution uses ``not_run``.  SAT and UNSAT do not mean one uniform "pass" or
"fail" across algorithms because the polarity depends on the property being
checked.  The human renderer therefore reports executed and indeterminate
coverage, and expands only indeterminate algorithms and their reasons.

For structural/topological algorithms, ``sat`` means that the structural
analysis completed and produced its topology result; it is not a claim that
the model satisfies every property.  Consumers must read the algorithm's
diagnostics together with ``result_kind`` rather than treating structural
``sat`` as a universal pass verdict.

LLM report contract
-------------------

``llm-json`` and ``llm-md`` are presentation contracts for repair loops. They do
not replace the full report. Their output does not include ``verification``
execution metadata; consumers that need coverage or indeterminate results must
use the full JSON report. Validate ``llm-json`` with the
``inspect_llm_report_schema.json`` shipped with the same ``pyfcstm`` release.
Neither the public payload nor the Markdown presentation carries a product
schema version or status marker.

The structure-statistics policy is descriptive by default: all raw counts and
rates are emitted, and the three conservative advisory defaults are recorded in
``thresholds``. A high value only adds its field name to
``exceeded_thresholds``; no G5 health warning or score is created. A rate with
an empty denominator is ``null`` (``N/A`` in human/Markdown output). Callers
may pass ``StructureStatisticsPolicy`` (or a partial mapping) to
``inspect_model``; ``None`` disables an individual advisory threshold. Any
future corpus-derived cutoff must identify its corpus and be explicitly configured.

The default ``6.0`` review trigger is an engineering baseline informed by the
pooled ``T / S = 2.75`` and the observed protocol-level range in the 14-protocol
PSMBench/RFC2PSM cohort (`PSMBench DOI <https://doi.org/10.52202/085713-1899>`_).
That cohort is flat, protocol-specific, and too small to define a universal
FCSTM limit; the trigger is intentionally broad enough not to flag ordinary
high-density protocol machines. The ``10%`` unreachable-population defaults are
review-budget heuristics, not published quality boundaries. UML 2.5.1 models
both transition ``guard`` and ``effect`` as optional, so this report
intentionally leaves those style rates without default cutoffs (`OMG UML 2.5.1
<https://www.omg.org/spec/UML/2.5.1/PDF>`_).

``unguarded_rate`` counts authored transitions whose AST has no guard.
``missing_effect_rate`` uses non-forced authored transitions as its denominator,
because forced declarations do not accept an effect in the FCSTM grammar.
``eventless_unconditional_rate`` counts transitions with neither an event nor a
guard. These are syntax-level observations, not claims that a transition is
semantically unsafe. Unreachable-transition reason buckets are deliberately
non-exclusive; the total is the union of authored identities, so one transition
may contribute to more than one reason while being counted once in the total.

.. list-table:: LLM top-level fields
   :header-rows: 1
   :widths: 28 72

   * - Field
     - Meaning
   * - ``status``
     - Overall status: ``ok``, ``info``, ``warning``, or ``error``.
   * - ``input``
     - Input path or ``null``.
   * - ``repair_protocol``
     - Object with ``goal`` and ordered ``rules`` for safe repair prompts.
   * - ``summary``
     - Counts for errors, warnings, infos, states, leaf states, transitions, variables, and root state, plus the ``structure_statistics`` object.
   * - ``diagnostics``
     - Compact diagnostic entries enriched with source excerpts and registry guidance.

.. list-table:: LLM diagnostic fields
   :header-rows: 1
   :widths: 28 72

   * - Field
     - Meaning
   * - ``code`` / ``severity`` / ``message``
     - Same stable code identity as the full report.
   * - ``location``
     - ``path``, ``line``, ``column``, ``end_line``, ``end_column`` or ``null``.
   * - ``source_excerpt``
     - Anchor line, caret, and nearby context lines when source text is available.
   * - ``refs``
     - Structured payload copied from the diagnostic.
   * - ``source``
     - ``inspect-static``, ``verify-backed``, or ``unknown``.
   * - ``provenance``
     - ``kind`` plus ``verify_required`` flag; verify-backed entries may also
       carry ``source_ids`` with stable ``algorithm_name@verification_scope``
       identifiers. These identifiers contain no product or schema version.
   * - ``summary``
     - Registry LLM summary for the diagnostic code.
   * - ``recommended_actions`` / ``do_not``
     - Registry guidance copied from ``codes.yaml``.
   * - ``repair_guidance``
     - Renderer-produced short guidance for the repair loop.

Invalid input boundary
----------------------

The inspect command first reads, decodes, parses, and validates the DSL. If any
of those steps fails, the command raises a controlled CLI error instead of
returning a normal inspect report. Treat this as an input failure, not as a
``diagnostics`` array with an ``E_*`` code.

Variable roles and access locations
-----------------------------------

Each ``VariableInfo`` retains its existing read/write summaries and adds
``external_supply``, ``diagnostic_policy``, ``read_sites`` and ``write_sites``.
These fields describe the expanded model, not an execution trace.

.. list-table:: Ownership and diagnostic applicability
   :header-rows: 1
   :widths: 22 23 55

   * - ``role``
     - ``external_supply``
     - ``diagnostic_policy``
   * - ``control`` (including legacy ``def``)
     - ``none``
     - ``unused``, ``unwritten``, ``write_only`` and ``constant_guard`` are true.
   * - ``input_dynamic`` (``input``)
     - ``cycle``
     - All four flags are false; the environment supplies each cycle's value.
   * - ``input_static`` (``param``)
     - ``construction``
     - All four flags are false; the parameter is fixed at construction.
   * - ``output``
     - ``none``
     - All four flags are false; external consumers need not read through the model.

The policy flags document the applicability of the existing control-variable
unused, unwritten-read, write-only and guard-variable-change diagnostics. They
are not configurable suppression switches and do not disable other validation
or constant-expression analysis. In particular, writing an input or parameter
is a model error. Multiple output writers remain permitted.

Each access site has the following fields:

.. list-table:: VariableAccessSite
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Meaning
   * - ``kind``
     - ``action``, ``guard`` or ``effect``. Conditions inside an action/effect keep that container's kind.
   * - ``state_path``
     - Expanded owning state path, including the import instance.
   * - ``action`` / ``action_index``
     - Action signature and zero-based index into ``actions``; both null for transitions. Inline signatures may repeat; use the index for identity.
   * - ``transition_index``
     - Zero-based index into ``transitions`` for guards/effects; null for actions.
   * - ``statement_path``
     - Zero-based statement and branch indices within the container. ``[0]`` is its first statement; ``[0, 0]`` is that conditional's first branch condition; ``[0, 0, 1]`` is the second statement in that branch. A transition guard uses ``[]``.
   * - ``source_path``
     - Authored source file, distinct from the expanded state path; null when unavailable.
   * - ``span``
     - Authored statement, branch block or transition range, using the existing 1-based, end-exclusive ``Span`` contract; null when unavailable. It is not a variable-token range.

Repeated occurrences of a variable in one expression yield one read site;
different statements, branches and imported instances retain separate sites.
An assignment that reads its destination has both a read and a write site.
Initializers are declaration metadata, not action/effect writes. Unreachable
statements still have sites. Abstract actions contribute no invented accesses;
action references use the existing ``action_ref_graph``, while their concrete
bodies have sites at their definitions. Access arrays follow model traversal
order, with actions before transitions in each state and nested statements in
source order. Indices are local to a report, not stable identifiers across edits.

Human reports list each variable's role and external supply. LLM repair reports
include ownership guidance so an empty write list for input/param or an empty
read list for output is not treated as a request to modify the model. Full
structured access sites remain in the full JSON report. The public payload does
not contain a schema or product version marker; validate against the schema
shipped with the running release.
