"""Unit tests for the SysDeSim Phase9/10/11 compatibility and SMT layers."""

from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest

from pyfcstm.convert.sysdesim import (
    build_sysdesim_state_coexistence_constraint_preview,
    build_sysdesim_state_coexistence_timeline_report,
    build_sysdesim_phase10_report,
    build_sysdesim_phase9_report,
    build_sysdesim_termination_summary,
    build_sysdesim_timeline_import_report,
    format_sysdesim_termination_summary_lines,
    solve_sysdesim_state_coexistence,
)
from pyfcstm.convert.sysdesim.timeline_verify import (
    _output_contains_source_path,
    _state_seen_in_trace,
)

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def _build_parallel_timeline_xml(tmp_path: Path) -> Path:
    """Build one compact parallel SysDeSim sample for Phase9/10/11 testing."""
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Coexist" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Coexist">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_start" source="state_idle" target="state_control">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_root_start" event="signal_evt_start"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_control" name="Control">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_f"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_fw" source="state_f" target="state_w">
                        <ownedRule xmi:type="uml:Constraint" xmi:id="guard_fw_rule">
                          <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_fw_expr">
                            <body>c &lt; d</body>
                          </specification>
                        </ownedRule>
                      </transition>
                      <transition xmi:type="uml:Transition" xmi:id="tx_wh" source="state_w" target="state_h">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_wh" event="signal_evt_sig2"/>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_f" name="F"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_w" name="W"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_h" name="H">
                        <region xmi:type="uml:Region" xmi:id="region_h" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_h_init" source="init_h" target="state_l"/>
                          <transition xmi:type="uml:Transition" xmi:id="tx_lm" source="state_l" target="state_m">
                            <trigger xmi:type="uml:Trigger" xmi:id="trigger_lm" event="signal_evt_sig9"/>
                          </transition>
                          <transition xmi:type="uml:Transition" xmi:id="tx_ml" source="state_m" target="state_l">
                            <trigger xmi:type="uml:Trigger" xmi:id="trigger_ml" event="signal_evt_sig6"/>
                          </transition>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_h"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_l" name="L"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_m" name="M"/>
                        </region>
                      </subvertex>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_j"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_jk" source="state_j" target="state_k">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_jk" event="signal_evt_sig2"/>
                      </transition>
                      <transition xmi:type="uml:Transition" xmi:id="tx_ks" source="state_k" target="state_s">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_ks" event="signal_evt_sig4"/>
                      </transition>
                      <transition xmi:type="uml:Transition" xmi:id="tx_sx" source="state_s" target="state_x"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_xs" source="state_x" target="state_s">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_xs" event="signal_evt_sig4"/>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_j" name="J"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_k" name="K"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_s" name="S"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_x" name="X"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario 1">
                <ownedRule xmi:type="uml:DurationConstraint" xmi:id="dur_rule_1" constrainedElement="msg_sig2 msg_sig4">
                  <specification xmi:type="uml:DurationInterval" xmi:id="dur_interval_1" min="dur_min_1" max="dur_max_1"/>
                </ownedRule>
                <ownedRule xmi:type="uml:TimeConstraint" xmi:id="time_rule_1" constrainedElement="msg_self">
                  <specification xmi:type="uml:TimeInterval" xmi:id="time_interval_1" min="time_min_1" max="time_max_1"/>
                </ownedRule>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_send" covered="ll_module" message="msg_start"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_recv" covered="ll_control" message="msg_start"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_c" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_c_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_c_expr">
                      <body>c=0</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="self_send" covered="ll_control" message="msg_self"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="self_recv" covered="ll_control" message="msg_self"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_d" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_d_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_d_expr">
                      <body>d=0</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_send" covered="ll_module" message="msg_sig2"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig2_recv" covered="ll_control" message="msg_sig2"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig9_send" covered="ll_control" message="msg_sig9"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig9_recv" covered="ll_module" message="msg_sig9"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig4_send" covered="ll_module" message="msg_sig4"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig4_recv" covered="ll_control" message="msg_sig4"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_send" covered="ll_control" message="msg_tail"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_recv" covered="ll_module" message="msg_tail"/>
                <message xmi:type="uml:Message" xmi:id="msg_start" sendEvent="start_send" receiveEvent="start_recv" signature="signal_start"/>
                <message xmi:type="uml:Message" xmi:id="msg_self" sendEvent="self_send" receiveEvent="self_recv"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig2" sendEvent="sig2_send" receiveEvent="sig2_recv" signature="signal_sig2"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig9" sendEvent="sig9_send" receiveEvent="sig9_recv" signature="signal_sig9"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig4" sendEvent="sig4_send" receiveEvent="sig4_recv" signature="signal_sig4"/>
                <message xmi:type="uml:Message" xmi:id="msg_tail" sendEvent="tail_send" receiveEvent="tail_recv" signature="signal_tail"/>
              </ownedBehavior>
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_c" name="c">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Real"/>
                <defaultValue xmi:type="uml:LiteralReal" xmi:id="var_c_default" value="0.0"/>
              </ownedAttribute>
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_d" name="d">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Real"/>
                <defaultValue xmi:type="uml:LiteralReal" xmi:id="var_d_default" value="0.0"/>
              </ownedAttribute>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_start" name="Sig1"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_start" signal="signal_start"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig2" name="Sig2"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig2" signal="signal_sig2"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig4" name="Sig4"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig4" signal="signal_sig4"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig6" name="Sig6"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig6" signal="signal_sig6"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig9" name="Sig9"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig9" signal="signal_sig9"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_tail" name="Sig11"/>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_min_1" observation="dur_obs_min">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_min_1_expr" value="10s"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Duration" xmi:id="dur_max_1" observation="dur_obs_max">
              <expr xmi:type="uml:LiteralString" xmi:id="dur_max_1_expr" value="10s"/>
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


def _build_same_level_final_timeline_xml(tmp_path: Path) -> Path:
    """Build a compact timeline where one inbound signal terminates the runtime."""
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Ended" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Ended">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_end" source="state_idle" target="final_root">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_end" event="signal_evt_end"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_tail" source="state_other" target="state_other">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_tail" event="signal_evt_tail"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_other" name="Other"/>
                  <subvertex xmi:type="uml:FinalState" xmi:id="final_root" name=""/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_internal" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_internal_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_internal_expr">
                      <body>ready</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="end_send" covered="ll_module" message="msg_end"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="end_recv" covered="ll_control" message="msg_end"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_send" covered="ll_module" message="msg_tail"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_recv" covered="ll_control" message="msg_tail"/>
                <message xmi:type="uml:Message" xmi:id="msg_end" sendEvent="end_send" receiveEvent="end_recv" signature="signal_end"/>
                <message xmi:type="uml:Message" xmi:id="msg_tail" sendEvent="tail_send" receiveEvent="tail_recv" signature="signal_tail"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_end" name="SigEnd"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_end" signal="signal_end"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_tail" name="SigTail"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_tail" signal="signal_tail"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )


def _build_hidden_auto_final_timeline_xml(tmp_path: Path) -> Path:
    """Build a compact timeline where a hidden auto transition terminates."""
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Auto Ended" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Auto Ended">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_start" source="state_idle" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_start" event="signal_evt_start"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_done_final" source="state_done" target="final_root"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_tail" source="state_other" target="state_other">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_tail" event="signal_evt_tail"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_other" name="Other"/>
                  <subvertex xmi:type="uml:FinalState" xmi:id="final_root" name=""/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_internal" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_internal_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_internal_expr">
                      <body>ready</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_send" covered="ll_module" message="msg_start"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_recv" covered="ll_control" message="msg_start"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_send" covered="ll_module" message="msg_tail"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_recv" covered="ll_control" message="msg_tail"/>
                <message xmi:type="uml:Message" xmi:id="msg_start" sendEvent="start_send" receiveEvent="start_recv" signature="signal_start"/>
                <message xmi:type="uml:Message" xmi:id="msg_tail" sendEvent="tail_send" receiveEvent="tail_recv" signature="signal_tail"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_start" name="SigStart"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_start" signal="signal_start"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_tail" name="SigTail"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_tail" signal="signal_tail"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )


def _build_parallel_hidden_auto_final_timeline_xml(tmp_path: Path) -> Path:
    """Build a two-output timeline where one split output terminates early."""
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Parallel Ended" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Parallel Ended">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_control"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:FinalState" xmi:id="final_root" name=""/>
                  <subvertex xmi:type="uml:State" xmi:id="state_control" name="Control">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_start" source="state_idle" target="state_done">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_start" event="signal_evt_start"/>
                      </transition>
                      <transition xmi:type="uml:Transition" xmi:id="tx_done_final" source="state_done" target="final_root"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_wait"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_tail" source="state_wait" target="state_other">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_tail" event="signal_evt_tail"/>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_other" name="Other"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_internal" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_internal_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_internal_expr">
                      <body>ready</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_send" covered="ll_module" message="msg_start"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_recv" covered="ll_control" message="msg_start"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_send" covered="ll_module" message="msg_tail"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_recv" covered="ll_control" message="msg_tail"/>
                <message xmi:type="uml:Message" xmi:id="msg_start" sendEvent="start_send" receiveEvent="start_recv" signature="signal_start"/>
                <message xmi:type="uml:Message" xmi:id="msg_tail" sendEvent="tail_send" receiveEvent="tail_recv" signature="signal_tail"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_start" name="SigStart"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_start" signal="signal_start"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_tail" name="SigTail"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_tail" signal="signal_tail"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )


def _build_unclosed_child_final_timeline_xml(tmp_path: Path) -> Path:
    """Build a nested final that cannot close the parent composite."""
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timeline Unclosed Child Final" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timeline Unclosed Child Final">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_parent"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                    <region xmi:type="uml:Region" xmi:id="region_parent" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_parent_init" source="init_parent" target="state_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_start" source="state_idle" target="state_done">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_start" event="signal_evt_start"/>
                      </transition>
                      <transition xmi:type="uml:Transition" xmi:id="tx_done_final" source="state_done" target="final_parent"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_parent"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                      <subvertex xmi:type="uml:FinalState" xmi:id="final_parent" name=""/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_control" name="控制"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_module" name="模块"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_control" name="控制" represents="prop_control"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_module" name="模块" represents="prop_module"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_internal" covered="ll_control">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_internal_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_internal_expr">
                      <body>ready</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_send" covered="ll_module" message="msg_start"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="start_recv" covered="ll_control" message="msg_start"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_send" covered="ll_module" message="msg_tail"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="tail_recv" covered="ll_control" message="msg_tail"/>
                <message xmi:type="uml:Message" xmi:id="msg_start" sendEvent="start_send" receiveEvent="start_recv" signature="signal_start"/>
                <message xmi:type="uml:Message" xmi:id="msg_tail" sendEvent="tail_send" receiveEvent="tail_recv" signature="signal_tail"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_start" name="SigStart"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_start" signal="signal_start"/>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_tail" name="SigTail"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_tail" signal="signal_tail"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )


def test_phase9_builds_output_family_from_parallel_timeline_xml(tmp_path: Path):
    """Phase9 should expose the compatibility output family and parsed models."""
    xml_file = _build_parallel_timeline_xml(tmp_path)

    report = build_sysdesim_phase9_report(str(xml_file))

    assert report.selected_machine_name == "Timeline Coexist"
    assert report.selected_interaction_name == "Scenario 1"
    assert [item.output_name for item in report.outputs] == [
        "TimelineCoexist",
        "TimelineCoexist__Control_region1",
        "TimelineCoexist__Control_region2",
    ]

    left_output = {item.output_name: item for item in report.outputs}[
        "TimelineCoexist__Control_region1"
    ]
    right_output = {item.output_name: item for item in report.outputs}[
        "TimelineCoexist__Control_region2"
    ]

    assert left_output.define_names == ("c", "d")
    assert "/SIG1" in left_output.event_runtime_refs
    assert "/SIG2" in left_output.event_runtime_refs
    assert "/SIG9" in left_output.event_runtime_refs
    assert right_output.define_names == ()
    assert "/SIG4" in right_output.event_runtime_refs


def test_phase10_builds_runtime_traces_and_hidden_auto_windows(tmp_path: Path):
    """Phase10 should build bindings, normalized timing, and auto-closure traces."""
    xml_file = _build_parallel_timeline_xml(tmp_path)

    report = build_sysdesim_phase10_report(str(xml_file))

    assert [item.step_id for item in report.scenario.steps] == [
        "s01",
        "s02",
        "s03",
        "s04",
        "s05",
        "s06",
        "s07",
        "s08",
    ]
    assert [
        (
            item.left_step_id,
            item.right_step_id,
            item.min_seconds_text,
            item.max_seconds_text,
            item.strict_lower,
        )
        for item in report.scenario.temporal_constraints
    ] == [
        ("s02", "s03", "0", "1", True),
        ("s05", "s07", "10", "10", False),
    ]

    binding_index = {item.machine_alias: item for item in report.bindings}
    assert binding_index["TimelineCoexist__Control_region1"].event_map == {
        "Sig1": "/SIG1",
        "Sig2": "/SIG2",
    }
    assert binding_index["TimelineCoexist__Control_region1"].input_map == {
        "c": "c",
        "d": "d",
    }
    assert binding_index["TimelineCoexist__Control_region2"].event_map == {
        "Sig1": "/SIG1",
        "Sig2": "/SIG2",
        "Sig4": "/SIG4",
    }

    trace_index = {item.machine_alias: item for item in report.traces}
    left_trace = trace_index["TimelineCoexist__Control_region1"]
    right_trace = trace_index["TimelineCoexist__Control_region2"]

    assert [item.post_state_path for item in left_trace.steps] == [
        "TimelineCoexist.Control.F",
        "TimelineCoexist.Control.F",
        "TimelineCoexist.Control.F",
        "TimelineCoexist.Control.F",
        "TimelineCoexist.Control.F",
        "TimelineCoexist.Control.F",
        "TimelineCoexist.Control.F",
        "TimelineCoexist.Control.F",
    ]
    assert [item.post_state_path for item in right_trace.steps] == [
        "TimelineCoexist.Control.J",
        "TimelineCoexist.Control.J",
        "TimelineCoexist.Control.J",
        "TimelineCoexist.Control.J",
        "TimelineCoexist.Control.K",
        "TimelineCoexist.Control.K",
        "TimelineCoexist.Control.S",
        "TimelineCoexist.Control.X",
    ]
    assert right_trace.steps[6].stabilized_state_path == "TimelineCoexist.Control.X"
    assert [
        (item.occurrence_symbol, item.from_state_path, item.to_state_path)
        for item in right_trace.steps[6].auto_occurrences
    ] == [
        (
            "tau__TimelineCoexist__Control_region2__s07__1",
            "TimelineCoexist.Control.S",
            "TimelineCoexist.Control.X",
        )
    ]
    assert [
        (item.source_step_id, item.state_path, item.start_symbol, item.end_symbol)
        for item in right_trace.state_windows
        if item.source_step_id == "s07"
    ] == [
        (
            "s07",
            "TimelineCoexist.Control.S",
            "t07",
            "tau__TimelineCoexist__Control_region2__s07__1",
        ),
        (
            "s07",
            "TimelineCoexist.Control.X",
            "tau__TimelineCoexist__Control_region2__s07__1",
            "t08",
        ),
    ]


def test_phase11_solves_sat_and_unsat_state_coexistence_queries(tmp_path: Path):
    """Phase11 should provide exact Z3 answers for both SAT and UNSAT cases."""
    xml_file = _build_parallel_timeline_xml(tmp_path)

    sat_preview = build_sysdesim_state_coexistence_constraint_preview(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "F",
        "TimelineCoexist__Control_region2",
        "X",
    )
    assert ("t07", "场景 step `s07` 的观测时刻。") in sat_preview.symbol_meanings
    assert (
        "tau__TimelineCoexist__Control_region2__s07__1",
        "隐藏 auto occurrence：TimelineCoexist.Control.S -> TimelineCoexist.Control.X 在 step `s07` 之后的内部发生时刻。",
    ) in sat_preview.symbol_meanings
    assert "0 <= t01" in sat_preview.base_constraints
    assert (
        "tau__TimelineCoexist__Control_region2__s07__1 > t07"
        in sat_preview.base_constraints
    )
    assert (
        "tau__TimelineCoexist__Control_region2__s07__1 < t08"
        in sat_preview.base_constraints
    )
    assert sat_preview.candidate_count > 0
    assert "接受两类证据" in sat_preview.query_summary
    assert "post_step(s08)" in sat_preview.query_summary
    assert "最早可在 `post_step(s08)` 构造" in sat_preview.candidate_notes[1]

    sat_result = solve_sysdesim_state_coexistence(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "F",
        "TimelineCoexist__Control_region2",
        "X",
    )
    assert sat_result.status == "sat"
    assert sat_result.solver_status == "sat"
    assert sat_result.observation_kind == "post_step"
    assert any(
        symbol == "tau__TimelineCoexist__Control_region2__s07__1"
        for symbol, _ in sat_result.time_values
    )
    final_states = dict(sat_result.witness_steps[-1].machine_states)
    assert (
        final_states["TimelineCoexist__Control_region1"] == "TimelineCoexist.Control.F"
    )
    assert (
        final_states["TimelineCoexist__Control_region2"] == "TimelineCoexist.Control.X"
    )

    interval_result = solve_sysdesim_state_coexistence(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "F",
        "TimelineCoexist__Control_region2",
        "X",
        observation_scope="open_interval",
    )
    assert interval_result.status == "sat"
    assert interval_result.observation_kind == "open_interval"

    unsat_result = solve_sysdesim_state_coexistence(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "M",
        "TimelineCoexist__Control_region2",
        "X",
    )
    unsat_preview = build_sysdesim_state_coexistence_constraint_preview(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "M",
        "TimelineCoexist__Control_region2",
        "X",
    )
    assert unsat_result.status == "unsat"
    assert unsat_result.solver_status == "unsat"
    assert (
        unsat_result.reason
        == "The left queried state never appears in the imported trajectory."
    )
    assert unsat_result.time_values == ()
    assert unsat_result.witness_steps == ()
    assert unsat_preview.candidate_count == 0
    assert "这个查询恒为假" in unsat_preview.query_summary
    assert unsat_preview.candidate_notes == (
        "`TimelineCoexist__Control_region1` 的 `TimelineCoexist.Control.H.M` 在当前导入轨迹里一次都没有出现，所以不存在可构造的共存点。",
    )


def test_phase11_accepts_initial_state_coexistence_before_first_step(tmp_path: Path):
    """Initial stable states should count as a valid coexistence witness."""
    xml_file = _build_parallel_timeline_xml(tmp_path)

    preview = build_sysdesim_state_coexistence_constraint_preview(
        str(xml_file),
        "TimelineCoexist",
        "Idle",
        "TimelineCoexist__Control_region1",
        "Idle",
    )
    result = solve_sysdesim_state_coexistence(
        str(xml_file),
        "TimelineCoexist",
        "Idle",
        "TimelineCoexist__Control_region1",
        "Idle",
    )
    timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_file),
        "TimelineCoexist",
        "Idle",
        "TimelineCoexist__Control_region1",
        "Idle",
    )

    assert ("t00", "导入场景开始前的初始稳定时刻。") in preview.symbol_meanings
    assert "initial(t00)" in preview.query_summary
    assert preview.candidate_count == 2
    assert result.status == "sat"
    assert result.observation_kind == "initial"
    assert result.witness_notes == ("violation_at_initial=t00",)
    assert timeline.status == "sat"
    assert timeline.first_coexistence_symbol == "t00"
    assert timeline.timeline_points[0].point_kind == "initial"
    assert timeline.timeline_points[0].machine_states[:2] == (
        ("TimelineCoexist", "TimelineCoexist.Idle"),
        ("TimelineCoexist__Control_region1", "TimelineCoexist.Idle"),
    )


def test_phase11_builds_single_solved_timeline_report(tmp_path: Path):
    """The simplified timeline report should expose one readable witness line."""
    xml_file = _build_parallel_timeline_xml(tmp_path)

    sat_timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "F",
        "TimelineCoexist__Control_region2",
        "X",
    )
    assert sat_timeline.status == "sat"
    assert sat_timeline.solver_status == "sat"
    assert sat_timeline.time_domain == "real"
    assert (
        sat_timeline.first_coexistence_symbol
        == "tau__TimelineCoexist__Control_region2__s07__1"
    )
    assert sat_timeline.first_coexistence_time_text is not None
    assert sat_timeline.first_coexistence_note is not None
    assert sat_timeline.timeline_points
    assert sat_timeline.timeline_points[-1].machine_states[-1] == (
        "TimelineCoexist__Control_region2",
        "TimelineCoexist.Control.X",
    )
    assert any(item.is_coexistent for item in sat_timeline.timeline_points)

    unsat_timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "M",
        "TimelineCoexist__Control_region2",
        "X",
    )
    assert unsat_timeline.status == "unsat"
    assert unsat_timeline.solver_status == "unsat"
    assert unsat_timeline.time_domain == "real"
    assert unsat_timeline.timeline_points == ()
    assert (
        unsat_timeline.reason
        == "The left queried state never appears in the imported trajectory."
    )


def test_phase11_accepts_suffix_state_refs_for_nested_states(tmp_path: Path):
    """Nested suffix state refs such as ``H.M`` should resolve for coexistence queries."""
    xml_file = _build_parallel_timeline_xml(tmp_path)

    unsat_timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_file),
        "TimelineCoexist__Control_region1",
        "H.M",
        "TimelineCoexist__Control_region2",
        "S",
    )

    assert unsat_timeline.status == "unsat"
    assert unsat_timeline.solver_status == "unsat"
    assert unsat_timeline.timeline_points == ()
    assert (
        unsat_timeline.reason
        == "The left queried state never appears in the imported trajectory."
    )


def test_phase10_marks_same_level_final_runtime_as_ended_after_signal(
    tmp_path: Path,
):
    """A signal transition to ``[*]`` should keep later trace rows safe."""
    xml_file = _build_same_level_final_timeline_xml(tmp_path)

    report = build_sysdesim_phase10_report(str(xml_file))

    assert [trace.machine_alias for trace in report.traces] == ["TimelineEnded"]
    trace = report.traces[0]
    assert trace.initial_state_path == "TimelineEnded.Idle"
    assert [step.step_id for step in trace.steps] == ["s01", "s02"]
    assert (
        trace.steps[0].pre_state_path,
        trace.steps[0].bound_event_path,
        trace.steps[0].post_state_path,
        trace.steps[0].stabilized_state_path,
    ) == ("TimelineEnded.Idle", "/SIGEND", "[*]", "[*]")
    assert (
        trace.steps[1].pre_state_path,
        trace.steps[1].bound_event_path,
        trace.steps[1].post_state_path,
        trace.steps[1].stabilized_state_path,
    ) == ("[*]", "/SIGTAIL", "[*]", "[*]")
    assert trace.steps[0].auto_occurrences == ()
    assert trace.steps[1].auto_occurrences == ()
    assert [
        (item.source_step_id, item.state_path, item.start_symbol, item.end_symbol)
        for item in trace.state_windows
    ] == [
        ("initial", "TimelineEnded.Idle", "t00", "t01"),
        ("s01", "[*]", "t01", "t02"),
    ]
    assert not any(
        "__sysdesim_final_" in value
        for step in trace.steps
        for value in (
            step.pre_state_path,
            step.post_state_path,
            step.stabilized_state_path,
        )
    )


def test_phase10_records_hidden_auto_final_transition_to_ended(tmp_path: Path):
    """A hidden auto transition that exits should be recorded as ``Done -> [*]``."""
    xml_file = _build_hidden_auto_final_timeline_xml(tmp_path)

    report = build_sysdesim_phase10_report(str(xml_file))

    trace = report.traces[0]
    assert trace.machine_alias == "TimelineAutoEnded"
    assert trace.initial_state_path == "TimelineAutoEnded.Idle"
    assert (
        trace.steps[0].pre_state_path,
        trace.steps[0].bound_event_path,
        trace.steps[0].post_state_path,
        trace.steps[0].stabilized_state_path,
    ) == (
        "TimelineAutoEnded.Idle",
        "/SIGSTART",
        "TimelineAutoEnded.Done",
        "[*]",
    )
    assert [
        (
            item.occurrence_symbol,
            item.from_state_path,
            item.to_state_path,
            item.right_observation_step_id,
            item.right_emit_step_id,
        )
        for item in trace.steps[0].auto_occurrences
    ] == [
        (
            "tau__TimelineAutoEnded__s01__1",
            "TimelineAutoEnded.Done",
            "[*]",
            "s02",
            "s02",
        )
    ]
    assert (
        trace.steps[1].pre_state_path,
        trace.steps[1].bound_event_path,
        trace.steps[1].post_state_path,
        trace.steps[1].stabilized_state_path,
        trace.steps[1].auto_occurrences,
    ) == ("[*]", "/SIGTAIL", "[*]", "[*]", ())
    assert [
        (
            item.source_step_id,
            item.state_path,
            item.start_symbol,
            item.end_symbol,
            item.note,
        )
        for item in trace.state_windows
    ] == [
        (
            "initial",
            "TimelineAutoEnded.Idle",
            "t00",
            "t01",
            "initial_before_first_step",
        ),
        (
            "s01",
            "TimelineAutoEnded.Done",
            "t01",
            "tau__TimelineAutoEnded__s01__1",
            "before_hidden_auto",
        ),
        (
            "s01",
            "[*]",
            "tau__TimelineAutoEnded__s01__1",
            "t02",
            "after_hidden_auto",
        ),
    ]


def test_phase11_does_not_extend_pre_ended_state_windows(tmp_path: Path):
    """Ended split outputs should not keep their final ordinary state alive."""
    xml_file = _build_parallel_hidden_auto_final_timeline_xml(tmp_path)

    phase10 = build_sysdesim_phase10_report(str(xml_file))
    trace_index = {trace.machine_alias: trace for trace in phase10.traces}
    left_trace = trace_index["TimelineParallelEnded__Control_region1"]
    right_trace = trace_index["TimelineParallelEnded__Control_region2"]

    assert left_trace.steps[0].post_state_path == "TimelineParallelEnded.Control.Done"
    assert left_trace.steps[0].stabilized_state_path == "[*]"
    assert left_trace.steps[1].pre_state_path == "[*]"
    assert right_trace.steps[1].post_state_path == "TimelineParallelEnded.Control.Other"
    assert [
        (item.state_path, item.start_symbol, item.end_symbol)
        for item in left_trace.state_windows
        if item.state_path == "TimelineParallelEnded.Control.Done"
    ] == [
        (
            "TimelineParallelEnded.Control.Done",
            "t01",
            "tau__TimelineParallelEnded__Control_region1__s01__1",
        )
    ]

    preview = build_sysdesim_state_coexistence_constraint_preview(
        str(xml_file),
        "TimelineParallelEnded__Control_region1",
        "Done",
        "TimelineParallelEnded__Control_region2",
        "Other",
    )
    result = solve_sysdesim_state_coexistence(
        str(xml_file),
        "TimelineParallelEnded__Control_region1",
        "Done",
        "TimelineParallelEnded__Control_region2",
        "Other",
    )
    assert preview.candidate_count == 0
    assert result.status == "unsat"
    assert result.solver_status == "unsat"

    interval_result = solve_sysdesim_state_coexistence(
        str(xml_file),
        "TimelineParallelEnded__Control_region1",
        "Done",
        "TimelineParallelEnded__Control_region2",
        "Wait",
        observation_scope="open_interval",
    )
    assert interval_result.status == "sat"
    assert interval_result.observation_kind == "open_interval"


def test_phase10_real_cross_level_final_fixture_handles_ended_without_hidden_final():
    """The real model0608 fixture should remain importable after ended support."""
    xml_file = (
        Path(__file__).parents[2]
        / "testfile/sysdesim/final_state_cross_level_model0608.xml"
    )

    report = build_sysdesim_phase10_report(str(xml_file))

    all_state_paths = [
        value
        for trace in report.traces
        for step in trace.steps
        for value in (
            step.pre_state_path,
            step.post_state_path,
            step.stabilized_state_path,
        )
    ]
    all_state_paths.extend(
        value
        for trace in report.traces
        for window in trace.state_windows
        for value in (window.state_path,)
    )
    assert all_state_paths
    assert not any("__sysdesim_final_" in value for value in all_state_paths)


def test_phase10_does_not_record_failed_unclosed_child_final_auto(
    tmp_path: Path,
):
    """A rejected child-final auto transition should not create fake tau rows."""
    xml_file = _build_unclosed_child_final_timeline_xml(tmp_path)

    report = build_sysdesim_phase10_report(str(xml_file))

    trace = report.traces[0]
    assert [step.post_state_path for step in trace.steps] == [
        "TimelineUnclosedChildFinal.Parent.Done",
        "TimelineUnclosedChildFinal.Parent.Done",
    ]
    assert [step.stabilized_state_path for step in trace.steps] == [
        "TimelineUnclosedChildFinal.Parent.Done",
        "TimelineUnclosedChildFinal.Parent.Done",
    ]

    assert all(step.auto_occurrences == () for step in trace.steps)
    assert not _state_seen_in_trace(trace, "[*]")
    assert [
        (item.source_step_id, item.state_path, item.start_symbol, item.end_symbol)
        for item in trace.state_windows
    ] == [
        ("initial", "TimelineUnclosedChildFinal.Parent.Idle", "t00", "t01"),
        ("s01", "TimelineUnclosedChildFinal.Parent.Done", "t01", "t02"),
    ]


def test_final_state_termination_summary_uses_trace_alias_when_no_output_matches():
    """FinalState rows should still report a trace when source matching fails."""

    class FakeMachine:
        """Minimal machine stub exposing the ``walk_states`` contract."""

        def walk_states(self):
            """Return one unrelated state so source-path matching fails."""
            return [
                SimpleNamespace(
                    path=("Root", "Other"),
                    name="Other",
                    extra_name=None,
                )
            ]

    phase10_report = SimpleNamespace(
        phase9_report=SimpleNamespace(
            phase78_report=SimpleNamespace(
                machine_graph=[
                    SimpleNamespace(
                        source_path=("NoSuchSource",),
                        target_id="final_root",
                        target_path=("Root",),
                        target_vertex_type="final",
                        transition_ids=("tx_end",),
                    )
                ],
            ),
            outputs=(
                SimpleNamespace(
                    output_name="NoMatchOutput",
                    machine=FakeMachine(),
                ),
            ),
        ),
        traces=(
            SimpleNamespace(
                machine_alias="TraceOnlyOutput",
                steps=(
                    SimpleNamespace(
                        step_id="s01",
                        post_state_path="[*]",
                        stabilized_state_path="[*]",
                    ),
                ),
            ),
        ),
    )

    summary = build_sysdesim_termination_summary(phase10_report)

    assert summary == [
        {
            "machine_alias": "TraceOnlyOutput",
            "source_path": ["NoSuchSource"],
            "target_id": "final_root",
            "target_path": ["Root"],
            "target_vertex_type": "final",
            "transition_ids": ["tx_end"],
            "reached": True,
            "ended_step_ids": ["s01"],
        }
    ]


def test_final_state_termination_formatter_accepts_scalar_defensive_fields():
    """Formatter should degrade predictably for scalar report fields."""
    lines = format_sysdesim_termination_summary_lines(
        [
            {
                "machine_alias": "MachineA",
                "source_path": "Root.Idle",
                "target_id": "final_root",
                "transition_ids": "tx_end",
                "ended_step_ids": "s01",
                "reached": False,
            }
        ]
    )

    assert lines == [
        "未触发终止: MachineA has XML FinalState final_root via "
        "transition tx_end from Root.Idle."
    ]


def test_output_contains_source_path_handles_empty_and_incomplete_paths():
    """Source-path matching should reject empty and incomplete fake machines."""

    class IncompleteMachine:
        """Machine stub missing the parent path for its only leaf state."""

        def walk_states(self):
            """Return only the leaf, forcing a missing-parent lookup."""
            return [
                SimpleNamespace(
                    path=("Root", "Parent", "Leaf"),
                    name="Leaf",
                    extra_name="LeafLabel",
                )
            ]

    output = SimpleNamespace(machine=IncompleteMachine())

    assert not _output_contains_source_path(output, ())
    assert not _output_contains_source_path(output, ("ParentLabel", "LeafLabel"))


def test_timeline_import_report_rejects_partial_phase11_query(tmp_path: Path):
    """Phase11 query arguments should be provided as an all-or-nothing group."""
    xml_file = _build_same_level_final_timeline_xml(tmp_path)

    with pytest.raises(ValueError):
        build_sysdesim_timeline_import_report(
            str(xml_file),
            left_machine_alias="TimelineEnded",
        )
