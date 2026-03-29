"""Unit tests for the SysDeSim Phase7/8 timeline-import candidate layer."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import (
    SysDeSimTimelineEmitAction,
    SysDeSimTimelineSetInputAction,
    build_sysdesim_phase78_report,
)

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def test_phase7_builds_machine_graph_and_binding_candidates(tmp_path: Path):
    """Phase7 should expose machine graph plus input/event binding candidates."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Import Demo" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Import Demo">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_go" source="state_idle" target="state_active">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="signal_evt_go"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_change_rmt" source="state_active" target="state_wait">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_change_rmt" event="change_evt_rmt"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_guard_rmt" source="state_active" target="state_wait">
                    <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rmt_rule">
                      <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_rmt_expr">
                        <body>rmt &lt; 5000</body>
                      </specification>
                    </ownedRule>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_reply" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_reply" event="signal_evt_reply"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_finish" source="state_done" target="state_finish"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_active" name="Active">
                    <doActivity xmi:type="uml:Activity" xmi:id="do_mode" name="Mode=1"/>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_finish" name="Finish"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario 1">
                <ownedRule xmi:type="uml:DurationConstraint" xmi:id="dur_rule_1" constrainedElement="msg_go msg_reply">
                  <specification xmi:type="uml:DurationInterval" xmi:id="dur_interval_1" min="dur_min_1" max="dur_max_1"/>
                </ownedRule>
                <ownedRule xmi:type="uml:TimeConstraint" xmi:id="time_rule_1" constrainedElement="msg_self">
                  <specification xmi:type="uml:TimeInterval" xmi:id="time_interval_1" min="time_min_1" max="time_max_1"/>
                </ownedRule>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_send" covered="ll_module" message="msg_go"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_recv" covered="ll_control" message="msg_go"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_rmt" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_rmt_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_rmt_expr">
                      <body>Rmt=4999</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="self_send" covered="ll_control" message="msg_self"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="self_recv" covered="ll_control" message="msg_self"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="reply_send" covered="ll_control" message="msg_reply"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="reply_recv" covered="ll_module" message="msg_reply"/>
                <message xmi:type="uml:Message" xmi:id="msg_go" messageSort="asynchCall" sendEvent="go_send" receiveEvent="go_recv" signature="signal_go"/>
                <message xmi:type="uml:Message" xmi:id="msg_self" sendEvent="self_send" receiveEvent="self_recv"/>
                <message xmi:type="uml:Message" xmi:id="msg_reply" name="Reply" messageSort="asynchCall" sendEvent="reply_send" receiveEvent="reply_recv" signature="signal_reply"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Sig1"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_go" signal="signal_go"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_reply" name="SigReply"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_reply" signal="signal_reply"/>
            <packagedElement xmi:type="uml:ChangeEvent" xmi:id="change_evt_rmt">
              <changeExpression xmi:type="uml:OpaqueExpression" xmi:id="change_rmt_expr">
                <body>R_mt &lt; 5000</body>
              </changeExpression>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_min_1" observation="dur_obs_min">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_min_1_expr" value="20s-30s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_max_1" observation="dur_obs_max">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_max_1_expr" value="20s-30s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_min"/>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_max"/>
            <packagedElement xmi:type="uml:TimeExpression" xmi:id="time_min_1" observation="time_obs_min">
              <expr xmi:type="uml:LiteralString" xmi:id="time_min_1_expr" value="0s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeExpression" xmi:id="time_max_1" observation="time_obs_max">
              <expr xmi:type="uml:LiteralString" xmi:id="time_max_1_expr" value="1s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeObservation" xmi:id="time_obs_min"/>
            <packagedElement xmi:type="uml:TimeObservation" xmi:id="time_obs_max"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    report = build_sysdesim_phase78_report(str(xml_file))

    assert report.selected_machine_name == "Timeline Import Demo"
    assert report.selected_interaction_name == "Scenario 1"

    graph_by_pair = {
        (item.source_path, item.target_path): item for item in report.machine_graph
    }
    assert graph_by_pair[((), ("Idle",))].semantic_kind == "initial_transition"
    assert graph_by_pair[(("Idle",), ("Active",))].semantic_kind == "signal_transition"
    assert graph_by_pair[(("Idle",), ("Active",))].machine_event_path == "/SIG1"
    assert (
        graph_by_pair[(("Active",), ("Wait",))].semantic_kind == "condition_transition"
    )
    assert graph_by_pair[(("Active",), ("Wait",))].guard_text == "rmt < 5000"
    assert graph_by_pair[(("Active",), ("Wait",))].transition_ids == (
        "tx_change_rmt",
        "tx_guard_rmt",
    )
    assert graph_by_pair[(("Wait",), ("Done",))].machine_event_path == "/SIGREPLY"
    assert graph_by_pair[(("Done",), ("Finish",))].semantic_kind == "auto_transition"
    assert "hidden_internal_transition" in graph_by_pair[(("Done",), ("Finish",))].notes

    input_by_name = {item.normalized_name: item for item in report.input_candidates}
    assert input_by_name["rmt"].role == "external_input"
    assert input_by_name["rmt"].scenario_names == ("Rmt",)
    assert input_by_name["rmt"].machine_local_names == ("R_mt", "rmt")
    assert input_by_name["rmt"].observation_values == ("4999",)
    assert input_by_name["rmt"].trigger_expressions == ("rmt < 5000",)
    assert input_by_name["mode"].role == "internal_state"
    assert input_by_name["mode"].machine_local_names == ("Mode",)
    assert input_by_name["mode"].write_texts == ("Mode=1",)

    event_by_name = {item.scenario_event_name: item for item in report.event_candidates}
    assert event_by_name["Sig1"].machine_event_path == "/SIG1"
    assert event_by_name["Sig1"].emit_allowed is True
    assert event_by_name["Sig1"].message_directions == ("inbound",)
    assert event_by_name["SigReply"].machine_event_path == "/SIGREPLY"
    assert event_by_name["SigReply"].emit_allowed is False
    assert event_by_name["SigReply"].message_directions == ("outbound",)

    assert "timeline_outbound_machine_signal" in [
        item.code for item in report.diagnostics
    ]


def test_phase8_builds_steps_and_timing_candidates(tmp_path: Path):
    """Phase8 should lower the observation stream into ordered step candidates."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Import Demo" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Import Demo">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_go" source="state_idle" target="state_active">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="signal_evt_go"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_change_rmt" source="state_active" target="state_wait">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_change_rmt" event="change_evt_rmt"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_guard_rmt" source="state_active" target="state_wait">
                    <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rmt_rule">
                      <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_rmt_expr">
                        <body>rmt &lt; 5000</body>
                      </specification>
                    </ownedRule>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_reply" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_reply" event="signal_evt_reply"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_finish" source="state_done" target="state_finish"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_active" name="Active">
                    <doActivity xmi:type="uml:Activity" xmi:id="do_mode" name="Mode=1"/>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_finish" name="Finish"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario 1">
                <ownedRule xmi:type="uml:DurationConstraint" xmi:id="dur_rule_1" constrainedElement="msg_go msg_reply">
                  <specification xmi:type="uml:DurationInterval" xmi:id="dur_interval_1" min="dur_min_1" max="dur_max_1"/>
                </ownedRule>
                <ownedRule xmi:type="uml:TimeConstraint" xmi:id="time_rule_1" constrainedElement="msg_self">
                  <specification xmi:type="uml:TimeInterval" xmi:id="time_interval_1" min="time_min_1" max="time_max_1"/>
                </ownedRule>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_send" covered="ll_module" message="msg_go"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_recv" covered="ll_control" message="msg_go"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_rmt" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_rmt_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_rmt_expr">
                      <body>Rmt=4999</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="self_send" covered="ll_control" message="msg_self"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="self_recv" covered="ll_control" message="msg_self"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="reply_send" covered="ll_control" message="msg_reply"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="reply_recv" covered="ll_module" message="msg_reply"/>
                <message xmi:type="uml:Message" xmi:id="msg_go" messageSort="asynchCall" sendEvent="go_send" receiveEvent="go_recv" signature="signal_go"/>
                <message xmi:type="uml:Message" xmi:id="msg_self" sendEvent="self_send" receiveEvent="self_recv"/>
                <message xmi:type="uml:Message" xmi:id="msg_reply" name="Reply" messageSort="asynchCall" sendEvent="reply_send" receiveEvent="reply_recv" signature="signal_reply"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Sig1"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_go" signal="signal_go"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_reply" name="SigReply"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_reply" signal="signal_reply"/>
            <packagedElement xmi:type="uml:ChangeEvent" xmi:id="change_evt_rmt">
              <changeExpression xmi:type="uml:OpaqueExpression" xmi:id="change_rmt_expr">
                <body>R_mt &lt; 5000</body>
              </changeExpression>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_min_1" observation="dur_obs_min">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_min_1_expr" value="20s-30s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_max_1" observation="dur_obs_max">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_max_1_expr" value="20s-30s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_min"/>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_max"/>
            <packagedElement xmi:type="uml:TimeExpression" xmi:id="time_min_1" observation="time_obs_min">
              <expr xmi:type="uml:LiteralString" xmi:id="time_min_1_expr" value="0s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeExpression" xmi:id="time_max_1" observation="time_obs_max">
              <expr xmi:type="uml:LiteralString" xmi:id="time_max_1_expr" value="1s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeObservation" xmi:id="time_obs_min"/>
            <packagedElement xmi:type="uml:TimeObservation" xmi:id="time_obs_max"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    report = build_sysdesim_phase78_report(str(xml_file))

    assert [item.step_id for item in report.steps] == ["s01", "s02", "s03", "s04"]

    step1, step2, step3, step4 = report.steps
    assert isinstance(step1.actions[0], SysDeSimTimelineEmitAction)
    assert step1.actions[0].machine_event_path == "/SIG1"
    assert step1.direction == "inbound"

    assert isinstance(step2.actions[0], SysDeSimTimelineSetInputAction)
    assert step2.actions[0].input_name == "rmt"
    assert step2.actions[0].raw_name == "Rmt"
    assert step2.actions[0].value_text == "4999"

    assert step3.actions == ()
    assert step3.direction == "self"
    assert step3.notes == ("self_message",)

    assert step4.actions == ()
    assert step4.direction == "outbound"
    assert "outbound_signal=SigReply" in step4.notes
    assert "machine_relevant_direction_mismatch" in step4.notes

    assert len(report.time_windows) == 1
    assert report.time_windows[0].step_id == "s03"
    assert report.time_windows[0].value_text == "0s-1s"

    assert len(report.duration_constraints) == 1
    assert report.duration_constraints[0].left_step_id == "s01"
    assert report.duration_constraints[0].right_step_id == "s04"
    assert report.duration_constraints[0].value_text == "20s-30s"
