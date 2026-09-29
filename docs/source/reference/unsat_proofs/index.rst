UNSAT proof API reference
=========================

This reference covers the standalone APIs in :mod:`pyfcstm.solver.proof`,
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
     - ``node_id``, native ``rule``, ordered proof ``parents``, optional ``conclusion``, other term ``operands``, ``parameters``, alternative ``input_occurrences``, ``open_hypotheses``, ``discharged_hypotheses``, ``local_check``, binder ``bindings``, ``inference_kind`` and optional ``certificate``, ``cardinality`` and ``interval`` evidence.
   * - ``ProofParameter``
     - ``kind`` and textual ``value``. Kinds: integer, double, rational, symbol, sort, expression or declaration.
   * - ``ArithmeticCertificate``
     - ``bounds``, normalized exact ``weights``, resulting ``constant`` and Boolean ``strict``. Each ``LinearBound`` retains ``term_id``, ``negated``, term/coefficient pairs, ``constant`` and relation ``le|lt|eq`` against zero.
   * - ``CardinalityCertificate``
     - Temporary ``assumptions``, ``constraint_id``, required ``constraint_value``, known Boolean ``assignments`` and weighted ``contributions``. ``minimum`` and ``maximum`` are exact integer totals.
   * - ``CountContribution``
     - Boolean ``term_id``, signed integer ``weight`` and its exact ``minimum`` / ``maximum`` contribution.
   * - ``IntervalCertificate``
     - Local normalized ``bounds``, ordered ``steps``, and exactly one of ``conflict`` or ``equality``. Result pairs are zero-based step indices. Contradictions use disjoint ranges of one term; equality uses equal closed singleton ranges of an equality alternative in the conclusion.
   * - ``TermEquality``
     - ``left_id``, ``right_id`` and ``bound_indices``: one local equality or two opposing non-strict bounds establishing equal terms.
   * - ``IntervalStep``
     - ``term_id``, exact rational ``lower`` / ``upper`` (``None`` denotes infinity), ``lower_open`` / ``upper_open``, deduction ``rule``, prior-step ``premises`` and optional ``bound_index`` for a linear deduction. ``substitutions`` retains local equalities. A ``congruence`` step transfers its one source range; ``congruence_sum`` checks exact cancellation of equal terms and records the resulting constant singleton. Steps unrelated to the final result are removed.
   * - ``ReadingBlock``
     - ``block_id``, ``kind``, conclusion ``claims``, ``premise_block_ids``, ``active_hypotheses``, ``evidence_node_ids``, ``source_links``, folded ``detail_block_ids``, optional ``title_en`` and ``title_zh``.
   * - ``ProofReading``
     - ``query_id``, ``solver_status``, optional ``root_id``, ``status``, visible ``blocks``, ``sources``, ``gaps`` and hidden ``detail_blocks``. The bound graph is shared with the report, not serialized twice within the reading.

``local_check`` is ``not_run|checked|trusted|unsupported|invalid``. Reading kinds
are ``input``, ``assumption``, ``discharge``, ``arithmetic``, ``cardinality``, ``order``, ``logical``,
``division_identity``, ``remainder_lower``, ``remainder_upper``,
``floor_lower``, ``floor_upper``, ``real_division``, ``arithmetic_identity``,
``even_power``, ``root_nonnegative``, ``root_identity``, ``interval``,
``equality``, ``rewrite``, ``definition``, ``resolution``, ``opaque`` and
``domain``. Native bound variables are rendered as de Bruijn indices: ``#0``
is the innermost variable, with names/sorts retained in ``bindings``.
Solver-introduced symbols are not decoded into fabricated source variables.
The ``order`` category checks that equality/order alternatives cover all signs
of one normalized arithmetic difference. Shared nonlinear terms can be treated
as atoms for this check; it does not certify their multiplication properties.
Division categories match the guarded Euclidean identity and remainder bounds
from `SMT-LIB Ints <https://smt-lib.org/theories-Ints.shtml>`_. The zero-divisor
alternative remains in the proof; no division property is inferred at zero.
Power categories check positive even integer exponents and principal square
root sign/identity deductions. Square root deductions require a nonnegative
radicand, established by the local premises, clause alternatives or a numeric
literal. These checks also recognize direct contradictions from local premises;
they do not use unrelated query assertions to justify an intermediate step.
Interval deductions use exact rational bounds, open endpoints, integer rounding,
products, repeated-factor squares and conditionally selected arithmetic branches.
Only local premises and temporary negations of conclusion alternatives establish
bounds. The text exposes those assumptions, every retained range deduction and
the final contradiction or singleton equality. Bounded propagation can leave a
lemma unsupported when no certificate is found; it never upgrades that result
to a checked inference merely because the overall query is UNSAT.

Floor checks establish ``to_int(x) <= x < to_int(x) + 1``. Real division
checks preserve the nonzero-divisor condition. Equivalent ``x*x`` and ``x^2``
terms share an arithmetic atom; cancellation still requires exact coefficients.
When native weights are unavailable, reconstruction may combine two local
bounds with exact cancelling weights. Positive integral powers can propagate
ranges when the exponent has a checked singleton value. All finite endpoints
remain exact rationals, including extremely small or large values.

When the initial arithmetic configuration returns a known arithmetic or proof
production limitation, capture retries with Z3 arithmetic solver 6, the exact
original assertions and the same total deadline. Only the resulting execution
is exported. Timeout and unresolved UNKNOWN outcomes remain explicit.

``reading.to_text(language="en", detail="standard")`` accepts ``en`` or ``zh``
and returns plain text with a final newline. Reading detail is independent of
core minimization and rule checking:

* ``brief`` gives a guide: inputs, key deductions and the contradiction. Linear
  combinations show their result rather than every coefficient. Long formulas
  are references; this view is explicitly not a standalone derivation.
* ``standard`` is the default. It folds exclusively used mechanical premises
  into their consuming deduction, keeping arithmetic certificates, local
  assumptions, discharge boundaries and unsupported steps visible. Shared long
  formulas have complete definitions at the end of the text.
* ``detailed`` renders the full reading and expands caller-supplied domain folds.
  It does not print every native solver node; the captured graph remains the
  separate evidence artifact.

Changing detail does not solve again, mutate the report, minimize its core or
upgrade ``rule_check``. All levels preserve explicit gaps. Formula references
such as ``[[t12]]`` identify terms in the report graph;
``reading.get_term_text("t12")`` returns the exact unabridged formula offline.
Unknown term IDs raise ``KeyError``; a reading without a graph raises
``ValueError``. The detailed view and formula expansion also work after loading
a serialized report without Z3.

``get_block(id)`` and ``get_source(id)`` look
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
