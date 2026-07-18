"""Tests for the user-facing BMC command-line entry point."""

from __future__ import annotations

import json
import copy
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from pyfcstm.bmc import BmcBuildError, BmcFeasibilityCheck, BmcFeasibilityResult
from pyfcstm.bmc.witness import BmcReplayMismatch, BmcSolveResult
from pyfcstm.dsl import GrammarParseError
from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.base import ClickErrorException
from pyfcstm.utils import ModelValidationError


pytestmark = pytest.mark.unittest


def _assert_bmc_schema_instance(schema, value, path="$", definitions=None):
    """Validate the BMC result schema with the standard-library test harness."""
    definitions = schema.get("$defs", {}) if definitions is None else definitions
    if "$ref" in schema:
        ref = schema["$ref"]
        assert ref.startswith("#/$defs/"), "%s has unsupported ref %r" % (path, ref)
        return _assert_bmc_schema_instance(
            definitions[ref.split("/", 2)[-1]], value, path, definitions
        )
    if "oneOf" in schema:
        errors = []
        for branch in schema["oneOf"]:
            try:
                _assert_bmc_schema_instance(branch, value, path, definitions)
            except AssertionError as err:
                errors.append(str(err))
            else:
                return
        raise AssertionError("%s matched no oneOf branch: %s" % (path, errors))
    if "const" in schema:
        assert value == schema["const"], "%s != const %r" % (path, schema["const"])
    if "enum" in schema:
        assert value in schema["enum"], "%s not in enum %r" % (path, schema["enum"])
    if "type" in schema:
        allowed_types = schema["type"]
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]
        type_matches = {
            "null": value is None,
            "boolean": type(value) is bool,
            "integer": type(value) is int,
            "number": type(value) in (int, float) and type(value) is not bool,
            "string": isinstance(value, str),
            "array": isinstance(value, list),
            "object": isinstance(value, dict),
        }
        assert any(type_matches[item] for item in allowed_types), (
            "%s has wrong type: %r" % (path, type(value).__name__)
        )
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            assert required in value, "%s missing required %s" % (path, required)
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(properties), "%s has unknown fields %r" % (
                path,
                sorted(set(value) - set(properties)),
            )
        for key, item in value.items():
            if key in properties:
                _assert_bmc_schema_instance(
                    properties[key], item, "%s.%s" % (path, key), definitions
                )
            elif isinstance(schema.get("additionalProperties"), dict):
                _assert_bmc_schema_instance(
                    schema["additionalProperties"],
                    item,
                    "%s.%s" % (path, key),
                    definitions,
                )
    elif isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            _assert_bmc_schema_instance(
                schema["items"], item, "%s[%d]" % (path, index), definitions
            )
    if "minimum" in schema and type(value) in (int, float):
        assert value >= schema["minimum"], "%s is below minimum" % path


@pytest.fixture()
def bmc_files(tmp_path: Path):
    """Create entry-owned model and query fixtures."""
    model_path = tmp_path / "machine.fcstm"
    model_path.write_text("state Root;\n", encoding="utf-8")

    def query(text: str, name: str = "property.fbmcq") -> Path:
        path = tmp_path / name
        path.write_text(text + "\n", encoding="utf-8")
        return path

    return model_path, query


def _run(*args: str):
    return CliRunner().invoke(pyfcstmcli, ["bmc", *args])


def _json_result(model_path: Path, query_path: Path, *args: str):
    result = _run("-i", str(model_path), "-q", str(query_path), "--json", *args)
    return result, json.loads(result.stdout) if result.stdout else None


def _stderr_text(result) -> str:
    """Return stderr across Click versions with and without split capture."""
    try:
        return result.stderr
    except ValueError:
        # Older Click releases merge stderr into output and reject the stderr
        # property instead of exposing a separately captured stream.
        return result.output


def _assert_stderr_only(result, fragment: str) -> None:
    """Check an error message and strict stdout separation when available."""
    try:
        stderr = result.stderr
    except ValueError:
        # Older Click cannot prove stream separation; output still proves the
        # user-facing error while surrounding assertions cover side effects.
        assert fragment in result.output
    else:
        assert result.stdout == ""
        assert fragment in stderr


def test_importing_entry_does_not_eagerly_load_bmc() -> None:
    """Registering CLI commands leaves the optional BMC stack unloaded."""
    script = """
import sys
from pyfcstm.entry import pyfcstmcli

assert pyfcstmcli.name == "pyfcstmcli"
loaded = sorted(
    name for name in sys.modules
    if name == "pyfcstm.bmc" or name.startswith("pyfcstm.bmc.")
)
if loaded:
    raise SystemExit("\\n".join(loaded))
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_bmc_help_registers_frozen_options() -> None:
    """The root CLI exposes the complete frozen BMC option surface."""
    result = _run("--help")

    assert result.exit_code == 0
    assert "-i, --input-code" in result.output
    assert "-q, --query-file" in result.output
    assert "-o, --output" in result.output
    assert "--json" in result.output
    assert "--timeout-ms" in result.output
    assert "--max-bound" in result.output
    assert "--color" in result.output


@pytest.mark.parametrize(
    ("query_text", "expected_exit", "status", "outcome", "has_trace"),
    [
        ('check reach <= 1: active("Root");', 0, "sat", "witness_found", True),
        ("check reach <= 1: terminated();", 1, "unsat", "no_witness", False),
        (
            'check forbid <= 1: active("Root");',
            1,
            "sat",
            "property_violated",
            True,
        ),
        (
            "check forbid <= 1: terminated();",
            0,
            "unsat",
            "property_satisfied",
            False,
        ),
    ],
)
def test_bmc_json_verdict_matrix(
    bmc_files,
    query_text: str,
    expected_exit: int,
    status: str,
    outcome: str,
    has_trace: bool,
) -> None:
    """JSON mirrors process verdicts across witness and counterexample polarity."""
    model_path, query = bmc_files
    query_path = query(query_text)

    result, payload = _json_result(model_path, query_path)

    schema = json.loads(
        Path("docs/source/reference/bmc_results/bmc_cli.schema.json").read_text(
            encoding="utf-8"
        )
    )
    _assert_bmc_schema_instance(schema, payload)
    assert result.exit_code == expected_exit
    assert "schema_version" not in payload
    assert payload["exit_code"] == result.exit_code
    assert payload["result"]["status"] == status
    assert payload["result"]["outcome"] == outcome
    assert (payload["witness"] is not None) is has_trace
    assert (payload["replay"] is not None) is has_trace
    if has_trace:
        assert payload["replay"]["ok"] is True
        assert "delta" in payload["replay"]["runtime_trace"]["steps"][0]
    assert "formulas" not in json.dumps(payload)


def test_bmc_human_report_prioritizes_verdict_and_diagnostics(bmc_files) -> None:
    """Human output exposes scenario, search, conclusion, and evidence first."""
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    result = _run("-i", str(model_path), "-q", str(query_path))

    assert result.exit_code == 0
    assert result.stdout.startswith("BMC reach <= 1: WITNESS FOUND WITHIN BOUND\n")
    assert "Scenario: FEASIBLE" in result.stdout
    assert "Primary search: WITNESS = SAT" in result.stdout
    assert "Response horizon:" not in result.stdout
    assert (
        "Conclusion: At least one admissible execution satisfies the reach "
        "objective within 1 macro-step."
    ) in result.stdout
    assert "Evidence:" in result.stdout
    assert "Model role: PRIMARY WITNESS" in result.stdout
    assert "Solver: SAT in " in result.stdout
    assert "Replay: verified (2 frames, 1 step)." in result.stdout
    assert "\nTrace\n  0: init -> Root [initial]" in result.stdout
    assert "This is a bounded result" in result.stdout
    assert "Use --json for the complete" in result.stdout
    assert "BmcSolveResult" not in result.stdout
    assert "BmcWitnessTrace" not in result.stdout
    assert result.stdout.endswith("\n")


@pytest.mark.parametrize(
    ("query_text", "heading", "fragments"),
    [
        (
            "check reach <= 1: terminated();",
            "BMC reach <= 1: NO WITNESS WITHIN BOUND",
            (
                "Scenario: FEASIBLE",
                "Primary search: WITNESS = UNSAT",
                "Conclusion: No admissible execution satisfies the reach objective "
                "within 1 macro-step.",
            ),
        ),
        (
            'check forbid <= 1: active("Root");',
            "BMC forbid <= 1: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND",
            (
                "Scenario: FEASIBLE",
                "Primary search: COUNTEREXAMPLE = SAT",
                "Conclusion: At least one admissible execution violates the forbid "
                "property within 1 macro-step.",
                "Model role: PRIMARY COUNTEREXAMPLE",
            ),
        ),
        (
            "check forbid <= 1: terminated();",
            "BMC forbid <= 1: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE",
            (
                "Scenario: FEASIBLE",
                "Primary search: COUNTEREXAMPLE = UNSAT",
                "Conclusion: Every admissible execution within 1 macro-step satisfies "
                "the forbid property.",
            ),
        ),
        (
            "check response <= 1: trigger true -> within 2 false;",
            "BMC response <= 1: PROPERTY INCONCLUSIVE; RESPONSE HORIZON INCOMPLETE",
            (
                "Scenario: FEASIBLE",
                "Primary search: COUNTEREXAMPLE = UNSAT",
                "Response horizon: OPEN",
                "An admissible finite prefix leaves a response obligation open beyond "
                "the current horizon; no bounded property verdict is available.",
                "Model role: INCOMPLETE SUFFIX",
                "Replay: verified finite prefix (2 frames, 1 step).",
            ),
        ),
    ],
)
def test_bmc_human_report_explains_each_verdict_family(
    bmc_files, query_text: str, heading: str, fragments: tuple[str, ...]
) -> None:
    """Human reports distinguish each primary polarity and response outcome."""
    model_path, query = bmc_files
    query_path = query(query_text)

    result = _run("-i", str(model_path), "-q", str(query_path))

    assert result.stdout.startswith(heading + "\n")
    for fragment in fragments:
        assert fragment in result.stdout


@pytest.mark.parametrize(
    ("query_text", "headline_fragment", "conclusion_fragment"),
    [
        (
            "check exists_always <= 1: true;",
            "WITNESS FOUND WITHIN BOUND",
            "satisfies the exists_always objective",
        ),
        (
            "check invariant <= 1: true;",
            "PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE",
            "satisfies the invariant property",
        ),
        (
            'check must_reach <= 1: active("Root");',
            "PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE",
            "satisfies the must_reach property",
        ),
    ],
)
def test_bmc_human_report_uses_property_kind_in_quantifier_text(
    bmc_files,
    query_text: str,
    headline_fragment: str,
    conclusion_fragment: str,
) -> None:
    """Human conclusions do not hard-code the reach property kind."""
    model_path, query = bmc_files
    query_path = query(query_text)

    result = _run("-i", str(model_path), "-q", str(query_path))

    assert headline_fragment in result.stdout
    assert conclusion_fragment in result.stdout
    assert "reach objective" not in result.stdout


def test_bmc_human_report_marks_complete_response_horizon(bmc_files) -> None:
    """A response without a nontrivial suffix reports a complete horizon."""
    model_path, query = bmc_files
    query_path = query("check response <= 1: trigger true -> within 1 true;")

    result = _run("-i", str(model_path), "-q", str(query_path))

    assert result.exit_code == 0
    assert "PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE" in result.stdout
    assert "Response horizon: NOT NEEDED" in result.stdout
    assert "The response horizon is complete and no counterexample exists" in (
        result.stdout
    )


def test_bmc_human_report_distinguishes_feasibility_unknown_timeout_and_unchecked(
    bmc_files, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Feasibility uncertainty is not presented as an empty scenario."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query("check reach <= 1: terminated();")
    not_checked = BmcFeasibilityCheck(None, "not_checked")

    def run_with_result(feasibility, diagnostics=()):
        def solve(formula, *, timeout_ms=None):
            return BmcSolveResult(
                formula,
                "unsat",
                timeout_ms=timeout_ms,
                diagnostics=diagnostics,
                feasibility=feasibility,
            )

        monkeypatch.setattr(bmc_entry, "_solve_bmc_property", solve)
        return _run("-i", str(model_path), "-q", str(query_path))

    unknown = run_with_result(
        BmcFeasibilityResult(
            not_checked,
            not_checked,
            BmcFeasibilityCheck(
                "unknown", "checked", reason="incomplete", elapsed_ms=1.0
            ),
            localization_status="unknown",
        )
    )
    assert unknown.exit_code == 3
    assert "SCENARIO FEASIBILITY UNKNOWN; PROPERTY NOT EVALUATED" in unknown.stdout
    assert "Scenario: UNKNOWN" in unknown.stdout

    timed_out = run_with_result(
        BmcFeasibilityResult(
            not_checked,
            not_checked,
            BmcFeasibilityCheck("timeout", "checked", reason="timeout", elapsed_ms=1.0),
            localization_status="timeout",
        )
    )
    assert timed_out.exit_code == 3
    assert "SCENARIO FEASIBILITY TIMED OUT; PROPERTY NOT EVALUATED" in (
        timed_out.stdout
    )
    assert "Scenario: UNKNOWN" in timed_out.stdout

    unchecked = run_with_result(
        BmcFeasibilityResult(
            not_checked,
            not_checked,
            not_checked,
            localization_status="not_checked",
        ),
        diagnostics=(
            "feasibility_timeout:deadline_exhausted_before_assumptions_check",
        ),
    )
    assert unchecked.exit_code == 3
    assert "SCENARIO FEASIBILITY TIMED OUT; PROPERTY NOT EVALUATED" in (
        unchecked.stdout
    )
    assert "Scenario: NOT CHECKED" in unchecked.stdout


def test_bmc_human_report_keeps_known_infeasible_scenario_when_localization_stops(
    bmc_files, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Localization timeout does not downgrade a proven empty scenario."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query("check reach <= 1: terminated();")
    not_checked = BmcFeasibilityCheck(None, "not_checked")
    feasibility = BmcFeasibilityResult(
        not_checked,
        BmcFeasibilityCheck("timeout", "checked", reason="timeout", elapsed_ms=1.0),
        BmcFeasibilityCheck("unsat", "checked", elapsed_ms=1.0),
        localization_status="timeout",
    )

    def solve(formula, *, timeout_ms=None):
        return BmcSolveResult(
            formula,
            "unsat",
            timeout_ms=timeout_ms,
            feasibility=feasibility,
        )

    monkeypatch.setattr(bmc_entry, "_solve_bmc_property", solve)
    result = _run("-i", str(model_path), "-q", str(query_path))

    assert result.exit_code == 3
    assert "SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED" in result.stdout
    assert "Failure boundary: NOT LOCALIZED" in result.stdout
    assert "Localization: TIMEOUT (timeout)" in result.stdout
    assert "feasibility_unknown" not in result.stdout


def test_bmc_human_presentation_marks_api_only_disabled_suffix() -> None:
    """The internal presentation contract distinguishes a deliberately disabled suffix."""
    import pyfcstm.entry.bmc as bmc_entry
    from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    model = load_state_machine_from_text("state Root;\n")
    prepared = BmcEngine(model).prepare(
        "check response <= 1: trigger true -> within 2 false;"
    )
    formula = compile_bmc_property(build_bmc_core_formula(prepared))
    inferred_sat = BmcFeasibilityCheck("sat", "inferred")
    feasibility = BmcFeasibilityResult(
        inferred_sat,
        inferred_sat,
        BmcFeasibilityCheck("sat", "checked", elapsed_ms=1.0),
        localization_status="not_needed",
    )
    result = BmcSolveResult(
        formula,
        "unsat",
        incomplete_reason="incomplete check disabled",
        feasibility=feasibility,
    )
    execution = bmc_entry._BmcExecution(formula, result, None, None, 3)

    presentation = bmc_entry._human_presentation(execution)

    assert presentation.response_horizon == "DISABLED"
    assert "response horizon check was disabled" in presentation.conclusion


def test_bmc_human_color_is_terminal_only(bmc_files) -> None:
    """ANSI decoration is explicit for terminals and absent from JSON/files."""
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    colored = _run("-i", str(model_path), "-q", str(query_path), "--color", "always")
    assert "\x1b[" in colored.stdout
    assert "WITNESS FOUND WITHIN BOUND" in colored.stdout

    json_result = _run(
        "-i",
        str(model_path),
        "-q",
        str(query_path),
        "--json",
        "--color",
        "always",
    )
    assert "\x1b[" not in json_result.stdout
    json.loads(json_result.stdout)

    output_path = model_path.parent / "human.txt"
    file_result = _run(
        "-i",
        str(model_path),
        "-q",
        str(query_path),
        "--color",
        "always",
        "-o",
        str(output_path),
    )
    assert file_result.stdout == ""
    assert "\x1b[" not in output_path.read_text(encoding="utf-8")


def test_bmc_auto_color_honors_terminal_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto color follows TTY, NO_COLOR, and dumb-terminal conventions."""
    import pyfcstm.entry.bmc as bmc_entry

    monkeypatch.setattr(bmc_entry.sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert bmc_entry._resolve_bmc_color_enabled(
        "auto", json_output=False, output_file=None
    )

    monkeypatch.setenv("NO_COLOR", "1")
    assert not bmc_entry._resolve_bmc_color_enabled(
        "auto", json_output=False, output_file=None
    )

    assert not bmc_entry._resolve_bmc_color_enabled(
        "always", json_output=True, output_file=None
    )
    assert not bmc_entry._resolve_bmc_color_enabled(
        "always", json_output=False, output_file="report.txt"
    )


def test_bmc_output_file_receives_nonzero_verdict_atomically(bmc_files) -> None:
    """A deterministic negative result writes its report and leaves stdout empty."""
    model_path, query = bmc_files
    query_path = query("check reach <= 1: terminated();")
    output_path = model_path.parent / "result.json"
    output_path.write_text("old", encoding="utf-8")

    result = _run(
        "-i",
        str(model_path),
        "-q",
        str(query_path),
        "--json",
        "-o",
        str(output_path),
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["exit_code"] == 1
    assert not list(output_path.parent.glob(".result.json.*.tmp"))


def test_bmc_input_error_does_not_modify_output(bmc_files) -> None:
    """A query read failure is stderr-only and preserves an existing target."""
    model_path, _query = bmc_files
    output_path = model_path.parent / "result.json"
    output_path.write_text("keep", encoding="utf-8")

    result = _run(
        "-i",
        str(model_path),
        "-q",
        str(model_path.parent / "missing.fbmcq"),
        "--json",
        "-o",
        str(output_path),
    )

    assert result.exit_code == 1
    _assert_stderr_only(result, "Query file not found")
    assert output_path.read_text(encoding="utf-8") == "keep"


def test_bmc_structured_replay_mismatch_is_exit_four(
    bmc_files, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A returned replay mismatch produces a complete payload and exit four."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')
    original = bmc_entry._replay_bmc_witness

    def mismatching_replay(model, witness, *, abstract_handlers=None):
        replay = original(model, witness, abstract_handlers=abstract_handlers)
        return replace(
            replay,
            mismatches=(
                BmcReplayMismatch("frames[1].state", "Root", "Bad", "state mismatch"),
            ),
        )

    monkeypatch.setattr(bmc_entry, "_replay_bmc_witness", mismatching_replay)
    result, payload = _json_result(model_path, query_path)

    assert result.exit_code == 4
    assert payload["exit_code"] == 4
    assert payload["witness"] is not None
    assert payload["replay"]["ok"] is False
    assert payload["replay"]["mismatches"][0]["path"] == "frames[1].state"

    human = _run("-i", str(model_path), "-q", str(query_path), "--color", "always")
    assert human.exit_code == 4
    assert "EVIDENCE/REPLAY MISMATCH; RESULT UNTRUSTED" in human.stdout
    assert "could not be reproduced by the runtime" in human.stdout
    assert "Replay:" in human.stdout
    assert "FAILED (1 mismatch)." in human.stdout
    assert "Mismatch frames[1].state: state mismatch" in human.stdout


def test_bmc_schema_prioritizes_replay_mismatch_exit_four(
    bmc_files, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI schema accepts replay exit four and rejects lower-priority codes."""
    import pyfcstm.entry.bmc as bmc_entry

    jsonschema = pytest.importorskip("jsonschema")
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')
    original = bmc_entry._replay_bmc_witness

    def mismatching_replay(model, witness, *, abstract_handlers=None):
        replay = original(model, witness, abstract_handlers=abstract_handlers)
        return replace(
            replay,
            mismatches=(
                BmcReplayMismatch("frames[1].state", "Root", "Bad", "state mismatch"),
            ),
        )

    monkeypatch.setattr(bmc_entry, "_replay_bmc_witness", mismatching_replay)
    _, payload = _json_result(model_path, query_path)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )

    assert payload["result"]["outcome"] == "witness_found"
    assert payload["replay"]["ok"] is False
    assert payload["exit_code"] == 4
    assert list(validator.iter_errors(payload)) == []

    for exit_code in (0, 1, 3):
        forged = copy.deepcopy(payload)
        forged["exit_code"] = exit_code
        assert list(validator.iter_errors(forged)), exit_code

    replay_marked_ok = copy.deepcopy(payload)
    replay_marked_ok["replay"]["ok"] = True
    replay_marked_ok["replay"]["mismatches"] = payload["replay"]["mismatches"]
    replay_marked_ok["exit_code"] = 0
    assert list(validator.iter_errors(replay_marked_ok))

    mismatch_without_details = copy.deepcopy(payload)
    mismatch_without_details["replay"]["mismatches"] = []
    assert list(validator.iter_errors(mismatch_without_details))

    exit_four_without_replay = copy.deepcopy(payload)
    exit_four_without_replay["replay"] = None
    assert list(validator.iter_errors(exit_four_without_replay))


def test_bmc_internal_witness_error_keeps_traceback(
    bmc_files, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Internal witness consistency failures are not downgraded to CLI input errors."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    def fail_decode(*args, **kwargs):
        raise BmcBuildError(
            "This is an internal BMC witness consistency error; please open an issue."
        )

    monkeypatch.setattr(bmc_entry, "_decode_bmc_result_trace", fail_decode)
    result = _run("-i", str(model_path), "-q", str(query_path), "--json")

    assert result.exit_code == 1
    _assert_stderr_only(result, "Unexpected error found when running pyfcstm!")
    assert "internal BMC witness consistency error" in _stderr_text(result)


@pytest.mark.parametrize("stage", ["decode", "replay"])
def test_bmc_unexpected_witness_pipeline_error_keeps_traceback(
    bmc_files, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """Unexpected decode and replay failures retain the process traceback."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    def fail_pipeline(*args, **kwargs):
        raise ValueError("forged %s failure" % stage)

    target = "_decode_bmc_result_trace" if stage == "decode" else "_replay_bmc_witness"
    monkeypatch.setattr(bmc_entry, target, fail_pipeline)
    result = _run("-i", str(model_path), "-q", str(query_path), "--json")

    assert result.exit_code == 1
    _assert_stderr_only(result, "Unexpected error found when running pyfcstm!")
    assert "ValueError: forged %s failure" % stage in _stderr_text(result)


def test_bmc_rejects_nonpositive_numeric_options(bmc_files) -> None:
    """Click rejects nonpositive timeout and maximum bound values as usage errors."""
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    for option in ("--timeout-ms", "--max-bound"):
        result = _run("-i", str(model_path), "-q", str(query_path), option, "0")
        assert result.exit_code == 2
        assert "Invalid value" in _stderr_text(result)


def test_bmc_response_incomplete_is_exit_three(bmc_files) -> None:
    """A satisfiable tail observation remains an explicit incomplete verdict."""
    model_path, query = bmc_files
    query_path = query("check response <= 1: trigger true -> within 2 false;")

    result, payload = _json_result(model_path, query_path)

    schema = json.loads(
        Path("docs/source/reference/bmc_results/bmc_cli.schema.json").read_text(
            encoding="utf-8"
        )
    )
    _assert_bmc_schema_instance(schema, payload)
    assert result.exit_code == 3
    assert payload["exit_code"] == 3
    assert payload["result"]["status"] == "unsat"
    assert payload["result"]["incomplete"] is True
    assert payload["result"]["outcome"] == "incomplete"
    assert payload["result"]["incomplete_status"] == "sat"
    assert "schema_version" not in payload["witness"]
    assert payload["witness"]["model_role"] == "incomplete_suffix"
    assert payload["replay"]["model_role"] == "incomplete_suffix"


def test_bmc_scenario_infeasible_is_not_a_property_failure(bmc_files) -> None:
    """Contradictory assumptions produce a distinct non-verdict CLI result."""
    model_path, query = bmc_files
    model_path.write_text("def int x = 0;\nstate Root;\n", encoding="utf-8")
    query_path = query(
        'assume at 0: x == 0;\nassume at 0: x == 1;\ncheck reach <= 1: active("Root");'
    )

    result, payload = _json_result(model_path, query_path)

    assert result.exit_code == 3
    assert payload["exit_code"] == 3
    assert payload["result"]["outcome"] == "scenario_infeasible"
    assert payload["result"]["property_satisfied"] is None
    assert payload["witness"] is None
    assert payload["replay"] is None

    human = _run("-i", str(model_path), "-q", str(query_path))
    assert human.exit_code == 3
    assert "SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED" in human.stdout
    assert "Scenario: INFEASIBLE" in human.stdout
    assert "Primary search: WITNESS = UNSAT" in human.stdout
    assert "Failure boundary: ASSUMPTIONS" in human.stdout
    assert "Adding assumptions leaves no admissible execution." in human.stdout


def test_bmc_schema_rejects_forged_scenario_infeasible_verdict(bmc_files) -> None:
    """The published schema rejects terminal verdict and channel mutations."""
    jsonschema = pytest.importorskip("jsonschema")
    model_path, query = bmc_files
    model_path.write_text("def int x = 0;\nstate Root;\n", encoding="utf-8")
    query_path = query(
        'assume at 0: x == 0;\nassume at 0: x == 1;\ncheck reach <= 1: active("Root");'
    )
    _, payload = _json_result(model_path, query_path)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )

    assert list(validator.iter_errors(payload)) == []
    mutations = (
        ("outcome", lambda item: item["result"].update(outcome="property_satisfied")),
        (
            "verdict",
            lambda item: item["result"].update(
                property_satisfied=True,
                witness_found=False,
                counterexample_found=False,
                incomplete=False,
                outcome="property_satisfied",
            ),
        ),
        (
            "role",
            lambda item: item["result"].update(
                available_model_roles=["primary_counterexample"]
            ),
        ),
        (
            "assumptions origin",
            lambda item: item["result"]["feasibility"]["assumptions"].update(
                origin="inferred"
            ),
        ),
        (
            "infeasible stage localization",
            lambda item: item["result"]["feasibility"].update(
                localization_status="not_needed"
            ),
        ),
        (
            "complete refinement without checks",
            lambda item: item["result"]["feasibility"].update(
                refinement_status="complete", refinement_checks=[]
            ),
        ),
        (
            "unused refinement with checks",
            lambda item: item["result"]["feasibility"].update(
                refinement_status="not_needed",
                refinement_checks=[
                    {
                        "name": "unsat_core",
                        "status": "complete",
                        "reason": None,
                        "elapsed_ms": 1.0,
                    }
                ],
            ),
        ),
        (
            "refinement completed reason",
            lambda item: item["result"]["feasibility"].update(
                refinement_status="partial",
                refinement_checks=[
                    {
                        "name": "component_initialization",
                        "status": "sat",
                        "reason": "forged",
                        "elapsed_ms": 1.0,
                    }
                ],
            ),
        ),
        (
            "localized refinement status",
            lambda item: item["result"]["feasibility"].update(
                refinement_status="not_needed"
            ),
        ),
        (
            "result reason",
            lambda item: item["result"].update(reason="forged"),
        ),
        (
            "negative timeout",
            lambda item: item["result"].update(timeout_ms=-1),
        ),
        ("exit code", lambda item: item.update(exit_code=0)),
    )
    for name, mutate in mutations:
        forged = copy.deepcopy(payload)
        mutate(forged)
        assert list(validator.iter_errors(forged)), name


def test_bmc_schema_rejects_localized_prefix_origin_mutations(bmc_files) -> None:
    """Schema localization branches require real checked prefix evidence."""
    jsonschema = pytest.importorskip("jsonschema")
    model_path, query = bmc_files
    model_path.write_text("def int x = 0;\nstate Root;\n", encoding="utf-8")
    query_path = query(
        'assume at 0: x == 0;\nassume at 0: x == 1;\ncheck reach <= 1: active("Root");'
    )
    _, payload = _json_result(model_path, query_path)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )
    assert list(validator.iter_errors(payload)) == []

    inferred_initialization = copy.deepcopy(payload)
    inferred_initialization["result"]["feasibility"]["initialization"].update(
        origin="inferred", elapsed_ms=None
    )
    assert list(validator.iter_errors(inferred_initialization))

    inferred_kernel = copy.deepcopy(payload)
    feasibility = inferred_kernel["result"]["feasibility"]
    feasibility["infeasible_stage"] = "initialization"
    feasibility["initialization"].update(
        status="unsat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["kernel"].update(
        status="sat", origin="inferred", reason=None, elapsed_ms=None
    )
    assert list(validator.iter_errors(inferred_kernel))

    inferred_without_checked_source = copy.deepcopy(payload)
    feasibility = inferred_without_checked_source["result"]["feasibility"]
    feasibility["kernel"].update(
        status="sat", origin="inferred", reason=None, elapsed_ms=None
    )
    feasibility["initialization"].update(
        status="unknown", origin="checked", reason="probe unknown", elapsed_ms=1.0
    )
    feasibility["assumptions"].update(
        status="unsat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["infeasible_stage"] = None
    feasibility["localization_status"] = "unknown"
    assert list(validator.iter_errors(inferred_without_checked_source))

    unchecked_kernel_outer_stages = copy.deepcopy(payload)
    result = unchecked_kernel_outer_stages["result"]
    result.update(
        property_satisfied=False,
        witness_found=False,
        counterexample_found=False,
        incomplete=False,
        outcome="no_witness",
        available_model_roles=[],
    )
    feasibility = result["feasibility"]
    not_checked = {
        "status": None,
        "origin": "not_checked",
        "reason": None,
        "elapsed_ms": None,
    }
    feasibility["kernel"].update(
        status="unsat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["initialization"] = copy.deepcopy(not_checked)
    feasibility["assumptions"] = copy.deepcopy(not_checked)
    feasibility["infeasible_stage"] = "kernel"
    feasibility["localization_status"] = "complete"
    assert list(validator.iter_errors(unchecked_kernel_outer_stages))

    unchecked_initialization_outer_stage = copy.deepcopy(payload)
    result = unchecked_initialization_outer_stage["result"]
    result.update(
        property_satisfied=False,
        witness_found=False,
        counterexample_found=False,
        incomplete=False,
        outcome="no_witness",
        available_model_roles=[],
    )
    feasibility = result["feasibility"]
    feasibility["kernel"].update(
        status="sat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["initialization"].update(
        status="unsat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["assumptions"] = copy.deepcopy(not_checked)
    feasibility["infeasible_stage"] = "initialization"
    feasibility["localization_status"] = "complete"
    assert list(validator.iter_errors(unchecked_initialization_outer_stage))

    unlocalized_assumptions = copy.deepcopy(payload)
    feasibility = unlocalized_assumptions["result"]["feasibility"]
    feasibility["kernel"].update(
        status="unknown", origin="checked", reason="timeout", elapsed_ms=1.0
    )
    feasibility["infeasible_stage"] = None
    feasibility["localization_status"] = "not_checked"
    assert list(validator.iter_errors(unlocalized_assumptions))

    unlocalized_initialization = copy.deepcopy(payload)
    feasibility = unlocalized_initialization["result"]["feasibility"]
    feasibility["kernel"].update(
        status="sat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["initialization"].update(
        status="unsat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["assumptions"].update(
        status="unsat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["infeasible_stage"] = None
    feasibility["localization_status"] = "not_checked"
    assert list(validator.iter_errors(unlocalized_initialization))

    unlocalized_not_needed = copy.deepcopy(payload)
    feasibility = unlocalized_not_needed["result"]["feasibility"]
    feasibility["kernel"] = {
        "status": None,
        "origin": "not_checked",
        "reason": None,
        "elapsed_ms": None,
    }
    feasibility["initialization"] = copy.deepcopy(feasibility["kernel"])
    feasibility["assumptions"].update(
        status="unsat", origin="checked", reason=None, elapsed_ms=1.0
    )
    feasibility["infeasible_stage"] = None
    feasibility["localization_status"] = "not_needed"
    assert list(validator.iter_errors(unlocalized_not_needed))

    for localization_status in ("unknown", "timeout"):
        unlocalized_inconclusive = copy.deepcopy(unlocalized_not_needed)
        unlocalized_inconclusive["result"]["feasibility"]["localization_status"] = (
            localization_status
        )
        assert list(validator.iter_errors(unlocalized_inconclusive))


def test_bmc_schema_rejects_terminal_verdict_mutations(bmc_files) -> None:
    """Schema binds feasible primary UNSAT to its polarity truth table."""
    jsonschema = pytest.importorskip("jsonschema")
    model_path, query = bmc_files
    query_path = query("check forbid <= 1: terminated();")
    _, payload = _json_result(model_path, query_path)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )
    assert list(validator.iter_errors(payload)) == []

    mutations = (
        {"property_satisfied": False, "witness_found": True},
        {"outcome": "no_witness"},
        {"incomplete": True},
        {"exit_code": 0},
    )
    for changes in mutations:
        forged = copy.deepcopy(payload)
        forged["result"].update(changes)
        if "exit_code" in changes:
            forged["exit_code"] = changes["exit_code"]
        assert list(validator.iter_errors(forged)), changes


def test_bmc_schema_rejects_suffix_channel_mutations(bmc_files) -> None:
    """Schema keeps suffix status, reason, feasibility, and role aligned."""
    jsonschema = pytest.importorskip("jsonschema")
    model_path, query = bmc_files
    query_path = query("check response <= 1: trigger true -> within 2 false;")
    _, payload = _json_result(model_path, query_path)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )
    assert list(validator.iter_errors(payload)) == []

    forged_elapsed = copy.deepcopy(payload)
    forged_elapsed["result"]["incomplete_reason"] = "forged"
    forged_elapsed["result"]["incomplete_elapsed_ms"] = None
    assert list(validator.iter_errors(forged_elapsed))

    forged_trace_elapsed = copy.deepcopy(payload)
    forged_trace_elapsed["witness"]["solver"]["incomplete_elapsed_ms"] = None
    assert list(validator.iter_errors(forged_trace_elapsed))

    forged_feasibility = copy.deepcopy(payload)
    forged_feasibility["result"]["feasibility"]["assumptions"] = {
        "status": "unknown",
        "origin": "checked",
        "reason": "solver stopped",
        "elapsed_ms": 1.0,
    }
    forged_feasibility["result"]["feasibility"]["localization_status"] = "unknown"
    assert list(validator.iter_errors(forged_feasibility))

    forged_solver_reason = copy.deepcopy(payload)
    forged_solver_reason["witness"]["solver"]["primary_reason"] = "forged"
    assert list(validator.iter_errors(forged_solver_reason))

    forged_property = copy.deepcopy(payload)
    forged_property["witness"]["property"]["kind"] = "reach"
    assert list(validator.iter_errors(forged_property))


def test_bmc_schema_rejects_mismatched_role_aware_trace_roles(bmc_files) -> None:
    """Envelope replay role must match the result and witness channel."""
    jsonschema = pytest.importorskip("jsonschema")
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')
    _, payload = _json_result(model_path, query_path)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )
    assert list(validator.iter_errors(payload)) == []
    assert payload["result"]["available_model_roles"] == ["primary_witness"]
    assert payload["witness"]["model_role"] == "primary_witness"
    assert payload["replay"]["model_role"] == "primary_witness"

    forged = copy.deepcopy(payload)
    forged["replay"]["model_role"] = "primary_counterexample"
    assert list(validator.iter_errors(forged))


@pytest.mark.parametrize(
    ("status", "reason"), [("timeout", "timeout"), ("unknown", "incomplete")]
)
def test_bmc_solver_inconclusive_is_exit_three(
    bmc_files,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    reason: str,
) -> None:
    """Timeout and unknown outcomes remain report-bearing exit-three results."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    def inconclusive(formula, *, timeout_ms=None):
        return BmcSolveResult(
            formula,
            status,
            reason=reason,
            timeout_ms=timeout_ms,
        )

    monkeypatch.setattr(bmc_entry, "_solve_bmc_property", inconclusive)
    result, payload = _json_result(model_path, query_path, "--timeout-ms", "25")

    schema = json.loads(
        Path("docs/source/reference/bmc_results/bmc_cli.schema.json").read_text(
            encoding="utf-8"
        )
    )
    _assert_bmc_schema_instance(schema, payload)
    assert result.exit_code == 3
    assert payload["exit_code"] == 3
    assert payload["result"]["status"] == status
    assert payload["result"]["outcome"] == status
    assert payload["result"]["timeout_ms"] == 25
    assert payload["witness"] is None
    assert payload["replay"] is None

    human = _run(
        "-i",
        str(model_path),
        "-q",
        str(query_path),
        "--timeout-ms",
        "25",
    )
    assert human.exit_code == 3
    assert "Timeout: 25 ms shared by all solver checks" in human.stdout
    assert "Scenario: NOT CHECKED" in human.stdout
    assert "Primary search: WITNESS = %s" % status.upper() in human.stdout
    assert "Solver reason: %s" % reason in human.stdout


def test_bmc_schema_rejects_removed_version_fields(bmc_files) -> None:
    """The unversioned schema rejects version fields at every payload level."""
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')
    _, payload = _json_result(model_path, query_path)
    schema = json.loads(
        Path("docs/source/reference/bmc_results/bmc_cli.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert "schema_version" not in payload
    assert "schema_version" not in payload["result"]
    assert "schema_version" not in payload["witness"]

    versioned_root = deepcopy(payload)
    versioned_root["schema_version"] = "bmc-cli/v1"
    with pytest.raises(AssertionError, match="unknown fields"):
        _assert_bmc_schema_instance(schema, versioned_root)

    versioned_result = deepcopy(payload)
    versioned_result["result"]["schema_version"] = "bmc-solve-result/v2"
    with pytest.raises(AssertionError, match="unknown fields"):
        _assert_bmc_schema_instance(schema, versioned_result)

    versioned_witness = deepcopy(payload)
    versioned_witness["witness"]["schema_version"] = "bmc-witness/v2"
    with pytest.raises(AssertionError, match="unknown fields"):
        _assert_bmc_schema_instance(schema, versioned_witness)


def test_bmc_schema_accepts_legacy_shape_envelope(bmc_files) -> None:
    """The published schema accepts the pre-role payload by structural shape."""
    jsonschema = pytest.importorskip("jsonschema")
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')
    _, payload = _json_result(model_path, query_path)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )

    legacy = deepcopy(payload)
    for key in (
        "incomplete_elapsed_ms",
        "total_elapsed_ms",
        "feasibility",
        "available_model_roles",
    ):
        legacy["result"].pop(key, None)
    for key in ("model_role", "verdict"):
        legacy["witness"].pop(key, None)
    legacy["witness"]["solver"] = {
        "status": "sat",
        "reason": None,
        "incomplete_status": None,
    }
    legacy["replay"].pop("model_role", None)

    assert list(validator.iter_errors(legacy)) == []


def test_bmc_max_bound_is_a_controlled_compile_error(bmc_files) -> None:
    """The maximum-bound policy rejects larger queries without writing a report."""
    model_path, query = bmc_files
    query_path = query('check reach <= 2: active("Root");')

    result = _run(
        "-i",
        str(model_path),
        "-q",
        str(query_path),
        "--max-bound",
        "1",
    )

    assert result.exit_code == 1
    _assert_stderr_only(
        result, "max_bound policy rejected query_bound=2 with max_bound=1"
    )


@pytest.mark.parametrize(
    ("query_text", "message"),
    [
        ("check reach <= 1 true;", "Failed to compile BMC query"),
        ('check reach <= 1: active("Missing");', "unknown_state"),
    ],
)
def test_bmc_query_parse_and_binding_errors_are_controlled(
    bmc_files, query_text: str, message: str
) -> None:
    """Malformed text and invalid model references remain concise user errors."""
    model_path, query = bmc_files
    query_path = query(query_text)

    result = _run("-i", str(model_path), "-q", str(query_path))

    assert result.exit_code == 1
    _assert_stderr_only(result, message)
    assert "Unexpected error found" not in _stderr_text(result)


def test_bmc_missing_output_parent_is_controlled(bmc_files) -> None:
    """Atomic output creation does not create missing parent directories."""
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')
    output_path = model_path.parent / "missing" / "result.json"

    result = _run(
        "-i",
        str(model_path),
        "-q",
        str(query_path),
        "--json",
        "-o",
        str(output_path),
    )

    assert result.exit_code == 1
    _assert_stderr_only(result, "Failed to write BMC output file")
    assert not output_path.parent.exists()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (UnicodeDecodeError("utf-8", b"x", 0, 1, "bad"), "decode BMC query"),
        (PermissionError("denied"), "read BMC query"),
    ],
)
def test_bmc_query_read_errors_are_controlled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    message: str,
) -> None:
    """Query decoding and filesystem failures become concise CLI errors."""
    import pyfcstm.entry.bmc as bmc_entry

    query_path = tmp_path / "query.fbmcq"
    query_path.write_bytes(b"x")

    def fail_decode(data):
        raise error

    monkeypatch.setattr(bmc_entry, "auto_decode", fail_decode)
    with pytest.raises(ClickErrorException, match=message):
        bmc_entry._read_query_file(str(query_path))


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (FileNotFoundError("missing"), "Input DSL file not found"),
        (UnicodeDecodeError("utf-8", b"x", 0, 1, "bad"), "decode FCSTM model"),
        (GrammarParseError([]), "parse FCSTM model"),
        (ModelValidationError(message="bad model"), "Invalid FCSTM model"),
        (PermissionError("denied"), "read FCSTM model"),
    ],
)
def test_bmc_model_load_errors_are_controlled(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    message: str,
) -> None:
    """Import-aware loader failures retain a precise user-facing category."""
    import pyfcstm.entry.bmc as bmc_entry

    def fail_load(path):
        raise error

    monkeypatch.setattr(bmc_entry, "load_state_machine_from_file", fail_load)
    with pytest.raises(ClickErrorException, match=message):
        bmc_entry._load_model("machine.fcstm")


def test_bmc_internal_compile_and_solve_errors_keep_internal_identity(
    bmc_files, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Internal compile and solve guards are never downgraded to input errors."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    def fail_compile(model, query_text, *, options=None):
        raise BmcBuildError("forged compile invariant failure")

    monkeypatch.setattr(bmc_entry, "_compile_bmc_query", fail_compile)
    result = _run("-i", str(model_path), "-q", str(query_path))
    assert result.exit_code == 1
    assert "forged compile invariant failure" in _stderr_text(result)
    assert "Unexpected error found when running pyfcstm!" in _stderr_text(result)

    monkeypatch.undo()

    def fail_solve(formula, *, timeout_ms=None):
        raise BmcBuildError("solver bundle is inconsistent")

    monkeypatch.setattr(bmc_entry, "_solve_bmc_property", fail_solve)
    result = _run("-i", str(model_path), "-q", str(query_path))
    assert result.exit_code == 1
    assert "solver bundle is inconsistent" in _stderr_text(result)


def test_atomic_writer_reports_replace_and_cleanup_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Atomic output failures remove temporary files or expose cleanup errors."""
    import pyfcstm.entry.bmc as bmc_entry

    target = tmp_path / "result.txt"

    def fail_replace(source, destination):
        raise OSError("replace denied")

    monkeypatch.setattr(bmc_entry.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace denied"):
        bmc_entry.write_bmc_output(str(target), "payload\n")
    assert not list(tmp_path.glob(".result.txt.*.tmp"))

    def missing_unlink(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(bmc_entry.os, "unlink", missing_unlink)
    with pytest.raises(OSError, match="replace denied"):
        bmc_entry.write_bmc_output(str(target), "payload\n")

    def fail_unlink(path):
        raise OSError("cleanup denied")

    monkeypatch.setattr(bmc_entry.os, "unlink", fail_unlink)
    with pytest.raises(OSError, match="additionally failed.*cleanup denied"):
        bmc_entry.write_bmc_output(str(target), "payload\n")


def test_human_formatter_covers_event_call_and_diagnostic_edges(
    tmp_path: Path,
) -> None:
    """Compact human rendering covers event/call previews and rare diagnostics."""
    import pyfcstm.entry.bmc as bmc_entry
    from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
    from pyfcstm.bmc.witness import BmcSolveResult
    from pyfcstm.model import load_state_machine_from_text

    model_path = tmp_path / "calls.fcstm"
    model_path.write_text(
        """def int x = 0;
state Root {
    event Go;
    state Idle { during abstract Tick; }
    state Done;
    [*] -> Idle;
    Idle -> Done : Go;
}
""",
        encoding="utf-8",
    )
    query_path = tmp_path / "calls.fbmcq"
    query_path.write_text(
        """init state("Root.Idle");
check reach <= 1:
    called("Root.Idle.Tick", step=0, role="leaf_during", where x == 0)
    && call_count("Root.Idle.Tick", step=*) == 1;
""",
        encoding="utf-8",
    )
    result = _run("-i", str(model_path), "-q", str(query_path))
    assert "calls=Root.Idle.Tick" in result.stdout

    event_query = tmp_path / "event.fbmcq"
    event_query.write_text(
        """init state("Root.Idle");
assume event("Root.Go", 0) == true;
check reach <= 1: active("Root.Done");
""",
        encoding="utf-8",
    )
    result = _run("-i", str(model_path), "-q", str(event_query))
    assert "events=Root.Go" in result.stdout

    assert bmc_entry._human_compact_values(("a", "b", "c", "d")) == ("a,b,c,+1 more")
    unknown_witness = SimpleNamespace(
        frames=(SimpleNamespace(state=None, sentinel=None),)
    )
    assert bmc_entry._human_frame_label(unknown_witness, 0) == "unknown"

    assert "\x1b[33m" in bmc_entry._colorize_human_report(
        "BMC response <= 1: PROPERTY INCONCLUSIVE; RESPONSE HORIZON INCOMPLETE\n"
        "Scenario: FEASIBLE\n",
        "yellow",
    )
    assert "\x1b[31m" in bmc_entry._colorize_human_report(
        "BMC reach <= 1: NO WITNESS WITHIN BOUND\nScenario: FEASIBLE\n",
        "red",
    )

    model = load_state_machine_from_text("state Root;")
    prepared = BmcEngine(model).prepare(
        "check response <= 1: trigger true -> within 2 false;"
    )
    formula = compile_bmc_property(build_bmc_core_formula(prepared))
    solve_result = BmcSolveResult(
        formula,
        "unsat",
        incomplete_status="unknown",
        incomplete_elapsed_ms=1.0,
        incomplete_reason="incomplete",
        feasibility=BmcFeasibilityResult(
            BmcFeasibilityCheck("sat", "inferred"),
            BmcFeasibilityCheck("sat", "inferred"),
            BmcFeasibilityCheck("sat", "checked", elapsed_ms=1.0),
            localization_status="not_needed",
        ),
        diagnostics=("custom_diagnostic=1",),
    )
    execution = bmc_entry._BmcExecution(formula, solve_result, None, None, 3)
    diagnostics = bmc_entry._human_diagnostics(execution)
    assert "Horizon reason: incomplete" in diagnostics
    assert "Diagnostic: custom_diagnostic=1" in diagnostics
