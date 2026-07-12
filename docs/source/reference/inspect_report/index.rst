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
   * - ``ComboOriginTermInfo`` / ``ComboOriginRefInfo``
     - Term index, role, consumed term flag, text, and transition/trigger/term/value/removal spans.
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
   * - ``ModelDiagnostic``
     - ``code``, ``severity``, ``message``, ``span``, ``refs``, and optional ``suggested_fix``.
   * - ``Span``
     - ``line``, ``column``, ``end_line``, and ``end_column``.

LLM report contract
-------------------

``llm-json`` and ``llm-md`` are presentation contracts for repair loops. They do
not replace the full report.

.. list-table:: LLM top-level fields
   :header-rows: 1
   :widths: 28 72

   * - Field
     - Meaning
   * - ``schema_version``
     - Constant ``pyfcstm.inspect.llm.v1``.
   * - ``schema_status``
     - Constant ``stable``.
   * - ``status``
     - Overall status: ``ok``, ``info``, ``warning``, or ``error``.
   * - ``input``
     - Input path or ``null``.
   * - ``repair_protocol``
     - Object with ``goal`` and ordered ``rules`` for safe repair prompts.
   * - ``summary``
     - Counts for errors, warnings, infos, states, leaf states, transitions, variables, and root state.
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
     - ``kind`` plus ``verify_required`` flag.
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
