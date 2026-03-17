"""Unit tests for the SysDeSim phase4 cross-level lowering pipeline."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import (
    build_machine_ast,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_dsl,
    load_sysdesim_machine,
    normalize_machine,
    validate_program_roundtrip,
)
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import StateMachine, parse_dsl_node_to_state_machine

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def _find_substate(state: dsl_nodes.StateDefinition, name: str) -> dsl_nodes.StateDefinition:
    """Return one direct child state by name."""
    for substate in state.substates:
        if substate.name == name:
            return substate
    raise AssertionError(f"Substate {name!r} not found.")


def _normalize_newlines(text: str) -> str:
    """Normalize text line endings to ``\\n`` for cross-platform assertions."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _assert_program_loads(program: dsl_nodes.StateMachineDSLProgram) -> StateMachine:
    """Assert that a generated AST program is accepted by the public model loader."""
    model = parse_dsl_node_to_state_machine(program)
    assert isinstance(model, StateMachine)
    return model


def _assert_dsl_code_loads_to_state_machine(dsl_code: str) -> StateMachine:
    """Assert that DSL text can be parsed and loaded into the public StateMachine model."""
    parsed_program = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    model = parse_dsl_node_to_state_machine(parsed_program)
    assert isinstance(model, StateMachine)
    return model


def test_phase4_direct_bridge_to_deeper_target_inserts_conditional_init_and_flag_cleanup(tmp_path: Path):
    """Direct-child cross-level transitions should bridge directly and rewrite the target init chain."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Direct Bridge" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Direct Bridge">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_source"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_cross_AAAAAA" source="state_source" target="state_target_leaf">
                    <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rule_cross">
                      <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_expr_cross">
                        <body> count &gt; 0 </body>
                      </specification>
                    </ownedRule>
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

    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    program = build_machine_ast(machine)
    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file))
    model = _assert_program_loads(program)
    dsl_model = _assert_dsl_code_loads_to_state_machine(dsl_code)
    parsed_program, _ = validate_program_roundtrip(program)
    dsl_code = _normalize_newlines(dsl_code)

    route_flag_name = "__sysdesim_flag_route_source__tx_aaaaaa"
    expected_dsl = dedent(
        """\
        def int count = 0;
        def int __sysdesim_flag_route_source__tx_aaaaaa = 0;
        state DirectBridge named 'Direct Bridge' {
            state Source;
            state TargetBranch {
                state DefaultLeaf;
                state TargetLeaf {
                    enter {
                        __sysdesim_flag_route_source__tx_aaaaaa = 0;
                    }
                }
                [*] -> TargetLeaf : if [__sysdesim_flag_route_source__tx_aaaaaa > 0];
                [*] -> DefaultLeaf;
            }
            [*] -> Source;
            Source -> TargetBranch : if [count > 0] effect {
                __sysdesim_flag_route_source__tx_aaaaaa = 1;
            }
        }"""
    )

    assert dsl_code == expected_dsl
    assert _normalize_newlines(str(program)) == expected_dsl
    assert _normalize_newlines(str(parsed_program)) == expected_dsl
    assert model.root_state.name == "DirectBridge"
    assert dsl_model.root_state.name == "DirectBridge"
    assert [definition.name for definition in program.definitions] == ["count", route_flag_name]
    assert parsed_program.root_state.name == "DirectBridge"

    target_branch = _find_substate(program.root_state, "TargetBranch")
    target_leaf = _find_substate(target_branch, "TargetLeaf")
    assert str(target_branch.transitions[0]) == f"[*] -> TargetLeaf : if [{route_flag_name} > 0];"
    assert str(target_branch.transitions[1]) == "[*] -> DefaultLeaf;"
    assert str(target_leaf.enters[0]) == f"enter {{\n    {route_flag_name} = 0;\n}}"


def test_phase4_nested_source_builds_exit_chain_and_root_bridge_with_signal_trigger(tmp_path: Path):
    """Nested-source cross-level transitions should exit upward before bridging across branches."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Signal Exit Chain" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Signal Exit Chain">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_left"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_cross_BBBBBB" source="state_source" target="state_ready">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="signal_evt_go"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_left" name="Left">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_mid"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_mid" name="Mid">
                        <region xmi:type="uml:Region" xmi:id="region_mid" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_mid_init" source="init_mid" target="state_source"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_mid"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                        </region>
                      </subvertex>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Go Signal"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_go" name="" signal="signal_go"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    program = build_machine_ast(machine)
    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file))
    model = _assert_program_loads(program)
    dsl_model = _assert_dsl_code_loads_to_state_machine(dsl_code)
    parsed_program, _ = validate_program_roundtrip(program)
    dsl_code = _normalize_newlines(dsl_code)

    route_flag_name = "__sysdesim_flag_route_left_mid_source__tx_bbbbbb"
    expected_dsl = dedent(
        """\
        def int __sysdesim_flag_route_left_mid_source__tx_bbbbbb = 0;
        state SignalExitChain named 'Signal Exit Chain' {
            state Left {
                state Mid {
                    state Source;
                    [*] -> Source;
                    Source -> [*] : /GO_SIGNAL effect {
                        __sysdesim_flag_route_left_mid_source__tx_bbbbbb = 1;
                    }
                }
                Mid -> [*] : if [__sysdesim_flag_route_left_mid_source__tx_bbbbbb > 0];
                [*] -> Mid;
            }
            state Ready {
                enter {
                    __sysdesim_flag_route_left_mid_source__tx_bbbbbb = 0;
                }
            }
            event GO_SIGNAL named 'Go Signal';
            Left -> Ready : if [__sysdesim_flag_route_left_mid_source__tx_bbbbbb > 0];
            [*] -> Left;
        }"""
    )

    assert dsl_code == expected_dsl
    assert _normalize_newlines(str(program)) == expected_dsl
    assert _normalize_newlines(str(parsed_program)) == expected_dsl
    assert model.root_state.name == "SignalExitChain"
    assert dsl_model.root_state.name == "SignalExitChain"
    assert [definition.name for definition in program.definitions] == [route_flag_name]
    assert str(program.root_state.events[0]) == "event GO_SIGNAL named 'Go Signal';"
    assert str(program.root_state.transitions[0]) == f"Left -> Ready : if [{route_flag_name} > 0];"
    assert str(program.root_state.transitions[1]) == "[*] -> Left;"

    left_state = _find_substate(program.root_state, "Left")
    mid_state = _find_substate(left_state, "Mid")
    ready_state = _find_substate(program.root_state, "Ready")
    assert str(left_state.transitions[0]) == f"Mid -> [*] : if [{route_flag_name} > 0];"
    assert str(left_state.transitions[1]) == "[*] -> Mid;"
    assert str(mid_state.transitions[0]) == "[*] -> Source;"
    assert str(mid_state.transitions[1]) == (
        "Source -> [*] : /GO_SIGNAL effect {\n"
        f"    {route_flag_name} = 1;\n"
        "}"
    )
    assert str(ready_state.enters[0]) == f"enter {{\n    {route_flag_name} = 0;\n}}"


def test_phase4_time_triggered_cross_level_transition_reuses_phase3_timeout_guard(tmp_path: Path):
    """Cross-level timeout transitions should combine timer lowering with route-flag routing."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timed Cross Level" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timed Cross Level">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_warmup"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_cross_CCCCCC" source="state_countdown" target="state_complete">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_2s"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_warmup" name="Warmup">
                    <region xmi:type="uml:Region" xmi:id="region_warmup" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_warmup_init" source="init_warmup" target="state_countdown"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_warmup"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_countdown" name="Countdown"/>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_complete" name="Complete"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_2s" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_2s" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_2s_value" name="Literal" value="2s"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    program = convert_sysdesim_xml_to_ast(str(xml_file), tick_duration_ms=1000.0)
    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file), tick_duration_ms=1000.0)
    model = _assert_program_loads(program)
    dsl_model = _assert_dsl_code_loads_to_state_machine(dsl_code)
    parsed_program, _ = validate_program_roundtrip(program)
    dsl_code = _normalize_newlines(dsl_code)

    route_flag_name = "__sysdesim_flag_route_warmup_countdown__tx_cccccc"
    timer_name = "__sysdesim_after_warmup_countdown__tx_cccccc_ticks"
    expected_dsl = dedent(
        """\
        def int __sysdesim_flag_route_warmup_countdown__tx_cccccc = 0;
        def int __sysdesim_after_warmup_countdown__tx_cccccc_ticks = 0;
        state TimedCrossLevel named 'Timed Cross Level' {
            state Warmup {
                state Countdown {
                    enter {
                        __sysdesim_after_warmup_countdown__tx_cccccc_ticks = 0;
                    }
                    during {
                        __sysdesim_after_warmup_countdown__tx_cccccc_ticks = __sysdesim_after_warmup_countdown__tx_cccccc_ticks + 1;
                    }
                }
                [*] -> Countdown;
                Countdown -> [*] : if [__sysdesim_after_warmup_countdown__tx_cccccc_ticks >= 2] effect {
                    __sysdesim_flag_route_warmup_countdown__tx_cccccc = 1;
                }
            }
            state Complete {
                enter {
                    __sysdesim_flag_route_warmup_countdown__tx_cccccc = 0;
                }
            }
            Warmup -> Complete : if [__sysdesim_flag_route_warmup_countdown__tx_cccccc > 0];
            [*] -> Warmup;
        }"""
    )

    assert dsl_code == expected_dsl
    assert _normalize_newlines(str(program)) == expected_dsl
    assert _normalize_newlines(str(parsed_program)) == expected_dsl
    assert model.root_state.name == "TimedCrossLevel"
    assert dsl_model.root_state.name == "TimedCrossLevel"
    assert [definition.name for definition in program.definitions] == [route_flag_name, timer_name]
    warmup_state = _find_substate(program.root_state, "Warmup")
    assert str(warmup_state.transitions[1]) == (
        "Countdown -> [*] : if "
        f"[{timer_name} >= 2] effect {{\n"
        f"    {route_flag_name} = 1;\n"
        "}"
    )
    assert f"Warmup -> Complete : if [{route_flag_name} > 0];" in dsl_code
    complete_state = _find_substate(program.root_state, "Complete")
    assert str(complete_state.enters[0]) == f"enter {{\n    {route_flag_name} = 0;\n}}"


def test_phase4_ancestor_target_cross_level_transition_is_still_rejected(tmp_path: Path):
    """Ancestor-target cross-level transitions remain outside the supported phase4 subset."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Ancestor Target" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Ancestor Target">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_parent"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_cross_DDDDDD" source="state_source" target="state_parent"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                    <region xmi:type="uml:Region" xmi:id="region_parent" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_parent_init" source="init_parent" target="state_mid"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_parent"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_mid" name="Mid">
                        <region xmi:type="uml:Region" xmi:id="region_mid" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_mid_init" source="init_mid" target="state_source"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_mid"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                        </region>
                      </subvertex>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    with pytest.raises(NotImplementedError, match="ancestor-target cross-level transitions"):
        convert_sysdesim_xml_to_dsl(str(xml_file))
