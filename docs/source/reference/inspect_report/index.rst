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
     - Default inspect graph: guards ignored, composite initial edges followed. A transition into ``Owner.[H]`` / ``Owner.[H*]`` also reaches the states of the default path and what a restore can re-enter; see :ref:`dsl-history-reference`.
   * - ``event_emission_map``
     - Event name to source states that can emit it.
   * - ``var_dataflow``
     - Variable name to read/write state paths.
   * - ``aspect_impact_map``
     - Composite path to descendant leaves reached by aspect actions.
   * - ``action_ref_graph``
     - Named-action signature to referenced named-action signatures.
   * - ``regions``
     - Optional. ``RegionInfo`` objects, present only when the model declares regions; see :ref:`inspect-report-regions`.
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
     - ``path``, ``name``, ``parent_path``, ``is_leaf``, ``is_pseudo``, ``is_composite``, ``substates``, ``initial_targets``, lifecycle action arrays, aspect arrays, and ``has_abstract_action``. A model that uses history is reported as written, before lowering, so no state or initial target is one that lowering generated. See :ref:`dsl-history-reference`.
   * - ``RegionInfo``
     - ``path``, ``name``, ``owner_path``, ``index``, ``substates``, ``initial_targets``, ``aspect_before`` and ``aspect_after``; see :ref:`inspect-report-regions`.
   * - ``TransitionInfo``
     - ``from_path``, ``to_path``, ``event``, ``event_scope``, ``guard``, ``effect``, ``effect_self_assigns``, ``is_forced``, ``forced_origin``, ``transition_index``, and combo projection/provenance fields. ``target_history`` (``shallow``, ``deep`` or null) marks a transition that enters ``Target.[H]`` / ``Target.[H*]``; its ``to_path`` names the history owner.
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

.. _inspect-report-regions:

Regions in the report
---------------------

A model that declares ``region`` blocks adds an optional top-level ``regions``
array. It is present only for such models, so the report of a model without
regions is unchanged. Each ``RegionInfo`` gives the region ``path``, its
``name``, the ``owner_path`` of the state that owns it, ``index`` (the
zero-based declaration order among the owner's regions, which is also their
execution order), the direct child ``substates``, the region's
``initial_targets`` and its ``aspect_before`` / ``aspect_after`` labels.

States, transitions, events and actions inside a region appear in the ordinary
arrays. A state in a region reports the region path as its ``parent_path``, and
a state that owns regions is ``is_composite`` with an empty ``substates``. The
report describes the model as written, so ``active("...")`` queries never add
hidden flag variables to ``variables``.

.. list-table:: ``RegionInfo`` fields
   :header-rows: 1
   :widths: 24 76

   * - Field
     - Meaning
   * - ``path``
     - Dotted path of the region, owner path plus the region name, for example ``Root.First``.
   * - ``name``
     - Region name as written.
   * - ``owner_path``
     - Dotted path of the state that owns the region.
   * - ``index``
     - Zero-based declaration order among the owner's regions. It is the execution order.
   * - ``substates``
     - Direct child state paths of the region.
   * - ``initial_targets``
     - Targets of the region's ``[*] -> ...`` transitions, each with ``target``, ``guard``, ``event`` and ``is_unconditional``.
   * - ``aspect_before`` / ``aspect_after``
     - Labels of the ``>> during before`` and ``>> during after`` actions declared in the region.

The model below has two regions that both write ``out``. The first
command prints the first lines of the human report. The script after it prints the whole
``regions`` array, the neighbouring ``states`` facts, and the blind-overwrite
diagnostic as JSON.

.. literalinclude:: region_overwrite_basic.fcstm
   :language: fcstm
   :caption: region_overwrite_basic.fcstm

.. code-block:: console

   $ pyfcstm inspect -i region_overwrite_basic.fcstm --color never
   [WARN] FCSTM Inspect Report: region_overwrite_basic.fcstm

   Summary
     status: warning
     root: Root
     states: 3 total / 2 leaf
     transitions: 2
     regions: 2
       Root.First: order 0 in Root; 1 states
       Root.Second: order 1 in Root; 1 states
     variables: 2
       out: control; external supply: none
       y: control; external supply: none
   ...

.. testcode::

   import json

   from pyfcstm.entry.inspect import build_inspect_json

   report = json.loads(build_inspect_json("region_overwrite_basic.fcstm"))
   print(json.dumps(report["regions"], indent=2, sort_keys=True))
   for path in ("Root", "Root.First.A"):
       state = [s for s in report["states"] if s["path"] == path][0]
       print(path, state["parent_path"], state["is_composite"], state["substates"])
   item = [d for d in report["diagnostics"] if d["code"] == "W_REGION_BLIND_OVERWRITE"][0]
   print(json.dumps(item, indent=2, sort_keys=True))

.. testoutput::

   [
     {
       "aspect_after": [],
       "aspect_before": [],
       "index": 0,
       "initial_targets": [
         {
           "event": null,
           "guard": null,
           "is_unconditional": true,
           "target": "Root.First.A"
         }
       ],
       "name": "First",
       "owner_path": "Root",
       "path": "Root.First",
       "substates": [
         "Root.First.A"
       ]
     },
     {
       "aspect_after": [],
       "aspect_before": [],
       "index": 1,
       "initial_targets": [
         {
           "event": null,
           "guard": null,
           "is_unconditional": true,
           "target": "Root.Second.B"
         }
       ],
       "name": "Second",
       "owner_path": "Root",
       "path": "Root.Second",
       "substates": [
         "Root.Second.B"
       ]
     }
   ]
   Root None True []
   Root.First.A Root.First False []
   {
     "code": "W_REGION_BLIND_OVERWRITE",
     "message": "Region 'Root.Second' overwrites variable 'out' in every cycle without using the value written by the earlier region 'Root.First'; that earlier write is lost whenever it runs.",
     "refs": {
       "owner_path": "Root",
       "previous_region": "Root.First",
       "previous_write_span": {
         "column": 28,
         "end_column": 36,
         "end_line": 5,
         "line": 5
       },
       "region": "Root.Second",
       "variable": "out"
     },
     "severity": "warning",
     "span": {
       "column": 28,
       "end_column": 40,
       "end_line": 9,
       "line": 9
     }
   }

A model without regions has no ``regions`` key at all:

.. testcode::

   import json

   from pyfcstm.entry.inspect import build_inspect_json

   plain = json.loads(build_inspect_json("region_branch_plain_exits.fcstm"))
   print("regions" in plain)

.. testoutput::

   False

Read the output as follows. ``index`` 0 and 1 are the declaration order, so
``Root.First`` runs before ``Root.Second``. ``Root.First.A`` reports
``Root.First`` as its ``parent_path``, and ``Root`` is composite with no direct
``substates``. A model without regions has no ``regions`` key at all (``False``
in the last block). The full human report, which this page does not repeat,
also carries the usual structure statistics and unrelated warnings such as
``W_UNREFERENCED_VAR``.

.. _inspect-report-region-order:

Order diagnostics
~~~~~~~~~~~~~~~~~

Both order diagnostics are judged on the model as written, before ``active()``
queries are lowered to hidden flag variables. Both look at the regions of one
owner at a time; a region nested in a region is examined when its own owner is
reached, and its accesses also count for the enclosing region. Neither is
produced for a model without regions.

.. list-table:: Order diagnostics
   :header-rows: 1
   :widths: 28 12 60

   * - Code
     - Severity
     - ``refs`` fields
   * - ``I_REGION_BACKWARD_READ``
     - ``info``
     - ``owner_path``, ``reader_region``, ``target_kind`` (``variable`` or ``active``), ``target`` (variable name, or the dotted path of the queried state), ``writer_regions`` (all later regions that write the variable or contain the queried state).
   * - ``W_REGION_BLIND_OVERWRITE``
     - ``warning``
     - ``owner_path``, ``region`` (the later, overwriting region), ``previous_region`` (the nearest earlier region that also writes the variable), ``variable``, ``previous_write_span`` (the lost write).

``I_REGION_BACKWARD_READ`` fires when a region reads a variable, or queries
``active("...")`` for a state, that a *later* region of the same owner writes or
contains. The earlier region runs first, so it sees the previous cycle's value.
It is informational because that is the defined behavior of ordered regions;
the message exists so that the order can be confirmed as intended. It is not
reported when the read follows a write of the same variable in the same action
chain (the region reads its own fresh value), when the writer is an *earlier*
region (a forward read), or when no later region writes the variable.

``W_REGION_BLIND_OVERWRITE`` fires only when an earlier write is lost in every
cycle. All of the following must hold:

* every non-pseudo leaf state of the later region writes the variable
  unconditionally at the top level of its ``during`` actions, or of a
  ``>> during before`` action declared in that region;
* nothing in the later region reads the variable ahead of that write: no guard,
  effect, ``enter``, ``exit``, right-hand side, ``if`` condition or earlier
  statement, and no state of the region that does not write it;
* the later region cannot finish (it has no ``[*]`` exit), contains no nested
  region owner, and has no abstract or ``ref`` action that a handler could use
  to read the variable;
* nothing that runs after the earlier write in the same cycle reads the
  variable, no region in between reads it or has an abstract action, and the
  earlier region has no abstract action.

Aspects declared on the owner or further out run once per cycle around the whole
group of regions, so they neither use nor shield the earlier value and are
ignored. The diagnostic points at the overwriting statement; ``previous_write_span``
names the lost write.

The script below builds the inspect report of six models of ``I_REGION_BACKWARD_READ`` and eight of
``W_REGION_BLIND_OVERWRITE`` and prints which of the two codes each model
triggers; an empty list means neither. ``region_overwrite_middle_reads.fcstm``
belongs to the second family but triggers the first code, which the table
below explains.

.. testcode::

   import json
   from pathlib import Path

   from pyfcstm.entry.inspect import build_inspect_json

   wanted = {"I_REGION_BACKWARD_READ", "W_REGION_BLIND_OVERWRITE"}
   for pattern in ("region_backward_read_*.fcstm", "region_overwrite_*.fcstm"):
       for path in sorted(Path(".").glob(pattern)):
           report = json.loads(build_inspect_json(str(path)))
           print(path.name, sorted({d["code"] for d in report["diagnostics"]} & wanted))

.. testoutput::

   region_backward_read_active.fcstm ['I_REGION_BACKWARD_READ']
   region_backward_read_forward.fcstm []
   region_backward_read_no_writer.fcstm []
   region_backward_read_own_write.fcstm []
   region_backward_read_two_writers.fcstm ['I_REGION_BACKWARD_READ']
   region_backward_read_variable.fcstm ['I_REGION_BACKWARD_READ']
   region_overwrite_aspect.fcstm ['W_REGION_BLIND_OVERWRITE']
   region_overwrite_basic.fcstm ['W_REGION_BLIND_OVERWRITE']
   region_overwrite_can_finish.fcstm []
   region_overwrite_conditional.fcstm []
   region_overwrite_middle_reads.fcstm ['I_REGION_BACKWARD_READ']
   region_overwrite_skip_middle.fcstm ['W_REGION_BLIND_OVERWRITE']
   region_overwrite_some_states.fcstm []
   region_overwrite_uses_old.fcstm []

The message of one finding, as the human report prints it:

.. code-block:: console

   $ pyfcstm inspect -i region_backward_read_two_writers.fcstm --color never
   ...
   [INFO] I_REGION_BACKWARD_READ
     Region 'Root.Reader' reads variable 'level', which is produced by the later region 'Root.First', 'Root.Second'; it sees the value from the previous cycle.
   ...

.. list-table:: Why each model reports or stays quiet
   :header-rows: 1
   :widths: 38 14 48

   * - Model file
     - Reported
     - Reason
   * - ``region_backward_read_variable.fcstm``
     - yes
     - ``Reader`` declared first reads ``level`` in ``seen = level;``; ``Writer`` writes it.
   * - ``region_backward_read_active.fcstm``
     - yes
     - ``active("Root.Writer.Busy")`` queries a state of the later region: ``target_kind`` is ``active``.
   * - ``region_backward_read_two_writers.fcstm``
     - yes
     - Two later regions write ``level``; ``writer_regions`` lists both (the message joins them in one clause).
   * - ``region_backward_read_own_write.fcstm``
     - no
     - ``level = 5; seen = level;`` reads the region's own fresh write.
   * - ``region_backward_read_forward.fcstm``
     - no
     - The writer is declared first; the reader sees the current cycle's value.
   * - ``region_backward_read_no_writer.fcstm``
     - no
     - Nothing in a later region writes ``level``.
   * - ``region_overwrite_basic.fcstm``
     - yes
     - ``Second`` has one leaf that writes ``out = y + 2;`` at the top of ``during`` and cannot finish.
   * - ``region_overwrite_aspect.fcstm``
     - yes
     - The overwrite sits in a region-level ``>> during before`` action, which runs ahead of every ``during``.
   * - ``region_overwrite_skip_middle.fcstm``
     - yes
     - ``Middle`` neither reads nor writes ``out``; ``previous_region`` is ``Root.First``.
   * - ``region_overwrite_uses_old.fcstm``
     - no
     - ``out = out + y + 2;`` uses the earlier value.
   * - ``region_overwrite_conditional.fcstm``
     - no
     - The write is inside ``if [y > 0] { ... }``.
   * - ``region_overwrite_some_states.fcstm``
     - no
     - ``B2`` does not write ``out``, so the default in front survives while the region rests there.
   * - ``region_overwrite_can_finish.fcstm``
     - no
     - ``B -> [*]`` lets the region finish, and a finished region stops writing.
   * - ``region_overwrite_middle_reads.fcstm``
     - no for the overwrite
     - ``Middle`` reads ``out`` between the two writes, so the first write is used. ``Middle`` reading what ``Last`` writes is itself reported as ``I_REGION_BACKWARD_READ``.

.. _inspect-report-region-reachability:

Branch rules and reachability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The reachability of the report and the structural algorithms of
``pyfcstm.verify`` read a composite state as *branches*: a state that owns
regions has one branch per region, a plain composite state is the case of one
branch, and a model without composite states has none. The rules are:

.. list-table:: Branch rules
   :header-rows: 1
   :widths: 30 70

   * - Construct
     - Rule
   * - Entering a state that owns regions
     - Reaches the initial targets of every region.
   * - Ordinary transition leaving a composite state (``Job -> Next``)
     - Counts as reachable only when some child of the state (every region, for an owner) can reach ``[*]``. Otherwise it is reported by ``W_UNREACHABLE_TRANSITION`` with the reason ``owner_never_completes`` and its target by ``W_UNREACHABLE_STATE``.
   * - Forced transition (``!Group -> Next :: Stop``)
     - Leaves from every leaf of the state, so it is reachable with the state. The exits that its expansion adds below the state do not count as a child leaving on its own.
   * - History default (``[H] -> Child``, entered through ``Owner.[H]``)
     - Starts a branch the way the initial transition does.

The script prints the unreachable findings for matching pairs of models, as
the code and the line of each finding. These findings come from the default
static report; ``--enable-verify`` is not needed.

.. literalinclude:: region_owner_never_completes.fcstm
   :language: fcstm
   :caption: region_owner_never_completes.fcstm

.. testcode::

   import json
   from pathlib import Path

   from pyfcstm.entry.inspect import build_inspect_json

   patterns = ("region_owner_*.fcstm", "region_branch_*.fcstm", "region_over_history_initial.fcstm")
   for pattern in patterns:
       for path in sorted(Path(".").glob(pattern)):
           report = json.loads(build_inspect_json(str(path)))
           found = [(d["code"], d["span"]["line"]) for d in report["diagnostics"] if d["code"].startswith("W_UNREACHABLE")]
           print(path.name, found)

.. testoutput::

   region_owner_completes.fcstm []
   region_owner_never_completes.fcstm [('W_UNREACHABLE_STATE', 15), ('W_UNREACHABLE_TRANSITION', 17)]
   region_branch_forced.fcstm []
   region_branch_history.fcstm []
   region_branch_plain_exits.fcstm []
   region_branch_plain_stuck.fcstm [('W_UNREACHABLE_STATE', 9), ('W_UNREACHABLE_TRANSITION', 11)]
   region_over_history_initial.fcstm []

The human report names the reason for the first model:

.. code-block:: console

   $ pyfcstm inspect -i region_owner_never_completes.fcstm --color never
   ...
   [WARN] W_UNREACHABLE_STATE
     State 'Root.Next' is unreachable from the root entry path.
   ...
   [WARN] W_UNREACHABLE_TRANSITION
     Authored transition 'Root.Job' -> 'Root.Next' is unreachable for reasons: owner_never_completes.
   ...

In ``region_owner_never_completes.fcstm`` the ``Monitor`` region has no ``[*]``
exit, so ``Job -> Next`` never runs: ``Root.Next`` is unreachable and the
transition gets ``owner_never_completes``. Giving ``Monitor`` an exit
(``region_owner_completes.fcstm``) removes both findings.

**The one intended output change for a model without regions.** A plain
composite state none of whose children can leave never takes its ordinary
outgoing transitions. ``region_branch_plain_stuck.fcstm`` shows it:
``Group -> Next`` gets ``owner_never_completes`` and ``Root.Next`` is
unreachable, where earlier reports treated the composite state as something the
machine could simply leave. The simulator already behaved that way.
``region_branch_plain_exits.fcstm`` (``B -> [*]``), ``region_branch_forced.fcstm``
(a forced transition) and ``region_branch_history.fcstm`` (a forced transition
and a ``[H]`` default) print nothing.

Known over-approximations
~~~~~~~~~~~~~~~~~~~~~~~~~

Three approximations stay in the structural analysis. All three err toward
*missing* a finding, so an empty report is not a proof of reachability.

#. A composite state entered only through ``Owner.[H]`` keeps its ordinary
   initial child reachable. In ``region_over_history_initial.fcstm`` ``Work`` is
   entered only through ``Work.[H]``, whose default is ``Slow``; ``Fast`` can
   never be entered, and the script above prints no finding for it.
#. The algorithms of ``pyfcstm.verify`` judge the machine that runs, where a
   forced declaration is a relay, and stay guard-agnostic about it. A state
   behind a composite state that only a forced declaration can take elsewhere may
   still be listed as reachable.
#. A single forced declaration is marked as a whole as soon as one of its
   expansions starts from an unreachable state. This aggregation predates regions.

With ``--enable-verify`` the topology algorithms
(``topological_reachable_set``, ``unreachable_states``,
``strongly_connected_components``, ``topological_finite``,
``topological_inevitable_terminator`` and
``event_emission_to_consumer_reachable``) run on a model with regions as on any
other model. A state is unreachable when no reachable position holds it. A leaf
has no way out when the branches around it cannot all finish (the report calls
that a deadlock). The topology is non-terminating when some reachable position
can repeat or cannot move. The solver-local algorithms run inside regions; the
lifecycle check of a state inside a region is skipped.

jsfcstm boundary
~~~~~~~~~~~~~~~~

The jsfcstm structural inspector does not produce a report for a model with
regions. ``isInspectable(machine)`` returns ``false`` for a machine that declares
regions or uses ``active()`` queries, and ``inspectModel`` throws an ``Error``
(``inspectModel does not support machines with regions or active() queries``)
instead of returning one. The jsfcstm semantic analysis still checks such a
model, and the reachability rule above, including ``owner_never_completes`` for
models without regions, is implemented in jsfcstm as well. ``pyfcstm inspect``
is the way to get the order diagnostics and the ``regions`` array.

Which machine a finding is judged on
------------------------------------
The report and every finding that describes what was written are judged on the
model as written: its states, transitions, history entries, forced declarations
and ``active()`` queries as they stand in the text. The findings of the verify
pipeline say how a machine behaves instead, and are judged on the machine that
runs. History, ``active()`` and forced declarations are lowered into plain FCSTM
with hidden variables, relay transitions and gate states, and the text a model
exports is that plain FCSTM, so a model and its exported text give the same
verify findings. A condition on ``active("...")`` is judged like any condition
over the hidden flag variable that nothing constrains.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Judged on
     - Codes
   * - The machine that runs
     - ``I_NONTRIVIAL_SCC``, ``W_TOPOLOGICAL_NOEXIT``, ``I_TOPOLOGICAL_NON_TERMINATING``, ``W_EVENT_UNREACHABLE_EMIT``, ``W_DEAD_GUARD``, ``W_GUARD_TAUTOLOGY``, ``W_EFFECT_SMT_NO_OP``, ``I_EFFECT_GUARD_CONTRADICT``, ``W_TRANSITION_SHADOWED``, ``I_ENTER_DURING_CONTRADICT``, ``W_COMPOSITE_INIT_INCOMPLETE``
   * - The model as written
     - every other code, including ``W_FORCED_GUARD_UNSAT``, which judges a forced declaration that the machine that runs no longer carries

The machine that runs has the lowering in it, so a finding can name a hidden
variable such as ``__forced_0`` or ``__hist_goto``, a generated gate state, or a
transition that the text never wrote, and a model that is written correctly can
get a finding about them: a relay that lowers the hidden variable of its own
guard is reported as ``I_EFFECT_GUARD_CONTRADICT``. Such a finding points at the
construct it was lowered from. Without ``--enable-verify`` nothing is judged on
the machine that runs. A combo trigger is a different case: the generated guard
of its relay is reported once, as the term of the trigger it came from, by the
``W_COMBO_*`` code of that term.

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
   * - ``input``
     - ``cycle``
     - All four flags are false; the environment supplies each cycle's value.
   * - ``param``
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
