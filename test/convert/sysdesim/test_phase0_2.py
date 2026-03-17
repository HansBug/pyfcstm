"""Unit tests for the SysDeSim phase0-2 conversion pipeline."""

import inspect
from dataclasses import fields
from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.convert.sysdesim import (
    build_machine_ast,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_dsl,
    emit_program,
    load_sysdesim_machine,
    load_sysdesim_xml,
    make_internal_name,
    normalize_machine,
    validate_program_roundtrip,
)
from pyfcstm.convert.sysdesim.ir import (
    IrActionRef,
    IrMachine,
    IrRegion,
    IrSignal,
    IrSignalEvent,
    IrTimeEvent,
    IrTransition,
    IrVariable,
    IrVertex,
)
from pyfcstm.model import expr as model_expr
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


def _assert_dataclass_field_names(obj, expected_names) -> None:
    """Assert that a dataclass instance exposes exactly the expected fields."""
    assert [item.name for item in fields(obj) if not item.name.startswith("_")] == list(expected_names)


def _assert_property_names(obj, expected_names) -> None:
    """Assert that an object type exposes exactly the expected properties."""
    assert tuple(
        name for name, value in inspect.getmembers(type(obj)) if isinstance(value, property)
    ) == tuple(expected_names)


def _assert_program_loads_to_state_machine(
    program: dsl_nodes.StateMachineDSLProgram,
) -> StateMachine:
    """Assert that a DSL program can be loaded into the public StateMachine model."""
    model = parse_dsl_node_to_state_machine(program)
    assert isinstance(model, StateMachine)
    return model


def _assert_dsl_code_loads_to_state_machine(dsl_code: str) -> StateMachine:
    """Assert that DSL text can be parsed and loaded into the public StateMachine model."""
    parsed_program = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    return _assert_program_loads_to_state_machine(parsed_program)


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

    _assert_dataclass_field_names(
        machine,
        (
            "machine_id",
            "name",
            "root_region",
            "signals",
            "signal_events",
            "time_events",
            "variables",
            "diagnostics",
            "safe_name",
            "display_name",
        ),
    )
    assert machine.machine_id == "machine_1"
    assert machine.name == "ThermalStation"
    assert machine.variables == []
    assert machine.diagnostics == []
    assert machine.safe_name is None
    assert machine.display_name is None

    root_region = machine.root_region
    _assert_dataclass_field_names(root_region, ("region_id", "owner_state_id", "vertices", "transitions"))
    assert root_region.region_id == "region_root"
    assert root_region.owner_state_id is None
    assert [vertex.vertex_id for vertex in root_region.vertices] == [
        "init_root",
        "state_idle",
        "state_heat",
        "state_alarm",
    ]
    assert [transition.transition_id for transition in root_region.transitions] == ["tx_init", "tx_heat", "tx_alarm"]

    init_root = machine.get_vertex("init_root")
    _assert_dataclass_field_names(
        init_root,
        (
            "vertex_id",
            "vertex_type",
            "raw_name",
            "safe_name",
            "display_name",
            "parent_region_id",
            "entry_action",
            "exit_action",
            "state_invariant",
            "regions",
            "is_composite",
            "is_parallel_owner",
        ),
    )
    assert init_root.vertex_id == "init_root"
    assert init_root.vertex_type == "pseudostate"
    assert init_root.raw_name == ""
    assert init_root.safe_name is None
    assert init_root.display_name is None
    assert init_root.parent_region_id == "region_root"
    assert init_root.entry_action is None
    assert init_root.exit_action is None
    assert init_root.state_invariant is None
    assert init_root.regions == []
    assert init_root.is_composite is False
    assert init_root.is_parallel_owner is False

    state_heat = machine.get_vertex("state_heat")
    _assert_dataclass_field_names(
        state_heat,
        (
            "vertex_id",
            "vertex_type",
            "raw_name",
            "safe_name",
            "display_name",
            "parent_region_id",
            "entry_action",
            "exit_action",
            "state_invariant",
            "regions",
            "is_composite",
            "is_parallel_owner",
        ),
    )
    assert state_heat.vertex_id == "state_heat"
    assert state_heat.vertex_type == "state"
    assert state_heat.raw_name == "Loop Heat"
    assert state_heat.safe_name is None
    assert state_heat.display_name is None
    assert state_heat.parent_region_id == "region_root"
    assert state_heat.entry_action is None
    assert state_heat.exit_action is None
    assert state_heat.state_invariant is None
    assert [region.region_id for region in state_heat.regions] == ["region_heat_a", "region_heat_b"]
    assert state_heat.is_composite is True
    assert state_heat.is_parallel_owner is True

    state_alarm = machine.get_vertex("state_alarm")
    assert state_alarm.vertex_id == "state_alarm"
    assert state_alarm.vertex_type == "state"
    assert state_alarm.raw_name == "Alarm Hold"
    assert state_alarm.safe_name is None
    assert state_alarm.display_name is None
    assert state_alarm.parent_region_id == "region_root"
    assert state_alarm.state_invariant is None
    assert state_alarm.regions == []
    assert state_alarm.is_composite is False
    assert state_alarm.is_parallel_owner is False

    entry_action = state_alarm.entry_action
    _assert_dataclass_field_names(entry_action, ("action_id", "raw_name", "safe_name", "display_name"))
    assert entry_action.action_id == "entry_alarm"
    assert entry_action.raw_name == "NotifyOperator"
    assert entry_action.safe_name is None
    assert entry_action.display_name is None

    exit_action = state_alarm.exit_action
    _assert_dataclass_field_names(exit_action, ("action_id", "raw_name", "safe_name", "display_name"))
    assert exit_action.action_id == "exit_alarm"
    assert exit_action.raw_name == "ResetIndicator"
    assert exit_action.safe_name is None
    assert exit_action.display_name is None

    tx_heat = machine.get_transition("tx_heat")
    _assert_dataclass_field_names(
        tx_heat,
        (
            "transition_id",
            "source_id",
            "target_id",
            "trigger_kind",
            "trigger_ref_id",
            "guard_expr_raw",
            "guard_expr_ir",
            "effect_action",
            "source_region_id",
            "target_region_id",
            "is_cross_level",
            "is_cross_region",
            "origin_kind",
        ),
    )
    assert tx_heat.transition_id == "tx_heat"
    assert tx_heat.source_id == "state_idle"
    assert tx_heat.target_id == "state_heat"
    assert tx_heat.trigger_kind == "signal"
    assert tx_heat.trigger_ref_id == "signal_evt_heat"
    assert tx_heat.guard_expr_raw is None
    assert tx_heat.guard_expr_ir is None
    assert tx_heat.effect_action is None
    assert tx_heat.source_region_id == "region_root"
    assert tx_heat.target_region_id == "region_root"
    assert tx_heat.is_cross_level is False
    assert tx_heat.is_cross_region is False
    assert tx_heat.origin_kind == "original"

    tx_alarm = machine.get_transition("tx_alarm")
    assert tx_alarm.transition_id == "tx_alarm"
    assert tx_alarm.source_id == "state_heat"
    assert tx_alarm.target_id == "state_alarm"
    assert tx_alarm.trigger_kind == "time"
    assert tx_alarm.trigger_ref_id == "time_evt_alarm"
    assert tx_alarm.guard_expr_raw is None
    assert tx_alarm.guard_expr_ir is None
    assert tx_alarm.effect_action is None
    assert tx_alarm.source_region_id == "region_root"
    assert tx_alarm.target_region_id == "region_root"
    assert tx_alarm.is_cross_level is False
    assert tx_alarm.is_cross_region is False
    assert tx_alarm.origin_kind == "original"

    signal = machine.get_signal("signal_heat")
    _assert_dataclass_field_names(signal, ("signal_id", "raw_name", "safe_name", "display_name"))
    assert signal.signal_id == "signal_heat"
    assert signal.raw_name == "Heat Request"
    assert signal.safe_name is None
    assert signal.display_name is None

    signal_event = machine.get_signal_event("signal_evt_heat")
    _assert_dataclass_field_names(signal_event, ("event_id", "signal_id", "raw_name", "safe_name", "display_name"))
    assert signal_event.event_id == "signal_evt_heat"
    assert signal_event.signal_id == "signal_heat"
    assert signal_event.raw_name == ""
    assert signal_event.safe_name is None
    assert signal_event.display_name is None

    time_event = machine.get_time_event("time_evt_alarm")
    _assert_dataclass_field_names(
        time_event,
        ("time_event_id", "raw_literal", "is_relative", "normalized_delay", "normalized_unit"),
    )
    assert time_event.time_event_id == "time_evt_alarm"
    assert time_event.raw_literal == "0.5s"
    assert time_event.is_relative is True
    assert time_event.normalized_delay is None
    assert time_event.normalized_unit is None

    assert [region.region_id for region in machine.walk_regions()] == ["region_root", "region_heat_a", "region_heat_b"]
    assert [vertex.vertex_id for vertex in machine.walk_vertices()] == [
        "init_root",
        "state_idle",
        "state_heat",
        "state_alarm",
        "init_heat_a",
        "state_cycle",
        "init_heat_b",
        "state_guard",
    ]
    assert [transition.transition_id for transition in machine.walk_transitions()] == [
        "tx_init",
        "tx_heat",
        "tx_alarm",
        "tx_heat_init_a",
        "tx_heat_init_b",
    ]
    assert machine.state_id_path("state_cycle") == ("state_heat", "state_cycle")
    assert machine.state_path("state_cycle") == ("Loop Heat", "Cycle")
    assert machine.state_path("state_cycle", use_safe_name=True) == ("Loop Heat", "Cycle")
    assert machine.descendant_state_ids("state_heat") == ("state_cycle", "state_guard")
    assert machine.region_count("state_heat") == 2
    assert machine.lca_state_id("state_cycle", "state_guard") == "state_heat"
    machine_dict = machine.to_dict()
    assert tuple(key for key in machine_dict if not key.startswith("_")) == (
        "machine_id",
        "name",
        "root_region",
        "signals",
        "signal_events",
        "time_events",
        "variables",
        "diagnostics",
        "safe_name",
        "display_name",
    )
    assert machine_dict["name"] == "ThermalStation"
    assert machine_dict["time_events"][0]["raw_literal"] == "0.5s"


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

    _assert_dataclass_field_names(
        machine.variables[0],
        ("variable_id", "raw_name", "safe_name", "display_name", "type_name", "default_value", "is_synthetic"),
    )
    _assert_dataclass_field_names(
        machine.get_signal("signal_ready"),
        ("signal_id", "raw_name", "safe_name", "display_name"),
    )
    _assert_dataclass_field_names(
        machine.get_signal_event("signal_evt_ready"),
        ("event_id", "signal_id", "raw_name", "safe_name", "display_name"),
    )
    assert machine.safe_name == "ShuiXiangXunHuanDanYuan"
    assert machine.display_name == "水箱循环单元"
    assert machine.get_vertex("state_idle").safe_name == "ShuiBengDaiMing"
    assert machine.get_vertex("state_idle").display_name == "水泵待命"
    assert machine.get_signal("signal_ready").safe_name == "LIU_LIANG_YI_WEN_DING"
    assert machine.get_signal("signal_ready").display_name == "流量已稳定"
    assert machine.get_signal_event("signal_evt_ready").safe_name == "LIU_LIANG_YI_WEN_DING"
    assert machine.get_signal_event("signal_evt_ready").display_name == "流量已稳定"
    assert machine.variables[0].safe_name == "counter"
    assert machine.variables[0].display_name == "counter"
    assert machine.variables[0].type_name == "int"
    assert machine.variables[0].default_value == "0"
    assert machine.variables[0].is_synthetic is False
    assert machine.state_path("state_idle", use_safe_name=True) == ("ShuiBengDaiMing",)
    assert make_internal_name("flag_route", ["pump_loop"], "transition-001") == (
        "__sysdesim_flag_route_pump_loop_ion001"
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
    dsl_code = _normalize_newlines(str(program))
    expected_dsl = dedent(
        """\
        def int counter = 0;
        state MixerPanel named 'Mixer Panel' {
            state BufferReady named 'Buffer Ready';
            state MixCycle named 'Mix Cycle' {
                enter abstract PrimeValve;
                exit abstract DrainValve;
            }
            event START_BLEND named 'Start Blend';
            [*] -> BufferReady;
            BufferReady -> MixCycle : /START_BLEND;
            MixCycle -> BufferReady;
        }"""
    )

    assert dsl_code == expected_dsl
    assert _normalize_newlines(emit_program(program)) == expected_dsl
    assert _normalize_newlines(str(parsed)) == expected_dsl
    assert _assert_program_loads_to_state_machine(program).root_state.name == "MixerPanel"
    assert _assert_program_loads_to_state_machine(parsed).root_state.name == "MixerPanel"
    assert _assert_dsl_code_loads_to_state_machine(dsl_code).root_state.name == "MixerPanel"

    _assert_dataclass_field_names(program, ("definitions", "root_state"))
    assert len(program.definitions) == 1
    definition = program.definitions[0]
    _assert_dataclass_field_names(definition, ("name", "type", "expr"))
    assert definition.name == "counter"
    assert definition.type == "int"
    assert isinstance(definition.expr, dsl_nodes.Integer)
    _assert_dataclass_field_names(definition.expr, ("raw",))
    assert definition.expr.raw == "0"
    assert str(definition) == "def int counter = 0;"

    root_state = program.root_state
    _assert_dataclass_field_names(
        root_state,
        (
            "name",
            "extra_name",
            "events",
            "substates",
            "transitions",
            "enters",
            "durings",
            "exits",
            "during_aspects",
            "force_transitions",
            "is_pseudo",
        ),
    )
    assert root_state.name == "MixerPanel"
    assert root_state.extra_name == "Mixer Panel"
    assert root_state.enters == []
    assert root_state.durings == []
    assert root_state.exits == []
    assert root_state.during_aspects == []
    assert root_state.force_transitions == []
    assert root_state.is_pseudo is False
    assert [state.name for state in root_state.substates] == ["BufferReady", "MixCycle"]
    assert [event.name for event in root_state.events] == ["START_BLEND"]
    assert [transition.from_state for transition in root_state.transitions] == [
        dsl_nodes.INIT_STATE,
        "BufferReady",
        "MixCycle",
    ]
    assert [transition.to_state for transition in root_state.transitions] == ["BufferReady", "MixCycle", "BufferReady"]

    root_event = root_state.events[0]
    _assert_dataclass_field_names(root_event, ("name", "extra_name"))
    assert root_event.name == "START_BLEND"
    assert root_event.extra_name == "Start Blend"
    assert str(root_event) == "event START_BLEND named 'Start Blend';"

    buffer_ready = root_state.substates[0]
    _assert_dataclass_field_names(
        buffer_ready,
        (
            "name",
            "extra_name",
            "events",
            "substates",
            "transitions",
            "enters",
            "durings",
            "exits",
            "during_aspects",
            "force_transitions",
            "is_pseudo",
        ),
    )
    assert buffer_ready.name == "BufferReady"
    assert buffer_ready.extra_name == "Buffer Ready"
    assert buffer_ready.events == []
    assert buffer_ready.substates == []
    assert buffer_ready.transitions == []
    assert buffer_ready.enters == []
    assert buffer_ready.durings == []
    assert buffer_ready.exits == []
    assert buffer_ready.during_aspects == []
    assert buffer_ready.force_transitions == []
    assert buffer_ready.is_pseudo is False
    assert str(buffer_ready) == "state BufferReady named 'Buffer Ready';"

    mix_cycle = root_state.substates[1]
    _assert_dataclass_field_names(
        mix_cycle,
        (
            "name",
            "extra_name",
            "events",
            "substates",
            "transitions",
            "enters",
            "durings",
            "exits",
            "during_aspects",
            "force_transitions",
            "is_pseudo",
        ),
    )
    assert mix_cycle.name == "MixCycle"
    assert mix_cycle.extra_name == "Mix Cycle"
    assert mix_cycle.events == []
    assert mix_cycle.substates == []
    assert mix_cycle.transitions == []
    assert mix_cycle.durings == []
    assert mix_cycle.during_aspects == []
    assert mix_cycle.force_transitions == []
    assert mix_cycle.is_pseudo is False
    assert len(mix_cycle.enters) == 1
    assert len(mix_cycle.exits) == 1

    enter_stmt = mix_cycle.enters[0]
    _assert_dataclass_field_names(enter_stmt, ("name", "doc"))
    assert isinstance(enter_stmt, dsl_nodes.EnterAbstractFunction)
    assert enter_stmt.name == "PrimeValve"
    assert enter_stmt.doc is None
    assert str(enter_stmt) == "enter abstract PrimeValve;"

    exit_stmt = mix_cycle.exits[0]
    _assert_dataclass_field_names(exit_stmt, ("name", "doc"))
    assert isinstance(exit_stmt, dsl_nodes.ExitAbstractFunction)
    assert exit_stmt.name == "DrainValve"
    assert exit_stmt.doc is None
    assert str(exit_stmt) == "exit abstract DrainValve;"

    init_transition, go_transition, back_transition = root_state.transitions
    for transition in (init_transition, go_transition, back_transition):
        _assert_dataclass_field_names(
            transition,
            ("from_state", "to_state", "event_id", "condition_expr", "post_operations"),
        )
        assert transition.condition_expr is None
        assert transition.post_operations == []

    assert init_transition.from_state is dsl_nodes.INIT_STATE
    assert init_transition.to_state == "BufferReady"
    assert init_transition.event_id is None
    assert str(init_transition) == "[*] -> BufferReady;"

    assert go_transition.from_state == "BufferReady"
    assert go_transition.to_state == "MixCycle"
    assert isinstance(go_transition.event_id, dsl_nodes.ChainID)
    _assert_dataclass_field_names(go_transition.event_id, ("path", "is_absolute"))
    assert go_transition.event_id.path == ["START_BLEND"]
    assert go_transition.event_id.is_absolute is True
    assert str(go_transition) == "BufferReady -> MixCycle : /START_BLEND;"

    assert back_transition.from_state == "MixCycle"
    assert back_transition.to_state == "BufferReady"
    assert back_transition.event_id is None
    assert str(back_transition) == "MixCycle -> BufferReady;"

    _assert_dataclass_field_names(parsed, ("definitions", "root_state"))
    parsed_definition = parsed.definitions[0]
    assert parsed_definition.name == "counter"
    assert parsed_definition.type == "int"
    assert isinstance(parsed_definition.expr, dsl_nodes.Integer)
    assert parsed_definition.expr.raw == "0"
    parsed_root = parsed.root_state
    assert parsed_root.name == "MixerPanel"
    assert parsed_root.extra_name == "Mixer Panel"
    assert [item.name for item in parsed_root.events] == ["START_BLEND"]
    assert [item.extra_name for item in parsed_root.events] == ["Start Blend"]
    assert [item.name for item in parsed_root.substates] == ["BufferReady", "MixCycle"]
    assert [item.extra_name for item in parsed_root.substates] == ["Buffer Ready", "Mix Cycle"]
    assert [item.from_state for item in parsed_root.transitions] == [dsl_nodes.INIT_STATE, "BufferReady", "MixCycle"]
    assert [item.to_state for item in parsed_root.transitions] == ["BufferReady", "MixCycle", "BufferReady"]
    assert parsed_root.substates[1].enters[0].name == "PrimeValve"
    assert parsed_root.substates[1].exits[0].name == "DrainValve"

    _assert_dataclass_field_names(model, ("defines", "root_state"))
    assert tuple(model.defines) == ("counter",)
    assert list(state.name for state in model.walk_states()) == ["MixerPanel", "BufferReady", "MixCycle"]

    var_define = model.defines["counter"]
    _assert_dataclass_field_names(var_define, ("name", "type", "init"))
    assert var_define.name == "counter"
    assert var_define.type == "int"
    assert isinstance(var_define.init, model_expr.Integer)
    _assert_dataclass_field_names(var_define.init, ("value",))
    assert var_define.init.value == 0
    assert var_define.to_ast_node() == definition
    assert var_define.name_ast_node().name == "counter"

    model_root = model.root_state
    _assert_dataclass_field_names(
        model_root,
        (
            "name",
            "path",
            "substates",
            "events",
            "transitions",
            "named_functions",
            "on_enters",
            "on_durings",
            "on_exits",
            "on_during_aspects",
            "parent_ref",
            "substate_name_to_id",
            "extra_name",
            "is_pseudo",
        ),
    )
    _assert_property_names(
        model_root,
        (
            "abstract_on_during_aspects",
            "abstract_on_durings",
            "abstract_on_enters",
            "abstract_on_exits",
            "init_transitions",
            "is_leaf_state",
            "is_root_state",
            "is_stoppable",
            "non_abstract_on_during_aspects",
            "non_abstract_on_durings",
            "non_abstract_on_enters",
            "non_abstract_on_exits",
            "parent",
            "transitions_entering_children",
            "transitions_entering_children_simplified",
            "transitions_from",
            "transitions_to",
        ),
    )
    assert model_root.name == "MixerPanel"
    assert model_root.path == ("MixerPanel",)
    assert tuple(model_root.substates) == ("BufferReady", "MixCycle")
    assert tuple(model_root.events) == ("START_BLEND",)
    assert len(model_root.transitions) == 3
    assert model_root.named_functions == {}
    assert model_root.on_enters == []
    assert model_root.on_durings == []
    assert model_root.on_exits == []
    assert model_root.on_during_aspects == []
    assert model_root.parent_ref is None
    assert model_root.substate_name_to_id == {"BufferReady": 0, "MixCycle": 1}
    assert model_root.extra_name == "Mixer Panel"
    assert model_root.is_pseudo is False
    assert model_root.parent is None
    assert model_root.is_leaf_state is False
    assert model_root.is_stoppable is False
    assert model_root.is_root_state is True
    assert model_root.abstract_on_enters == []
    assert model_root.non_abstract_on_enters == []
    assert model_root.abstract_on_durings == []
    assert model_root.non_abstract_on_durings == []
    assert model_root.abstract_on_exits == []
    assert model_root.non_abstract_on_exits == []
    assert model_root.abstract_on_during_aspects == []
    assert model_root.non_abstract_on_during_aspects == []
    assert model_root.list_on_enters() == []
    assert model_root.list_on_enters(with_ids=True) == []
    assert model_root.list_on_durings() == []
    assert model_root.list_on_durings(with_ids=True) == []
    assert model_root.list_on_exits() == []
    assert model_root.list_on_exits(with_ids=True) == []
    assert model_root.list_on_during_aspects() == []
    assert model_root.list_on_during_aspects(with_ids=True) == []
    assert list(model_root.iter_on_during_before_aspect_recursively()) == []
    assert list(model_root.iter_on_during_before_aspect_recursively(with_ids=True)) == []
    assert list(model_root.iter_on_during_after_aspect_recursively()) == []
    assert list(model_root.iter_on_during_after_aspect_recursively(with_ids=True)) == []
    assert list(model_root.iter_on_during_aspect_recursively()) == []
    assert list(model_root.iter_on_during_aspect_recursively(with_ids=True)) == []
    assert model_root.list_on_during_aspect_recursively() == []
    assert model_root.list_on_during_aspect_recursively(with_ids=True) == []
    assert len(model_root.init_transitions) == 1
    assert model_root.init_transitions[0].from_state is dsl_nodes.INIT_STATE
    assert [item.from_state for item in model_root.transitions_entering_children] == [dsl_nodes.INIT_STATE]
    assert [item.to_state for item in model_root.transitions_entering_children] == ["BufferReady"]
    assert len(model_root.transitions_entering_children_simplified) == 1
    assert model_root.transitions_entering_children_simplified[0].from_state is dsl_nodes.INIT_STATE
    assert len(model_root.transitions_from) == 1
    assert model_root.transitions_from[0].from_state == "MixerPanel"
    assert model_root.transitions_from[0].to_state is dsl_nodes.EXIT_STATE
    assert model_root.transitions_from[0].event is None
    assert model_root.transitions_from[0].guard is None
    assert model_root.transitions_from[0].effects == []
    assert len(model_root.transitions_to) == 1
    assert model_root.transitions_to[0].from_state is dsl_nodes.INIT_STATE
    assert model_root.transitions_to[0].to_state == "MixerPanel"
    assert model_root.transitions_to[0].event is None
    assert model_root.transitions_to[0].guard is None
    assert model_root.transitions_to[0].effects == []

    model_event = model_root.events["START_BLEND"]
    _assert_dataclass_field_names(model_event, ("name", "state_path", "extra_name"))
    _assert_property_names(model_event, ("path", "path_name"))
    assert model_event.name == "START_BLEND"
    assert model_event.state_path == ("MixerPanel",)
    assert model_event.extra_name == "Start Blend"
    assert model_event.path == ("MixerPanel", "START_BLEND")
    assert model_event.path_name == "MixerPanel.START_BLEND"
    assert model_event.to_ast_node() == root_event
    assert model.resolve_event("MixerPanel.START_BLEND") is model_event
    assert model_root.resolve_event("START_BLEND") is model_event
    assert model_root.resolve_event("/START_BLEND") is model_event

    model_init, model_go, model_back = model_root.transitions
    for transition in (model_init, model_go, model_back):
        _assert_dataclass_field_names(
            transition,
            ("from_state", "to_state", "event", "guard", "effects", "parent_ref"),
        )
        _assert_property_names(transition, ("parent",))
        assert transition.parent is model_root
        assert transition.parent_ref is not None
        assert transition.guard is None
        assert transition.effects == []

    assert model_init.from_state is dsl_nodes.INIT_STATE
    assert model_init.to_state == "BufferReady"
    assert model_init.event is None
    assert model_init.to_ast_node() == init_transition

    assert model_go.from_state == "BufferReady"
    assert model_go.to_state == "MixCycle"
    assert model_go.event is model_event
    model_go_ast = model_go.to_ast_node()
    assert model_go_ast.from_state == "BufferReady"
    assert model_go_ast.to_state == "MixCycle"
    assert model_go_ast.condition_expr is None
    assert model_go_ast.post_operations == []
    assert model_go_ast.event_id.path == ["START_BLEND"]
    assert model_go_ast.event_id.is_absolute is False
    assert str(model_go_ast) == "BufferReady -> MixCycle : START_BLEND;"

    assert model_back.from_state == "MixCycle"
    assert model_back.to_state == "BufferReady"
    assert model_back.event is None
    assert model_back.to_ast_node() == back_transition

    model_buffer_ready = model_root.substates["BufferReady"]
    _assert_dataclass_field_names(
        model_buffer_ready,
        (
            "name",
            "path",
            "substates",
            "events",
            "transitions",
            "named_functions",
            "on_enters",
            "on_durings",
            "on_exits",
            "on_during_aspects",
            "parent_ref",
            "substate_name_to_id",
            "extra_name",
            "is_pseudo",
        ),
    )
    _assert_property_names(
        model_buffer_ready,
        (
            "abstract_on_during_aspects",
            "abstract_on_durings",
            "abstract_on_enters",
            "abstract_on_exits",
            "init_transitions",
            "is_leaf_state",
            "is_root_state",
            "is_stoppable",
            "non_abstract_on_during_aspects",
            "non_abstract_on_durings",
            "non_abstract_on_enters",
            "non_abstract_on_exits",
            "parent",
            "transitions_entering_children",
            "transitions_entering_children_simplified",
            "transitions_from",
            "transitions_to",
        ),
    )
    assert model_buffer_ready.name == "BufferReady"
    assert model_buffer_ready.path == ("MixerPanel", "BufferReady")
    assert model_buffer_ready.substates == {}
    assert model_buffer_ready.events == {}
    assert model_buffer_ready.transitions == []
    assert model_buffer_ready.named_functions == {}
    assert model_buffer_ready.on_enters == []
    assert model_buffer_ready.on_durings == []
    assert model_buffer_ready.on_exits == []
    assert model_buffer_ready.on_during_aspects == []
    assert model_buffer_ready.parent_ref is not None
    assert model_buffer_ready.substate_name_to_id == {}
    assert model_buffer_ready.extra_name == "Buffer Ready"
    assert model_buffer_ready.is_pseudo is False
    assert model_buffer_ready.parent is model_root
    assert model_buffer_ready.is_leaf_state is True
    assert model_buffer_ready.is_stoppable is True
    assert model_buffer_ready.is_root_state is False
    assert model_buffer_ready.init_transitions == []
    assert model_buffer_ready.transitions_entering_children == []
    assert model_buffer_ready.transitions_entering_children_simplified == [None]
    assert [item.from_state for item in model_buffer_ready.transitions_from] == ["BufferReady"]
    assert [item.to_state for item in model_buffer_ready.transitions_from] == ["MixCycle"]
    assert [item.from_state for item in model_buffer_ready.transitions_to] == [dsl_nodes.INIT_STATE, "MixCycle"]
    assert [item.to_state for item in model_buffer_ready.transitions_to] == ["BufferReady", "BufferReady"]
    assert model_buffer_ready.abstract_on_enters == []
    assert model_buffer_ready.non_abstract_on_enters == []
    assert model_buffer_ready.abstract_on_durings == []
    assert model_buffer_ready.non_abstract_on_durings == []
    assert model_buffer_ready.abstract_on_exits == []
    assert model_buffer_ready.non_abstract_on_exits == []
    assert model_buffer_ready.abstract_on_during_aspects == []
    assert model_buffer_ready.non_abstract_on_during_aspects == []
    assert model_buffer_ready.list_on_enters() == []
    assert model_buffer_ready.list_on_durings() == []
    assert model_buffer_ready.list_on_exits() == []
    assert model_buffer_ready.list_on_during_aspects() == []
    assert list(model_buffer_ready.iter_on_during_before_aspect_recursively()) == []
    assert list(model_buffer_ready.iter_on_during_after_aspect_recursively()) == []
    assert list(model_buffer_ready.iter_on_during_aspect_recursively()) == []
    assert model_buffer_ready.list_on_during_aspect_recursively() == []

    model_mix_cycle = model_root.substates["MixCycle"]
    _assert_dataclass_field_names(
        model_mix_cycle,
        (
            "name",
            "path",
            "substates",
            "events",
            "transitions",
            "named_functions",
            "on_enters",
            "on_durings",
            "on_exits",
            "on_during_aspects",
            "parent_ref",
            "substate_name_to_id",
            "extra_name",
            "is_pseudo",
        ),
    )
    _assert_property_names(
        model_mix_cycle,
        (
            "abstract_on_during_aspects",
            "abstract_on_durings",
            "abstract_on_enters",
            "abstract_on_exits",
            "init_transitions",
            "is_leaf_state",
            "is_root_state",
            "is_stoppable",
            "non_abstract_on_during_aspects",
            "non_abstract_on_durings",
            "non_abstract_on_enters",
            "non_abstract_on_exits",
            "parent",
            "transitions_entering_children",
            "transitions_entering_children_simplified",
            "transitions_from",
            "transitions_to",
        ),
    )
    assert model_mix_cycle.name == "MixCycle"
    assert model_mix_cycle.path == ("MixerPanel", "MixCycle")
    assert model_mix_cycle.substates == {}
    assert model_mix_cycle.events == {}
    assert model_mix_cycle.transitions == []
    assert tuple(model_mix_cycle.named_functions) == ("PrimeValve", "DrainValve")
    assert len(model_mix_cycle.on_enters) == 1
    assert model_mix_cycle.on_durings == []
    assert len(model_mix_cycle.on_exits) == 1
    assert model_mix_cycle.on_during_aspects == []
    assert model_mix_cycle.parent_ref is not None
    assert model_mix_cycle.substate_name_to_id == {}
    assert model_mix_cycle.extra_name == "Mix Cycle"
    assert model_mix_cycle.is_pseudo is False
    assert model_mix_cycle.parent is model_root
    assert model_mix_cycle.is_leaf_state is True
    assert model_mix_cycle.is_stoppable is True
    assert model_mix_cycle.is_root_state is False
    assert model_mix_cycle.init_transitions == []
    assert model_mix_cycle.transitions_entering_children == []
    assert model_mix_cycle.transitions_entering_children_simplified == [None]
    assert [item.from_state for item in model_mix_cycle.transitions_from] == ["MixCycle"]
    assert [item.to_state for item in model_mix_cycle.transitions_from] == ["BufferReady"]
    assert [item.from_state for item in model_mix_cycle.transitions_to] == ["BufferReady"]
    assert [item.to_state for item in model_mix_cycle.transitions_to] == ["MixCycle"]
    assert [item.name for item in model_mix_cycle.abstract_on_enters] == ["PrimeValve"]
    assert model_mix_cycle.non_abstract_on_enters == []
    assert model_mix_cycle.abstract_on_durings == []
    assert model_mix_cycle.non_abstract_on_durings == []
    assert [item.name for item in model_mix_cycle.abstract_on_exits] == ["DrainValve"]
    assert model_mix_cycle.non_abstract_on_exits == []
    assert model_mix_cycle.abstract_on_during_aspects == []
    assert model_mix_cycle.non_abstract_on_during_aspects == []
    assert [item.name for item in model_mix_cycle.list_on_enters()] == ["PrimeValve"]
    assert model_mix_cycle.list_on_enters(with_ids=True)[0][0] == 1
    assert model_mix_cycle.list_on_enters(with_ids=True)[0][1] is model_mix_cycle.on_enters[0]
    assert model_mix_cycle.list_on_durings() == []
    assert [item.name for item in model_mix_cycle.list_on_exits()] == ["DrainValve"]
    assert model_mix_cycle.list_on_exits(with_ids=True)[0][0] == 1
    assert model_mix_cycle.list_on_exits(with_ids=True)[0][1] is model_mix_cycle.on_exits[0]
    assert model_mix_cycle.list_on_during_aspects() == []
    assert list(model_mix_cycle.iter_on_during_before_aspect_recursively()) == []
    assert list(model_mix_cycle.iter_on_during_before_aspect_recursively(with_ids=True)) == []
    assert list(model_mix_cycle.iter_on_during_after_aspect_recursively()) == []
    assert list(model_mix_cycle.iter_on_during_after_aspect_recursively(with_ids=True)) == []
    assert list(model_mix_cycle.iter_on_during_aspect_recursively()) == []
    assert list(model_mix_cycle.iter_on_during_aspect_recursively(with_ids=True)) == []
    assert model_mix_cycle.list_on_during_aspect_recursively() == []
    assert model_mix_cycle.list_on_during_aspect_recursively(with_ids=True) == []

    enter_action = model_mix_cycle.on_enters[0]
    _assert_dataclass_field_names(
        enter_action,
        ("stage", "aspect", "name", "doc", "operations", "is_abstract", "state_path", "ref", "ref_state_path", "parent_ref"),
    )
    _assert_property_names(enter_action, ("func_name", "is_aspect", "is_ref", "parent"))
    assert enter_action.stage == "enter"
    assert enter_action.aspect is None
    assert enter_action.name == "PrimeValve"
    assert enter_action.doc is None
    assert enter_action.operations == []
    assert enter_action.is_abstract is True
    assert enter_action.state_path == ("MixerPanel", "MixCycle", "PrimeValve")
    assert enter_action.ref is None
    assert enter_action.ref_state_path is None
    assert enter_action.parent_ref is not None
    assert enter_action.parent is model_mix_cycle
    assert enter_action.is_ref is False
    assert enter_action.is_aspect is False
    assert enter_action.func_name == "MixerPanel.MixCycle.PrimeValve"
    assert model_mix_cycle.named_functions["PrimeValve"] is enter_action
    assert enter_action.to_ast_node() == enter_stmt

    exit_action = model_mix_cycle.on_exits[0]
    _assert_dataclass_field_names(
        exit_action,
        ("stage", "aspect", "name", "doc", "operations", "is_abstract", "state_path", "ref", "ref_state_path", "parent_ref"),
    )
    _assert_property_names(exit_action, ("func_name", "is_aspect", "is_ref", "parent"))
    assert exit_action.stage == "exit"
    assert exit_action.aspect is None
    assert exit_action.name == "DrainValve"
    assert exit_action.doc is None
    assert exit_action.operations == []
    assert exit_action.is_abstract is True
    assert exit_action.state_path == ("MixerPanel", "MixCycle", "DrainValve")
    assert exit_action.ref is None
    assert exit_action.ref_state_path is None
    assert exit_action.parent_ref is not None
    assert exit_action.parent is model_mix_cycle
    assert exit_action.is_ref is False
    assert exit_action.is_aspect is False
    assert exit_action.func_name == "MixerPanel.MixCycle.DrainValve"
    assert model_mix_cycle.named_functions["DrainValve"] is exit_action
    assert exit_action.to_ast_node() == exit_stmt

    model_roundtrip_ast = model.to_ast_node()
    assert _normalize_newlines(str(model_roundtrip_ast)) == dedent(
        """\
        def int counter = 0;
        state MixerPanel named 'Mixer Panel' {
            state BufferReady named 'Buffer Ready';
            state MixCycle named 'Mix Cycle' {
                enter abstract PrimeValve;
                exit abstract DrainValve;
            }
            event START_BLEND named 'Start Blend';
            [*] -> BufferReady;
            BufferReady -> MixCycle : START_BLEND;
            MixCycle -> BufferReady;
        }"""
    )


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

    expected_dsl = dedent(
        """\
        state DoorCycle named 'Door Cycle' {
            state Closed;
            state Open;
            event OPEN_REQUEST named 'Open Request';
            [*] -> Closed;
            Closed -> Open : /OPEN_REQUEST;
        }"""
    )
    assert _normalize_newlines(dsl_code) == expected_dsl
    assert _assert_dsl_code_loads_to_state_machine(dsl_code).root_state.name == "DoorCycle"


class TestSysDeSimCoverageScenarios:
    def test_phase0_load_parses_type_default_and_machine_selection_variants(self, tmp_path: Path):
        """Phase0 should cover XML parsing variants through the public loading APIs."""
        xml_file = _write_xml(
            tmp_path,
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <packagedElement xmi:type="uml:PrimitiveType" xmi:id="primitive_int" name="Integer"/>
              <packagedElement xmi:type="uml:PrimitiveType" xmi:id="primitive_real" name="Real"/>
              <packagedElement xmi:type="uml:PrimitiveType" xmi:id="primitive_mode" name="Mode"/>

              <packagedElement xmi:type="uml:Class" xmi:id="class_skip" name="Skip Holder" classifierBehavior="machine_skip">
                <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_skip" name="Skip Holder"/>
              </packagedElement>

              <packagedElement xmi:type="uml:Class" xmi:id="class_parse" name="Parse Variants" classifierBehavior="machine_parse">
                <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_parse" name="Parse Variants">
                  <region xmi:type="uml:Region" xmi:id="region_parse_root" name="">
                    <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_alpha"/>
                    <transition xmi:type="uml:Transition" xmi:id="tx_alpha_beta" source="state_alpha" target="state_beta">
                      <ownedRule xmi:type="uml:Constraint" xmi:id="guard_alpha_beta">
                        <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_alpha_beta_expr">
                          <body> count &gt; 0 </body>
                        </specification>
                      </ownedRule>
                    </transition>
                    <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                    <subvertex xmi:type="uml:State" xmi:id="state_alpha" name="Alpha">
                      <ownedRule xmi:type="uml:Constraint" xmi:id="alpha_rule_missing_spec"/>
                      <ownedRule xmi:type="uml:Constraint" xmi:id="alpha_rule_missing_body">
                        <specification xmi:type="uml:OpaqueExpression" xmi:id="alpha_expr_missing_body"/>
                      </ownedRule>
                      <ownedRule xmi:type="uml:Constraint" xmi:id="alpha_rule">
                        <specification xmi:type="uml:OpaqueExpression" xmi:id="alpha_expr">
                          <body>   </body>
                        </specification>
                      </ownedRule>
                    </subvertex>
                    <subvertex xmi:type="uml:State" xmi:id="state_beta" name="Beta">
                      <ownedRule xmi:type="uml:Constraint" xmi:id="beta_rule">
                        <specification xmi:type="uml:OpaqueExpression" xmi:id="beta_expr">
                          <body> temperature &gt; 10 </body>
                        </specification>
                      </ownedRule>
                    </subvertex>
                    <subvertex xmi:type="uml:FinalState" xmi:id="final_done" name="Done"/>
                    <subvertex xmi:type="uml:TerminatePseudoState" xmi:id="unknown_1" name="Mystery"/>
                  </region>
                  <region xmi:type="uml:Region" xmi:id="region_parse_unused" name="">
                    <subvertex xmi:type="uml:State" xmi:id="unused_state" name="Unused"/>
                  </region>
                </ownedBehavior>

                <ownedAttribute xmi:type="uml:Port" xmi:id="port_ignore" name="ignoredPort"/>

                <ownedAttribute xmi:type="uml:Property" xmi:id="var_ref_int" name="ref_int" type="primitive_int">
                  <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_ref_int_default" value="1"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_ref_float" name="ref_float" type="primitive_real">
                  <defaultValue xmi:type="uml:LiteralReal" xmi:id="var_ref_float_default" value="2.5"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_ref_other" name="ref_other" type="primitive_mode">
                  <defaultValue xmi:type="uml:LiteralString" xmi:id="var_ref_other_default" value="MODE_A"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_href_float" name="href_float">
                  <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Double"/>
                  <defaultValue xmi:type="uml:LiteralUnlimitedNatural" xmi:id="var_href_float_default" value="3.0"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_href_other" name="href_other">
                  <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#CustomType"/>
                  <defaultValue xmi:type="uml:OpaqueExpression" xmi:id="var_href_other_default">text_default</defaultValue>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_name_float" name="name_float">
                  <type xmi:type="uml:PrimitiveType" name="Double"/>
                  <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_name_float_default" value="4"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_name_int" name="name_int">
                  <type xmi:type="uml:PrimitiveType" name="Integer"/>
                  <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_name_int_default" value="5"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_name_other" name="name_other">
                  <type xmi:type="uml:PrimitiveType" name="Token"/>
                  <defaultValue xmi:type="uml:LiteralString" xmi:id="var_name_other_default" value="TOKEN"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_no_default" name="no_default" type="primitive_int"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_untyped" name="untyped">
                  <defaultValue xmi:type="uml:LiteralString" xmi:id="var_untyped_default" value="9"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="var_empty_type" name="empty_type">
                  <type xmi:type="uml:PrimitiveType"/>
                  <defaultValue xmi:type="uml:LiteralString" xmi:id="var_empty_type_default" value="10"/>
                </ownedAttribute>
              </packagedElement>

              <packagedElement xmi:type="uml:Class" xmi:id="class_select" name="Selected Machine" classifierBehavior="machine_select">
                <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_select" name="Selected Machine">
                  <region xmi:type="uml:Region" xmi:id="region_select" name="">
                    <transition xmi:type="uml:Transition" xmi:id="tx_select_init" source="select_init" target="select_state"/>
                    <subvertex xmi:type="uml:Pseudostate" xmi:id="select_init"/>
                    <subvertex xmi:type="uml:State" xmi:id="select_state" name="Ready"/>
                  </region>
                </ownedBehavior>
              </packagedElement>
            </xmi:XMI>
            """,
        )

        machines = load_sysdesim_xml(str(xml_file))
        assert [machine.machine_id for machine in machines] == ["machine_parse", "machine_select"]

        parse_machine = load_sysdesim_machine(str(xml_file), machine_id="machine_parse")
        assert parse_machine.name == "Parse Variants"
        assert len(parse_machine.diagnostics) == 1
        assert parse_machine.diagnostics[0].level == "warning"
        assert parse_machine.diagnostics[0].code == "multiple_root_regions"
        assert parse_machine.diagnostics[0].source_id == "machine_parse"
        assert parse_machine.root_region.region_id == "region_parse_root"
        assert [vertex.vertex_type for vertex in parse_machine.root_region.vertices] == [
            "pseudostate",
            "state",
            "state",
            "final",
            "terminatepseudostate",
        ]
        assert parse_machine.get_vertex("state_alpha").state_invariant is None
        assert parse_machine.get_vertex("state_beta").state_invariant == "temperature > 10"
        assert parse_machine.get_transition("tx_alpha_beta").guard_expr_raw == "count > 0"
        assert parse_machine.get_variable("var_ref_int").type_name == "int"
        assert parse_machine.get_variable("var_ref_int").default_value == "1"
        assert parse_machine.get_variable("var_ref_float").type_name == "float"
        assert parse_machine.get_variable("var_ref_float").default_value == "2.5"
        assert parse_machine.get_variable("var_ref_other").type_name == "mode"
        assert parse_machine.get_variable("var_ref_other").default_value == "MODE_A"
        assert parse_machine.get_variable("var_href_float").type_name == "float"
        assert parse_machine.get_variable("var_href_float").default_value == "3.0"
        assert parse_machine.get_variable("var_href_other").type_name == "customtype"
        assert parse_machine.get_variable("var_href_other").default_value == "text_default"
        assert parse_machine.get_variable("var_name_float").type_name == "float"
        assert parse_machine.get_variable("var_name_float").default_value == "4"
        assert parse_machine.get_variable("var_name_int").type_name == "int"
        assert parse_machine.get_variable("var_name_int").default_value == "5"
        assert parse_machine.get_variable("var_name_other").type_name == "token"
        assert parse_machine.get_variable("var_name_other").default_value == "TOKEN"
        assert parse_machine.get_variable("var_no_default").type_name == "int"
        assert parse_machine.get_variable("var_no_default").default_value is None
        assert parse_machine.get_variable("var_untyped").type_name is None
        assert parse_machine.get_variable("var_untyped").default_value == "9"
        assert parse_machine.get_variable("var_empty_type").type_name is None
        assert parse_machine.get_variable("var_empty_type").default_value == "10"

        assert load_sysdesim_machine(str(xml_file), machine_name="Selected Machine").machine_id == "machine_select"
        with pytest.raises(KeyError, match="machine id"):
            load_sysdesim_machine(str(xml_file), machine_id="missing_machine")
        with pytest.raises(KeyError, match="machine name"):
            load_sysdesim_machine(str(xml_file), machine_name="Missing Machine")

        empty_file = _write_xml(
            tmp_path,
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <packagedElement xmi:type="uml:Class" xmi:id="class_empty" name="Empty Holder" classifierBehavior="machine_empty">
                <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_empty" name="Empty Holder"/>
              </packagedElement>
            </xmi:XMI>
            """,
        )
        with pytest.raises(ValueError, match="No uml:StateMachine found"):
            load_sysdesim_machine(str(empty_file))

    def test_phase0_load_supports_root_state_machine_without_owner(self, tmp_path: Path):
        """A state machine can be loaded directly from the XML root without owned attributes."""
        xml_path = tmp_path / "root_machine.sysdesim.xml"
        xml_path.write_text(
            dedent(
                """
                <?xml version="1.0" encoding="UTF-8"?>
                <uml:StateMachine xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                                  xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML"
                                  xmi:type="uml:StateMachine"
                                  xmi:id="machine_root"
                                  name="Root Machine">
                  <region xmi:type="uml:Region" xmi:id="region_root" name="">
                    <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_ready"/>
                    <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                    <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                  </region>
                </uml:StateMachine>
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        machine = load_sysdesim_machine(str(xml_path))
        assert machine.machine_id == "machine_root"
        assert machine.name == "Root Machine"
        assert machine.variables == []

    def test_phase1_normalize_covers_collisions_fallbacks_time_and_guards(self):
        """Normalization should cover public collision, fallback, and parsing behavior."""
        machine = IrMachine(
            machine_id="!!!",
            name="",
            root_region=IrRegion(
                region_id="region_root",
                owner_state_id=None,
                vertices=[
                    IrVertex(vertex_id="init_1", vertex_type="pseudostate", raw_name="", parent_region_id="region_root"),
                    IrVertex(vertex_id="state_same_1", vertex_type="state", raw_name="Same Name", parent_region_id="region_root"),
                    IrVertex(vertex_id="state_same_2", vertex_type="state", raw_name="Same Name", parent_region_id="region_root"),
                    IrVertex(
                        vertex_id="state_empty",
                        vertex_type="state",
                        raw_name="",
                        parent_region_id="region_root",
                        entry_action=IrActionRef(action_id="!!!", raw_name=""),
                    ),
                ],
                transitions=[
                    IrTransition(
                        transition_id="tx_init",
                        source_id="init_1",
                        target_id="state_same_1",
                        trigger_kind="none",
                        trigger_ref_id=None,
                        guard_expr_raw=None,
                    ),
                    IrTransition(
                        transition_id="tx_guard",
                        source_id="state_same_1",
                        target_id="state_empty",
                        trigger_kind="none",
                        trigger_ref_id=None,
                        guard_expr_raw="counter >= 10",
                    ),
                ],
            ),
            signals=[
                IrSignal(signal_id="signal_same_1", raw_name="same event"),
                IrSignal(signal_id="signal_same_2", raw_name="same event"),
                IrSignal(signal_id="!!!", raw_name=""),
            ],
            signal_events=[
                IrSignalEvent(event_id="event_same_1", signal_id="signal_same_1"),
                IrSignalEvent(event_id="event_same_2", signal_id="signal_same_2"),
                IrSignalEvent(event_id="event_empty", signal_id="!!!"),
            ],
            time_events=[
                IrTimeEvent(time_event_id="time_valid", raw_literal="250 ms", is_relative=True),
                IrTimeEvent(time_event_id="time_empty", raw_literal="", is_relative=False),
            ],
            variables=[
                IrVariable(
                    variable_id="synthetic_var",
                    raw_name="Temp Value",
                    type_name="int",
                    default_value="1",
                    is_synthetic=True,
                ),
            ],
        )

        normalized = normalize_machine(machine)

        assert normalized is machine
        assert machine.safe_name == "__sysdesim_state_sdesim"
        assert machine.display_name == ""
        assert machine.get_vertex("state_same_1").safe_name == "SameName"
        assert machine.get_vertex("state_same_2").safe_name == "SameName_esame2"
        assert machine.get_vertex("state_empty").safe_name == "__sysdesim_state_eempty"
        assert machine.get_vertex("state_empty").entry_action.safe_name == "__sysdesim_action_sdesim"
        assert machine.get_signal("signal_same_1").safe_name == "SAME_EVENT"
        assert machine.get_signal("signal_same_2").safe_name == "SAME_EVENT_lsame2"
        assert machine.get_signal("!!!").safe_name == "__sysdesim_evt_SDESIM"
        assert machine.get_signal_event("event_same_1").safe_name == "SAME_EVENT"
        assert machine.get_signal_event("event_same_2").safe_name == "SAME_EVENT_lsame2"
        assert machine.get_signal_event("event_empty").safe_name == "__sysdesim_evt_SDESIM"
        assert machine.get_time_event("time_valid").normalized_delay == 250.0
        assert machine.get_time_event("time_valid").normalized_unit == "ms"
        assert machine.get_time_event("time_empty").normalized_delay is None
        assert machine.get_time_event("time_empty").normalized_unit is None
        assert machine.get_transition("tx_guard").guard_expr_raw == "counter >= 10"
        assert machine.get_transition("tx_guard").guard_expr_ir is not None
        assert machine.get_variable("synthetic_var").safe_name == "__sysdesim_var_temp_value_ticvar"
        assert machine.get_variable("synthetic_var").display_name == "Temp Value"
        assert make_internal_name("flag", [], "!!!") == "__sysdesim_flag_sdesim"

        invalid_machine = IrMachine(
            machine_id="invalid_type_machine",
            name="Invalid Type",
            root_region=IrRegion(region_id="invalid_region", owner_state_id=None),
            variables=[
                IrVariable(
                    variable_id="invalid_var",
                    raw_name="counter",
                    type_name="bool",
                    default_value="0",
                    is_synthetic=False,
                )
            ],
        )
        with pytest.raises(ValueError, match="Unsupported explicit variable type"):
            normalize_machine(invalid_machine)

    def test_phase2_build_ast_supports_float_variables_and_skips_incomplete_ones(self, tmp_path: Path):
        """Phase2 should emit float definitions and skip variables that are incomplete."""
        xml_file = _write_xml(
            tmp_path,
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Float Machine" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Float Machine">
                    <region xmi:type="uml:Region" xmi:id="region_1" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_ready"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_guard" source="state_ready" target="state_hot">
                        <ownedRule xmi:type="uml:Constraint" xmi:id="guard_rule">
                          <specification xmi:type="uml:OpaqueExpression" xmi:id="guard_expr">
                            <body> temperature &gt; 30.0 </body>
                          </specification>
                        </ownedRule>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_hot" name="Hot"/>
                    </region>
                  </ownedBehavior>
                  <ownedAttribute xmi:type="uml:Property" xmi:id="var_count" name="count">
                    <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                    <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_count_default" value="1"/>
                  </ownedAttribute>
                  <ownedAttribute xmi:type="uml:Property" xmi:id="var_temperature" name="temperature">
                    <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Real"/>
                    <defaultValue xmi:type="uml:LiteralReal" xmi:id="var_temperature_default" value="42.5"/>
                  </ownedAttribute>
                  <ownedAttribute xmi:type="uml:Property" xmi:id="var_missing_default" name="pending">
                    <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                  </ownedAttribute>
                  <ownedAttribute xmi:type="uml:Property" xmi:id="var_missing_type" name="unknown_type">
                    <defaultValue xmi:type="uml:LiteralString" xmi:id="var_missing_type_default" value="9"/>
                  </ownedAttribute>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
        )

        program = convert_sysdesim_xml_to_ast(str(xml_file))
        assert [definition.name for definition in program.definitions] == ["count", "temperature"]
        assert [definition.type for definition in program.definitions] == ["int", "float"]
        assert isinstance(program.definitions[0].expr, dsl_nodes.Integer)
        assert program.definitions[0].expr.raw == "1"
        assert isinstance(program.definitions[1].expr, dsl_nodes.Float)
        assert program.definitions[1].expr.raw == "42.5"
        assert _normalize_newlines(str(program)) == dedent(
            """\
            def int count = 1;
            def float temperature = 42.5;
            state FloatMachine named 'Float Machine' {
                state Ready;
                state Hot;
                [*] -> Ready;
                Ready -> Hot : if [temperature > 30.0];
            }"""
        )
        assert _assert_program_loads_to_state_machine(program).root_state.name == "FloatMachine"
        assert _assert_dsl_code_loads_to_state_machine(str(program)).root_state.name == "FloatMachine"

        unsupported_type_machine = IrMachine(
            machine_id="unsupported_type_machine",
            name="Unsupported Type",
            root_region=IrRegion(region_id="unsupported_region", owner_state_id=None),
            variables=[
                IrVariable(
                    variable_id="bad_var",
                    raw_name="bad_var",
                    safe_name="bad_var",
                    display_name="bad_var",
                    type_name="token",
                    default_value="1",
                    is_synthetic=False,
                )
            ],
            safe_name="UnsupportedType",
            display_name="Unsupported Type",
        )
        with pytest.raises(ValueError, match="Unsupported variable type"):
            build_machine_ast(unsupported_type_machine)

    def test_phase2_output_loads_into_public_state_machine_model(self, tmp_path: Path):
        """Phase2 output should be loadable into the public StateMachine model API."""
        xml_file = _write_xml(
            tmp_path,
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Loader Check" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Loader Check">
                    <region xmi:type="uml:Region" xmi:id="region_1" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_ready"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
        )
        machine = normalize_machine(load_sysdesim_machine(str(xml_file)))

        program = build_machine_ast(machine)
        model = _assert_program_loads_to_state_machine(program)

        assert program.root_state.name == "LoaderCheck"
        assert isinstance(model, StateMachine)
        assert model.root_state.name == "LoaderCheck"
        assert _assert_dsl_code_loads_to_state_machine(str(program)).root_state.name == "LoaderCheck"

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
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Parallel Holder" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Parallel Holder">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_parent"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                        <region xmi:type="uml:Region" xmi:id="region_a" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_a" source="init_a" target="state_a"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_a"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_a" name="A"/>
                        </region>
                        <region xmi:type="uml:Region" xmi:id="region_b" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_b" source="init_b" target="state_b"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_b"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_b" name="B"/>
                        </region>
                      </subvertex>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "multi-region composite state",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Pseudo Holder" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Pseudo Holder">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_parent"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                        <region xmi:type="uml:Region" xmi:id="region_child" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_child_init" source="init_child" target="state_child"/>
                          <transition xmi:type="uml:Transition" xmi:id="tx_into_named" source="state_child" target="named_pseudo"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_child"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="named_pseudo" name="Checkpoint"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_child" name="Child"/>
                        </region>
                      </subvertex>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "init-pseudostate lowering",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Cross Region" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Cross Region">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_outer"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_cross" source="state_outer" target="state_inner"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_outer" name="Outer"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_parent" name="Parent">
                        <region xmi:type="uml:Region" xmi:id="region_child" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_child_init" source="init_child" target="state_inner"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_child"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_inner" name="Inner"/>
                        </region>
                      </subvertex>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "cross-level/cross-region transitions",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Unknown Trigger" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Unknown Trigger">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_unknown" source="state_idle" target="state_fire">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_unknown" event="missing_event"/>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_fire" name="Fire"/>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "signal/none triggers",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Signal Guard" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Signal Guard">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_guarded_signal" source="state_idle" target="state_fire">
                        <trigger xmi:type="uml:Trigger" xmi:id="trigger_signal" event="signal_event_1"/>
                        <ownedRule xmi:type="uml:Constraint" xmi:id="signal_guard_rule">
                          <specification xmi:type="uml:OpaqueExpression" xmi:id="signal_guard_expr">
                            <body> count &gt; 0 </body>
                          </specification>
                        </ownedRule>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_fire" name="Fire"/>
                    </region>
                  </ownedBehavior>
                </packagedElement>
                <packagedElement xmi:type="uml:Signal" xmi:id="signal_1" name="Go"/>
                <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_event_1" name="" signal="signal_1"/>
              </uml:Model>
            </xmi:XMI>
            """,
            "both signal and guard",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Effects" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Effects">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_effect" source="state_idle" target="state_fire">
                        <effect xmi:type="uml:Activity" xmi:id="effect_1" name="DoSideEffect"/>
                      </transition>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_fire" name="Fire"/>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "transition effects",
        ),
        (
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <xmi:XMI xmi:version="20131001"
                     xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                     xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
              <uml:Model xmi:id="model_1" name="model">
                <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Final Target" classifierBehavior="machine_1">
                  <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Final Target">
                    <region xmi:type="uml:Region" xmi:id="region_root" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_1" target="state_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_finish" source="state_idle" target="final_1"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_1"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                      <subvertex xmi:type="uml:FinalState" xmi:id="final_1" name="Done"/>
                    </region>
                  </ownedBehavior>
                </packagedElement>
              </uml:Model>
            </xmi:XMI>
            """,
            "state-to-state transitions",
        ),
        ],
    )
    def test_phase2_rejects_unsupported_public_scenarios(
        self, tmp_path: Path, xml_content: str, expected_message: str
    ):
        """Unsupported phase2 structures should fail through the public build API."""
        xml_file = _write_xml(tmp_path, xml_content)
        machine = load_sysdesim_machine(str(xml_file))
        normalize_machine(machine)

        with pytest.raises(NotImplementedError, match=expected_message):
            build_machine_ast(machine)

    def test_ir_public_helpers_cover_root_and_variable_lookup_paths(self):
        """Public IR helpers should cover the remaining observable traversal paths."""
        machine = IrMachine(
            machine_id="machine_public",
            name="Public Machine",
            root_region=IrRegion(
                region_id="region_public",
                owner_state_id=None,
                vertices=[IrVertex(vertex_id="root_state", vertex_type="state", raw_name="Root", parent_region_id=None)],
                transitions=[],
            ),
            variables=[
                IrVariable(
                    variable_id="counter_var",
                    raw_name="counter",
                    type_name="int",
                    default_value="0",
                    is_synthetic=False,
                )
            ],
        )

        assert machine.get_variable("counter_var").raw_name == "counter"
        assert machine.state_id_path("root_state") == ("root_state",)
