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


@pytest.mark.parametrize("field", ["stable_id", "category", "summary"])
def test_constraint_rejects_empty_identity_fields(field) -> None:
    """An unnamed constraint could never be traced back to its source."""
    payload = dict(
        stable_id="initial.target",
        stage="initialization",
        category="initial.target",
        source=_GENERATED,
        summary="initial target state",
    )
    payload[field] = ""

    with pytest.raises(ValueError, match="non-empty string"):
        BmcConstraintRef(**payload)


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

    with pytest.raises(ValueError, match="formula_summary"):
        BmcConflictCore(
            "initialization_component",
            "",
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


@pytest.mark.parametrize("slot", ["proof", "narrative"])
def test_reserved_slots_are_rejected_rather_than_silently_dropped(slot) -> None:
    """A filled slot fails loudly instead of vanishing from the payload.

    Both slots belong to a later delivery stage.  Serializing them to ``null``
    would let a caller believe a proof or narrative had been published.
    """
    filled = {
        "proof": BmcConflictProof("initialization_component", "root"),
        "narrative": BmcConflictNarrative("structural_only", "head", "body"),
    }[slot]

    with pytest.raises(ValueError, match="not produced at this stage"):
        BmcInfeasibilityExplanation(
            "proof",
            "formal",
            "partial",
            "initialization_self_conflict",
            _core(),
            reason="r",
            **{slot: filled},
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
    """A truthy stand-in would publish a non-boolean where JSON needs one."""
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
