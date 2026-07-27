"""TDD contracts for the public BMC infeasibility explanation data layer.

The dataclasses under test are the frozen public shape described by the
upstream design.  They deliberately carry no Z3 objects so that downstream
consumers can read an explanation without loading the solver stack.
"""

from __future__ import annotations

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
        normalized_fact={"stable_id": stable_id},
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


@pytest.mark.parametrize(
    "achieved_mode, status, reason, valid",
    [
        ("none", "unknown", "first probe returned unknown", True),
        ("none", "unknown", None, False),
        ("none", "timeout", "first probe exhausted the budget", True),
        ("none", "timeout", None, False),
        ("none", "partial", "raw core extraction returned unknown", True),
        ("none", "partial", None, False),
        ("formal", "partial", "minimization not attempted", True),
        ("formal", "partial", None, False),
        ("formal", "complete", None, False),
        ("formal", "complete", "unexpected", False),
    ],
)
def test_status_reason_matrix(achieved_mode, status, reason, valid) -> None:
    """``complete`` forbids a reason; every degraded status requires one."""
    kwargs = dict(
        requested_mode="formal",
        achieved_mode=achieved_mode,
        status=status,
        classification="assumptions_self_conflict",
        core=_core("assumptions_component") if achieved_mode == "formal" else None,
        reason=reason,
    )
    if valid:
        assert BmcInfeasibilityExplanation(**kwargs).status == status
    else:
        with pytest.raises(ValueError):
            BmcInfeasibilityExplanation(**kwargs)


@pytest.mark.parametrize("mode", ["none", "formal", "proof"])
def test_modes_accept_the_frozen_vocabulary(mode) -> None:
    """Only the three frozen mode names are accepted."""
    explanation = BmcInfeasibilityExplanation(
        requested_mode=mode,
        achieved_mode="none",
        status="unknown",
        classification=None,
        reason="probe unknown",
    )

    assert explanation.requested_mode == mode


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
        BmcCoreItem("initial.target", "initial_fact", None, False, {}, "text", False)

    with pytest.raises(ValueError, match="human_text"):
        BmcCoreItem(_constraint(), "initial_fact", None, False, {}, "", False)


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


@pytest.mark.parametrize("bad", [(True,), (-1,), ("0",), (1.0,)])
def test_frame_and_step_indices_must_be_non_negative_integers(bad) -> None:
    """A published index must survive the JSON contract unchanged.

    ``bool`` is an ``int`` subclass in Python, so an unchecked flag would be
    serialized as ``true`` where the schema promises a number.
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


@pytest.mark.parametrize("field", ["source_excerpt_truncated", "editable"])
def test_core_item_flags_must_be_real_booleans(field) -> None:
    """A truthy stand-in would publish a non-boolean where JSON needs one."""
    payload = dict(
        constraint=_constraint(),
        semantic_role="initial_fact",
        source_excerpt=None,
        source_excerpt_truncated=False,
        normalized_fact={},
        human_text="initial target state",
        editable=False,
    )
    payload[field] = "yes"

    with pytest.raises(TypeError, match="must be a bool"):
        BmcCoreItem(**payload)


def test_optional_text_fields_reject_non_strings() -> None:
    """An excerpt or a reason is text, so a number is not a quiet substitute."""
    with pytest.raises(TypeError, match="source_excerpt"):
        BmcCoreItem(_constraint(), "initial_fact", 123, False, {}, "t", False)

    with pytest.raises(TypeError, match="reason"):
        BmcInfeasibilityExplanation("formal", "none", "unknown", None, reason=123)
