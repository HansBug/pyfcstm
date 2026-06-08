"""Unit tests for the SysDeSim phase4 cross-level lowering pipeline."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import (
    build_machine_ast,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_asts,
    convert_sysdesim_xml_to_dsl,
    convert_sysdesim_xml_to_dsls,
    convert as sysdesim_convert,
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


def _find_substate(
    state: dsl_nodes.StateDefinition, name: str
) -> dsl_nodes.StateDefinition:
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


def _find_transition(
    state: dsl_nodes.StateDefinition,
    from_state,
    to_state,
) -> dsl_nodes.TransitionDefinition:
    """Return one direct transition by endpoint identity/value."""
    matches = [
        transition
        for transition in state.transitions
        if transition.from_state == from_state and transition.to_state is to_state
    ]
    if to_state is not dsl_nodes.EXIT_STATE and to_state is not dsl_nodes.INIT_STATE:
        matches = [
            transition
            for transition in state.transitions
            if transition.from_state == from_state and transition.to_state == to_state
        ]
    assert len(matches) == 1
    return matches[0]


def _assert_single_integer_assignment(
    transition: dsl_nodes.TransitionDefinition,
    name: str,
    raw: str,
) -> None:
    """Assert that a transition effect contains one integer assignment."""
    assert len(transition.post_operations) == 1
    operation = transition.post_operations[0]
    assert isinstance(operation, dsl_nodes.OperationAssignment)
    assert operation.name == name
    assert isinstance(operation.expr, dsl_nodes.Integer)
    assert operation.expr.raw == raw


def _minimal_cross_level_final_xml(
    *,
    machine_name: str = "Final Root Exit",
    transition_id: str = "tx_finish",
    transition_body: str = "",
    extra_package_elements: str = "",
    extra_owned_attribute: str = "",
) -> str:
    """Build a compact leaf-to-root-FinalState XML fixture."""
    return f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="{machine_name}" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="{machine_name}">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_parent"/>
                  <transition xmi:type="uml:Transition" xmi:id="{transition_id}" source="state_leaf" target="final_root">
                    {transition_body}
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                    <region xmi:type="uml:Region" xmi:id="region_parent" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_parent_init" source="init_parent" target="state_leaf"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_parent"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_leaf" name="Leaf"/>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:FinalState" xmi:id="final_root" name=""/>
                </region>
              </ownedBehavior>
              {extra_owned_attribute}
            </packagedElement>
            {extra_package_elements}
          </uml:Model>
        </xmi:XMI>
    """


def test_phase4_direct_bridge_to_deeper_target_inserts_conditional_init_and_flag_cleanup(
    tmp_path: Path,
):
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
    assert [definition.name for definition in program.definitions] == [
        "count",
        route_flag_name,
    ]
    assert parsed_program.root_state.name == "DirectBridge"

    target_branch = _find_substate(program.root_state, "TargetBranch")
    target_leaf = _find_substate(target_branch, "TargetLeaf")
    assert (
        str(target_branch.transitions[0])
        == f"[*] -> TargetLeaf : if [{route_flag_name} > 0];"
    )
    assert str(target_branch.transitions[1]) == "[*] -> DefaultLeaf;"
    assert str(target_leaf.enters[0]) == f"enter {{\n    {route_flag_name} = 0;\n}}"


def test_phase4_nested_source_builds_exit_chain_and_root_bridge_with_signal_trigger(
    tmp_path: Path,
):
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
    assert route_flag_name in [definition.name for definition in program.definitions]
    assert str(program.root_state.events[0]) == "event GO_SIGNAL named 'Go Signal';"
    assert (
        str(program.root_state.transitions[0])
        == f"Left -> Ready : if [{route_flag_name} > 0];"
    )
    assert str(program.root_state.transitions[1]) == "[*] -> Left;"

    left_state = _find_substate(program.root_state, "Left")
    mid_state = _find_substate(left_state, "Mid")
    ready_state = _find_substate(program.root_state, "Ready")
    assert str(left_state.transitions[0]) == f"Mid -> [*] : if [{route_flag_name} > 0];"
    assert str(left_state.transitions[1]) == "[*] -> Mid;"
    assert str(mid_state.transitions[0]) == "[*] -> Source;"
    assert str(mid_state.transitions[1]) == (
        f"Source -> [*] : /GO_SIGNAL effect {{\n    {route_flag_name} = 1;\n}}"
    )
    assert str(ready_state.enters[0]) == f"enter {{\n    {route_flag_name} = 0;\n}}"


def test_phase4_time_triggered_cross_level_transition_reuses_phase3_timeout_guard(
    tmp_path: Path,
):
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
    assert [definition.name for definition in program.definitions] == [
        route_flag_name,
        timer_name,
    ]
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


def test_phase4_real_model0608_lowers_cross_level_final_target_to_exit_chain():
    """The real model0608.xml sample should lower its cross-level FinalState target."""
    xml_file = (
        Path(__file__).resolve().parents[2]
        / "testfile/sysdesim/final_state_cross_level_model0608.xml"
    )

    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    transition = machine.get_transition("_y7sJsGMdEfG32u33dqGYFg")
    route_flag_name = sysdesim_convert._make_route_flag_name(machine, transition)
    programs = convert_sysdesim_xml_to_asts(str(xml_file))
    dsl_outputs = {
        name: _normalize_newlines(code)
        for name, code in convert_sysdesim_xml_to_dsls(str(xml_file)).items()
    }

    assert route_flag_name == "__sysdesim_flag_route_control_e__tx_dqgyfg"
    assert "StateMachine__Control_region1" in programs
    for program in programs.values():
        validate_program_roundtrip(program)
    for dsl_code in dsl_outputs.values():
        assert "state __sysdesim_final_" not in dsl_code
        assert "_yirz0GMdEfG32u33dqGYFg" not in dsl_code

    program = programs["StateMachine__Control_region1"]
    dsl_code = dsl_outputs["StateMachine__Control_region1"]
    control_state = _find_substate(program.root_state, "Control")
    first_hop = _find_transition(control_state, "EState", dsl_nodes.EXIT_STATE)
    final_hop = _find_transition(program.root_state, "Control", dsl_nodes.EXIT_STATE)

    assert route_flag_name.startswith("__sysdesim_flag_route_")
    assert route_flag_name in [definition.name for definition in program.definitions]
    assert first_hop.to_state is dsl_nodes.EXIT_STATE
    assert first_hop.event_id is None
    assert first_hop.condition_expr is None
    _assert_single_integer_assignment(first_hop, route_flag_name, "1")
    assert final_hop.to_state is dsl_nodes.EXIT_STATE
    assert str(final_hop.condition_expr) == f"{route_flag_name} > 0"
    _assert_single_integer_assignment(final_hop, route_flag_name, "0")
    assert (
        f"EState -> [*] effect {{\n            {route_flag_name} = 1;\n        }}"
        in dsl_code
    )
    assert f"Control -> [*] : if [{route_flag_name} > 0] effect {{" in dsl_code


def test_phase4_keeps_model2_same_level_final_target_baseline():
    """FS-2 should not regress the FS-1 real same-level FinalState baseline."""
    xml_file = (
        Path(__file__).resolve().parents[2]
        / "testfile/sysdesim/final_state_same_level_model2.xml"
    )

    program = convert_sysdesim_xml_to_ast(str(xml_file))
    dsl_code = _normalize_newlines(convert_sysdesim_xml_to_dsl(str(xml_file)))
    validate_program_roundtrip(program)
    exit_transitions = [
        transition
        for transition in program.root_state.transitions
        if transition.from_state == "SS" and transition.to_state is dsl_nodes.EXIT_STATE
    ]

    assert len(exit_transitions) == 1
    assert "SS -> [*];" in dsl_code
    assert "__sysdesim_flag_route_" not in dsl_code
    assert "state __sysdesim_final_" not in dsl_code


def test_phase4_lowers_minimal_cross_level_final_target_to_root_exit_chain(
    tmp_path: Path,
):
    """A nested leaf targeting a root FinalState should become a route-flag exit chain."""
    xml_file = _write_xml(tmp_path, _minimal_cross_level_final_xml())
    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    transition = machine.get_transition("tx_finish")
    route_flag_name = sysdesim_convert._make_route_flag_name(machine, transition)

    program = build_machine_ast(machine)
    parsed_program, _ = validate_program_roundtrip(program)
    dsl_code = _normalize_newlines(convert_sysdesim_xml_to_dsl(str(xml_file)))

    expected_dsl = dedent(
        f"""\
        def int {route_flag_name} = 0;
        state FinalRootExit named 'Final Root Exit' {{
            state Parent {{
                state Leaf;
                [*] -> Leaf;
                Leaf -> [*] effect {{
                    {route_flag_name} = 1;
                }}
            }}
            Parent -> [*] : if [{route_flag_name} > 0] effect {{
                {route_flag_name} = 0;
            }}
            [*] -> Parent;
        }}"""
    )
    parent_state = _find_substate(program.root_state, "Parent")
    first_hop = _find_transition(parent_state, "Leaf", dsl_nodes.EXIT_STATE)
    final_hop = _find_transition(program.root_state, "Parent", dsl_nodes.EXIT_STATE)

    assert dsl_code == expected_dsl
    assert _normalize_newlines(str(program)) == expected_dsl
    assert _normalize_newlines(str(parsed_program)) == expected_dsl
    assert route_flag_name == "__sysdesim_flag_route_parent_leaf__tx_finish"
    assert route_flag_name in [definition.name for definition in program.definitions]
    assert first_hop.to_state is dsl_nodes.EXIT_STATE
    _assert_single_integer_assignment(first_hop, route_flag_name, "1")
    assert str(final_hop.condition_expr) == f"{route_flag_name} > 0"
    _assert_single_integer_assignment(final_hop, route_flag_name, "0")
    assert "state __sysdesim_final_" not in dsl_code


def test_phase4_lowers_deep_cross_level_final_target_to_multi_hop_exit_chain(
    tmp_path: Path,
):
    """Deeply nested sources should exit each ancestor until the FinalState owner region."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Deep Final Root Exit" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Deep Final Root Exit">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init_root" source="init_root" target="state_parent"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_deep_finish" source="state_leaf" target="final_root"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                    <region xmi:type="uml:Region" xmi:id="region_parent" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init_parent" source="init_parent" target="state_mid"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_parent"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_mid" name="Mid">
                        <region xmi:type="uml:Region" xmi:id="region_mid" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_init_mid" source="init_mid" target="state_leaf"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_mid"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_leaf" name="Leaf"/>
                        </region>
                      </subvertex>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:FinalState" xmi:id="final_root" name=""/>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )
    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    route_flag_name = sysdesim_convert._make_route_flag_name(
        machine, machine.get_transition("tx_deep_finish")
    )

    program = build_machine_ast(machine)
    validate_program_roundtrip(program)
    parent_state = _find_substate(program.root_state, "Parent")
    mid_state = _find_substate(parent_state, "Mid")
    first_hop = _find_transition(mid_state, "Leaf", dsl_nodes.EXIT_STATE)
    middle_hop = _find_transition(parent_state, "Mid", dsl_nodes.EXIT_STATE)
    final_hop = _find_transition(program.root_state, "Parent", dsl_nodes.EXIT_STATE)

    _assert_single_integer_assignment(first_hop, route_flag_name, "1")
    assert str(middle_hop.condition_expr) == f"{route_flag_name} > 0"
    assert middle_hop.post_operations == []
    assert str(final_hop.condition_expr) == f"{route_flag_name} > 0"
    _assert_single_integer_assignment(final_hop, route_flag_name, "0")


def test_phase4_lowers_guarded_cross_level_final_target_to_exit_chain(
    tmp_path: Path,
):
    """A guard-only cross-level FinalState transition should keep the guard on the first hop."""
    xml_file = _write_xml(
        tmp_path,
        _minimal_cross_level_final_xml(
            machine_name="Guarded Final Root Exit",
            transition_id="tx_guarded_finish",
            transition_body="""
              <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rule">
                <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_expr">
                  <body> count &gt; 0 </body>
                </specification>
              </ownedRule>
            """,
            extra_owned_attribute="""
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_count" name="count">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_count_default" value="0"/>
              </ownedAttribute>
            """,
        ),
    )
    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    route_flag_name = sysdesim_convert._make_route_flag_name(
        machine, machine.get_transition("tx_guarded_finish")
    )

    program = build_machine_ast(machine)
    validate_program_roundtrip(program)
    dsl_code = _normalize_newlines(convert_sysdesim_xml_to_dsl(str(xml_file)))
    parent_state = _find_substate(program.root_state, "Parent")
    first_hop = _find_transition(parent_state, "Leaf", dsl_nodes.EXIT_STATE)
    final_hop = _find_transition(program.root_state, "Parent", dsl_nodes.EXIT_STATE)

    assert "Leaf -> [*] : if [count > 0] effect {" in dsl_code
    assert str(first_hop.condition_expr) == "count > 0"
    _assert_single_integer_assignment(first_hop, route_flag_name, "1")
    assert str(final_hop.condition_expr) == f"{route_flag_name} > 0"
    _assert_single_integer_assignment(final_hop, route_flag_name, "0")


def test_phase4_lowers_signal_cross_level_final_target_to_exit_chain(tmp_path: Path):
    """A signal-only cross-level FinalState transition should keep its signal on the first hop."""
    xml_file = _write_xml(
        tmp_path,
        _minimal_cross_level_final_xml(
            machine_name="Signal Final Root Exit",
            transition_id="tx_signal_finish",
            transition_body='<trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="signal_event_go"/>',
            extra_package_elements="""
              <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Go"/>
              <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_event_go" name="" signal="signal_go"/>
            """,
        ),
    )
    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    route_flag_name = sysdesim_convert._make_route_flag_name(
        machine, machine.get_transition("tx_signal_finish")
    )

    program = build_machine_ast(machine)
    validate_program_roundtrip(program)
    dsl_code = _normalize_newlines(convert_sysdesim_xml_to_dsl(str(xml_file)))
    parent_state = _find_substate(program.root_state, "Parent")
    first_hop = _find_transition(parent_state, "Leaf", dsl_nodes.EXIT_STATE)
    final_hop = _find_transition(program.root_state, "Parent", dsl_nodes.EXIT_STATE)

    assert str(first_hop.event_id) == "/GO"
    assert first_hop.condition_expr is None
    _assert_single_integer_assignment(first_hop, route_flag_name, "1")
    assert final_hop.event_id is None
    assert str(final_hop.condition_expr) == f"{route_flag_name} > 0"
    assert "Leaf -> [*] : /GO effect {" in dsl_code


def test_phase4_lowers_time_triggered_cross_level_final_target_to_exit_chain(
    tmp_path: Path,
):
    """A time-triggered cross-level FinalState transition should reuse the timeout guard."""
    xml_file = _write_xml(
        tmp_path,
        _minimal_cross_level_final_xml(
            machine_name="Timed Final Root Exit",
            transition_id="tx_timed_finish",
            transition_body='<trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_2s"/>',
            extra_package_elements="""
              <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_2s" name="" isRelative="true">
                <when xmi:type="uml:TimeExpression" xmi:id="time_expr_2s" name="timeExpression">
                  <expr xmi:type="uml:LiteralString" xmi:id="time_expr_2s_value" name="Literal" value="2s"/>
                </when>
              </packagedElement>
            """,
        ),
    )
    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    route_flag_name = sysdesim_convert._make_route_flag_name(
        machine, machine.get_transition("tx_timed_finish")
    )
    timer_name = "__sysdesim_after_parent_leaf__tx_finish_ticks"

    program = build_machine_ast(machine, tick_duration_ms=1000.0)
    validate_program_roundtrip(program)
    dsl_code = _normalize_newlines(
        convert_sysdesim_xml_to_dsl(str(xml_file), tick_duration_ms=1000.0)
    )
    parent_state = _find_substate(program.root_state, "Parent")
    leaf_state = _find_substate(parent_state, "Leaf")
    first_hop = _find_transition(parent_state, "Leaf", dsl_nodes.EXIT_STATE)
    final_hop = _find_transition(program.root_state, "Parent", dsl_nodes.EXIT_STATE)

    assert [definition.name for definition in program.definitions] == [
        route_flag_name,
        timer_name,
    ]
    assert str(leaf_state.enters[0]) == f"enter {{\n    {timer_name} = 0;\n}}"
    assert str(first_hop.condition_expr) == f"{timer_name} >= 2"
    _assert_single_integer_assignment(first_hop, route_flag_name, "1")
    assert final_hop.event_id is None
    assert str(final_hop.condition_expr) == f"{route_flag_name} > 0"
    assert "Leaf -> [*] : if " in dsl_code
    assert "state __sysdesim_final_" not in dsl_code


def test_phase4_rejects_signal_guard_cross_level_final_target_without_expanding_scope(
    tmp_path: Path,
):
    """Signal+guard cross-level FinalState transitions should remain unsupported."""
    xml_file = _write_xml(
        tmp_path,
        _minimal_cross_level_final_xml(
            machine_name="Signal Guard Final Root Exit",
            transition_id="tx_signal_guard_finish",
            transition_body="""
              <trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="signal_event_go"/>
              <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rule">
                <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_expr">
                  <body> count &gt; 0 </body>
                </specification>
              </ownedRule>
            """,
            extra_owned_attribute="""
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_count" name="count">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_count_default" value="0"/>
              </ownedAttribute>
            """,
            extra_package_elements="""
              <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Go"/>
              <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_event_go" name="" signal="signal_go"/>
            """,
        ),
    )

    with pytest.raises(NotImplementedError, match="both signal and guard"):
        convert_sysdesim_xml_to_ast(str(xml_file))


def test_phase4_rejects_unrelated_region_cross_level_final_target(tmp_path: Path):
    """A source outside the final owner subtree should fail loudly."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Unrelated Final" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Unrelated Final">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init_root" source="init_root" target="state_left"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_left" name="Left">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init_left" source="init_left" target="state_source"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_unrelated_finish" source="state_source" target="final_right"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_right" name="Right">
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init_right" source="init_right" target="state_dummy"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_dummy" name="Dummy"/>
                      <subvertex xmi:type="uml:FinalState" xmi:id="final_right" name=""/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    with pytest.raises(
        NotImplementedError,
        match="cross-level FinalState target outside source subtree",
    ):
        convert_sysdesim_xml_to_ast(str(xml_file))


def test_phase4_rejects_composite_source_cross_level_final_target(tmp_path: Path):
    """Composite-source FinalState transitions should not be expanded in FS-2."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Composite Final" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Composite Final">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init_root" source="init_root" target="state_parent"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_composite_finish" source="state_parent" target="final_root"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                    <region xmi:type="uml:Region" xmi:id="region_parent" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init_parent" source="init_parent" target="state_leaf"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_parent"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_leaf" name="Leaf"/>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:FinalState" xmi:id="final_root" name=""/>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    with pytest.raises(
        NotImplementedError, match=r"composite source.*FinalState target"
    ):
        convert_sysdesim_xml_to_ast(str(xml_file))


def test_phase4_ancestor_target_cross_level_transition_is_still_rejected(
    tmp_path: Path,
):
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

    with pytest.raises(
        NotImplementedError, match="ancestor-target cross-level transitions"
    ):
        convert_sysdesim_xml_to_dsl(str(xml_file))


@pytest.mark.parametrize(
    ("xml_content", "expected_message"),
    [
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Cross Final Source" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Cross Final Source">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_parent"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_cross_final_source" source="final_source" target="state_ready"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                        <region xmi:type="uml:Region" xmi:id="region_parent" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_parent_init" source="init_parent" target="state_source"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_parent"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                          <subvertex xmi:type="uml:FinalState" xmi:id="final_source" name=""/>
                        </region>
                      </subvertex>
                      <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "cross-level transitions from FinalState source",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Cross Signal Guard" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Cross Signal Guard">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_left"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_cross_GGGGGG" source="state_source" target="state_ready">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="signal_evt_go"/>
                        <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rule_cross">
                          <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_expr_cross">
                            <body> counter &gt; 0 </body>
                          </specification>
                        </ownedRule>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left" name="Left">
                        <region xmi:type="uml:Region" xmi:id="region_left" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_source"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                        </region>
                      </subvertex>
                      <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                    </region>
                  </ownedBehavior>
                  <ownedAttribute xmi:type="uml:Property" xmi:id="var_counter" name="counter">
                    <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                    <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_counter_default" value="0"/>
                  </ownedAttribute>
                </packagedElement>
                <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Go Signal"/>
                <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_go" name="" signal="signal_go"/>
              </uml:Model>
            </xmi:XMI>
            """,
            "does not support cross-level transitions with both signal and guard",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Cross Unknown Trigger" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Cross Unknown Trigger">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_left"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_cross_HHHHHH" source="state_source" target="state_ready">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_unknown" event="missing_event"/>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left" name="Left">
                        <region xmi:type="uml:Region" xmi:id="region_left" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_source"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                        </region>
                      </subvertex>
                      <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "only supports signal/none/time cross-level transitions",
        ),
    ],
)
def test_phase4_public_unsupported_cross_level_shapes_report_clear_errors(
    tmp_path: Path, xml_content: str, expected_message: str
):
    """Phase4 should reject still-unsupported public cross-level shapes with stable messages."""
    xml_file = _write_xml(tmp_path, xml_content)

    with pytest.raises(NotImplementedError, match=expected_message):
        convert_sysdesim_xml_to_ast(str(xml_file))
