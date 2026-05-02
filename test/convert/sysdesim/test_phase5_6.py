"""Unit tests for the SysDeSim Phase5/6 timeline-oriented extraction layer."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import (
    SysDeSimDurationConstraintObservation,
    SysDeSimMessageObservation,
    SysDeSimStateInvariantObservation,
    SysDeSimTimeConstraintObservation,
    SysDeSimTriggerCondition,
    SysDeSimTriggerNone,
    SysDeSimTriggerSignal,
    build_sysdesim_phase56_report,
    extract_sysdesim_interactions,
)

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def test_phase5_extracts_interaction_stream_directions_and_constraints(tmp_path: Path):
    """Phase5 should extract a stable interaction observation stream from UML sequence data."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Demo" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Demo">
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
                  <transition xmi:type="uml:Transition" xmi:id="tx_change_guard_y" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_change_y" event="change_evt_y"/>
                    <ownedRule xmi:type="uml:Constraint" xmi:id="guard_y_rule">
                      <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_y_expr">
                        <body>y &gt; 1000</body>
                      </specification>
                    </ownedRule>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_finish" source="state_done" target="state_finish"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_active" name="Active"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_finish" name="Finish"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario 1">
                <ownedRule xmi:type="uml:DurationConstraint" xmi:id="dur_rule_1" constrainedElement="msg_go msg_reply">
                  <specification xmi:type="uml:DurationInterval" xmi:id="dur_interval_1" min="dur_min_1" max="dur_max_1"/>
                </ownedRule>
                <ownedRule xmi:type="uml:TimeConstraint" xmi:id="time_rule_1" constrainedElement="msg_note">
                  <specification xmi:type="uml:TimeInterval" xmi:id="time_interval_1" min="time_min_1" max="time_max_1"/>
                </ownedRule>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_rmt" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_rmt_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_rmt_expr">
                      <body>Rmt=4999</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_send" name="sendEvent" covered="ll_module" message="msg_go"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_recv" name="receiveEvent" covered="ll_control" message="msg_go"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="note_send" name="sendEvent" covered="ll_control" message="msg_note"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="note_recv" name="receiveEvent" covered="ll_control" message="msg_note"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="reply_send" name="sendEvent" covered="ll_control" message="msg_reply"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="reply_recv" name="receiveEvent" covered="ll_module" message="msg_reply"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_y" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_y_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_y_expr">
                      <body>y=1300</body>
                    </specification>
                  </invariant>
                </fragment>
                <message xmi:type="uml:Message" xmi:id="msg_go" name="" messageSort="asynchCall" sendEvent="go_send" receiveEvent="go_recv" signature="signal_go"/>
                <message xmi:type="uml:Message" xmi:id="msg_note" name="" sendEvent="note_send" receiveEvent="note_recv"/>
                <message xmi:type="uml:Message" xmi:id="msg_reply" name="回复" messageSort="asynchCall" sendEvent="reply_send" receiveEvent="reply_recv" signature="signal_reply"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Sig1"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_go" signal="signal_go"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_reply" name="SigReply"/>
            <packagedElement xmi:type="uml:ChangeEvent" xmi:id="change_evt_rmt">
              <changeExpression xmi:type="uml:OpaqueExpression" xmi:id="change_rmt_expr">
                <body>R_mt &lt; 5000</body>
              </changeExpression>
            </packagedElement>
            <packagedElement xmi:type="uml:ChangeEvent" xmi:id="change_evt_y">
              <changeExpression xmi:type="uml:OpaqueExpression" xmi:id="change_y_expr">
                <body>y &lt; 2100</body>
              </changeExpression>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_min_1" name="MinDuration1" observation="dur_obs_min">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_min_1_expr" value="20s-30s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_max_1" name="MaxDuration1" observation="dur_obs_max">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_max_1_expr" value="20s-30s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_min"/>
            <packagedElement xmi:type="uml:DurationObservation" xmi:id="dur_obs_max"/>
            <packagedElement xmi:type="uml:TimeExpression" xmi:id="time_min_1" name="timeExpression" observation="time_obs_min">
              <expr xmi:type="uml:LiteralString" xmi:id="time_min_1_expr" value="0s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeExpression" xmi:id="time_max_1" name="timeExpression" observation="time_obs_max">
              <expr xmi:type="uml:LiteralString" xmi:id="time_max_1_expr" value="1s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeObservation" xmi:id="time_obs_min"/>
            <packagedElement xmi:type="uml:TimeObservation" xmi:id="time_obs_max"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    interactions = extract_sysdesim_interactions(str(xml_file))
    assert len(interactions) == 1
    interaction = interactions[0]

    assert interaction.interaction_name == "Scenario 1"
    assert [item.raw_name for item in interaction.lifelines] == ["控制", "模块"]
    assert interaction.internal_lifeline_ids == ("ll_control",)
    assert [
        item.raw_name for item in interaction.lifelines if item.is_machine_internal
    ] == ["控制"]
    assert interaction.activity_assignment_observations == ()

    message_items = [
        item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimMessageObservation)
    ]
    assert [item.direction for item in message_items] == ["inbound", "self", "outbound"]
    assert [item.signal_name for item in message_items] == ["Sig1", None, "SigReply"]
    assert [item.display_name for item in message_items] == ["Sig1", "", "回复"]
    assert [item.source_lifeline_name for item in message_items] == [
        "模块",
        "控制",
        "控制",
    ]
    assert [item.target_lifeline_name for item in message_items] == [
        "控制",
        "控制",
        "模块",
    ]

    invariant_items = [
        item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimStateInvariantObservation)
    ]
    assert [item.raw_text for item in invariant_items] == ["Rmt=4999", "y=1300"]
    assert [item.assignment_name for item in invariant_items] == ["Rmt", "y"]
    assert [item.normalized_name for item in invariant_items] == ["rmt", "y"]
    assert [item.value_text for item in invariant_items] == ["4999", "1300"]

    duration_items = [
        item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimDurationConstraintObservation)
    ]
    assert len(duration_items) == 1
    assert duration_items[0].constrained_element_ids == ("msg_go", "msg_reply")
    assert duration_items[0].min_text == "20s-30s"
    assert duration_items[0].max_text == "20s-30s"
    assert duration_items[0].min_observation_id == "dur_obs_min"
    assert duration_items[0].max_observation_id == "dur_obs_max"

    time_items = [
        item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimTimeConstraintObservation)
    ]
    assert len(time_items) == 1
    assert time_items[0].constrained_element_ids == ("msg_note",)
    assert time_items[0].min_text == "0s"
    assert time_items[0].max_text == "1s"
    assert time_items[0].min_observation_id == "time_obs_min"
    assert time_items[0].max_observation_id == "time_obs_max"


def test_phase6_builds_unified_triggers_and_name_hints(tmp_path: Path):
    """Phase6 should expose unified trigger objects and name normalization hints."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Demo" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Demo">
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
                  <transition xmi:type="uml:Transition" xmi:id="tx_change_guard_y" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_change_y" event="change_evt_y"/>
                    <ownedRule xmi:type="uml:Constraint" xmi:id="guard_y_rule">
                      <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_y_expr">
                        <body>y &gt; 1000</body>
                      </specification>
                    </ownedRule>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_finish" source="state_done" target="state_finish"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_active" name="Active"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_finish" name="Finish"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario 1">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_rmt" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_rmt_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_rmt_expr">
                      <body>Rmt=4999</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_y" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_y_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_y_expr">
                      <body>y=1300</body>
                    </specification>
                  </invariant>
                </fragment>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Sig1"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_go" signal="signal_go"/>
            <packagedElement xmi:type="uml:ChangeEvent" xmi:id="change_evt_rmt">
              <changeExpression xmi:type="uml:OpaqueExpression" xmi:id="change_rmt_expr">
                <body>R_mt &lt; 5000</body>
              </changeExpression>
            </packagedElement>
            <packagedElement xmi:type="uml:ChangeEvent" xmi:id="change_evt_y">
              <changeExpression xmi:type="uml:OpaqueExpression" xmi:id="change_y_expr">
                <body>y &lt; 2100</body>
              </changeExpression>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    report = build_sysdesim_phase56_report(str(xml_file))

    assert report.selected_machine_name == "Timeline Demo"
    assert report.selected_interaction_name == "Scenario 1"
    assert "implicit_condition_variable" in [item.code for item in report.diagnostics]

    transition_by_pair = {
        (item.source_path, item.target_path): item for item in report.transitions
    }

    idle_to_active = transition_by_pair[(("Idle",), ("Active",))]
    assert isinstance(idle_to_active.trigger, SysDeSimTriggerSignal)
    assert idle_to_active.trigger.signal_name == "SIG1"
    assert idle_to_active.trigger.signal_display_name == "Sig1"

    active_to_wait = transition_by_pair[(("Active",), ("Wait",))]
    assert isinstance(active_to_wait.trigger, SysDeSimTriggerCondition)
    assert active_to_wait.transition_ids == ("tx_change_rmt", "tx_guard_rmt")
    assert active_to_wait.trigger.raw_text == "rmt < 5000"
    assert active_to_wait.trigger.normalized_text == "rmt < 5000"
    assert active_to_wait.trigger.variable_names == ("R_mt", "rmt")
    assert active_to_wait.trigger.normalized_variable_names == ("rmt", "rmt")

    wait_to_done = transition_by_pair[(("Wait",), ("Done",))]
    assert isinstance(wait_to_done.trigger, SysDeSimTriggerCondition)
    assert "y < 2100" in wait_to_done.trigger.raw_text
    assert "y > 1000" in wait_to_done.trigger.raw_text
    assert wait_to_done.trigger.variable_names == ("y",)
    assert wait_to_done.trigger.normalized_variable_names == ("y",)

    done_to_finish = transition_by_pair[(("Done",), ("Finish",))]
    assert isinstance(done_to_finish.trigger, SysDeSimTriggerNone)

    hint_by_name = {item.normalized_name: item for item in report.name_hints}
    assert hint_by_name["rmt"].observation_names == ("Rmt",)
    assert hint_by_name["rmt"].trigger_variable_names == ("R_mt", "rmt")
    assert hint_by_name["y"].observation_names == ("y",)
    assert hint_by_name["y"].trigger_variable_names == ("y",)
