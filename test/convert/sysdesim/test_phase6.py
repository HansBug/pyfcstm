"""Unit tests for the SysDeSim phase6 reporting and regression pipeline."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import (
    build_sysdesim_conversion_report,
    convert_sysdesim_xml_to_dsl,
    convert_sysdesim_xml_to_dsls,
    load_sysdesim_machine,
    normalize_machine,
    prepare_sysdesim_output_machines,
)
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.model.model import StateMachine, parse_dsl_node_to_state_machine

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def _normalize_newlines(text: str) -> str:
    """Normalize text line endings to ``\\n`` for cross-platform assertions."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _assert_dsl_code_loads_to_state_machine(dsl_code: str) -> StateMachine:
    """Assert that DSL text can be parsed and loaded into the public StateMachine model."""
    parsed_program = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    model = parse_dsl_node_to_state_machine(parsed_program)
    assert isinstance(model, StateMachine)
    return model


def _walk_state_definitions(state_definition):
    """Yield one AST state definition and every nested child state definition."""
    yield state_definition
    for child_state in state_definition.substates:
        yield from _walk_state_definitions(child_state)


def test_phase6_builds_conversion_report_for_main_and_region_outputs(tmp_path: Path):
    """Phase6 should emit a stable validation report for each main/split output."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Parallel Split" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Parallel Split">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_controller"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_controller" name="Controller">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_left_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_go" source="state_left_idle" target="state_left_run"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left_idle" name="LeftIdle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left_run" name="LeftRun"/>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_right_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_go" source="state_right_idle" target="state_right_run"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_right_idle" name="RightIdle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_right_run" name="RightRun"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    dsl_outputs = {name: _normalize_newlines(code) for name, code in convert_sysdesim_xml_to_dsls(str(xml_file)).items()}
    report = build_sysdesim_conversion_report(str(xml_file))

    expected_outputs = {
        "ParallelSplit": dedent(
            """\
            state ParallelSplit named 'Parallel Split' {
                state Controller;
                [*] -> Controller;
            }"""
        ),
        "ParallelSplit__Controller_region1": dedent(
            """\
            state ParallelSplit named 'Parallel Split' {
                state Controller {
                    state LeftIdle;
                    state LeftRun;
                    [*] -> LeftIdle;
                    LeftIdle -> LeftRun;
                }
                [*] -> Controller;
            }"""
        ),
        "ParallelSplit__Controller_region2": dedent(
            """\
            state ParallelSplit named 'Parallel Split' {
                state Controller {
                    state RightIdle;
                    state RightRun;
                    [*] -> RightIdle;
                    RightIdle -> RightRun;
                }
                [*] -> Controller;
            }"""
        ),
    }

    assert dsl_outputs == expected_outputs
    for dsl_code in dsl_outputs.values():
        _assert_dsl_code_loads_to_state_machine(dsl_code)

    assert report.selected_machine_name == "Parallel Split"
    assert report.output_count == len(report.outputs)
    assert [item.output_name for item in report.outputs] == list(expected_outputs.keys())
    assert all(item.parser_roundtrip_ok for item in report.outputs)
    assert all(item.model_build_ok for item in report.outputs)
    assert all(item.guard_variables_defined for item in report.outputs)
    assert all(item.event_paths_valid for item in report.outputs)
    assert all(item.composite_states_have_init for item in report.outputs)
    assert report.outputs[0].semantic_note is not None
    assert report.outputs[1].semantic_note is not None
    assert report.outputs[2].semantic_note is not None
    assert report.to_dict()["output_count"] == 3


def test_phase6_time_transition_effects_are_ignored_with_validation_report(tmp_path: Path):
    """Time-trigger transition effects should be downgraded away while keeping DSL export valid."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timer Effect" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timer Effect">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_wait"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_timeout_kkkkkk" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_timeout"/>
                    <effect xmi:type="uml:Activity" xmi:id="effect_timeout" name="Drop Effect"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_timeout" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_timeout" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_timeout_value" name="Literal" value="1s"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    dsl_code = _normalize_newlines(convert_sysdesim_xml_to_dsl(str(xml_file), tick_duration_ms=1000.0))
    report = build_sysdesim_conversion_report(str(xml_file), tick_duration_ms=1000.0)
    expected_dsl = dedent(
        """\
        def int __sysdesim_after_wait__tx_kkkkkk_ticks = 0;
        state TimerEffect named 'Timer Effect' {
            state Wait {
                enter {
                    __sysdesim_after_wait__tx_kkkkkk_ticks = 0;
                }
                during {
                    __sysdesim_after_wait__tx_kkkkkk_ticks = __sysdesim_after_wait__tx_kkkkkk_ticks + 1;
                }
            }
            state Done;
            [*] -> Wait;
            Wait -> Done : if [__sysdesim_after_wait__tx_kkkkkk_ticks >= 1];
        }"""
    )

    assert dsl_code == expected_dsl
    _assert_dsl_code_loads_to_state_machine(dsl_code)
    assert "transition_effect_semantic_downgrade" in [item.code for item in report.outputs[0].diagnostics]


def test_phase6_cross_level_transition_effects_are_ignored_with_validation_report(tmp_path: Path):
    """Cross-level transition effects should be ignored while the route-lowered DSL remains valid."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Cross Effect" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Cross Effect">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_source"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_cross_ffffff" source="state_source" target="state_target_leaf">
                    <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rule_cross">
                      <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_expr_cross">
                        <body> count &gt; 0 </body>
                      </specification>
                    </ownedRule>
                    <effect xmi:type="uml:Activity" xmi:id="effect_cross" name="Drop Effect"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_target_branch" name="TargetBranch">
                    <region xmi:type="uml:Region" xmi:id="region_target" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_target_init" source="init_target" target="state_default_leaf"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_target"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_default_leaf" name="DefaultLeaf"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_target_leaf" name="TargetLeaf"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_count" name="count">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_count_default" value="0"/>
              </ownedAttribute>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    dsl_code = _normalize_newlines(convert_sysdesim_xml_to_dsl(str(xml_file)))
    report = build_sysdesim_conversion_report(str(xml_file))
    expected_dsl = dedent(
        """\
        def int count = 0;
        def int __sysdesim_flag_route_source__tx_ffffff = 0;
        state CrossEffect named 'Cross Effect' {
            state Source;
            state TargetBranch {
                state DefaultLeaf;
                state TargetLeaf {
                    enter {
                        __sysdesim_flag_route_source__tx_ffffff = 0;
                    }
                }
                [*] -> TargetLeaf : if [__sysdesim_flag_route_source__tx_ffffff > 0];
                [*] -> DefaultLeaf;
            }
            [*] -> Source;
            Source -> TargetBranch : if [count > 0] effect {
                __sysdesim_flag_route_source__tx_ffffff = 1;
            }
        }"""
    )

    assert dsl_code == expected_dsl
    _assert_dsl_code_loads_to_state_machine(dsl_code)
    assert "transition_effect_semantic_downgrade" in [item.code for item in report.outputs[0].diagnostics]


def test_phase6_normalize_machine_does_not_duplicate_transition_effect_diagnostics(tmp_path: Path):
    """Repeated public normalization should not duplicate effect-downgrade diagnostics."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Effect Once" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Effect Once">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_effect_once" source="state_idle" target="state_run">
                    <effect xmi:type="uml:Activity" xmi:id="effect_once" name="Drop Effect"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_run" name="Run"/>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = load_sysdesim_machine(str(xml_file))
    normalize_machine(machine)
    normalize_machine(machine)

    matching_codes = [item.code for item in machine.diagnostics if item.code == "transition_effect_semantic_downgrade"]
    assert matching_codes == ["transition_effect_semantic_downgrade"]
