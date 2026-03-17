"""Unit tests for the SysDeSim phase3 time-event lowering pipeline."""

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
from pyfcstm.convert.sysdesim.ir import IrMachine, IrRegion, IrTimeEvent, IrTransition, IrVertex
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


def test_phase3_leaf_time_event_lowering_supports_seconds_and_tail_insertion(tmp_path: Path):
    """Leaf-state time transitions should lower into timer vars, guards, and tail-appended transitions."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Leaf Timer" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Leaf Timer">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_armed"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_manual" source="state_armed" target="state_manual">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_manual" event="signal_evt_manual"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_after_2s_AAAAAA" source="state_armed" target="state_slow">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_after_2s" event="time_evt_2s"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_after_half_BBBBBB" source="state_armed" target="state_quick">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_after_half" event="time_evt_half"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_after_fourhalf_CCCCCC" source="state_armed" target="state_hold">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_after_fourhalf" event="time_evt_fourhalf"/>
                    <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rule_hold">
                      <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_expr_hold">
                        <body> count &gt; 0 </body>
                      </specification>
                    </ownedRule>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_armed" name="Armed"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_manual" name="Manual"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_slow" name="Slow"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_quick" name="Quick"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_hold" name="Hold"/>
                </region>
              </ownedBehavior>
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_count" name="count">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_count_default" value="0"/>
              </ownedAttribute>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_manual" name="Manual Override"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_manual" name="" signal="signal_manual"/>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_2s" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_2s" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_2s_value" name="Literal" value="2s"/>
              </when>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_half" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_half" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_half_value" name="Literal" value="0.5s"/>
              </when>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_fourhalf" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_fourhalf" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_fourhalf_value" name="Literal" value="4.5s"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    program = build_machine_ast(machine, tick_duration_ms=100.0)
    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file), tick_duration_ms=100.0)
    model = _assert_program_loads(program)
    dsl_model = _assert_dsl_code_loads_to_state_machine(dsl_code)

    expected_dsl = dedent(
        """\
        def int count = 0;
        def int __sysdesim_after_armed__tx_aaaaaa_ticks = 0;
        def int __sysdesim_after_armed__tx_bbbbbb_ticks = 0;
        def int __sysdesim_after_armed__tx_cccccc_ticks = 0;
        state LeafTimer named 'Leaf Timer' {
            state Armed {
                enter {
                    __sysdesim_after_armed__tx_aaaaaa_ticks = 0;
                    __sysdesim_after_armed__tx_bbbbbb_ticks = 0;
                    __sysdesim_after_armed__tx_cccccc_ticks = 0;
                }
                during {
                    __sysdesim_after_armed__tx_aaaaaa_ticks = __sysdesim_after_armed__tx_aaaaaa_ticks + 1;
                    __sysdesim_after_armed__tx_bbbbbb_ticks = __sysdesim_after_armed__tx_bbbbbb_ticks + 1;
                    __sysdesim_after_armed__tx_cccccc_ticks = __sysdesim_after_armed__tx_cccccc_ticks + 1;
                }
            }
            state Manual;
            state Slow;
            state Quick;
            state Hold;
            event MANUAL_OVERRIDE named 'Manual Override';
            [*] -> Armed;
            Armed -> Manual : /MANUAL_OVERRIDE;
            Armed -> Slow : if [__sysdesim_after_armed__tx_aaaaaa_ticks >= 20];
            Armed -> Quick : if [__sysdesim_after_armed__tx_bbbbbb_ticks >= 5];
            Armed -> Hold : if [(__sysdesim_after_armed__tx_cccccc_ticks >= 45) && count > 0];
        }"""
    )

    assert isinstance(model, StateMachine)
    assert _normalize_newlines(dsl_code) == expected_dsl
    assert _normalize_newlines(str(program)) == expected_dsl
    assert model.root_state.name == "LeafTimer"
    assert dsl_model.root_state.name == "LeafTimer"
    assert [definition.name for definition in program.definitions] == [
        "count",
        "__sysdesim_after_armed__tx_aaaaaa_ticks",
        "__sysdesim_after_armed__tx_bbbbbb_ticks",
        "__sysdesim_after_armed__tx_cccccc_ticks",
    ]
    assert [str(definition.expr) for definition in program.definitions[1:]] == ["0", "0", "0"]

    armed = _find_substate(program.root_state, "Armed")
    assert len(armed.enters) == 1
    assert isinstance(armed.enters[0], dsl_nodes.EnterOperations)
    assert [str(operation) for operation in armed.enters[0].operations] == [
        "__sysdesim_after_armed__tx_aaaaaa_ticks = 0;",
        "__sysdesim_after_armed__tx_bbbbbb_ticks = 0;",
        "__sysdesim_after_armed__tx_cccccc_ticks = 0;",
    ]
    assert len(armed.durings) == 1
    assert isinstance(armed.durings[0], dsl_nodes.DuringOperations)
    assert [str(operation) for operation in armed.durings[0].operations] == [
        "__sysdesim_after_armed__tx_aaaaaa_ticks = __sysdesim_after_armed__tx_aaaaaa_ticks + 1;",
        "__sysdesim_after_armed__tx_bbbbbb_ticks = __sysdesim_after_armed__tx_bbbbbb_ticks + 1;",
        "__sysdesim_after_armed__tx_cccccc_ticks = __sysdesim_after_armed__tx_cccccc_ticks + 1;",
    ]

    root_transitions = program.root_state.transitions
    assert [transition.from_state for transition in root_transitions] == [
        dsl_nodes.INIT_STATE,
        "Armed",
        "Armed",
        "Armed",
        "Armed",
    ]
    assert [transition.to_state for transition in root_transitions] == [
        "Armed",
        "Manual",
        "Slow",
        "Quick",
        "Hold",
    ]
    assert str(root_transitions[1].event_id) == "/MANUAL_OVERRIDE"
    assert str(root_transitions[2].condition_expr) == "__sysdesim_after_armed__tx_aaaaaa_ticks >= 20"
    assert str(root_transitions[3].condition_expr) == "__sysdesim_after_armed__tx_bbbbbb_ticks >= 5"
    assert (
        str(root_transitions[4].condition_expr)
        == "(__sysdesim_after_armed__tx_cccccc_ticks >= 45) && count > 0"
    )

    assert "Armed -> Manual : /MANUAL_OVERRIDE;" in dsl_code
    assert dsl_code.index("Armed -> Manual : /MANUAL_OVERRIDE;") < dsl_code.index(
        "Armed -> Slow : if [__sysdesim_after_armed__tx_aaaaaa_ticks >= 20];"
    )


def test_phase3_leaf_time_event_lowering_supports_microseconds(tmp_path: Path):
    """Microsecond time literals should round up to at least one configured tick."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Micro Timer" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Micro Timer">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_wait"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_after_micro_DDDDDD" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_after_micro" event="time_evt_micro"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_micro" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_micro" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_micro_value" name="Literal" value="20us"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    program = build_machine_ast(machine, tick_duration_ms=1.0)
    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file), tick_duration_ms=1.0)

    expected_dsl = dedent(
        """\
        def int __sysdesim_after_wait__tx_dddddd_ticks = 0;
        state MicroTimer named 'Micro Timer' {
            state Wait {
                enter {
                    __sysdesim_after_wait__tx_dddddd_ticks = 0;
                }
                during {
                    __sysdesim_after_wait__tx_dddddd_ticks = __sysdesim_after_wait__tx_dddddd_ticks + 1;
                }
            }
            state Done;
            [*] -> Wait;
            Wait -> Done : if [__sysdesim_after_wait__tx_dddddd_ticks >= 1];
        }"""
    )

    assert _normalize_newlines(dsl_code) == expected_dsl
    assert _normalize_newlines(str(program)) == expected_dsl
    assert [definition.name for definition in program.definitions] == ["__sysdesim_after_wait__tx_dddddd_ticks"]
    assert str(program.root_state.transitions[1].condition_expr) == "__sysdesim_after_wait__tx_dddddd_ticks >= 1"
    _assert_program_loads(program)
    dsl_model = _assert_dsl_code_loads_to_state_machine(dsl_code)
    assert dsl_model.root_state.name == "MicroTimer"


def test_phase3_composite_time_event_lowering_builds_exit_chain_and_aspect_timer(tmp_path: Path):
    """Composite-state time transitions should lower into propagated exit chains and aspect-based ticking."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Composite Timer" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Composite Timer">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_warmup"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_cancel" source="state_warmup" target="state_abort">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_cancel" event="signal_evt_cancel"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_timeout_EEEEEE" source="state_warmup" target="state_complete">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_timeout"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_warmup" name="Warmup">
                    <region xmi:type="uml:Region" xmi:id="region_warmup" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_warmup_init" source="init_warmup" target="state_step"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_step_to_nested" source="state_step" target="state_nested"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_warmup"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_step" name="Step"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_nested" name="Nested">
                        <region xmi:type="uml:Region" xmi:id="region_nested" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_nested_init" source="init_nested" target="state_deep"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_nested"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_deep" name="Deep"/>
                        </region>
                      </subvertex>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_complete" name="Complete"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_abort" name="Abort"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_cancel" name="Cancel"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_cancel" name="" signal="signal_cancel"/>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_timeout" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_timeout" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_timeout_value" name="Literal" value="0.5s"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = normalize_machine(load_sysdesim_machine(str(xml_file)))
    program = build_machine_ast(machine, tick_duration_ms=100.0)
    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file), tick_duration_ms=100.0)

    expected_dsl = dedent(
        """\
        def int __sysdesim_after_warmup__tx_eeeeee_ticks = 0;
        state CompositeTimer named 'Composite Timer' {
            state Warmup {
                enter {
                    __sysdesim_after_warmup__tx_eeeeee_ticks = 0;
                }
                >> during after {
                    __sysdesim_after_warmup__tx_eeeeee_ticks = __sysdesim_after_warmup__tx_eeeeee_ticks + 1;
                }
                state Step;
                state Nested {
                    state Deep;
                    [*] -> Deep;
                    Deep -> [*] : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];
                }
                [*] -> Step;
                Step -> Nested;
                Step -> [*] : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];
                Nested -> [*] : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];
            }
            state Complete;
            state Abort;
            event CANCEL named 'Cancel';
            [*] -> Warmup;
            Warmup -> Abort : /CANCEL;
            Warmup -> Complete : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];
        }"""
    )

    assert _normalize_newlines(dsl_code) == expected_dsl
    assert _normalize_newlines(str(program)) == expected_dsl
    assert [definition.name for definition in program.definitions] == ["__sysdesim_after_warmup__tx_eeeeee_ticks"]

    warmup = _find_substate(program.root_state, "Warmup")
    nested = _find_substate(warmup, "Nested")

    assert len(warmup.enters) == 1
    assert isinstance(warmup.enters[0], dsl_nodes.EnterOperations)
    assert [str(operation) for operation in warmup.enters[0].operations] == [
        "__sysdesim_after_warmup__tx_eeeeee_ticks = 0;"
    ]
    assert warmup.durings == []
    assert len(warmup.during_aspects) == 1
    assert isinstance(warmup.during_aspects[0], dsl_nodes.DuringAspectOperations)
    assert warmup.during_aspects[0].aspect == "after"
    assert [str(operation) for operation in warmup.during_aspects[0].operations] == [
        "__sysdesim_after_warmup__tx_eeeeee_ticks = __sysdesim_after_warmup__tx_eeeeee_ticks + 1;"
    ]

    assert [str(transition) for transition in warmup.transitions] == [
        "[*] -> Step;",
        "Step -> Nested;",
        "Step -> [*] : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];",
        "Nested -> [*] : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];",
    ]
    assert [str(transition) for transition in nested.transitions] == [
        "[*] -> Deep;",
        "Deep -> [*] : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];",
    ]
    assert [str(transition) for transition in program.root_state.transitions] == [
        "[*] -> Warmup;",
        "Warmup -> Abort : /CANCEL;",
        "Warmup -> Complete : if [__sysdesim_after_warmup__tx_eeeeee_ticks >= 5];",
    ]
    _assert_program_loads(program)
    dsl_model = _assert_dsl_code_loads_to_state_machine(dsl_code)
    assert dsl_model.root_state.name == "CompositeTimer"


def test_phase3_time_lowering_uses_safe_name_tokens_for_unnamed_source_state(tmp_path: Path):
    """Unnamed source states should derive timer scope tokens from the normalized public state name."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Unnamed Timer" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Unnamed Timer">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_empty"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_timeout_GGGGGG" source="state_empty" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_timeout"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_empty" name=""/>
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

    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file), tick_duration_ms=1000.0)
    expected_dsl = dedent(
        """\
        def int __sysdesim_after_sysdesim_state_eempty__tx_gggggg_ticks = 0;
        state UnnamedTimer named 'Unnamed Timer' {
            state __sysdesim_state_eempty {
                enter {
                    __sysdesim_after_sysdesim_state_eempty__tx_gggggg_ticks = 0;
                }
                during {
                    __sysdesim_after_sysdesim_state_eempty__tx_gggggg_ticks = __sysdesim_after_sysdesim_state_eempty__tx_gggggg_ticks + 1;
                }
            }
            state Done;
            [*] -> __sysdesim_state_eempty;
            __sysdesim_state_eempty -> Done : if [__sysdesim_after_sysdesim_state_eempty__tx_gggggg_ticks >= 1];
        }"""
    )

    assert _normalize_newlines(dsl_code) == expected_dsl
    dsl_model = _assert_dsl_code_loads_to_state_machine(dsl_code)
    assert dsl_model.root_state.name == "UnnamedTimer"


def test_phase3_time_lowering_uses_stable_suffix_when_public_ir_state_path_has_no_tokens():
    """Public IR inputs with tokenless source paths should fall back to a stable suffix-based timer scope."""
    machine = IrMachine(
        machine_id="machine_public_suffix",
        name="Manual Fallback",
        root_region=IrRegion(
            region_id="region_root",
            owner_state_id=None,
            vertices=[
                IrVertex(vertex_id="init_root", vertex_type="pseudostate", raw_name="", parent_region_id="region_root"),
                IrVertex(
                    vertex_id="!!!",
                    vertex_type="state",
                    raw_name="",
                    safe_name="__",
                    display_name="",
                    parent_region_id="region_root",
                ),
                IrVertex(
                    vertex_id="state_done",
                    vertex_type="state",
                    raw_name="Done",
                    safe_name="Done",
                    display_name="Done",
                    parent_region_id="region_root",
                ),
            ],
            transitions=[
                IrTransition(
                    transition_id="tx_init",
                    source_id="init_root",
                    target_id="!!!",
                    trigger_kind="none",
                    trigger_ref_id=None,
                    guard_expr_raw=None,
                ),
                IrTransition(
                    transition_id="tx_timeout_HHHHHH",
                    source_id="!!!",
                    target_id="state_done",
                    trigger_kind="time",
                    trigger_ref_id="time_evt_timeout",
                    guard_expr_raw=None,
                ),
            ],
        ),
        time_events=[
            IrTimeEvent(
                time_event_id="time_evt_timeout",
                raw_literal="1ms",
                is_relative=True,
                normalized_delay=1.0,
                normalized_unit="ms",
            )
        ],
        safe_name="ManualFallback",
        display_name="Manual Fallback",
    )

    program = build_machine_ast(machine, tick_duration_ms=1.0)
    parsed_program, model = validate_program_roundtrip(program)

    assert [definition.name for definition in program.definitions] == ["__sysdesim_after_sdesim__tx_hhhhhh_ticks"]
    assert str(program.root_state.transitions[1]) == "__ -> Done : if [__sysdesim_after_sdesim__tx_hhhhhh_ticks >= 1];"
    assert str(parsed_program.root_state.transitions[1]) == "__ -> Done : if [__sysdesim_after_sdesim__tx_hhhhhh_ticks >= 1];"
    assert isinstance(model, StateMachine)
    assert model.root_state.name == "ManualFallback"


def test_phase3_public_ir_composite_timeout_without_regions_skips_exit_chain_registration():
    """Public IR inputs may mark a state composite before child regions exist; that path should still build safely."""
    machine = IrMachine(
        machine_id="machine_public_composite",
        name="Public Composite",
        root_region=IrRegion(
            region_id="region_root",
            owner_state_id=None,
            vertices=[
                IrVertex(vertex_id="init_root", vertex_type="pseudostate", raw_name="", parent_region_id="region_root"),
                IrVertex(
                    vertex_id="state_source",
                    vertex_type="state",
                    raw_name="Source",
                    safe_name="Source",
                    display_name="Source",
                    parent_region_id="region_root",
                    is_composite=True,
                    regions=[],
                ),
                IrVertex(
                    vertex_id="state_done",
                    vertex_type="state",
                    raw_name="Done",
                    safe_name="Done",
                    display_name="Done",
                    parent_region_id="region_root",
                ),
            ],
            transitions=[
                IrTransition(
                    transition_id="tx_init",
                    source_id="init_root",
                    target_id="state_source",
                    trigger_kind="none",
                    trigger_ref_id=None,
                    guard_expr_raw=None,
                ),
                IrTransition(
                    transition_id="tx_timeout_IIIIII",
                    source_id="state_source",
                    target_id="state_done",
                    trigger_kind="time",
                    trigger_ref_id="time_evt_timeout",
                    guard_expr_raw=None,
                ),
            ],
        ),
        time_events=[
            IrTimeEvent(
                time_event_id="time_evt_timeout",
                raw_literal="1ms",
                is_relative=True,
                normalized_delay=1.0,
                normalized_unit="ms",
            )
        ],
        safe_name="PublicComposite",
        display_name="Public Composite",
    )

    program = build_machine_ast(machine, tick_duration_ms=1.0)
    parsed_program, model = validate_program_roundtrip(program)
    source_state = next(state for state in program.root_state.substates if state.name == "Source")

    assert source_state.transitions == []
    assert len(source_state.during_aspects) == 1
    assert str(source_state.during_aspects[0]) == dedent(
        """\
        >> during after {
            __sysdesim_after_source__tx_iiiiii_ticks = __sysdesim_after_source__tx_iiiiii_ticks + 1;
        }"""
    )
    assert str(program.root_state.transitions[1]) == "Source -> Done : if [__sysdesim_after_source__tx_iiiiii_ticks >= 1];"
    assert isinstance(model, StateMachine)
    assert parsed_program.root_state.name == "PublicComposite"


@pytest.mark.parametrize(
    ("literal", "is_relative", "tick_duration_ms", "expected_exception", "expected_message"),
    [
        ("0.5s", True, None, ValueError, "tick_duration_ms is required"),
        ("0.5s", True, 0.0, ValueError, "tick_duration_ms must be greater than 0"),
        ("0.5s", False, 100.0, NotImplementedError, "only supports relative uml:TimeEvent"),
        ("3min", True, 100.0, ValueError, "Unsupported uml:TimeEvent literal"),
    ],
)
def test_phase3_rejects_invalid_time_event_configuration(
    tmp_path: Path,
    literal: str,
    is_relative: bool,
    tick_duration_ms: float,
    expected_exception,
    expected_message: str,
):
    """Unsupported time-event literals or missing config should fail clearly."""
    xml_file = _write_xml(
        tmp_path,
        f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Invalid Timer" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Invalid Timer">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_wait"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_timeout_FFFFFF" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_timeout"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_timeout" name="" isRelative="{str(is_relative).lower()}">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_timeout" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_timeout_value" name="Literal" value="{literal}"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    with pytest.raises(expected_exception, match=expected_message):
        convert_sysdesim_xml_to_ast(str(xml_file), tick_duration_ms=tick_duration_ms)


@pytest.mark.parametrize(
    ("transition_body", "expected_message"),
    [
        (
            """
            <transition xmi:type="uml:Transition" xmi:id="tx_timeout_JJJJJJ" source="init_root" target="state_done">
              <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_timeout"/>
            </transition>
            """,
            "state-backed uml:TimeEvent sources",
        ),
        (
            """
            <transition xmi:type="uml:Transition" xmi:id="tx_timeout_KKKKKK" source="state_wait" target="state_done">
              <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_timeout"/>
              <effect xmi:type="uml:Activity" xmi:id="effect_timeout" name="DoSideEffect"/>
            </transition>
            """,
            "does not lower transition effects yet",
        ),
    ],
)
def test_phase3_rejects_public_time_event_shapes_not_supported_yet(
    tmp_path: Path,
    transition_body: str,
    expected_message: str,
):
    """Public XML inputs should reject unsupported time-event source and effect shapes."""
    xml_file = _write_xml(
        tmp_path,
        f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Unsupported Timer Shape" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Unsupported Timer Shape">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_wait"/>
                  {transition_body}
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

    with pytest.raises(NotImplementedError, match=expected_message):
        convert_sysdesim_xml_to_ast(str(xml_file), tick_duration_ms=1000.0)
