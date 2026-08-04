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
* :class:`BmcReasoningStep` - one step of the deterministic conflict narrative
* :class:`BmcConflictNarrative` - the deterministic account of why no execution
  exists, rendered from the published core and its normalized facts alone
* :class:`BmcProofNode` - one checked step of the verifiable proof
* :class:`BmcConflictProof` - the checked proof graph, published at proof depth
* :class:`BmcInfeasibilityExplanation` - the frozen top-level container
* :func:`explanation_text_lines` - the single renderer that both the CLI and
  ``BmcSolveResult.to_text()`` use, so neither can drift from the other

.. note::
   Both optional slots are published now.  A complete formal explanation requires
   a narrative whose derivation closed, and a proof-depth one additionally
   requires a proof whose nodes that narrative cites -- the delivery table refuses
   a proof beside a shallower achieved depth, and refuses a narrative citing proof
   nodes when no proof was published.

.. note::
   Nothing in this module imports ``z3``, reads a file or runs a solver.  A
   narrative is rendered from the published core and its normalized facts, so it
   cannot state more than the recognizers established: a shape none of them reads
   yields ``derivation_status="structural_only"`` and no conflict step rather than
   an invented chain.

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
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, Tuple

from .provenance import (
    BmcSourceRef,
    _require_json_mapping,
    exact_float,
    exact_int,
    exact_str,
    json_canonical,
)

try:
    from typing import Literal, get_args
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    # ``Literal`` and ``get_args`` both arrived in 3.8; the 3.7 floor this project
    # supports gets them from typing_extensions, which the runtime vocabularies
    # below read so a published type and its check cannot drift apart.
    from typing_extensions import Literal, get_args

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
BmcDerivationStatus = Literal["complete", "partial", "structural_only", "not_available"]
BmcReasoningStepKind = Literal["fact", "derivation", "conflict"]
BmcProofNodeKind = Literal["input", "derived", "contradiction"]
BmcProofRuleId = Literal[
    "source_fact",
    "case_condition_entailment",
    "transition_assignment",
    "equality_substitution",
    "arithmetic_evaluation",
    "interval_intersection",
    "state_domain_exhaustion",
    "definedness_failure",
    "incompatible_equalities",
    "boolean_complement",
]
BmcProofVerificationMethod = Literal[
    "core_binding", "core_binding_unit", "rule_checker", "solver_entailment"
]
BmcProofInputMinimality = Literal["subset_minimal"]
BmcProofGraphMinimality = Literal["dependency_pruned"]
BmcProofVerificationStatus = Literal["verified"]
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
class _DeliveryRow(NamedTuple):
    """One authored row of the frozen delivery table.

    The row used to be a bare seven-tuple whose last four positions were
    booleans, so reading it -- or documenting it -- meant counting positions and
    remembering that ``None`` is "either" while ``False`` is "forbidden".  Three
    of this series' documentation defects came out of getting that decoding
    wrong, in a page whose whole job was to state which combinations are legal.
    Naming the fields does not change a single accepted combination; it removes
    the step where the reader has to decode before they can be right.

    :param requested_modes: Requested depths this row covers.
    :type requested_modes: Tuple[str, ...]
    :param achieved_mode: The depth actually delivered.
    :type achieved_mode: str
    :param status: How complete the delivered depth is.
    :type status: str
    :param classification: ``True`` required, ``False`` forbidden, ``None``
        either.
    :type classification: bool, optional
    :param core: Same three-valued convention.
    :type core: bool, optional
    :param proof: Same three-valued convention.
    :type proof: bool, optional
    :param reason: Same three-valued convention.
    :type reason: bool, optional

    Example::

        >>> row = _DeliveryRow(("formal",), "none", "timeout", False, False, False, True)
        >>> row.reason
        True
    """

    requested_modes: Tuple[str, ...]
    achieved_mode: str
    status: str
    classification: Optional[bool]
    core: Optional[bool]
    proof: Optional[bool]
    reason: Optional[bool]


_DELIVERY_MATRIX_ROWS = (
    # Row 1: the first optional probe returned unknown, so there is neither a
    # classification nor a publishable sound core.
    _DeliveryRow(("formal", "proof"), "none", "unknown", False, False, False, True),
    # Row 2: the same shape after the budget expired instead.
    _DeliveryRow(("formal", "proof"), "none", "timeout", False, False, False, True),
    # Row 3: classification finished, the raw core did not.  The classification
    # metadata is kept, but it must not pose as a formal artifact.
    _DeliveryRow(("formal", "proof"), "none", "partial", True, False, False, True),
    # Rows 4, 6 and 7: a sound core whose minimality, scope or proof is still
    # open.  All three are indistinguishable from the published fields.
    _DeliveryRow(("formal", "proof"), "formal", "partial", None, True, False, True),
    # Row 5: a diagnostic subset-minimal core with complete semantic facts.
    # Requesting 'proof' cannot land here: an unclosed proof forces row 7.
    _DeliveryRow(("formal",), "formal", "complete", True, True, False, False),
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
    _DeliveryRow(("proof",), "proof", "partial", False, True, True, True),
    # Row 8: a verified proof over a diagnostic artifact.
    _DeliveryRow(("proof",), "proof", "complete", True, True, True, False),
    # The row the previous stage recorded as missing.  A diagnostic classification
    # did finish and a proof was verified, but the narrative degraded: a semantic
    # fact with no dedicated recognizer forces structural_only, and the artifact is
    # then partial rather than complete.  Row 9 is the same status over a
    # stage-fallback artifact, where no classification exists at all; this is its
    # counterpart with one.
    _DeliveryRow(("proof",), "proof", "partial", True, True, True, True),
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
    # The scan runs on the exact text, so the answer describes the characters
    # that would actually be published.
    try:
        plain = exact_str(value, "value")
    except TypeError:
        # exact_str raises for anything that is not a str.
        return False
    return bool(plain) and all("\x20" <= char <= "\x7e" for char in plain)


#: How each published relation reads in an English sentence.
#:
#: The keys are the operator tags a ``variable_comparison`` fact may carry, so a
#: relation added to the recognizer without a phrase here fails loudly instead of
#: rendering as a bare tag inside otherwise fluent prose.
_RELATION_PHRASES = {
    "eq": "to equal %s",
    "ne": "to differ from %s",
    "le": "to be at most %s",
    "lt": "to be less than %s",
    "ge": "to be at least %s",
    "gt": "to be greater than %s",
}

#: How an assignment reads, keyed by the operation a published fact names.
#:
#: Each phrase names both the operand and the variable, because the natural word
#: order differs between them: an addition reads "adds 1 to x" and a multiplication
#: reads "multiplies x by 1".  Formatting by name rather than by position is what
#: lets each operation put them where its own English wants them.  An operation
#: absent here has no reading, which is why the recognizer only names the four the
#: evaluation rule can apply.
_ASSIGNMENT_PHRASES = {
    "add": "adds {operand} to {variable}",
    "sub": "subtracts {operand} from {variable}",
    "mul": "multiplies {variable} by {operand}",
    "div": "divides {variable} by {operand}",
    # Not an arithmetic update: the next frame's value does not depend on this one,
    # so the sentence says what the variable becomes rather than how it changes.
    "set": "sets {variable} to {operand}",
}

#: Which authority a role speaks for, in the voice the sentence needs.
#:
#: A reader deciding where to make an edit cares whether a requirement came from
#: their query, their machine definition or the encoding, so the sentence names
#: that rather than the role tag.
_ROLE_VOICES = {
    "assumption": "the query",
    "initial_fact": "the initializer",
    "domain_rule": "the model",
    "transition_rule": "the transition",
    "definedness": "the expression",
}


def require_published_text(value: Any, where: str) -> str:
    """Return published text, refusing anything a reader would see as empty.

    One rule with six exits is one rule only if they share a predicate.  These
    fields had grown three different emptiness tests -- ``.strip()``, ``if not
    text`` and plain truthiness -- so ``"   "`` was refused in three places and
    published in the other three, and the schema's ``minLength`` agreed with
    neither.  Whitespace is the case that separates them, and it is exactly what a
    reader gets nothing from.

    :param value: The candidate text.
    :type value: object
    :param where: Field name used in the error message.
    :type where: str
    :return: The validated text as an exact ``str``.
    :rtype: str
    :raises TypeError: If the value is not a plain ``str``.  It comes from
        :func:`pyfcstm.bmc.provenance.exact_str`, which refuses a lookalike before
        emptiness is even considered, so a caller distinguishing the two failures
        gets the type error first.
    :raises ValueError: If the value is a ``str`` holding no non-whitespace
        character.

    Example::

        >>> require_published_text("At frame 0, x equals 1.", "human_text")
        'At frame 0, x equals 1.'
        >>> require_published_text("   ", "human_text")
        Traceback (most recent call last):
        ValueError: human_text must not be blank.
    """
    text = exact_str(value, where)
    if not text.strip():
        raise ValueError("%s must not be blank." % where)
    return text


#: What a frame's state slot is called where a subject has to be printed.
#:
#: The rules compare subjects before values, so the slot needs one to be compared
#: by.  The name is only a label: what tells the slot apart from a variable is the
#: fact's own ``state_slot`` flag, which the slot comparison, the binding and the
#: reading all consult.  Nothing decides identity by reading this string.
#:
#: That was the third attempt.  Twice the slot was told apart by its name, and twice
#: an argument for why a model could not declare that name turned out to be wrong --
#: ``state`` is a keyword only in the lexer's default mode, so an import mapping
#: renames past it; and ``$state`` is reachable too, because the target *template*
#: rule admits ``$`` and ``def x_* -> *$state;`` with an empty capture renders it
#: exactly.  A name a model can also write cannot carry identity, however it is
#: spelled, so identity moved off the name entirely.
#:
#: The spelling is kept for the reader's sake -- it matches how the sentinel state
#: paths spell themselves -- and a model that declares the same name is now simply a
#: model with a variable of that name.
_STATE_SLOT_SUBJECT = "$state"


#: How the encoding's own two states are read to someone who wrote the model.
#:
#: They are not states the author declared, and the query binder refuses them by
#: name -- ``active("$STATE_TERMINATE")`` comes back as a reserved path.  A reader
#: told that name has been handed something they cannot use, so each is read as the
#: thing the query language already lets them talk about: ``terminated()`` for one,
#: the ``init`` clause for the other.
#:
#: Each spelling carries parentheses, which no state path can, so a model that
#: happens to declare a state called ``terminated`` is still spelled apart from
#: this one -- and the reader is looking at the very token they would type.
_SENTINEL_STATE_PHRASES = {
    "$STATE_TERMINATE": "terminated()",
    "$STATE_INIT": "before(start)",
}


def _state_display(code: Any, state_paths: Optional[Mapping]) -> str:
    """Spell one state for a reader, from the model's table when there is one.

    The encoding numbers states, and a reader who wrote ``Root.A`` cannot map
    ``state 1`` back to it: the item's excerpt lives in another block and quotes
    a whole line.  Given the model's own table the reader gets the path; with no
    table, or with no entry for this state, the code stands in rather than a name
    being invented.

    Every reader-facing surface resolves a state through this one function.  The
    proof reading and the core items' human text are two spellings of the same
    state to the same reader, so a table that resolves differently between them --
    a missing entry against a present-but-empty one, say -- would put two names on
    one thing.

    :param code: The published state code.
    :type code: object
    :param state_paths: State code to authored path, or ``None``.
    :type state_paths: Optional[Mapping[int, str]]
    Two of the encoding's states are not the author's at all, and the query binder
    refuses them by name: writing ``active("$STATE_TERMINATE")`` is rejected as a
    reserved path.  Telling a reader a name they are forbidden to type is worse than
    unhelpful, so each is read as the thing the query language does let them write.
    Those spellings carry parentheses, which no state path can, so a model that
    declares a state of its own called ``terminated`` stays distinct from this one.

    :param code: The published state code.
    :type code: object
    :param state_paths: State code to authored path, or ``None``.
    :type state_paths: Optional[Mapping[int, str]]
    :return: The state's authored path, its reader-facing phrase, or its code.
    :rtype: str

    Example::

        >>> _state_display(1, {1: "Root.A"})
        'Root.A'
        >>> _state_display(1, None)
        '1'
        >>> _state_display(1, {2: "Root.B"})
        '1'
        >>> _state_display(-1, {-1: "$STATE_TERMINATE"})
        'terminated()'
    """
    if state_paths:
        path = state_paths.get(code)
        if path is not None:
            return _SENTINEL_STATE_PHRASES.get(path, "%s" % path)
    return "%s" % code


def _state_label(code: Any, state_paths: Optional[Mapping]) -> str:
    """Render one state for a human sentence.

    :param code: The published state code.
    :type code: object
    :param state_paths: State code to authored path, or ``None``.
    :type state_paths: Optional[Mapping[int, str]]
    :return: The phrase naming that state.
    :rtype: str

    Example::

        >>> _state_label(1, {1: "Root.A"})
        'state Root.A'
        >>> _state_label(1, None)
        'state 1'
    """
    return "state %s" % _state_display(code, state_paths)


def _state_phrase(states, names: Optional[Mapping[int, str]] = None) -> str:
    """Return a reader-facing list of states."""
    return ", ".join(_state_display(state, names) for state in states)


#: How a relation reads inside a condition clause.
#:
#: Separate from :data:`_RELATION_PHRASES` because that table completes "requires
#: x", so its phrases are infinitives.  A clause needs the indicative: "where y is
#: at least 3", not "where y to be at least 3".
_CONDITION_RELATIONS = {
    "eq": "is %s",
    "ne": "is not %s",
    "le": "is at most %s",
    "lt": "is less than %s",
    "ge": "is at least %s",
    "gt": "is greater than %s",
}


def _condition_clause(members, names=None) -> str:
    """Read the condition a case is selected under, as a clause that can be inserted.

    Empty when there is no condition, so a fact that carries none reads exactly as it
    did before this existed.  A member with no reading is named by its tag rather than
    dropped: a clause that quietly listed fewer requirements than the fact carries
    would understate what the step depends on.

    :param members: The published condition facts, or ``None``.
    :type members: Optional[Sequence[Mapping[str, Any]]]
    :param names: What the model calls each state, keyed by encoded index, defaults to
        ``None``.
    :type names: Optional[Mapping[int, str]], optional
    :return: A leading-space clause, or the empty string.
    :rtype: str

    Example::

        >>> _condition_clause(None)
        ''
        >>> member = {"kind": "state_membership", "frame": 0, "state": 1}
        >>> _condition_clause([member])
        ' where frame 0 holds 1'
        >>> _condition_clause([member], {1: "Root.A"})
        ' where frame 0 holds Root.A'
    """
    if not members:
        return ""
    phrases = []
    for member in members:
        kind = member.get("kind")
        if kind == "state_membership":
            phrases.append(
                "frame %s %s %s"
                % (
                    member.get("frame"),
                    "does not hold" if member.get("excluded") else "holds",
                    _state_display(member.get("state"), names),
                )
            )
        elif kind == "variable_comparison":
            # A relation reads differently as a condition than as a requirement:
            # ``_RELATION_PHRASES`` is written to follow "requires x", which gives
            # "y to be at least 3" where a clause needs "y is at least 3".
            phrase = _CONDITION_RELATIONS.get(member.get("operator"))
            phrases.append(
                "%s %s at frame %s"
                % (
                    member.get("variable"),
                    (phrase % member.get("value")) if phrase else "is constrained",
                    member.get("frame"),
                )
            )
        else:
            phrases.append("a %s requirement" % (kind or "further"))
    return " where %s" % " and ".join(phrases)


def _fact_sentence(
    fact: Mapping[str, Any], names: Optional[Mapping[int, str]] = None
) -> str:
    """Return the sentence stating one fact in the model's vocabulary.

    :param fact: The fact a node concludes.
    :type fact: Mapping[str, object]
    :param names: What the model calls each state, if the caller knows.
    :type names: Mapping[int, str], optional
    :return: One sentence.
    :rtype: str

    Example::

        >>> _fact_sentence({"kind": "state_domain", "frame": 1, "states": [1, 2]})
        'At frame 1, the model allows the states 1, 2.'
        >>> _fact_sentence(
        ...     {"kind": "state_domain", "frame": 1, "states": [1]}, {1: "Root.Idle"}
        ... )
        'At frame 1, the model allows the states Root.Idle.'
    """
    kind = fact.get("kind")
    if kind == "variable_equality":
        if fact.get("state_slot"):
            # A frame's state slot is compared like a variable so the rules can
            # reach it, but it is read like a state: rendering the equality verbatim
            # would tell the author their state "must equal 2", which names neither
            # the slot nor the state they asked for.
            return "At frame %s, the state must be %s." % (
                fact.get("frame"),
                _state_display(fact.get("value"), names),
            )
        return "At frame %s, %s must equal %s." % (
            fact.get("frame"),
            fact.get("variable"),
            fact.get("value"),
        )
    if kind == "variable_bound":
        phrase = {
            "ge": "at least",
            "gt": "greater than",
            "le": "at most",
            "lt": "less than",
        }.get(fact.get("operator"), "related to")
        return "At frame %s, %s must be %s %s." % (
            fact.get("frame"),
            fact.get("variable"),
            phrase,
            fact.get("value"),
        )
    if kind == "state_domain":
        return "At frame %s, the model allows the states %s." % (
            fact.get("frame"),
            _state_phrase(fact.get("states") or (), names),
        )
    if kind == "state_exclusion":
        return "At frame %s, state %s is ruled out." % (
            fact.get("frame"),
            _state_display(fact.get("state"), names),
        )
    if kind == "definedness_guard":
        return "At frame %s, the %s requires %s to differ from %s." % (
            fact.get("frame"),
            fact.get("operation"),
            fact.get("variable"),
            fact.get("forbidden"),
        )
    if kind == "proposition":
        return "At the frame it names, %s is required to %s." % (
            fact.get("identity"),
            "hold" if fact.get("holds") else "not hold",
        )
    if kind == "transition_case":
        # The condition is part of what the fact states, so it is part of the reading.
        # Without it the sentence asserts the assignment unconditionally while the
        # fact carries a condition -- the human account and the machine fact would
        # then disagree, which is the one thing this tier exists to prevent.
        return "Between frame %s and frame %s, the transition changes %s by %s%s." % (
            fact.get("frame"),
            fact.get("target_frame"),
            fact.get("variable"),
            fact.get("operand", fact.get("operand_variable")),
            _condition_clause(fact.get("condition"), names),
        )
    if kind == "arithmetic_expression":
        return "Between frame %s and frame %s, %s changes by %s." % (
            fact.get("frame"),
            fact.get("target_frame"),
            fact.get("variable"),
            fact.get("operand"),
        )
    if kind == "false":
        # The contradiction node's own sentence.  A reading built from the graph says
        # more -- which rule closed it, and that the property went unevaluated -- but
        # the node still has to state something when read on its own, and the generic
        # fallback below would say the opposite of what a contradiction is.
        return "These requirements cannot all hold."
    return "A model or query requirement constrains this scenario."


def human_text_for_fact(
    role: str, fact: Mapping, state_paths: Optional[Mapping] = None
) -> str:
    """Render one published fact as a deterministic domain sentence.

    The sentence is derived from the fact alone, so it never states more than a
    recognizer established.  A fact that carries no domain reading renders as its
    own identity instead of being dressed up as a derivation nobody made.

    :param role: The item's semantic role.
    :type role: str
    :param fact: The published normalized fact.
    :type fact: Mapping
    :param state_paths: State code to authored path, so a sentence can name the
        state the reader wrote rather than the encoding's number for it; defaults
        to ``None``.
    :type state_paths: Optional[Mapping[int, str]], optional
    :return: One sentence describing what the group requires.  A fact whose tag
        arrives without the keys that tag implies renders as an unreduced group
        rather than raising, since the published gates require only the tag.
    :rtype: str

    Example::

        >>> human_text_for_fact(
        ...     "assumption",
        ...     {
        ...         "kind": "variable_comparison",
        ...         "variable": "x",
        ...         "frame": 0,
        ...         "operator": "eq",
        ...         "value": 1,
        ...     },
        ... )
        'At frame 0, the query requires x to equal 1.'
    """
    kind = fact.get("kind")
    voice = _ROLE_VOICES.get(role, "the model")
    # A tag with its companion keys missing passes both published gates -- the
    # schema requires ``kind`` and nothing else -- so reading them directly turned
    # a payload both gates accept into a bare KeyError out of a public function.
    # Rendering the fallback keeps the contract: a sentence never claims more than
    # the fact carries.
    if kind == "variable_comparison" and {
        "operator",
        "value",
        "variable",
        "frame",
    } <= set(fact):
        phrase = _RELATION_PHRASES.get(fact["operator"])
        if phrase is None:
            return _unreduced_sentence(role, fact)
        phrase = phrase % fact["value"]
        return "At frame %s, %s requires %s %s." % (
            fact["frame"],
            voice,
            fact["variable"],
            phrase,
        )
    if kind == "state_membership" and {"frame", "state"} <= set(fact):
        # The state code is published rather than a name: the encoding's map is
        # not carried on the item, and the source excerpt beside this sentence
        # quotes the line that names the state.  A negated assertion rules the
        # state out instead of requiring it, and saying "requires" there would
        # invert the source line.
        return "At frame %s, %s %s %s." % (
            fact["frame"],
            voice,
            "rules out" if fact.get("excluded") else "requires",
            _state_label(fact["state"], state_paths),
        )
    if kind == "state_domain" and {"frame", "states"} <= set(fact):
        # The domain is published as encoded integers, so the sentence reports
        # how many states remain legal rather than inventing names the fact does
        # not carry.
        count = len(fact["states"])
        return "At frame %s, %s allows %d state%s." % (
            fact["frame"],
            voice,
            count,
            "" if count == 1 else "s",
        )
    if kind == "proposition" and {"identity", "holds"} <= set(fact):
        return "At the step it names, %s requires %s to %s." % (
            voice,
            fact["identity"],
            "occur" if fact["holds"] else "not occur",
        )
    if kind == "transition_case" and {
        "variable",
        "frame",
        "target_frame",
        "operation",
        "condition",
    } <= set(fact):
        phrase = _ASSIGNMENT_PHRASES.get(fact["operation"])
        operand = fact.get("operand")
        if operand is None:
            operand = fact.get("operand_variable")
        if phrase is None or operand is None:
            return _unreduced_sentence(role, fact)
        # The condition is read out rather than alluded to.  An earlier version said
        # "where its case applies" and justified it by the condition being the
        # encoder's own text -- true of the first shape this fact had, and false once
        # it became a list of normalized facts.  The reader is owed the requirement
        # itself: the step after this one says "therefore", and its only warrant is
        # that this condition holds.
        return "Between frame %s and frame %s, %s %s%s." % (
            fact["frame"],
            fact["target_frame"],
            voice,
            phrase.format(operand=operand, variable=fact["variable"]),
            _condition_clause(fact["condition"], state_paths),
        )
    if kind == "definedness_condition" and {"frame", "operation"} <= set(fact):
        variable = fact.get("variable")
        if variable is None:
            return "At frame %s, a %s must stay defined." % (
                fact["frame"],
                fact["operation"],
            )
        return "At frame %s, the %s requires %s to be non-zero." % (
            fact["frame"],
            fact["operation"],
            variable,
        )
    return _unreduced_sentence(role, fact)


def _unreduced_sentence(role: str, fact: Mapping) -> str:
    """Describe a group whose fact carries no usable reading.

    :param role: The item's semantic role.
    :type role: str
    :param fact: The published normalized fact.
    :type fact: Mapping
    :return: One sentence naming the group without claiming a derivation.
    :rtype: str

    Example::

        >>> _unreduced_sentence("transition_rule", {"kind": "structural_constraint"})
        'A transition rule constrains this scenario without a reduced domain fact.'
    """
    # No recognizer read this group, so the sentence says what the group *is*
    # rather than what it requires.  Naming the role reads as a description a
    # reader can place -- "the transition rule for this step" -- instead of an
    # apology about the reduction, while still promising no derivation.
    article = "an" if role[0] in "aeiou" else "a"
    return "%s %s constrains this scenario without a reduced domain fact." % (
        article.capitalize(),
        role.replace("_", " "),
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
    # The prefix test runs on the exact text: the category is a dispatch key, so
    # the family it resolves to has to follow from the characters themselves.
    try:
        plain = exact_str(category, "category")
    except TypeError:
        # exact_str raises for anything that is not a str.
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
        # exact_str raises for anything that is not a str.
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
#: Every tag a published normalized fact may carry.
#:
#: A fact describes *one* source group, so the vocabulary is deliberately small.
#: ``variable_comparison`` covers every relation between one frame variable and
#: one value, carrying the relation in an ``operator`` field rather than splitting
#: into a tag per relation.  ``state_membership`` pins one frame to one state code,
#: which is what an initial target and an ``active(...)`` assumption both lower to.
#: ``state_domain`` gives the legal states of a frame
#: and ``definedness_condition`` the operation a group keeps well defined.
#: ``transition_case`` gives the assignment one step's selected case makes, under
#: the condition that selects it.  ``proposition`` gives one requirement about one
#: event at one step, with the polarity the query asked for; a state assertion is
#: *not* one of these -- it stays ``state_membership``, because the rule that
#: exhausts a frame's domain reads state exclusions and would go dark if state
#: assertions moved here.
#: ``structural_constraint`` is the honest fallback for a shape no recognizer
#: reads.
#:
#: The cross-group patterns -- mutually exclusive equalities, an empty interval,
#: an exhausted state domain, a value carried across a step, a definedness
#: failure -- are *derivations* over several facts, so they are named by the
#: narrative's rule vocabulary and never appear here.  A machine consumer
#: dispatches on this tag, so adding one is a published-contract change.
_FACT_KINDS = (
    "structural_constraint",
    "variable_comparison",
    "state_membership",
    "state_domain",
    "definedness_condition",
    "transition_case",
    "proposition",
)

#: Frozen upper bound on a published excerpt, in Unicode code points.  A long
#: authored line would otherwise put an unbounded slice of the user's source
#: into canonical JSON.
MAX_SOURCE_EXCERPT_CHARS = 4096

#: Published slots that no delivery stage fills yet.
#:
#: Empty now that the proof tier is built.  The tuple stays because the guard it
#: drives is the difference between a reserved slot failing loudly and it being
#: serialized as ``null`` -- a caller reading ``null`` cannot tell "not produced"
#: from "produced and empty".
UNBUILT_SLOTS = ()

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
    :raises TypeError: If the value is not a real integer, so that no index can
        be read from it.

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
    """Reject a non-boolean where the JSON contract promises a boolean.

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
    # ``bool`` cannot be subclassed and both values are singletons, so identity is
    # the exact test and needs no isinstance fallback.
    if value is not True and value is not False:
        raise TypeError("%s must be a bool, got %r." % (label, value))
    return value


def _require_optional_text(value: Any, label: str) -> Optional[str]:
    """Reject a non-string value for an optional text field.

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
    try:
        return exact_str(value, label)
    except TypeError:
        # exact_str raises for anything that is not a str, which is how a wrong
        # type reaches this optional-text field.
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
    # ``bool`` is named separately because it is an ``int``, not because it could
    # pass for a member: no published vocabulary contains one.
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError(
            "%s must be one of %s, got %r." % (label, ", ".join(allowed), value)
        )
    plain = exact_str(value, label)
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
    :type stage: BmcConstraintStage
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
        # Each published string is stored as the exact text it holds, so the
        # emptiness check below and every later reader see the same characters.
        for name in ("stable_id", "category", "summary"):
            value = getattr(self, name)
            try:
                plain = exact_str(value, "constraint %s" % name)
            except TypeError:
                # exact_str raises for anything that is not a str, which is how a
                # wrong type passed to this constructor arrives here.
                raise ValueError(
                    "constraint %s must be a non-empty string." % name
                ) from None
            # ``summary`` is prose a reader sees; the other two are identifiers a
            # consumer matches on.  All three go through the one predicate so the
            # rule cannot grow a second reading of "empty".
            require_published_text(plain, "constraint %s" % name)
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
        # The exact type, not isinstance: each composition boundary publishes by
        # calling to_canonical() on what it stored, so it stores only the type
        # whose canonical output the schema describes.  The same rule applies at
        # every composition boundary below.
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
    :type semantic_role: BmcSemanticRole
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
        require_published_text(self.human_text, "core item human_text")
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
    :type scope: BmcConflictCoreScope
    :param formula_summary: Short description of the proven target formula.
    :type formula_summary: str
    :param granularity: Core granularity, currently always ``source_group``.
    :type granularity: BmcCoreGranularity
    :param reduction: How far deletion checking got: ``raw`` when no deletion
        check finished, ``partial_minimized`` when some did but the sweep is
        open, ``subset_minimal`` when every member proved necessary.
    :type reduction: BmcCoreReduction
    :param subset_minimality: Whether subset minimality has been proven.  It
        is determined by ``reduction``: only ``subset_minimal`` may claim
        ``proven``, which keeps "not proven minimal" distinct from "proven
        non-minimal".
    :type subset_minimality: BmcSubsetMinimality
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
        try:
            plain_summary = exact_str(self.formula_summary, "core formula_summary")
        except TypeError:
            # exact_str raises for anything that is not a str, which is how a wrong
            # type passed to this constructor arrives here.
            raise ValueError(
                "core formula_summary must be a non-empty string."
            ) from None
        require_published_text(plain_summary, "core formula_summary")
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


#: Every kind a published reasoning step may carry.
#:
#: ``fact`` restates one requirement, ``derivation`` combines earlier steps, and
#: ``conflict`` closes the chain.  A narrative that reached no contradiction has
#: no ``conflict`` step, which is how ``structural_only`` stays honest.
#:
#: Derived from the published :data:`BmcReasoningStepKind` rather than retyped, so
#: the runtime check and the type a caller annotates against cannot drift apart.
_REASONING_STEP_KINDS = get_args(BmcReasoningStepKind)

#: How far a derivation was reconstructed.
#:
#: ``complete`` closed the chain, ``partial`` got some of the way,
#: ``structural_only`` established joint unsatisfiability without a value or
#: state derivation, and ``not_available`` means the renderer produced nothing.
#:
#: Derived from the published :data:`BmcDerivationStatus` for the same reason.
_DERIVATION_STATUSES = get_args(BmcDerivationStatus)


@dataclass(frozen=True)
class BmcReasoningStep:
    """One step of the deterministic conflict narrative.

    A step never stands alone: it names the core members it reads, so a consumer
    can jump from a sentence to the source lines behind it.  ``proof_node_ids``
    stays empty outside proof mode, where the steps also bind to DAG nodes.

    :param kind: ``fact``, ``derivation`` or ``conflict``.
    :type kind: BmcReasoningStepKind
    :param item_ids: Stable ids of the core members this step reads.
    :type item_ids: Tuple[str, ...]
    :param proof_node_ids: Proof nodes this step binds to, empty outside proof
        mode.
    :type proof_node_ids: Tuple[str, ...]
    :param text: One deterministic sentence.
    :type text: str
    :raises ValueError: If the kind is unknown, the step reads no member, or a
        published id repeats.

    Example::

        >>> step = BmcReasoningStep(
        ...     "fact", ("assumption.0000.frame.0000",), (), "x must equal 1.",
        ... )
        >>> step.kind
        'fact'
    """

    kind: BmcReasoningStepKind
    item_ids: Tuple[str, ...]
    proof_node_ids: Tuple[str, ...]
    text: str

    def __post_init__(self) -> None:
        _require_member(self.kind, _REASONING_STEP_KINDS, "reasoning step kind")
        # Freeze before validating.  ``frozen=True`` stops the field being
        # rebound, not the list behind it being emptied, so a caller keeping its
        # own reference could pass every check here and then remove the members
        # those checks were about.  ``BmcConflictCore.items`` has always copied
        # for this reason; these fields had not.
        object.__setattr__(self, "item_ids", tuple(self.item_ids))
        object.__setattr__(self, "proof_node_ids", tuple(self.proof_node_ids))
        if not self.item_ids:
            # A step that reads nothing cannot be traced back to a source line,
            # which is the one thing a narrative step is for.
            raise ValueError("a reasoning step must reference at least one core item.")
        for name, ids in (
            ("item_ids", self.item_ids),
            ("proof_node_ids", self.proof_node_ids),
        ):
            for value in ids:
                # The schema types these arrays as non-empty strings, so anything
                # else reaches canonical JSON that a conforming validator refuses
                # -- the constructor accepting what the schema rejects, which is
                # the opposite direction from every named exception.
                require_published_text(value, "reasoning step %s entry" % name)
            if len(set(ids)) != len(ids):
                raise ValueError("reasoning step %s must not repeat an id." % name)
        require_published_text(self.text, "reasoning step text")

    def to_canonical(self) -> Dict[str, Any]:
        """Return the published mapping for this step.

        :return: Plain JSON containers in published key order.
        :rtype: Dict[str, Any]

        Example::

            >>> BmcReasoningStep("fact", ("g0",), (), "t").to_canonical()["kind"]
            'fact'
        """
        return {
            "kind": self.kind,
            "item_ids": list(self.item_ids),
            "proof_node_ids": list(self.proof_node_ids),
            "text": self.text,
        }


@dataclass(frozen=True)
class BmcConflictNarrative:
    """The deterministic account of why no execution exists.

    The narrative is rendered from the published core and its normalized facts
    alone.  It reads no file and runs no solver, so it cannot state more than the
    recognizers established: a shape with no domain reading yields
    ``structural_only`` and no ``conflict`` step rather than an invented chain.

    :param derivation_status: ``complete``, ``partial``, ``structural_only`` or
        ``not_available``.
    :type derivation_status: BmcDerivationStatus
    :param headline: One-line human summary.
    :type headline: str
    :param summary: Longer deterministic summary.
    :type summary: str
    :param reasoning_steps: Steps in causal order, defaults to ``()``.
    :type reasoning_steps: Tuple[BmcReasoningStep, ...], optional
    :param review_surfaces: Editable core ids offered for review, defaults to
        ``()``.
    :type review_surfaces: Tuple[str, ...], optional
    :raises ValueError: If the status is unknown, a text is blank, a review
        surface repeats, or a ``complete`` derivation carries no conflict step.

    Example::

        >>> BmcConflictNarrative("structural_only", "conflict", "summary").headline
        'conflict'
    """

    derivation_status: BmcDerivationStatus
    headline: str
    summary: str
    reasoning_steps: Tuple[BmcReasoningStep, ...] = ()
    review_surfaces: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_member(
            self.derivation_status, _DERIVATION_STATUSES, "narrative derivation_status"
        )
        # Same reason as the step above: copy before the invariants read them.
        object.__setattr__(self, "reasoning_steps", tuple(self.reasoning_steps))
        object.__setattr__(self, "review_surfaces", tuple(self.review_surfaces))
        for name, text in (("headline", self.headline), ("summary", self.summary)):
            require_published_text(text, "narrative %s" % name)
        if len(set(self.review_surfaces)) != len(self.review_surfaces):
            raise ValueError("narrative review_surfaces must not repeat an id.")
        if self.derivation_status == "complete" and not [
            step for step in self.reasoning_steps if step.kind == "conflict"
        ]:
            # "Complete" claims the chain reached the contradiction.  Without a
            # conflict step it claims a closed derivation whose closing step is
            # missing, which is exactly the overclaim structural_only avoids.
            raise ValueError(
                "a complete derivation requires a conflict reasoning step."
            )

    def to_canonical(self) -> Dict[str, Any]:
        """Return the published mapping for this narrative.

        :return: Plain JSON containers in published key order.
        :rtype: Dict[str, Any]

        Example::

            >>> narrative = BmcConflictNarrative("structural_only", "h", "s")
            >>> narrative.to_canonical()["derivation_status"]
            'structural_only'
        """
        return {
            "derivation_status": self.derivation_status,
            "headline": self.headline,
            "summary": self.summary,
            "reasoning_steps": [step.to_canonical() for step in self.reasoning_steps],
            "review_surfaces": list(self.review_surfaces),
        }


#: What a proof node contributes.
#:
#: ``input`` restates one core member as a domain fact, ``derived`` carries a new
#: fact obtained by a rule, and ``contradiction`` is the single node concluding
#: that no execution exists.
#:
#: Derived from the published :data:`BmcProofNodeKind` so the runtime check and the
#: annotated type cannot drift apart.
_PROOF_NODE_KINDS = get_args(BmcProofNodeKind)

#: The domain rules a step may cite.
#:
#: Closed on purpose: a step naming a rule outside this list has no published
#: premise shape, conclusion shape or side condition, so nothing could check it.
_PROOF_RULE_IDS = get_args(BmcProofRuleId)

#: How a step was checked.
#:
#: ``core_binding`` proves an input fact equivalent to its source group in both
#: directions, ``rule_checker`` verifies a rule application directly, and
#: ``solver_entailment`` re-encodes premises and conclusion and refutes their
#: conjunction.  There is deliberately no value for an unchecked step: the contract
#: forbids holes, trust and opaque solver steps in a published proof.
_PROOF_VERIFICATION_METHODS = get_args(BmcProofVerificationMethod)

#: The methods that describe an input's binding rather than a step's derivation.
#:
#: The split is published, not implied: the reference says of both bindings that they
#: are "used by input nodes only", and of the other two that they are used by derived
#: and root nodes.  Written out rather than derived, because which side a method falls
#: on is a statement about what was checked, not a fact about its name.
_INPUT_VERIFICATION_METHODS = ("core_binding", "core_binding_unit")

#: The one input-minimality a published proof may claim.
#:
#: Single-valued because a proof whose leaves are not exactly a proven
#: subset-minimal core is not published at all.
_PROOF_INPUT_MINIMALITIES = get_args(BmcProofInputMinimality)

#: The one graph-minimality a published proof may claim, for the same reason.
_PROOF_GRAPH_MINIMALITIES = get_args(BmcProofGraphMinimality)

#: The one verification status a published proof may claim, for the same reason.
_PROOF_VERIFICATION_STATUSES = get_args(BmcProofVerificationStatus)

#: The conclusion the single root node carries.
_PROOF_FALSE_CONCLUSION_KIND = "false"


@dataclass(frozen=True)
class BmcProofNode:
    """One checked step of the verifiable domain proof.

    A node states a domain fact and records how that fact was established: an input
    restates a core member, a derived node applies one rule to earlier nodes, and
    the contradiction closes the chain.  The premises are ids of earlier nodes
    rather than nested objects, so a shared fact is one node however many steps use
    it.

    :param stable_id: Identifier unique within the proof.
    :type stable_id: str
    :param kind: What this node contributes.
    :type kind: BmcProofNodeKind
    :param rule_id: The domain rule this step applies.
    :type rule_id: BmcProofRuleId
    :param premise_ids: Ids of the earlier nodes this step reads.
    :type premise_ids: Tuple[str, ...]
    :param conclusion: The structured fact this step establishes.
    :type conclusion: Mapping[str, object]
    :param item_ids: Core members this step ultimately rests on.
    :type item_ids: Tuple[str, ...]
    :param human_text: The domain sentence for this step.
    :type human_text: str
    :param verification_method: How the step was checked.
    :type verification_method: BmcProofVerificationMethod
    :param unit_index: Which requirement of the member's group this input restates,
        counting from zero in the group's own decomposition order.  Only a
        ``core_binding_unit`` input carries it, defaults to ``None``.
    :type unit_index: Optional[int], optional
    :param unit_count: How many requirements that decomposition has, so a reader
        can see what proportion of the group this one fact covers.  Only a
        ``core_binding_unit`` input carries it, defaults to ``None``.
    :type unit_count: Optional[int], optional
    :raises ValueError: If a vocabulary value is unknown, a published text is
        blank, a sequence repeats an id, or the two unit fields disagree with the
        verification method or with each other.

    Example::

        >>> node = BmcProofNode(
        ...     "proof.input.0000", "input", "source_fact", (),
        ...     {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0},
        ...     ("assumption.0000.frame.0000",),
        ...     "The query requires x to equal 0 initially.", "core_binding",
        ... )
        >>> node.to_canonical()["rule_id"]
        'source_fact'
    """

    stable_id: str
    kind: BmcProofNodeKind
    rule_id: BmcProofRuleId
    premise_ids: Tuple[str, ...]
    conclusion: Mapping[str, Any]
    item_ids: Tuple[str, ...]
    human_text: str
    verification_method: BmcProofVerificationMethod
    unit_index: Optional[int] = None
    unit_count: Optional[int] = None

    def __post_init__(self) -> None:
        # Copied before the invariants read them, so a caller's list cannot be
        # mutated afterwards into a shape the checks already passed.
        object.__setattr__(self, "premise_ids", tuple(self.premise_ids))
        object.__setattr__(self, "item_ids", tuple(self.item_ids))
        require_published_text(self.stable_id, "proof node stable_id")
        require_published_text(self.human_text, "proof node human_text")
        _require_member(self.kind, _PROOF_NODE_KINDS, "proof node kind")
        _require_member(self.rule_id, _PROOF_RULE_IDS, "proof node rule_id")
        _require_member(
            self.verification_method,
            _PROOF_VERIFICATION_METHODS,
            "proof node verification_method",
        )
        # One predicate, both directions.  A binding is what an input's re-encoding
        # was checked by; the rule checker and the solver discharge derived and root
        # steps.  Either pairing reversed describes a check that cannot have happened
        # -- a contradiction has no core member to re-encode against, an input has no
        # premises to re-derive from -- and the reference states the split outright,
        # so the constructor is where a caller assembling a proof to publish learns
        # it rather than a consumer reading the result.
        if (self.verification_method in _INPUT_VERIFICATION_METHODS) != (
            self.kind == "input"
        ):
            raise ValueError(
                "proof node verification_method %r does not belong to a %s node."
                % (self.verification_method, self.kind)
            )
        # The two unit fields and the method that admits them travel together in
        # both directions.  Either alone says something a reader cannot use: an
        # index without a count gives no proportion, a count without an index names
        # no requirement, and either on a whole-group binding claims a decomposition
        # that binding never made.
        unit_fields = (self.unit_index, self.unit_count)
        if self.verification_method == "core_binding_unit":
            if any(value is None for value in unit_fields):
                raise ValueError(
                    "a core_binding_unit proof node must carry unit_index and "
                    "unit_count."
                )
            index = exact_int(self.unit_index, "proof node unit_index")
            count = exact_int(self.unit_count, "proof node unit_count")
            if count < 1:
                raise ValueError("proof node unit_count must be at least 1.")
            if not 0 <= index < count:
                raise ValueError("proof node unit_index must be within its unit_count.")
        elif any(value is not None for value in unit_fields):
            raise ValueError(
                "only a core_binding_unit proof node may carry unit_index or "
                "unit_count."
            )
        for name, ids in (
            ("premise_ids", self.premise_ids),
            ("item_ids", self.item_ids),
        ):
            for value in ids:
                require_published_text(value, "proof node %s entry" % name)
            if len(set(ids)) != len(ids):
                raise ValueError("proof node %s must not repeat an id." % name)
        conclusion = _require_json_mapping(self.conclusion, "proof node conclusion")
        if (
            not isinstance(conclusion.get("kind"), str)
            or not conclusion["kind"].strip()
        ):
            # A conclusion without a tag cannot be dispatched on, and the root is
            # recognized by its tag being ``false``.
            raise ValueError("proof node conclusion must carry a kind.")
        if "state_slot" in conclusion and conclusion["state_slot"] is not True:
            # The published schema pins this to ``true``, and ``1 == True`` in
            # Python, so a node built directly could carry a value the schema
            # refuses.  A field this small decides whether a conclusion is read as a
            # state or as a variable, so the two gates answer it the same way.
            raise ValueError(
                "proof node conclusion state_slot must be true when present."
            )
        object.__setattr__(self, "conclusion", MappingProxyType(conclusion))

    def to_canonical(self) -> Dict[str, Any]:
        """Return the published mapping for this node.

        :return: Canonical node dictionary in field order.
        :rtype: Dict[str, object]

        Example::

            >>> node = BmcProofNode(
            ...     "proof.false", "contradiction", "incompatible_equalities",
            ...     ("proof.input.0000",), {"kind": "false"},
            ...     ("assumption.0000.frame.0000",),
            ...     "The initial value of x cannot be both 0 and 1.", "rule_checker",
            ... )
            >>> node.to_canonical()["conclusion"]
            {'kind': 'false'}
        """
        mapping = {
            "stable_id": self.stable_id,
            "kind": self.kind,
            "rule_id": self.rule_id,
            "premise_ids": list(self.premise_ids),
            "conclusion": json_canonical(self.conclusion),
            "item_ids": list(self.item_ids),
            "human_text": self.human_text,
            "verification_method": self.verification_method,
        }
        if self.verification_method == "core_binding_unit":
            # Present only where the method admits them, matching the constructor's
            # own rule in both directions.  Emitting nulls on a whole-group binding
            # would put two keys in front of every reader that mean nothing there,
            # and the published schema lists them as optional for the same reason.
            mapping["unit_index"] = exact_int(self.unit_index, "proof node unit_index")
            mapping["unit_count"] = exact_int(self.unit_count, "proof node unit_count")
        return mapping


@dataclass(frozen=True)
class BmcConflictProof:
    """The verifiable domain proof that a scope admits no execution.

    Every node is checked, and the graph is held to the shape a reader can follow:
    ``nodes`` is itself the canonical topological order, premises look backwards
    only, exactly one node concludes ``false``, and every node reaches that root.
    The last of those is why a step cannot ride along unused -- publishing it would
    claim it took part in the conclusion.

    None of these are expressible in the published Draft 2020-12 schema: they are
    relations between array members and reachability over a graph, so the schema
    accepts a payload whose ``premise_ids`` name nothing and this constructor
    refuses it.  The contract names that split as a semantic-gate exception.

    :param scope: Diagnostic scope the proof discharges.
    :type scope: BmcConflictCoreScope
    :param root_id: Id of the single node concluding ``false``.
    :type root_id: str
    :param nodes: Every node, in canonical topological order.
    :type nodes: Tuple[BmcProofNode, ...]
    :param input_minimality: How minimal the input leaves are.
    :type input_minimality: BmcProofInputMinimality
    :param graph_minimality: How pruned the graph is.
    :type graph_minimality: BmcProofGraphMinimality
    :param verification_status: How far verification got.
    :type verification_status: BmcProofVerificationStatus
    :raises ValueError: If a vocabulary value is unknown, the graph is empty, an id
        repeats, a premise names no earlier node, the root is not the single
        ``false`` node, or a node cannot reach the root.

    Example::

        >>> fact = BmcProofNode(
        ...     "proof.input.0000", "input", "source_fact", (),
        ...     {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0},
        ...     ("assumption.0000.frame.0000",), "x starts at 0.", "core_binding",
        ... )
        >>> closing = BmcProofNode(
        ...     "proof.false", "contradiction", "incompatible_equalities",
        ...     ("proof.input.0000",), {"kind": "false"},
        ...     ("assumption.0000.frame.0000",), "x cannot be 0 and 1.", "rule_checker",
        ... )
        >>> proof = BmcConflictProof(
        ...     "assumptions_component", "proof.false", (fact, closing),
        ...     "subset_minimal", "dependency_pruned", "verified",
        ... )
        >>> proof.to_canonical()["verification_status"]
        'verified'
    """

    scope: BmcConflictCoreScope
    root_id: str
    nodes: Tuple[BmcProofNode, ...]
    input_minimality: BmcProofInputMinimality
    graph_minimality: BmcProofGraphMinimality
    verification_status: BmcProofVerificationStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        require_published_text(self.root_id, "proof root_id")
        # The core's scope vocabulary, not the classification's: the contract types
        # this field as ``BmcConflictCoreScope`` and requires the proof's scope to
        # equal the core's, and the two vocabularies are different -- a fallback
        # scope exists for cores and has no classification.
        _require_member(self.scope, _SCOPES, "proof scope")
        _require_member(
            self.input_minimality,
            _PROOF_INPUT_MINIMALITIES,
            "proof input_minimality",
        )
        _require_member(
            self.graph_minimality,
            _PROOF_GRAPH_MINIMALITIES,
            "proof graph_minimality",
        )
        _require_member(
            self.verification_status,
            _PROOF_VERIFICATION_STATUSES,
            "proof verification_status",
        )
        if not self.nodes:
            # An empty graph establishes nothing, and its root names a node that is
            # not there -- the two failures are the same one.
            raise ValueError("a published proof must carry at least one node.")
        seen = set()
        for node in self.nodes:
            if node.stable_id in seen:
                raise ValueError(
                    "proof nodes contain duplicate stable id %r." % node.stable_id
                )
            for premise in node.premise_ids:
                if premise not in seen:
                    # Covers both directions at once: an id defined later, and an id
                    # that names no node at all.  ``nodes`` being the canonical
                    # order is what lets one check settle both.
                    raise ValueError(
                        "proof node %r cites premise %r, which is not an earlier "
                        "node." % (node.stable_id, premise)
                    )
            seen.add(node.stable_id)
        roots = [
            node
            for node in self.nodes
            if node.conclusion.get("kind") == _PROOF_FALSE_CONCLUSION_KIND
        ]
        if len(roots) != 1:
            raise ValueError(
                "a published proof must conclude on exactly one false node, got %d."
                % len(roots)
            )
        if roots[0].stable_id != self.root_id:
            raise ValueError(
                "proof root_id %r does not name the false node %r."
                % (self.root_id, roots[0].stable_id)
            )
        # Walk the premise edges backwards from the root: whatever the conclusion
        # rests on is reachable, and anything left over is a step the proof does not
        # use.  Publishing one would name it among the reasons.
        by_id = {node.stable_id: node for node in self.nodes}
        used, pending = set(), [self.root_id]
        while pending:
            current = pending.pop()
            if current in used:
                continue
            used.add(current)
            pending.extend(by_id[current].premise_ids)
        unused = sorted(set(by_id) - used)
        if unused:
            raise ValueError(
                "proof nodes %s do not reach the root; a pruned graph carries no "
                "unused step." % ", ".join(repr(name) for name in unused)
            )

    def to_canonical(self) -> Dict[str, Any]:
        """Return the published mapping for this proof.

        The nodes are nested rather than referenced, so one payload carries the
        whole graph in the order a reader follows it.

        :return: Canonical proof dictionary in field order.
        :rtype: Dict[str, object]

        Example::

            >>> node = BmcProofNode(
            ...     "proof.false", "contradiction", "definedness_failure", (),
            ...     {"kind": "false"}, ("assumption.0000.frame.0000",),
            ...     "The division cannot stay defined.", "rule_checker",
            ... )
            >>> proof = BmcConflictProof(
            ...     "assumptions_component", "proof.false", (node,),
            ...     "subset_minimal", "dependency_pruned", "verified",
            ... )
            >>> proof.to_canonical()["input_minimality"]
            'subset_minimal'
        """
        return {
            "scope": self.scope,
            "root_id": self.root_id,
            "nodes": [node.to_canonical() for node in self.nodes],
            "input_minimality": self.input_minimality,
            "graph_minimality": self.graph_minimality,
            "verification_status": self.verification_status,
        }


@dataclass(frozen=True)
class BmcInfeasibilityExplanation:
    """Frozen public container for one scenario infeasibility explanation.

    The field list is frozen once and never reshaped by later stages; they
    only populate slots that this stage leaves empty.  ``achieved_mode``
    reports what was actually delivered, which can be weaker than
    ``requested_mode`` whenever a probe or extraction step degrades.

    :param requested_mode: Explanation depth the caller asked for.
    :type requested_mode: BmcInfeasibilityExplanationMode
    :param achieved_mode: Explanation depth actually delivered.
    :type achieved_mode: BmcInfeasibilityExplanationMode
    :param status: Completeness of the delivered artifact.
    :type status: BmcInfeasibilityExplanationStatus
    :param classification: Structured infeasibility classification, or ``None``
        when only a stage fallback is honest.
    :type classification: Optional[BmcInfeasibilityClassification]
    :param core: Sound source core, defaults to ``None``.
    :type core: Optional[BmcConflictCore], optional
    :param proof: The verified proof, present exactly when ``achieved_mode`` is ``"proof"``.
    :type proof: Optional[BmcConflictProof], optional
    :param narrative: Deterministic account of why no execution exists, or
        ``None`` when no core was published; defaults to ``None``.
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
        else:
            # The ninth published text field, and the one my own wording excluded
            # by counting eight.  A degraded artifact's reason is what the human
            # report prints on its ``Reason:`` line, so whitespace here is the same
            # defect as anywhere else and goes through the same predicate.
            if self.reason is None:
                raise ValueError(
                    "%s explanations require a non-empty reason." % self.status
                )
            require_published_text(self.reason, "%s explanation reason" % self.status)
        if self.elapsed_ms is not None:
            if isinstance(self.elapsed_ms, bool) or not isinstance(
                self.elapsed_ms, (int, float)
            ):
                raise TypeError("explanation elapsed_ms must be a number or None.")
            # The comparisons below would otherwise be answered by the value's
            # own __lt__ and __float__, so a negative duration could report
            # itself as non-negative and be published as recorded.
            try:
                if isinstance(self.elapsed_ms, float):
                    plain = exact_float(self.elapsed_ms, "explanation elapsed_ms")
                else:
                    whole = exact_int(self.elapsed_ms, "explanation elapsed_ms")
                    try:
                        plain = float(whole)
                    except OverflowError:
                        # An integer past the float range is a legal JSON number
                        # the schema accepts, so refusing it has to say so in the
                        # same terms as every other bound here rather than
                        # escaping as OverflowError.
                        raise ValueError(
                            "explanation elapsed_ms is too large to represent as "
                            "a duration, got %r." % self.elapsed_ms
                        ) from None
            except TypeError:
                # exact_* raise for a value that is not a real number.
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
            # A complete explanation needs a narrative whose derivation closed.
            # Present-but-degraded is the case worth naming: a structural_only
            # account says outright that it could not derive the conflict, so
            # publishing full confidence over it is the overclaim the frozen row
            # exists to prevent.
            if self.narrative is None:
                raise ValueError("a complete explanation requires a narrative.")
            if self.narrative.derivation_status != "complete":
                raise ValueError(
                    "a complete explanation requires a complete narrative, got "
                    "derivation_status %r." % self.narrative.derivation_status
                )
        if self.narrative is not None and self.proof is None:
            # Steps bind to proof nodes only in proof mode; with no proof there
            # are no nodes, so a citation points at something no artifact
            # contains.  The step class documents the field as empty outside
            # proof mode and this is what holds it to that.
            cited = [
                step for step in self.narrative.reasoning_steps if step.proof_node_ids
            ]
            if cited:
                raise ValueError(
                    "a reasoning step cites proof nodes, but no proof was published."
                )
        if self.narrative is not None and self.core is None:
            # A narrative describes a core, and with none published its ids point
            # at nothing by construction -- the reference check below cannot even
            # run.  The frozen not-achieved transcript says the same: no conflict
            # core, no causal chain.
            raise ValueError(
                "a narrative requires the core it describes; none was published."
            )
        if self.narrative is not None and self.core is not None:
            # These two are separate published arrays, so neither class can check
            # the relation alone: the narrative cannot see the core it describes.
            # This is the object that holds both, which is where the ids a reader
            # will follow have to be shown to exist.
            members = {item.constraint.stable_id: item for item in self.core.items}
            for step in self.narrative.reasoning_steps:
                unknown = [name for name in step.item_ids if name not in members]
                if unknown:
                    raise ValueError(
                        "reasoning step cites %r, which is not a member of the "
                        "published core." % unknown[0]
                    )
            for name in self.narrative.review_surfaces:
                item = members.get(name)
                if item is None:
                    raise ValueError(
                        "review surface %r is not a member of the published core."
                        % name
                    )
                if not item.editable:
                    # A generated rule has no authored line, so offering it for
                    # review sends the reader looking for a file that does not
                    # exist.
                    raise ValueError(
                        "review surface %r is not editable; only authored "
                        "members are offered for review." % name
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
            # Both are published now, so both are serialized; emitting either
            # directly would put a repr in the payload.
            "proof": (None if self.proof is None else self.proof.to_canonical()),
            "narrative": (
                None if self.narrative is None else self.narrative.to_canonical()
            ),
            "reason": self.reason,
            "elapsed_ms": self.elapsed_ms,
        }


__all__ = [
    # Published with ``autofunction`` in the API reference, so exported here too.
    "category_role",
    "constraint_aggregate",
    "depth_line_is_needed",
    "build_conflict_narrative",
    "explanation_text_lines",
    "require_published_text",
    "human_text_for_fact",
    "index_value",
    "is_printable_ascii",
    "BmcConflictCore",
    "BmcConflictCoreScope",
    "BmcConflictNarrative",
    "BmcReasoningStep",
    "BmcConflictProof",
    "BmcProofNode",
    "BmcProofNodeKind",
    "BmcProofRuleId",
    "BmcProofVerificationMethod",
    "BmcProofInputMinimality",
    "BmcProofGraphMinimality",
    "BmcProofVerificationStatus",
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


#: Headline for each achieved depth and status, keyed by ``(mode, status)``.
#: A depth that was requested but not achieved has no entry: it is named by
#: the requested mode instead, so the reader is told what they asked for
#: rather than being shown a headline for a result that does not exist.
#:
#: The module-private ``_ALL_EXPLANATION_HEADLINES`` holds both families in one
#: mapping for the renderer and for anything that has to enumerate every headline
#: a user can see.  This one stays as documented above: it is rendered by
#: ``autodata`` on the API reference page, so its keys and values are published.
EXPLANATION_HEADLINES = MappingProxyType(
    {
        ("formal", "partial"): "PARTIAL FORMAL DOMAIN EXPLANATION",
        ("formal", "complete"): "COMPLETE FORMAL DOMAIN EXPLANATION",
        ("proof", "partial"): "PARTIAL VERIFIED DOMAIN PROOF",
        ("proof", "complete"): "COMPLETE VERIFIED DOMAIN PROOF",
    }
)

#: Every headline the explanation block can open with, achieved or not.
#:
#: Keyed by the pair that decides it.  When a depth was achieved that is
#: ``(achieved_mode, status)`` and the entry is the one
#: :data:`EXPLANATION_HEADLINES` publishes.  When nothing was achieved there is
#: no achieved depth to name, so the key is ``("none", requested_mode)`` and the
#: headline names what was asked for.
#:
#: The second family used to be a fallback branch in the renderer, so nothing
#: enumerated all six in one place and both the reference page and its checker
#: were written from the four-entry mapping.  Reading this one instead is what
#: keeps them honest.  It stays private because the published mapping documents
#: itself as covering achieved depths only, and widening that in place would
#: change a value the API reference renders.
_ALL_EXPLANATION_HEADLINES = MappingProxyType(
    {
        **EXPLANATION_HEADLINES,
        ("none", "formal"): "FORMAL EXPLANATION NOT ACHIEVED",
        ("none", "proof"): "PROOF EXPLANATION NOT ACHIEVED",
    }
)

#: How the ``Proof strength`` block words each published strength value.
#:
#: Transcribed from the contract's §12.1 transcript rather than derived from the
#: enum spellings, because the block is frozen text: ``subset_minimal`` prints as
#: "subset-minimal" and ``verified`` as a whole clause, neither of which a
#: mechanical transformation of the value would produce.  A value added to one of
#: the enums without a phrase here raises instead of printing a label nobody wrote.
_PROOF_STRENGTH_PHRASES = MappingProxyType(
    {
        "input": MappingProxyType({"subset_minimal": "subset-minimal"}),
        "graph": MappingProxyType({"dependency_pruned": "dependency-pruned"}),
        "verification": MappingProxyType(
            {"verified": "checked against the encoded model semantics"}
        ),
    }
)

#: Each classification in the words a reader can act on.
CLASSIFICATION_PHRASES = MappingProxyType(
    {
        "kernel_conflict": "the model's own domain and transition rules conflict",
        "initialization_self_conflict": "initialization is internally inconsistent",
        "initialization_domain_conflict": (
            "initialization conflicts with the frame domain"
        ),
        "initialization_kernel_conflict": (
            "initialization conflicts with the transition relation"
        ),
        "assumptions_self_conflict": "the assumptions are internally inconsistent",
        "assumptions_domain_conflict": "the assumptions conflict with the frame domain",
        "assumptions_prefix_conflict": (
            "assumptions conflict with the feasible prefix"
        ),
    }
)


def _item_location(item) -> str:
    """Render one core member's source position for human output.

    The same string serves the conflict list and the review surfaces, so both
    name a member the same way: a reader comparing the two blocks is looking at
    one entry, not two spellings of it.

    :param item: The published core member.
    :type item: BmcCoreItem
    :return: A path with span when available, or an honest substitute.
    :rtype: str

    Example::

        >>> reference = BmcConstraintRef(
        ...     "g0", "assumptions", "assumption.frame",
        ...     BmcSourceRef("generated", None, None), "s",
        ... )
        >>> item = BmcCoreItem(
        ...     reference, "assumption", None, False,
        ...     {"kind": "structural_constraint"}, "t", False,
        ... )
        >>> _item_location(item)
        'generated assumption constraint'
    """
    source = item.constraint.source
    span = source.span
    if source.path is not None and span is not None:
        location = "%s:%d:%d" % (source.path, span.line, span.column)
        if span.end_line is not None and span.end_column is not None:
            location += "-%d:%d" % (span.end_line, span.end_column)
        return location
    if source.path is not None:
        return source.path
    if source.kind == "generated":
        return "generated %s constraint" % _category_noun(item.constraint)
    # An authored constraint whose origin was never named -- a programmatic
    # query, for instance -- still came from the user's own text.  Calling it
    # generated would attribute their constraint to the encoder, which the frozen
    # contract forbids.
    return "%s %s constraint (source location unavailable)" % (
        source.kind,
        _category_noun(item.constraint),
    )


def _core_position(constraint: BmcConstraintRef) -> str:
    """Return the frame or step position a core member constrains.

    Called only for a generated group.  A generated group is part of the proof
    that no execution exists, so its position may not be hidden for tidiness; it
    is printed inline after the location, which is where the published transcript
    puts it, so a reader can tell which macro-step the constraint belongs to.  An
    authored group's own text already states its position -- ``assume at 1: ...``
    -- so it is not routed through here.

    :param constraint: Published constraint reference of one core member.
    :type constraint: pyfcstm.bmc.explanation.BmcConstraintRef
    :return: Text such as ``at step 0``, or ``""`` when the member constrains no
        particular position.
    :rtype: str

    Example::

        >>> class _Ref:
        ...     frames = ()
        ...     steps = (0,)
        >>> _core_position(_Ref())
        'at step 0'
    """
    parts = []
    if constraint.frames:
        label = "frame" if len(constraint.frames) == 1 else "frames"
        parts.append("%s %s" % (label, ", ".join(str(f) for f in constraint.frames)))
    if constraint.steps:
        label = "step" if len(constraint.steps) == 1 else "steps"
        parts.append("%s %s" % (label, ", ".join(str(s) for s in constraint.steps)))
    if not parts:
        return ""
    return "at %s" % " and ".join(parts)


def _core_structural_refs(constraint: BmcConstraintRef) -> str:
    """Return the builder metadata a machine reader is told to consume.

    Called only for a generated group.  Such a group has no source text of its
    own, so its position and its remaining refs are shown rather than hidden for
    tidiness: the position goes on the group's own line, and this function
    supplies the indented line that follows when there is anything left.
    ``frame`` and ``step`` are already on that line, so only the other keys are
    added here.  An authored group is not routed through
    this function -- its own text states its position, and its refs remain a
    machine contract carried by the JSON.

    :param constraint: Published constraint reference of one core member.
    :type constraint: pyfcstm.bmc.explanation.BmcConstraintRef
    :return: Text such as ``assumption 0, kind state``, or ``""`` when the member
        records no other metadata.
    :rtype: str

    Example::

        >>> class _Ref:
        ...     refs = {"step": 0, "kind": "state"}
        >>> _core_structural_refs(_Ref())
        'kind state'
    """
    positional = {"frame", "frames", "step", "steps"}
    rendered = [
        "%s %s" % (key, constraint.refs[key])
        for key in sorted(constraint.refs)
        if key not in positional
    ]
    if not rendered:
        return ""
    return ", ".join(rendered)


def _category_noun(constraint: BmcConstraintRef) -> str:
    """Return the reader-facing noun for one tracked group's category.

    A group is named by the leading segment of its category followed by the word
    "constraint" -- "generated transition constraint" -- never by the internal
    dotted form.

    The leading segment is used rather than the aggregate formula the group
    belongs to because the aggregate vocabulary is too small to name every group.
    It offers four words -- domain, transition, initial and environment -- while
    the groups the builder emits need five nouns, and two of those are not
    aggregate names at all.  An assumption group's aggregate is ``environment``, a
    word that appears nowhere else a reader can see.  A definedness group's
    aggregate is ``initial`` when it comes from initialization and ``environment``
    when it comes from an assumption, so the aggregate names neither the group nor
    anything stable across the two places it is emitted from.  The specification
    also names these groups by their category segments in its own prose, calling
    them generated domain/transition support groups.

    Two earlier versions of this docstring argued from a stage and category
    pairing the relation builder never produces -- first that a transition group
    could arrive through the assumptions stage, then that a definedness group
    could arrive through the kernel one.  Neither happens: a transition group's
    stage is always the kernel one, and definedness groups are emitted only from
    initialization and assumptions.  Both claims came from resolving an aggregate
    for an input rather than checking which inputs occur.

    Both the generated and the location-less authored branch read the noun from
    here.  They print different sentences, but they must agree on what the group
    is called: cleaning only one of them would leave the dotted category leaking
    on the other.

    :param constraint: Published constraint reference of one core member.
    :type constraint: pyfcstm.bmc.explanation.BmcConstraintRef
    :return: Reader-facing noun such as ``transition`` or ``assumption``.
    :rtype: str

    Example::

        >>> class _Ref:
        ...     category = "transition.step"
        >>> _category_noun(_Ref())
        'transition'

    The noun comes from the same family prefixes :data:`CATEGORY_ROLES` is keyed
    on rather than from a split of its own, so the naming table and the role table
    cannot disagree about where a category's family name ends.
    """
    for prefix in sorted(CATEGORY_ROLES, key=len, reverse=True):
        if constraint.category.startswith(prefix):
            return prefix.rstrip(".")
    # Unreachable through any public path, and kept as stated defensive code: the
    # constructor already ran category_role over the same CATEGORY_ROLES keys with
    # the same prefix test, so a category that got this far matched one of them.
    # It fires only if a later change gives the two lookups different families.
    raise ValueError(
        "category %r matches no known family prefix; the naming table and the "
        "role table must list the same families." % constraint.category
    )


def depth_line_is_needed(requested_mode: str, achieved_mode: str) -> bool:
    """Return whether both explanation depths have to be stated separately.

    A reader needs the depth they asked for and the depth they got.  The headline
    already names one of them: the achieved depth when something was achieved,
    and the requested depth in the "not achieved" shape.  It is therefore
    ambiguous only when a deeper request settled for a shallower result, and only
    then is a separate line added.

    It is a named predicate rather than an inline condition because the built-in
    report and the command line must not diverge on when the line appears, and
    because a caller rendering their own report needs the same answer this one
    uses rather than having to re-derive it from the two mode fields.

    :param requested_mode: Depth the caller asked for.
    :type requested_mode: str
    :param achieved_mode: Depth actually reached, or ``"none"``.
    :type achieved_mode: str
    :return: ``True`` when the depths must be stated on their own line.
    :rtype: bool

    Example::

        >>> depth_line_is_needed("proof", "formal")
        True
        >>> depth_line_is_needed("proof", "proof")
        False
        >>> depth_line_is_needed("formal", "none")
        False
    """
    return achieved_mode != "none" and requested_mode != achieved_mode


#: The keys each fact tag implies, so a consumer can require them before reading.
#:
#: The published schema requires only ``kind``, so a tag arriving without its
#: companions is valid output that every reader has to survive.  Filtering members
#: on this table at selection time is what lets the code below index directly:
#: adding a tag here is what makes its keys required, rather than each reader
#: remembering to guard.
_FACT_REQUIRED_KEYS = {
    "structural_constraint": (),
    "variable_comparison": ("variable", "frame", "operator", "value"),
    "state_membership": ("frame", "state"),
    "state_domain": ("frame", "states"),
    "definedness_condition": ("frame", "operation"),
    # ``operand`` and ``operand_variable`` are deliberately absent: exactly one of
    # them is present, decided by whether the model wrote a literal or a variable
    # on the right of the assignment.  Requiring either would make the other shape
    # unpublishable, and requiring neither is what lets a reader dispatch on which
    # one arrived.
    "transition_case": ("variable", "frame", "target_frame", "operation", "condition"),
    # No ``frame``: a proposition's step is inside its identity, because the rule
    # that closes over a proposition and its complement compares subjects and
    # nothing else.  Publishing the step separately as well would give a reader two
    # places to look for the same thing.
    "proposition": ("identity", "holds"),
}


def _readable(item, kind: str) -> bool:
    """Report whether one member's fact carries every key its tag implies.

    A member always holds a non-empty fact naming a known tag -- :class:`BmcCoreItem`
    refuses anything else -- so this reads the field directly and asks only the two
    questions the caller cannot answer for itself: is this the tag I mean, and can I
    index what that tag promises.

    :param item: The published core member.
    :type item: BmcCoreItem
    :param kind: The tag the caller intends to read.
    :type kind: str
    :return: ``True`` when the fact is that tag and complete enough to index.
    :rtype: bool

    Example::

        >>> reference = BmcConstraintRef(
        ...     "assumption.x.0", "assumptions", "assumption.frame",
        ...     BmcSourceRef("generated", None, None), "bound",
        ... )
        >>> partial = BmcCoreItem(
        ...     reference, "assumption", None, False,
        ...     {"kind": "state_membership", "frame": 0, "state": 1}, "bound", False,
        ... )
        >>> _readable(partial, "state_membership")
        True
        >>> _readable(partial, "variable_comparison")
        False
    """
    fact = item.normalized_fact
    if fact.get("kind") != kind:
        return False
    return all(key in fact for key in _FACT_REQUIRED_KEYS.get(kind, ()))


def _members(items, kind: str, **axes) -> List["BmcCoreItem"]:
    """Return the members carrying ``kind`` whole and agreeing with every axis.

    An axis names a fact key and what it must hold: ``frame=1`` picks one frame, and
    a set picks any of several, so ``state=legal`` keeps the exclusions a domain
    reading can consume.  There is deliberately no negated axis.  A key the tag does
    not require may be absent, and absence equals no expected value, so an
    incomplete fact can never satisfy an axis by omitting it -- the way a ``!=``
    comparison would let it.

    :param items: The published core members to select from.
    :type items: Iterable[BmcCoreItem]
    :param kind: The tag the caller intends to read.
    :type kind: str
    :param axes: Fact keys and the value, or set of values, each must hold.
    :return: The members that qualify, in the order given.
    :rtype: List[BmcCoreItem]

    Example::

        >>> _members((), "variable_comparison", frame=0)
        []
    """
    selected = []
    for item in items:
        if not _readable(item, kind):
            continue
        fact = item.normalized_fact
        if all(
            fact.get(name) in value
            if isinstance(value, (set, frozenset))
            else fact.get(name) == value
            for name, value in axes.items()
        ):
            selected.append(item)
    return selected


def _state_members(items, excluded: bool, **axes) -> List["BmcCoreItem"]:
    """Return the state members of one polarity, on the axes given.

    ``excluded`` is optional on the fact -- a member requiring a state simply omits
    it -- so the two polarities are asked for by name rather than through an axis,
    where an absent key would match neither value.

    :param items: The published core members to select from.
    :type items: Iterable[BmcCoreItem]
    :param excluded: ``True`` for members ruling a state out, ``False`` for members
        requiring one.
    :type excluded: bool
    :param axes: Further fact keys, as in :func:`_members`.
    :return: The members that qualify, in the order given.
    :rtype: List[BmcCoreItem]

    Example::

        >>> _state_members((), True, frame=0)
        []
    """
    return [
        item
        for item in _members(items, "state_membership", **axes)
        if bool(item.normalized_fact.get("excluded")) is excluded
    ]


def _explains_every_member(participants, items) -> bool:
    """Report whether a reading may close, given the members it actually uses.

    This is the only place a pattern decides it has explained the core, and its
    first argument is the set the conclusion is built from -- not a count taken over
    a wider selection.  Keeping the two the same object is the point: a count over
    everything carrying the right tag passes while the proof consumes a subset, and
    the conflict step then names members that played no part, which is a true
    sentence resting on a false attribution.

    Comparing ids is how the question is phrased rather than a stronger check than
    comparing sizes: a core refuses duplicate ids and every caller passes members
    selected from it, so the two agree on any core that can be built.  The point of
    the set form is that it stays right without that argument.

    :param participants: The members the conclusion is derived from.
    :type participants: Iterable[BmcCoreItem]
    :param items: Every member of the published core.
    :type items: Iterable[BmcCoreItem]
    :return: ``True`` when the two name the same members.
    :rtype: bool

    Example::

        >>> _explains_every_member((), ())
        True
    """
    cited = {item.constraint.stable_id for item in participants}
    return cited == {item.constraint.stable_id for item in items}


def _conflict_pattern(
    items: Tuple["BmcCoreItem", ...],
    minimality: str = "not_proven",
    state_paths: Optional[Mapping] = None,
) -> Optional[Tuple[str, str]]:
    """Name the cross-group pattern the published facts support, if any.

    Only patterns the recognized facts actually establish are reported.  A pair
    of equalities on one variable in one frame is a contradiction outright; a
    pair of bounds is one when no value satisfies both.  Anything else returns
    ``None`` so the narrative degrades instead of guessing.

    :param items: Published core members in stable-id order.
    :type items: Tuple[BmcCoreItem, ...]
    :param minimality: The core's published ``subset_minimality``; a pattern whose
        soundness argument needs every member to be load-bearing is only offered
        when it is ``proven``, defaults to ``"not_proven"``.
    :type minimality: str, optional
    :param state_paths: State code to authored path, so a conclusion names the
        state the reader wrote rather than the encoding's number; defaults to
        ``None``.
    :type state_paths: Optional[Mapping[int, str]], optional
    :return: The rule name and its sentence, or ``None``.
    :rtype: Optional[Tuple[str, str]]

    Example::

        >>> _conflict_pattern(()) is None
        True
    """
    propositions = _members(items, "proposition")
    if len(propositions) == 2 and _explains_every_member(propositions, items):
        first, second = (item.normalized_fact for item in propositions)
        if (
            first["identity"] == second["identity"]
            and first["holds"] != second["holds"]
        ):
            # The same subject demanded and ruled out.  Naming it is the whole value:
            # "jointly unsatisfiable" would leave the reader to notice that the two
            # lines are about one event at one step, which is exactly what the
            # identity was built to make visible.
            return (
                "boolean_complement",
                "%s is required to occur and required not to occur."
                % first["identity"],
            )
    definedness = _members(items, "definedness_condition")
    if len(definedness) == 1 and len(items) > 1 and minimality == "proven":
        # One domain condition beside facts about the very variable it guards.
        # Every member of a *proven* subset-minimal core is load-bearing, so the
        # condition is part of the contradiction and the facts beside it are why
        # it fails.  The minimality is checked rather than assumed: in a raw core
        # a redundant guard can ride along, and calling it the cause would point
        # the reader at a line that is not why anything failed.
        # Requiring the core to hold *nothing but* domain conditions sent the most
        # natural way of writing this -- a divisor the initializer pins to zero --
        # to the structural fallback.
        guard = definedness[0].normalized_fact
        subject, frame = guard.get("variable"), guard["frame"]
        paired = _members(items, "variable_comparison", variable=subject, frame=frame)
        if subject is not None and _explains_every_member(definedness + paired, items):
            return (
                "definedness_failure",
                "The %s at frame %s cannot stay defined: %s is required to be a "
                "value it rules out." % (guard["operation"], frame, subject),
            )
    if definedness and _explains_every_member(definedness, items):
        # The core is the domain condition itself, and a published core is
        # unsatisfiable, so the reason no execution exists is that the operation
        # cannot be defined there.  Naming the operation is the whole value of
        # this pattern: "jointly unsatisfiable" leaves the reader to work out
        # which one was at fault.
        frames = sorted({item.normalized_fact["frame"] for item in definedness})
        operations = sorted({item.normalized_fact["operation"] for item in definedness})
        if len(frames) == 1 and len(operations) == 1:
            return (
                "definedness_failure",
                "The %s at frame %s cannot stay defined." % (operations[0], frames[0]),
            )
        return (
            "definedness_failure",
            "No execution keeps every operation defined at %s."
            % ", ".join("frame %s" % frame for frame in frames),
        )
    domains = _members(items, "state_domain")
    if len(domains) == 1:
        legal = domains[0].normalized_fact
        legal_states = set(legal["states"])
        # The conclusion is quantified over the frame's *legal* states, so those are
        # the axes: an exclusion elsewhere, or naming a state this frame does not
        # list, takes no part in it.  Both can sit in a core -- a frame's domain is
        # not the same at every frame, since entry admits states a recurrence step
        # does not, so ruling out a composite at frame 1 is an ordinary authored line
        # landing outside frame 1's domain.
        exclusions = _state_members(
            items, True, frame=legal["frame"], state=legal_states
        )
        removed = {item.normalized_fact["state"] for item in exclusions}
        if (
            exclusions
            and _explains_every_member(domains + exclusions, items)
            and legal_states <= removed
        ):
            # Every state the frame may hold has been ruled out, so the frame has
            # nothing left to be.  Checked against the published domain rather
            # than inferred from how many exclusions happen to be present.
            return (
                "state_domain_exhaustion",
                "Frame %s has no state left: every one of its %d legal states is "
                "ruled out." % (legal["frame"], len(legal["states"])),
            )
    states = _state_members(items, False)
    if states and _explains_every_member(states, items):
        frames = {item.normalized_fact["frame"] for item in states}
        required = sorted({item.normalized_fact["state"] for item in states})
        if len(frames) == 1 and len(required) > 1:
            # One frame holds exactly one state, so two different requirements on
            # it cannot both hold.  This is the same shape as incompatible
            # equalities, over the state slot instead of a variable.
            return (
                "incompatible_equalities",
                "Frame %s cannot be in two states at once; %s are each "
                "required."
                % (
                    sorted(frames)[0],
                    " and ".join(_state_label(code, state_paths) for code in required),
                ),
            )
    comparisons = _members(items, "variable_comparison")
    if len(comparisons) < 2 or not _explains_every_member(comparisons, items):
        # A pattern over a subset would leave the remaining members unexplained
        # while the narrative claimed a closed chain.
        return None
    frames = {item.normalized_fact["frame"] for item in comparisons}
    variables = {item.normalized_fact["variable"] for item in comparisons}
    if len(frames) != 1 or len(variables) != 1:
        return None
    frame = comparisons[0].normalized_fact["frame"]
    variable = comparisons[0].normalized_fact["variable"]
    equalities = sorted(
        item.normalized_fact["value"]
        for item in comparisons
        if item.normalized_fact["operator"] == "eq"
    )
    if len(equalities) == len(comparisons) and len(set(equalities)) > 1:
        return (
            "incompatible_equalities",
            "Frame %s cannot assign %s to %s at the same time."
            % (frame, " and ".join(str(value) for value in equalities), variable),
        )
    # Only the members the reading uses count as explained; a skipped ``ne`` would
    # otherwise be listed in the conflict step without bearing on it.
    if _explains_every_member(
        _bounds_participants(comparisons), items
    ) and _interval_is_empty(comparisons):
        return (
            "interval_intersection",
            "No value of %s satisfies every bound required at frame %s."
            % (variable, frame),
        )
    return None


def _interval_is_empty(items: Tuple["BmcCoreItem", ...]) -> bool:
    """Report whether published bounds on one variable admit no value.

    The domain matters.  Over the integers ``x > 0`` and ``x < 1`` admit nothing,
    while over the reals they admit every value between them, so the integer
    tightening is applied only when every published value is an ``int`` -- which
    is exactly how the recognizer distinguishes the two sorts.  Strict bounds on
    a real domain are handled by tracking whether each limit is inclusive, so an
    interval is empty when the limits cross or when they meet at a point neither
    side includes.

    Inequality (``ne``) is deliberately ignored: excluding a single value never
    empties a range on its own, and treating it as a bound would claim a conflict
    the constraints do not have.

    :param items: Published comparison members on one variable and frame.
    :type items: Tuple[BmcCoreItem, ...]
    :return: ``True`` when no value of the variable satisfies every bound.
    :rtype: bool

    Example::

        >>> _interval_is_empty(())
        False
    """
    integral = all(isinstance(item.normalized_fact["value"], int) for item in items)
    lower = upper = None
    lower_open = upper_open = False
    for item in items:
        fact = item.normalized_fact
        operator, value = fact["operator"], fact["value"]
        if operator == "eq":
            bounds = ((value, False), (value, False))
        elif operator == "ge":
            bounds = ((value, False), None)
        elif operator == "gt":
            bounds = ((value + 1, False) if integral else (value, True), None)
        elif operator == "le":
            bounds = (None, (value, False))
        elif operator == "lt":
            bounds = (None, (value - 1, False) if integral else (value, True))
        else:
            continue
        low, high = bounds
        if low is not None and (
            lower is None or low[0] > lower or (low[0] == lower and low[1])
        ):
            lower, lower_open = low[0], low[1] or (low[0] == lower and lower_open)
        if high is not None and (
            upper is None or high[0] < upper or (high[0] == upper and high[1])
        ):
            upper, upper_open = high[0], high[1] or (high[0] == upper and upper_open)
    if lower is None or upper is None:
        return False
    if lower > upper:
        return True
    # The limits meet.  A single point survives only when both sides include it.
    return lower == upper and (lower_open or upper_open)


def _bounds_participants(items: Tuple["BmcCoreItem", ...]) -> Tuple:
    """Return the members whose operator the interval reading actually uses.

    ``ne`` is skipped when the limits are computed -- excluding one value never
    empties a range -- so a core carrying one passes the sibling coverage count
    while contributing nothing to the conclusion.  Counting participants instead
    of members keeps "every member is explained" true rather than merely counted.

    The operator is read directly because the only caller has already reduced its
    members to readable comparison facts and refuses the pattern unless *every*
    member survived that filter.  Repeating the check here would be dead code: an
    unreducible fact cannot reach this function.

    :param items: Published comparison members on one variable and frame, each
        already carrying every key its tag implies.
    :type items: Tuple[BmcCoreItem, ...]
    :return: The subset the limits are derived from.
    :rtype: Tuple[BmcCoreItem, ...]

    Example::

        >>> _bounds_participants(())
        ()
    """
    return tuple(
        item
        for item in items
        if item.normalized_fact["operator"] in ("eq", "ge", "gt", "le", "lt")
    )


def _propagation_steps(core: "BmcConflictCore", forced_values: Tuple):
    """Build the chain for a value the prefix forces against an assumption.

    Each forced value was established by a probe over the core's non-assumption
    groups, so this only arranges what was already proven: the facts those groups
    publish, then the derivation the probe closed, then the assumption that
    disagrees, then the contradiction.  Returns ``None`` when no forced value
    contradicts an assumption, so the caller falls through to the single-shape
    patterns.

    :param core: The published core.
    :type core: BmcConflictCore
    :param forced_values: Values the prefix admits no alternative to.
    :type forced_values: Tuple[pyfcstm.bmc.infeasibility.ForcedValue, ...]
    :return: The ordered steps, the closing sentence and the phrase naming what
        carried the value, or ``None``.  The phrase travels with the steps so the
        summary cannot describe the same derivation differently from the step
        that made it.
    :rtype: Optional[Tuple[Tuple[BmcReasoningStep, ...], str, str]]

    Example::

        >>> _propagation_steps(None, ()) is None
        True
    """
    if not forced_values:
        return None
    by_id = {item.constraint.stable_id: item for item in core.items}
    for forced in forced_values:
        # The readability check carries different weight in the two selections
        # below.  Here it decides membership: the last comparison is ``!=``, which
        # an *absent* value satisfies, so a fact missing that key would be read as
        # disagreeing and then published as one.  In the supporting selection every
        # comparison is ``==``, which an absent key can never satisfy, so the check
        # only licenses the direct indexing and never changes who is selected.
        # The one comparison that cannot become an axis: ``!=`` is satisfied by an
        # absent key, so asking for it through :func:`_members` would select a fact
        # with no value and publish the value it does not have.  The equalities go
        # through the shared selection; the inequality stays here, after it.
        disagreeing = [
            item
            for item in _members(
                core.items,
                "variable_comparison",
                variable=forced.variable,
                frame=forced.frame,
                operator="eq",
            )
            if item.constraint.stage == "assumptions"
            and item.normalized_fact["value"] != forced.value
        ]
        if not disagreeing:
            continue
        # ``supporting_ids`` is a list of names, and nothing promises they are
        # distinct or that they name groups outside the assumptions -- the type
        # copies no invariant onto them.  Both cases have to be settled here,
        # before a step exists: a step refuses to repeat an id, so a name given
        # twice, or a member that both carries the value and contradicts it, would
        # raise out of a published builder instead of leaving the derivation
        # unmade.  Naming the same group twice is redundant rather than wrong, so
        # it collapses; a group on both sides contradicts the value it is offered
        # as forcing, and no honest step can be built from it.
        seen, supporting = set(), []
        for name in forced.supporting_ids:
            if name in by_id and name not in seen:
                seen.add(name)
                supporting.append(by_id[name])
        if seen & {item.constraint.stable_id for item in disagreeing}:
            continue
        if _members(
            supporting,
            "variable_comparison",
            variable=forced.variable,
            frame=forced.frame,
            operator="eq",
            value=forced.value,
        ):
            # A supporting fact already states this value at this frame, so "the
            # prefix therefore requires it" restates the line above it -- and
            # credits a transition prefix even where no transition took part.
            # The single-shape patterns describe such a core better.
            continue
        steps = tuple(
            BmcReasoningStep("fact", (item.constraint.stable_id,), (), item.human_text)
            for item in supporting
        )
        # Name what actually carried the value.  "The transition prefix" is true
        # only when a transition rule took part; with an initializer and a
        # predicate alone it credits machinery the model does not contain, and
        # the reader looks for a transition that is not there.
        carriers = {item.semantic_role for item in supporting}
        if "transition_rule" in carriers:
            source_phrase = "The transition prefix"
        elif carriers == {"initial_fact"}:
            source_phrase = "The initial state"
        else:
            source_phrase = "The constraints above"
        steps += (
            BmcReasoningStep(
                "derivation",
                tuple(item.constraint.stable_id for item in supporting),
                (),
                "%s therefore requires %s to equal %s at frame %s."
                % (source_phrase, forced.variable, forced.value, forced.frame),
            ),
        )
        steps += tuple(
            BmcReasoningStep("fact", (item.constraint.stable_id,), (), item.human_text)
            for item in disagreeing
        )
        if not _explains_every_member(supporting + disagreeing, core.items):
            # The coverage check the four single-shape patterns all make.  On the
            # orchestration path the shrink already guarantees it -- the
            # supporting set plus one disagreeing assumption is unsatisfiable, so
            # a minimal core holds nothing else -- but this branch is reached
            # through a published function too, and a rule the reader has to
            # reconstruct from elsewhere is not a rule this branch states.
            continue
        values = sorted(
            {forced.value} | {item.normalized_fact["value"] for item in disagreeing}
        )
        closing = "Frame %s cannot assign %s to %s at the same time." % (
            forced.frame,
            " and ".join(str(value) for value in values),
            forced.variable,
        )
        steps += (
            BmcReasoningStep(
                "conflict",
                tuple(item.constraint.stable_id for item in supporting)
                + tuple(item.constraint.stable_id for item in disagreeing),
                (),
                closing,
            ),
        )
        return steps, closing, source_phrase
    return None


def build_conflict_narrative(
    core: "BmcConflictCore",
    forced_values: Tuple = (),
    state_paths: Optional[Mapping] = None,
) -> BmcConflictNarrative:
    """Render the deterministic account of why the published core is unsatisfiable.

    The narrative reads the core and its normalized facts only, so it never
    outruns the recognizers: with a supported pattern it walks each fact and then
    names the contradiction, and otherwise it states that the listed groups are
    jointly unsatisfiable and stops.  The steps are ordered causally -- facts
    first, the closing conflict last -- rather than by stable id.

    :param core: The published subset core to describe.
    :type core: BmcConflictCore
    :param forced_values: Values the core's non-assumption groups leave no
        alternative to, each established by a solver probe rather than read from
        the formula, defaults to ``()``.
    :type forced_values: Tuple[pyfcstm.bmc.infeasibility.ForcedValue, ...], optional
    :param state_paths: State code to authored path, so every sentence names the
        state the reader wrote; defaults to ``None``.
    :type state_paths: Optional[Mapping[int, str]], optional
    :return: The narrative for this core.
    :rtype: BmcConflictNarrative

    Example::

        >>> reference = BmcConstraintRef(
        ...     "g0", "kernel", "transition.step",
        ...     BmcSourceRef("generated", None, None), "step rule",
        ... )
        >>> item = BmcCoreItem(
        ...     reference, "transition_rule", None, False,
        ...     {"kind": "structural_constraint"}, "step rule", False,
        ... )
        >>> core = BmcConflictCore(
        ...     "kernel", "target", "source_group", "raw", "not_proven", (item,),
        ... )
        >>> build_conflict_narrative(core).derivation_status
        'structural_only'
    """
    ids = tuple(item.constraint.stable_id for item in core.items)
    # Only authored entries are offered: a generated encoding rule has no line
    # for the reader to open.  These are review entry points, not a repair
    # instruction, and editing one does not promise the full target becomes
    # satisfiable.
    surfaces = tuple(
        sorted(item.constraint.stable_id for item in core.items if item.editable)
    )
    propagation = _propagation_steps(core, forced_values)
    if propagation is not None:
        steps, closing, carrier = propagation
        return BmcConflictNarrative(
            derivation_status="complete",
            headline=closing,
            summary=(
                "The scenario is empty before the property objective is "
                "considered: a value carried by %s contradicts an assumption "
                "in %s." % (carrier[0].lower() + carrier[1:], core.scope)
            ),
            reasoning_steps=steps,
            review_surfaces=surfaces,
        )
    pattern = _conflict_pattern(core.items, core.subset_minimality, state_paths)
    if pattern is None:
        # The frozen degradation wording: state the joint fact, say the specific
        # derivation is unavailable, and do not present that as a root cause.
        summary = (
            "The listed source groups are jointly unsatisfiable in %s. A more "
            "specific value/state derivation is not available for this "
            "expression shape." % core.scope
        )
        return BmcConflictNarrative(
            derivation_status="structural_only",
            headline="The %s constraints cannot hold together." % core.scope,
            summary=summary,
            reasoning_steps=(BmcReasoningStep("fact", ids, (), summary),),
            review_surfaces=surfaces,
        )
    rule, closing = pattern
    steps = tuple(
        BmcReasoningStep("fact", (item.constraint.stable_id,), (), item.human_text)
        for item in core.items
    ) + (BmcReasoningStep("conflict", ids, (), closing),)
    return BmcConflictNarrative(
        derivation_status="complete",
        headline=closing,
        summary=(
            "The scenario is empty before the property objective is considered: "
            "%s over %d source group%s in %s."
            % (
                rule.replace("_", " "),
                len(core.items),
                "" if len(core.items) == 1 else "s",
                core.scope,
            )
        ),
        reasoning_steps=steps,
        review_surfaces=surfaces,
    )


def explanation_text_lines(explanation) -> List[str]:
    """Render one published explanation as human report lines.

    ``BmcSolveResult.__str__()``, ``to_text()`` and the CLI must present an
    explanation the same way, and narrative and text rendering belong in this
    module rather than in the solver-facing one.  Both callers route through here
    so neither can drift from the other, and a caller who paid for ``formal`` or
    ``proof`` sees the result wherever they read it.

    :param explanation: Published explanation, or ``None``.
    :type explanation: Optional[BmcInfeasibilityExplanation]
    :return: Report lines, empty when no explanation was published.
    :rtype: List[str]

    Example::

        >>> explanation_text_lines(None)
        []
    """
    if explanation is None:
        return []
    lines = []
    # An achieved depth is named with its status; achieving nothing is named with
    # the request instead, and the key says which of the two this is.
    key = (
        ("none", explanation.requested_mode)
        if explanation.achieved_mode == "none"
        else (explanation.achieved_mode, explanation.status)
    )
    lines.append("Explanation: %s" % _ALL_EXPLANATION_HEADLINES[key])
    if depth_line_is_needed(explanation.requested_mode, explanation.achieved_mode):
        lines.append(
            "Explanation depth: requested %s, achieved %s"
            % (explanation.requested_mode, explanation.achieved_mode)
        )
    if explanation.classification is not None:
        lines.append(
            "Classification: %s" % CLASSIFICATION_PHRASES[explanation.classification]
        )
    narrative = explanation.narrative
    if narrative is not None and narrative.reasoning_steps:
        lines.append("")
        lines.append("Why no execution exists:")
        for index, step in enumerate(narrative.reasoning_steps, start=1):
            lines.append("  %d. %s" % (index, step.text))
        if narrative.derivation_status == "structural_only":
            # The frozen degradation transcript labels the depth outright so a
            # reader never mistakes a joint-unsatisfiability statement for an
            # identified root cause.
            lines.append("Derivation: STRUCTURAL ONLY")
    core = explanation.core
    if core is not None:
        lines.append("")
        lines.append("Conflict constraints:")
        for index, item in enumerate(core.items, start=1):
            source = item.constraint.source
            location = _item_location(item)
            if source.kind == "generated":
                # The frozen contract is explicit that a generated support group
                # must be shown together with its frame/step/refs rather than
                # hidden for tidiness, and its transcript prints that position
                # inline on the group's own line, with any remaining refs on
                # an indented line after it.  An authored
                # constraint instead shows its own text, whose "assume at 1"
                # already states the position.
                position = _core_position(item.constraint)
                if position:
                    location = "%s %s" % (location, position)
                lines.append("  %d. %s" % (index, location))
                structural = _core_structural_refs(item.constraint)
                if structural:
                    lines.append("     %s" % structural)
            else:
                lines.append("  %d. %s" % (index, location))
                detail = item.source_excerpt or item.human_text
                if detail:
                    lines.append("     %s" % detail)
        lines.append("")
        if core.subset_minimality == "proven":
            lines.append(
                "The displayed core is sufficient for UNSAT and proven subset-minimal."
            )
        else:
            lines.append(
                "The displayed core is sufficient for UNSAT but is not proven "
                "subset-minimal."
            )
        lines.append("Core scope: %s" % core.scope)
        # The fuller block belongs to the closed-derivation transcript.  The
        # degraded one prints scope, reduction and the reason the reduction
        # stopped, and nothing else, so emitting granularity, size, a labelled
        # minimality line and a duration there would claim a completeness that
        # transcript does not have.  The discriminator is the derivation rather
        # than the status, because a stage-fallback artifact closes its chain and
        # is still published as partial.
        closed = narrative is not None and narrative.derivation_status == "complete"
        if closed:
            lines.append("Core granularity: %s" % core.granularity)
            lines.append("Core size: %d" % len(core.items))
        lines.append("Reduction: %s" % core.reduction)
        if closed:
            lines.append("Subset minimality: %s" % core.subset_minimality)
        if closed and explanation.proof is not None:
            # Frozen by the contract at §12.1, wording included.  The three facts
            # were reaching JSON only, so a reader of the human report was told the
            # proof is complete without being told what "complete" was checked
            # against.  Transcribed rather than derived from the values: each field
            # admits one value today, and spelling them out is what makes a widened
            # enum fail here instead of printing a label nobody wrote.
            lines.append("")
            lines.append("Proof strength:")
            lines.append(
                "  Input constraints: %s"
                % _PROOF_STRENGTH_PHRASES["input"][explanation.proof.input_minimality]
            )
            lines.append(
                "  Reasoning graph: %s"
                % _PROOF_STRENGTH_PHRASES["graph"][explanation.proof.graph_minimality]
            )
            lines.append(
                "  Every reasoning step: %s"
                % _PROOF_STRENGTH_PHRASES["verification"][
                    explanation.proof.verification_status
                ]
            )
        if closed and narrative.review_surfaces:
            lines.append("")
            lines.append("Review surfaces:")
            surfaces = {
                item.constraint.stable_id: item
                for item in core.items
                if item.constraint.stable_id in set(narrative.review_surfaces)
            }
            for stable_id in narrative.review_surfaces:
                item = surfaces[stable_id]
                lines.append(
                    "  %s  %s"
                    % (
                        item.semantic_role.replace("_", " "),
                        _item_location(item),
                    )
                )
            # Fixed wording from the frozen transcript.  A review surface is an
            # entry point for the reader to inspect, not a repair the tool chose,
            # and it is no promise that editing one makes the target satisfiable.
            lines.append("  No automatic repair has been selected.")
    if explanation.reason is not None:
        lines.append("Reason: %s" % explanation.reason)
    if (
        explanation.elapsed_ms is not None
        and explanation.narrative is not None
        and explanation.narrative.derivation_status == "complete"
    ):
        lines.append("")
        lines.append("Explanation time: %.3f ms" % explanation.elapsed_ms)
    if core is None and explanation.classification is not None:
        lines.append("")
        # Two physical lines, broken where the frozen transcript breaks them.
        lines.append(
            "No conflict core or causal chain was published. The classification "
            "is retained"
        )
        lines.append(
            "as partial metadata, but it is not presented as a completed formal "
            "explanation."
        )
    return lines
