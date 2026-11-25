"""``pyfcstm bmc`` on a model with regions: the report and the JSON result."""

import json
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from pyfcstm.entry import pyfcstmcli

pytestmark = pytest.mark.unittest

SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "docs/source/reference/bmc_results/bmc_cli.schema.json"
)

INTERLOCK = """
input int fault;
input int requested;
control int permit = 0;
output int motor = 0;
state Controller {
    event Start;
    [*] -> Idle;
    state Idle { during { motor = 0; } }
    state Running {
        region Safety {
            [*] -> Watching;
            state Watching {
                during { if [fault != 0] { permit = 0; } else { permit = 1; } }
            }
        }
        region Motion {
            [*] -> Off;
            state Off { during { motor = 0; } }
            state On { during { motor = 1; } }
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [permit == 0 || requested == 0];
        }
    }
    Idle -> Running : /Start;
}
"""

MOTOR_ON = 'check reach <= 3: active("Controller.Running.Motion.On");'


def run_bmc(tmp_path, text, query, *extra):
    model = tmp_path / "m.fcstm"
    model.write_text(text, encoding="utf-8")
    question = tmp_path / "q.fbmcq"
    question.write_text(query, encoding="utf-8")
    return CliRunner().invoke(
        pyfcstmcli, ["bmc", "-i", str(model), "-q", str(question), *extra]
    )


def test_the_human_trace_shows_the_configuration_and_the_local_cases(tmp_path):
    result = run_bmc(tmp_path, INTERLOCK, MOTOR_ON, "--color", "never")
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert "  2: Controller.Running{Safety: Watching, Motion: Off}" in lines
    assert (
        "       -> Controller.Running{Safety: Watching, Motion: On} [transition]"
        in lines
    )
    assert "       Safety: Watching -> Watching [fallback]" in lines
    assert "       Motion: Off -> On [transition]" in lines
    assert "\x1b[" not in result.output


def test_the_group_entry_is_listed_under_the_owner_that_starts_its_regions(tmp_path):
    lines = run_bmc(tmp_path, INTERLOCK, MOTOR_ON, "--color", "never").output.splitlines()
    assert "       Controller.Idle -> Controller.Running [transition]" in lines
    assert "       Running: [start] -> Safety.Watching [initial]" in lines
    assert "       Running: [start] -> Motion.Off [initial]" in lines


def test_the_json_result_of_a_model_with_regions_passes_the_shipped_schema(tmp_path):
    result = run_bmc(tmp_path, INTERLOCK, MOTOR_ON, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)
    assert payload["replay"]["ok"] is True
    step = payload["witness"]["steps"][-1]
    assert step["case_label"] is None
    assert [item["scope"] for item in step["local_cases"]] == [
        "Controller.Running.Safety",
        "Controller.Running.Motion",
    ]
    last = payload["witness"]["frames"][-1]
    assert last["configuration"] == "Controller.Running{Safety: Watching, Motion: On}"
    assert payload["replay"]["runtime_trace"]["frames"][-1]["configuration"] == (
        last["configuration"]
    )
    assert not {"schema_version", "schema_status"} & set(payload)


def test_a_hot_start_by_configuration_text_is_checked_and_replayed(tmp_path):
    query = (
        'init state("Controller.Running{Motion: On}") havoc * '
        "where permit == 1 && motor == 1;\n"
        'check reach <= 2: active("Controller.Running.Motion.Off");'
    )
    result = run_bmc(tmp_path, INTERLOCK, query, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        payload
    )
    assert payload["witness"]["initial"]["configuration"] == (
        "Controller.Running{Safety: [init], Motion: On}"
    )
    assert payload["replay"]["ok"] is True


def test_a_runtime_error_in_a_region_is_reported_with_its_exit_code(tmp_path):
    text = """
    input int d;
    def int x = 0;
    state Root {
        region A { [*] -> P; state P { during { x = 10 % d; } } }
        region B { [*] -> Q; state Q; }
    }
    """
    result = run_bmc(
        tmp_path, text, "check reach <= 1: terminated();", "--json"
    )
    assert result.exit_code == 5, result.output
    payload = json.loads(result.output)
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        payload
    )
    assert payload["result"]["runtime_safety"]["status"] == "violated"
    assert payload["replay"]["ok"] is True


def test_the_human_trace_names_the_cold_start_and_the_start_of_every_region(tmp_path):
    text = (
        "state Root {\n"
        "    region A { [*] -> P; state P; }\n"
        "    region B { [*] -> Q; state Q; }\n"
        "}\n"
    )
    result = run_bmc(
        tmp_path, text, 'check reach <= 1: active("Root.A.P");', "--color", "never"
    )
    assert result.exit_code == 0
    assert "-> Root{A: P, B: Q} [initial]" in result.output
    assert "[start] -> Root [initial]" in result.output
    assert "Root: [start] -> A.P [initial]" in result.output
    assert "Root: [start] -> B.Q [initial]" in result.output


def test_the_human_trace_marks_a_region_that_finished(tmp_path):
    text = (
        "state Root {\n"
        "    region A { [*] -> P; state P; P -> [*]; }\n"
        "    region B { [*] -> Q; state Q; }\n"
        "}\n"
    )
    result = run_bmc(
        tmp_path, text, 'check reach <= 2: active("Root.B.Q");', "--color", "never"
    )
    assert result.exit_code == 0
    assert "A: P -> [done] [transition]" in result.output
