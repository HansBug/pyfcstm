"""Tests for the SysDeSim CLI conversion entry."""

import json
import re
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.entry import pyfcstmcli
from pyfcstm.model.model import StateMachine, parse_dsl_node_to_state_machine
from test.convert.sysdesim.test_phase9_11 import _build_parallel_timeline_xml

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


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


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences for stable CLI assertions."""
    return _ANSI_RE.sub("", text)


def _write_sysdesim_convert_json_report(
    xml_file: Path, output_dir: Path, report_file: Path
) -> str:
    """Run the conversion CLI with one explicit JSON report export."""
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "-i",
            str(xml_file),
            "-o",
            str(output_dir),
            "--report-file",
            str(report_file),
        ],
        color=True,
    )
    assert result.exit_code == 0, result.output
    return _strip_ansi(result.output)


@pytest.mark.unittest
def test_sysdesim_cli_writes_outputs_and_report(tmp_path: Path):
    """The phase6 CLI should write all FCSTM outputs plus the JSON report."""
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
    output_dir = tmp_path / "out"
    report_file = tmp_path / "conversion_report.json"

    plain_output = _write_sysdesim_convert_json_report(
        xml_file, output_dir, report_file
    )
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

    for output_name, expected_dsl in expected_outputs.items():
        dsl_file = output_dir / f"{output_name}.fcstm"
        dsl_code = _normalize_newlines(dsl_file.read_text(encoding="utf-8"))
        assert dsl_code == expected_dsl
        _assert_dsl_code_loads_to_state_machine(dsl_code)

    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["selected_machine_name"] == "Parallel Split"
    assert report_data["output_count"] == 3
    assert [item["output_name"] for item in report_data["outputs"]] == list(
        expected_outputs.keys()
    )
    assert all(item["parser_roundtrip_ok"] for item in report_data["outputs"])
    assert all(item["model_build_ok"] for item in report_data["outputs"])
    assert all(item["guard_variables_defined"] for item in report_data["outputs"])
    assert all(item["event_paths_valid"] for item in report_data["outputs"])
    assert all(item["composite_states_have_init"] for item in report_data["outputs"])
    assert "SysDeSim Conversion Complete" in plain_output
    assert "Machine: Parallel Split [machine_1]" in plain_output
    assert f"Output Dir: {output_dir}" in plain_output
    assert f"Report: {report_file}" in plain_output
    assert "Tick: not required" in plain_output
    assert "Outputs: 3" in plain_output
    assert "| output" in plain_output
    assert "| file" in plain_output
    assert "| ln" in plain_output
    assert "| status" in plain_output
    assert "| diag" in plain_output
    assert "ParallelSplit.fcstm" in plain_output
    assert "ParallelSplit__Controller_region1.fcstm" in plain_output
    assert "ParallelSplit__Controller_region2.fcstm" in plain_output
    assert "OK" in plain_output
    assert "parallel-main" in plain_output
    assert "parallel-split" in plain_output
    assert "full details are in the JSON report" in plain_output


@pytest.mark.unittest
def test_sysdesim_cli_does_not_export_convert_report_without_option(tmp_path: Path):
    """The conversion CLI should skip JSON export unless --report-file is provided."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Simple" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Simple">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )
    output_dir = tmp_path / "out"

    result = CliRunner().invoke(
        pyfcstmcli,
        ["sysdesim", "-i", str(xml_file), "-o", str(output_dir)],
        color=True,
    )

    assert result.exit_code == 0, result.output
    plain_output = _strip_ansi(result.output)
    assert "SysDeSim Conversion Complete" in plain_output
    assert "Report:" not in plain_output
    assert "use --report-file to export full JSON diagnostics" not in plain_output
    assert not (output_dir / "sysdesim_conversion_report.json").exists()


@pytest.mark.unittest
def test_sysdesim_cli_reports_missing_tick_duration_for_timeevent(tmp_path: Path):
    """The CLI should turn missing phase3 tick configuration into a clear message."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Timer Sample" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Timer Sample">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_wait"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_timeout" source="state_wait" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_timeout" event="time_evt_1"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_wait" name="Wait"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                </region>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:TimeEvent" xmi:id="time_evt_1" name="" isRelative="true">
              <when xmi:type="uml:TimeExpression" xmi:id="time_expr_1">
                <expr xmi:type="uml:LiteralReal" xmi:id="time_lit_1" value="0.1s"/>
              </when>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    result = CliRunner().invoke(
        pyfcstmcli,
        ["sysdesim", "-i", str(xml_file), "-o", str(tmp_path / "out")],
        color=True,
    )

    assert result.exit_code != 0
    assert "\x1b[" in result.output
    assert "please provide --tick-duration-ms" in _strip_ansi(result.output)


@pytest.mark.unittest
def test_sysdesim_cli_ignores_transition_effects_with_report_diagnostic(tmp_path: Path):
    """The CLI should downgrade transition effects to diagnostics while still exporting DSL."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Effect Sample" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Effect Sample">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_go" source="state_idle" target="state_run">
                    <effect xmi:type="uml:Activity" xmi:id="effect_1" name="Start Service"/>
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

    output_dir = tmp_path / "out"
    report_file = tmp_path / "conversion_report.json"
    plain_output = _write_sysdesim_convert_json_report(
        xml_file, output_dir, report_file
    )
    expected_dsl = dedent(
        """\
        state EffectSample named 'Effect Sample' {
            state Idle;
            state Run;
            [*] -> Idle;
            Idle -> Run;
        }"""
    )
    dsl_code = _normalize_newlines(
        (output_dir / "EffectSample.fcstm").read_text(encoding="utf-8")
    )
    assert dsl_code == expected_dsl
    _assert_dsl_code_loads_to_state_machine(dsl_code)

    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["output_count"] == 1
    assert (
        report_data["outputs"][0]["diagnostics"][-1]["code"]
        == "transition_effect_semantic_downgrade"
    )
    assert "tx-effect" in plain_output


@pytest.mark.unittest
def test_sysdesim_cli_validate_writes_timeline_import_report(tmp_path: Path):
    """The nested validate command should write one review-oriented timeline report."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    report_file = tmp_path / "timeline_import_report.json"

    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--report-file",
            str(report_file),
        ],
        color=True,
    )

    assert result.exit_code == 0, result.output
    plain_output = _strip_ansi(result.output)
    assert "Wrote SysDeSim timeline import report" in plain_output
    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["selected_machine_name"] == "Timeline Coexist"
    assert report_data["selected_interaction_name"] == "Scenario 1"
    assert [item["output_name"] for item in report_data["phase9"]["outputs"]] == [
        "TimelineCoexist",
        "TimelineCoexist__Control_region1",
        "TimelineCoexist__Control_region2",
    ]
    assert report_data["phase10"]["scenario"]["steps"][0]["step_id"] == "s01"
    assert (
        report_data["phase10"]["traces"][0]["state_windows"][0]["source_step_id"]
        == "initial"
    )
    assert "phase11" not in report_data
    assert "SysDeSim Timeline Import Report Complete" in plain_output
    assert "Mode: import report only" in plain_output
    assert "Machine: Timeline Coexist" in plain_output
    assert "Interaction: Scenario 1" in plain_output
    assert f"Report: {report_file}" in plain_output
    assert (
        "Model Import: graph_edges={graph} inputs={inputs} events={events} "
        "steps={steps} windows={windows} durations={durations} diagnostics={diagnostics}".format(
            graph=len(report_data["phase78"]["machine_graph"]),
            inputs=len(report_data["phase78"]["input_candidates"]),
            events=len(report_data["phase78"]["event_candidates"]),
            steps=len(report_data["phase78"]["steps"]),
            windows=len(report_data["phase78"]["time_windows"]),
            durations=len(report_data["phase78"]["duration_constraints"]),
            diagnostics=len(report_data["phase78"]["diagnostics"]),
        )
        in plain_output
    )
    assert "Outputs: 3" in plain_output
    assert "| output" in plain_output
    assert "| defines" in plain_output
    assert "| events" in plain_output
    assert "| diag" in plain_output
    assert "parallel-main" in plain_output
    assert "parallel-split" in plain_output
    assert (
        "Scenario: scenario={name} steps={steps} temporal_constraints={constraints} "
        "bindings={bindings} traces={traces} diagnostics={diagnostics}".format(
            name=report_data["phase10"]["scenario"]["name"],
            steps=len(report_data["phase10"]["scenario"]["steps"]),
            constraints=len(report_data["phase10"]["scenario"]["temporal_constraints"]),
            bindings=len(report_data["phase10"]["bindings"]),
            traces=len(report_data["phase10"]["traces"]),
            diagnostics=len(report_data["phase10"]["diagnostics"]),
        )
        in plain_output
    )
    assert "Initial States:" in plain_output
    assert "TimelineCoexist -> TimelineCoexist.Idle" in plain_output
    assert "Phase11" not in plain_output
    assert "State Query: not requested." in plain_output


@pytest.mark.unittest
def test_sysdesim_cli_validate_writes_phase11_summary_when_report_file_is_used(
    tmp_path: Path,
):
    """The nested validate command should print a readable Phase11 summary when exporting JSON."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    report_file = tmp_path / "phase11_report.json"

    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--report-file",
            str(report_file),
            "--left-machine-alias",
            "TimelineCoexist",
            "--left-state",
            "Idle",
            "--right-machine-alias",
            "TimelineCoexist__Control_region1",
            "--right-state",
            "Idle",
        ],
        color=True,
    )

    assert result.exit_code == 0, result.output
    plain_output = _strip_ansi(result.output)
    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["phase11"]["solve_result"]["status"] == "sat"
    assert "SysDeSim State Query Complete" in plain_output
    assert "Mode: import report + state query" in plain_output
    assert (
        "State Query: TimelineCoexist:TimelineCoexist.Idle <-> "
        "TimelineCoexist__Control_region1:TimelineCoexist.Idle"
    ) in plain_output
    assert "scope: both | candidates: 2 | status: SAT" in plain_output
    assert "first coexistence: t00 = 0" in plain_output
    assert "witness timeline:" in plain_output
    assert "| t" in plain_output
    assert "| Main" in plain_output
    assert "| R1" in plain_output
    assert "| co" in plain_output
    assert "| 0" in plain_output
    assert "| initial" in plain_output
    assert "| Idle" in plain_output
    assert "| start" in plain_output
    assert "Wrote SysDeSim timeline validation report" in plain_output


@pytest.mark.unittest
def test_sysdesim_cli_validate_unsat_query_does_not_print_witness_table(
    tmp_path: Path,
):
    """The nested validate command should keep UNSAT output concise."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    report_file = tmp_path / "phase11_unsat_report.json"

    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--report-file",
            str(report_file),
            "--left-machine-alias",
            "TimelineCoexist__Control_region1",
            "--left-state",
            "M",
            "--right-machine-alias",
            "TimelineCoexist__Control_region2",
            "--right-state",
            "X",
        ],
        color=True,
    )

    assert result.exit_code == 0, result.output
    plain_output = _strip_ansi(result.output)
    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["phase11"]["solve_result"]["status"] == "unsat"
    assert "status: UNSAT" in plain_output
    assert "reason:" in plain_output
    assert "Phase11" not in plain_output
    assert "witness timeline:" not in plain_output


@pytest.mark.unittest
def test_sysdesim_cli_validate_can_include_phase11_query_in_stdout(tmp_path: Path):
    """The nested validate command should optionally embed one Phase11 query bundle."""
    xml_file = _build_parallel_timeline_xml(tmp_path)

    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--left-machine-alias",
            "TimelineCoexist",
            "--left-state",
            "Idle",
            "--right-machine-alias",
            "TimelineCoexist__Control_region1",
            "--right-state",
            "Idle",
        ],
        color=False,
    )

    assert result.exit_code == 0, result.output
    report_data = json.loads(result.output)
    assert report_data["phase11"]["constraint_preview"]["candidate_count"] == 2
    assert report_data["phase11"]["solve_result"]["status"] == "sat"
    assert report_data["phase11"]["solve_result"]["observation_kind"] == "initial"
    assert (
        report_data["phase11"]["timeline_report"]["first_coexistence_symbol"] == "t00"
    )
