"""Unit tests for the SysDeSim phase0-2 conversion pipeline."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import (
    build_machine_ast,
    convert_sysdesim_xml_to_dsl,
    load_sysdesim_machine,
    normalize_machine,
    validate_program_roundtrip,
)
from pyfcstm.convert.sysdesim.convert import make_internal_name
from pyfcstm.convert.sysdesim.ir import IrMachine, IrRegion, IrVariable

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def test_phase0_can_parse_graph_structure_and_events(tmp_path: Path):
    """Phase0 should parse regions, vertices, transitions, signals, and time events."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="ThermalStation" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="ThermalStation">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_heat" source="state_idle" target="state_heat">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_heat" event="signal_evt_heat"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_alarm" source="state_heat" target="state_alarm">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_alarm" event="time_evt_alarm"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Buffer Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_heat" name="Loop Heat">
                    <region xmi:type="uml:Region" xmi:id="region_heat_a" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_heat_init_a" source="init_heat_a" target="state_cycle"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_heat_a"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_cycle" name="Cycle"/>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_heat_b" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_heat_init_b" source="init_heat_b" target="state_guard"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_heat_b"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_guard" name="Guard"/>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_alarm" name="Alarm Hold">
                    <entry xmi:type="uml:Activity" xmi:id="entry_alarm" name="NotifyOperator"/>
                    <exit xmi:type="uml:Activity" xmi:id="exit_alarm" name="ResetIndicator"/>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_heat" name="Heat Request"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_heat" name="" signal="signal_heat"/>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_alarm" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_alarm" name="timeExpression">
                <expr xmi:type="uml:LiteralString" xmi:id="time_expr_alarm_value" name="Literal" value="0.5s"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = load_sysdesim_machine(str(xml_file))

    assert machine.name == "ThermalStation"
    assert machine.root_region.region_id == "region_root"
    assert len(machine.signals) == 1
    assert len(machine.signal_events) == 1
    assert len(machine.time_events) == 1
    assert machine.time_events[0].raw_literal == "0.5s"
    assert machine.get_vertex("state_heat").is_parallel_owner is True
    assert machine.get_vertex("state_alarm").entry_action.raw_name == "NotifyOperator"
    assert machine.get_vertex("state_alarm").exit_action.raw_name == "ResetIndicator"


def test_phase1_normalize_names_and_variables(tmp_path: Path):
    """Phase1 should normalize state and event names while keeping legal variables unchanged."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="水箱循环单元" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="水箱循环单元">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="水泵待命"/>
                </region>
              </ownedBehavior>
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_counter" name="counter">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_counter_default" value="0"/>
              </ownedAttribute>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_ready" name="流量已稳定"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_ready" name="" signal="signal_ready"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = load_sysdesim_machine(str(xml_file))
    normalize_machine(machine)

    assert machine.safe_name == "ShuiXiangXunHuanDanYuan"
    assert machine.get_vertex("state_idle").safe_name == "ShuiBengDaiMing"
    assert machine.get_signal("signal_ready").safe_name == "LIU_LIANG_YI_WEN_DING"
    assert machine.variables[0].safe_name == "counter"
    assert make_internal_name("flag_route", ["pump_loop"], "transition-001").startswith(
        "__sysdesim_flag_route_pump_loop_"
    )


def test_phase1_rejects_illegal_explicit_variable_name():
    """Illegal explicit variable identifiers should fail instead of being renamed."""
    machine = IrMachine(
        machine_id="machine_1",
        name="TestRig",
        root_region=IrRegion(region_id="region_1", owner_state_id=None),
        variables=[
            IrVariable(
                variable_id="var_1",
                raw_name="温度",
                type_name="int",
                default_value="0",
                is_synthetic=False,
            )
        ],
    )

    with pytest.raises(ValueError, match="Unsupported explicit variable name"):
        normalize_machine(machine)


def test_phase2_build_ast_and_roundtrip(tmp_path: Path):
    """Phase2 should emit valid DSL for single-region, same-level transitions."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Mixer Panel" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Mixer Panel">
                <region xmi:type="uml:Region" xmi:id="region_1" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_go" source="state_idle" target="state_blend">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="event_start"/>
                  </transition>
                  <transition xmi:type="uml:Transition" xmi:id="tx_back" source="state_blend" target="state_idle"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Buffer Ready"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_blend" name="Mix Cycle">
                    <entry xmi:type="uml:Activity" xmi:id="entry_blend" name="PrimeValve"/>
                    <exit xmi:type="uml:Activity" xmi:id="exit_blend" name="DrainValve"/>
                  </subvertex>
                </region>
              </ownedBehavior>
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_counter" name="counter">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_counter_default" value="0"/>
              </ownedAttribute>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_start" name="Start Blend"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="event_start" name="" signal="signal_start"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = load_sysdesim_machine(str(xml_file))
    normalize_machine(machine)
    program = build_machine_ast(machine)
    parsed, model = validate_program_roundtrip(program)
    dsl_code = str(program)

    assert program.root_state.name == "MixerPanel"
    assert [item.name for item in program.root_state.events] == ["START_BLEND"]
    assert "state BufferReady named " in dsl_code
    assert "event START_BLEND named " in dsl_code
    assert "state MixCycle named " in dsl_code
    assert "enter abstract PrimeValve;" in dsl_code
    assert "exit abstract DrainValve;" in dsl_code
    assert "BufferReady -> MixCycle : /START_BLEND;" in dsl_code
    assert parsed.root_state.name == "MixerPanel"
    assert model.root_state.name == "MixerPanel"
    assert "counter" in model.defines


def test_phase2_missing_init_in_composite_state_raises(tmp_path: Path):
    """Composite states without a valid init pseudostate should fail in phase2."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Valve Rack" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Valve Rack">
                <region xmi:type="uml:Region" xmi:id="region_1" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_parent"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Valve Group">
                    <region xmi:type="uml:Region" xmi:id="region_child" name="">
                      <subvertex xmi:type="uml:State" xmi:id="state_child" name="Flush Step"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    machine = load_sysdesim_machine(str(xml_file))
    normalize_machine(machine)

    with pytest.raises(ValueError, match="must have exactly one init pseudostate"):
        build_machine_ast(machine)


def test_convert_sysdesim_xml_to_dsl_runs_end_to_end(tmp_path: Path):
    """The public end-to-end converter should return DSL text for the supported subset."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Door Cycle" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Door Cycle">
                <region xmi:type="uml:Region" xmi:id="region_1" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_closed"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_open" source="state_closed" target="state_open">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_open" event="event_open"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_closed" name="Closed"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_open" name="Open"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_open" name="Open Request"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="event_open" name="" signal="signal_open"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    dsl_code = convert_sysdesim_xml_to_dsl(str(xml_file))

    assert "state DoorCycle;" not in dsl_code
    assert "state DoorCycle named " in dsl_code
    assert "Closed -> Open : /OPEN_REQUEST;" in dsl_code
