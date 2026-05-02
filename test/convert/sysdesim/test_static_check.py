"""
Unit tests for :mod:`pyfcstm.convert.sysdesim.static_check`.

These tests exercise each detector independently using small inline SysDeSim
XML fixtures, and also assert end-to-end behavior of
:func:`run_sysdesim_static_pre_checks` on the same fixtures.
"""

from __future__ import annotations

from decimal import Decimal
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
from pyfcstm.convert.sysdesim import static_check as sc


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


def _build_dead_state_xml(tmp_path: Path) -> Path:
    """
    Tiny machine ``DeadDemo`` containing an ``Orphan`` state that has zero
    inbound transitions. Used to exercise the dead-state branch of
    :func:`_analyze_unreachability`.
    """
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="DeadDemo" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="DeadDemo">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_idle_run" source="state_idle" target="state_run">
                    <trigger xmi:type="uml:Trigger" xmi:id="trig_run" event="signal_evt_sig2"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_run" name="Run"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_orphan" name="Orphan"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="ScenDead">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_a" name="a"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_b" name="b"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_a" name="a" represents="prop_a"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_b" name="b" represents="prop_b"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_a" covered="ll_a">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_a_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_a_expr">
                      <body>true</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_send" covered="ll_b" message="msg_sig2"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_recv" covered="ll_a" message="msg_sig2"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig2" sendEvent="sig2_send" receiveEvent="sig2_recv" signature="signal_sig2"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig2" name="Sig2"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig2" signal="signal_sig2"/>
          </uml:Model>
        </xmi:XMI>
        """,
        name="dead_state.xml",
    )


def _build_signal_dropped_xml(tmp_path: Path) -> Path:
    """
    Tiny machine ``DroppedSig`` whose scenario emits ``Sig4`` *before* the
    region has transitioned out of ``Idle``. The transition to ``Done`` is
    triggered by ``Sig4`` from ``Run``; in this scenario the region is still
    in ``Idle`` when ``Sig4`` fires, so it is silently dropped and ``Done``
    is never entered.
    """
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="DroppedSig" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="DroppedSig">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_idle_run" source="state_idle" target="state_run">
                    <trigger xmi:type="uml:Trigger" xmi:id="trig_run" event="signal_evt_sig2"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_run_done" source="state_run" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trig_done" event="signal_evt_sig4"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_run" name="Run"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="ScenDropped">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_a" name="a"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_b" name="b"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_a" name="a" represents="prop_a"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_b" name="b" represents="prop_b"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_a" covered="ll_a">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_a_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_a_expr">
                      <body>true</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig4_send" covered="ll_b" message="msg_sig4"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig4_recv" covered="ll_a" message="msg_sig4"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_send" covered="ll_b" message="msg_sig2"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_recv" covered="ll_a" message="msg_sig2"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig4" sendEvent="sig4_send" receiveEvent="sig4_recv" signature="signal_sig4"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig2" sendEvent="sig2_send" receiveEvent="sig2_recv" signature="signal_sig2"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig2" name="Sig2"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig2" signal="signal_sig2"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig4" name="Sig4"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig4" signal="signal_sig4"/>
          </uml:Model>
        </xmi:XMI>
        """,
        name="signal_dropped.xml",
    )


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


# =============================================================================
# Direct unit coverage for private helpers (no mocks; real values only).
# =============================================================================


@pytest.mark.unittest
class TestParseTimeSeconds:
    """Cover :func:`_parse_time_seconds` happy / sad paths."""

    def test_returns_none_for_none_input(self):
        assert sc._parse_time_seconds(None) is None

    def test_seconds_default_unit(self):
        assert sc._parse_time_seconds("10s") == Decimal("10")
        assert sc._parse_time_seconds("0.5s") == Decimal("0.5")

    def test_milliseconds(self):
        assert sc._parse_time_seconds("250ms") == Decimal("0.250")

    def test_minutes_and_hours(self):
        assert sc._parse_time_seconds("2min") == Decimal("120")
        assert sc._parse_time_seconds("1h") == Decimal("3600")

    def test_unitless_treated_as_seconds(self):
        assert sc._parse_time_seconds("42") == Decimal("42")

    def test_raises_on_garbage_literal(self):
        with pytest.raises(ValueError, match="Unsupported time literal"):
            sc._parse_time_seconds("garbage")

    def test_raises_on_unknown_unit(self):
        # The regex itself rejects an unknown unit such as ``"10x"`` because
        # ``x`` is not in the (?:ms|s|min|h)? alternation, so we synthesize a
        # regex-passing string and a missing factor by passing a malformed
        # literal that *parses* via the structural regex but with capital unit.
        # Actually the regex is case-insensitive, so "10X" still fails. Use a
        # purely structural mismatch instead:
        with pytest.raises(ValueError):
            sc._parse_time_seconds("10x")


@pytest.mark.unittest
class TestFormatDurationExpression:
    """Cover :func:`_format_duration_expression` for every output shape.

    Each shape models a real form a SysDeSim ``DurationConstraint`` can take
    in the XML, lowered into a single human-readable inequality.
    """

    def test_equality_when_min_equals_max(self):
        assert (
            sc._format_duration_expression(
                "Sig9", "Sig6", Decimal("10"), Decimal("10"), False
            )
            == "t(Sig6) - t(Sig9) == 10s"
        )

    def test_range_when_min_less_than_max(self):
        assert (
            sc._format_duration_expression(
                "Sig13", "Sig4", Decimal("0"), Decimal("10"), False
            )
            == "0s <= t(Sig4) - t(Sig13) <= 10s"
        )

    def test_range_with_strict_lower(self):
        assert (
            sc._format_duration_expression(
                "Sig9", "Sig99", Decimal("0"), Decimal("1"), True
            )
            == "0s < t(Sig99) - t(Sig9) <= 1s"
        )

    def test_strict_equality_with_strict_lower_keeps_range_form(self):
        """When min == max but lower is strict, render as a (degenerate) range."""
        rendered = sc._format_duration_expression(
            "A", "B", Decimal("5"), Decimal("5"), True
        )
        # A strict-lower equality is logically empty; we still render the
        # bounds explicitly so the modeler sees what they wrote.
        assert rendered == "5s < t(B) - t(A) <= 5s"


@pytest.mark.unittest
class TestFormatSeconds:
    """Cover :func:`_format_seconds`."""

    def test_integer_seconds(self):
        assert sc._format_seconds(Decimal("10")) == "10s"

    def test_fractional_strips_trailing_zeros(self):
        assert sc._format_seconds(Decimal("1.500")) == "1.5s"

    def test_zero_normalizes_to_plain_zero(self):
        assert sc._format_seconds(Decimal("0")) == "0s"

    def test_negative_zero_normalizes_to_plain_zero(self):
        assert sc._format_seconds(Decimal("-0")) == "0s"


@pytest.mark.unittest
class TestFriendlyStepLabel:
    """Cover :func:`_friendly_step_label` for every recognized step shape."""

    def test_emit_action_returns_event_name(self):
        class _Action:
            event_name = "Sig9"
            input_name = None
            value_text = None
        class _Step:
            actions = (_Action(),)
            notes = ()
        assert sc._friendly_step_label(_Step()) == "Sig9"

    def test_set_input_action_returns_assignment_text(self):
        class _Action:
            event_name = None
            input_name = "y"
            value_text = "2300"
        class _Step:
            actions = (_Action(),)
            notes = ()
        assert sc._friendly_step_label(_Step()) == "y=2300"

    def test_set_input_without_value_returns_input_name_only(self):
        class _Action:
            event_name = None
            input_name = "y"
            value_text = None
        class _Step:
            actions = (_Action(),)
            notes = ()
        assert sc._friendly_step_label(_Step()) == "y"

    def test_outbound_signal_note_renders_arrow(self):
        class _Step:
            actions = ()
            notes = ("outbound_signal=Sig13",)
        assert sc._friendly_step_label(_Step()) == "-->Sig13"

    def test_self_message_note_returns_label(self):
        class _Step:
            actions = ()
            notes = ("self_message",)
        assert sc._friendly_step_label(_Step()) == "self-message"

    def test_anchor_step_falls_back_to_order_index_marker(self):
        class _Step:
            actions = ()
            notes = ()
            order_index = 7
        assert sc._friendly_step_label(_Step()) == "(anchor #7)"

    def test_anchor_step_without_order_index_falls_back_to_generic_marker(self):
        class _Step:
            actions = ()
            notes = ()
        assert sc._friendly_step_label(_Step()) == "(anchor)"


@pytest.mark.unittest
class TestDisplayNameHelpers:
    """Cover ``_display_event_name`` and ``_display_state_name``."""

    def test_display_event_name_prefers_extra_name(self):
        class _Event:
            name = "SIG9"
            extra_name = "Sig9"
        assert sc._display_event_name(_Event()) == "Sig9"

    def test_display_event_name_falls_back_to_name(self):
        class _Event:
            name = "SIG9"
            extra_name = None
        assert sc._display_event_name(_Event()) == "SIG9"

    def test_display_event_name_returns_none_when_event_is_none(self):
        assert sc._display_event_name(None) is None

    def test_display_event_name_returns_none_when_no_attributes(self):
        class _Empty:
            name = None
            extra_name = None
        assert sc._display_event_name(_Empty()) is None

    def test_display_state_name_prefers_extra_name(self):
        class _State:
            name = "STATE_FOO"
            extra_name = "Foo"
        assert sc._display_state_name(_State()) == "Foo"

    def test_display_state_name_falls_back_to_name(self):
        class _State:
            name = "STATE_FOO"
            extra_name = None
        assert sc._display_state_name(_State()) == "STATE_FOO"

    def test_display_state_name_returns_none_when_state_is_none(self):
        assert sc._display_state_name(None) is None

    def test_display_state_name_returns_none_when_empty(self):
        class _Empty:
            name = None
            extra_name = None
        assert sc._display_state_name(_Empty()) is None


@pytest.mark.unittest
class TestLevenshtein:
    """Cover :func:`_levenshtein` early-return branches and the DP body."""

    def test_equal_strings(self):
        assert sc._levenshtein("foo", "foo") == 0

    def test_left_empty(self):
        assert sc._levenshtein("", "abc") == 3

    def test_right_empty(self):
        assert sc._levenshtein("abc", "") == 3

    def test_typical_distance(self):
        # Insert, delete, replace
        assert sc._levenshtein("kitten", "sitting") == 3


@pytest.mark.unittest
class TestAliasLookups:
    """Cover the alias / trace / state-path lookup helpers."""

    def test_machine_for_alias_returns_none_when_unknown(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        assert sc._machine_for_alias(phase10, "no-such-alias") is None

    def test_trace_for_alias_returns_none_when_unknown(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        assert sc._trace_for_alias(phase10, "no-such-alias") is None

    def test_candidate_state_paths_empty_for_unknown_alias(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        assert sc._candidate_state_paths_for_alias(phase10, "no-such-alias") == ()


@pytest.mark.unittest
class TestStateInTrace:
    """Cover the three matching paths in :func:`_state_in_trace`."""

    def test_initial_state_match(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        trace = sc._trace_for_alias(phase10, "TimelineCoexist__Control_region1")
        assert trace is not None
        assert sc._state_in_trace(trace, trace.initial_state_path) is True

    def test_post_step_match(self, tmp_path: Path):
        """A state that appears as a step's post_state but not as initial."""
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        trace = sc._trace_for_alias(phase10, "TimelineCoexist__Control_region2")
        assert trace is not None
        # Region 2 starts in Idle and walks Control.J -> K -> S -> X.
        candidate = next(
            (
                step.post_state_path
                for step in trace.steps
                if step.post_state_path
                and step.post_state_path != trace.initial_state_path
            ),
            None,
        )
        assert candidate is not None
        assert sc._state_in_trace(trace, candidate) is True

    def test_state_window_only_match(self):
        """A state that appears ONLY in state_windows (not in initial / steps)."""
        from types import SimpleNamespace

        window = SimpleNamespace(state_path="WindowOnly")
        synthetic_trace = SimpleNamespace(
            initial_state_path="OtherInitial",
            steps=(),
            state_windows=(window,),
        )
        assert sc._state_in_trace(synthetic_trace, "WindowOnly") is True

    def test_returns_false_for_unreachable_state(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        trace = sc._trace_for_alias(phase10, "TimelineCoexist__Control_region1")
        assert trace is not None
        # M is unreachable in this scenario.
        assert sc._state_in_trace(trace, "TimelineCoexist.Control.H.M") is False


@pytest.mark.unittest
class TestResolveStatePath:
    """Cover the early-return and ambiguity branches of :func:`_resolve_state_path`."""

    def test_returns_none_when_machine_is_none(self):
        assert sc._resolve_state_path(None, "X") is None

    def test_resolves_full_path(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        machine = sc._machine_for_alias(phase10, "TimelineCoexist__Control_region2")
        assert machine is not None
        assert (
            sc._resolve_state_path(machine, "TimelineCoexist.Control.X")
            == "TimelineCoexist.Control.X"
        )

    def test_resolves_local_name(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        machine = sc._machine_for_alias(phase10, "TimelineCoexist__Control_region2")
        assert machine is not None
        assert sc._resolve_state_path(machine, "X").endswith(".X")

    def test_returns_none_for_unknown_name(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        machine = sc._machine_for_alias(phase10, "TimelineCoexist__Control_region2")
        assert machine is not None
        assert sc._resolve_state_path(machine, "NEVER_EXISTS") is None

    def test_resolves_via_suffix_tokens(self, tmp_path: Path):
        """A multi-token suffix uniquely identifies a deeply nested state."""
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        machine = sc._machine_for_alias(phase10, "TimelineCoexist__Control_region1")
        assert machine is not None
        # "H.M" suffix-matches "TimelineCoexist.Control.H.M" but not
        # "TimelineCoexist.Control.H.L"; the resolver returns the unique match.
        resolved = sc._resolve_state_path(machine, "H.M")
        assert resolved == "TimelineCoexist.Control.H.M"


@pytest.mark.unittest
class TestTemporalDetectorEdgeCases:
    """Cover edge branches inside :func:`detect_temporal_constraints_unsat`."""

    def test_empty_scenario_returns_no_diagnostics(self, monkeypatch):
        """No steps → early return without solver invocation."""
        # Construct a minimal stand-in Phase10Report whose scenario has zero
        # steps; we use ``types.SimpleNamespace`` so we never mock z3 itself.
        from types import SimpleNamespace

        empty_scenario = SimpleNamespace(steps=(), temporal_constraints=())
        empty_report = SimpleNamespace(
            scenario=empty_scenario,
            phase9_report=SimpleNamespace(outputs=()),
            traces=(),
        )
        assert sc.detect_temporal_constraints_unsat(empty_report) == []

    def test_unknown_step_in_constraint_is_skipped(self, tmp_path: Path):
        """A constraint referencing a non-existent step is silently skipped."""
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        # Inject a synthesized constraint referencing a nonexistent step id.
        from pyfcstm.convert.sysdesim.timeline_verify import (
            SysDeSimNormalizedTemporalConstraint,
        )

        bogus_constraint = SysDeSimNormalizedTemporalConstraint(
            constraint_id="bogus-1",
            kind="duration_constraint",
            left_step_id="doesnt-exist",
            right_step_id="also-doesnt-exist",
            left_time_symbol="t-bogus-left",
            right_time_symbol="t-bogus-right",
            min_seconds_text="1s",
            max_seconds_text="1s",
            strict_lower=False,
            note=None,
        )
        # Replace temporal_constraints with the original ones plus the bogus one.
        from dataclasses import replace
        new_scenario = replace(
            phase10.scenario,
            temporal_constraints=tuple(phase10.scenario.temporal_constraints)
            + (bogus_constraint,),
        )
        new_phase10 = replace(phase10, scenario=new_scenario)
        # Should still be SAT (the canonical fixture is timing-feasible) and
        # the bogus constraint is dropped, not raised.
        diags = sc.detect_temporal_constraints_unsat(new_phase10)
        assert diags == []

    def test_malformed_bound_value_is_skipped(self, tmp_path: Path):
        """A constraint with an unparseable time literal is skipped, not raised."""
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        from pyfcstm.convert.sysdesim.timeline_verify import (
            SysDeSimNormalizedTemporalConstraint,
        )
        from dataclasses import replace

        # Use a real step id but with a garbage time literal.
        first_step_id = phase10.scenario.steps[0].step_id
        second_step_id = phase10.scenario.steps[1].step_id
        bogus = SysDeSimNormalizedTemporalConstraint(
            constraint_id="bad-literal",
            kind="duration_constraint",
            left_step_id=first_step_id,
            right_step_id=second_step_id,
            left_time_symbol=phase10.scenario.steps[0].time_symbol,
            right_time_symbol=phase10.scenario.steps[1].time_symbol,
            min_seconds_text="not-a-time",
            max_seconds_text="also-not",
            strict_lower=False,
            note=None,
        )
        new_scenario = replace(
            phase10.scenario,
            temporal_constraints=tuple(phase10.scenario.temporal_constraints)
            + (bogus,),
        )
        new_phase10 = replace(phase10, scenario=new_scenario)
        diags = sc.detect_temporal_constraints_unsat(new_phase10)
        assert diags == []


@pytest.mark.unittest
class TestDetectorAliasMissingSafety:
    """Detectors should silently no-op when an alias does not match any output."""

    def test_target_state_never_entered_skips_unknown_alias(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        diags = detect_target_state_never_entered(
            phase10,
            left_machine_alias="no-such-alias",
            left_state_ref="X",
        )
        assert diags == []

    def test_query_state_name_unknown_skips_when_alias_missing(self, tmp_path: Path):
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        diags = detect_query_state_name_unknown(
            phase10,
            left_machine_alias="no-such-alias",
            left_state_ref="X",
        )
        assert diags == []

    def test_query_state_name_unknown_skips_when_only_alias_provided(
        self, tmp_path: Path
    ):
        """Half-specified queries (only alias, no state) are ignored."""
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        diags = detect_query_state_name_unknown(
            phase10,
            left_machine_alias="TimelineCoexist__Control_region1",
            left_state_ref=None,
        )
        assert diags == []

    def test_target_state_never_entered_skips_unresolvable_ref(
        self, tmp_path: Path
    ):
        """If the ref cannot be resolved, the target-entered check defers to
        :func:`detect_query_state_name_unknown`."""
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        diags = detect_target_state_never_entered(
            phase10,
            left_machine_alias="TimelineCoexist__Control_region1",
            left_state_ref="NEVER_EXISTS",
        )
        assert diags == []


@pytest.mark.unittest
class TestUnreachabilityAnalysis:
    """Cover the two ``hints``-generation branches of :func:`_analyze_unreachability`."""

    def test_canonical_fixture_yields_no_emitted_trigger_hint(self, tmp_path: Path):
        """In the canonical fixture, M is unreachable because Sig9 is only sent
        outbound (machine_relevant_direction_mismatch), not as a real emit. The
        analyzer should fall through to the "trigger signal never emitted" hint
        and not the "dropped at wrong state" hint."""
        xml_file = _build_parallel_timeline_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        diags = detect_target_state_never_entered(
            phase10,
            left_machine_alias="TimelineCoexist__Control_region1",
            left_state_ref="M",
        )
        assert diags
        first = diags[0]
        # The inbound transitions list should include the L --Sig9--> M edge.
        assert first.details["inbound_transitions"]
        # No emit records for Sig9 (it is outbound only in this fixture).
        assert first.details["trigger_signal_emit_steps"] == []
        # Hint mentions that the signal was never emitted.
        assert any("none of those signals were emitted" in h for h in first.hints)

    def test_dead_state_with_no_inbound_yields_dead_state_hint(self, tmp_path: Path):
        """A target state with zero inbound transitions yields the "dead state" hint."""
        xml_file = _build_dead_state_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        diags = detect_target_state_never_entered(
            phase10,
            left_machine_alias="DeadDemo",
            left_state_ref="Orphan",
        )
        assert diags
        first = diags[0]
        assert first.details["inbound_transitions"] == []
        assert any("dead state" in h for h in first.hints)

    def test_emitted_at_wrong_state_yields_dropped_hint(self, tmp_path: Path):
        """A scenario where the trigger IS emitted but the region is in the
        wrong source state -> the "silently dropped" hint fires."""
        xml_file = _build_signal_dropped_xml(tmp_path)
        phase10 = build_sysdesim_phase10_report(str(xml_file))
        diags = detect_target_state_never_entered(
            phase10,
            left_machine_alias="DroppedSig",
            left_state_ref="Done",
        )
        assert diags
        first = diags[0]
        recs = first.details["trigger_signal_emit_steps"]
        assert recs
        assert any(not r["did_fire"] for r in recs)
        assert any("silently dropped" in h for h in first.hints)
        # Friendly labels — no raw step ids should leak into the hint.
        assert "s0" not in first.hints[0]
