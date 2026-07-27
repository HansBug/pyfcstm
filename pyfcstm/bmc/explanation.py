"""Solver-free public data layer for BMC scenario infeasibility explanations.

When bounded model checking reports that a scenario is infeasible, the
mandatory verdict only names the first infeasible stage.  This module owns the
public values that answer the two follow-up questions: *how* the stage is
infeasible, and *which* authored FCSTM/FBMCQ constraints already suffice to
make it infeasible.

The module deliberately imports neither Z3 nor any relation/witness machinery.
Every value here is plain data, so an IDE, a report generator or an LLM can
consume an explanation without loading the solver stack.  The orchestration
that actually runs probes and extracts a core lives in
:mod:`pyfcstm.bmc.infeasibility`; the dependency direction is one-way.

The module contains:

* :class:`BmcConstraintRef` - public identity and provenance of one tracked
  source group
* :class:`BmcCoreItem` - one core member together with its semantic reading
* :class:`BmcConflictCore` - an ordered, sound set of core members for one
  diagnostic scope
* :class:`BmcConflictNarrative` - reserved container for the deterministic
  narrative introduced by a later stage
* :class:`BmcConflictProof` - reserved container for the verifiable proof DAG
  introduced by a later stage
* :class:`BmcInfeasibilityExplanation` - the frozen top-level container

.. note::
   :class:`BmcConflictNarrative` and :class:`BmcConflictProof` exist so that
   :class:`BmcInfeasibilityExplanation` can freeze its full field list once.
   This stage never populates them; both slots stay ``None``.

Example::

    >>> from pyfcstm.bmc.explanation import BmcInfeasibilityExplanation
    >>> explanation = BmcInfeasibilityExplanation(
    ...     requested_mode="formal",
    ...     achieved_mode="none",
    ...     status="unknown",
    ...     classification=None,
    ...     reason="component probe returned unknown",
    ... )
    >>> explanation.status
    'unknown'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple

from .provenance import BmcSourceRef

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

BmcInfeasibilityExplanationMode = Literal["none", "formal", "proof"]
BmcInfeasibilityExplanationStatus = Literal["complete", "partial", "unknown", "timeout"]
BmcInfeasibilityClassification = Literal[
    "kernel_conflict",
    "initialization_self_conflict",
    "initialization_domain_conflict",
    "initialization_kernel_conflict",
    "assumptions_self_conflict",
    "assumptions_domain_conflict",
    "assumptions_prefix_conflict",
]
BmcConflictCoreScope = Literal[
    "kernel",
    "initialization_component",
    "initialization_domain",
    "initialization_prefix",
    "assumptions_component",
    "assumptions_domain",
    "assumptions_prefix",
    "initialization_stage_fallback",
    "assumptions_stage_fallback",
]
BmcConstraintStage = Literal["kernel", "initialization", "assumptions"]
BmcCoreGranularity = Literal["source_group"]
BmcCoreReduction = Literal["raw", "minimized"]
BmcSubsetMinimality = Literal["proven", "not_proven"]
BmcSemanticRole = Literal["structural", "value", "state", "event", "definedness"]

_MODES = ("none", "formal", "proof")
_STATUSES = ("complete", "partial", "unknown", "timeout")
_GRANULARITIES = ("source_group",)
_REDUCTIONS = ("raw", "minimized")
_MINIMALITIES = ("proven", "not_proven")
_STAGES = ("kernel", "initialization", "assumptions")
_SEMANTIC_ROLES = ("structural", "value", "state", "event", "definedness")

#: Every classification maps to exactly one diagnostic scope.
CLASSIFICATION_SCOPES = MappingProxyType(
    {
        "kernel_conflict": "kernel",
        "initialization_self_conflict": "initialization_component",
        "initialization_domain_conflict": "initialization_domain",
        "initialization_kernel_conflict": "initialization_prefix",
        "assumptions_self_conflict": "assumptions_component",
        "assumptions_domain_conflict": "assumptions_domain",
        "assumptions_prefix_conflict": "assumptions_prefix",
    }
)

#: The two scopes that stay honest when classification never completed.
STAGE_FALLBACK_SCOPES = ("initialization_stage_fallback", "assumptions_stage_fallback")

_SCOPES = tuple(CLASSIFICATION_SCOPES.values()) + STAGE_FALLBACK_SCOPES


def _require_member(value: Any, allowed: Tuple[str, ...], label: str) -> str:
    """Reject anything outside a frozen vocabulary, including ``bool``.

    :param value: Candidate value supplied by a caller.
    :type value: object
    :param allowed: Frozen vocabulary for this field.
    :type allowed: Tuple[str, ...]
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated value.
    :rtype: str
    :raises ValueError: If the value is not one of the allowed names.

    Example::

        >>> _require_member("formal", ("none", "formal"), "mode")
        'formal'
    """
    if isinstance(value, bool) or not isinstance(value, str) or value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r." % (label, ", ".join(allowed), value)
        )
    return value


@dataclass(frozen=True)
class BmcConstraintRef:
    """Public identity and provenance of one tracked source group.

    :param stable_id: Deterministic identifier of the tracked group.
    :type stable_id: str
    :param stage: Formula stage the group belongs to.
    :type stage: str
    :param category: Domain-specific group category.
    :type category: str
    :param source: FCSTM, FBMCQ or generated source reference.
    :type source: pyfcstm.bmc.provenance.BmcSourceRef
    :param summary: Short deterministic description of the group.
    :type summary: str
    :param frames: Frame indices the group constrains, defaults to ``()``.
    :type frames: Tuple[int, ...], optional
    :param steps: Macro-step indices the group constrains, defaults to ``()``.
    :type steps: Tuple[int, ...], optional
    :param refs: Stable structural metadata, defaults to ``{}``.
    :type refs: Mapping[str, object], optional
    :raises ValueError: If the identifier, stage, category or summary is not a
        non-empty string.
    :raises TypeError: If ``source`` is not a
        :class:`pyfcstm.bmc.provenance.BmcSourceRef`.

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef
        >>> ref = BmcConstraintRef(
        ...     "initial.target", "initialization", "initial.target",
        ...     BmcSourceRef("generated", None, None), "initial target state",
        ... )
        >>> ref.stable_id
        'initial.target'
    """

    stable_id: str
    stage: BmcConstraintStage
    category: str
    source: BmcSourceRef
    summary: str
    frames: Tuple[int, ...] = ()
    steps: Tuple[int, ...] = ()
    refs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("stable_id", "category", "summary"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError("constraint %s must be a non-empty string." % name)
        _require_member(self.stage, _STAGES, "constraint stage")
        if not isinstance(self.source, BmcSourceRef):
            raise TypeError("constraint source must be BmcSourceRef.")
        object.__setattr__(self, "frames", tuple(self.frames))
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "refs", MappingProxyType(dict(self.refs)))

    def to_canonical(self) -> Dict[str, Any]:
        """Return a JSON-compatible constraint reference.

        :return: Canonical constraint dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.provenance import BmcSourceRef
            >>> BmcConstraintRef(
            ...     "initial.target", "initialization", "initial.target",
            ...     BmcSourceRef("generated", None, None), "initial target",
            ... ).to_canonical()["stage"]
            'initialization'
        """
        return {
            "stable_id": self.stable_id,
            "stage": self.stage,
            "category": self.category,
            "source": self.source.to_canonical(),
            "summary": self.summary,
            "frames": list(self.frames),
            "steps": list(self.steps),
            "refs": dict(self.refs),
        }


@dataclass(frozen=True)
class BmcCoreItem:
    """One core member together with its semantic reading.

    :param constraint: Identity and provenance of the tracked group.
    :type constraint: BmcConstraintRef
    :param semantic_role: Recognized role of the constraint.
    :type semantic_role: str
    :param source_excerpt: Authored text the span points at, or ``None``.
    :type source_excerpt: Optional[str]
    :param source_excerpt_truncated: Whether the excerpt was shortened.
    :type source_excerpt_truncated: bool
    :param normalized_fact: Structured, deterministic fact for machine readers.
    :type normalized_fact: Mapping[str, object]
    :param human_text: Deterministic single-sentence reading.
    :type human_text: str
    :param editable: Whether the constraint maps to an editable source entry.
    :type editable: bool
    :raises ValueError: If the semantic role is unknown or ``human_text`` is
        not a non-empty string.
    :raises TypeError: If ``constraint`` is not a :class:`BmcConstraintRef`.

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef
        >>> ref = BmcConstraintRef(
        ...     "initial.target", "initialization", "initial.target",
        ...     BmcSourceRef("generated", None, None), "initial target",
        ... )
        >>> BmcCoreItem(ref, "structural", None, False, {}, "initial target",
        ...             False).editable
        False
    """

    constraint: BmcConstraintRef
    semantic_role: BmcSemanticRole
    source_excerpt: Optional[str]
    source_excerpt_truncated: bool
    normalized_fact: Mapping[str, object]
    human_text: str
    editable: bool

    def __post_init__(self) -> None:
        if not isinstance(self.constraint, BmcConstraintRef):
            raise TypeError("core item constraint must be BmcConstraintRef.")
        _require_member(self.semantic_role, _SEMANTIC_ROLES, "core item semantic_role")
        if not isinstance(self.human_text, str) or not self.human_text:
            raise ValueError("core item human_text must be a non-empty string.")
        object.__setattr__(
            self, "normalized_fact", MappingProxyType(dict(self.normalized_fact))
        )

    def to_canonical(self) -> Dict[str, Any]:
        """Return a JSON-compatible core item.

        :return: Canonical core item dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.provenance import BmcSourceRef
            >>> ref = BmcConstraintRef(
            ...     "initial.target", "initialization", "initial.target",
            ...     BmcSourceRef("generated", None, None), "initial target",
            ... )
            >>> item = BmcCoreItem(ref, "structural", None, False, {},
            ...                    "initial target", False)
            >>> item.to_canonical()["semantic_role"]
            'structural'
        """
        return {
            "constraint": self.constraint.to_canonical(),
            "semantic_role": self.semantic_role,
            "source_excerpt": self.source_excerpt,
            "source_excerpt_truncated": self.source_excerpt_truncated,
            "normalized_fact": dict(self.normalized_fact),
            "human_text": self.human_text,
            "editable": self.editable,
        }


@dataclass(frozen=True)
class BmcConflictCore:
    """An ordered, sound set of core members for one diagnostic scope.

    Items are sorted by ``stable_id`` so that the published order never leaks
    the solver's own core ordering.

    :param scope: Diagnostic or stage-fallback scope the core proves.
    :type scope: str
    :param formula_summary: Short description of the proven target formula.
    :type formula_summary: str
    :param granularity: Core granularity, currently always ``source_group``.
    :type granularity: str
    :param reduction: Whether the core was minimized.
    :type reduction: str
    :param subset_minimality: Whether subset minimality has been proven.
    :type subset_minimality: str
    :param items: Core members; reordered by ``stable_id`` on construction.
    :type items: Tuple[BmcCoreItem, ...]
    :raises ValueError: If the scope, granularity, reduction or minimality is
        unknown, if ``items`` is empty, or if two items share a ``stable_id``.

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef
        >>> ref = BmcConstraintRef(
        ...     "initial.target", "initialization", "initial.target",
        ...     BmcSourceRef("generated", None, None), "initial target",
        ... )
        >>> item = BmcCoreItem(ref, "structural", None, False, {},
        ...                    "initial target", False)
        >>> core = BmcConflictCore("initialization_component", "I_0",
        ...                        "source_group", "raw", "not_proven", (item,))
        >>> core.scope
        'initialization_component'
    """

    scope: BmcConflictCoreScope
    formula_summary: str
    granularity: BmcCoreGranularity
    reduction: BmcCoreReduction
    subset_minimality: BmcSubsetMinimality
    items: Tuple[BmcCoreItem, ...]

    def __post_init__(self) -> None:
        _require_member(self.scope, _SCOPES, "core scope")
        _require_member(self.granularity, _GRANULARITIES, "core granularity")
        _require_member(self.reduction, _REDUCTIONS, "core reduction")
        _require_member(self.subset_minimality, _MINIMALITIES, "core subset_minimality")
        if not isinstance(self.formula_summary, str) or not self.formula_summary:
            raise ValueError("core formula_summary must be a non-empty string.")
        items = tuple(self.items)
        if not items:
            raise ValueError("core items must not be empty.")
        for item in items:
            if not isinstance(item, BmcCoreItem):
                raise TypeError("core items must be BmcCoreItem values.")
        identifiers = [item.constraint.stable_id for item in items]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("core items contain duplicate stable ids.")
        object.__setattr__(
            self,
            "items",
            tuple(sorted(items, key=lambda item: item.constraint.stable_id)),
        )

    def to_canonical(self) -> Dict[str, Any]:
        """Return a JSON-compatible conflict core.

        :return: Canonical core dictionary with ordered items.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.provenance import BmcSourceRef
            >>> ref = BmcConstraintRef(
            ...     "initial.target", "initialization", "initial.target",
            ...     BmcSourceRef("generated", None, None), "initial target",
            ... )
            >>> item = BmcCoreItem(ref, "structural", None, False, {},
            ...                    "initial target", False)
            >>> core = BmcConflictCore("initialization_component", "I_0",
            ...                        "source_group", "raw", "not_proven", (item,))
            >>> core.to_canonical()["reduction"]
            'raw'
        """
        return {
            "scope": self.scope,
            "formula_summary": self.formula_summary,
            "granularity": self.granularity,
            "reduction": self.reduction,
            "subset_minimality": self.subset_minimality,
            "items": [item.to_canonical() for item in self.items],
        }


@dataclass(frozen=True)
class BmcConflictNarrative:
    """Reserved container for the deterministic conflict narrative.

    The narrative belongs to a later delivery stage.  It is declared here only
    so that :class:`BmcInfeasibilityExplanation` can freeze its field list
    once; this stage always leaves the slot empty.

    :param derivation_status: How far the derivation was reconstructed.
    :type derivation_status: str
    :param headline: One-line human summary.
    :type headline: str
    :param summary: Longer deterministic summary.
    :type summary: str

    Example::

        >>> BmcConflictNarrative("structural_only", "conflict", "summary").headline
        'conflict'
    """

    derivation_status: str
    headline: str
    summary: str


@dataclass(frozen=True)
class BmcConflictProof:
    """Reserved container for the verifiable domain proof DAG.

    The proof DAG belongs to a later delivery stage.  It is declared here only
    so that :class:`BmcInfeasibilityExplanation` can freeze its field list
    once; this stage always leaves the slot empty.

    :param scope: Diagnostic scope the proof discharges.
    :type scope: str
    :param root_id: Identifier of the single false root node.
    :type root_id: str

    Example::

        >>> BmcConflictProof("assumptions_component", "root").root_id
        'root'
    """

    scope: str
    root_id: str


@dataclass(frozen=True)
class BmcInfeasibilityExplanation:
    """Frozen public container for one scenario infeasibility explanation.

    The field list is frozen once and never reshaped by later stages; they
    only populate slots that this stage leaves empty.  ``achieved_mode``
    reports what was actually delivered, which can be weaker than
    ``requested_mode`` whenever a probe or extraction step degrades.

    :param requested_mode: Explanation depth the caller asked for.
    :type requested_mode: str
    :param achieved_mode: Explanation depth actually delivered.
    :type achieved_mode: str
    :param status: Completeness of the delivered artifact.
    :type status: str
    :param classification: Structured infeasibility classification, or ``None``
        when only a stage fallback is honest.
    :type classification: Optional[str]
    :param core: Sound source core, defaults to ``None``.
    :type core: Optional[BmcConflictCore], optional
    :param proof: Reserved for a later stage; always ``None`` here.
    :type proof: Optional[BmcConflictProof], optional
    :param narrative: Reserved for a later stage; always ``None`` here.
    :type narrative: Optional[BmcConflictNarrative], optional
    :param reason: Why the artifact is degraded, defaults to ``None``.
    :type reason: Optional[str], optional
    :param elapsed_ms: Wall-clock time of the optional stage, defaults to
        ``None``.
    :type elapsed_ms: Optional[float], optional
    :raises ValueError: If a mode or status is outside its frozen vocabulary,
        if a ``complete`` status carries a reason, if a degraded status omits
        one, if a classification and core scope disagree, or if a stage
        fallback scope carries a classification.

    Example::

        >>> explanation = BmcInfeasibilityExplanation(
        ...     requested_mode="formal",
        ...     achieved_mode="none",
        ...     status="timeout",
        ...     classification=None,
        ...     reason="component probe exhausted the shared budget",
        ... )
        >>> explanation.achieved_mode
        'none'
    """

    requested_mode: BmcInfeasibilityExplanationMode
    achieved_mode: BmcInfeasibilityExplanationMode
    status: BmcInfeasibilityExplanationStatus
    classification: Optional[BmcInfeasibilityClassification]
    core: Optional[BmcConflictCore] = None
    proof: Optional[BmcConflictProof] = None
    narrative: Optional[BmcConflictNarrative] = None
    reason: Optional[str] = None
    elapsed_ms: Optional[float] = None

    def __post_init__(self) -> None:
        _require_member(self.requested_mode, _MODES, "requested_mode")
        _require_member(self.achieved_mode, _MODES, "achieved_mode")
        _require_member(self.status, _STATUSES, "status")
        if self.classification is not None:
            _require_member(
                self.classification, tuple(CLASSIFICATION_SCOPES), "classification"
            )
        if self.status == "complete":
            if self.reason is not None:
                raise ValueError("complete explanations must not carry a reason.")
        elif not self.reason:
            raise ValueError(
                "%s explanations require a non-empty reason." % self.status
            )
        if self.core is not None:
            if not isinstance(self.core, BmcConflictCore):
                raise TypeError("explanation core must be BmcConflictCore.")
            self._validate_scope(self.core.scope)

    def _validate_scope(self, scope: str) -> None:
        """Enforce the frozen classification-to-scope mapping.

        ``kernel`` is not a stage fallback: the kernel stage has no weaker
        component or domain probe, so localization alone already fixes
        ``kernel_conflict``.  Only the two ``*_stage_fallback`` scopes are
        allowed to carry no classification.

        :param scope: Core scope to validate against ``classification``.
        :type scope: str
        :return: ``None``.
        :rtype: None
        :raises ValueError: If the pairing is not one of the frozen ones.

        Example::

            >>> explanation = BmcInfeasibilityExplanation(
            ...     "formal", "none", "unknown", None, reason="probe unknown",
            ... )
            >>> explanation._validate_scope("assumptions_stage_fallback")
        """
        if self.classification is None:
            if scope not in STAGE_FALLBACK_SCOPES:
                raise ValueError(
                    "an absent classification only allows a stage fallback scope, "
                    "got %r; note that kernel always carries kernel_conflict." % scope
                )
            return
        if scope in STAGE_FALLBACK_SCOPES:
            raise ValueError(
                "a stage fallback scope must not carry classification %r."
                % self.classification
            )
        expected = CLASSIFICATION_SCOPES[self.classification]
        if scope != expected:
            raise ValueError(
                "classification %r maps to scope %r, got %r."
                % (self.classification, expected, scope)
            )

    def to_canonical(self) -> Dict[str, Any]:
        """Return a JSON-compatible explanation.

        :return: Canonical explanation dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> explanation = BmcInfeasibilityExplanation(
            ...     "formal", "none", "unknown", None, reason="probe unknown",
            ... )
            >>> explanation.to_canonical()["status"]
            'unknown'
        """
        return {
            "requested_mode": self.requested_mode,
            "achieved_mode": self.achieved_mode,
            "status": self.status,
            "classification": self.classification,
            "core": None if self.core is None else self.core.to_canonical(),
            "proof": None,
            "narrative": None,
            "reason": self.reason,
            "elapsed_ms": self.elapsed_ms,
        }


__all__ = []
