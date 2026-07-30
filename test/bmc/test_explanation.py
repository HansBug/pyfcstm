"""TDD contracts for the public BMC infeasibility explanation data layer.

The dataclasses under test are the frozen public shape described by the
upstream design.  They deliberately carry no Z3 objects so that downstream
consumers can read an explanation without loading the solver stack.
"""

from __future__ import annotations

from collections import UserDict
from types import MappingProxyType

import json
import subprocess
import sys

import pytest

from pyfcstm.bmc.explanation import (
    MAX_SOURCE_EXCERPT_CHARS,
    BmcConflictCore,
    BmcConflictNarrative,
    BmcConflictProof,
    BmcConstraintRef,
    BmcCoreItem,
    BmcInfeasibilityExplanation,
)
from pyfcstm.bmc.provenance import BmcSourceRef

pytestmark = pytest.mark.unittest

_GENERATED = BmcSourceRef("generated", None, None)


#: One stage that every scope's target formula legitimately contains, so a
#: fixture core can be built for any scope without leaving its target.
_SCOPE_MEMBER_STAGE = {
    "kernel": "kernel",
    "initialization_component": "initialization",
    "initialization_domain": "initialization",
    "initialization_prefix": "initialization",
    "assumptions_component": "assumptions",
    "assumptions_domain": "assumptions",
    "assumptions_prefix": "assumptions",
    "initialization_stage_fallback": "initialization",
    "assumptions_stage_fallback": "assumptions",
}

_STAGE_CATEGORY = {
    "kernel": ("domain.frame_state", "domain_rule"),
    "initialization": ("initial.target", "initial_fact"),
    "assumptions": ("assumption.frame", "assumption"),
}


def _constraint(
    stable_id: str = "initial.target", stage: str = "initialization"
) -> BmcConstraintRef:
    category, _ = _STAGE_CATEGORY[stage]
    return BmcConstraintRef(
        stable_id=stable_id,
        stage=stage,
        category=category,
        source=_GENERATED,
        summary="initial target state",
    )


def _item(
    stable_id: str = "initial.target", stage: str = "initialization"
) -> BmcCoreItem:
    _, role = _STAGE_CATEGORY[stage]
    return BmcCoreItem(
        constraint=_constraint(stable_id, stage),
        semantic_role=role,
        source_excerpt=None,
        source_excerpt_truncated=False,
        normalized_fact={"kind": "structural_constraint", "stable_id": stable_id},
        human_text="initial target state",
        editable=False,
    )


def _core(
    scope: str = "initialization_component",
    reduction: str = "raw",
    subset_minimality: str = "not_proven",
) -> BmcConflictCore:
    stage = _SCOPE_MEMBER_STAGE[scope]
    return BmcConflictCore(
        scope=scope,
        formula_summary="I_0",
        granularity="source_group",
        reduction=reduction,
        subset_minimality=subset_minimality,
        items=(_item(stage=stage),),
    )


def test_explanation_module_never_imports_z3() -> None:
    """The public data layer stays solver-free so consumers can skip Z3.

    The check runs in a fresh interpreter: deleting modules from the current
    ``sys.modules`` would leave every later test in this process importing a
    half-torn-down package.
    """
    probe = "import sys\nimport pyfcstm.bmc.explanation\nprint('z3' in sys.modules)\n"
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.strip() == "False"


def test_a_category_outside_every_family_is_refused() -> None:
    """The published schema constrains this field to the five known families.

    Accepting anything else means this exported constructor can emit output that
    fails the contract it publishes -- the direction the asymmetry ledger does
    not cover.  ``category_role`` already states the rule; the constructor now
    goes through it.
    """
    with pytest.raises(ValueError, match="belongs to no known family"):
        BmcConstraintRef("x", "kernel", "not_a_family", _GENERATED, "s")

    # Each known family is still accepted.
    for category in (
        "domain.frame_state",
        "initial.target",
        "transition.step",
        "assumption.frame",
        "definedness",
    ):
        stage = "kernel"
        if category.startswith("initial"):
            stage = "initialization"
        elif category.startswith("assumption"):
            stage = "assumptions"
        assert (
            BmcConstraintRef("x", stage, category, _GENERATED, "s").category == category
        )


#: Frozen structures the transcription test above pins by value.
_TRANSCRIBED_FROZEN_NAMES = frozenset(
    {
        "_DERIVATION_STATUSES",
        "_FACT_REQUIRED_KEYS",
        "_REASONING_STEP_KINDS",
        "_RELATION_PHRASES",
        "_ROLE_VOICES",
        "CATEGORY_ROLES",
        "CLASSIFICATION_SCOPES",
        "INDEX_REF_KEYS",
        "SCOPE_AGGREGATES",
        "STAGE_FALLBACK_SCOPES",
        "UNBUILT_SLOTS",
        "_FACT_KINDS",
        "_GRANULARITIES",
        "_MINIMALITIES",
        "_MODES",
        "_REDUCTIONS",
        "CLASSIFICATION_PHRASES",
        "EXPLANATION_HEADLINES",
        "_SEMANTIC_ROLES",
        "_STAGES",
        "_STATUSES",
    }
)

#: Frozen structures deliberately not transcribed, each with its reason.
_DERIVED_FROZEN_NAMES = {
    "_SCOPES": "concatenation of CLASSIFICATION_SCOPES values and the fallbacks",
    "_DELIVERY_MATRIX_ROWS": "transcribed by the delivery-matrix test instead",
    "_DELIVERY_SIGNATURES": "expanded from _DELIVERY_MATRIX_ROWS",
    "_MODE_ORDER": "an ordering over _MODES, pinned by the delivery matrix",
    "_REDUCTION_MINIMALITY": "pinned by the reduction/minimality coupling tests",
}


def test_the_transcription_guard_covers_every_frozen_structure() -> None:
    """The guard has to notice a frozen structure nobody transcribed.

    Listing vocabularies by hand has now missed some three times, most recently
    in the very test written to stop that happening.  Enumerating the module
    instead means a newly frozen structure fails here until someone either
    transcribes it or records why it is derived from one that already is.
    """
    from collections.abc import Collection, Mapping

    from pyfcstm.bmc import explanation as module

    frozen_names = set()
    for name in dir(module):
        if name.startswith("__"):
            continue
        value = getattr(module, name)
        # Any container at all, decided by the abstract protocols rather than a
        # list of concrete types.  Each earlier version named the types it knew
        # about and leaked through the next one -- first plain dicts, then
        # ``list``, then a ``deque`` holding a frozen table.  ``str`` and
        # ``bytes`` are Collections too but are scalars here, so they are the
        # only exclusions.
        if isinstance(value, (Collection, Mapping)) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            # Type aliases and imported helpers are not frozen data.
            if name in {"Any", "Dict", "Mapping", "Optional", "Tuple", "Literal"}:
                continue
            frozen_names.add(name)

    accounted = _TRANSCRIBED_FROZEN_NAMES | set(_DERIVED_FROZEN_NAMES)
    assert frozen_names - accounted == set(), (
        "a frozen structure is neither transcribed nor recorded as derived"
    )
    # And nothing in the lists has quietly disappeared from the module.
    assert accounted - frozen_names == set()

    # The sibling modules hold frozen tables too, and an enumeration of one
    # module would say nothing about them.
    from pyfcstm.bmc import infeasibility, provenance

    sibling_frozen = set()
    for sibling, imported in (
        (provenance, {"Span"}),
        (
            infeasibility,
            # Re-exports of tables this module already accounts for.
            {"CLASSIFICATION_SCOPES", "SCOPE_AGGREGATES", "SCOPE_TARGETS"},
        ),
    ):
        for name in dir(sibling):
            if name.startswith("__") or name in imported:
                continue
            value = getattr(sibling, name)
            if not isinstance(value, (Collection, Mapping)) or isinstance(
                value, (str, bytes, bytearray)
            ):
                continue
            sibling_frozen.add("%s.%s" % (sibling.__name__.rsplit(".", 1)[1], name))

    assert sibling_frozen == {
        "provenance._SOURCE_KINDS",
        "provenance._VALUE_FACT_CATEGORIES",
        "provenance.TRACKED_GROUP_PAIRINGS",
        "infeasibility.AGGREGATE_SELECTORS",
        "infeasibility._INDEX_REF_KEYS",
        "infeasibility._STAGE_FALLBACK_BY_STAGE",
    }
    assert provenance._SOURCE_KINDS == {"fcstm", "fbmcq", "generated"}
    # Transcribed because it decides which groups get a value-level reading at
    # all: a category dropped from here silently degrades to structural.
    # Transcribed because they are the whole published sentence vocabulary: a
    # relation or role dropped from either mapping renders as a bare tag inside
    # otherwise fluent prose, or silently borrows another role's voice.
    # Transcribed because they are published dispatch vocabularies: a kind or
    # status added without a schema enum entry would pass Python and fail
    # validation, and one removed would silently narrow what can be published.
    # Transcribed because it decides which members a reader may index directly:
    # a tag whose keys are dropped from here silently becomes indexable without
    # them, which is the KeyError this table exists to prevent.
    assert module._FACT_REQUIRED_KEYS == {
        "structural_constraint": (),
        "variable_comparison": ("variable", "frame", "operator", "value"),
        "state_membership": ("frame", "state"),
        "state_domain": ("frame", "states"),
        "definedness_condition": ("frame", "operation"),
    }
    # Every published tag needs an entry, or it becomes readable by omission.
    assert set(module._FACT_REQUIRED_KEYS) == set(module._FACT_KINDS)
    assert module._REASONING_STEP_KINDS == ("fact", "derivation", "conflict")
    assert module._DERIVATION_STATUSES == (
        "complete",
        "partial",
        "structural_only",
        "not_available",
    )
    assert set(module._RELATION_PHRASES) == {"eq", "ne", "le", "lt", "ge", "gt"}
    assert module._RELATION_PHRASES["eq"] == "to equal %s"
    assert module._ROLE_VOICES == {
        "assumption": "the query",
        "initial_fact": "the initializer",
        "domain_rule": "the model",
        "transition_rule": "the transition",
        "definedness": "the expression",
    }
    assert provenance._VALUE_FACT_CATEGORIES == (
        "assumption.frame",
        "initial.variable",
        "initial.where",
    )
    # Transcribed, not merely registered: the constructor refuses a pairing that
    # is not listed here, so the contents are the contract.
    assert provenance.TRACKED_GROUP_PAIRINGS == frozenset(
        {
            ("assumptions", "assumption.cardinality"),
            ("assumptions", "assumption.event"),
            ("assumptions", "assumption.frame"),
            ("assumptions", "definedness"),
            ("initialization", "definedness"),
            ("initialization", "initial.target"),
            ("initialization", "initial.variable"),
            ("initialization", "initial.where"),
            ("kernel", "domain.frame_state"),
            ("kernel", "transition.case"),
            ("kernel", "transition.step"),
        }
    )
    assert infeasibility._INDEX_REF_KEYS == ("frame", "frames", "step", "steps")
    assert dict(infeasibility._STAGE_FALLBACK_BY_STAGE) == {
        "initialization": "initialization_stage_fallback",
        "assumptions": "assumptions_stage_fallback",
    }
    assert set(infeasibility.AGGREGATE_SELECTORS) == {
        "domain",
        "transition",
        "initial",
        "environment",
    }


def test_every_frozen_vocabulary_matches_the_authored_list() -> None:
    """Each vocabulary is compared against an independent transcription.

    Widening a vocabulary is invisible to every other test here: the corpus that
    checks schema/constructor agreement draws its values from the implementation's
    own tuples, so adding a member widens the corpus with it.  The list below has
    to name every vocabulary the package freezes, including the ones in
    ``provenance``: the first version of this guard missed two, which is the same
    "the exhaustive list is itself incomplete" mistake it was written to prevent.  Adding a bogus
    entry to the statuses, modes or reductions failed nothing before this test
    existed.  The lists below are copied from the authored contract rather than
    imported, because comparing a table with itself proves only that it equals
    itself.
    """
    from pyfcstm.bmc import explanation as module

    assert module._MODES == ("none", "formal", "proof")
    assert module._STATUSES == ("complete", "partial", "unknown", "timeout")
    assert module._REDUCTIONS == ("raw", "partial_minimized", "subset_minimal")
    assert module._MINIMALITIES == ("proven", "not_proven")
    assert module._GRANULARITIES == ("source_group",)
    assert module._STAGES == ("kernel", "initialization", "assumptions")
    assert module._SEMANTIC_ROLES == (
        "domain_rule",
        "initial_fact",
        "transition_rule",
        "assumption",
        "definedness",
    )
    assert dict(module.CATEGORY_ROLES) == {
        "domain.": "domain_rule",
        "initial.": "initial_fact",
        "transition.": "transition_rule",
        "assumption.": "assumption",
        "definedness": "definedness",
    }
    assert dict(module.CLASSIFICATION_SCOPES) == {
        "kernel_conflict": "kernel",
        "initialization_self_conflict": "initialization_component",
        "initialization_domain_conflict": "initialization_domain",
        "initialization_kernel_conflict": "initialization_prefix",
        "assumptions_self_conflict": "assumptions_component",
        "assumptions_domain_conflict": "assumptions_domain",
        "assumptions_prefix_conflict": "assumptions_prefix",
    }
    assert module.STAGE_FALLBACK_SCOPES == (
        "initialization_stage_fallback",
        "assumptions_stage_fallback",
    )
    assert module._FACT_KINDS == (
        "structural_constraint",
        "variable_comparison",
        "state_membership",
        "state_domain",
        "definedness_condition",
    )
    assert module.UNBUILT_SLOTS == ("proof",)
    assert module.INDEX_REF_KEYS == ("frame", "frames", "step", "steps")
    assert dict(module.SCOPE_AGGREGATES) == {
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
    # The published excerpt bound is stated by the contract, not derived.
    assert module.MAX_SOURCE_EXCERPT_CHARS == 4096

    from pyfcstm.bmc import provenance

    assert provenance._SOURCE_KINDS == {"fcstm", "fbmcq", "generated"}
    assert provenance.MAX_METADATA_DEPTH == 64
    assert provenance.MAX_METADATA_INT_DIGITS == 4300


def test_explanation_field_order_matches_frozen_prototype() -> None:
    """The container shape is frozen once; later stages only fill it in."""
    assert tuple(BmcInfeasibilityExplanation.__dataclass_fields__) == (
        "requested_mode",
        "achieved_mode",
        "status",
        "classification",
        "core",
        "proof",
        "narrative",
        "reason",
        "elapsed_ms",
    )


@pytest.mark.parametrize(
    "classification, scope",
    [
        ("kernel_conflict", "kernel"),
        ("initialization_self_conflict", "initialization_component"),
        ("initialization_domain_conflict", "initialization_domain"),
        ("initialization_kernel_conflict", "initialization_prefix"),
        ("assumptions_self_conflict", "assumptions_component"),
        ("assumptions_domain_conflict", "assumptions_domain"),
        ("assumptions_prefix_conflict", "assumptions_prefix"),
    ],
)
def test_classification_scope_pairs_are_accepted(classification, scope) -> None:
    """Each classification pairs with exactly one diagnostic scope."""
    explanation = BmcInfeasibilityExplanation(
        requested_mode="formal",
        achieved_mode="formal",
        status="partial",
        classification=classification,
        core=_core(scope),
        reason="minimization not attempted",
    )

    assert explanation.core is not None
    assert explanation.core.scope == scope


def test_classification_scope_cross_product_rejects_mismatches() -> None:
    """The 7x7 cross product accepts exactly the seven frozen pairings."""
    pairs = [
        ("kernel_conflict", "kernel"),
        ("initialization_self_conflict", "initialization_component"),
        ("initialization_domain_conflict", "initialization_domain"),
        ("initialization_kernel_conflict", "initialization_prefix"),
        ("assumptions_self_conflict", "assumptions_component"),
        ("assumptions_domain_conflict", "assumptions_domain"),
        ("assumptions_prefix_conflict", "assumptions_prefix"),
    ]
    accepted = 0
    for classification, _ in pairs:
        for _, scope in pairs:
            try:
                BmcInfeasibilityExplanation(
                    requested_mode="formal",
                    achieved_mode="formal",
                    status="partial",
                    classification=classification,
                    core=_core(scope),
                    reason="minimization not attempted",
                )
            except ValueError:
                continue
            accepted += 1

    assert accepted == len(pairs)


@pytest.mark.parametrize(
    "scope", ["initialization_stage_fallback", "assumptions_stage_fallback"]
)
def test_stage_fallback_scopes_require_absent_classification(scope) -> None:
    """A stage fallback never claims a self/domain/prefix classification."""
    accepted = BmcInfeasibilityExplanation(
        requested_mode="formal",
        achieved_mode="formal",
        status="partial",
        classification=None,
        core=_core(scope),
        reason="classification degraded to stage fallback",
    )
    assert accepted.classification is None

    with pytest.raises(ValueError, match="stage fallback"):
        BmcInfeasibilityExplanation(
            requested_mode="formal",
            achieved_mode="formal",
            status="partial",
            classification="assumptions_self_conflict",
            core=_core(scope),
            reason="classification degraded to stage fallback",
        )


def test_kernel_scope_is_not_a_stage_fallback() -> None:
    """``kernel`` always carries ``kernel_conflict`` and is never a fallback.

    The kernel stage has no weaker component or domain probe, so localization
    alone already determines the classification.  Treating ``kernel`` as a
    ``classification=None`` fallback would break the unique mapping.
    """
    with pytest.raises(ValueError, match="kernel"):
        BmcInfeasibilityExplanation(
            requested_mode="formal",
            achieved_mode="formal",
            status="partial",
            classification=None,
            core=_core("kernel"),
            reason="classification degraded",
        )


#: The frozen delivery table, transcribed from the authored rows.
#:
#: This is deliberately a second, independent copy rather than an import from
#: the implementation: checking a table against itself proves only that it
#: equals itself.  Each entry is ``(requested_mode, achieved_mode, status,
#: classification present, core present, reason present)``.
_AUTHORED_DELIVERY_ROWS = frozenset(
    [
        # Row 1: first optional probe unknown, so no classification and no core.
        ("formal", "none", "unknown", False, False, True),
        ("proof", "none", "unknown", False, False, True),
        # Row 2: the same after the budget expired.
        ("formal", "none", "timeout", False, False, True),
        ("proof", "none", "timeout", False, False, True),
        # Row 3: classification finished, raw core did not.
        ("formal", "none", "partial", True, False, True),
        ("proof", "none", "partial", True, False, True),
        # Rows 4, 6, 7: a sound core with minimality, scope or proof still open.
        ("formal", "formal", "partial", False, True, True),
        ("formal", "formal", "partial", True, True, True),
        ("proof", "formal", "partial", False, True, True),
        ("proof", "formal", "partial", True, True, True),
        # Row 5: a diagnostic subset-minimal core with complete semantic facts.
        ("formal", "formal", "complete", True, True, False),
        # Row 8: a verified proof DAG over a diagnostic artifact.
        ("proof", "proof", "complete", True, True, False),
        # Row 9: a verified proof DAG over a stage-fallback artifact.  A
        # stage-fallback scope means the classification did not finish, which
        # the frozen boundary states as "proof 完整，但 classification 未完成",
        # so this row carries no classification.  A verified proof beside a
        # finished classification is row 8, which is complete rather than
        # partial; the table lists no partial row for that shape.
        ("proof", "proof", "partial", False, True, True),
    ]
)

#: Rows the table allows but this stage cannot build yet.
#:
#: ``complete`` requires a narrative and ``achieved_mode='proof'`` requires a
#: proof DAG; both slots are unbuilt, so those rows must be rejected here even
#: though the frozen table lists them.  Naming the reason keeps the exclusion
#: reviewable instead of quietly shrinking the expected set.
_UNBUILT_DELIVERY_ROWS = frozenset(
    row for row in _AUTHORED_DELIVERY_ROWS if row[2] == "complete" or row[1] == "proof"
)


@pytest.mark.parametrize("requested_mode", ["none", "formal", "proof"])
@pytest.mark.parametrize("achieved_mode", ["none", "formal", "proof"])
@pytest.mark.parametrize("status", ["complete", "partial", "unknown", "timeout"])
@pytest.mark.parametrize("has_classification", [False, True])
@pytest.mark.parametrize("has_core", [False, True])
@pytest.mark.parametrize("has_reason", [False, True])
def test_delivery_matrix_accepts_exactly_the_authored_rows(
    requested_mode, achieved_mode, status, has_classification, has_core, has_reason
) -> None:
    """The frozen table is exhaustive, so anything outside it must be refused.

    Independent per-field rules are strictly weaker than the table: each rule
    can hold while the combination appears in no authored row.  Enumerating the
    whole cross product is the only way to see that gap, because a combination
    the implementation wrongly accepts looks exactly like one it should.
    """
    row = (
        requested_mode,
        achieved_mode,
        status,
        has_classification,
        has_core,
        has_reason,
    )
    expected_valid = (
        row in _AUTHORED_DELIVERY_ROWS and row not in _UNBUILT_DELIVERY_ROWS
    )

    kwargs = dict(
        requested_mode=requested_mode,
        achieved_mode=achieved_mode,
        status=status,
        classification="assumptions_self_conflict" if has_classification else None,
        # An absent classification forces the stage-fallback scope; that is the
        # frozen scope mapping composing with this table, not a third rule.
        core=(
            _core(
                "assumptions_component"
                if has_classification
                else "assumptions_stage_fallback"
            )
            if has_core
            else None
        ),
        reason="degraded" if has_reason else None,
    )
    if expected_valid:
        assert BmcInfeasibilityExplanation(**kwargs).status == status
    else:
        with pytest.raises(ValueError):
            BmcInfeasibilityExplanation(**kwargs)


def test_metadata_deeper_than_the_published_limit_is_named() -> None:
    """A depth the serializer cannot handle is refused with the field named.

    The recursive walk and the JSON encoder are both bounded by the interpreter
    stack.  Without an explicit limit a legal but very deep mapping passes
    validation and then dies during serialization with a bare ``RecursionError``
    that names neither the field nor the object -- the exact failure mode this
    boundary exists to prevent.
    """
    from pyfcstm.bmc.provenance import MAX_METADATA_DEPTH

    def nest(depth):
        payload = {"leaf": 1}
        for _ in range(depth):
            payload = {"n": payload}
        return payload

    accepted = BmcConstraintRef(
        "g0",
        "assumptions",
        "assumption.frame",
        _GENERATED,
        "s",
        refs=nest(MAX_METADATA_DEPTH - 2),
    )
    assert accepted.refs

    with pytest.raises(ValueError, match="nests deeper than the published limit"):
        BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            _GENERATED,
            "s",
            refs=nest(MAX_METADATA_DEPTH + 5),
        )


def test_published_metadata_is_detached_from_the_caller() -> None:
    """A frozen object must not change when the caller's own dict changes.

    Validating the mapping and then keeping a shallow copy of it means the value
    that finally reaches JSON is not the value that was validated: the caller
    still holds every nested mapping and can write to it afterwards.  Nothing
    fails at construction time, so the corruption only surfaces when the whole
    result is dumped, naming neither the field nor the object.
    """
    import json

    refs_alias = {}
    reference = BmcConstraintRef(
        "g0",
        "assumptions",
        "assumption.frame",
        _GENERATED,
        "s",
        refs={"nested": refs_alias},
    )
    fact_alias = {}
    item = BmcCoreItem(
        reference,
        "assumption",
        None,
        False,
        {"kind": "structural_constraint", "nested": fact_alias},
        "frame assumption",
        False,
    )

    refs_alias[1] = object()
    fact_alias[2] = object()

    assert 1 not in reference.refs["nested"]
    assert 2 not in item.normalized_fact["nested"]
    json.dumps(reference.to_canonical(), allow_nan=False)
    json.dumps(item.to_canonical(), allow_nan=False)


@pytest.mark.parametrize(
    "refs",
    [
        {"nested": UserDict({"ok": 1})},
        {"seq": [UserDict({"ok": 1})]},
        {"seq": [{"deep": UserDict({"ok": 1})}]},
        {"nested": MappingProxyType({"ok": 1})},
    ],
)
def test_any_nested_mapping_becomes_json_serializable(refs) -> None:
    """The public field accepts any ``Mapping``, so any of them must serialize.

    A ``UserDict`` passes an ``isinstance(..., Mapping)`` check and then fails in
    ``json.dumps``, which is the one place the failure is least attributable.
    Rebuilding the graph during validation is what makes the declared type and
    the canonical output agree.
    """
    import json

    reference = BmcConstraintRef(
        "g0", "assumptions", "assumption.frame", _GENERATED, "s", refs=refs
    )
    payload = json.dumps(reference.to_canonical(), allow_nan=False)

    assert "ok" in payload
    # Sequences come back as JSON arrays rather than the tuples used internally.
    assert "(" not in payload


def test_canonical_output_uses_only_json_containers() -> None:
    """Read-only views and tuples have no JSON counterpart, so they convert."""
    reference = BmcConstraintRef(
        "g0",
        "assumptions",
        "assumption.frame",
        _GENERATED,
        "s",
        refs={"nested": {"seq": [1, {"deep": 2}]}},
    )

    canonical = reference.to_canonical()["refs"]

    assert canonical == {"nested": {"seq": [1, {"deep": 2}]}}
    assert type(canonical) is dict
    assert type(canonical["nested"]) is dict
    assert type(canonical["nested"]["seq"]) is list
    assert type(canonical["nested"]["seq"][1]) is dict


def test_an_integer_too_long_to_render_is_refused_by_name() -> None:
    """A number JSON cannot render must fail here, not inside the encoder.

    CPython refuses to turn an integer longer than 4300 digits into text by
    default, so an oversized one passes every type check and then dies in
    ``json.dumps`` with an error naming neither the field nor the object -- the
    failure this boundary exists to prevent.
    """
    import json

    from pyfcstm.bmc.provenance import MAX_METADATA_INT_DIGITS

    assert MAX_METADATA_INT_DIGITS == 4300

    largest = 10**MAX_METADATA_INT_DIGITS - 1
    too_long = 10**MAX_METADATA_INT_DIGITS

    accepted = BmcConstraintRef(
        "g0",
        "assumptions",
        "assumption.frame",
        _GENERATED,
        "s",
        frames=(largest,),
        refs={"big": largest},
    )
    json.dumps(accepted.to_canonical(), allow_nan=False)

    for kwargs in (
        {"frames": (too_long,)},
        {"refs": {"huge": too_long}},
        {"refs": {"huge": -too_long}},
    ):
        with pytest.raises(ValueError, match="exceeds the .* decimal digits"):
            BmcConstraintRef(
                "g0", "assumptions", "assumption.frame", _GENERATED, "s", **kwargs
            )


def test_a_classification_outside_the_frozen_vocabulary_is_refused() -> None:
    """Only a published classification may reach the JSON contract.

    The field names one of a frozen set of verdicts, so a value outside that set
    would publish a classification no consumer of the schema can interpret.
    """
    explanation = BmcInfeasibilityExplanation(
        requested_mode="formal",
        achieved_mode="none",
        status="partial",
        classification="assumptions_self_conflict",
        reason="raw core unknown",
    )
    assert explanation.classification == "assumptions_self_conflict"

    with pytest.raises(ValueError, match="classification"):
        BmcInfeasibilityExplanation(
            requested_mode="formal",
            achieved_mode="none",
            status="partial",
            classification="assumptions_self_conflicts",
            reason="raw core unknown",
        )


def test_an_excerpt_is_bounded_and_its_truncation_flag_has_to_agree() -> None:
    """Both directions of the excerpt bound are refused.

    A caller assembling an item from source text can exceed the published bound,
    or mark a short excerpt as truncated.  Publishing either would misdescribe
    what the reader is looking at, so both are refused rather than repaired.
    """
    reference = _constraint()

    with pytest.raises(ValueError, match="must not exceed"):
        BmcCoreItem(
            reference,
            "initial_fact",
            "X" * (MAX_SOURCE_EXCERPT_CHARS + 1),
            False,
            {"kind": "structural_constraint"},
            "t",
            False,
        )
    with pytest.raises(ValueError, match="truncated excerpt"):
        BmcCoreItem(
            reference,
            "initial_fact",
            "ab",
            True,
            {"kind": "structural_constraint"},
            "t",
            False,
        )

    # Exactly at the bound is accepted, and an untruncated excerpt needs no flag.
    at_bound = BmcCoreItem(
        reference,
        "initial_fact",
        "X" * MAX_SOURCE_EXCERPT_CHARS,
        False,
        {"kind": "structural_constraint"},
        "t",
        False,
    )
    assert len(at_bound.source_excerpt) == MAX_SOURCE_EXCERPT_CHARS


def test_a_declared_role_must_agree_with_its_category() -> None:
    """A role that contradicts its own category is refused, not published.

    ``category`` is a machine dispatch key and ``semantic_role`` is what a reader
    is told the item means.  A caller can pass a pair that disagrees, and
    publishing it would let the two be read against each other.
    """
    from pyfcstm.bmc.explanation import category_role

    # category_role is exported, so a caller can ask directly what a category means.
    assert category_role("initial.target") == "initial_fact"
    assert category_role("assumption.frame") == "assumption"

    with pytest.raises(ValueError, match="contradicts category"):
        BmcCoreItem(
            BmcConstraintRef(
                "initial.target",
                "initialization",
                "initial.target",
                _GENERATED,
                "initial target",
            ),
            "assumption",
            None,
            False,
            {"kind": "structural_constraint"},
            "t",
            False,
        )


def test_published_order_is_by_stable_id_whatever_order_it_was_given() -> None:
    """A core publishes its members sorted, not in the order it received them.

    The solver's own core ordering is not reproducible between runs, so the
    published order has to be a property of the contract rather than of how the
    items happened to arrive.
    """
    items = tuple(
        BmcCoreItem(
            BmcConstraintRef(
                name,
                "initialization",
                "initial.target",
                _GENERATED,
                "initial target",
            ),
            "initial_fact",
            None,
            False,
            {"kind": "structural_constraint", "stable_id": name},
            "t",
            False,
        )
        # Deliberately not sorted, and not reverse-sorted either, so neither
        # "kept as given" nor "reversed" would produce the expected result.
        for name in ("b", "c", "a")
    )

    core = BmcConflictCore(
        "initialization_component", "I_0", "source_group", "raw", "not_proven", items
    )

    assert [item.constraint.stable_id for item in core.items] == ["a", "b", "c"]


def test_a_control_character_cannot_reach_a_published_identifier() -> None:
    """A stable id becomes a solver literal name and a JSON key, so it stays ASCII.

    A caller assembling an id from source text can carry a control character into
    it without noticing, which is why the check is on the value rather than on
    where it came from.
    """
    from pyfcstm.bmc.explanation import is_printable_ascii

    assert is_printable_ascii("initial.target.0000") is True
    assert is_printable_ascii("a\x00b") is False
    assert is_printable_ascii("tab\tseparated") is False
    with pytest.raises(ValueError, match="printable ASCII"):
        BmcConstraintRef(
            "a\x00b",
            "initialization",
            "initial.target",
            _GENERATED,
            "initial target",
        )


def test_the_depth_limit_itself_is_guarded_by_an_absolute_bound() -> None:
    """A relative test cannot falsify the constant it is derived from.

    Every other depth test nests ``MAX_METADATA_DEPTH + 5`` levels, so raising the
    constant to a billion keeps them green -- they would simply build a billion
    levels and hang rather than fail.  Pinning an absolute depth and an absolute
    ceiling on the constant is what makes the limit itself observable.
    """
    from pyfcstm.bmc.provenance import MAX_METADATA_DEPTH

    assert MAX_METADATA_DEPTH <= 200

    payload = {"leaf": 1}
    for _ in range(200):
        payload = {"n": payload}

    with pytest.raises(ValueError, match="nests deeper than the published limit"):
        BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            _GENERATED,
            "s",
            refs=payload,
        )


def test_index_keys_are_canonical_on_the_public_path_too() -> None:
    """Both doors publish one index the same way.

    The orchestration canonicalizes the index keys it reads from the builder, so
    a public constructor that echoed a whole-valued float back would put ``1`` and
    ``1.0`` for one position in two documents that are supposed to agree.
    """
    reference = BmcConstraintRef(
        "g0",
        "assumptions",
        "assumption.frame",
        _GENERATED,
        "s",
        frames=[1.0],
        refs={"frame": 1.0, "steps": [2.0], "threshold": 2.5},
    )

    canonical = reference.to_canonical()

    assert canonical["refs"]["frame"] == 1
    assert canonical["refs"]["steps"] == [2]
    assert type(canonical["refs"]["frame"]) is type(canonical["frames"][0])
    # Free-form metadata keeps the value it was given.
    assert canonical["refs"]["threshold"] == 2.5


def test_the_canonical_exit_is_bounded_like_the_validator() -> None:
    """The public converter cannot be handed data the validator never saw.

    It is exported, so a caller may pass a graph built by hand.  Without its own
    bound, the depth problem the validator names precisely comes back as a bare
    ``RecursionError`` from the converter instead.
    """
    from pyfcstm.bmc.provenance import MAX_METADATA_DEPTH, json_canonical

    value = None
    for _ in range(MAX_METADATA_DEPTH + 5):
        value = {"x": value}

    with pytest.raises(ValueError, match="nests deeper than the published limit"):
        json_canonical(value)


def test_int_subclasses_are_canonicalized_to_plain_ints() -> None:
    """A canonical index is an ``int``, not merely something that acts like one.

    ``IntEnum`` and other ``int`` subclasses pass an ``isinstance`` check but keep
    their own ``repr``, so the published tuple would carry an object that is only
    incidentally an integer.  JSON renders it as a number either way, which is
    exactly why nothing else would notice.
    """
    import enum

    class Frame(enum.IntEnum):
        SECOND = 1

    class Step(int):
        pass

    reference = BmcConstraintRef(
        "initial.target",
        "initialization",
        "initial.target",
        _GENERATED,
        "initial target state",
        frames=[Frame.SECOND],
        steps=[Step(4)],
    )

    assert reference.frames == (1,)
    assert reference.steps == (4,)
    assert [type(value) for value in reference.frames] == [int]
    assert [type(value) for value in reference.steps] == [int]


@pytest.mark.parametrize("values", ["", "12", {}, {"a": 1}, 1, None, {0, 1}])
def test_index_fields_require_an_actual_array(values) -> None:
    """A non-array container is refused instead of being iterated.

    Iterating whatever is handed in silently accepts values the published schema
    refuses: ``""`` and ``{}`` both iterate empty, so the constructor would
    publish ``[]`` for two payloads that are not arrays at all, while the schema
    rejects them.  A ``set`` is not JSON either, and its iteration order is not
    the caller's.
    """
    with pytest.raises(TypeError, match="must be a list or tuple of indices"):
        BmcConstraintRef(
            "initial.target",
            "initialization",
            "initial.target",
            _GENERATED,
            "initial target state",
            frames=values,
        )


def test_the_implementation_matrix_equals_the_authored_table() -> None:
    """Compare the two transcriptions directly, including unreachable rows.

    ``complete`` needs a narrative and ``achieved_mode='proof'`` needs a proof
    DAG, so those rows cannot be constructed at this stage and no behavioural
    test can distinguish them.  Widening one of them would therefore go
    unnoticed until a later stage builds the missing slot and inherits a row the
    frozen table never listed.  Comparing the sets pins them now.
    """
    from pyfcstm.bmc.explanation import _DELIVERY_SIGNATURES

    # The implementation carries proof and narrative as separate slots; this
    # table folds narrative into 'status == complete', so drop the proof slot to
    # compare like with like.
    implemented = {
        (requested, achieved, status, has_classification, has_core, has_reason)
        for requested, achieved, status, has_classification, has_core, _, has_reason in (
            _DELIVERY_SIGNATURES
        )
    }

    assert implemented == set(_AUTHORED_DELIVERY_ROWS)
    # Folding away the proof slot must not have merged two distinct rows.
    assert len(_DELIVERY_SIGNATURES) == len(_AUTHORED_DELIVERY_ROWS)


def test_every_reachable_authored_row_has_a_positive_case() -> None:
    """A rejection matrix alone could pass by refusing everything.

    The cross-product test above is only meaningful if some row survives it, so
    pin that each reachable authored row is genuinely constructible.
    """
    reachable = _AUTHORED_DELIVERY_ROWS - _UNBUILT_DELIVERY_ROWS

    assert reachable, "the delivery matrix would be vacuous"
    for requested, achieved, status, has_classification, has_core, has_reason in sorted(
        reachable
    ):
        explanation = BmcInfeasibilityExplanation(
            requested_mode=requested,
            achieved_mode=achieved,
            status=status,
            classification=(
                "assumptions_self_conflict" if has_classification else None
            ),
            core=(
                _core(
                    "assumptions_component"
                    if has_classification
                    else "assumptions_stage_fallback"
                )
                if has_core
                else None
            ),
            reason="degraded" if has_reason else None,
        )
        assert explanation.achieved_mode == achieved
    # Rows 1, 2 and 3 for each of the two non-'none' requests, plus rows 4/6/7
    # for each request and each classification presence.
    assert len(reachable) == 10


@pytest.mark.parametrize("mode", ["formal", "proof"])
def test_modes_accept_the_frozen_vocabulary(mode) -> None:
    """Only the three frozen mode names are accepted as a request."""
    explanation = BmcInfeasibilityExplanation(
        requested_mode=mode,
        achieved_mode="none",
        status="unknown",
        classification=None,
        reason="probe unknown",
    )

    assert explanation.requested_mode == mode


def test_requesting_none_publishes_no_explanation_object() -> None:
    """``none`` is a mode of the request, never of a published explanation.

    The frozen contract answers a request for ``none`` with ``explanation=None``
    rather than with an object that records the request, so an object claiming
    ``requested_mode='none'`` can only misdescribe what happened.  ``none``
    remains a legal ``achieved_mode``, which is the row above.
    """
    with pytest.raises(ValueError, match="publishes no explanation"):
        BmcInfeasibilityExplanation(
            requested_mode="none",
            achieved_mode="none",
            status="unknown",
            classification=None,
            reason="probe unknown",
        )


@pytest.mark.parametrize("mode", ["None", "FORMAL", "Proof", "full", "", True, 1])
def test_unknown_modes_are_loudly_rejected(mode) -> None:
    """Case variants, bools and unknown strings never pass silently."""
    with pytest.raises(ValueError):
        BmcInfeasibilityExplanation(
            requested_mode=mode,
            achieved_mode="none",
            status="unknown",
            classification=None,
            reason="probe unknown",
        )


def test_proof_and_narrative_stay_absent_in_this_stage() -> None:
    """The container reserves both slots, but this stage never fills them."""
    explanation = BmcInfeasibilityExplanation(
        requested_mode="proof",
        achieved_mode="formal",
        status="partial",
        classification="assumptions_self_conflict",
        core=_core("assumptions_component"),
        reason="proof construction not implemented in this stage",
    )

    assert explanation.proof is None
    assert explanation.narrative is None
    assert issubclass(BmcConflictProof, object)
    assert issubclass(BmcConflictNarrative, object)


def test_core_items_are_sorted_by_stable_id() -> None:
    """Public core ordering is deterministic and never Z3 return order."""
    core = BmcConflictCore(
        scope="assumptions_component",
        formula_summary="ENV_N",
        granularity="source_group",
        reduction="raw",
        subset_minimality="not_proven",
        items=(
            _item("assumption.0002.event.0000", stage="assumptions"),
            _item("assumption.0001.frame.0000", stage="assumptions"),
        ),
    )

    assert [item.constraint.stable_id for item in core.items] == [
        "assumption.0001.frame.0000",
        "assumption.0002.event.0000",
    ]


def test_core_rejects_an_empty_item_tuple() -> None:
    """An empty core proves nothing and must never be published."""
    with pytest.raises(ValueError, match="items"):
        BmcConflictCore(
            scope="assumptions_component",
            formula_summary="ENV_N",
            granularity="source_group",
            reduction="raw",
            subset_minimality="not_proven",
            items=(),
        )


def test_core_rejects_duplicate_stable_ids() -> None:
    """Duplicate labels mean a broken mapping and must fail closed."""
    with pytest.raises(ValueError, match="duplicate"):
        BmcConflictCore(
            scope="assumptions_component",
            formula_summary="ENV_N",
            granularity="source_group",
            reduction="raw",
            subset_minimality="not_proven",
            items=(_item("assumption.0001.frame.0000"),) * 2,
        )


def test_explanation_to_canonical_is_json_compatible() -> None:
    """Canonical output stays plain data for JSON and LLM consumers."""
    explanation = BmcInfeasibilityExplanation(
        requested_mode="formal",
        achieved_mode="formal",
        status="partial",
        classification="assumptions_self_conflict",
        core=_core("assumptions_component"),
        reason="minimization not attempted",
        elapsed_ms=1.5,
    )
    canonical = explanation.to_canonical()

    assert canonical["requested_mode"] == "formal"
    assert canonical["achieved_mode"] == "formal"
    assert canonical["status"] == "partial"
    assert canonical["classification"] == "assumptions_self_conflict"
    assert canonical["proof"] is None
    assert canonical["narrative"] is None
    assert canonical["core"]["scope"] == "assumptions_component"
    assert canonical["core"]["reduction"] == "raw"
    assert canonical["core"]["subset_minimality"] == "not_proven"
    assert canonical["core"]["items"][0]["constraint"]["stable_id"] == "initial.target"


def _explanation():
    """Return the published explanation module, as a caller imports it."""
    from pyfcstm.bmc import explanation

    return explanation


@pytest.mark.parametrize(
    ("call", "expected", "message"),
    [
        # A category or stage a caller assembled from the wrong variable reaches
        # these directly: all four are published with ``autofunction``.
        pytest.param(
            lambda: _explanation().is_printable_ascii(123),
            False,
            None,
            id="printable-ascii-of-a-non-string",
        ),
        pytest.param(
            lambda: _explanation().category_role(123),
            None,
            "belongs to no known family",
            id="role-of-a-non-string-category",
        ),
        pytest.param(
            lambda: _explanation().constraint_aggregate(123, "definedness"),
            None,
            "matches no aggregate",
            id="aggregate-of-a-non-string-stage",
        ),
        pytest.param(
            lambda: _explanation().constraint_aggregate("kernel", 123),
            None,
            "matches no aggregate",
            id="aggregate-of-a-non-string-category",
        ),
        pytest.param(
            lambda: _explanation().index_value("0", "line"),
            None,
            "must contain non-negative integers",
            id="index-of-a-numeric-string",
        ),
    ],
)
def test_the_published_helpers_handle_a_wrong_type(call, expected, message) -> None:
    """The exported helpers answer for a wrong type instead of leaking one.

    Each is published with ``autofunction``, so a caller reaches it directly with
    whatever they have.  ``is_printable_ascii`` answers ``False`` because it is a
    question; the others raise the ``ValueError`` their docstrings promise rather
    than the ``TypeError`` an exact reader would have raised.
    """
    if message is None:
        assert call() is expected
    else:
        with pytest.raises(ValueError, match=message):
            call()


@pytest.mark.parametrize("field", ["stable_id", "category", "summary"])
# An empty value names nothing, whitespace names nothing while looking like it
# does, and a non-string is the other way a caller gets this wrong -- each
# reaches the same field through a different check.
@pytest.mark.parametrize(
    "value", ["", "   ", 123], ids=["empty", "whitespace", "not-a-string"]
)
def test_constraint_rejects_unusable_identity_fields(field, value) -> None:
    """An unnamed constraint could never be traced back to its source."""
    payload = dict(
        stable_id="initial.target",
        stage="initialization",
        category="initial.target",
        source=_GENERATED,
        summary="initial target state",
    )
    payload[field] = value

    # The two refusals word themselves differently -- one names the type, the
    # other the emptiness -- so the assertion pins the field rather than either
    # phrasing.
    with pytest.raises(ValueError, match="constraint %s" % field):
        BmcConstraintRef(**payload)


@pytest.mark.parametrize(
    "stage", ["", 123, "kernels"], ids=["empty", "not-a-string", "near-miss"]
)
def test_constraint_stage_must_name_a_published_stage(stage) -> None:
    """The stage is a closed vocabulary, so anything outside it is refused.

    It is not checked by the identity rule above: an empty stage, a non-string,
    and a plausible near-miss all fail the same way, because what matters is
    whether the value is one of the three published stages.  Accepting any of
    them would publish a ``stage`` the schema does not allow.
    """
    with pytest.raises(ValueError, match="stage must be one of"):
        BmcConstraintRef(
            stable_id="initial.target",
            stage=stage,
            category="initial.target",
            source=_GENERATED,
            summary="initial target state",
        )


def test_constraint_requires_a_real_source_reference() -> None:
    """Provenance is typed so a core member always resolves to a document."""
    with pytest.raises(TypeError, match="BmcSourceRef"):
        BmcConstraintRef(
            stable_id="initial.target",
            stage="initialization",
            category="initial.target",
            source="machine.fcstm",
            summary="initial target state",
        )


def test_core_item_requires_a_typed_constraint_and_a_reading() -> None:
    """Every published member carries both an identity and a sentence."""
    with pytest.raises(TypeError, match="BmcConstraintRef"):
        BmcCoreItem(
            "initial.target",
            "initial_fact",
            None,
            False,
            {"kind": "structural_constraint"},
            "text",
            False,
        )

    with pytest.raises(ValueError, match="human_text"):
        BmcCoreItem(
            _constraint(),
            "initial_fact",
            None,
            False,
            {"kind": "structural_constraint"},
            "",
            False,
        )


def test_core_rejects_an_empty_or_untyped_membership() -> None:
    """A core with no members, or with foreign members, proves nothing."""
    with pytest.raises(ValueError, match="must not be empty"):
        BmcConflictCore(
            "initialization_component", "I_0", "source_group", "raw", "not_proven", ()
        )

    with pytest.raises(TypeError, match="BmcCoreItem"):
        BmcConflictCore(
            "initialization_component",
            "I_0",
            "source_group",
            "raw",
            "not_proven",
            (_constraint(),),
        )

    # An empty summary describes nothing, and a non-string is the other way a
    # caller gets this field wrong.  Both reach the same refusal.
    for unusable_summary in ("", 123):
        with pytest.raises(ValueError, match="formula_summary"):
            BmcConflictCore(
                "initialization_component",
                unusable_summary,
                "source_group",
                "raw",
                "not_proven",
                (_item(),),
            )


@pytest.mark.parametrize(
    "reduction, subset_minimality",
    [
        ("raw", "proven"),
        ("partial_minimized", "proven"),
        ("subset_minimal", "not_proven"),
    ],
)
def test_reduction_and_minimality_stay_coupled(reduction, subset_minimality) -> None:
    """ "Not proven minimal" must never be readable as "proven non-minimal"."""
    with pytest.raises(ValueError, match="subset_minimality"):
        BmcConflictCore(
            "initialization_component",
            "I_0",
            "source_group",
            reduction,
            subset_minimality,
            (_item(),),
        )


def test_core_members_stay_inside_their_scope_target() -> None:
    """A component scope never quotes a stage its target formula excludes.

    A domain or prefix scope legitimately reaches earlier stages, so the check
    is containment in the scope's target, not equality with one stage.
    """
    with pytest.raises(ValueError, match="outside the target"):
        BmcConflictCore(
            "assumptions_component",
            "ENV_N",
            "source_group",
            "raw",
            "not_proven",
            (_item(stage="initialization"),),
        )

    widened = BmcConflictCore(
        "assumptions_prefix",
        "S_assume",
        "source_group",
        "raw",
        "not_proven",
        (_item("initial.target", stage="initialization"),),
    )
    assert widened.items[0].constraint.stage == "initialization"


@pytest.mark.parametrize("elapsed", [-1.0, "fast", True])
def test_elapsed_time_matches_the_published_schema(elapsed) -> None:
    """Timing is a non-negative number so the JSON schema can accept it."""
    with pytest.raises((TypeError, ValueError), match="elapsed_ms"):
        BmcInfeasibilityExplanation(
            "formal", "none", "unknown", None, reason="probe", elapsed_ms=elapsed
        )


def test_explanation_core_slot_is_typed() -> None:
    """The core slot holds a validated core, never a loose mapping."""
    with pytest.raises(TypeError, match="BmcConflictCore"):
        BmcInfeasibilityExplanation(
            "formal", "formal", "partial", None, core={"scope": "kernel"}, reason="r"
        )


def test_achieved_depth_never_exceeds_the_requested_depth() -> None:
    """A run cannot deliver more than the caller asked for."""
    with pytest.raises(ValueError, match="stronger than requested_mode"):
        BmcInfeasibilityExplanation(
            "none", "formal", "partial", "kernel_conflict", _core("kernel"), reason="r"
        )


def test_the_none_depth_publishes_neither_core_nor_completion() -> None:
    """``none`` states that nothing publishable survived."""
    with pytest.raises(ValueError, match="no sound core"):
        BmcInfeasibilityExplanation(
            "formal", "none", "partial", "kernel_conflict", _core("kernel"), reason="r"
        )

    with pytest.raises(ValueError, match="cannot be complete"):
        BmcInfeasibilityExplanation("formal", "none", "complete", None)


def test_the_formal_depth_requires_a_core() -> None:
    """Claiming a formal explanation without a core would be unfalsifiable."""
    with pytest.raises(ValueError, match="requires a core"):
        BmcInfeasibilityExplanation(
            "formal", "formal", "partial", "kernel_conflict", None, reason="r"
        )


def test_the_proof_depth_requires_a_proof() -> None:
    """``proof`` is not deliverable until the proof DAG exists."""
    with pytest.raises(ValueError, match="requires a proof"):
        BmcInfeasibilityExplanation(
            "proof", "proof", "partial", "kernel_conflict", _core("kernel"), reason="r"
        )


def test_a_complete_explanation_requires_a_classification() -> None:
    """Completion without a named cause would explain nothing."""
    with pytest.raises(ValueError, match="classification"):
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "complete",
            None,
            _core("initialization_stage_fallback", "subset_minimal", "proven"),
        )


def test_a_proof_is_only_published_when_proof_was_requested() -> None:
    """A proof slot filled under a weaker request would misreport the run."""
    with pytest.raises(ValueError, match="only published when"):
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "initialization_self_conflict",
            _core(),
            proof=BmcConflictProof("initialization_component", "root"),
            reason="r",
        )


def test_a_reserved_slot_is_rejected_rather_than_silently_dropped() -> None:
    """A filled ``proof`` fails loudly instead of vanishing from the payload.

    The slot belongs to a later delivery stage, and serializing it to ``null``
    would let a caller believe a proof had been published.  ``narrative`` was
    reserved the same way until it gained a builder and a schema; it is now
    accepted, which the delivery tests cover directly.
    """
    with pytest.raises(ValueError, match="not produced at this stage"):
        BmcInfeasibilityExplanation(
            "proof",
            "formal",
            "partial",
            "initialization_self_conflict",
            _core(),
            reason="r",
            proof=BmcConflictProof("initialization_component", "root"),
        )


@pytest.mark.parametrize("bad", [(True,), (-1,), ("0",), (1.5,), (-1.0,)])
def test_frame_and_step_indices_must_be_non_negative_integers(bad) -> None:
    """A published index must survive the JSON contract unchanged.

    ``bool`` is an ``int`` subclass in Python, so an unchecked flag would be
    serialized as ``true`` where the schema promises a number.  A fractional or
    negative value is not an index at all.
    """
    with pytest.raises(ValueError, match="non-negative integers"):
        BmcConstraintRef(
            "initial.target",
            "initialization",
            "initial.target",
            _GENERATED,
            "initial target state",
            frames=bad,
        )

    with pytest.raises(ValueError, match="non-negative integers"):
        BmcConstraintRef(
            "initial.target",
            "initialization",
            "initial.target",
            _GENERATED,
            "initial target state",
            steps=bad,
        )


def test_whole_float_indices_are_accepted_and_canonicalized() -> None:
    """``1.0`` is valid JSON for an integer, so it is accepted and normalized.

    A validator judging ``integer`` by numeric value cannot tell ``1.0`` from
    ``1``, so rejecting it would make the published schema and this constructor
    disagree on a payload that is legal JSON.
    """
    reference = BmcConstraintRef(
        "initial.target",
        "initialization",
        "initial.target",
        _GENERATED,
        "initial target state",
        frames=[1.0, 0.0],
        steps=[2.0],
    )

    assert reference.frames == (1, 0)
    assert reference.steps == (2,)
    assert all(type(value) is int for value in reference.frames + reference.steps)


@pytest.mark.parametrize("field", ["source_excerpt_truncated", "editable"])
def test_core_item_flags_must_be_real_booleans(field) -> None:
    """A truthy non-boolean would publish where JSON needs a boolean."""
    payload = dict(
        constraint=_constraint(),
        semantic_role="initial_fact",
        source_excerpt=None,
        source_excerpt_truncated=False,
        normalized_fact={"kind": "structural_constraint"},
        human_text="initial target state",
        editable=False,
    )
    payload[field] = "yes"

    with pytest.raises(TypeError, match="must be a bool"):
        BmcCoreItem(**payload)


def test_optional_text_fields_reject_non_strings() -> None:
    """An excerpt or a reason is text, so a number is not a quiet substitute."""
    with pytest.raises(TypeError, match="source_excerpt"):
        BmcCoreItem(
            _constraint(),
            "initial_fact",
            123,
            False,
            {"kind": "structural_constraint"},
            "t",
            False,
        )

    with pytest.raises(TypeError, match="reason"):
        BmcInfeasibilityExplanation("formal", "none", "unknown", None, reason=123)


@pytest.mark.parametrize(
    "refs, match",
    [
        ({"frame": {1, 2}}, "not JSON-compatible"),
        ({"frame": object()}, "not JSON-compatible"),
        ({1: "a"}, "keys must be strings"),
        ({"outer": {"inner": {3, 4}}}, "not JSON-compatible"),
        ({"outer": [1, {2, 3}]}, "not JSON-compatible"),
        ({"outer": {2: "b"}}, "keys must be strings"),
    ],
)
def test_structural_metadata_must_survive_json(refs, match) -> None:
    """Free-form metadata still has to be serializable.

    Both mappings go straight into the canonical payload, so an unserializable
    value placed here would not fail until the whole result is dumped, and the
    error would name neither the field nor the object that produced it.
    """
    with pytest.raises(TypeError, match=match):
        BmcConstraintRef(
            "initial.target",
            "initialization",
            "initial.target",
            _GENERATED,
            "initial target state",
            refs=refs,
        )


def test_nested_json_metadata_is_accepted() -> None:
    """Lists, nested mappings and every JSON scalar remain usable."""
    reference = BmcConstraintRef(
        "initial.target",
        "initialization",
        "initial.target",
        _GENERATED,
        "initial target state",
        refs={
            "frame": 0,
            "labels": ["a", "b"],
            "nested": {"flag": True, "ratio": 1.5, "absent": None},
        },
    )
    item = BmcCoreItem(
        reference,
        "initial_fact",
        None,
        False,
        {"kind": "structural_constraint", "stable_id": "initial.target", "frames": [0]},
        "initial target state",
        False,
    )

    assert json.loads(json.dumps(item.to_canonical()))["constraint"]["refs"] == {
        "frame": 0,
        "labels": ["a", "b"],
        "nested": {"flag": True, "ratio": 1.5, "absent": None},
    }


def test_a_hand_built_item_cannot_exceed_the_published_excerpt_bound() -> None:
    """The 4096 bound applies to direct construction, not only to the mapper.

    The orchestration truncates what it publishes, but these dataclasses are
    root exports: a report generator building an item by hand would otherwise
    put an unbounded slice of the user's source into canonical JSON.
    """
    from pyfcstm.bmc.explanation import MAX_SOURCE_EXCERPT_CHARS

    with pytest.raises(ValueError, match="must not exceed"):
        BmcCoreItem(
            _constraint(),
            "initial_fact",
            "x" * (MAX_SOURCE_EXCERPT_CHARS + 1),
            True,
            {"kind": "structural_constraint"},
            "text",
            False,
        )

    at_limit = BmcCoreItem(
        _constraint(),
        "initial_fact",
        "x" * MAX_SOURCE_EXCERPT_CHARS,
        False,
        {"kind": "structural_constraint"},
        "text",
        False,
    )
    assert len(at_limit.source_excerpt) == MAX_SOURCE_EXCERPT_CHARS


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_timings_must_be_finite(value) -> None:
    """A non-finite timing cannot round-trip through strict JSON.

    ``json.dumps`` emits ``NaN`` and ``Infinity`` by default, which are not
    valid JSON, and refuses them under ``allow_nan=False``.  Either way the
    published payload would stop being interchangeable.
    """
    with pytest.raises(ValueError, match="must be finite"):
        BmcInfeasibilityExplanation(
            "formal", "none", "unknown", None, reason="probe", elapsed_ms=value
        )


@pytest.mark.parametrize(
    "value, match",
    [
        (float("nan"), "finite number"),
        (float("inf"), "finite number"),
        ({"nested": float("-inf")}, "finite number"),
        ([], "must be a mapping"),
        ("text", "must be a mapping"),
    ],
)
def test_structural_metadata_rejects_values_json_cannot_carry(value, match) -> None:
    """A mapping field must really be a mapping, and its numbers must be finite.

    ``dict([])`` would silently turn a sequence into an empty mapping, losing
    the caller's data while the JSON contract calls this field an object.
    ``NaN`` and ``Infinity`` are not JSON numbers at all.
    """
    refs = value if isinstance(value, (list, str)) else {"v": value}
    if isinstance(value, dict):
        refs = value

    with pytest.raises((TypeError, ValueError), match=match):
        BmcConstraintRef(
            "initial.target",
            "initialization",
            "initial.target",
            _GENERATED,
            "initial target state",
            refs=refs,
        )


@pytest.mark.parametrize("fact", [{}, {"kind": "bogus"}, {"kind": 1}, {"other": 1}])
def test_a_core_item_must_declare_a_recognized_fact_kind(fact) -> None:
    """The dispatch key machine consumers rely on cannot be absent or invented.

    The frozen contract tells machine readers to branch on ``kind`` rather
    than on human text, so an item without a recognized tag gives them nothing
    to branch on.
    """
    with pytest.raises(ValueError, match="normalized_fact must carry a kind"):
        BmcCoreItem(
            _constraint(),
            "initial_fact",
            None,
            False,
            fact,
            "initial target state",
            False,
        )


def test_a_role_that_contradicts_its_category_is_rejected() -> None:
    """Category decides the reading, so a declared role cannot disagree.

    Machine consumers branch on ``semantic_role`` together with ``category``;
    letting the two disagree would make a domain rule readable as an
    assumption depending on which field the reader trusts.
    """
    with pytest.raises(ValueError, match="contradicts category"):
        BmcCoreItem(
            _constraint(),
            "assumption",
            None,
            False,
            {"kind": "structural_constraint"},
            "initial target state",
            False,
        )


def test_a_generated_constraint_is_not_an_editable_review_surface() -> None:
    """There is no authored line behind a generated conjunct to edit."""
    with pytest.raises(ValueError, match="no authored line"):
        BmcCoreItem(
            _constraint(),
            "initial_fact",
            None,
            False,
            {"kind": "structural_constraint"},
            "initial target state",
            True,
        )


@pytest.mark.parametrize("excerpt", [None, "short", "x" * 4095])
def test_a_declared_truncation_must_show_the_cut(excerpt) -> None:
    """The flag says the excerpt was cut, so the excerpt has to be the cut one."""
    from pyfcstm.bmc.explanation import MAX_SOURCE_EXCERPT_CHARS

    with pytest.raises(ValueError, match="truncated excerpt"):
        BmcCoreItem(
            _constraint(),
            "initial_fact",
            excerpt,
            True,
            {"kind": "structural_constraint"},
            "initial target state",
            False,
        )

    at_bound = BmcCoreItem(
        _constraint(),
        "initial_fact",
        "x" * MAX_SOURCE_EXCERPT_CHARS,
        True,
        {"kind": "structural_constraint"},
        "initial target state",
        False,
    )
    assert at_bound.source_excerpt_truncated is True


def test_scope_membership_separates_the_two_kernel_aggregates() -> None:
    """A domain scope cannot quote a transition group, though both are kernel.

    ``initialization_domain`` targets ``D_N`` and ``I_0`` but not ``T_N``.  A
    stage-level check could not tell them apart because both domain and
    transition groups live in the kernel stage.
    """
    from pyfcstm.bmc.explanation import SCOPE_AGGREGATES

    assert "transition" not in SCOPE_AGGREGATES["initialization_domain"]
    transition = BmcCoreItem(
        BmcConstraintRef(
            "transition.step.0000",
            "kernel",
            "transition.step",
            _GENERATED,
            "step relation",
        ),
        "transition_rule",
        None,
        False,
        {"kind": "structural_constraint"},
        "step relation",
        False,
    )

    with pytest.raises(ValueError, match="outside the target"):
        BmcConflictCore(
            "initialization_domain",
            "L_init",
            "source_group",
            "raw",
            "not_proven",
            (transition,),
        )

    widened = BmcConflictCore(
        "initialization_prefix",
        "L_init",
        "source_group",
        "raw",
        "not_proven",
        (transition,),
    )
    assert widened.items[0].semantic_role == "transition_rule"


@pytest.mark.parametrize(
    "stage, category",
    [
        ("kernel", "assumption.frame"),
        ("kernel", "definedness"),
        ("mystery", "domain.frame_state"),
    ],
)
def test_an_unassignable_group_has_no_aggregate(stage, category) -> None:
    """A pairing the builder never emits must not be guessed into an aggregate.

    Only the kernel stage splits by category, and it splits into exactly domain
    and transition.  Anything else means a new group family arrived without a
    decision about which formula contains it.
    """
    from pyfcstm.bmc.explanation import constraint_aggregate

    with pytest.raises(ValueError, match="aggregate|domain nor a transition"):
        constraint_aggregate(stage, category)


def test_every_produced_pairing_resolves_to_one_aggregate() -> None:
    """The pairings the builder does emit each land in exactly one aggregate."""
    from pyfcstm.bmc.explanation import constraint_aggregate

    assert constraint_aggregate("kernel", "domain.frame_state") == "domain"
    assert constraint_aggregate("kernel", "transition.case") == "transition"
    assert constraint_aggregate("initialization", "initial.where") == "initial"
    assert constraint_aggregate("initialization", "definedness") == "initial"
    assert constraint_aggregate("assumptions", "assumption.event") == "environment"
    assert constraint_aggregate("assumptions", "definedness") == "environment"


@pytest.mark.parametrize("stable_id", ["冲突", "assumé", "id with nbsp"])
def test_a_stable_id_must_be_printable_ascii(stable_id) -> None:
    """Stable ids stay printable ASCII because they name things elsewhere.

    Each id is generated from a fixed category/index/path encoding and is used
    downstream as a solver literal name and as a JSON key, so letting a model
    identifier through would put its round-tripping outside this contract.

    ``str.isascii`` is deliberately not the test: it admits control characters,
    which the published pattern rejects, so the two boundaries would disagree.
    """
    with pytest.raises(ValueError, match="must be printable ASCII"):
        BmcConstraintRef(
            stable_id,
            "initialization",
            "initial.target",
            _GENERATED,
            "initial target state",
        )


#: One well-formed argument set per published dataclass.
#:
#: The values are authored, but the *field list* is not: each sweep below reads
#: the dataclass's own fields and requires every one of them to appear here, so a
#: newly added field fails the sweep until it is given a value.
#: A feasibility check the constructor accepts, used as the well-formed value
#: for the three required check fields of BmcFeasibilityResult.
def _feasibility_check():
    from pyfcstm.bmc.witness import BmcFeasibilityCheck

    return BmcFeasibilityCheck("unsat", "checked", elapsed_ms=1.0)


@pytest.mark.unittest
def test_human_vocabularies_are_transcribed_from_the_frozen_transcripts() -> None:
    """Both human vocabularies, copied verbatim, not paraphrased.

    Rewriting a frozen phrase from memory produces text that reads correctly and
    passes every test that uses the same rewritten constant, so the only check
    that can catch it is a transcription compared against the governing transcript.

    The published transcripts give two different phrasings for one
    classification: one says "assumptions conflict with the initialized
    transition prefix" and the other "assumptions conflict with the feasible
    prefix", both under identical scenario and core-scope lines that map to
    ``assumptions_prefix_conflict`` alone.  The implementation has to pick one,
    and that choice is recorded here rather than left implicit.
    """
    from pyfcstm.bmc.explanation import (
        CLASSIFICATION_PHRASES,
        CLASSIFICATION_SCOPES,
        EXPLANATION_HEADLINES,
    )

    # Three of the four are sampled by a transcript.  The partial proof row is
    # not; it follows the same two-word substitution the sampled proof row uses.
    assert EXPLANATION_HEADLINES == {
        ("formal", "complete"): "COMPLETE FORMAL DOMAIN EXPLANATION",
        ("formal", "partial"): "PARTIAL FORMAL DOMAIN EXPLANATION",
        ("proof", "complete"): "COMPLETE VERIFIED DOMAIN PROOF",
        ("proof", "partial"): "PARTIAL VERIFIED DOMAIN PROOF",
    }

    # The two frozen phrasings for assumptions_prefix_conflict, transcribed.
    frozen_prefix_phrasings = (
        "assumptions conflict with the initialized transition prefix",
        "assumptions conflict with the feasible prefix",
    )
    assert CLASSIFICATION_PHRASES["assumptions_prefix_conflict"] in (
        frozen_prefix_phrasings
    )
    # The classification line of the not-achieved transcript.
    assert (
        CLASSIFICATION_PHRASES["initialization_self_conflict"]
        == "initialization is internally inconsistent"
    )
    # Every classification has a phrase, and no phrase is left empty or
    # duplicated onto two classifications.
    assert set(CLASSIFICATION_PHRASES) == set(CLASSIFICATION_SCOPES)
    assert all(phrase.strip() for phrase in CLASSIFICATION_PHRASES.values())
    assert len(set(CLASSIFICATION_PHRASES.values())) == len(CLASSIFICATION_PHRASES)


@pytest.mark.unittest
def test_reserved_placeholder_fields_are_pinned() -> None:
    """Pin the field lists of the published narrative and the reserved proof.

    ``proof`` cannot be carried by a published explanation yet, but it is
    exported, documented and constructible, so a field added to it would reach
    the published surface with nothing describing it.  The narrative is published
    now, which makes its field list part of the contract rather than a
    placeholder.
    """
    import dataclasses

    from pyfcstm.bmc.explanation import (
        UNBUILT_SLOTS,
        BmcConflictNarrative,
        BmcConflictProof,
        BmcReasoningStep,
    )

    assert set(UNBUILT_SLOTS) == {"proof"}
    assert [f.name for f in dataclasses.fields(BmcConflictNarrative)] == [
        "derivation_status",
        "headline",
        "summary",
        "reasoning_steps",
        "review_surfaces",
    ]
    assert [f.name for f in dataclasses.fields(BmcReasoningStep)] == [
        "kind",
        "item_ids",
        "proof_node_ids",
        "text",
    ]
    assert [f.name for f in dataclasses.fields(BmcConflictProof)] == [
        "scope",
        "root_id",
    ]
    # Both remain refused on a published explanation, which is what makes the
    # sweep's skip correct rather than merely convenient.  The two are refused for
    # different reasons, so each is checked against its own message.
    from pyfcstm.bmc.explanation import BmcInfeasibilityExplanation

    core = BmcConflictCore(
        "initialization_component",
        "C_init restricted to the conflicting groups",
        "source_group",
        "raw",
        "not_proven",
        (
            BmcCoreItem(
                BmcConstraintRef(
                    "initial.variable.x",
                    "initialization",
                    "initial.variable",
                    BmcSourceRef("generated", None, None),
                    "initial fact",
                    refs={"frame": 0},
                ),
                "initial_fact",
                None,
                False,
                {"kind": "structural_constraint"},
                "initial fact",
                False,
            ),
        ),
    )
    with pytest.raises(ValueError, match="only published when 'proof' was requested"):
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "initialization_self_conflict",
            core=core,
            reason="sound source core published without a minimality proof",
            proof=BmcConflictProof("initialization_component", "root"),
        )
    # The narrative slot is published now, so a degraded artifact may carry the
    # honest structural reading beside its unproven core.
    accepted = BmcInfeasibilityExplanation(
        "formal",
        "formal",
        "partial",
        "initialization_self_conflict",
        core=core,
        reason="sound source core published without a minimality proof",
        narrative=BmcConflictNarrative("structural_only", "headline", "summary"),
    )
    assert accepted.narrative.derivation_status == "structural_only"


@pytest.mark.parametrize(
    "elapsed_ms",
    ["1.5", [], True, float("nan"), float("inf")],
    ids=["string", "list", "bool", "nan", "inf"],
)
def test_an_elapsed_duration_must_be_a_real_finite_number(elapsed_ms) -> None:
    """A duration is published as a JSON number, so only a real one is stored.

    A caller assembling an explanation passes whatever their clock gave them.  A
    string, a container, a ``bool``, or a non-finite float would each reach the
    published JSON as something no consumer of the schema can read as a duration.
    """
    with pytest.raises((TypeError, ValueError), match="elapsed_ms"):
        BmcInfeasibilityExplanation(
            requested_mode="formal",
            achieved_mode="none",
            status="partial",
            classification="assumptions_self_conflict",
            reason="raw core unknown",
            elapsed_ms=elapsed_ms,
        )


@pytest.mark.unittest
def test_a_published_item_reads_as_a_sentence_about_the_model() -> None:
    """``human_text`` states the domain fact, not the group's identifier.

    A reader who does not know the encoding gets nothing from
    "assumption constraint assumption.0000.frame.0000 from q.fbmcq".  The frozen
    prototype renders the same item as a sentence naming the frame, the variable
    and the value, and that is what the recognized facts now make possible.
    """
    from pyfcstm.bmc.explanation import human_text_for_fact

    assumption = human_text_for_fact(
        "assumption",
        {
            "kind": "variable_comparison",
            "variable": "x",
            "frame": 0,
            "operator": "eq",
            "value": 1,
        },
    )
    assert assumption == "At frame 0, the query requires x to equal 1."

    initial = human_text_for_fact(
        "initial_fact",
        {
            "kind": "variable_comparison",
            "variable": "x",
            "frame": 0,
            "operator": "eq",
            "value": 0,
        },
    )
    assert initial == "At frame 0, the initializer requires x to equal 0."

    bounded = human_text_for_fact(
        "assumption",
        {
            "kind": "variable_comparison",
            "variable": "x",
            "frame": 2,
            "operator": "lt",
            "value": 3,
        },
    )
    assert bounded == "At frame 2, the query requires x to be less than 3."

    # A shape no recognizer read must not be dressed up as a domain sentence.
    structural = human_text_for_fact(
        "transition_rule",
        {
            "kind": "structural_constraint",
            "stable_id": "transition.0000.step.0000",
            "stage": "kernel",
            "category": "transition.step",
        },
    )
    # It describes the group rather than claiming a requirement it never derived.
    assert "transition rule" in structural
    assert "requires" not in structural
    assert structural.endswith(".")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "values, empty",
    [
        ((("gt", 0), ("lt", 1)), True),
        ((("gt", 0.0), ("lt", 1.0)), False),
        ((("gt", 1.0), ("le", 1.0)), True),
        ((("ge", 1.0), ("le", 1.0)), False),
        ((("ne", 1), ("ge", 0)), False),
    ],
    ids=[
        "integers-admit-nothing-between-0-and-1",
        "reals-admit-plenty-between-0-and-1",
        "reals-meeting-at-an-excluded-point",
        "reals-meeting-at-an-included-point",
        "excluding-one-value-empties-nothing",
    ],
)
def test_an_interval_is_read_over_the_variable_domain_it_belongs_to(
    values, empty
) -> None:
    """The same two bounds mean different things over integers and reals.

    ``x > 0`` with ``x < 1`` admits nothing over the integers and every value
    between them over the reals, and the recognizer marks which domain it is in
    by publishing whole real values as floats.

    What this protects is the helper's own stated contract, not a currently
    reachable verdict.  A published core is always unsatisfiable, and on a core
    whose members are all bounds on one variable "no value satisfies them"
    already follows from that -- integer tightening only ever shrinks an
    interval, so on such a core it can reach a wrong conclusion by a wrong route
    but not a wrong answer.  The compatible cases below therefore cannot arrive
    through the orchestrator today.  They are pinned because the function says it
    reports whether bounds admit a value, and the next caller -- proof mode, or a
    conjunction group -- will be entitled to believe that sentence.
    """
    from pyfcstm.bmc.explanation import _interval_is_empty

    def member(operator, value):
        reference = BmcConstraintRef(
            "assumption.%s.%s" % (operator, value),
            "assumptions",
            "assumption.frame",
            BmcSourceRef("generated", None, None),
            "bound",
            frames=(0,),
            refs={"frame": 0},
        )
        return BmcCoreItem(
            reference,
            "assumption",
            None,
            False,
            {
                "kind": "variable_comparison",
                "variable": "x",
                "frame": 0,
                "operator": operator,
                "value": value,
            },
            "bound",
            False,
        )

    items = tuple(member(operator, value) for operator, value in values)

    assert _interval_is_empty(items) is empty


def _published_core_and_narrative():
    """Return a real published core plus a narrative that matches it."""
    from pyfcstm.bmc import (
        BmcEngine,
        build_bmc_core_formula,
        compile_bmc_property,
        solve_bmc_property,
    )
    from pyfcstm.model import load_state_machine_from_text

    context = BmcEngine(
        load_state_machine_from_text("def int x = 0; state Root;")
    ).prepare(
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 1: active("Root");'
    )
    explanation = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="formal",
    ).feasibility.explanation
    return explanation.core, explanation.narrative


@pytest.mark.unittest
def test_a_complete_verdict_requires_a_derivation_that_closed() -> None:
    """``status="complete"`` may not sit on a narrative that gave up.

    The frozen delivery row asks for a *complete* narrative, not merely a present
    one.  Accepting ``structural_only`` there publishes full confidence over an
    account that says outright it could not derive the conflict.
    """
    from pyfcstm.bmc.explanation import (
        BmcConflictNarrative,
        BmcInfeasibilityExplanation,
    )

    core, _ = _published_core_and_narrative()

    with pytest.raises(ValueError, match="complete narrative"):
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "complete",
            "assumptions_self_conflict",
            core=core,
            narrative=BmcConflictNarrative("structural_only", "headline", "summary"),
        )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "field, message",
    [
        ("reasoning_steps", "reasoning step"),
        ("review_surfaces", "review surface"),
    ],
    ids=["step-cites-a-member-that-is-not-there", "surface-offers-a-missing-member"],
)
def test_a_narrative_may_only_reference_the_core_beside_it(field, message) -> None:
    """Every id a narrative publishes has to exist in the core it describes.

    A step citing an absent member sends a reader to a line the report never
    listed, and a review surface offering one points at nothing to edit.  Neither
    can be checked inside the narrative, which cannot see the core, so the class
    that holds both is where the check belongs.
    """
    from pyfcstm.bmc.explanation import (
        BmcConflictNarrative,
        BmcInfeasibilityExplanation,
        BmcReasoningStep,
    )

    core, good = _published_core_and_narrative()
    if field == "reasoning_steps":
        broken = BmcConflictNarrative(
            good.derivation_status,
            good.headline,
            good.summary,
            good.reasoning_steps
            + (BmcReasoningStep("fact", ("absent.member",), (), "text"),),
            good.review_surfaces,
        )
    else:
        broken = BmcConflictNarrative(
            good.derivation_status,
            good.headline,
            good.summary,
            good.reasoning_steps,
            good.review_surfaces + ("absent.member",),
        )

    with pytest.raises(ValueError, match=message):
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "complete",
            "assumptions_self_conflict",
            core=core,
            narrative=broken,
        )


@pytest.mark.unittest
def test_a_review_surface_must_be_a_member_the_reader_can_edit() -> None:
    """Offering a generated rule for review points at no authored line.

    ``editable=False`` means the encoding produced the member, so there is no
    file and no span for the reader to open.  Listing it as a review surface
    would send them looking for something that does not exist.
    """
    from pyfcstm.bmc.explanation import (
        BmcConflictNarrative,
        BmcInfeasibilityExplanation,
    )

    core, good = _published_core_and_narrative()
    # Publish an existing member that the core marks as not editable.
    non_editable = [item for item in core.items if not item.editable]
    if not non_editable:
        pytest.skip("this corpus publishes only authored members")

    broken = BmcConflictNarrative(
        good.derivation_status,
        good.headline,
        good.summary,
        good.reasoning_steps,
        (non_editable[0].constraint.stable_id,),
    )

    with pytest.raises(ValueError, match="editable"):
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "complete",
            "assumptions_self_conflict",
            core=core,
            narrative=broken,
        )


def _guard_item(variable, frame=0, operation="division"):
    """A definedness member guarding one variable at one frame."""
    fact = {"kind": "definedness_condition", "frame": frame, "operation": operation}
    if variable is not None:
        fact["variable"] = variable
    reference = BmcConstraintRef(
        "definedness.%s.%s" % (variable, frame),
        "assumptions",
        "definedness",
        BmcSourceRef("generated", None, None),
        "guard",
        frames=(frame,),
        refs={"frame": frame},
    )
    return BmcCoreItem(reference, "definedness", None, False, fact, "guard", False)


def _comparison_item(variable, frame=0, operator="eq", value=0):
    """A comparison member on one variable at one frame."""
    reference = BmcConstraintRef(
        "assumption.%s.%s.%s" % (variable, frame, value),
        "assumptions",
        "assumption.frame",
        BmcSourceRef("generated", None, None),
        "bound",
        frames=(frame,),
        refs={"frame": frame},
    )
    return BmcCoreItem(
        reference,
        "assumption",
        None,
        False,
        {
            "kind": "variable_comparison",
            "variable": variable,
            "frame": frame,
            "operator": operator,
            "value": value,
        },
        "bound",
        False,
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "members, named",
    [
        ((("guard", "x", 0), ("cmp", "x", 0)), True),
        ((("guard", "x", 0), ("cmp", "y", 0)), False),
        ((("guard", "x", 0), ("cmp", "x", 1)), False),
        ((("guard", None, 0), ("cmp", "x", 0)), False),
        ((("guard", "x", 0), ("guard", "y", 0), ("cmp", "x", 0)), False),
    ],
    ids=[
        "the-facts-are-about-the-guarded-variable",
        "the-facts-are-about-another-variable",
        "the-facts-are-about-another-frame",
        "the-guard-does-not-name-its-variable",
        "two-guards-leave-it-ambiguous",
    ],
)
def test_a_definedness_failure_is_claimed_only_when_the_facts_explain_it(
    members, named
) -> None:
    """Relaxing the pattern must not let it explain a conflict it did not cause.

    A domain condition in a subset-minimal core is load-bearing, but that alone
    does not make it *the* story: if the facts beside it constrain a different
    variable or a different frame, the contradiction is somewhere else and naming
    the operation would misattribute it.  The pattern therefore claims the
    failure only when every other member speaks about the variable the guard
    protects, at the frame it protects.
    """
    from pyfcstm.bmc.explanation import _conflict_pattern

    items = tuple(
        _guard_item(name, frame) if kind == "guard" else _comparison_item(name, frame)
        for kind, name, frame in members
    )

    # The branch reasons from every member being load-bearing, so it is only
    # offered for a proven-minimal core; the raw case has its own test.
    pattern = _conflict_pattern(items, "proven")

    if named:
        assert pattern is not None
        assert pattern[0] == "definedness_failure"
    else:
        assert pattern is None or pattern[0] != "definedness_failure"


@pytest.mark.unittest
def test_a_redundant_guard_is_not_reported_as_the_reason() -> None:
    """The load-bearing argument needs the minimality it argues from.

    The relaxed branch reasons that a domain condition inside a subset-minimal
    core must be part of the contradiction.  That is true of a *proven* core and
    false of a raw one, where a redundant member can ride along: here ``x != 0``
    is compatible with either equality and dropping it leaves the rest
    unsatisfiable, so the division is not why anything failed.  Publishing it as
    the cause is the exact failure this mode exists to avoid -- a sentence that
    reads like an explanation and points at the wrong line.
    """
    from pyfcstm.bmc.explanation import build_conflict_narrative

    core = BmcConflictCore(
        "assumptions_component",
        "target",
        "source_group",
        "raw",
        "not_proven",
        (
            _guard_item("x"),
            _comparison_item("x", value=1),
            _comparison_item("x", value=2),
        ),
    )

    narrative = build_conflict_narrative(core)

    assert "division" not in narrative.headline
    # The equalities are still readable, so the honest reading is available.
    assert narrative.derivation_status in ("complete", "structural_only")
    if narrative.derivation_status == "complete":
        assert "cannot assign" in narrative.headline


def _domain_item(frame, states):
    """A published domain member listing a frame's legal states."""
    reference = BmcConstraintRef(
        "domain.frame.%s" % frame,
        "kernel",
        "domain.frame_state",
        BmcSourceRef("generated", None, None),
        "domain",
        frames=(frame,),
        refs={"frame": frame},
    )
    return BmcCoreItem(
        reference,
        "domain_rule",
        None,
        False,
        {"kind": "state_domain", "frame": frame, "states": list(states)},
        "domain",
        False,
    )


def _state_item(frame, state, excluded):
    """A published state member either requiring or ruling out one state."""
    reference = BmcConstraintRef(
        "state.%s.%s.%s" % (frame, state, excluded),
        "assumptions",
        "assumption.frame",
        BmcSourceRef("generated", None, None),
        "state",
        frames=(frame,),
        refs={"frame": frame},
    )
    return BmcCoreItem(
        reference,
        "assumption",
        None,
        False,
        {
            "kind": "state_membership",
            "frame": frame,
            "state": state,
            "excluded": excluded,
        },
        "state",
        False,
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "domain, states, exhausted",
    [
        ((1, (-1, 1, 2)), ((1, -1, True), (1, 1, True), (1, 2, True)), True),
        ((1, (-1, 1, 2)), ((1, 1, True), (1, 2, True)), False),
        ((1, (-1, 1)), ((0, -1, True), (0, 1, True)), False),
        ((1, (1,)), ((1, 7, True),), False),
        ((1, (1,)), ((1, 1, True), (1, 9, True)), True),
        ((1, (1, 2)), ((1, 1, False), (1, 2, False)), False),
    ],
    ids=[
        "every-legal-state-is-ruled-out",
        "one-legal-state-still-remains",
        "the-exclusions-are-about-another-frame",
        "the-exclusion-names-a-state-outside-the-domain",
        "a-spare-exclusion-does-not-change-the-answer",
        "requirements-are-not-exclusions",
    ],
)
def test_exhaustion_is_claimed_only_when_the_domain_is_actually_empty(
    domain, states, exhausted
) -> None:
    """Emptying a frame is checked against the published domain, not counted.

    The sentence claims the frame has nothing left to be, so it has to follow
    from the legal states the core actually published: exclusions about another
    frame, or naming a state the domain never allowed, leave the frame with
    somewhere to go.  Reading a requirement as an exclusion would invert the
    source line and reach the same wrong conclusion from the other direction.
    """
    from pyfcstm.bmc.explanation import _conflict_pattern

    items = (_domain_item(*domain),) + tuple(
        _state_item(frame, state, excluded) for frame, state, excluded in states
    )

    pattern = _conflict_pattern(items, "proven")

    if exhausted:
        assert pattern is not None
        assert pattern[0] == "state_domain_exhaustion"
    else:
        assert pattern is None or pattern[0] != "state_domain_exhaustion"


@pytest.mark.unittest
def test_a_narrative_needs_the_core_it_talks_about() -> None:
    """No sound core means no causal chain to tell.

    ``achieved_mode="none"`` says nothing publishable came back, and the frozen
    not-achieved transcript spells out that no conflict core or causal chain was
    published.  A narrative beside a missing core also escapes the reference
    check, which can only run when there is a core to check against, so its ids
    point at nothing by construction.
    """
    from pyfcstm.bmc.explanation import (
        BmcConflictNarrative,
        BmcInfeasibilityExplanation,
        BmcReasoningStep,
    )

    narrative = BmcConflictNarrative(
        "structural_only",
        "headline",
        "summary",
        (BmcReasoningStep("fact", ("g0",), (), "text"),),
        (),
    )

    with pytest.raises(ValueError, match="narrative"):
        BmcInfeasibilityExplanation(
            "formal",
            "none",
            "unknown",
            None,
            narrative=narrative,
            reason="probe unknown",
        )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "ids", [(1,), (None,), (b"g0",)], ids=["integer", "none", "bytes"]
)
def test_a_reasoning_step_publishes_only_string_ids(ids) -> None:
    """A published id is a string, and the constructor is where that is decided.

    The schema types these arrays as strings, so a non-string element reaches
    canonical JSON that a conforming validator refuses -- the constructor
    accepting what the schema rejects, which is the opposite direction from every
    named exception and belongs to none of them.
    """
    from pyfcstm.bmc.explanation import BmcReasoningStep

    with pytest.raises((TypeError, ValueError)):
        BmcReasoningStep("fact", ids, (), "text")


@pytest.mark.unittest
def test_a_published_id_is_never_blank() -> None:
    """The schema gives these ids ``minLength: 1``, so the constructor must too.

    An empty id names nothing and reaches canonical JSON a conforming validator
    refuses -- the constructor accepting what the schema rejects, in the opposite
    direction from every named exception.
    """
    from pyfcstm.bmc.explanation import BmcReasoningStep

    with pytest.raises(ValueError, match="must not be blank"):
        BmcReasoningStep("fact", ("",), (), "text")


@pytest.mark.unittest
def test_proof_node_references_need_a_proof_to_reference() -> None:
    """Outside proof mode there are no nodes, so a step cannot cite one.

    ``BmcReasoningStep`` documents ``proof_node_ids`` as empty outside proof mode
    and the PR states the same, but nothing enforced it: a formal explanation
    could publish steps pointing at nodes no artifact contains.
    """
    from pyfcstm.bmc.explanation import (
        BmcConflictNarrative,
        BmcInfeasibilityExplanation,
        BmcReasoningStep,
    )

    core, good = _published_core_and_narrative()
    ghosted = BmcConflictNarrative(
        good.derivation_status,
        good.headline,
        good.summary,
        tuple(
            BmcReasoningStep(step.kind, step.item_ids, ("ghost.proof.node",), step.text)
            for step in good.reasoning_steps
        ),
        good.review_surfaces,
    )

    with pytest.raises(ValueError, match="proof"):
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "complete",
            "assumptions_self_conflict",
            core=core,
            narrative=ghosted,
        )


def _propagation_item(stable_id, stage, variable, value):
    """A comparison member on one variable, in the stage its category implies."""
    category = "initial.variable" if stage == "initialization" else "assumption.frame"
    role = "initial_fact" if stage == "initialization" else "assumption"
    reference = BmcConstraintRef(
        stable_id,
        stage,
        category,
        BmcSourceRef("generated", None, None),
        "member",
        frames=(0,),
        refs={"frame": 0},
    )
    return BmcCoreItem(
        reference,
        role,
        None,
        False,
        {
            "kind": "variable_comparison",
            "variable": variable,
            "frame": 0,
            "operator": "eq",
            "value": value,
        },
        "member",
        False,
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "spare_member, forced_values, speaks",
    [
        (False, ((0,),), False),
        (False, ((7,),), True),
        (True, ((0,), (5,)), False),
    ],
    ids=[
        "the-derivation-would-restate-a-supporting-fact",
        "the-derivation-adds-something-the-facts-do-not-state",
        "a-later-candidate-cannot-speak-past-an-unexplained-member",
    ],
)
def test_stepping_aside_never_turns_into_speaking_up(
    spare_member, forced_values, speaks
) -> None:
    """The two skips must end in silence, not in a later candidate speaking.

    Both guards ``continue`` rather than return, so they move on to the next
    forced value.  A candidate skipped for restating a fact must not be followed
    by one that speaks while a member stays unexplained -- the loop has to run out
    and hand the core to the single-shape patterns.
    """
    from pyfcstm.bmc.explanation import _propagation_steps
    from pyfcstm.bmc.infeasibility import ForcedValue

    items = [
        _propagation_item("prefix.x", "initialization", "x", 0),
        _propagation_item("assume.x", "assumptions", "x", 1),
    ]
    if spare_member:
        items.append(_propagation_item("assume.y", "assumptions", "y", 9))
    core = BmcConflictCore(
        "assumptions_prefix",
        "target",
        "source_group",
        "raw",
        "not_proven",
        tuple(items),
    )
    forced = tuple(
        ForcedValue("x", 0, value, ("prefix.x",)) for (value,) in forced_values
    )

    result = _propagation_steps(core, forced)

    assert (result is not None) is speaks


@pytest.mark.unittest
@pytest.mark.parametrize(
    "code, paths, rendered",
    [
        (1, {1: "Root.A"}, "state Root.A"),
        (5, {5: "Root.Outer.Inner"}, "state Root.Outer.Inner"),
        (-1, {-1: "$STATE_TERMINATE"}, "state $STATE_TERMINATE"),
        (9, {1: "Root.A"}, "state 9"),
        (1, None, "state 1"),
        (1, {}, "state 1"),
    ],
    ids=[
        "a-state-the-table-knows",
        "a-nested-path",
        "a-sentinel",
        "a-code-the-table-does-not-know",
        "no-table-at-all",
        "an-empty-table",
    ],
)
def test_a_state_falls_back_to_its_code_rather_than_inventing_a_name(
    code, paths, rendered
) -> None:
    """Naming a state is a lookup, and a miss must not become a guess.

    The path is what the reader wrote and is worth printing, but a code the
    table does not carry has no name to print.  Falling back to the code keeps
    the sentence true and still traceable through ``normalized_fact``; inventing
    one would put a state in the report that the model does not contain.
    """
    from pyfcstm.bmc.explanation import _state_label

    assert _state_label(code, paths) == rendered


@pytest.mark.unittest
def test_every_published_field_documents_the_type_it_is_annotated_with() -> None:
    """A field's annotation and its ``:type:`` line are two exits for one fact.

    Five fields were annotated with their frozen ``Literal`` while the docstring
    beside them still said ``str``, so a caller reading the rendered API page saw
    a weaker type than the one the code declares -- and had no way to discover the
    vocabulary.  Enumerating the dataclasses keeps that from drifting again
    silently, which is how it arose: the annotations were tightened one at a time
    and the prose was not.
    """
    import inspect
    import re

    from pyfcstm.bmc import explanation as explanation_module
    from pyfcstm.bmc import infeasibility as infeasibility_module

    published = [
        explanation_module.BmcReasoningStep,
        explanation_module.BmcConflictNarrative,
        explanation_module.BmcCoreItem,
        explanation_module.BmcConflictCore,
        explanation_module.BmcConstraintRef,
        explanation_module.BmcInfeasibilityExplanation,
        infeasibility_module.ForcedValue,
        infeasibility_module.MinimizedCore,
        infeasibility_module.ProbeRecord,
    ]

    mismatched = []
    for cls in published:
        doc = inspect.getdoc(cls) or ""
        for field in cls.__dataclass_fields__.values():
            documented = re.search(r":type %s:\s*(.+)" % re.escape(field.name), doc)
            if documented is None:
                mismatched.append("%s.%s has no :type:" % (cls.__name__, field.name))
                continue
            annotation = str(field.type).replace("typing.", "")
            # The head of the annotation is the name that matters: ``Tuple[X, ...]``
            # documents as ``Tuple[X, ...]``, and ``Optional[X]`` as ``X, optional``.
            names = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", annotation)[:2]
            if names and not any(name in documented.group(1) for name in names):
                mismatched.append(
                    "%s.%s annotated %s, documented %s"
                    % (cls.__name__, field.name, annotation, documented.group(1))
                )

    assert mismatched == []


@pytest.mark.unittest
def test_no_published_text_field_accepts_whitespace() -> None:
    """One rule about blank text, one predicate, every exit.

    These six fields had grown three different emptiness tests -- ``.strip()``,
    ``if not text`` and plain truthiness -- so ``"   "`` was refused in three
    places and published in the other three, and the schema's ``minLength``
    agreed with neither.  Whitespace is the input that separates the readings, so
    it is the one worth enumerating: a field added later that invents a fourth
    test fails here rather than quietly becoming the seventh exit.
    """
    from pyfcstm.bmc.explanation import (
        BmcConflictCore,
        BmcConflictNarrative,
        BmcConstraintRef,
        BmcCoreItem,
        BmcInfeasibilityExplanation,
        BmcReasoningStep,
    )

    blank = "   "
    reference = BmcConstraintRef(
        "g0",
        "assumptions",
        "assumption.frame",
        BmcSourceRef("generated", None, None),
        "summary",
    )
    item = BmcCoreItem(
        reference,
        "assumption",
        None,
        False,
        {"kind": "structural_constraint"},
        "t",
        False,
    )

    builders = {
        "reasoning step text": lambda: BmcReasoningStep("fact", ("g0",), (), blank),
        "reasoning step item_ids entry": lambda: BmcReasoningStep(
            "fact", (blank,), (), "t"
        ),
        "reasoning step proof_node_ids entry": lambda: BmcReasoningStep(
            "fact", ("g0",), (blank,), "t"
        ),
        "narrative headline": lambda: BmcConflictNarrative(
            "structural_only", blank, "summary"
        ),
        "narrative summary": lambda: BmcConflictNarrative(
            "structural_only", "headline", blank
        ),
        "core formula_summary": lambda: BmcConflictCore(
            "assumptions_component",
            blank,
            "source_group",
            "raw",
            "not_proven",
            (item,),
        ),
        "core item human_text": lambda: BmcCoreItem(
            reference,
            "assumption",
            None,
            False,
            {"kind": "structural_constraint"},
            blank,
            False,
        ),
        "constraint summary": lambda: BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            BmcSourceRef("generated", None, None),
            blank,
        ),
        # The ninth field, and the one an earlier count of "all eight" excluded.
        # A degraded artifact's reason is printed on the report's ``Reason:`` line.
        "explanation reason": lambda: BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "assumptions_self_conflict",
            core=BmcConflictCore(
                "assumptions_component",
                "F",
                "source_group",
                "raw",
                "not_proven",
                (item,),
            ),
            reason=blank,
        ),
    }

    accepted = []
    for where, build in builders.items():
        try:
            build()
        except ValueError:
            continue
        accepted.append(where)

    assert accepted == []


@pytest.mark.unittest
def test_the_shared_text_predicate_documents_both_refusals() -> None:
    """A caller distinguishing the two failures needs both named.

    The predicate refuses a non-``str`` through ``exact_str`` before emptiness is
    considered, so the two inputs raise different classes.  Documenting only one
    is the mirror of a comment claiming more than the code does: here the prose
    claimed less, and a caller catching ``ValueError`` alone would miss half of
    it.
    """
    import inspect

    from pyfcstm.bmc.explanation import require_published_text

    doc = inspect.getdoc(require_published_text) or ""
    assert ":raises TypeError:" in doc
    assert ":raises ValueError:" in doc

    with pytest.raises(TypeError):
        require_published_text(123, "field")
    with pytest.raises(ValueError):
        require_published_text("   ", "field")


@pytest.mark.unittest
def test_a_frozen_narrative_keeps_the_members_it_was_validated_with() -> None:
    """``frozen=True`` stops rebinding, not emptying the list behind the field.

    Every invariant here reads a sequence the caller supplied, so a caller that
    keeps its own reference can satisfy each check and then remove exactly what
    the checks were about -- leaving a ``complete`` narrative with no conflict
    step and a step citing nothing.  ``BmcConflictCore.items`` has always copied
    on the way in; these four fields had not.
    """
    from pyfcstm.bmc.explanation import BmcConflictNarrative, BmcReasoningStep

    item_ids = ["g0"]
    node_ids = ["n0"]
    step = BmcReasoningStep("conflict", item_ids, node_ids, "closing")
    steps = [step]
    surfaces = ["g0"]
    narrative = BmcConflictNarrative("complete", "headline", "summary", steps, surfaces)

    item_ids.clear()
    node_ids.clear()
    steps.clear()
    surfaces.clear()

    assert step.item_ids == ("g0",)
    assert step.proof_node_ids == ("n0",)
    assert narrative.reasoning_steps == (step,)
    assert narrative.review_surfaces == ("g0",)
    # And the invariant the copies protect still holds afterwards.
    assert [s for s in narrative.reasoning_steps if s.kind == "conflict"]


@pytest.mark.unittest
def test_a_skipped_operator_does_not_count_as_explained() -> None:
    """Coverage means the members bear on the conclusion, not that they were counted.

    ``ne`` is deliberately left out of the interval arithmetic, because excluding
    one value never empties a range.  A core carrying one therefore satisfied the
    sibling coverage count while contributing nothing, so the conflict step listed
    a member the sentence does not rest on.
    """
    from pyfcstm.bmc.explanation import _conflict_pattern

    def bound(operator, value):
        reference = BmcConstraintRef(
            "assumption.%s.%s" % (operator, value),
            "assumptions",
            "assumption.frame",
            BmcSourceRef("generated", None, None),
            "bound",
            frames=(0,),
            refs={"frame": 0},
        )
        return BmcCoreItem(
            reference,
            "assumption",
            None,
            False,
            {
                "kind": "variable_comparison",
                "variable": "x",
                "frame": 0,
                "operator": operator,
                "value": value,
            },
            "bound",
            False,
        )

    crossing = (bound("ge", 5), bound("le", 3))
    assert _conflict_pattern(crossing, "proven")[0] == "interval_intersection"

    # The same crossing bounds beside an inequality the reading skips.
    with_spare = crossing + (bound("ne", 99),)
    pattern = _conflict_pattern(with_spare, "proven")
    assert pattern is None or pattern[0] != "interval_intersection"


@pytest.mark.unittest
def test_every_tag_survives_every_public_consumer() -> None:
    """The matrix, not the reasoning: each published tag against each renderer.

    The schema requires only ``kind``, so a bare tag is valid published output and
    every public consumer has to survive it.  This rule was fixed once on
    ``human_text_for_fact`` while ``build_conflict_narrative`` thirty lines below
    kept indexing ``fact["frame"]`` -- two functions disagreeing about the same
    payload.  Enumerating the vocabulary against the consumers is what finds that;
    reading the code and asking "where else might this happen" is what missed it
    three rounds running.
    """
    from pyfcstm.bmc.explanation import (
        _FACT_KINDS,
        BmcConflictCore,
        BmcConstraintRef,
        BmcCoreItem,
        build_conflict_narrative,
        human_text_for_fact,
    )

    def core_of(fact):
        reference = BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            BmcSourceRef("generated", None, None),
            "summary",
            frames=(0,),
            refs={"frame": 0},
        )
        item = BmcCoreItem(reference, "assumption", None, False, fact, "t", False)
        return BmcConflictCore(
            "assumptions_component", "F", "source_group", "raw", "not_proven", (item,)
        )

    consumers = {
        "human_text_for_fact": lambda fact: human_text_for_fact("assumption", fact),
        "build_conflict_narrative": lambda fact: build_conflict_narrative(
            core_of(fact)
        ),
    }

    raised = []
    for kind in _FACT_KINDS:
        for name, consume in consumers.items():
            try:
                consume({"kind": kind})
            except (KeyError, TypeError, IndexError, AttributeError) as err:
                raised.append("%s(%s) -> %s" % (name, kind, type(err).__name__))

    assert raised == []


@pytest.mark.unittest
def test_a_partly_complete_fact_is_declined_by_every_consumer() -> None:
    """A tag with some of its keys is the shape that slipped through five times.

    A bare tag was handled; a tag carrying *part* of what it implies was not, and
    that is what the published gates actually allow -- the schema requires ``kind``
    and nothing more.  Each such fact must degrade the same way through both public
    consumers: no exception, and no ``complete`` derivation resting on a reading
    nobody could make.

    The cases are generated from the required-key table, so a tag or a key added
    later is covered without anyone remembering to add it here.
    """
    from itertools import combinations

    from pyfcstm.bmc.explanation import (
        _FACT_REQUIRED_KEYS,
        BmcConflictCore,
        BmcConstraintRef,
        BmcCoreItem,
        build_conflict_narrative,
        human_text_for_fact,
    )

    sample = {
        "variable": "x",
        "frame": 0,
        "operator": "eq",
        "value": 1,
        "state": 1,
        "states": [1, 2],
        "operation": "division",
    }

    def core_of(fact):
        reference = BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            BmcSourceRef("generated", None, None),
            "summary",
            frames=(0,),
            refs={"frame": 0},
        )
        item = BmcCoreItem(reference, "assumption", None, False, fact, "t", False)
        return BmcConflictCore(
            "assumptions_component", "F", "source_group", "raw", "not_proven", (item,)
        )

    failures = []
    for kind, keys in _FACT_REQUIRED_KEYS.items():
        # Every strict subset of the keys the tag implies, including the empty one.
        for size in range(len(keys)):
            for subset in combinations(keys, size):
                fact = {"kind": kind}
                fact.update({key: sample[key] for key in subset})
                try:
                    human_text_for_fact("assumption", fact)
                except Exception as err:  # noqa: BLE001 - the failure is the finding
                    failures.append("human_text %s%s: %r" % (kind, subset, err))
                try:
                    narrative = build_conflict_narrative(core_of(fact))
                except Exception as err:  # noqa: BLE001 - same
                    failures.append("narrative %s%s: %r" % (kind, subset, err))
                    continue
                if narrative.derivation_status == "complete":
                    failures.append("narrative %s%s claimed complete" % (kind, subset))

    assert failures == []
