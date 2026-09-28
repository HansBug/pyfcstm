"""Portable evidence and the public entry point for native UNSAT proofs.

The evidence contains identifiers and plain Python values. Native Z3 objects
belong to one invocation and never escape into its serialized proof graph.
"""

from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Optional, Tuple


@dataclass(frozen=True)
class SourceDescription:
    """Portable caller-supplied source metadata; never a logical premise.

    :param source_id: Source identity within the report.
    :param title: Human description.
    :param document_id: Optional source document identity.
    :param span: One-based start/end line and column; end is exclusive.
    :param excerpt: Optional authored text for offline reading.
    """

    source_id: str
    title: str
    document_id: Optional[str] = None
    span: Optional[Tuple[int, int, int, int]] = None
    excerpt: Optional[str] = None

    def __post_init__(self):
        for value in (self.source_id, self.title):
            if not isinstance(value, str) or not value:
                raise ValueError('source identity and title must be nonempty strings')
        for value in (self.document_id, self.excerpt):
            if value is not None and not isinstance(value, str):
                raise ValueError('source document and excerpt must be strings or None')
        if self.span is not None:
            if not isinstance(self.span, (tuple, list)) or len(self.span) != 4:
                raise ValueError('source span requires four coordinates')
            span = tuple(self.span)
            if any(type(coordinate) is not int or coordinate < 1 for coordinate in span) or span[2:] < span[:2]:
                raise ValueError('invalid source span')
            object.__setattr__(self, 'span', span)


@dataclass(frozen=True)
class SourceLink:
    """An explicit source relationship rather than a necessity claim.

    :param source_id: Referenced description.
    :param relation: ``logical``, ``construction`` or ``context``.
    :param occurrence_id: Exact input occurrence when applicable.
    :param term_id: Exact expression term for a construction/context attachment.
    """

    source_id: str
    relation: str
    occurrence_id: Optional[str] = None
    term_id: Optional[str] = None


@dataclass(frozen=True)
class SourceBinding:
    """Bind an original expression to application construction or context.

    :param expression: Exact Z3 expression in the query's original context.
    :param source: Description or application handle accepted by the adapter.
    :param relation: ``construction`` or ``context``; metadata cannot add a
        logical premise. Unused expressions do not acquire proof references.
    """

    expression: object
    source: object
    relation: str = 'construction'

    def __post_init__(self):
        if self.relation not in ('construction', 'context'):
            raise ValueError('source binding relation must be construction or context')


@dataclass(frozen=True)
class ProofSource:
    """Portable source binding to a term in a particular proof execution.

    :param term_id: Matched term, retaining expression identity rather than text.
    :param description: Portable source description.
    :param relation: Construction or contextual relationship.
    """

    term_id: str
    description: SourceDescription
    relation: str


class SourceAdapter:
    """Describe application metadata, with plain descriptions supported directly.

    Subclasses may override :meth:`describe` and :meth:`bindings`.
    """

    def describe(self, handle) -> SourceDescription:
        """Return a portable description; application objects need an override."""
        if not isinstance(handle, SourceDescription):
            raise TypeError('source requires SourceDescription or a SourceAdapter')
        return handle

    def bindings(self) -> Tuple[SourceBinding, ...]:
        """Return exact expression/source bindings; default is no bindings."""
        return ()


@dataclass(frozen=True)
class ProofExtensions:
    """Explicit per-call extensions; no mutable global registration.

    :param rule_handlers: Additional proof-rule interpreters.
    :param source_adapter: Caller metadata description adapter.
    :param reading_folders: Domain-specific checked reading proposals.
    """

    rule_handlers: tuple = ()
    source_adapter: Optional[SourceAdapter] = None
    reading_folders: tuple = ()

    def __post_init__(self):
        from .rules import _index_handlers

        object.__setattr__(self, 'rule_handlers', tuple(self.rule_handlers))
        object.__setattr__(self, 'reading_folders', tuple(self.reading_folders))
        _index_handlers(self.rule_handlers)


@dataclass(frozen=True)
class ProofParameter:
    """One native declaration parameter, preserving its kind and exact value.

    :param kind: Native parameter kind name.
    :param value: Exact textual value, including rational coefficients.
    """

    kind: str
    value: str


@dataclass(frozen=True)
class ProofTerm:
    """One shared expression node in the native proof's term table.

    :param term_id: Identity within one proof graph.
    :param kind: Literal, algebraic real, constant, application, variable or quantifier.
    :param sort: Native sort spelling.
    :param operator: Native operator spelling, or quantifier kind.
    :param arguments: Child term identifiers in native order.
    :param value: Exact literal value or constant display name. Algebraic reals
        retain their native root-object expression and are not rational coefficients.
    :param bindings: Bound variable names and sorts for quantifiers.
    :param operator_kind: ``builtin`` or ``uninterpreted``; spelling alone
        cannot distinguish an authored function from a native operator.
    :param parameters: Native indexed-operator parameters, for example extract bounds.
    """

    term_id: str
    kind: str
    sort: str
    operator: str
    arguments: Tuple[str, ...] = ()
    value: str = ''
    bindings: Tuple[Tuple[str, str], ...] = ()
    operator_kind: str = 'builtin'
    parameters: Tuple[ProofParameter, ...] = ()


@dataclass(frozen=True)
class ProofInput:
    """One occurrence of an expression in the caller's exact conjunction.

    :param occurrence_id: Identity distinct from expression identity.
    :param constraint_id: Named input group.
    :param expression_index: Position within that group.
    :param term_id: Shared expression identifier.
    :param background: Whether the group is fixed during minimization.
    """

    occurrence_id: str
    constraint_id: str
    expression_index: int
    term_id: str
    background: bool


@dataclass(frozen=True)
class ProofNode:
    """One native proof inference, without expanding shared subproofs.

    :param node_id: Identity within the containing graph.
    :param rule: Native inference name.
    :param parents: Ordered subproof identifiers.
    :param conclusion: Conclusion term identifier, if the node has a fact.
    :param operands: Other non-proof term arguments.
    :param parameters: Native declaration parameters.
    :param input_occurrences: Alternative origins of an asserted expression.
    :param open_hypotheses: Local hypotheses still in scope.
    :param discharged_hypotheses: Hypotheses closed by this inference.
    :param local_check: Extent of local inference checking.
    :param bindings: Native bound-variable names and sorts for proof binders.
    :param inference_kind: Semantic category used to assemble readable deductions.
    :param certificate: Optional exact, normalized arithmetic certificate.
    :param cardinality: Optional checked Boolean counting contradiction.
    :param interval: Optional exact local interval contradiction.
    """

    node_id: str
    rule: str
    parents: Tuple[str, ...]
    conclusion: Optional[str]
    operands: Tuple[str, ...] = ()
    parameters: Tuple[ProofParameter, ...] = ()
    input_occurrences: Tuple[str, ...] = ()
    open_hypotheses: Tuple[str, ...] = ()
    discharged_hypotheses: Tuple[str, ...] = ()
    local_check: str = 'not_run'
    bindings: Tuple[Tuple[str, str], ...] = ()
    inference_kind: str = 'opaque'
    certificate: Optional['ArithmeticCertificate'] = None
    cardinality: Optional['CardinalityCertificate'] = None
    interval: Optional['IntervalCertificate'] = None


@dataclass(frozen=True)
class TermEquality:
    """Equal arithmetic terms established by local normalized bounds.

    :param left_id: First equal term.
    :param right_id: Second equal term, of the same sort.
    :param bound_indices: One equality bound or two opposing non-strict bounds.
    """

    left_id: str
    right_id: str
    bound_indices: Tuple[int, ...]


@dataclass(frozen=True)
class IntervalStep:
    """One range deduction with exact rational endpoints and prior evidence.

    :param term_id: Arithmetic expression bounded by this step.
    :param lower: Rational lower endpoint, or None for negative infinity.
    :param upper: Rational upper endpoint, or None for positive infinity.
    :param lower_open: Whether the lower endpoint is excluded.
    :param upper_open: Whether the upper endpoint is excluded.
    :param rule: Literal, linear, arithmetic, conditional or intersection rule.
    :param premises: Zero-based indices of earlier interval steps.
    :param bound_index: Index of a local normalized premise, for linear steps.
    :param substitutions: Local equalities used to transfer an expression range.
    """

    term_id: str
    lower: Optional[str]
    upper: Optional[str]
    lower_open: bool
    upper_open: bool
    rule: str
    premises: Tuple[int, ...] = ()
    bound_index: Optional[int] = None
    substitutions: Tuple[TermEquality, ...] = ()


@dataclass(frozen=True)
class IntervalCertificate:
    """Exact local range evidence for a contradiction or arithmetic equality.

    :param bounds: Normalized local premises and negated conclusion literals.
    :param steps: Ordered exact deductions, including integer rounding.
    :param conflict: Indices of two incompatible ranges, or None.
    :param equality: Indices of equal singleton ranges proving an equality, or None.
    """

    bounds: Tuple['LinearBound', ...]
    steps: Tuple[IntervalStep, ...]
    conflict: Optional[Tuple[int, int]]
    equality: Optional[Tuple[int, int]] = None


@dataclass(frozen=True)
class CountContribution:
    """An exact weighted Boolean contribution, with unknown values in [0, 1].

    :param term_id: Boolean argument of a native cardinality constraint.
    :param weight: Signed integer weight multiplying its truth indicator.
    :param minimum: Smallest possible weighted contribution.
    :param maximum: Largest possible weighted contribution.
    """

    term_id: str
    weight: int
    minimum: int
    maximum: int


@dataclass(frozen=True)
class CardinalityCertificate:
    """A Boolean weighted sum incompatible with a required constraint truth.

    :param assumptions: Conclusion-clause literals temporarily assumed false.
    :param constraint_id: Native Boolean cardinality expression.
    :param constraint_value: Truth required by a premise or temporary assumption.
    :param assignments: Known expression truth values from those same premises.
    :param contributions: Checked interval for each weighted Boolean argument.
    """

    assumptions: Tuple[str, ...]
    constraint_id: str
    constraint_value: bool
    assignments: Tuple[Tuple[str, bool], ...]
    contributions: Tuple[CountContribution, ...]

    @property
    def minimum(self) -> int:
        """Return the lower bound of the weighted sum."""
        return sum(item.minimum for item in self.contributions)

    @property
    def maximum(self) -> int:
        """Return the upper bound of the weighted sum."""
        return sum(item.maximum for item in self.contributions)


@dataclass(frozen=True)
class LinearBound:
    """Exact affine relation used by a native arithmetic certificate.

    :param term_id: Original literal, negated when ``negated`` is true.
    :param negated: Whether this is a negated conclusion-clause literal.
    :param coefficients: Term identifiers and rational coefficients.
    :param constant: Exact additive constant.
    :param relation: ``le``, ``lt`` or ``eq`` against zero.
    """

    term_id: str
    negated: bool
    coefficients: Tuple[Tuple[str, str], ...]
    constant: str
    relation: str


@dataclass(frozen=True)
class ArithmeticCertificate:
    """A checked rational linear combination resulting in a contradiction.

    :param bounds: Normalized input relations.
    :param weights: Exact coefficients for the normalized bounds, in bound order.
        Inequality weights use the absolute native coefficient; the original
        signed values remain in the proof node parameters.
    :param constant: Resulting constant after all variable terms cancel.
    :param strict: Whether the resulting upper bound is strict.
    """

    bounds: Tuple[LinearBound, ...]
    weights: Tuple[str, ...]
    constant: str
    strict: bool


@dataclass(frozen=True)
class ProofGap:
    """An explicit unavailable or invalid piece of proof evidence.

    :param reason: Machine-readable reason.
    :param node_id: Affected inference, if any.
    :param detail: Human-readable diagnostic.
    """

    reason: str
    node_id: Optional[str]
    detail: str


@dataclass(frozen=True)
class ProofGraph:
    """Shared native evidence for one execution of an exact query.

    :param execution_id: Identity of this proof-producing solver run.
    :param root_id: Refutation root node.
    :param nodes: Topologically ordered proof nodes.
    :param terms: Shared expression table.
    :param inputs: Original input occurrences, including unused conditions.
    :param source_bindings: Portable construction/context attachments to exact terms.
    """

    execution_id: str
    root_id: str
    nodes: Tuple[ProofNode, ...]
    terms: Tuple[ProofTerm, ...]
    inputs: Tuple[ProofInput, ...]
    source_bindings: Tuple[ProofSource, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, '_nodes', MappingProxyType({n.node_id: n for n in self.nodes}))
        object.__setattr__(self, '_terms', MappingProxyType({t.term_id: t for t in self.terms}))

    def node(self, node_id: str) -> ProofNode:
        """Look up a node; unknown identifiers raise :class:`KeyError`."""
        return self._nodes[node_id]

    def term(self, term_id: str) -> ProofTerm:
        """Look up a term; unknown identifiers raise :class:`KeyError`."""
        return self._terms[term_id]


@dataclass(frozen=True)
class UnsatReport:
    """Solver outcome and separately qualified evidence for one exact query.

    :param query_id: Caller-supplied query identity, not a property verdict.
    :param solver_status: SAT, UNSAT, UNKNOWN or timeout outcome.
    :param proof_status: Captured, invalid, unavailable or not requested.
    :param proof: Portable evidence when captured.
    :param input_check: Whether asserted leaves match the submitted inputs.
    :param stop_reason: Reason evidence could not be produced.
    :param scope_check: Whether the refutation closes all local hypotheses.
    :param rule_check: Independent rule checking, separate from readability.
    :param gaps: Explicit unsupported or invalid evidence.
    :param reading: Assembled reading, or ``None`` if assembly could not finish.
    :param reading_status: Complete, partial or not requested.
    :param source_status: Absent, partial or complete input source descriptions.
    :param proof_scope: Full conjunction, selected core, or no proof.
    :param full_proof: Original graph retained after reduced reproof succeeds.
    :param core: Portable core/minimization evidence when requested.
    """

    query_id: str
    solver_status: str
    proof_status: str
    proof: Optional[ProofGraph]
    input_check: str = 'not_run'
    stop_reason: Optional[str] = None
    scope_check: str = 'not_run'
    rule_check: str = 'not_run'
    gaps: Tuple[ProofGap, ...] = ()
    reading: Optional['ProofReading'] = None
    reading_status: str = 'not_requested'
    source_status: str = 'absent'
    proof_scope: str = 'none'
    full_proof: Optional[ProofGraph] = None
    core: Optional['CoreEvidence'] = None

    def to_canonical(self) -> dict:
        """Return a JSON-compatible snapshot with no live solver objects."""
        return asdict(self)

    @classmethod
    def from_canonical(cls, data: dict) -> 'UnsatReport':
        """Load a detached snapshot without importing Z3.

        :param data: A canonical mapping, including one read with ``json.load``.
        :return: Typed evidence and navigable reading data.
        :raises ValueError: On malformed fields, references or cycles.

        Loading checks the data contract, not the authenticity of supplied
        solver evidence or plugin claims. It does not independently certify Z3.

        Example::

            >>> original = UnsatReport('empty', 'sat', 'unavailable', None)
            >>> UnsatReport.from_canonical(original.to_canonical()).solver_status
            'sat'
        """
        from .io import load_report

        return load_report(data)


@dataclass(frozen=True)
class CoreEvidence:
    """Portable core selection relative to the original named conjunction.

    :param constraint_ids: All original removable condition groups.
    :param background_ids: Fixed groups retained in all checks.
    :param core_ids: Rechecked subset, or ``None`` when unavailable.
    :param core_check: Independent subset check result.
    :param subset_minimality: ``proven`` or ``not_proven``; never cardinality optimality.
    :param reduction: Extent of deletion-based shrinking.
    :param stop_reason: Optional interruption diagnostic.
    """

    constraint_ids: Tuple[str, ...]
    background_ids: Tuple[str, ...]
    core_ids: Optional[Tuple[str, ...]]
    core_check: str
    subset_minimality: str
    reduction: str
    stop_reason: Optional[str]

    @classmethod
    def from_result(cls, result):
        """Detach a core result from its native query and application handles."""
        return cls(tuple(group.stable_id for group in result.query.constraints),
                   tuple(group.stable_id for group in result.query.background),
                   result.core_ids, result.core_check, result.subset_minimality,
                   result.reduction, result.stop_reason)


def _assemble(report, query, extensions, budget):
    from dataclasses import replace
    from ..budget import BudgetExpired
    from .rules import analyze_proof
    from .text import build_reading

    try:
        if report.proof is not None:
            analysis = analyze_proof(report.proof, extensions.rule_handlers, budget)
            valid = (report.input_check == 'passed' and analysis.scope_check != 'failed' and
                     analysis.rule_check != 'failed')
            report = replace(report, proof=analysis.graph,
                             proof_status='captured' if valid else 'invalid',
                             scope_check=analysis.scope_check, rule_check=analysis.rule_check,
                             gaps=analysis.gaps)
        reading, sources = build_reading(report, query, extensions, budget)
        return replace(report, reading=reading, reading_status=reading.status, source_status=sources)
    except BudgetExpired as error:
        # Analysis/reading checkpoints share the solve deadline. Completed
        # native evidence is still valid when optional assembly runs out of time.
        return replace(report, stop_reason=str(error))


def explain_unsat(query, *, mode='proof', minimize=False, timeout_ms=None,
                  names=None, extensions=None) -> UnsatReport:
    """Explain the exact conjunction in a caller-supplied named query.

    :param query: An :class:`~pyfcstm.solver.unsat.UnsatQuery`.
    :param mode: ``proof`` for native evidence or ``core`` for a conflict core.
    :param minimize: Whether to minimize removable condition groups.
    :param timeout_ms: Shared positive millisecond budget, or ``None``.
    :param names: Optional construction-time symbol registry.
    :param extensions: Optional per-call rule/source/reading extensions.
    :return: Evidence with explicit availability and checking states.
    :raises TypeError: For an invalid query or minimization option.
    :raises ValueError: For an invalid mode or timeout.

    Example::

        >>> import z3
        >>> from pyfcstm.solver import UnsatConstraint, UnsatQuery
        >>> query = UnsatQuery('impossible', (UnsatConstraint('rule', (z3.BoolVal(False),)),))
        >>> report = explain_unsat(query)
        >>> report.solver_status, report.scope_check, report.reading_status
        ('unsat', 'passed', 'complete')
        >>> report.proof.node(report.proof.root_id).rule
        'asserted'
    """
    from ..budget import SolveBudget
    from ..unsat import UnsatQuery, _explain_unsat_core
    from ..symbols import SymbolNames
    from ._z3_proof import capture_proof
    from dataclasses import replace

    if not isinstance(query, UnsatQuery):
        raise TypeError('query must be an UnsatQuery')
    if mode not in ('core', 'proof'):
        raise ValueError('mode must be core or proof')
    if not isinstance(minimize, bool):
        raise TypeError('minimize must be a bool')
    if names is not None and not isinstance(names, SymbolNames):
        raise TypeError('names must be SymbolNames')
    if extensions is not None and not isinstance(extensions, ProofExtensions):
        raise TypeError('extensions must be ProofExtensions')
    extensions = ProofExtensions() if extensions is None else extensions
    budget = SolveBudget(timeout_ms)
    if mode == 'core':
        result = _explain_unsat_core(query, minimize=minimize, budget=budget)
        report = UnsatReport(query.query_id, result.solver_status, 'not_requested', None,
                             stop_reason=result.stop_reason, core=CoreEvidence.from_result(result))
        return _assemble(report, query, extensions, budget)
    adapter = extensions.source_adapter or SourceAdapter()
    report = _assemble(capture_proof(query, budget, names, adapter), query, extensions, budget)
    if not minimize or report.proof_status != 'captured' or report.stop_reason is not None:
        return report
    result = _explain_unsat_core(query, minimize=True, budget=budget)
    report = replace(report, core=CoreEvidence.from_result(result), stop_reason=result.stop_reason)
    if result.core_ids is None:
        return report
    reduced_query = UnsatQuery(query.query_id, tuple(group for group in query.constraints
                              if group.stable_id in result.core_ids), query.background)
    reduced = _assemble(capture_proof(reduced_query, budget, names, adapter), reduced_query, extensions, budget)
    if reduced.proof_status != 'captured' or reduced.stop_reason is not None:
        return replace(report, stop_reason=reduced.stop_reason or 'reduced proof was not accepted')
    return replace(reduced, proof_scope='core', full_proof=report.proof,
                   core=report.core, stop_reason=report.stop_reason)
