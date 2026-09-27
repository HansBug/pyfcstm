UNSAT proof API reference
=========================

This reference covers the standalone APIs in :mod:`pyfcstm.solver.proof`,
:mod:`pyfcstm.solver.proof_rules`, :mod:`pyfcstm.solver.proof_text`,
:mod:`pyfcstm.solver.unsat` and :mod:`pyfcstm.solver.symbols`.
Examples are in :doc:`/tutorials/unsat_proofs/index` and
:doc:`/how_to/unsat_proofs/index`. Existing BMC commands are unchanged.

Inputs and entry point
----------------------

.. code-block:: python

    UnsatConstraint(stable_id, expressions, source=None)
    UnsatQuery(query_id, constraints, background=())
    explain_unsat(query, *, mode="proof", minimize=False, timeout_ms=None,
                  names=None, extensions=None)

``stable_id`` and ``query_id`` are nonempty strings. ``expressions`` is a
nonempty iterable of Z3 Boolean expressions. All expressions in a query share
one context. IDs are unique across constraints and background. Empty queries
are legal and SAT. Python ``True`` is not a Z3 expression; use
``z3.BoolVal(True)``. Collection inputs are frozen as tuples.

.. list-table:: Entry options
   :header-rows: 1
   :widths: 22 28 50

   * - Parameter
     - Default / accepted values
     - Contract
   * - ``mode``
     - ``"proof"``; ``"core"``
     - Native evidence or checked core evidence only.
   * - ``minimize``
     - ``False``; Boolean
     - Delete removable groups and reprove the selected subset in proof mode. Not cardinality optimization.
   * - ``timeout_ms``
     - ``None``; positive integer excluding Boolean
     - Shared cooperative deadline in milliseconds. ``None`` is unbounded.
   * - ``names``
     - ``None``; ``SymbolNames``
     - Actual symbol bindings registered with ``register(symbol, display)``. Colliding display names are rejected.
   * - ``extensions``
     - ``None``; ``ProofExtensions``
     - Per-call rule interpreters, source adapter and reading folders; no global registry.

``explain_unsat_core(query, *, selected_ids=None, minimize=True,
timeout_ms=None)`` is the lower-level core API. Its default minimization is
``True``, unlike ``explain_unsat``. ``selected_ids`` explicitly chooses removable
occurrences; IDs must be unique and known. Even an explicit selection is
independently rechecked without restoring omitted conditions. Use
``minimize=False`` to preserve that selection. Its ``UnsatCoreResult.query``
retains native expressions and caller handles; serialize ``UnsatReport`` for
portable evidence instead.

Report fields
-------------

``explain_unsat`` returns ``UnsatReport``. Optional fields use ``None`` in
Python and ``null`` in JSON.

.. list-table:: Complete report field groups
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Meaning and values
   * - ``query_id``
     - Original caller identity, never a property verdict.
   * - ``solver_status``
     - ``sat``, ``unsat``, ``unknown`` or ``timeout``.
   * - ``proof_status``
     - ``captured``, ``invalid``, ``unavailable`` or ``not_requested``. Captured does not imply independent certification.
   * - ``proof``
     - Selected ``ProofGraph`` or ``None``. Invalid evidence can be retained for inspection.
   * - ``proof_scope``
     - ``full``, ``core`` or ``none``; identifies which conjunction the selected graph proves.
   * - ``full_proof``
     - Original graph after a reduced graph is accepted; otherwise ``None``. On failed reduction, the original remains in ``proof``.
   * - ``input_check``
     - ``not_run``, ``passed`` or ``failed``; asserted leaves versus exact inputs.
   * - ``scope_check``
     - ``not_run``, ``passed``, ``partial`` or ``failed``; local assumptions and the False root.
   * - ``rule_check``
     - ``not_run``, ``complete``, ``partial`` or ``failed``. Trusted mechanical steps make independent rule checking partial.
   * - ``gaps``
     - Tuple of ``ProofGap(reason, node_id, detail)``. ``node_id`` may be ``None``. Reasons include ``unsupported_rule``, ``invalid_inference``, ``open_hypotheses`` and ``non_false_root``.
   * - ``reading``
     - ``ProofReading`` or ``None`` if assembly could not finish.
   * - ``reading_status``
     - ``complete``, ``partial`` or ``not_requested``; does not duplicate ``rule_check``.
   * - ``source_status``
     - ``absent``, ``partial`` or ``complete``. Complete means all used named input groups have descriptions; it does not prove uniquely necessary spans.
   * - ``core``
     - ``CoreEvidence`` when core work was requested, otherwise ``None``.
   * - ``stop_reason``
     - Optional interruption/unavailability text. Read it even when the original solve was UNSAT.

``CoreEvidence`` contains ``constraint_ids`` (all original removable groups),
``background_ids`` (fixed groups), ``core_ids`` (verified subset or ``None``),
``core_check`` (``verified|not_checked|sat|unknown|timeout``),
``subset_minimality`` (``proven|not_proven``), ``reduction``
(``raw|partial_minimized|subset_minimal``), and ``stop_reason`` for core work.
A verified ``core_ids=()`` means the background alone is contradictory.

For example, ``solver_status="unsat", proof_status="captured",
reading_status="not_requested"`` is possible when assembly times out after
capture. ``rule_check="partial", reading_status="complete"`` is possible
with trusted mechanical rules. ``core.subset_minimality="proven",
proof_scope="full"`` is possible when reduced reproof fails: the core evidence
and chosen graph have separately qualified guarantees.

Evidence and reading data
-------------------------

.. list-table:: Data records
   :header-rows: 1
   :widths: 25 75

   * - Record
     - Fields
   * - ``ProofGraph``
     - ``execution_id``, ``root_id``, topological ``nodes`` and ``terms``, original ``inputs``, and ``source_bindings``. ``node(id)`` and ``term(id)`` look up exact records.
   * - ``ProofTerm``
     - ``term_id``, ``kind`` (literal/algebraic/constant/application/variable/quantifier), ``sort``, ``operator``, child ``arguments``, ``value``, binder ``bindings``, ``operator_kind`` (builtin/uninterpreted), and indexed-operator ``parameters``.
   * - ``ProofInput``
     - ``occurrence_id``, ``constraint_id``, zero-based ``expression_index``, ``term_id`` and Boolean ``background``. Unused submitted expressions remain recorded.
   * - ``ProofNode``
     - ``node_id``, native ``rule``, ordered proof ``parents``, optional ``conclusion``, other term ``operands``, ``parameters``, alternative ``input_occurrences``, ``open_hypotheses``, ``discharged_hypotheses``, ``local_check``, binder ``bindings``, ``inference_kind`` and optional ``certificate``.
   * - ``ProofParameter``
     - ``kind`` and textual ``value``. Kinds: integer, double, rational, symbol, sort, expression or declaration.
   * - ``ArithmeticCertificate``
     - ``bounds``, normalized exact ``weights``, resulting ``constant`` and Boolean ``strict``. Each ``LinearBound`` retains ``term_id``, ``negated``, term/coefficient pairs, ``constant`` and relation ``le|lt|eq`` against zero.
   * - ``ReadingBlock``
     - ``block_id``, ``kind``, conclusion ``claims``, ``premise_block_ids``, ``active_hypotheses``, ``evidence_node_ids``, ``source_links``, folded ``detail_block_ids``, optional ``title_en`` and ``title_zh``.
   * - ``ProofReading``
     - ``query_id``, ``solver_status``, optional ``root_id``, ``status``, visible ``blocks``, ``sources``, ``gaps`` and hidden ``detail_blocks``. The bound graph is shared with the report, not serialized twice within the reading.

``local_check`` is ``not_run|checked|trusted|unsupported|invalid``. Reading kinds
are ``input``, ``assumption``, ``discharge``, ``arithmetic``, ``logical``,
``equality``, ``rewrite``, ``definition``, ``resolution``, ``opaque`` and
``domain``. Native bound variables are rendered as de Bruijn indices: ``#0``
is the innermost variable, with names/sorts retained in ``bindings``.
Solver-introduced symbols are not decoded into fabricated source variables.

``reading.to_text(language="en")`` accepts ``en`` or ``zh`` and returns complete
plain text with a final newline. ``get_block(id)`` and ``get_source(id)`` look
up records. ``expand(id)`` returns folded details when present, otherwise direct
premise blocks. These methods raise ``KeyError`` for unknown IDs.
``to_canonical()`` returns detached JSON-compatible data. At the report level,
``UnsatReport.from_canonical(data)`` reconstructs and validates it without Z3.
Unsupported fields, wrong types, duplicate identities, missing references,
cycles and inconsistent report states raise ``ValueError``.

Extension and source contracts
------------------------------

``ProofExtensions(rule_handlers=(), source_adapter=None, reading_folders=())``
freezes its two collections. Application callbacks are trusted code, invoked
synchronously; their unexpected exceptions are not swallowed.

* ``ProofRuleHandler(rule, interpret)`` selects one exact native rule.
  ``interpret(node, graph)`` returns ``RuleAnalysis(kind, local_check="trusted")``.
  Allowed kinds are logical/equality/rewrite/definition/resolution/opaque;
  checks are checked/trusted/unsupported/invalid. The input/scope rules
  ``asserted``, ``hypothesis`` and ``lemma`` cannot be overridden.
* ``SourceAdapter.describe(handle)`` returns ``SourceDescription``. The default
  accepts an existing description. ``bindings()`` returns ``SourceBinding``
  records; the default is empty.
* ``SourceBinding(expression, source, relation="construction")`` binds an exact
  original-context expression. Relation is construction/context, never logical.
  Unmatched expressions add no assumptions or term links. ``ProofSource`` stores
  the matched ``term_id``, ``description`` and ``relation`` in the graph.
* ``SourceDescription(source_id, title, document_id=None, span=None,
  excerpt=None)`` uses nonempty identity/title strings. Optional document/excerpt
  values are strings. A span has four positive integer coordinates with exclusive
  end, and is copied to a tuple. Conflicting descriptions for one ID are errors.
* ``SourceLink(source_id, relation, occurrence_id=None, term_id=None)`` keeps
  logical/construction/context separate. An occurrence link names an actual input;
  a term link records a construction/context attachment.
* ``ReadingFolder(propose)`` calls ``propose(reading)`` for iterable
  ``FoldProposal(root_id, block_ids, premise_block_ids, claims,
  active_hypotheses, title_en, title_zh)`` records. Both titles are required.
  Removed or unknown blocks, duplicate/disconnected slices, changed claims,
  missing premises and hidden live hypotheses are rejected.

Errors and operating limits
---------------------------

Bad input/group/context/option types raise ``TypeError`` or ``ValueError`` as
specified by the generated API. Invalid examples include ``minimize=1``,
``timeout_ms=0``, a Python Boolean in ``expressions``, and a source expression
from a different context. Supply a Boolean option, positive integer deadline,
Z3 Boolean expression and original-context binding respectively.

The solver result is not a complete independent certificate; unsupported
native rules remain partial. Linear arithmetic checks do not claim general
nonlinear or quantified proof reconstruction. Source mappings report caller
metadata, not a source-language semantics proof. Text/proof shape can vary
with Z3 versions. Text is not the machine protocol; use the canonical records.
No helper writes files or sends data to a service. Offline loading validates a
snapshot's contract, not its authenticity. No minimum-cardinality core,
shortest-proof, hard callback deadline or cross-execution node identity is
promised.
