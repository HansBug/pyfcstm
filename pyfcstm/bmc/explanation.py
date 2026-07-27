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

import math
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
BmcCoreReduction = Literal["raw", "partial_minimized", "subset_minimal"]
BmcSubsetMinimality = Literal["proven", "not_proven"]
BmcSemanticRole = Literal[
    "domain_rule",
    "initial_fact",
    "transition_rule",
    "assumption",
    "definedness",
]

_MODES = ("none", "formal", "proof")
_STATUSES = ("complete", "partial", "unknown", "timeout")
_GRANULARITIES = ("source_group",)
_REDUCTIONS = ("raw", "partial_minimized", "subset_minimal")
_MINIMALITIES = ("proven", "not_proven")

#: Explanation depths ordered from weakest to strongest.
_MODE_ORDER = {"none": 0, "formal": 1, "proof": 2}

#: A reduction level admits exactly one subset-minimality claim.
_REDUCTION_MINIMALITY = {
    "raw": "not_proven",
    "partial_minimized": "not_proven",
    "subset_minimal": "proven",
}
_STAGES = ("kernel", "initialization", "assumptions")
_SEMANTIC_ROLES = (
    "domain_rule",
    "initial_fact",
    "transition_rule",
    "assumption",
    "definedness",
)

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

#: Category prefix to frozen semantic role.  This answers "what kind of fact is
#: this", which the relation builder encodes in the category name.
CATEGORY_ROLES = MappingProxyType(
    {
        "domain.": "domain_rule",
        "initial.": "initial_fact",
        "transition.": "transition_rule",
        "assumption.": "assumption",
        "definedness": "definedness",
    }
)


def category_role(category: str) -> str:
    """Return the frozen semantic role of a group category.

    :param category: Group category assigned by the relation builder.
    :type category: str
    :return: One of the frozen semantic roles.
    :rtype: str
    :raises ValueError: If the category matches no known prefix, which means a
        new group family was added without deciding how a reader should
        understand it.

    Example::

        >>> category_role("assumption.frame")
        'assumption'
    """
    for prefix, role in CATEGORY_ROLES.items():
        if category.startswith(prefix):
            return role
    raise ValueError("category %r belongs to no known family." % category)


def constraint_aggregate(stage: str, category: str) -> str:
    """Return the aggregate formula a tracked group belongs to.

    This answers a different question from :func:`category_role`: which of
    ``D_N`` / ``T_N`` / ``I_0`` / ``ENV_N`` contains the group.  The stage
    decides it, and only the kernel stage needs the category to split domain
    from transition.  A ``definedness`` group, for instance, reads as a
    definedness fact but lives in whichever stage lowered it.

    :param stage: Formula stage recorded for the group.
    :type stage: str
    :param category: Group category assigned by the relation builder.
    :type category: str
    :return: One of ``domain``, ``transition``, ``initial``, ``environment``.
    :rtype: str
    :raises ValueError: If the pairing matches no aggregate.

    Example::

        >>> constraint_aggregate("initialization", "definedness")
        'initial'
        >>> constraint_aggregate("kernel", "transition.step")
        'transition'
    """
    if stage == "kernel":
        if category.startswith("domain"):
            return "domain"
        if category.startswith("transition"):
            return "transition"
        raise ValueError(
            "kernel category %r is neither a domain nor a transition group." % category
        )
    if stage == "initialization":
        return "initial"
    if stage == "assumptions":
        return "environment"
    raise ValueError("stage %r belongs to no aggregate." % stage)


#: Aggregates each scope's target formula is built from.  Unlike the stage-level
#: view this distinguishes ``D_N`` from ``T_N``, both of which live in the
#: kernel stage, so a domain scope cannot quote a transition group.
SCOPE_AGGREGATES = MappingProxyType(
    {
        "kernel": ("domain", "transition"),
        "initialization_component": ("initial",),
        "initialization_domain": ("domain", "initial"),
        "initialization_prefix": ("domain", "transition", "initial"),
        "assumptions_component": ("environment",),
        "assumptions_domain": ("domain", "environment"),
        "assumptions_prefix": ("domain", "transition", "initial", "environment"),
        "initialization_stage_fallback": ("domain", "transition", "initial"),
        "assumptions_stage_fallback": (
            "domain",
            "transition",
            "initial",
            "environment",
        ),
    }
)

#: Recognized ``normalized_fact`` tags.  An expression this stage cannot
#: reduce declares itself structural rather than guessing a domain reading;
#: later stages add their recognizers here.
_FACT_KINDS = ("structural_constraint",)

#: Frozen upper bound on a published excerpt, in Unicode code points.  A long
#: authored line would otherwise put an unbounded slice of the user's source
#: into canonical JSON.
MAX_SOURCE_EXCERPT_CHARS = 4096

#: Frozen slots whose content a later delivery stage produces.  Populating one
#: now would break the frozen rule that the published JSON schema and this
#: constructor accept the same payload set, because neither slot has a schema
#: yet.  A ``complete`` explanation depends on ``narrative`` alone, so removing
#: that entry unlocks complete formal artifacts even while ``proof`` remains.
UNBUILT_SLOTS = ("proof", "narrative")

#: The two scopes that stay honest when classification never completed.
STAGE_FALLBACK_SCOPES = ("initialization_stage_fallback", "assumptions_stage_fallback")

_SCOPES = tuple(CLASSIFICATION_SCOPES.values()) + STAGE_FALLBACK_SCOPES


def _require_indices(values: Any, label: str) -> Tuple[int, ...]:
    """Reject anything that is not a tuple of non-negative integers.

    ``bool`` is an ``int`` subclass in Python but is not an index, and letting
    it through would publish ``true`` where the JSON contract promises a
    number.  A whole-valued ``float`` is accepted and canonicalized instead,
    because ``1.0`` is valid JSON for an integer and a validator judging by
    numeric value cannot tell it apart from ``1``.

    :param values: Candidate index sequence.
    :type values: object
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated indices as a tuple.
    :rtype: Tuple[int, ...]
    :raises ValueError: If any entry is not a non-negative integer.

    Example::

        >>> _require_indices([1, 0], "frames")
        (1, 0)
        >>> _require_indices([1.0], "frames")
        (1,)
    """
    normalized = []
    for entry in values:
        if isinstance(entry, bool):
            raise ValueError(
                "%s must contain non-negative integers, got %r." % (label, entry)
            )
        if isinstance(entry, float):
            # A JSON document may write a whole number as 1.0, and a validator
            # judging "integer" by value accepts it.  Canonicalizing here keeps
            # the published tuple integral without rejecting valid JSON.
            if not math.isfinite(entry) or not entry.is_integer():
                raise ValueError(
                    "%s must contain non-negative integers, got %r." % (label, entry)
                )
            entry = int(entry)
        if not isinstance(entry, int) or entry < 0:
            raise ValueError(
                "%s must contain non-negative integers, got %r." % (label, entry)
            )
        normalized.append(entry)
    return tuple(normalized)


def _require_json_mapping(value: Any, label: str) -> Dict[str, Any]:
    """Reject metadata that could not survive a round trip through JSON.

    These mappings are free-form by design, which is exactly why they need a
    boundary: an unserializable value placed here would not fail until the
    whole result is dumped, and the error would name neither the field nor the
    object it came from.

    :param value: Candidate mapping.
    :type value: object
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated mapping as a plain dict.
    :rtype: Dict[str, object]
    :raises TypeError: If a key is not a string, or a value is outside the
        JSON data model.

    Example::

        >>> _require_json_mapping({"frame": 0}, "refs")
        {'frame': 0}
    """

    def _check(entry: Any, where: str) -> None:
        if entry is None or isinstance(entry, (str, bool, int)):
            return
        if isinstance(entry, float):
            # NaN and Infinity are not JSON numbers.  json.dumps emits them by
            # default and refuses them under allow_nan=False, so either way the
            # payload stops being interchangeable.
            if not math.isfinite(entry):
                raise ValueError("%s must be a finite number, got %r." % (where, entry))
            return
        if isinstance(entry, (list, tuple)):
            for index, item in enumerate(entry):
                _check(item, "%s[%d]" % (where, index))
            return
        if isinstance(entry, Mapping):
            for key, item in entry.items():
                if not isinstance(key, str):
                    raise TypeError("%s keys must be strings, got %r." % (where, key))
                _check(item, "%s[%r]" % (where, key))
            return
        raise TypeError("%s is not JSON-compatible, got %r." % (where, entry))

    if not isinstance(value, Mapping):
        # A sequence would be silently normalized into an empty mapping by
        # dict(), which loses the caller's data and disagrees with the JSON
        # contract that names this field an object.
        raise TypeError("%s must be a mapping, got %r." % (label, value))
    mapping = dict(value)
    _check(mapping, label)
    return mapping


def _require_flag(value: Any, label: str) -> bool:
    """Reject a truthy stand-in where the JSON contract promises a boolean.

    :param value: Candidate flag.
    :type value: object
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated flag.
    :rtype: bool
    :raises TypeError: If the value is not a ``bool``.

    Example::

        >>> _require_flag(False, "editable")
        False
    """
    if not isinstance(value, bool):
        raise TypeError("%s must be a bool, got %r." % (label, value))
    return value


def _require_optional_text(value: Any, label: str) -> Optional[str]:
    """Reject a non-string stand-in for an optional text field.

    :param value: Candidate text, or ``None``.
    :type value: object
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated text.
    :rtype: Optional[str]
    :raises TypeError: If the value is neither ``None`` nor a string.

    Example::

        >>> _require_optional_text(None, "reason") is None
        True
    """
    if value is not None and not isinstance(value, str):
        raise TypeError("%s must be a string or None, got %r." % (label, value))
    return value


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
        object.__setattr__(self, "frames", _require_indices(self.frames, "frames"))
        object.__setattr__(self, "steps", _require_indices(self.steps, "steps"))
        object.__setattr__(
            self, "refs", MappingProxyType(_require_json_mapping(self.refs, "refs"))
        )

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
        >>> BmcCoreItem(ref, "initial_fact", None, False,
        ...             {"kind": "structural_constraint"}, "initial target",
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
        _require_optional_text(self.source_excerpt, "core item source_excerpt")
        if (
            self.source_excerpt is not None
            and len(self.source_excerpt) > MAX_SOURCE_EXCERPT_CHARS
        ):
            raise ValueError(
                "core item source_excerpt must not exceed %d code points, got %d."
                % (MAX_SOURCE_EXCERPT_CHARS, len(self.source_excerpt))
            )
        _require_flag(
            self.source_excerpt_truncated, "core item source_excerpt_truncated"
        )
        _require_flag(self.editable, "core item editable")
        expected_role = category_role(self.constraint.category)
        if self.semantic_role != expected_role:
            raise ValueError(
                "core item semantic_role %r contradicts category %r, which is "
                "read as %r."
                % (self.semantic_role, self.constraint.category, expected_role)
            )
        if self.constraint.source.kind == "generated" and self.editable:
            raise ValueError(
                "a generated constraint has no authored line to edit, so it "
                "cannot be an editable review surface."
            )
        if self.source_excerpt_truncated and (
            self.source_excerpt is None
            or len(self.source_excerpt) != MAX_SOURCE_EXCERPT_CHARS
        ):
            raise ValueError(
                "a truncated excerpt must be present and exactly %d code "
                "points long." % MAX_SOURCE_EXCERPT_CHARS
            )
        if not isinstance(self.human_text, str) or not self.human_text:
            raise ValueError("core item human_text must be a non-empty string.")
        fact = _require_json_mapping(self.normalized_fact, "normalized_fact")
        kind = fact.get("kind")
        if not isinstance(kind, str) or kind not in _FACT_KINDS:
            raise ValueError(
                "core item normalized_fact must carry a kind from %s, got %r; "
                "machine consumers dispatch on it instead of on human text."
                % (", ".join(_FACT_KINDS), kind)
            )
        object.__setattr__(self, "normalized_fact", MappingProxyType(fact))

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
            >>> item = BmcCoreItem(ref, "initial_fact", None, False,
            ...                    {"kind": "structural_constraint"},
            ...                    "initial target", False)
            >>> item.to_canonical()["semantic_role"]
            'initial_fact'
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
    :param reduction: How far deletion checking got: ``raw`` when no deletion
        check finished, ``partial_minimized`` when some did but the sweep is
        open, ``subset_minimal`` when every member proved necessary.
    :type reduction: str
    :param subset_minimality: Whether subset minimality has been proven.  It
        is determined by ``reduction``: only ``subset_minimal`` may claim
        ``proven``, which keeps "not proven minimal" distinct from "proven
        non-minimal".
    :type subset_minimality: str
    :param items: Core members; reordered by ``stable_id`` on construction.
    :type items: Tuple[BmcCoreItem, ...]
    :raises ValueError: If the scope, granularity, reduction or minimality is
        unknown, if the minimality claim does not match the reduction level,
        if ``items`` is empty, if two items share a ``stable_id``, or if an
        item's stage lies outside the scope's target formula.

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef
        >>> ref = BmcConstraintRef(
        ...     "initial.target", "initialization", "initial.target",
        ...     BmcSourceRef("generated", None, None), "initial target",
        ... )
        >>> item = BmcCoreItem(ref, "initial_fact", None, False,
        ...                    {"kind": "structural_constraint"},
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
        expected_minimality = _REDUCTION_MINIMALITY[self.reduction]
        if self.subset_minimality != expected_minimality:
            raise ValueError(
                "reduction %r requires subset_minimality %r, got %r; only a "
                "completed deletion sweep may claim 'proven'."
                % (self.reduction, expected_minimality, self.subset_minimality)
            )
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
        allowed = SCOPE_AGGREGATES[self.scope]
        for item in items:
            aggregate = constraint_aggregate(
                item.constraint.stage, item.constraint.category
            )
            if aggregate not in allowed:
                raise ValueError(
                    "core item %r is a %s constraint, which is outside the "
                    "target of scope %r (%s)."
                    % (
                        item.constraint.stable_id,
                        aggregate,
                        self.scope,
                        ", ".join(allowed),
                    )
                )
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
            >>> item = BmcCoreItem(ref, "initial_fact", None, False,
            ...                    {"kind": "structural_constraint"},
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
    :param proof: Reserved for a later stage; rejected while non-``None``.
    :type proof: Optional[BmcConflictProof], optional
    :param narrative: Reserved for a later stage; rejected while non-``None``.
    :type narrative: Optional[BmcConflictNarrative], optional
    :param reason: Why the artifact is degraded, defaults to ``None``.
    :type reason: Optional[str], optional
    :param elapsed_ms: Wall-clock time of the optional stage, defaults to
        ``None``.
    :type elapsed_ms: Optional[float], optional
    :raises ValueError: If a mode or status is outside its frozen vocabulary,
        if a ``complete`` status carries a reason, if a degraded status omits
        one, if a classification and core scope disagree, if a stage fallback
        scope carries a classification, or if the delivery matrix checked by
        :meth:`_validate_delivery` is violated.

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
        _require_optional_text(self.reason, "explanation reason")
        if self.status == "complete":
            if self.reason is not None:
                raise ValueError("complete explanations must not carry a reason.")
        elif not self.reason:
            raise ValueError(
                "%s explanations require a non-empty reason." % self.status
            )
        if self.elapsed_ms is not None:
            if isinstance(self.elapsed_ms, bool) or not isinstance(
                self.elapsed_ms, (int, float)
            ):
                raise TypeError("explanation elapsed_ms must be a number or None.")
            if not math.isfinite(self.elapsed_ms):
                raise ValueError(
                    "explanation elapsed_ms must be finite, got %r." % self.elapsed_ms
                )
            if self.elapsed_ms < 0:
                raise ValueError("explanation elapsed_ms must not be negative.")
        if self.core is not None:
            if not isinstance(self.core, BmcConflictCore):
                raise TypeError("explanation core must be BmcConflictCore.")
            self._validate_scope(self.core.scope)
        self._validate_delivery()

    def _validate_delivery(self) -> None:
        """Enforce the frozen cross-field delivery matrix.

        Each field is separately legal in isolation, so the contract only
        becomes checkable as a table: what ``achieved_mode`` was reached
        constrains which of ``core``, ``proof`` and ``narrative`` may be
        present, and how strong the core's minimality claim must be.

        :return: ``None``.
        :rtype: None
        :raises ValueError: If the combination is outside the frozen matrix.

        Example::

            >>> BmcInfeasibilityExplanation(
            ...     "formal", "none", "timeout", None, reason="budget spent",
            ... ).achieved_mode
            'none'
        """
        if _MODE_ORDER[self.achieved_mode] > _MODE_ORDER[self.requested_mode]:
            raise ValueError(
                "achieved_mode %r is stronger than requested_mode %r."
                % (self.achieved_mode, self.requested_mode)
            )
        if self.achieved_mode == "none":
            if self.core is not None:
                raise ValueError(
                    "achieved_mode 'none' means no sound core was published."
                )
            if self.status == "complete":
                raise ValueError(
                    "achieved_mode 'none' cannot be complete; it is partial, "
                    "unknown or timeout."
                )
        elif self.core is None:
            raise ValueError("achieved_mode %r requires a core." % self.achieved_mode)
        if self.achieved_mode == "proof" and self.proof is None:
            raise ValueError("achieved_mode 'proof' requires a proof.")
        if self.proof is not None and self.requested_mode != "proof":
            raise ValueError("a proof is only published when 'proof' was requested.")
        if self.status == "complete":
            if self.classification is None:
                raise ValueError(
                    "a complete explanation requires a diagnostic classification."
                )
            if self.core.reduction != "subset_minimal":
                raise ValueError(
                    "a complete explanation requires a subset-minimal core, got "
                    "reduction %r." % self.core.reduction
                )
            # A complete explanation needs a narrative.  The rule names that
            # one slot rather than the whole unbuilt set, so a later stage that
            # implements narratives unlocks complete formal artifacts even
            # while the proof DAG is still outstanding.
            if self.narrative is None:
                raise ValueError(
                    "a complete explanation requires a complete narrative, "
                    "which is not built yet."
                )
        for name in UNBUILT_SLOTS:
            if getattr(self, name) is not None:
                raise ValueError(
                    "explanation %s is not produced at this stage; it must be "
                    "None." % name
                )

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
            # Both slots are kept None by the delivery matrix, so emitting the
            # fields directly can never silently drop a caller's value.
            "proof": self.proof,
            "narrative": self.narrative,
            "reason": self.reason,
            "elapsed_ms": self.elapsed_ms,
        }


__all__ = [
    "BmcConflictCore",
    "BmcConflictCoreScope",
    "BmcConflictNarrative",
    "BmcConflictProof",
    "BmcConstraintRef",
    "BmcConstraintStage",
    "BmcCoreGranularity",
    "BmcCoreItem",
    "BmcCoreReduction",
    "BmcInfeasibilityClassification",
    "BmcInfeasibilityExplanation",
    "BmcInfeasibilityExplanationMode",
    "BmcInfeasibilityExplanationStatus",
    "BmcSemanticRole",
    "BmcSubsetMinimality",
    "CLASSIFICATION_SCOPES",
    "STAGE_FALLBACK_SCOPES",
]
