"""Contracts for wiring an infeasibility explanation into the solve result.

The aggregate telemetry fields and the published explanation must agree: a
reader should never see a ``refinement_status`` that contradicts the
explanation it sits next to.
"""

from __future__ import annotations

import pytest

from pyfcstm.bmc import build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.engine import BmcEngine
from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.bmc.explanation import (
    BmcConflictCore,
    BmcConstraintRef,
    BmcCoreItem,
    BmcInfeasibilityExplanation,
)
from pyfcstm.bmc.provenance import BmcSourceRef
from pyfcstm.bmc.witness import (
    BmcFeasibilityCheck,
    BmcFeasibilityRefinementCheck,
    BmcFeasibilityResult,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest


def _check(status: str = "sat") -> BmcFeasibilityCheck:
    return BmcFeasibilityCheck(
        status=status, origin="checked", reason=None, elapsed_ms=0.1
    )


def _localized(**kwargs) -> BmcFeasibilityResult:
    payload = dict(
        kernel=_check("sat"),
        initialization=_check("sat"),
        assumptions=_check("unsat"),
        infeasible_stage="assumptions",
        localization_status="complete",
    )
    payload.update(kwargs)
    return BmcFeasibilityResult(**payload)


def _subset_minimal_core() -> BmcConflictCore:
    reference = BmcConstraintRef(
        stable_id="assumption.0000.frame.0000",
        stage="assumptions",
        category="assumption.frame",
        source=BmcSourceRef("generated", None, None),
        summary="frame assumption",
    )
    return BmcConflictCore(
        scope="assumptions_component",
        formula_summary="ENV_N",
        granularity="source_group",
        reduction="subset_minimal",
        subset_minimality="proven",
        items=(
            BmcCoreItem(
                constraint=reference,
                semantic_role="assumption",
                source_excerpt=None,
                source_excerpt_truncated=False,
                normalized_fact={
                    "kind": "structural_constraint",
                    "stable_id": reference.stable_id,
                },
                human_text="frame assumption",
                editable=False,
            ),
        ),
    )


def _probe(
    name: str = "component_assumptions", status: str = "unsat"
) -> BmcFeasibilityRefinementCheck:
    return BmcFeasibilityRefinementCheck(
        name=name, status=status, reason=None, elapsed_ms=0.1
    )


def _explanation(status: str = "partial", **kwargs) -> BmcInfeasibilityExplanation:
    payload = dict(
        requested_mode="formal",
        achieved_mode="none",
        status=status,
        classification=None,
        reason="probe returned unknown",
    )
    payload.update(kwargs)
    return BmcInfeasibilityExplanation(**payload)


def test_result_has_an_explanation_slot() -> None:
    """The result carries the published explanation next to its telemetry."""
    assert "explanation" in BmcFeasibilityResult.__dataclass_fields__
    assert _localized().explanation is None


def test_localized_stage_still_allows_not_requested() -> None:
    """Asking for no explanation keeps the previous aggregate value."""
    result = _localized(refinement_status="not_requested")

    assert result.refinement_status == "not_requested"
    assert result.explanation is None


@pytest.mark.parametrize("status", ["partial", "unknown", "timeout"])
def test_localized_stage_accepts_every_explanation_status(status) -> None:
    """A localized stage may now report the explanation's own status.

    The previous contract pinned a localized stage to ``not_requested``, which
    made it impossible to publish an explanation at all: an explanation only
    exists once a stage has been localized.
    """
    result = _localized(
        refinement_status=status,
        refinement_reason="probe returned unknown",
        refinement_checks=(_probe(),),
        explanation=_explanation(status),
    )

    assert result.refinement_status == status
    assert result.explanation is not None
    assert result.explanation.status == status


def test_complete_status_is_not_deliverable_without_a_narrative() -> None:
    """``complete`` is reserved for a subset-minimal core plus a narrative.

    Neither is produced at this stage, so the frozen matrix rejects it rather
    than letting a raw candidate core be published as a finished explanation.
    """
    with pytest.raises(ValueError, match="narrative"):
        BmcInfeasibilityExplanation(
            requested_mode="formal",
            achieved_mode="formal",
            status="complete",
            classification="assumptions_self_conflict",
            core=_subset_minimal_core(),
        )


def test_partial_refinement_requires_a_reason() -> None:
    """A degraded aggregate never hides why it degraded."""
    with pytest.raises(BmcBuildError, match="partial"):
        _localized(
            refinement_status="partial",
            refinement_reason=None,
            explanation=_explanation("partial"),
        )


def test_aggregate_status_must_match_the_explanation() -> None:
    """Telemetry and explanation are two views of the same outcome."""
    with pytest.raises(BmcBuildError, match="explanation"):
        _localized(
            refinement_status="timeout",
            refinement_reason="probe returned unknown",
            explanation=_explanation("unknown"),
        )


def test_aggregate_reason_must_match_the_explanation() -> None:
    """A reader must not see two different reasons for one degradation."""
    with pytest.raises(BmcBuildError, match="reason"):
        _localized(
            refinement_status="unknown",
            refinement_reason="a different reason",
            explanation=_explanation("unknown"),
        )


def test_explanation_requires_a_localized_stage() -> None:
    """Without a localized stage there is no honest target to explain."""
    with pytest.raises(BmcBuildError, match="localized"):
        BmcFeasibilityResult(
            kernel=_check("sat"),
            initialization=_check("sat"),
            assumptions=_check("sat"),
            infeasible_stage=None,
            localization_status="not_needed",
            refinement_status="not_needed",
            explanation=_explanation("unknown"),
        )


def test_explanation_enters_canonical_output() -> None:
    """Machine consumers read the explanation from the canonical payload."""
    result = _localized(
        refinement_status="unknown",
        refinement_reason="probe returned unknown",
        refinement_checks=(_probe(),),
        explanation=_explanation("unknown"),
    )
    canonical = result.to_canonical()

    assert canonical["refinement_status"] == "unknown"
    assert canonical["explanation"]["status"] == "unknown"
    assert canonical["explanation"]["achieved_mode"] == "none"


def test_absent_explanation_stays_absent_in_canonical_output() -> None:
    """The default path keeps its previous canonical shape."""
    canonical = _localized().to_canonical()

    assert canonical["explanation"] is None


def _solve(query: str, **kwargs):
    """Drive the real solve path with real FCSTM and FBMCQ text."""
    machine = load_state_machine_from_text(
        "def int x = 0;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
    )
    context = BmcEngine(machine).prepare(query)
    formula = compile_bmc_property(build_bmc_core_formula(context))
    return solve_bmc_property(formula, **kwargs)


_ASSUMPTIONS_QUERY = (
    'init state("Root.A") where x == 0; '
    'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
    'check reach <= 2: active("Root.B");'
)
_INITIALIZATION_QUERY = (
    'init state("Root.A") where x == 1 && x == 2; check reach <= 2: active("Root.B");'
)


@pytest.mark.parametrize(
    "query, stage, classification",
    [
        (_ASSUMPTIONS_QUERY, "assumptions", "assumptions_self_conflict"),
        (_INITIALIZATION_QUERY, "initialization", "initialization_self_conflict"),
    ],
)
def test_every_localized_stage_reaches_the_explanation_hook(
    query, stage, classification
) -> None:
    """Requesting an explanation must work from every localizing return path.

    The solve function returns from several places once a stage is localized.
    Driving each of them through real text catches a branch that forgot to
    call the hook, which would silently leave that stage unexplainable.
    """
    result = _solve(query, infeasibility_explanation="formal")
    feasibility = result.feasibility

    assert feasibility.infeasible_stage == stage
    assert feasibility.explanation is not None
    assert feasibility.explanation.classification == classification
    assert feasibility.refinement_status == feasibility.explanation.status
    assert feasibility.refinement_checks


@pytest.mark.parametrize("query", [_ASSUMPTIONS_QUERY, _INITIALIZATION_QUERY])
def test_the_default_mode_adds_no_refinement_work(query) -> None:
    """``none`` keeps the previous behaviour: no explanation, no extra check."""
    feasibility = _solve(query).feasibility

    assert feasibility.infeasible_stage is not None
    assert feasibility.explanation is None
    assert feasibility.refinement_status == "not_requested"
    assert feasibility.refinement_checks == ()


@pytest.mark.parametrize("mode", ["formal ", "FORMAL", "", "subset", True, 1, None])
def test_unknown_explanation_modes_are_rejected_loudly(mode) -> None:
    """Only the three frozen mode names are accepted, with no coercion."""
    with pytest.raises(BmcBuildError, match="infeasibility_explanation"):
        _solve(_ASSUMPTIONS_QUERY, infeasibility_explanation=mode)


def _core_with(
    reduction: str = "raw", subset_minimality: str = "not_proven", members: int = 1
):
    """Build one publishable core at a chosen minimality level.

    ``members`` exists so a test about per-member evidence can actually use
    more than one member; a single-member fixture would make "every member"
    and "some member" indistinguishable.
    """
    items = []
    for index in range(members):
        reference = BmcConstraintRef(
            stable_id="assumption.%04d.frame.0000" % index,
            stage="assumptions",
            category="assumption.frame",
            source=BmcSourceRef("generated", None, None),
            summary="frame assumption %d" % index,
        )
        items.append(
            BmcCoreItem(
                constraint=reference,
                semantic_role="assumption",
                source_excerpt=None,
                source_excerpt_truncated=False,
                normalized_fact={"kind": "structural_constraint"},
                human_text="frame assumption %d" % index,
                editable=False,
            )
        )
    return BmcConflictCore(
        scope="assumptions_component",
        formula_summary="ENV_N",
        granularity="source_group",
        reduction=reduction,
        subset_minimality=subset_minimality,
        items=tuple(items),
    )


def test_a_published_core_needs_a_recorded_core_check() -> None:
    """A core is a claim that some check proved its target unsatisfiable.

    Accepting one without the matching ledger entry would let a result assert
    solver work that never happened.
    """
    explanation = _explanation(
        "partial",
        achieved_mode="formal",
        classification="assumptions_self_conflict",
        core=_core_with(),
    )

    with pytest.raises(BmcBuildError, match="unsat-core"):
        _localized(
            refinement_status="partial",
            refinement_reason="probe returned unknown",
            refinement_checks=(_probe("component_assumptions"),),
            explanation=explanation,
        )

    accepted = _localized(
        refinement_status="partial",
        refinement_reason="probe returned unknown",
        refinement_checks=(
            _probe("component_assumptions"),
            _probe("unsat_core", "complete"),
        ),
        explanation=explanation,
    )
    assert accepted.explanation is explanation


def test_a_minimal_core_needs_recorded_deletion_checks() -> None:
    """Minimality is only proven by deletion checks, never asserted for free."""
    explanation = _explanation(
        "partial",
        achieved_mode="formal",
        classification="assumptions_self_conflict",
        core=_core_with("subset_minimal", "proven"),
    )

    with pytest.raises(BmcBuildError, match="deletion check per member"):
        _localized(
            refinement_status="partial",
            refinement_reason="probe returned unknown",
            refinement_checks=(_probe("unsat_core", "complete"),),
            explanation=explanation,
        )


def test_a_core_check_that_did_not_prove_anything_cannot_back_a_core() -> None:
    """The ledger must show the proof, not merely the right check name.

    A satisfiable target would in fact disprove the core, so an entry that
    only matches by name is weaker evidence than none at all: it looks like
    corroboration while contradicting the claim.
    """
    explanation = _explanation(
        "partial",
        achieved_mode="formal",
        classification="assumptions_self_conflict",
        core=_core_with(),
    )

    with pytest.raises(BmcBuildError, match="completed unsat-core"):
        _localized(
            refinement_status="partial",
            refinement_reason="probe returned unknown",
            refinement_checks=(_probe("unsat_core", "sat"),),
            explanation=explanation,
        )


def test_deletion_checks_must_have_shown_each_member_necessary() -> None:
    """Minimality follows from satisfiable deletions, not from any deletion.

    A deletion check that comes back unsat shows the removed member was
    redundant, which is the opposite of what a minimal core claims.  The core
    carries several members so "some deletion" and "every deletion" are
    distinguishable.
    """
    explanation = _explanation(
        "partial",
        achieved_mode="formal",
        classification="assumptions_self_conflict",
        core=_core_with("subset_minimal", "proven", members=3),
    )

    with pytest.raises(BmcBuildError, match="every deletion check to"):
        _localized(
            refinement_status="partial",
            refinement_reason="probe returned unknown",
            refinement_checks=(
                _probe("unsat_core", "complete"),
                _probe("unsat_core_minimization", "unsat"),
            ),
            explanation=explanation,
        )

    # One satisfiable deletion is not enough for a three-member core: it shows
    # that *some* member is needed, not that every one of them is.
    with pytest.raises(BmcBuildError, match="deletion check per member"):
        _localized(
            refinement_status="partial",
            refinement_reason="probe returned unknown",
            refinement_checks=(
                _probe("unsat_core", "complete"),
                _probe("unsat_core_minimization", "sat"),
            ),
            explanation=explanation,
        )

    accepted = _localized(
        refinement_status="partial",
        refinement_reason="probe returned unknown",
        refinement_checks=(
            _probe("unsat_core", "complete"),
            _probe("unsat_core_minimization", "sat"),
            _probe("unsat_core_minimization", "sat"),
            _probe("unsat_core_minimization", "sat"),
        ),
        explanation=explanation,
    )
    assert accepted.explanation is explanation
    assert len(accepted.explanation.core.items) == 3


def test_no_attempted_check_means_no_explanation() -> None:
    """A deadline that refused every attempt leaves nothing to explain.

    Publishing a not-started attempt as a finished check would overstate the
    solver work the budget actually allowed.
    """
    from pyfcstm.bmc import build_bmc_core_formula, compile_bmc_property
    from pyfcstm.bmc.engine import BmcEngine
    from pyfcstm.bmc.solver import _SolveBudget
    from pyfcstm.bmc.witness import _attach_explanation, solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    machine = load_state_machine_from_text(
        "def int x = 0;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    formula = compile_bmc_property(build_bmc_core_formula(context))
    baseline = solve_bmc_property(formula).feasibility

    spent = _SolveBudget(1)
    spent.deadline = spent.deadline - 10.0
    attached = _attach_explanation(baseline, formula.core, spent, "formal")

    assert attached is baseline
    assert attached.explanation is None
    assert attached.refinement_status == "not_requested"
    assert attached.refinement_checks == ()


def test_a_partially_minimized_core_needs_a_finished_deletion_check() -> None:
    """The middle reduction level also has to be backed by evidence.

    ``partial_minimized`` states that at least one deletion check finished.
    With none in the ledger the core is simply raw, and claiming otherwise
    reports progress that never happened.
    """
    explanation = _explanation(
        "partial",
        achieved_mode="formal",
        classification="assumptions_self_conflict",
        core=_core_with("partial_minimized", "not_proven"),
    )

    with pytest.raises(BmcBuildError, match="at least one recorded"):
        _localized(
            refinement_status="partial",
            refinement_reason="probe returned unknown",
            refinement_checks=(_probe("unsat_core", "complete"),),
            explanation=explanation,
        )

    accepted = _localized(
        refinement_status="partial",
        refinement_reason="probe returned unknown",
        refinement_checks=(
            _probe("unsat_core", "complete"),
            _probe("unsat_core_minimization", "unsat"),
        ),
        explanation=explanation,
    )
    assert accepted.explanation is explanation


def test_a_raw_core_needs_no_deletion_evidence() -> None:
    """``raw`` claims nothing about minimality, so it asks for nothing."""
    accepted = _localized(
        refinement_status="partial",
        refinement_reason="probe returned unknown",
        refinement_checks=(_probe("unsat_core", "complete"),),
        explanation=_explanation(
            "partial",
            achieved_mode="formal",
            classification="assumptions_self_conflict",
            core=_core_with(),
        ),
    )

    assert accepted.explanation.core.reduction == "raw"


def test_an_optional_explanation_never_destroys_a_usable_verdict(monkeypatch) -> None:
    """A fail-closed guard inside the optional stage must not reach the caller.

    Asking for an explanation would otherwise be strictly worse than not
    asking: the same query returns a localized verdict with ``none`` and
    crashes with ``formal``.
    """
    from pyfcstm.bmc import build_bmc_core_formula, compile_bmc_property
    from pyfcstm.bmc.engine import BmcEngine
    from pyfcstm.bmc.witness import solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    machine = load_state_machine_from_text(
        "def int x = 0;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    formula = compile_bmc_property(build_bmc_core_formula(context))
    baseline = solve_bmc_property(formula).feasibility

    def drift(_core):
        raise BmcBuildError("simulated relation-builder drift")

    monkeypatch.setattr("pyfcstm.bmc.infeasibility.partition_tracked_groups", drift)
    degraded = solve_bmc_property(
        formula, infeasibility_explanation="formal"
    ).feasibility

    assert degraded.infeasible_stage == baseline.infeasible_stage
    assert degraded.explanation is None
    assert degraded.refinement_status == "not_requested"


@pytest.mark.parametrize("status", ["partial", "unknown", "timeout"])
def test_an_unlocalized_result_cannot_report_a_degraded_refinement(status) -> None:
    """A degraded refinement needs a stage it could have been attempted on.

    These statuses say optional work was tried and fell short.  With no
    localized stage there was no target to try it against, so the claim
    describes work that had nothing to work on and a reader can no longer use
    ``refinement_status`` to tell whether an optional stage existed at all.
    """
    with pytest.raises(BmcBuildError, match="unlocalized result"):
        BmcFeasibilityResult(
            kernel=_check("sat"),
            initialization=_check("sat"),
            assumptions=_check("sat"),
            infeasible_stage=None,
            localization_status="not_needed",
            refinement_status=status,
            refinement_reason="optional stage allegedly failed",
        )


def test_a_feasible_scenario_still_reports_no_refinement_need() -> None:
    """The ordinary unlocalized shape is untouched."""
    result = BmcFeasibilityResult(
        kernel=_check("sat"),
        initialization=_check("sat"),
        assumptions=_check("sat"),
        infeasible_stage=None,
        localization_status="not_needed",
        refinement_status="not_needed",
    )

    assert result.refinement_status == "not_needed"
    assert result.explanation is None
