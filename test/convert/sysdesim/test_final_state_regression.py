"""FS-5 regression tests for SysDeSim UML FinalState support."""

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from pyfcstm.convert.sysdesim import (
    build_sysdesim_phase10_report,
    build_sysdesim_timeline_import_report,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_asts,
    convert_sysdesim_xml_to_dsl,
    convert_sysdesim_xml_to_dsls,
    validate_program_roundtrip,
)
from pyfcstm.convert.sysdesim.render import (
    build_overlay_from_diagnostics,
    render_sysdesim_timeline_svg,
)
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.entry import pyfcstmcli

pytestmark = pytest.mark.unittest

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "testfile/sysdesim"
_SAME_LEVEL_FINAL = _FIXTURE_ROOT / "final_state_same_level_model2.xml"
_CROSS_LEVEL_FINAL = _FIXTURE_ROOT / "final_state_cross_level_model0608.xml"
_REAL_CROSS_FINAL_ID = "_yirz0GMdEfG32u33dqGYFg"
_REAL_CROSS_TRANSITION_ID = "_y7sJsGMdEfG32u33dqGYFg"
_TERMINATION_KEYS = {
    "machine_alias",
    "source_path",
    "target_id",
    "target_path",
    "target_vertex_type",
    "transition_ids",
    "reached",
    "ended_step_ids",
}


def _normalize_newlines(text: str) -> str:
    """Normalize text line endings for cross-platform DSL assertions."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a compact SysDeSim XML fixture under ``tmp_path``."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def _machine_state_cells(overlay):
    """Return all rendered machine-state cell texts from one overlay payload."""
    machine_indexes = [
        index
        for index, column in enumerate(overlay["state_columns"])
        if column["kind"] == "machine"
    ]
    assert machine_indexes
    return [
        row["cells"][index]
        for row in overlay["step_states"]
        for index in machine_indexes
    ]


def test_same_level_final_state_fixture_stays_plain_exit_transition():
    """The real model2 fixture keeps the FS-1 same-level FinalState contract."""
    program = convert_sysdesim_xml_to_ast(str(_SAME_LEVEL_FINAL))
    dsl_code = _normalize_newlines(convert_sysdesim_xml_to_dsl(str(_SAME_LEVEL_FINAL)))
    validate_program_roundtrip(program)

    exit_transitions = [
        transition
        for transition in program.root_state.transitions
        if transition.from_state == "SS" and transition.to_state is dsl_nodes.EXIT_STATE
    ]

    assert len(exit_transitions) == 1
    assert "SS -> [*];" in dsl_code
    assert "state __sysdesim_final_" not in dsl_code
    assert "__sysdesim_flag_route_" not in dsl_code
    assert "_rJto4GCxEfGqsb6wf6ZObA" not in dsl_code


def test_cross_level_final_state_fixture_keeps_route_flag_exit_chain():
    """The real model0608 fixture keeps the FS-2 route-flag exit-chain contract."""
    programs = convert_sysdesim_xml_to_asts(str(_CROSS_LEVEL_FINAL))
    outputs = {
        name: _normalize_newlines(text)
        for name, text in convert_sysdesim_xml_to_dsls(str(_CROSS_LEVEL_FINAL)).items()
    }

    for program in programs.values():
        validate_program_roundtrip(program)
    for text in outputs.values():
        assert "state __sysdesim_final_" not in text
        assert _REAL_CROSS_FINAL_ID not in text

    route_outputs = {
        name: text for name, text in outputs.items() if "__sysdesim_flag_route_" in text
    }
    assert set(route_outputs) == {"StateMachine__Control_region1"}
    route_text = route_outputs["StateMachine__Control_region1"]
    route_flag = "__sysdesim_flag_route_control_e__tx_dqgyfg"

    assert route_flag in route_text
    assert "EState -> [*] effect {" in route_text
    assert f"{route_flag} = 1;" in route_text
    assert f"Control -> [*] : if [{route_flag} > 0] effect {{" in route_text
    assert f"{route_flag} = 0;" in route_text


def test_final_state_trace_report_overlay_and_svg_share_one_public_contract():
    """The checked-in cross-level fixture exercises the FS-3/FS-4 downstream chain."""
    phase10 = build_sysdesim_phase10_report(str(_CROSS_LEVEL_FINAL))
    report = build_sysdesim_timeline_import_report(str(_CROSS_LEVEL_FINAL))
    overlay = build_overlay_from_diagnostics(
        phase10_report=phase10, diagnostics=[], include_state_cells=True
    )
    svg = render_sysdesim_timeline_svg(phase10_report=phase10, overlay=overlay)

    assert any(
        step.post_state_path == "[*]" or step.stabilized_state_path == "[*]"
        for trace in phase10.traces
        for step in trace.steps
    )

    termination = report["phase10"]["termination"]
    assert len(termination) == 1
    row = termination[0]
    assert set(row) == _TERMINATION_KEYS
    assert row["machine_alias"] == "StateMachine__Control_region1"
    assert row["source_path"] == ["Control", "E"]
    assert row["target_id"] == _REAL_CROSS_FINAL_ID
    assert row["target_path"] == []
    assert row["target_vertex_type"] == "final"
    assert row["transition_ids"] == [_REAL_CROSS_TRANSITION_ID]
    assert row["reached"] is True
    assert row["ended_step_ids"] == ["s27", "s28", "s29"]

    machine_cells = _machine_state_cells(overlay)
    assert "已终止" in machine_cells
    assert "[*]" not in machine_cells
    assert "已终止" in svg
    assert _REAL_CROSS_FINAL_ID in svg
    assert _REAL_CROSS_TRANSITION_ID in svg
    assert "__sysdesim_final_" not in svg
    assert "__sysdesim_final_" not in repr(overlay)
    assert "__sysdesim_final_" not in repr(report)


def test_validate_cli_render_report_keeps_final_state_contract(tmp_path: Path):
    """The CLI smoke path uses ``--report-file`` and preserves termination provenance."""
    out_svg = tmp_path / "timeline.svg"
    report_file = tmp_path / "timeline.json"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "--no-static-check",
            "-i",
            str(_CROSS_LEVEL_FINAL),
            "--render-diagram",
            str(out_svg),
            "--render-format",
            "svg",
            "--report-file",
            str(report_file),
        ],
        color=False,
    )

    assert result.exit_code == 0, result.output
    assert "Termination" in result.output
    assert "已终止" in result.output
    assert "StateMachine__Control_region1" in result.output
    assert _REAL_CROSS_FINAL_ID in result.output
    assert _REAL_CROSS_TRANSITION_ID in result.output
    assert "__sysdesim_final_" not in result.output

    report_text = report_file.read_text(encoding="utf-8")
    svg_text = out_svg.read_text(encoding="utf-8")
    assert "phase10" in report_text
    assert "termination" in report_text
    assert "已终止" in svg_text
    assert _REAL_CROSS_FINAL_ID in svg_text
    assert "__sysdesim_final_" not in report_text
    assert "__sysdesim_final_" not in svg_text


def test_final_state_source_remains_fail_loud(tmp_path: Path):
    """Unsupported FinalState source transitions stay explicit non-goals."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Final Source" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Final Source">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_finish" source="state_idle" target="final_done"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_bad" source="final_done" target="state_idle"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:FinalState" xmi:id="final_done" name=""/>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    with pytest.raises(NotImplementedError, match="FinalState source"):
        convert_sysdesim_xml_to_ast(str(xml_file))


def test_unrelated_region_cross_level_final_state_remains_fail_loud(tmp_path: Path):
    """Unrelated-region FinalState jumps are still outside the supported subset."""
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
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_left"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_left" name="Left">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_source"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_unrelated" source="state_source" target="final_right"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_source" name="Source"/>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_right" name="Right">
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_sink"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_sink" name="Sink"/>
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
        NotImplementedError, match="cross-level FinalState target outside source subtree"
    ):
        convert_sysdesim_xml_to_ast(str(xml_file))
