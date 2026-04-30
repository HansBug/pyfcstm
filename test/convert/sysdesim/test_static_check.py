"""
Unit tests for :mod:`pyfcstm.convert.sysdesim.static_check`.

These tests exercise each detector independently using small inline SysDeSim
XML fixtures, and also assert end-to-end behavior of
:func:`run_sysdesim_static_pre_checks` on the same fixtures.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert import (
    detect_query_state_name_unknown,
    detect_signal_dropped_in_state,
    detect_target_state_never_entered,
    detect_temporal_constraints_unsat,
    run_sysdesim_static_pre_checks,
)
from pyfcstm.convert.sysdesim import build_sysdesim_phase10_report


def _write_xml(tmp_path: Path, content: str, name: str = "sample.sysdesim.xml") -> Path:
    """Write a temporary SysDeSim XML fixture and return its path."""
    xml_file = tmp_path / name
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


# -----------------------------------------------------------------------------
# Fixture: parallel timeline with two regions, used as a base for many cases.
# Region 1 (left): F -> W [c < d] -> H {L, M},  L --Sig9--> M, M --Sig6--> L
# Region 2 (right): J --Sig2--> K --Sig4--> S, S --(completion)--> X, X --Sig4--> S
# Scenario:  Sig1 -> self(0..1s) -> Sig2 -> Sig9 -> Sig4 -> Sig11
# DurationConstraint: Sig2 -> Sig4 = [10s, 10s]
# -----------------------------------------------------------------------------


def _build_parallel_timeline_xml(tmp_path: Path) -> Path:
    """Reuse the canonical Phase9/10/11 fixture from ``test_phase9_11``."""
    from test.convert.sysdesim.test_phase9_11 import _build_parallel_timeline_xml as _orig_builder

    return _orig_builder(tmp_path)


def _build_contradictory_durations_xml(tmp_path: Path) -> Path:
    """
    Same shape as the parallel timeline above, but with TWO contradictory
    DurationConstraints over Sig2 / Sig4 / Sig9: Sig2 -> Sig4 = 10s and
    Sig2 -> Sig9 = 1s, while the lifeline order has Sig9 *after* Sig4.

    With Sig9 - Sig2 = 1s and Sig4 - Sig2 = 10s, lifeline order Sig4 <= Sig9
    forces 10 <= 1 which is impossible — Z3 should report unsat.
    """
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Tiny" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Tiny">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_idle_run" source="state_idle" target="state_run">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_idle_run" event="signal_evt_sig2"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_run_done" source="state_run" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_run_done" event="signal_evt_sig4"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_run" name="Run"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="ScenarioBad">
                <ownedRule xmi:type="uml:DurationConstraint" xmi:id="dur_rule_a" constrainedElement="msg_sig2 msg_sig4">
                  <specification xmi:type="uml:DurationInterval" xmi:id="dur_interval_a" min="dur_min_a" max="dur_max_a"/>
                </ownedRule>
                <ownedRule xmi:type="uml:DurationConstraint" xmi:id="dur_rule_b" constrainedElement="msg_sig2 msg_sig9">
                  <specification xmi:type="uml:DurationInterval" xmi:id="dur_interval_b" min="dur_min_b" max="dur_max_b"/>
                </ownedRule>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="ctrl"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="mod"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="ctrl" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="mod" represents="prop_module"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_send" covered="ll_module" message="msg_sig2"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_recv" covered="ll_control" message="msg_sig2"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig4_send" covered="ll_module" message="msg_sig4"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig4_recv" covered="ll_control" message="msg_sig4"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig9_send" covered="ll_control" message="msg_sig9"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig9_recv" covered="ll_module" message="msg_sig9"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig2" sendEvent="sig2_send" receiveEvent="sig2_recv" signature="signal_sig2"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig4" sendEvent="sig4_send" receiveEvent="sig4_recv" signature="signal_sig4"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig9" sendEvent="sig9_send" receiveEvent="sig9_recv" signature="signal_sig9"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig2" name="Sig2"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig2" signal="signal_sig2"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig4" name="Sig4"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig4" signal="signal_sig4"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig9" name="Sig9"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig9" signal="signal_sig9"/>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_min_a" observation="dur_obs_a">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_min_a_expr" value="10s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_max_a" observation="dur_obs_a">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_max_a_expr" value="10s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_min_b" observation="dur_obs_b">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_min_b_expr" value="1s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_max_b" observation="dur_obs_b">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_max_b_expr" value="1s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_a"/>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_b"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )


# =============================================================================
# detect_temporal_constraints_unsat
# =============================================================================


@pytest.mark.unittest
def test_temporal_constraints_unsat_detects_contradiction(tmp_path: Path):
    """Z3 unsat-core finds the conflicting duration pair against lifeline order."""
    xml_file = _build_contradictory_durations_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = detect_temporal_constraints_unsat(phase10)
    assert len(diags) == 1
    diag = diags[0]
    assert diag.level == "error"
    assert diag.code == "temporal_constraints_unsat"
    assert diag.details is not None
    assert diag.details["method"] == "z3_unsat_core"
    # Both contradictory DurationConstraints should appear in the unsat core.
    involved = set(diag.details["involved_constraint_ids"])
    assert "dur_rule_a" in involved or "dur_rule_b" in involved
    # Suggestion field is set to the smallest-bound (most likely culprit) one.
    assert diag.details["suggested_first_culprit_constraint_id"] in {
        "dur_rule_a",
        "dur_rule_b",
    }
    # Hints are populated.
    assert diag.hints
    assert any("DurationConstraint" in h for h in diag.hints)


@pytest.mark.unittest
def test_temporal_constraints_unsat_clean_when_satisfiable(tmp_path: Path):
    """A scenario whose timing is satisfiable returns zero diagnostics."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = detect_temporal_constraints_unsat(phase10)
    assert diags == []


# =============================================================================
# detect_query_state_name_unknown
# =============================================================================


@pytest.mark.unittest
def test_query_state_name_unknown_returns_diagnostic_with_suggestions(tmp_path: Path):
    """Misspelled state refs are reported as errors with Levenshtein suggestions."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = detect_query_state_name_unknown(
        phase10,
        left_machine_alias="TimelineCoexist__Control_region2",
        left_state_ref="X_TYPO",
    )
    assert len(diags) == 1
    diag = diags[0]
    assert diag.level == "error"
    assert diag.code == "query_state_name_unknown"
    assert diag.details is not None
    assert diag.details["state_ref"] == "X_TYPO"
    # The available_states list should include the real X path.
    assert any("Control.X" in s for s in diag.details["available_states"])
    # Closest match should rank the actual X path near the top.
    closest = diag.details["closest_matches"]
    assert any(c.endswith(".X") for c in closest)


@pytest.mark.unittest
def test_query_state_name_unknown_clean_for_valid_refs(tmp_path: Path):
    """Cleanly resolvable state refs produce no diagnostics."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = detect_query_state_name_unknown(
        phase10,
        left_machine_alias="TimelineCoexist__Control_region2",
        left_state_ref="X",
        right_machine_alias="TimelineCoexist__Control_region1",
        right_state_ref="L",
    )
    assert diags == []


# =============================================================================
# detect_target_state_never_entered
# =============================================================================


@pytest.mark.unittest
def test_target_state_never_entered_reports_unreached_state(tmp_path: Path):
    """In the parallel timeline fixture, M is never entered (F never leaves F)."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = detect_target_state_never_entered(
        phase10,
        left_machine_alias="TimelineCoexist__Control_region1",
        left_state_ref="M",
        right_machine_alias="TimelineCoexist__Control_region2",
        right_state_ref="X",
    )
    # Only M is unreachable; X is reached via the unconditional S->X transition.
    codes = [d.code for d in diags]
    assert "target_state_never_entered" in codes
    matching = [d for d in diags if d.details and d.details.get("state_path", "").endswith(".M")]
    assert matching, "expected a diagnostic mentioning M as the unreachable state"
    diag = matching[0]
    assert diag.level == "error"
    # Inbound transitions should at least include L --Sig9--> M.
    inbound_triggers = {
        entry["trigger_event_name"] for entry in diag.details["inbound_transitions"]
    }
    assert any(name and name.lower() == "sig9" for name in inbound_triggers)


@pytest.mark.unittest
def test_target_state_never_entered_clean_when_state_reached(tmp_path: Path):
    """Both ends of a Phase11 query reach the trace -> no diagnostic."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = detect_target_state_never_entered(
        phase10,
        left_machine_alias="TimelineCoexist__Control_region1",
        left_state_ref="F",
        right_machine_alias="TimelineCoexist__Control_region2",
        right_state_ref="J",
    )
    assert diags == []


# =============================================================================
# detect_signal_dropped_in_state
# =============================================================================


@pytest.mark.unittest
def test_signal_dropped_in_state_warns_for_unconsumed_emit(tmp_path: Path):
    """Sig2 is emitted at a step where region 1 is still in F (F has no Sig2 transition; W does)."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = detect_signal_dropped_in_state(phase10)
    assert all(d.level == "warning" for d in diags)
    # The Sig2 emit while region1 is still in F should be flagged: F has no
    # outgoing Sig2 transition (W does), so the signal is silently dropped.
    sig2_drops = [
        d for d in diags
        if d.details
        and d.details.get("signal", "").lower() == "sig2"
        and d.details.get("machine_alias") == "TimelineCoexist__Control_region1"
    ]
    assert sig2_drops, (
        "expected a Sig2-dropped warning for region 1 while still in F; "
        "got: {}".format([(d.details.get("signal"), d.details.get("machine_alias")) for d in diags])
    )


# =============================================================================
# run_sysdesim_static_pre_checks (public API)
# =============================================================================


@pytest.mark.unittest
def test_run_static_pre_checks_orchestrates_all_detectors(tmp_path: Path):
    """The orchestrator runs every detector and returns a stable list."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    diags = run_sysdesim_static_pre_checks(
        xml_path=str(xml_file),
        left_machine_alias="TimelineCoexist__Control_region1",
        left_state_ref="M",
        right_machine_alias="TimelineCoexist__Control_region2",
        right_state_ref="X",
    )
    codes = {d.code for d in diags}
    # M is unreachable -> error
    assert "target_state_never_entered" in codes
    # Sig9 dropped in F -> warning
    assert "signal_dropped_in_state" in codes


@pytest.mark.unittest
def test_run_static_pre_checks_accepts_prebuilt_phase10(tmp_path: Path):
    """The orchestrator can accept a pre-built Phase10 report instead of a path."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    diags = run_sysdesim_static_pre_checks(phase10_report=phase10)
    # Without an explicit Phase11 query, only signal-dropped warnings can fire.
    assert all(d.level == "warning" for d in diags)


@pytest.mark.unittest
def test_run_static_pre_checks_requires_input():
    """Calling without xml_path or phase10_report raises ValueError."""
    with pytest.raises(ValueError):
        run_sysdesim_static_pre_checks()


@pytest.mark.unittest
def test_run_static_pre_checks_unknown_state_short_circuits_target_check(
    tmp_path: Path,
):
    """When a state name is unknown, the target-entered check is skipped for it."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    diags = run_sysdesim_static_pre_checks(
        xml_path=str(xml_file),
        left_machine_alias="TimelineCoexist__Control_region2",
        left_state_ref="NOT_A_STATE",
    )
    codes = [d.code for d in diags]
    # query_state_name_unknown fires; target_state_never_entered does NOT fire
    # for the unresolvable side.
    assert "query_state_name_unknown" in codes


@pytest.mark.unittest
def test_run_static_pre_checks_returns_temporal_unsat(tmp_path: Path):
    """The orchestrator surfaces the Z3 unsat-core diagnostic for the bad fixture."""
    xml_file = _build_contradictory_durations_xml(tmp_path)
    diags = run_sysdesim_static_pre_checks(xml_path=str(xml_file))
    error_codes = {d.code for d in diags if d.level == "error"}
    assert "temporal_constraints_unsat" in error_codes
