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

from .provenance import (
    BmcSourceRef,
    _require_json_mapping,
    exact_float,
    exact_int,
    exact_str,
    json_canonical,
)

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

#: The frozen delivery truth table, one entry per authored row.
#:
#: The frozen contract is an exhaustive table, not a conjunction of independent
#: field rules.  A conjunction is strictly weaker: every local rule can hold
#: while the resulting combination appears in no row at all, which is how a
#: published core once coexisted with ``status='unknown'``.  Membership in this
#: table is therefore the authoritative check; the targeted checks in
#: :meth:`BmcInfeasibilityExplanation._validate_delivery` only exist to report
#: the common mistakes with a specific message.
#:
#: Each entry is ``(requested modes, achieved_mode, status, classification,
#: core, proof, reason)`` where the last four are ``True`` for required,
#: ``False`` for forbidden and ``None`` for "either".  Rows that differ only in
#: something an explanation object cannot show — a subset-minimal core versus a
#: stage-fallback one — share a single entry.
_DELIVERY_MATRIX_ROWS = (
    # Row 1: the first optional probe returned unknown, so there is neither a
    # classification nor a publishable sound core.
    (("formal", "proof"), "none", "unknown", False, False, False, True),
    # Row 2: the same shape after the budget expired instead.
    (("formal", "proof"), "none", "timeout", False, False, False, True),
    # Row 3: classification finished, the raw core did not.  The classification
    # metadata is kept, but it must not pose as a formal artifact.
    (("formal", "proof"), "none", "partial", True, False, False, True),
    # Rows 4, 6 and 7: a sound core whose minimality, scope or proof is still
    # open.  All three are indistinguishable from the published fields.
    (("formal", "proof"), "formal", "partial", None, True, False, True),
    # Row 5: a diagnostic subset-minimal core with complete semantic facts.
    # Requesting 'proof' cannot land here: an unclosed proof forces row 7.
    (("formal",), "formal", "complete", True, True, False, False),
    # Row 9: a verified proof over a stage-fallback artifact.  A stage-fallback
    # scope means the classification did not finish, so this row carries none.
    # The frozen timeout boundary spells the same row out as "proof 完整，但
    # classification 未完成".
    #
    # A verified proof beside a classification that *did* finish is row 8, which
    # is complete rather than partial.  The frozen table lists no partial row for
    # that shape, so one must be added deliberately when narratives land: the
    # boundary table's "semantic fact without a dedicated recognizer" case forces
    # status=partial with a narrative of structural_only, and at proof depth that
    # combination has no row yet.  Widening this row to "either" would hide that
    # gap instead of recording it.
    (("proof",), "proof", "partial", False, True, True, True),
    # Row 8: a verified proof over a diagnostic artifact.
    (("proof",), "proof", "complete", True, True, True, False),
)


def _expand_delivery_matrix() -> frozenset:
    """Expand the authored delivery rows into exact field signatures.

    ``None`` entries mean the row accepts either presence, so they expand into
    both concrete signatures.  Expanding once at import time keeps the runtime
    check a single set membership test.

    :return: Every legal delivery signature.
    :rtype: frozenset

    Example::

        >>> signatures = _expand_delivery_matrix()
        >>> ("formal", "none", "timeout", False, False, False, True) in signatures
        True
        >>> ("none", "none", "unknown", False, False, False, True) in signatures
        False
    """
    signatures = set()
    for requested_modes, achieved, status, *slots in _DELIVERY_MATRIX_ROWS:
        choices = [(True, False) if slot is None else (slot,) for slot in slots]
        for requested in requested_modes:
            for has_classification in choices[0]:
                for has_core in choices[1]:
                    for has_proof in choices[2]:
                        for has_reason in choices[3]:
                            signatures.add(
                                (
                                    requested,
                                    achieved,
                                    status,
                                    has_classification,
                                    has_core,
                                    has_proof,
                                    has_reason,
                                )
                            )
    return frozenset(signatures)


#: Every delivery signature the frozen table admits.
_DELIVERY_SIGNATURES = _expand_delivery_matrix()

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


def is_printable_ascii(value: str) -> bool:
    """Report whether a string is entirely printable ASCII.

    Stable ids are generated from fixed category/index/path encodings and are
    used downstream as solver literal names and as JSON keys, so the frozen
    contract keeps them ASCII.  ``str.isascii`` is not the right test: it also
    admits control characters, which would survive the Python boundary and then
    fail the published pattern.  Both sides therefore share this predicate.

    :param value: Candidate string.
    :type value: str
    :return: ``True`` when every character is in the printable ASCII range.
    :rtype: bool

    Example::

        >>> is_printable_ascii("assumption.0000.frame.0000")
        True
        >>> is_printable_ascii("a" + chr(9) + "b")
        False
        >>> is_printable_ascii("\u51b2\u7a81")
        False
    """
    # Iteration goes through __iter__, which a subclass may override to hide the
    # characters it really holds, so the scan runs on the exact text.
    try:
        plain = exact_str(value, "value")
    except TypeError:
        # exact_str refuses an object that only claims to be a str.
        return False
    return bool(plain) and all("\x20" <= char <= "\x7e" for char in plain)


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
    # str.startswith is an instance method, so a subclass could claim any family
    # and pick its own semantic role.  The prefix test runs on the exact text.
    try:
        plain = exact_str(category, "category")
    except TypeError:
        # exact_str refuses an object that only claims to be a str.
        raise ValueError("category %r belongs to no known family." % category) from None
    for prefix, role in CATEGORY_ROLES.items():
        if plain.startswith(prefix):
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
    # Both reads go through the exact text, for the same reason category_role
    # does: `==` and `startswith` are methods the untrusted value provides, so it
    # would otherwise decide which aggregate formula it belongs to.
    try:
        stage = exact_str(stage, "stage")
        category = exact_str(category, "category")
    except TypeError:
        # exact_str refuses an object that only claims to be a str.
        raise ValueError(
            "stage %r with category %r matches no aggregate." % (stage, category)
        ) from None
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
#:
#: The frozen design counts three honest fallback targets for an unfinished
#: classification: ``kernel``, ``initialization_stage_fallback`` and
#: ``assumptions_stage_fallback``.  Only two appear here, because ``kernel`` is
#: not a *degraded* scope: the kernel stage has no weaker component or domain
#: probe, so localizing it already fixes ``kernel_conflict`` and its scope name
#: is the diagnostic one.  This tuple names the scopes that carry no
#: classification, which is what :meth:`BmcInfeasibilityExplanation._validate_scope`
#: needs, so a reader counting three targets against it would come up one short
#: without this note.
STAGE_FALLBACK_SCOPES = ("initialization_stage_fallback", "assumptions_stage_fallback")

_SCOPES = tuple(CLASSIFICATION_SCOPES.values()) + STAGE_FALLBACK_SCOPES


def index_value(value: Any, label: str) -> int:
    """Canonicalize one recorded index, or refuse it.

    This is the single answer to "is this an index", shared by the public
    constructors and by the orchestration that reads the relation builder's
    metadata.  When each side decides for itself, the two disagree on inputs
    neither side's tests cover, and the published ``frames``/``steps`` can end
    up contradicting the ``refs`` mapping they were derived from.

    ``bool`` is an ``int`` subclass in Python but is not an index, and letting
    it through would publish ``true`` where the JSON contract promises a
    number.  A whole-valued ``float`` is accepted and canonicalized instead,
    because ``1.0`` is valid JSON for an integer and a validator judging by
    numeric value cannot tell it apart from ``1``.

    :param value: Candidate index.
    :type value: object
    :param label: Field or metadata key name used in the error message.
    :type label: str
    :return: The canonical non-negative integer index.
    :rtype: int
    :raises ValueError: If the value is not a non-negative integer index.
    :raises TypeError: If the value only claims to be a number, for instance by
        faking ``__class__``, so that no real value can be read from it.

    Example::

        >>> index_value(2, "frames")
        2
        >>> index_value(1.0, "frames")
        1
        >>> index_value(True, "frames")
        Traceback (most recent call last):
            ...
        ValueError: frames must contain non-negative integers, got True.
    """
    if isinstance(value, bool):
        raise ValueError(
            "%s must contain non-negative integers, got %r." % (label, value)
        )
    # Every read below goes through the base type's own method rather than the
    # instance's.  A subclass may override __int__, __float__ or is_integer, and
    # then both the check and the canonicalization would be answered by the value
    # being validated: a float subclass claiming is_integer() would be accepted
    # as an index while really holding 2.5, and int() would publish whatever
    # __int__ chose to return instead of the number the object is.
    if isinstance(value, float):
        # A JSON document may write a whole number as 1.0, and a validator
        # judging "integer" by value accepts it.  Canonicalizing here keeps the
        # published tuple integral without rejecting valid JSON.
        # Extract the real value once through the base type; everything after
        # this point works on a genuine float, so ordinary methods are safe.
        plain = exact_float(value, label)
        if not math.isfinite(plain) or not plain.is_integer():
            raise ValueError(
                "%s must contain non-negative integers, got %r." % (label, value)
            )
        value = int(plain)
    if not isinstance(value, int):
        raise ValueError(
            "%s must contain non-negative integers, got %r." % (label, value)
        )
    # int.__int__ rather than int(): an int subclass such as IntEnum passes the
    # check above but keeps its own repr, so the published tuple would carry an
    # object that is only incidentally an integer.  JSON renders it as a number
    # either way, but a canonical field should not depend on that.
    canonical = exact_int(value, label)
    if canonical < 0:
        raise ValueError(
            "%s must contain non-negative integers, got %r." % (label, value)
        )
    return canonical


def _require_indices(values: Any, label: str) -> Tuple[int, ...]:
    """Reject anything that is not a sequence of non-negative integer indices.

    The container is checked too.  Iterating an arbitrary object silently
    accepts values the published schema refuses: ``""`` and ``{}`` both iterate
    empty, so without this check the constructor would accept two payloads that
    are not arrays at all.

    The caller's order is preserved.  Only the reader in
    :mod:`pyfcstm.bmc.infeasibility` sorts, because it merges the singular and
    plural metadata keys and needs a deterministic merge; the frozen field is
    just ``Tuple[int, ...]``, so reordering an explicitly supplied sequence
    would be this function inventing a rule the contract does not state.

    :param values: Candidate index sequence.
    :type values: object
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated indices, in the order given.
    :rtype: Tuple[int, ...]
    :raises TypeError: If ``values`` is not a list or tuple.
    :raises ValueError: If any entry is not a non-negative integer.

    Example::

        >>> _require_indices([1, 0], "frames")
        (1, 0)
        >>> _require_indices([1.0], "frames")
        (1,)
        >>> _require_indices("", "frames")
        Traceback (most recent call last):
            ...
        TypeError: frames must be a list or tuple of indices, got ''.
    """
    if not isinstance(values, (list, tuple)):
        raise TypeError(
            "%s must be a list or tuple of indices, got %r." % (label, values)
        )
    return tuple(index_value(entry, label) for entry in values)


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
    # ``bool`` cannot be subclassed and both values are singletons, so identity
    # is the exact test.  An object merely claiming to be a bool through
    # ``__class__`` satisfies ``isinstance`` and has no JSON counterpart.
    if value is not True and value is not False:
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
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("%s must be a string or None, got %r." % (label, value))
    try:
        # The exact text is returned so that a later length or content check
        # reads the characters the value holds rather than what it reports.
        return exact_str(value, label)
    except TypeError:
        # exact_str refuses an object that only claims to be a str.
        raise TypeError(
            "%s must be a string or None, got %r." % (label, value)
        ) from None


def _require_member(value: Any, allowed: Tuple[str, ...], label: str) -> str:
    """Reject anything outside a frozen vocabulary, including ``bool``.

    Membership is decided on the plain text the value actually holds.  ``in``
    uses ``__eq__``, so a ``str`` subclass overriding it satisfies any vocabulary
    check and is then published verbatim -- the value being validated would be
    the one deciding whether it is valid.

    :param value: Candidate value supplied by a caller.
    :type value: object
    :param allowed: Frozen vocabulary for this field.
    :type allowed: Tuple[str, ...]
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated value as an exact ``str``.
    :rtype: str
    :raises ValueError: If the value is not one of the allowed names.

    Example::

        >>> _require_member("formal", ("none", "formal"), "mode")
        'formal'
    """
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError(
            "%s must be one of %s, got %r." % (label, ", ".join(allowed), value)
        )
    try:
        plain = exact_str(value, label)
    except TypeError:
        # exact_str refuses an object that only claims to be a str.
        raise ValueError(
            "%s must be one of %s, got %r." % (label, ", ".join(allowed), value)
        ) from None
    if plain not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r." % (label, ", ".join(allowed), value)
        )
    return plain


#: Metadata keys whose values are indices rather than free-form values.
INDEX_REF_KEYS = ("frame", "frames", "step", "steps")


def _canonical_index_refs(refs: Dict[str, Any]) -> Dict[str, Any]:
    """Publish the index keys of a metadata mapping in their canonical form.

    ``frames`` and ``steps`` are canonicalized to integers, so echoing a
    whole-valued float back under ``frame`` would put two JSON types for one
    position in the same document.  Only these keys are touched: a whole-valued
    float under any other key may well be a measurement rather than a position.

    A value that is not an index is left alone here rather than refused: this
    mapping is free-form metadata, and the dedicated fields are where an index is
    required.

    :param refs: Validated metadata mapping.
    :type refs: Dict[str, object]
    :return: The same mapping with canonical index values.
    :rtype: Dict[str, object]

    Example::

        >>> _canonical_index_refs({"frame": 1.0, "threshold": 2.5})
        {'frame': 1, 'threshold': 2.5}
    """
    canonical = {}
    for key, value in refs.items():
        if key not in INDEX_REF_KEYS:
            canonical[key] = value
            continue
        try:
            if isinstance(value, (list, tuple)):
                canonical[key] = tuple(index_value(item, key) for item in value)
            else:
                canonical[key] = index_value(value, key)
        except (TypeError, ValueError):
            # index_value refuses a value that is not an index; metadata is
            # free-form, so it is republished as recorded instead.
            canonical[key] = value
    return canonical


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
        # Every published string is replaced by the exact text it holds before
        # anything reads it.  Otherwise the checks below run against methods the
        # value itself provides: `len`, `startswith`, `__iter__`, `__bool__` and
        # `__lt__` are all overridable, so a subclass could pass a check and then
        # publish something the check would have refused.
        for name in ("stable_id", "category", "summary"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise ValueError("constraint %s must be a non-empty string." % name)
            try:
                plain = exact_str(value, "constraint %s" % name)
            except TypeError:
                # exact_str refuses an object that only claims to be a str.
                raise ValueError(
                    "constraint %s must be a non-empty string." % name
                ) from None
            if not plain:
                raise ValueError("constraint %s must be a non-empty string." % name)
            object.__setattr__(self, name, plain)
        # The published schema constrains this to the five known families, so a
        # category outside them makes to_canonical() emit output that fails the
        # contract it publishes.  category_role states the same rule and is what
        # every reader of this field goes through.
        try:
            category_role(self.category)
        except ValueError:
            raise ValueError(
                "constraint category %r belongs to no known family." % self.category
            ) from None
        if not is_printable_ascii(self.stable_id):
            raise ValueError(
                "constraint stable_id must be printable ASCII, got %r." % self.stable_id
            )
        # The validated text is written back, not just checked: a well-behaved
        # str subclass would otherwise be published verbatim, so the frozen
        # vocabulary would hold a value whose repr is not the vocabulary's.
        object.__setattr__(
            self, "stage", _require_member(self.stage, _STAGES, "constraint stage")
        )
        # The exact type, not isinstance: a subclass passes the check and then
        # supplies its own to_canonical(), so the object that was validated is
        # not the one that gets published.  The same rule applies at every
        # composition boundary below.
        if type(self.source) is not BmcSourceRef:
            raise TypeError("constraint source must be BmcSourceRef.")
        object.__setattr__(self, "frames", _require_indices(self.frames, "frames"))
        object.__setattr__(self, "steps", _require_indices(self.steps, "steps"))
        object.__setattr__(
            self,
            "refs",
            MappingProxyType(
                _canonical_index_refs(_require_json_mapping(self.refs, "refs"))
            ),
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
            "refs": json_canonical(self.refs),
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
        if type(self.constraint) is not BmcConstraintRef:
            raise TypeError("core item constraint must be BmcConstraintRef.")
        object.__setattr__(
            self,
            "semantic_role",
            _require_member(
                self.semantic_role, _SEMANTIC_ROLES, "core item semantic_role"
            ),
        )
        object.__setattr__(
            self,
            "source_excerpt",
            _require_optional_text(self.source_excerpt, "core item source_excerpt"),
        )
        object.__setattr__(
            self,
            "human_text",
            _require_optional_text(self.human_text, "core item human_text"),
        )
        object.__setattr__(
            self,
            "source_excerpt_truncated",
            _require_flag(
                self.source_excerpt_truncated, "core item source_excerpt_truncated"
            ),
        )
        object.__setattr__(
            self, "editable", _require_flag(self.editable, "core item editable")
        )
        if (
            self.source_excerpt is not None
            and len(self.source_excerpt) > MAX_SOURCE_EXCERPT_CHARS
        ):
            raise ValueError(
                "core item source_excerpt must not exceed %d code points, got %d."
                % (MAX_SOURCE_EXCERPT_CHARS, len(self.source_excerpt))
            )
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
            "normalized_fact": json_canonical(self.normalized_fact),
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
        object.__setattr__(
            self, "scope", _require_member(self.scope, _SCOPES, "core scope")
        )
        object.__setattr__(
            self,
            "granularity",
            _require_member(self.granularity, _GRANULARITIES, "core granularity"),
        )
        object.__setattr__(
            self,
            "reduction",
            _require_member(self.reduction, _REDUCTIONS, "core reduction"),
        )
        object.__setattr__(
            self,
            "subset_minimality",
            _require_member(
                self.subset_minimality, _MINIMALITIES, "core subset_minimality"
            ),
        )
        expected_minimality = _REDUCTION_MINIMALITY[self.reduction]
        if self.subset_minimality != expected_minimality:
            raise ValueError(
                "reduction %r requires subset_minimality %r, got %r; only a "
                "completed deletion sweep may claim 'proven'."
                % (self.reduction, expected_minimality, self.subset_minimality)
            )
        if not isinstance(self.formula_summary, str):
            raise ValueError("core formula_summary must be a non-empty string.")
        try:
            plain_summary = exact_str(self.formula_summary, "core formula_summary")
        except TypeError:
            # exact_str refuses an object that only claims to be a str.
            raise ValueError(
                "core formula_summary must be a non-empty string."
            ) from None
        if not plain_summary:
            raise ValueError("core formula_summary must be a non-empty string.")
        object.__setattr__(self, "formula_summary", plain_summary)
        items = tuple(self.items)
        if not items:
            raise ValueError("core items must not be empty.")
        for item in items:
            if type(item) is not BmcCoreItem:
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
            tuple(
                # Every member's constraint is a BmcConstraintRef, whose stable_id is
                # already replaced by its exact text, so ordering here cannot be
                # steered by a member's own comparison methods.
                sorted(items, key=lambda item: item.constraint.stable_id)
            ),
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
        object.__setattr__(
            self,
            "requested_mode",
            _require_member(self.requested_mode, _MODES, "requested_mode"),
        )
        object.__setattr__(
            self,
            "achieved_mode",
            _require_member(self.achieved_mode, _MODES, "achieved_mode"),
        )
        object.__setattr__(
            self, "status", _require_member(self.status, _STATUSES, "status")
        )
        if self.classification is not None:
            object.__setattr__(
                self,
                "classification",
                _require_member(
                    self.classification, tuple(CLASSIFICATION_SCOPES), "classification"
                ),
            )
        object.__setattr__(
            self,
            "reason",
            _require_optional_text(self.reason, "explanation reason"),
        )
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
            # The comparisons below would otherwise be answered by the value's
            # own __lt__ and __float__, so a negative duration could report
            # itself as non-negative and be published as recorded.
            try:
                plain = (
                    exact_float(self.elapsed_ms, "explanation elapsed_ms")
                    if isinstance(self.elapsed_ms, float)
                    else float(exact_int(self.elapsed_ms, "explanation elapsed_ms"))
                )
            except TypeError:
                # exact_* refuse a value that only claims to be a number.
                raise TypeError(
                    "explanation elapsed_ms must be a number or None."
                ) from None
            if not math.isfinite(plain):
                raise ValueError(
                    "explanation elapsed_ms must be finite, got %r." % self.elapsed_ms
                )
            if plain < 0:
                raise ValueError("explanation elapsed_ms must not be negative.")
            object.__setattr__(self, "elapsed_ms", plain)
        if self.core is not None:
            if type(self.core) is not BmcConflictCore:
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
        # A caller who requested nothing gets no explanation object at all, so
        # such an object can only misreport what was asked for.
        if self.requested_mode == "none":
            raise ValueError(
                "requesting 'none' publishes no explanation at all, so an "
                "explanation object cannot record it as the request."
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
        # The authoritative check.  Everything above reports a specific mistake
        # well, but the checks are independent, so their conjunction admits
        # combinations that no authored row describes.
        signature = (
            self.requested_mode,
            self.achieved_mode,
            self.status,
            self.classification is not None,
            self.core is not None,
            self.proof is not None,
            self.reason is not None,
        )
        if signature not in _DELIVERY_SIGNATURES:
            raise ValueError(
                "delivery (requested=%r, achieved=%r, status=%r, "
                "classification=%s, core=%s, proof=%s, reason=%s) is outside "
                "the frozen truth table."
                % (
                    self.requested_mode,
                    self.achieved_mode,
                    self.status,
                    *("present" if flag else "absent" for flag in signature[3:]),
                )
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
