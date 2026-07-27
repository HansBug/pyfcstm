"""Contracts for wiring an infeasibility explanation into the solve result.

The aggregate telemetry fields and the published explanation must agree: a
reader should never see a ``refinement_status`` that contradicts the
explanation it sits next to.
"""

from __future__ import annotations

import pytest

from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.bmc.explanation import BmcInfeasibilityExplanation
from pyfcstm.bmc.witness import (
    BmcFeasibilityCheck,
    BmcFeasibilityRefinementCheck,
    BmcFeasibilityResult,
)

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


def _explanation(status: str = "partial", **kwargs) -> BmcInfeasibilityExplanation:
    payload = dict(
        requested_mode="formal",
        achieved_mode="none",
        status=status,
        classification=None,
        reason=None if status == "complete" else "probe returned unknown",
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


@pytest.mark.parametrize("status", ["complete", "partial", "unknown", "timeout"])
def test_localized_stage_accepts_every_explanation_status(status) -> None:
    """A localized stage may now report the explanation's own status.

    The previous contract pinned a localized stage to ``not_requested``, which
    made it impossible to publish an explanation at all: an explanation only
    exists once a stage has been localized.
    """
    result = _localized(
        refinement_status=status,
        refinement_reason=None if status in {"complete"} else "probe returned unknown",
        refinement_checks=(
            BmcFeasibilityRefinementCheck(
                name="component_assumptions",
                status="unsat",
                reason=None,
                elapsed_ms=0.1,
            ),
        ),
        explanation=_explanation(status),
    )

    assert result.refinement_status == status
    assert result.explanation is not None
    assert result.explanation.status == status


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
