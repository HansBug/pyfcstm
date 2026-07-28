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


def test_bmc_cli_compile_preserves_query_source_path(bmc_files) -> None:
    """The file-based entry pipeline preserves FBMCQ provenance metadata."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query(
        'init state("Root") where true;\ncheck reach <= 1: active("Root");'
    )
    model = bmc_entry._load_model(str(model_path))

    formula = bmc_entry._compile_query(
        model,
        query_path.read_text(encoding="utf-8"),
        max_bound=None,
        query_source_path=str(query_path),
    )
    context = formula.core.context
    assert context.query_source_path == str(query_path)
    target = next(
        group
        for group in formula.core._tracked_groups
        if group.stable_id == "initial.target"
    )
    assert target.source_ref.path == context._source_registry.display_path(
        str(query_path)
    )
    assert context._source_registry.excerpt(target.source_ref) == (
        'init state("Root") where true;'
    )


def test_entry_witness_decoder_wrapper_uses_real_public_decoder(bmc_files) -> None:
    """The lazy witness wrapper decodes a real SAT model without substitution."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')
    model = bmc_entry._load_model(str(model_path))
    formula = bmc_entry._compile_query(
        model,
        query_path.read_text(encoding="utf-8"),
        max_bound=None,
        query_source_path=str(query_path),
    )
    result = bmc_entry._solve_bmc_property(formula)

    assert result.status == "sat"
    trace = bmc_entry._decode_bmc_witness(formula, result.model)
    assert trace.frames
    assert trace.steps


def test_build_bmc_output_public_helper_returns_json_report(bmc_files) -> None:
    """The public entry helper runs the real file-based BMC pipeline."""
    from pyfcstm.entry.bmc import build_bmc_output

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    output, exit_code = build_bmc_output(
        str(model_path),
        str(query_path),
        json_output=True,
    )

    payload = json.loads(output)
    assert exit_code == 0
    assert payload["input"]["model_path"] == str(model_path)
    assert payload["input"]["query_path"] == str(query_path)
    assert payload["result"]["outcome"] == "witness_found"
    assert payload["witness"] is not None
    assert payload["replay"]["ok"] is True
    assert output.endswith("\n")


@pytest.mark.parametrize(
    ("option", "value"),
    [
        pytest.param("timeout_ms", 0, id="zero-timeout"),
        pytest.param("timeout_ms", True, id="boolean-timeout"),
        pytest.param("max_bound", 0, id="zero-max-bound"),
        pytest.param("max_bound", -1, id="negative-max-bound"),
    ],
)
def test_build_bmc_output_rejects_invalid_public_limits(
    bmc_files, option: str, value: object
) -> None:
    """Public BMC limits reject invalid values before pipeline execution."""
    from pyfcstm.entry.bmc import build_bmc_output

    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    with pytest.raises(ClickErrorException, match=option):
        build_bmc_output(
            str(model_path),
            str(query_path),
            **{option: value},
        )


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
    assert result.stdout.startswith(
        "BMC reach <= 1: PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND\n"
    )
    assert "Scenario: FEASIBLE" in result.stdout
    assert "Property verdict: SATISFIED WITHIN BOUND (WITNESS FOUND)" in result.stdout
    assert (
        "Semantic interpretation: A satisfying witness execution exists within "
        "the bound; this is existential evidence, not a universal guarantee."
    ) in result.stdout
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
            "BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS",
            (
                "Scenario: FEASIBLE",
                "Property verdict: NOT SATISFIED WITHIN BOUND (NO WITNESS)",
                "Primary search: WITNESS = UNSAT",
                "Semantic interpretation: The witness objective is unsatisfiable "
                "over the feasible bounded scenario; no satisfying execution "
                "exists within the bound.",
                "Conclusion: No admissible execution satisfies the reach objective "
                "within 1 macro-step.",
            ),
        ),
        (
            'check forbid <= 1: active("Root");',
            "BMC forbid <= 1: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND",
            (
                "Scenario: FEASIBLE",
                "Property verdict: NOT SATISFIED WITHIN BOUND (COUNTEREXAMPLE FOUND)",
                "Primary search: COUNTEREXAMPLE = SAT",
                "Semantic interpretation: A counterexample execution exists within "
                "the bound; the property is not satisfied there.",
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
                "Property verdict: SATISFIED WITHIN BOUND (NO COUNTEREXAMPLE)",
                "Primary search: COUNTEREXAMPLE = UNSAT",
                "Semantic interpretation: The counterexample objective is "
                "unsatisfiable over the feasible bounded scenario; every "
                "admissible execution within the bound satisfies the property.",
                "Conclusion: Every admissible execution within 1 macro-step satisfies "
                "the forbid property.",
            ),
        ),
        (
            "check response <= 1: trigger true -> within 2 false;",
            "BMC response <= 1: PROPERTY INCONCLUSIVE; RESPONSE HORIZON INCOMPLETE",
            (
                "Scenario: FEASIBLE",
                "Property verdict: INCONCLUSIVE (RESPONSE HORIZON INCOMPLETE)",
                "Primary search: COUNTEREXAMPLE = UNSAT",
                "Semantic interpretation: A feasible prefix leaves a response "
                "obligation beyond the bound; neither satisfaction nor violation "
                "can be established.",
                "Response horizon: OPEN",
                "Horizon reason: response obligation remains open beyond the current bounded horizon.",
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
            "PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND",
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
    assert (
        "Semantic interpretation: Scenario feasibility is unknown; the primary "
        "UNSAT result cannot establish a property conclusion."
    ) in unknown.stdout
    assert "Scenario: UNKNOWN" in unknown.stdout
    assert (
        "Property verdict: NOT EVALUATED (SCENARIO FEASIBILITY UNKNOWN)"
        in unknown.stdout
    )
    assert "Feasibility stage: ASSUMPTIONS" in unknown.stdout
    assert "Feasibility status: UNKNOWN" in unknown.stdout
    assert "Feasibility reason: incomplete" in unknown.stdout

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
    assert (
        "Semantic interpretation: Scenario feasibility was not resolved because "
        "the feasibility check timed out; the primary UNSAT result cannot "
        "establish a property conclusion."
    ) in timed_out.stdout
    assert "Scenario: TIMED OUT" in timed_out.stdout
    assert (
        "Property verdict: NOT EVALUATED (SCENARIO FEASIBILITY TIMED OUT)"
        in timed_out.stdout
    )
    assert "Feasibility stage: ASSUMPTIONS" in timed_out.stdout
    assert "Feasibility status: TIMED OUT" in timed_out.stdout
    assert "Feasibility reason: timeout" in timed_out.stdout

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
    assert "SCENARIO FEASIBILITY NOT CHECKED; PROPERTY NOT EVALUATED" in (
        unchecked.stdout
    )
    assert "Scenario: NOT CHECKED" in unchecked.stdout
    assert (
        "Semantic interpretation: Scenario feasibility was not checked because "
        "the shared budget was exhausted first; the primary UNSAT result cannot "
        "establish a property conclusion."
    ) in unchecked.stdout
    assert (
        "Property verdict: NOT EVALUATED (SCENARIO FEASIBILITY NOT CHECKED)"
        in unchecked.stdout
    )
    assert "Feasibility stage: ASSUMPTIONS (NOT CHECKED)" in unchecked.stdout
    assert (
        "Feasibility reason: shared timeout budget exhausted before assumptions check."
        in unchecked.stdout
    )


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
    assert (
        "Semantic interpretation: The scenario constraints are unsatisfiable; "
        "no admissible execution exists, so the property was not evaluated."
    ) in result.stdout
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
    assert presentation.property_verdict == "INCONCLUSIVE (RESPONSE HORIZON INCOMPLETE)"
    assert "response horizon check was disabled" in presentation.conclusion


def test_bmc_human_color_is_terminal_only(bmc_files) -> None:
    """ANSI decoration is explicit for terminals and absent from JSON/files."""
    model_path, query = bmc_files
    query_path = query('check reach <= 1: active("Root");')

    colored = _run("-i", str(model_path), "-q", str(query_path), "--color", "always")
    assert "\x1b[" in colored.stdout
    assert "PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND" in colored.stdout

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

    human = _run("-i", str(model_path), "-q", str(query_path), "--color", "never")
    assert human.exit_code == 4
    assert "EVIDENCE/REPLAY MISMATCH; RESULT UNTRUSTED" in human.stdout
    assert "Property verdict: INCONCLUSIVE (EVIDENCE/REPLAY MISMATCH)" in human.stdout
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


def test_bmc_incomplete_suffix_internal_error_keeps_traceback(
    bmc_files, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A suffix witness consistency failure remains an internal CLI error."""
    import pyfcstm.entry.bmc as bmc_entry

    model_path, query = bmc_files
    query_path = query("check response <= 1: trigger true -> within 2 false;")

    def fail_suffix_decode(result, *, source):
        assert source == "incomplete_suffix"
        raise BmcBuildError("forged incomplete suffix consistency failure")

    monkeypatch.setattr(bmc_entry, "_decode_bmc_result_trace", fail_suffix_decode)
    result = _run("-i", str(model_path), "-q", str(query_path), "--json")

    assert result.exit_code == 1
    _assert_stderr_only(result, "Unexpected error found when running pyfcstm!")
    assert "forged incomplete suffix consistency failure" in _stderr_text(result)


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

    def fail_compile(model, query_text, *, options=None, query_source_path=None):
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
        "BMC reach <= 1: GOAL UNREALIZABLE WITHIN BOUND; NO WITNESS\nScenario: FEASIBLE\n",
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


def test_bmc_human_color_rejects_unknown_severity() -> None:
    """The human formatter rejects severities outside the CLI color contract."""
    import pyfcstm.entry.bmc as bmc_entry

    with pytest.raises(
        bmc_entry._BmcCliInternalError, match="Unsupported human report severity"
    ):
        bmc_entry._colorize_human_report("BMC report\n", "purple")


_EXPLAIN_MODEL = """def int x = 0;
state Root {
    event Go;
    state A;
    state B;
    [*] -> A;
    A -> B :: Go;
}
"""

_EXPLAIN_QUERY = """init state("Root.A") where x == 0;
assume at 0: var("x") == 1;
assume at 0: var("x") == 2;
check reach <= 2: active("Root.B");
"""


@pytest.fixture()
def explain_files(tmp_path):
    """Write one model and one self-conflicting query to disk."""
    model = tmp_path / "machine.fcstm"
    query = tmp_path / "scenario.fbmcq"
    model.write_text(_EXPLAIN_MODEL, encoding="utf-8")
    query.write_text(_EXPLAIN_QUERY, encoding="utf-8")
    return str(model), str(query)


@pytest.mark.unittest
def test_build_bmc_output_default_publishes_no_explanation(explain_files):
    """The file helper keeps its previous behaviour unless asked otherwise."""
    from pyfcstm.entry.bmc import build_bmc_output

    model, query = explain_files

    text, exit_code = build_bmc_output(model, query, json_output=True)
    payload = json.loads(text)
    feasibility = payload["result"]["feasibility"]

    assert exit_code == 3
    assert feasibility["infeasible_stage"] == "assumptions"
    assert feasibility["explanation"] is None
    assert feasibility["refinement_status"] == "not_requested"
    assert feasibility["refinement_checks"] == []


@pytest.mark.unittest
def test_build_bmc_output_can_publish_a_source_mapped_explanation(explain_files):
    """Asking for an explanation reaches JSON with the authored lines in it."""
    from pyfcstm.entry.bmc import build_bmc_output

    model, query = explain_files

    text, exit_code = build_bmc_output(
        model, query, json_output=True, infeasibility_explanation="formal"
    )
    payload = json.loads(text)
    feasibility = payload["result"]["feasibility"]
    explanation = feasibility["explanation"]

    assert exit_code == 3
    assert explanation["classification"] == "assumptions_self_conflict"
    assert explanation["achieved_mode"] == "formal"
    assert explanation["core"]["scope"] == "assumptions_component"
    assert [item["source_excerpt"] for item in explanation["core"]["items"]] == [
        'assume at 0: var("x") == 1;',
        'assume at 0: var("x") == 2;',
    ]
    assert feasibility["refinement_status"] == explanation["status"]
    assert feasibility["refinement_checks"]

    schema = json.loads(
        Path("docs/source/reference/bmc_results/bmc_cli.schema.json").read_text(
            encoding="utf-8"
        )
    )
    _assert_bmc_schema_instance(schema, payload)


@pytest.mark.unittest
@pytest.mark.parametrize("mode", ["FORMAL", "formal ", "", "subset", True, None])
def test_build_bmc_output_rejects_unknown_explanation_modes(explain_files, mode):
    """A bad depth is an argument error, not an internal failure."""
    from pyfcstm.entry.bmc import build_bmc_output

    model, query = explain_files

    with pytest.raises(ClickErrorException, match="infeasibility_explanation"):
        build_bmc_output(model, query, infeasibility_explanation=mode)


@pytest.mark.unittest
def test_bmc_cli_can_request_each_explanation_depth(explain_files) -> None:
    """The three frozen depths are reachable from the command line.

    The helper behind the command has accepted a depth for several rounds, but
    the option itself was missing, so the capability existed with no user entry
    point -- and the frozen contract asks for the three modes to be published
    together across the API, the CLI and the JSON.
    """
    model, query = explain_files

    result, payload = _json_result(
        Path(model), Path(query), "--explain-infeasibility", "formal"
    )
    explanation = payload["result"]["feasibility"]["explanation"]

    assert result.exit_code == 3
    assert explanation["classification"] == "assumptions_self_conflict"
    assert explanation["core"]["scope"] == "assumptions_component"
    assert [item["source_excerpt"] for item in explanation["core"]["items"]] == [
        'assume at 0: var("x") == 1;',
        'assume at 0: var("x") == 2;',
    ]

    # The default stays exactly as it was, with no explanation at all.
    default_result, default_payload = _json_result(Path(model), Path(query))
    default_feasibility = default_payload["result"]["feasibility"]
    assert default_result.exit_code == 3
    assert default_feasibility["explanation"] is None
    assert default_feasibility["refinement_status"] == "not_requested"

    # Spelling the default explicitly must agree with omitting it.
    explicit_result, explicit_payload = _json_result(
        Path(model), Path(query), "--explain-infeasibility", "none"
    )
    assert explicit_result.exit_code == default_result.exit_code
    assert explicit_payload["result"]["feasibility"]["explanation"] is None

    # An unknown depth is refused by the option, before any solving happens.
    rejected = _run(
        "-i", str(model), "-q", str(query), "--explain-infeasibility", "bogus"
    )
    assert rejected.exit_code != 0
    assert "is not one of" in rejected.output


@pytest.mark.unittest
def test_bmc_human_output_shows_the_explanation_it_paid_for(explain_files) -> None:
    """A human reader must see the explanation their request produced.

    Requesting ``formal`` costs extra solver work.  Before this, the human report
    was byte-identical to the default, so the option looked like it had done
    nothing at all -- while the frozen terminal transcripts spell out the lines
    this report has to carry.
    """
    model, query = explain_files

    default = _run("-i", str(model), "-q", str(query))
    formal = _run(
        "-i", str(model), "-q", str(query), "--explain-infeasibility", "formal"
    )

    assert default.exit_code == formal.exit_code == 3
    assert "Explanation:" not in default.output
    assert "Explanation: PARTIAL FORMAL DOMAIN EXPLANATION" in formal.output
    assert (
        "Classification: the assumptions are internally inconsistent" in formal.output
    )
    assert "Conflict constraints:" in formal.output
    # The authored source location and text, not a paraphrase.
    assert 'assume at 0: var("x") == 1;' in formal.output
    assert "Core scope: assumptions_component" in formal.output
    assert "Reduction: raw" in formal.output
    assert (
        "The displayed core is sufficient for UNSAT but is not proven "
        "subset-minimal." in formal.output
    )
    # The mandatory verdict is untouched.
    for line in default.output.splitlines():
        if line.startswith(("BMC ", "Scenario:", "Property verdict:")):
            assert line in formal.output

    # Files and JSON stay ANSI-free, and JSON keeps carrying the same data.
    assert "\x1b[" not in formal.output
    _, payload = _json_result(
        Path(model), Path(query), "--explain-infeasibility", "formal"
    )
    explanation = payload["result"]["feasibility"]["explanation"]
    assert explanation["core"]["scope"] == "assumptions_component"


@pytest.mark.unittest
def test_human_explanation_renders_every_published_shape() -> None:
    """Each branch of the human explanation section, driven directly.

    The renderer has to cope with a core member that carries no span, one that is
    generated rather than authored, a proven-minimal core, and a classification
    published with no core at all -- the last being the frozen "not achieved"
    transcript.  Only the first of those is reachable from the fixtures above.
    """
    from dataclasses import dataclass

    from pyfcstm.bmc.explanation import (
        BmcConflictCore,
        BmcConstraintRef,
        BmcCoreItem,
        BmcInfeasibilityExplanation,
    )
    from pyfcstm.bmc.provenance import BmcSourceRef
    from pyfcstm.entry.bmc import _human_explanation

    def item(source, excerpt=None, human_text="frame assumption"):
        reference = BmcConstraintRef(
            "assumption.0000.frame.0000",
            "assumptions",
            "assumption.frame",
            source,
            "frame assumption",
        )
        return BmcCoreItem(
            reference,
            "assumption",
            excerpt,
            False,
            {"kind": "structural_constraint"},
            human_text,
            source.kind in ("fcstm", "fbmcq"),
        )

    def core(items, **kwargs):
        payload = dict(
            scope="assumptions_component",
            formula_summary="ENV_N",
            granularity="source_group",
            reduction="raw",
            subset_minimality="not_proven",
            items=items,
        )
        payload.update(kwargs)
        return BmcConflictCore(**payload)

    @dataclass
    class _Feasibility:
        explanation: object

    @dataclass
    class _Result:
        feasibility: object

    @dataclass
    class _Execution:
        result: object

    def render(explanation):
        return _human_explanation(_Execution(_Result(_Feasibility(explanation))))

    # A path with no span falls back to the path alone.
    anchored = BmcSourceRef("fbmcq", "q.fbmcq", None)
    lines = render(
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "assumptions_self_conflict",
            core=core((item(anchored, excerpt=None),)),
            reason="minimization skipped",
        )
    )
    assert "  1. q.fbmcq" in lines
    assert "     frame assumption" in lines

    # An authored constraint whose origin was never named is still authored.
    # Calling it generated would attribute the user's own constraint to the
    # encoder, which the frozen contract forbids -- and a programmatic query
    # reaches this shape without anything hostile involved.
    for kind in ("fbmcq", "fcstm"):
        unnamed = BmcSourceRef(kind, None, None)
        lines = render(
            BmcInfeasibilityExplanation(
                "formal",
                "formal",
                "partial",
                "assumptions_self_conflict",
                core=core((item(unnamed),)),
                reason="minimization skipped",
            )
        )
        # Both the generated and the location-less authored branch read
        # the noun from one predicate, so neither can leak the dotted
        # category while the other is clean.
        assert (
            "  1. %s assumption constraint (source location unavailable)" % kind
            in lines
        )
        assert not any("assumption.frame" in line for line in lines)
        assert not any("generated" in line for line in lines)

    # A generated constraint has no authored location at all.
    generated = BmcSourceRef("generated", None, None)
    lines = render(
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "assumptions_self_conflict",
            core=core((item(generated),)),
            reason="minimization skipped",
        )
    )
    # A generated group is named by the leading segment of its category plus the
    # word "constraint", on one line of its own.
    assert "  1. generated assumption constraint" in lines
    assert not any("assumption.frame" in line for line in lines)

    # A proven-minimal core says so instead of hedging.
    lines = render(
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "assumptions_self_conflict",
            core=core(
                (item(generated),),
                reduction="subset_minimal",
                subset_minimality="proven",
            ),
            reason="narrative not built",
        )
    )
    # The whole sentence, not a substring: asserting only "proven
    # subset-minimal" is immune to the claim being inverted to "sufficient for
    # SAT", which would tell the reader the opposite of the truth.
    assert (
        "The displayed core is sufficient for UNSAT and proven subset-minimal." in lines
    )

    # A classification with no core is the frozen "not achieved" transcript.
    lines = render(
        BmcInfeasibilityExplanation(
            "formal",
            "none",
            "partial",
            "initialization_self_conflict",
            reason="the source-level core check timed out after classification",
        )
    )
    assert "Explanation: FORMAL EXPLANATION NOT ACHIEVED" in lines
    assert "Classification: initialization is internally inconsistent" in lines
    assert any("No conflict core or causal chain" in line for line in lines)

    # The frozen contract forbids hiding a necessary member's position: a
    # generated support group has to appear together with its frame/step/refs
    # rather than being tidied away, and the transcript prints the position
    # inline after the location.
    positioned = BmcConstraintRef(
        "transition.0000",
        "kernel",
        "transition.step",
        generated,
        "transition relation",
        steps=(0,),
        refs={"step": 0, "kind": "state"},
    )
    lines = render(
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "kernel_conflict",
            core=core(
                (
                    BmcCoreItem(
                        positioned,
                        "transition_rule",
                        None,
                        False,
                        {"kind": "structural_constraint"},
                        "transition relation",
                        False,
                    ),
                ),
                scope="kernel",
            ),
            reason="minimization skipped",
        )
    )
    # This is the one shape a published transcript pins verbatim.
    assert "  1. generated transition constraint at step 0" in lines
    assert "     kind state" in lines

    # Frames, plural positions and index keys that are already inline.
    multi = BmcConstraintRef(
        "assumption.0000",
        "assumptions",
        "assumption.frame",
        generated,
        "frame assumption",
        frames=(0, 1),
        steps=(2,),
        refs={"frame": 0, "assumption": 3},
    )
    lines = render(
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "assumptions_self_conflict",
            core=core(
                (
                    BmcCoreItem(
                        multi,
                        "assumption",
                        None,
                        False,
                        {"kind": "structural_constraint"},
                        "frame assumption",
                        False,
                    ),
                )
            ),
            reason="minimization skipped",
        )
    )
    assert "  1. generated assumption constraint at frames 0, 1 and step 2" in lines
    assert "     assumption 3" in lines
    # ``frame`` is already shown inline, so it is not repeated below.
    assert not any(line.strip().startswith("frame 0") for line in lines)

    # Every classification phrase is exercised, so changing any one of them
    # fails here rather than only the one the fixtures happen to produce.
    from pyfcstm.bmc.explanation import (
        CLASSIFICATION_PHRASES,
        CLASSIFICATION_SCOPES,
    )

    assert set(CLASSIFICATION_PHRASES) == set(CLASSIFICATION_SCOPES)
    expected_phrases = {
        "kernel_conflict": "the model's own domain and transition rules conflict",
        "initialization_self_conflict": "initialization is internally inconsistent",
        "initialization_domain_conflict": (
            "initialization conflicts with the frame domain"
        ),
        "initialization_kernel_conflict": (
            "initialization conflicts with the transition relation"
        ),
        "assumptions_self_conflict": "the assumptions are internally inconsistent",
        "assumptions_domain_conflict": (
            "the assumptions conflict with the frame domain"
        ),
        "assumptions_prefix_conflict": "assumptions conflict with the feasible prefix",
    }
    assert CLASSIFICATION_PHRASES == expected_phrases
    for classification, phrase in expected_phrases.items():
        rendered = render(
            BmcInfeasibilityExplanation(
                "formal",
                "none",
                "partial",
                classification,
                reason="probe unknown",
            )
        )
        assert "Classification: %s" % phrase in rendered

    # No explanation at all renders nothing.
    assert render(None) == []


@pytest.mark.unittest
def test_human_explanation_matches_the_frozen_transcript_line_shapes() -> None:
    """Compare each rendered line against the frozen transcript line it mirrors.

    The published conflict-constraint block gives an authored member exactly two
    lines -- location then its own text, with no position suffix and no builder
    metadata -- while a generated member occupies exactly one.  The not-achieved
    transcript ends with two physical lines, not one long one.
    Substring checks pass on all of those even when the shape is wrong, so the
    frozen lines are transcribed here and compared whole.
    """
    from dataclasses import dataclass

    from pyfcstm.bmc.explanation import (
        BmcConflictCore,
        BmcConstraintRef,
        BmcCoreItem,
        BmcInfeasibilityExplanation,
    )
    from pyfcstm.bmc.provenance import BmcSourceRef
    from pyfcstm.entry.bmc import _human_explanation
    from pyfcstm.utils.validate import Span

    # Transcribed from the published transcript.  Each entry is one line
    # with its ordinal dropped: an authored member contributes a location line
    # and its own text, a generated member contributes a single line.
    #
    # The ordinals are not transcribed.  Core items are published in stable_id
    # order -- sorted where the core is built, in BmcConflictCore's own
    # constructor, not here -- and this renderer prints the published order as it
    # receives it.  The sort is asserted directly in test/bmc/test_explanation.py,
    # so a reader can check the claim without leaving the test tree.  The sample's own in-block
    # order differs from that; where a requirement and an illustrative sample
    # conflict, the requirement governs.  The requirement is the extraction step
    # that sorts by stable_id before the core enters the public API and keeps
    # Z3's own order out of it, restated in the determinism section as core items
    # being published in stable id order.
    #
    # Nothing is claimed here about which orderings the two samples do or do not
    # admit.  Five versions of this comment tried to make such a claim and all
    # five were wrong: no-deterministic-order-exists (refuted by ordering on
    # source position), undecidable (the requirement decides it), neither-sample-
    # follows-role-order (the proven-minimal one does), and excludes-any-single-
    # ordering (refuted by "authored before generated, then by path and line").
    # The claim was never needed for the conclusion, so it is gone rather than
    # narrowed again.
    partial_core_transcript_shapes = [
        ("machine.fcstm:1:1-1:15", "persistent initializer: x = 0"),
        ("query.fbmcq:2:1-2:23", "assume at 0: x == 1;"),
        ("generated transition constraint at step 0", None),
    ]
    # Transcribed from the not-achieved transcript, including its line break.
    not_achieved_transcript_tail = [
        "No conflict core or causal chain was published. The classification is "
        "retained",
        "as partial metadata, but it is not presented as a completed formal "
        "explanation.",
    ]

    @dataclass
    class _Feasibility:
        explanation: object

    @dataclass
    class _Result:
        feasibility: object

    @dataclass
    class _Execution:
        result: object

    def render(explanation):
        return _human_explanation(_Execution(_Result(_Feasibility(explanation))))

    def authored(path, span, category, stage, role, excerpt, refs):
        reference = BmcConstraintRef(
            "%s.0000" % category,
            stage,
            category,
            BmcSourceRef("fcstm" if path.endswith(".fcstm") else "fbmcq", path, span),
            "authored constraint",
            # A real builder populates the positional tuple as well as ``refs``,
            # so the fixture does too: without it the renderer would have no
            # position to print and "no position suffix on an authored member"
            # would be asserted against a member that has no position at all.
            frames=(refs["frame"],),
            refs=refs,
        )
        return BmcCoreItem(
            reference,
            role,
            excerpt,
            False,
            {"kind": "structural_constraint"},
            "authored constraint",
            True,
        )

    generated_item = BmcCoreItem(
        BmcConstraintRef(
            "transition.step.0000",
            "kernel",
            "transition.step",
            BmcSourceRef("generated", None, None),
            "transition rule constraint",
            steps=(0,),
            refs={"step": 0},
        ),
        "transition_rule",
        None,
        False,
        {"kind": "structural_constraint"},
        "transition rule constraint, generated from the model",
        False,
    )

    core = BmcConflictCore(
        "assumptions_prefix",
        "S_assume restricted to the conflicting groups",
        "source_group",
        "partial_minimized",
        "not_proven",
        (
            authored(
                "machine.fcstm",
                Span(1, 1, 1, 15),
                "initial.variable",
                "initialization",
                "initial_fact",
                "persistent initializer: x = 0",
                {"frame": 0, "variable": "x"},
            ),
            authored(
                "query.fbmcq",
                Span(2, 1, 2, 23),
                "assumption.frame",
                "assumptions",
                "assumption",
                "assume at 0: x == 1;",
                {"assumption": 0, "frame": 0},
            ),
            generated_item,
        ),
    )
    lines = render(
        BmcInfeasibilityExplanation(
            "formal",
            "formal",
            "partial",
            "assumptions_prefix_conflict",
            core=core,
            reason="shared timeout budget exhausted during minimization",
        )
    )
    # A not-yet-minimal core reports scope, reduction and the reason its
    # reduction stopped, and nothing else.  Granularity, member count, a labelled
    # minimality line and the elapsed time belong to the proven-minimal shape,
    # which in turn reports no reduction at all -- the two shapes publish
    # different field sets rather than one extending the other.  An earlier
    # version of this test asserted the minimal shape's fields here, which locked
    # in three lines the not-yet-minimal transcript does not have.
    scope_at = lines.index("Core scope: assumptions_prefix")
    assert lines[scope_at + 1] == "Reduction: partial_minimized"
    assert not any(line.startswith("Core granularity:") for line in lines)
    assert not any(line.startswith("Core size:") for line in lines)
    assert not any(line.startswith("Semantic roles:") for line in lines)
    assert not any(line.startswith("Subset minimality:") for line in lines)
    assert not any(line.startswith("Explanation time:") for line in lines)

    start = lines.index("Conflict constraints:")
    block = lines[start + 1 : lines.index("", start + 1)]
    # Rebuild the block from the frozen shapes in the order the published core
    # actually uses, then compare whole lines.  A wrong shape -- an internal
    # dotted category, a position suffix on an authored member, a leaked
    # stable_id -- changes one of these strings and fails here.
    by_first_line = {shape[0]: shape for shape in partial_core_transcript_shapes}
    expected = []
    ordinal = 0
    for first_line in (
        "query.fbmcq:2:1-2:23",
        "machine.fcstm:1:1-1:15",
        "generated transition constraint at step 0",
    ):
        ordinal += 1
        head, detail = by_first_line[first_line]
        expected.append("  %d. %s" % (ordinal, head))
        if detail is not None:
            expected.append("     %s" % detail)
    assert block == expected
    assert not any("variable x" in line for line in lines)
    assert not any("assumption 0" in line for line in lines)
    assert not any("at frame 0" in line for line in lines)

    degraded = render(
        BmcInfeasibilityExplanation(
            "formal",
            "none",
            "partial",
            "initialization_self_conflict",
            reason="the source-level core check timed out after classification",
        )
    )
    # The whole block, not just its tail.  Pinning only the last two lines left
    # the header unguarded, so a stray line between the headline and the
    # classification -- for instance an unconditional depth line -- passed.
    assert (
        degraded
        == [
            "Explanation: FORMAL EXPLANATION NOT ACHIEVED",
            "Classification: initialization is internally inconsistent",
            "Reason: the source-level core check timed out after classification",
            "",
        ]
        + not_achieved_transcript_tail
    )

    # The depth line appears when a deeper request settled for a shallower
    # result, and only then.  Every mode pair the delivery matrix allows is
    # driven from the matrix itself rather than sampled: a hand-picked subset
    # leaves the condition open to widenings no sampled case contradicts, such
    # as keying it on the requested mode alone.
    from pyfcstm.bmc.explanation import _DELIVERY_SIGNATURES

    legal_pairs = sorted({(sig[0], sig[1]) for sig in _DELIVERY_SIGNATURES})
    assert legal_pairs == [
        ("formal", "formal"),
        ("formal", "none"),
        ("proof", "formal"),
        ("proof", "none"),
        ("proof", "proof"),
    ], legal_pairs

    # The decision itself is a predicate, so every pair is checked against it --
    # including the one whose object cannot be built here, because it needs a slot
    # that is named as not yet built.  Naming that pair as unconstructible and
    # skipping it left the gate open: a widening that only added that one pair
    # passed the whole suite.
    import pyfcstm.bmc.explanation as explanation_module

    from pyfcstm.bmc.explanation import (
        _DELIVERY_SIGNATURES,
        UNBUILT_SLOTS,
        depth_line_is_needed,
    )

    legal_pairs = sorted({(sig[0], sig[1]) for sig in _DELIVERY_SIGNATURES})
    assert legal_pairs == [
        ("formal", "formal"),
        ("formal", "none"),
        ("proof", "formal"),
        ("proof", "none"),
        ("proof", "proof"),
    ], legal_pairs

    assert {pair: depth_line_is_needed(*pair) for pair in legal_pairs} == {
        ("formal", "formal"): False,
        ("formal", "none"): False,
        ("proof", "formal"): True,
        ("proof", "none"): False,
        ("proof", "proof"): False,
    }

    # Every matrix row reaching an achieved "proof" also needs a proof slot, and
    # that slot is named as not yet built, so that pair has no object here.
    assert "proof" in UNBUILT_SLOTS
    needs_unbuilt_slot = {("proof", "proof")}
    assert needs_unbuilt_slot <= set(legal_pairs)
    buildable = [pair for pair in legal_pairs if pair not in needs_unbuilt_slot]

    def render_pair(requested, achieved):
        # Each pair needs a payload the matrix accepts for it: a core when a
        # depth was achieved, a bare reason when none was.
        if achieved == "none":
            extra = dict(reason="the component probe returned unknown")
        else:
            extra = dict(
                core=BmcConflictCore(
                    "initialization_component",
                    "C_init restricted to the conflicting groups",
                    "source_group",
                    "raw",
                    "not_proven",
                    (
                        authored(
                            "machine.fcstm",
                            Span(1, 1, 1, 15),
                            "initial.variable",
                            "initialization",
                            "initial_fact",
                            "persistent initializer: x = 0",
                            {"frame": 0, "variable": "x"},
                        ),
                    ),
                ),
                reason="sound source core published without a minimality proof",
            )
        return render(
            BmcInfeasibilityExplanation(
                requested,
                achieved,
                "partial",
                "initialization_self_conflict",
                **extra,
            )
        )

    def depth_lines(requested, achieved):
        return [
            line
            for line in render_pair(requested, achieved)
            if line.startswith("Explanation depth:")
        ]

    # Pinning the predicate is not enough on its own: the renderer could decide
    # for itself and the table above would still pass, because the pair the two
    # disagree on is the pair with no object.  So the wiring is pinned too, and
    # for every buildable pair rather than one of them -- checking a single pair
    # let a renderer consult the predicate for that pair and inline the decision
    # for the rest.
    real_predicate = explanation_module.depth_line_is_needed
    for requested, achieved in buildable:
        for forced in (True, False):
            try:
                explanation_module.depth_line_is_needed = (
                    lambda _requested, _achieved, value=forced: value
                )
                lines_for_pair = depth_lines(requested, achieved)
            finally:
                explanation_module.depth_line_is_needed = real_predicate
            expected_line = "Explanation depth: requested %s, achieved %s" % (
                requested,
                achieved,
            )
            assert lines_for_pair == ([expected_line] if forced else []), (
                requested,
                achieved,
                forced,
            )

    # With the real predicate back, the rendered output matches it for every
    # buildable pair.  That is as far as this can go: the renderer could keep the
    # predicate call and combine it with a copy of the decision, and the copy
    # would only ever differ on the pair that has no object, so no assertion
    # built on rendered output can reach it.  The ("proof", "proof") render path
    # is therefore not pinned until its slot exists; the predicate's value for it
    # is pinned above, and the assertion below is deliberately limited to pairs
    # the current slots allow rather than dressed up as complete coverage.
    for requested, achieved in buildable:
        expected = (
            ["Explanation depth: requested %s, achieved %s" % (requested, achieved)]
            if depth_line_is_needed(requested, achieved)
            else []
        )
        assert depth_lines(requested, achieved) == expected, (requested, achieved)
