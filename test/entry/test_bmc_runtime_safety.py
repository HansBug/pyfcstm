"""``pyfcstm bmc`` reports a reachable runtime error before the property."""

import json
from pathlib import Path

import pytest
import z3
from click.testing import CliRunner

from pyfcstm.entry import pyfcstmcli

DIVIDING_GUARD = """input int d;
state Root {
    [*] -> A;
    state A; state B; state C;
    A -> B : if [d == 1];
    A -> C : if [10 / d > 1];
}
"""
# Two macro steps leave step 1 as the only step an error can happen at.
QUERY = 'check reach <= 2: active("Root.B");\n'
SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "source"
    / "reference"
    / "bmc_results"
    / "bmc_cli.schema.json"
)


@pytest.fixture()
def files(tmp_path):
    def write(model, query=QUERY):
        model_path = tmp_path / "machine.fcstm"
        query_path = tmp_path / "property.fbmcq"
        model_path.write_text(model, encoding="utf-8")
        query_path.write_text(query, encoding="utf-8")
        return ["-i", str(model_path), "-q", str(query_path)]

    return write


def _run(*args):
    return CliRunner().invoke(pyfcstmcli, ["bmc", "--color", "never", *args])


def _schema_errors(payload):
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    return [error.message for error in validator.iter_errors(payload)]


@pytest.mark.unittest
def test_a_reachable_runtime_error_is_exit_five(files):
    result = _run(*files(DIVIDING_GUARD))

    assert result.exit_code == 5
    lines = result.stdout.splitlines()
    assert lines[0] == "BMC reach <= 2: RUNTIME ERROR REACHABLE WITHIN BOUND; PROPERTY NOT EVALUATED"
    assert "  Runtime error: division_by_zero at step 1" in lines
    assert "  Runtime error location: guard g1 in transition Root.A::1::A->C" in lines
    assert "Solver: NOT RUN" in lines
    assert "  1: Root.A -> RUNTIME ERROR division_by_zero" in lines
    assert any(line.startswith("  Replay: runtime error reproduced: ") for line in lines)


@pytest.mark.unittest
def test_the_runtime_error_json_follows_the_published_schema(files):
    result = _run(*files(DIVIDING_GUARD), "--json")

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["result"]["outcome"] == "runtime_error"
    assert payload["result"]["runtime_safety"]["status"] == "violated"
    assert payload["witness"]["model_role"] == "runtime_error_prefix"
    assert payload["witness"]["verdict"]["runtime_error"] == {
        "events": [],
        "inputs": {"d": 0},
        "kind": "division_by_zero",
        "location": "guard g1 in transition Root.A::1::A->C",
        "step": 1,
    }
    assert _schema_errors(payload) == []


@pytest.mark.unittest
def test_an_initializer_error_is_reported_before_any_step(files):
    result = _run(*files("def float x = sqrt(0 - 1);\nstate Root;\n", 'check reach <= 1: active("Root");\n'))

    assert result.exit_code == 5
    assert "  init: RUNTIME ERROR math_domain (initializer for x)" in result.stdout.splitlines()
    payload = json.loads(
        _run(*files("def float x = sqrt(0 - 1);\nstate Root;\n", 'check reach <= 1: active("Root");\n'), "--json").stdout
    )
    assert payload["witness"]["verdict"]["runtime_error"]["step"] is None
    assert _schema_errors(payload) == []


@pytest.mark.unittest
def test_the_check_can_be_switched_off(files):
    result = _run(*files(DIVIDING_GUARD), "--no-runtime-safety", "--json")

    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert payload["result"]["runtime_safety"] is None
    assert payload["result"]["outcome"] != "runtime_error"
    assert _schema_errors(payload) == []


@pytest.mark.unittest
def test_a_safe_model_reports_its_checked_operations(files):
    payload = json.loads(_run(*files(DIVIDING_GUARD.replace("d == 1", "d == 0")), "--json").stdout)

    safety = payload["result"]["runtime_safety"]
    assert (safety["status"], safety["error"], safety["reason"]) == ("safe", None, None)
    assert safety["sites"] >= 1
    assert _schema_errors(payload) == []


@pytest.mark.unittest
def test_an_undecided_check_is_exit_three(files, monkeypatch):
    args = files(DIVIDING_GUARD)
    # The solver gives up the way Z3 does on a query it cannot decide.
    monkeypatch.setattr(z3.Solver, "check", lambda self, *a: z3.unknown)
    monkeypatch.setattr(z3.Solver, "reason_unknown", lambda self: "incomplete")

    human = _run(*args)
    payload = json.loads(_run(*args, "--json").stdout)

    assert human.exit_code == 3
    assert "Runtime safety check: UNKNOWN in " in human.stdout
    assert payload["result"]["outcome"] == "runtime_safety_unknown"
    assert payload["witness"] is None
    assert _schema_errors(payload) == []


HALVING = """def int x = 0;
state Root {
    [*] -> A;
    A -> [*];
    state A { enter { x = x / 2; } }
}
"""


def _halving_query(start):
    return (
        'init cold havoc *;\nassume at 0: var("x") == %d;\n'
        'assume at 1: var("x") == 99;\ncheck reach <= 2: terminated();\n' % start
    )


@pytest.mark.unittest
def test_an_int_halved_without_remainder_is_proved_as_an_int(files):
    # True division leaves the quotient real, and the int writeback keeps it as
    # the integer the variable holds; the proof states that integer.
    result = _run(*files(HALVING, _halving_query(6)), "--explain-infeasibility", "proof")

    lines = result.stdout.splitlines()
    assert "Explanation: COMPLETE VERIFIED DOMAIN PROOF" in lines
    assert "  6. Starting from that value, the step therefore leaves x equal to 3 at frame 1." in lines


@pytest.mark.unittest
def test_an_int_halved_with_a_remainder_is_a_writeback_error(files):
    result = _run(*files(HALVING, _halving_query(7)))

    assert result.exit_code == 5
    assert "  Runtime error: writeback_non_integral at step 0" in result.stdout.splitlines()


@pytest.mark.unittest
def test_build_bmc_output_rejects_a_non_boolean_switch(files):
    from pyfcstm.entry.base import ClickErrorException
    from pyfcstm.entry.bmc import build_bmc_output

    model_path, query_path = files(DIVIDING_GUARD)[1::2]
    with pytest.raises(ClickErrorException, match="runtime_safety must be bool"):
        build_bmc_output(model_path, query_path, runtime_safety="yes")


@pytest.mark.unittest
@pytest.mark.parametrize("stage", ["_decode_bmc_result_trace", "_replay_bmc_witness"])
def test_an_internal_error_prefix_failure_keeps_its_traceback(files, monkeypatch, stage):
    import pyfcstm.entry.bmc as bmc_entry
    from pyfcstm.bmc import BmcBuildError

    def fail(*args, **kwargs):
        raise BmcBuildError("internal BMC witness consistency error")

    args = files(DIVIDING_GUARD)
    monkeypatch.setattr(bmc_entry, stage, fail)
    result = CliRunner().invoke(pyfcstmcli, ["bmc", *args, "--json"])

    assert result.exit_code == 1
    assert "internal BMC witness consistency error" in result.stderr


@pytest.mark.unittest
def test_a_constant_assignment_is_restated_as_it_was_written(files):
    model = HALVING.replace("x = x / 2;", "x = 5;")
    result = _run(*files(model, _halving_query(6)), "--explain-infeasibility", "proof")

    assert any("the transition sets x to 5" in line for line in result.stdout.splitlines())
