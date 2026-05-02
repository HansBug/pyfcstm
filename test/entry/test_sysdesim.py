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
    # Header / cell labels appear in the table (alignment-agnostic checks).
    assert " t " in plain_output
    assert "Main" in plain_output
    assert " R1 " in plain_output
    assert " co " in plain_output
    assert "initial" in plain_output
    assert " Idle " in plain_output
    assert "start" in plain_output
    assert "Wrote SysDeSim timeline validation report" in plain_output


@pytest.mark.unittest
def test_sysdesim_cli_validate_unsat_query_does_not_print_witness_table(
    tmp_path: Path,
):
    """
    The nested validate command should keep SMT-side UNSAT output concise. The
    test fixture is a model whose query target is statically unreachable, so we
    pass ``--no-static-check`` to force-run the SMT path that this test is
    actually exercising.
    """
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
            "--no-static-check",
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
    """The nested validate command should print a summary without exporting JSON by default."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    default_report = tmp_path / "sysdesim_timeline_report.json"

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
    plain_output = _strip_ansi(result.output)
    assert "SysDeSim State Query Complete" in plain_output
    assert "Mode: import report + state query" in plain_output
    assert (
        "State Query: TimelineCoexist:TimelineCoexist.Idle <-> "
        "TimelineCoexist__Control_region1:TimelineCoexist.Idle"
    ) in plain_output
    assert "first coexistence: t00 = 0" in plain_output
    assert "witness timeline:" in plain_output
    assert "Wrote SysDeSim timeline" not in plain_output
    assert "Report:" not in plain_output
    assert not default_report.exists()


# =============================================================================
# Static-check CLI integration tests (Issue #88)
# =============================================================================


@pytest.mark.unittest
def test_sysdesim_static_check_subcommand_passes_on_clean_xml(tmp_path: Path):
    """``pyfcstm sysdesim static-check`` exits 0 on a model with no static issues."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    # Query F (region1 initial) and J (region2 initial) — both are always reached.
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "static-check",
            "-i",
            str(xml_file),
            "--left-machine-alias",
            "TimelineCoexist__Control_region1",
            "--left-state",
            "F",
            "--right-machine-alias",
            "TimelineCoexist__Control_region2",
            "--right-state",
            "J",
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    plain = _strip_ansi(result.output)
    assert "Static Pre-check" in plain
    # Either "OK (no static issues found)" or warning-only is acceptable here;
    # the canonical fixture only emits informational warnings.
    assert ("OK" in plain) or ("warning" in plain.lower())


@pytest.mark.unittest
def test_sysdesim_static_check_subcommand_blocks_on_unreachable_state(tmp_path: Path):
    """A query for an unreachable state surfaces a structured error and exits 1."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    report_file = tmp_path / "static_check_report.json"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "static-check",
            "-i",
            str(xml_file),
            "--left-machine-alias",
            "TimelineCoexist__Control_region1",
            "--left-state",
            "M",
            "--right-machine-alias",
            "TimelineCoexist__Control_region2",
            "--right-state",
            "X",
            "--report-file",
            str(report_file),
        ],
        color=False,
    )
    assert result.exit_code != 0
    plain = _strip_ansi(result.output)
    assert "[ERROR]" in plain
    assert "target_state_never_entered" in plain
    payload = json.loads(report_file.read_text(encoding="utf-8"))
    codes = {entry["code"] for entry in payload["static_check"]["diagnostics"]}
    assert "target_state_never_entered" in codes
    assert payload["static_check"]["blocking_errors"] >= 1


@pytest.mark.unittest
def test_sysdesim_static_check_subcommand_levenshtein_suggestion(tmp_path: Path):
    """Misspelled state refs surface ``query_state_name_unknown`` with closest matches."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "static-check",
            "-i",
            str(xml_file),
            "--left-machine-alias",
            "TimelineCoexist__Control_region2",
            "--left-state",
            "X_TYPO",
        ],
        color=False,
    )
    assert result.exit_code != 0
    plain = _strip_ansi(result.output)
    assert "query_state_name_unknown" in plain
    # The suggestion list should mention X (the closest match) somewhere.
    assert "Did you mean" in plain or "closest_matches" in plain


@pytest.mark.unittest
def test_sysdesim_validate_blocks_when_static_check_fails(tmp_path: Path):
    """``validate`` short-circuits at the static pre-check when a target is unreachable."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--left-machine-alias",
            "TimelineCoexist__Control_region1",
            "--left-state",
            "M",
            "--right-machine-alias",
            "TimelineCoexist__Control_region2",
            "--right-state",
            "X",
        ],
        color=False,
    )
    assert result.exit_code != 0
    plain = _strip_ansi(result.output)
    assert "Static Pre-check" in plain
    assert "skipping SMT-based validation" in plain
    # The downstream SMT report should NOT have run.
    assert "status: UNSAT" not in plain
    assert "status: SAT" not in plain


@pytest.mark.unittest
def test_sysdesim_validate_no_static_check_flag_runs_smt(tmp_path: Path):
    """``--no-static-check`` bypasses the pre-check and falls through to SMT."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--left-machine-alias",
            "TimelineCoexist__Control_region1",
            "--left-state",
            "M",
            "--right-machine-alias",
            "TimelineCoexist__Control_region2",
            "--right-state",
            "X",
            "--no-static-check",
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    plain = _strip_ansi(result.output)
    assert "Static Pre-check" not in plain
    assert "SysDeSim State Query Complete" in plain


@pytest.mark.unittest
def test_sysdesim_static_check_warn_as_error_blocks(tmp_path: Path):
    """``--warn-as-error`` promotes warnings to blocking failures."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    # No Phase11 query: the only issues are signal_dropped warnings.
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "static-check",
            "-i",
            str(xml_file),
            "--warn-as-error",
        ],
        color=False,
    )
    assert result.exit_code != 0
    plain = _strip_ansi(result.output)
    assert "[WARN]" in plain
    assert "signal_dropped_in_state" in plain


@pytest.mark.unittest
def test_sysdesim_static_check_emits_ansi_color_when_color_enabled(tmp_path: Path):
    """Color terminals receive ANSI escape codes for severity prominence."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "static-check",
            "-i",
            str(xml_file),
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
    # Expect at least one ANSI escape sequence in the colored output.
    assert "\x1b[" in result.output, "expected ANSI escape codes when color=True"


def _build_static_check_clean_xml(tmp_path: Path) -> Path:
    """A tiny machine + scenario with literally zero static issues.

    Idle --Sig1--> Run; the scenario emits Sig1 once. No DurationConstraints,
    no signal-drops, no unreachable states. Used to verify the
    ``Static Pre-check OK`` clean-output branch.
    """
    return _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="CleanDemo" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="CleanDemo">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_idle"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_idle_run" source="state_idle" target="state_run">
                    <trigger xmi:type="uml:Trigger" xmi:id="trig_run" event="signal_evt_sig1"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_run" name="Run"/>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="ScenClean">
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_a" name="a"/>
                <ownedAttribute xmi:type="uml:Property" xmi:id="prop_b" name="b"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_a" name="a" represents="prop_a"/>
                <lifeline xmi:type="uml:Lifeline" xmi:id="ll_b" name="b" represents="prop_b"/>
                <fragment xmi:type="uml:StateInvariant" xmi:id="inv_a" covered="ll_a">
                  <invariant xmi:type="uml:Constraint" xmi:id="inv_a_rule">
                    <specification xmi:type="uml:OpaqueExpression" xmi:id="inv_a_expr">
                      <body>true</body>
                    </specification>
                  </invariant>
                </fragment>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig1_send" covered="ll_b" message="msg_sig1"/>
                <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="sig1_recv" covered="ll_a" message="msg_sig1"/>
                <message xmi:type="uml:Message" xmi:id="msg_sig1" sendEvent="sig1_send" receiveEvent="sig1_recv" signature="signal_sig1"/>
              </ownedBehavior>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_sig1" name="Sig1"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_sig1" signal="signal_sig1"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )


@pytest.mark.unittest
def test_sysdesim_static_check_clean_xml_emits_ok_branch(tmp_path: Path):
    """A model with zero diagnostics prints the clean ``OK`` branch."""
    xml_file = _build_static_check_clean_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        ["sysdesim", "static-check", "-i", str(xml_file)],
        color=False,
    )
    assert result.exit_code == 0, result.output
    plain = _strip_ansi(result.output)
    assert "OK (no static issues found)" in plain


@pytest.mark.unittest
def test_sysdesim_validate_writes_static_check_report_when_blocked(tmp_path: Path):
    """When validate's pre-check blocks, ``--report-file`` still receives the
    structured static-check payload so CI / LLM tooling can act on it."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    report_file = tmp_path / "blocked.json"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--left-machine-alias",
            "TimelineCoexist__Control_region1",
            "--left-state",
            "M",
            "--right-machine-alias",
            "TimelineCoexist__Control_region2",
            "--right-state",
            "X",
            "--report-file",
            str(report_file),
        ],
        color=False,
    )
    assert result.exit_code != 0
    payload = json.loads(report_file.read_text(encoding="utf-8"))
    assert "static_check" in payload
    assert payload["static_check"]["blocking_errors"] >= 1


@pytest.mark.unittest
def test_sysdesim_static_check_unknown_machine_name_yields_click_error(
    tmp_path: Path,
):
    """An unknown ``--machine-name`` exercises the static-check exception
    handler that converts ``KeyError`` into a clean ClickErrorException."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "static-check",
            "-i",
            str(xml_file),
            "--machine-name",
            "NoSuchMachine",
        ],
        color=False,
    )
    assert result.exit_code != 0
    plain = _strip_ansi(result.output)
    assert "NoSuchMachine" in plain


@pytest.mark.unittest
def test_sysdesim_validate_unknown_machine_name_in_static_check_phase(
    tmp_path: Path,
):
    """``validate``'s pre-check catches the same KeyError via the static_check
    exception handler in :func:`_run_sysdesim_validate`."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--machine-name",
            "NoSuchMachine",
        ],
        color=False,
    )
    assert result.exit_code != 0
    plain = _strip_ansi(result.output)
    assert "NoSuchMachine" in plain


@pytest.mark.unittest
def test_sysdesim_validate_no_static_check_propagates_smt_phase_error(
    tmp_path: Path,
):
    """``--no-static-check`` skips the pre-check, so the post-pre-check
    exception handler in :func:`_run_sysdesim_validate` is the layer that
    surfaces XML/lookup errors."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "validate",
            "-i",
            str(xml_file),
            "--machine-name",
            "NoSuchMachine",
            "--no-static-check",
        ],
        color=False,
    )
    assert result.exit_code != 0
    plain = _strip_ansi(result.output)
    assert "NoSuchMachine" in plain


@pytest.mark.unittest
def test_diagnostic_level_label_info_branch():
    """``_diagnostic_level_label`` returns the cyan ``[INFO]`` tag for
    non-error/warning levels (defensive code path for future detector kinds)."""
    from pyfcstm.entry.sysdesim import _diagnostic_level_label

    label = _diagnostic_level_label("info")
    # The literal "[INFO]" tag must be present, possibly wrapped with ANSI.
    assert "[INFO]" in label
    # Unknown level falls back to the same INFO bucket.
    assert "[INFO]" in _diagnostic_level_label("note")


@pytest.mark.unittest
def test_phase11_action_token_normalizes_legacy_and_new_forms():
    """``_format_phase11_action_token`` accepts both legacy ``emit(X)`` and
    the new symmetric ``X<--`` / ``-->X`` forms."""
    from pyfcstm.entry.sysdesim import _format_phase11_action_token

    # New encodings pass through unchanged.
    assert _format_phase11_action_token("Sig9<--", None) == "Sig9<--"
    assert _format_phase11_action_token("-->Sig13", None) == "-->Sig13"
    assert _format_phase11_action_token("y=2300", None) == "y=2300"
    # Legacy emit(X) gets converted to the new arrow form.
    assert _format_phase11_action_token("emit(Sig5)", None) == "Sig5<--"
    # Legacy SetInput(...) gets unwrapped.
    assert _format_phase11_action_token("SetInput(z=10)", None) == "z=10"


@pytest.mark.unittest
def test_phase11_action_token_classifier():
    """Token classification picks the right ANSI bucket per kind."""
    from pyfcstm.entry.sysdesim import _classify_action_token

    assert _classify_action_token("tau:R3 S->X") == "tau"
    assert _classify_action_token("Sig9<--") == "inbound"
    assert _classify_action_token("-->Sig13") == "outbound"
    assert _classify_action_token("y=2300") == "assignment"
    assert _classify_action_token("(unknown)") == "other"


@pytest.mark.unittest
def test_phase11_witness_uses_arrow_form_and_outbound_signals(tmp_path: Path):
    """A SAT scenario should surface ``Sig9<--`` for emits and ``-->Sig11`` for
    outbound notes; the first row is labeled ``initial`` (cyan) and the first
    coexistence row is underlined+bold when the terminal supports color."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    # Query Control / F: initial is Idle/Idle (not coexistent), subsequent
    # rows after Sig1 fire are Control/F (coexistent), giving us both an
    # ``initial`` row and a ``start`` row to assert on.
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
            "Control",
            "--right-machine-alias",
            "TimelineCoexist__Control_region1",
            "--right-state",
            "F",
        ],
        color=True,
    )
    assert result.exit_code == 0, result.output
    # Inbound emit on Sig1 surfaces in the new arrow form.
    assert "Sig1<--" in result.output
    # Outbound signal note must surface as -->SigN.
    assert "-->" in result.output
    # The very first witness row carries the ``initial`` label in cyan.
    assert "\x1b[36minitial" in result.output
    # The first coexistence row is line-level underline + bold.
    assert "\x1b[4m\x1b[1m" in result.output


@pytest.mark.unittest
def test_serialize_diagnostic_round_trips_state_path_field():
    """``_serialize_diagnostic`` includes ``state_path`` when the diagnostic
    carries one, and emits it as a JSON-friendly list."""
    from pyfcstm.convert.sysdesim.ir import IrDiagnostic
    from pyfcstm.entry.sysdesim import _serialize_diagnostic

    diag = IrDiagnostic(
        level="warning",
        code="custom_code",
        message="hi",
        state_path=("Root", "Inner"),
    )
    payload = _serialize_diagnostic(diag)
    assert payload["state_path"] == ["Root", "Inner"]
    assert payload["code"] == "custom_code"
    assert payload["level"] == "warning"


# =============================================================================
# Sequence-render CLI integration tests (Issue #87)
# =============================================================================


@pytest.mark.unittest
def test_sysdesim_sequence_render_writes_svg(tmp_path: Path):
    """``pyfcstm sysdesim sequence-render -i ... -o ...`` writes a valid SVG."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_svg = tmp_path / "seq.svg"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_svg),
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert out_svg.exists()
    text = out_svg.read_text(encoding="utf-8")
    assert text.startswith("<?xml")
    assert "</svg>" in text
    assert "Wrote sequence-diagram SVG to" in result.output


@pytest.mark.unittest
def test_sysdesim_sequence_render_supports_title_override(tmp_path: Path):
    """``--title`` overrides the diagram title written into the SVG."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_svg = tmp_path / "seq.svg"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_svg),
            "--title",
            "MyCustomTitle",
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert "MyCustomTitle" in out_svg.read_text(encoding="utf-8")


@pytest.mark.unittest
def test_sysdesim_sequence_render_unknown_machine_yields_click_error(
    tmp_path: Path,
):
    """An unknown ``--machine-name`` is translated by ``_format_sysdesim_cli_error``."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_svg = tmp_path / "seq.svg"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_svg),
            "--machine-name",
            "NoSuchMachine",
        ],
        color=False,
    )
    assert result.exit_code != 0
    assert "NoSuchMachine" in _strip_ansi(result.output)
    assert not out_svg.exists()


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.mark.unittest
def test_sysdesim_sequence_render_writes_png_via_extension(tmp_path: Path):
    """``-o foo.png`` infers the PNG format from the extension."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_png = tmp_path / "seq.png"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_png),
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert out_png.exists()
    assert out_png.read_bytes()[:8] == _PNG_MAGIC
    assert "Wrote sequence-diagram PNG to" in result.output


@pytest.mark.unittest
def test_sysdesim_sequence_render_format_flag_overrides_extension(tmp_path: Path):
    """``--format png`` forces PNG even when the output extension is unrelated."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out = tmp_path / "seq.bin"
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out),
            "--format",
            "png",
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert out.read_bytes()[:8] == _PNG_MAGIC


@pytest.mark.unittest
def test_sysdesim_sequence_render_requires_output_or_preview(tmp_path: Path):
    """Calling with neither ``--output`` nor ``--preview`` fails cleanly."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
        ],
        color=False,
    )
    assert result.exit_code != 0
    assert "Provide --output / -o, --preview" in _strip_ansi(result.output)


@pytest.mark.unittest
def test_sysdesim_sequence_render_preview_only_uses_tempfile(
    monkeypatch, tmp_path: Path
):
    """``--preview`` without ``-o`` writes a temp SVG and opens the browser."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    captured = {}

    def fake_open(uri):
        captured["uri"] = uri
        return True

    monkeypatch.setattr("pyfcstm.entry.sysdesim.webbrowser.open", fake_open)
    result = CliRunner().invoke(
        pyfcstmcli,
        ["sysdesim", "sequence-render", "-i", str(xml_file), "--preview"],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert "uri" in captured
    assert captured["uri"].startswith("file://")
    assert captured["uri"].endswith(".svg")
    # The temporary file must actually exist on disk.
    temp_path = Path(captured["uri"][len("file://") :])
    assert temp_path.exists()
    assert temp_path.read_bytes().startswith(b"<?xml")
    assert "opened" in result.output


@pytest.mark.unittest
def test_sysdesim_sequence_render_preview_with_explicit_output(
    monkeypatch, tmp_path: Path
):
    """``--preview -o foo.svg`` writes the explicit path AND opens the browser."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_svg = tmp_path / "explicit.svg"
    captured = {}

    def fake_open(uri):
        captured["uri"] = uri
        return True

    monkeypatch.setattr("pyfcstm.entry.sysdesim.webbrowser.open", fake_open)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_svg),
            "--preview",
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert out_svg.exists()
    # Browser receives the user-specified path, not a tempfile.
    assert captured["uri"] == out_svg.as_uri()


@pytest.mark.unittest
def test_sysdesim_sequence_render_preview_browser_unavailable(
    monkeypatch, tmp_path: Path
):
    """When ``webbrowser.open`` returns ``False`` the CLI still reports cleanly."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_svg = tmp_path / "seq.svg"
    monkeypatch.setattr(
        "pyfcstm.entry.sysdesim.webbrowser.open", lambda uri: False
    )
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_svg),
            "--preview",
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert "no browser available" in _strip_ansi(result.output)


@pytest.mark.unittest
def test_sysdesim_sequence_render_surfaces_render_error(monkeypatch, tmp_path: Path):
    """A ``SysdesimRenderError`` from the JS bundle becomes a ``ClickErrorException``."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_svg = tmp_path / "seq.svg"

    from pyfcstm.convert.sysdesim.render import SysdesimRenderError

    def boom(*_args, **_kwargs):
        raise SysdesimRenderError("simulated bundle failure")

    monkeypatch.setattr(
        "pyfcstm.entry.sysdesim.render_sysdesim_timeline_svg", boom
    )
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_svg),
        ],
        color=False,
    )
    assert result.exit_code != 0
    assert "simulated bundle failure" in _strip_ansi(result.output)
    assert not out_svg.exists()


@pytest.mark.unittest
def test_sysdesim_sequence_render_png_with_font_file(tmp_path: Path):
    """``--font-file`` paths are forwarded to the PNG renderer."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    out_png = tmp_path / "seq.png"
    # Use the bundled DejaVu Sans (also used as the default fallback) as a
    # stand-in user font so the test stays self-contained.
    extra_font = (
        Path(__file__).resolve().parents[2]
        / "js"
        / "sysdesim_render"
        / "src"
        / "fonts"
        / "DejaVuSans.ttf"
    )
    if not extra_font.exists():
        pytest.skip("bundled DejaVu Sans not present at expected source path")
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "sysdesim",
            "sequence-render",
            "-i",
            str(xml_file),
            "-o",
            str(out_png),
            "--font-file",
            str(extra_font),
        ],
        color=False,
    )
    assert result.exit_code == 0, result.output
    assert out_png.read_bytes()[:8] == _PNG_MAGIC
