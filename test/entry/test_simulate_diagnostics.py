"""Public CLI diagnostics, explicit inputs, and output stream contracts."""

import json

import pytest
from click.testing import CliRunner
from prompt_toolkit.document import Document

from pyfcstm.entry.cli import cli
from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest

MODEL = """
input int sensor;
param int gain = 2;
output int reading = 0;
state Root {
    state A { during { reading = sensor * gain; } }
    state B;
    [*] -> A;
    A -> B : if [sensor > 10];
}
"""


def invoke(tmp_path, commands, *options, source=MODEL):
    path = tmp_path / "model.fcstm"
    path.write_text(source)
    return CliRunner().invoke(
        cli,
        [
            "simulate",
            "-i",
            str(path),
            "--no-color",
            *options,
            "-e",
            commands,
        ],
    )


def test_batch_jsonl_inputs_parameters_and_human_queries(tmp_path):
    result = invoke(
        tmp_path,
        "cycle --input sensor=3; cycle --input sensor=12; decisions; why Root.A::0::A->B --verbose",
        "--param",
        "gain=4",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
    )
    assert result.exit_code == 0, result.output
    reports = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(reports) == 2
    assert reports[-1]["state_after"] == ["Root", "B"]
    assert reports[-1]["roles"] == {
        "sensor": "input",
        "gain": "param",
        "reading": "output",
    }
    committed = [d for d in reports[-1]["decisions"] if d["committed"]]
    assert committed[0]["inputs"] == {"sensor": 12}
    assert committed[0]["parameters"] == {"gain": 4}
    assert committed[0]["vars"] == {"reading": 12}
    assert "Root.A::0::A->B" in result.stderr
    assert "\x1b[" not in result.stdout


def test_batch_text_summary_and_repeated_vectors(tmp_path):
    result = invoke(
        tmp_path, "cycle 3 --input sensor=3; why Root.A::0::A->B", "--diagnostics"
    )
    assert result.exit_code == 0, result.output
    assert "guard_false" in result.stdout
    assert "Cycle 3:" in result.stdout
    assert "No recorded evidence" not in result.stdout


def test_query_never_replays_and_failed_call_clears_evidence():
    machine = SimulationRuntime(
        load_state_machine_from_text("""
        state Root { state A; state B; [*] -> A; A -> B :: Go; }
    """)
    )
    processor = CommandProcessor(machine, use_color=False)
    assert "No diagnostic report" in processor.process("decisions").output
    processor.process("setting diagnostics on")
    processor.process("cycle")
    processor.process("cycle")
    count = machine.cycle_count
    assert "event_missing" in processor.process("why Root.A::0::A->B").output
    assert "event_missing" in processor.process("decisions --verbose").output
    assert machine.cycle_count == count
    completer = processor.create_completer()
    assert "Root.A::0::A->B" in [
        c.text for c in completer.get_completions(Document("why "), None)
    ]
    result = processor.process("cycle UnknownEvent")
    assert result.exit_code != 0
    assert "No diagnostic report" in processor.process("decisions").output
    processor.process("cycle")
    processor.process("clear")
    assert "No diagnostic report" in processor.process("decisions").output


@pytest.mark.parametrize(
    "commands, options",
    [
        ("cycle", ()),
        ("cycle --input sensor=1 --input sensor=2", ()),
        ("cycle --input wrong=2", ()),
        ("cycle --input sensor=1.2", ()),
        ("cycle --input", ()),
        ("cycle --input sensor=bad", ()),
        ("cycle --input sensor=2", ("--param", "gain=1.2")),
        ("cycle --input sensor=2", ("--param", "sensor=1")),
    ],
)
def test_invalid_inputs_fail_without_successful_json(tmp_path, commands, options):
    result = invoke(
        tmp_path, commands, "--diagnostics", "--diagnostics-format", "jsonl", *options
    )
    assert result.exit_code != 0
    assert result.stdout == ""


def test_jsonl_requires_batch_and_diagnostics(tmp_path):
    path = tmp_path / "model.fcstm"
    path.write_text("state Root;")
    result = CliRunner().invoke(
        cli, ["simulate", "-i", str(path), "--diagnostics-format", "jsonl"]
    )
    assert result.exit_code != 0
    assert "batch" in result.output.lower()
    result = invoke(
        tmp_path, "cycle", "--diagnostics-format", "jsonl", source="state Root;"
    )
    assert result.exit_code != 0
    assert "--diagnostics" in result.output


@pytest.mark.parametrize(
    "commands",
    [
        "cycle --input sensor=3; setting diagnostics off; cycle --input sensor=3",
        "cycle --input sensor=3; init",
        "cycle --input sensor=3; init Root.A reading=bad",
        "cycle --input sensor=3; init Root.A",
        "cycle --input sensor=3; init Root.A bad",
        "cycle --input sensor=3; init Unknown reading=0",
        "cycle --input sensor=3; unknown",
        "cycle --input sensor=3; why",
        "cycle --input sensor=3; decisions unexpected",
        "cycle --input sensor=3; decisions --verbose --verbose",
    ],
)
def test_batch_command_errors_do_not_silently_succeed(tmp_path, commands):
    result = invoke(
        tmp_path, commands, "--diagnostics", "--diagnostics-format", "jsonl"
    )
    assert result.exit_code != 0
    assert len([json.loads(line) for line in result.stdout.splitlines()]) == 1


def test_explicit_retry_hot_start_and_reset(tmp_path):
    result = invoke(
        tmp_path,
        "cycle --input sensor=3; init Root.A reading=9; decisions; "
        "cycle --input sensor=4; clear; decisions; cycle --input sensor=5",
        "--param",
        "gain=3",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
    )
    assert result.exit_code == 0, result.output
    reports = [json.loads(line) for line in result.stdout.splitlines()]
    assert [r["cycle_count"] for r in reports] == [1, 1, 1]
    assert reports[1]["decisions"][0]["vars"] == {"reading": 9}
    assert all(d["parameters"] == {"gain": 3} for r in reports for d in r["decisions"])
    assert result.stderr.count("No diagnostic report") == 2


def test_terminated_input_model_needs_no_new_sample(tmp_path):
    result = invoke(
        tmp_path,
        "cycle --input sensor=1; cycle --input sensor=2; cycle",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
        source="input int sensor; state Root { state A; [*] -> A; A -> [*]; }",
    )
    assert result.exit_code == 0, result.output
    reports = [json.loads(line) for line in result.stdout.splitlines()]
    assert [r["outcome"] for r in reports] == ["cycle", "terminated", "noop"]
    assert [r["cycle_count"] for r in reports] == [1, 2, 2]


def test_multiple_jsonl_calls_and_no_false_record_after_expression_failure(tmp_path):
    result = invoke(
        tmp_path,
        "cycle 3 --input sensor=3",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
    )
    assert result.exit_code == 0, result.output
    assert len([json.loads(line) for line in result.stdout.splitlines()]) == 3
    failed = invoke(
        tmp_path,
        "cycle; cycle",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
        source="""
        control int x = 0;
        state Root { state A; state B { enter { x = 1 / 0; } } [*] -> A; A -> B; }
    """,
    )
    assert failed.exit_code != 0
    assert len([json.loads(line) for line in failed.stdout.splitlines()]) == 1
    assert "Cycle execution failed" in failed.stderr


@pytest.mark.parametrize("value", ["sensor", "=1", "sensor=nan"])
def test_invalid_vector_syntax_and_nonfinite_values(tmp_path, value):
    result = invoke(
        tmp_path,
        "cycle --input " + value,
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
    )
    assert result.exit_code != 0
    assert result.stdout == ""


def test_queries_after_disabled_collection_and_init_failures():
    processor = CommandProcessor(
        SimulationRuntime(
            load_state_machine_from_text(
                "state Root { state A; state B; [*] -> A; A -> B :: Go; }"
            )
        ),
        use_color=False,
    )
    processor.process("setting diagnostics on")
    processor.process("cycle")
    processor.process("setting diagnostics off")
    processor.process("cycle")
    assert "No diagnostic report" in processor.process("decisions").output
    processor.process("setting diagnostics on")
    processor.process("cycle")
    processor.process("init Missing")
    assert "No diagnostic report" in processor.process("decisions").output


def test_diagnostic_completion_with_and_without_evidence():
    from pyfcstm.entry.simulate.completer import SimulationCompleter

    machine = SimulationRuntime(load_state_machine_from_text("state Root;"))
    processor = CommandProcessor(machine, use_color=False)
    for completer in (SimulationCompleter(machine), processor.create_completer()):
        assert [c.text for c in completer.get_completions(Document("why "), None)] == [
            "--verbose"
        ]
        assert list(completer.get_completions(Document("why NoMatch"), None)) == []
        assert [
            c.text for c in completer.get_completions(Document("decisions --v"), None)
        ] == ["--verbose"]
        assert "diagnostics" in [
            c.text for c in completer.get_completions(Document("setting dia"), None)
        ]
        assert "on" in [
            c.text
            for c in completer.get_completions(Document("setting diagnostics "), None)
        ]


def test_unicode_digit_count_is_rejected_readably(tmp_path):
    result = invoke(
        tmp_path,
        "cycle ²",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
        source="state Root;",
    )
    assert result.exit_code == 1
    assert "invalid cycle count" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "command",
    [
        "cycle 0",
        "history 0",
        "history nope",
        "setting unknown",
        "setting unknown value",
        "export",
        "export invalid.txt",
        "export missing/out.csv",
        "export missing/out.json",
        "export missing/out.yaml",
        "export missing/out.jsonl",
    ],
)
def test_existing_command_errors_return_failure_status(tmp_path, command):
    from hbutils.testing import isolated_directory

    with isolated_directory():
        result = invoke(
            tmp_path,
            "cycle; " + command,
            "--diagnostics",
            "--diagnostics-format",
            "jsonl",
            source="state Root;",
        )
    assert result.exit_code == 1, result.output
    assert len(result.stdout.splitlines()) == 1


def test_external_python_input_source_keeps_restart_ownership():
    machine = SimulationRuntime(
        load_state_machine_from_text(MODEL), input_source={"sensor": 1}
    )
    processor = CommandProcessor(machine, use_color=False)
    assert processor.process("init Root.A reading=0").exit_code == 1
    assert processor.process("clear").exit_code == 1


def test_parse_failure_has_no_json_report(tmp_path):
    result = invoke(
        tmp_path,
        "cycle",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
        source="state {",
    )
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Failed to parse DSL file" in result.stderr


def test_cli_import_reports_parent_roles_and_original_location(tmp_path):
    (tmp_path / "child.fcstm").write_text("""
        input int sensor;
        state Child { state A; state B; [*] -> A; A -> B : if [sensor > 0]; }
    """)
    result = invoke(
        tmp_path,
        "cycle; cycle",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
        source="""
        control int value = 1;
        state Host { import "./child.fcstm" as Worker { var sensor -> value; } [*] -> Worker; }
    """,
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout.splitlines()[1])
    decision = next(d for d in report["decisions"] if d["guard"] is not None)
    assert report["roles"] == {"value": "control"}
    assert decision["inputs"] == {}
    assert decision["vars"] == {"value": 1}
    assert decision["location"]["path"].endswith("child.fcstm")


def test_parameters_cannot_be_reassigned_after_construction(tmp_path):
    result = invoke(
        tmp_path,
        "init Root.A reading=0 gain=9",
        "--param",
        "gain=3",
        "--diagnostics",
        "--diagnostics-format",
        "jsonl",
    )
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Initialization failed" in result.stderr
