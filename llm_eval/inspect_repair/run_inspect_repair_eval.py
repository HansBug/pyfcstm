"""
Evaluate LLM repairs guided by FCSTM inspect reports.

This maintenance script is intentionally outside the unit-test suite. It builds
isolated repair prompt packets from the official grammar guide, one broken
FCSTM fixture, and one LLM-oriented inspect report. Live mode can call local
provider CLIs; prepare and replay modes run without contacting providers.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pyfcstm.diagnostics import inspect_model  # noqa: E402
from pyfcstm.dsl.error import GrammarParseError  # noqa: E402
from pyfcstm.entry.inspect import build_inspect_output  # noqa: E402
from pyfcstm.llm import (  # noqa: E402
    get_grammar_guide_prompt_for_llm,
    get_grammar_guide_prompt_metadata_for_llm,
)
from pyfcstm.model import load_state_machine_from_file  # noqa: E402

_PROVIDERS = ("codex", "claude", "codex-deepseek")
_FORMATS = ("llm-json", "llm-md")
_FAILURE_CATEGORIES = (
    "passed",
    "prepared",
    "model-error",
    "infra-blocked",
    "guide-gap",
    "contract-gap",
)
_FCSTM_FENCE_RE = re.compile(
    r"```(?:fcstm|fcstm-valid|text)?\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)
_FCSTM_START_RE = re.compile(
    r"(?m)^\s*(?:"
    r"def\s+(?:int|float)\s+[A-Za-z_][A-Za-z0-9_]*\s*="
    r"|(?:pseudo\s+)?state\s+[A-Za-z_][A-Za-z0-9_]*"
    r"(?:\s+named\s+\"[^\"]*\")?\s*[;{]"
    r")"
)
_STATE_DECL_RE = re.compile(r"\b(?:pseudo\s+)?state\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_TRANSITION_RE = re.compile(
    r"(?:\[\*\]|[A-Za-z_][A-Za-z0-9_.]*)\s*->\s*"
    r"(?:\[\*\]|[A-Za-z_][A-Za-z0-9_.]*)"
)
_END_TRANSITION_RE = re.compile(r"->\s*\[\*\]")
_CONST_TRUE_GUARD_RE = re.compile(
    r":\s*(?:if\s*)?\[\s*(?:true|1\s*==\s*1|1\s*>\s*0|0\s*<\s*1)\s*\]"
)
_STDERR_TAIL_LIMIT = 2000


def _utc_timestamp() -> str:
    """
    Return a compact UTC timestamp.

    :return: Timestamp in ``YYYYmmddTHHMMSSZ`` form.
    :rtype: str
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_text(path: Path) -> str:
    """
    Read UTF-8 text from ``path``.

    :param path: File path.
    :type path: pathlib.Path
    :return: File content.
    :rtype: str
    :raises OSError: If reading fails.
    :raises UnicodeDecodeError: If the file is not UTF-8.
    """
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    """
    Write UTF-8 text, creating parent directories first.

    :param path: Output path.
    :type path: pathlib.Path
    :param text: Text content.
    :type text: str
    :return: ``None``.
    :rtype: None
    :raises OSError: If writing fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, data: Mapping[str, object]) -> None:
    """
    Write a JSON object with deterministic formatting.

    :param path: Output JSON path.
    :type path: pathlib.Path
    :param data: JSON-serializable mapping.
    :type data: Mapping[str, object]
    :return: ``None``.
    :rtype: None
    :raises OSError: If writing fails.
    """
    _write_text(
        path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def _repo_display_path(path: Path) -> str:
    """
    Return a repository-relative path when possible.

    :param path: Path to display in artifacts.
    :type path: pathlib.Path
    :return: Repository-relative path, or the original path when outside.
    :rtype: str
    """
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        # ValueError: caller supplied a path outside the repository tree.
        return str(path)


def _load_manifest(path: Path) -> Dict[str, object]:
    """
    Load the fixture manifest.

    :param path: Manifest JSON path.
    :type path: pathlib.Path
    :return: Parsed manifest.
    :rtype: Dict[str, object]
    :raises OSError: If reading fails.
    :raises ValueError: If the manifest is malformed.
    """
    data = json.loads(_read_text(path))
    if data.get("schema_version") != "pyfcstm.inspect_repair.fixtures.v1":
        raise ValueError("unsupported inspect repair fixture manifest schema")
    categories = data.get("failure_categories")
    if categories != list(_FAILURE_CATEGORIES):
        raise ValueError("fixture manifest failure categories do not match runner")
    fixtures = data.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("fixture manifest must contain a fixtures list")
    return data


def _select_fixtures(
    manifest: Mapping[str, object], fixture: Optional[str], smoke_only: bool
) -> List[Dict[str, object]]:
    """
    Select fixture entries from the manifest.

    :param manifest: Parsed fixture manifest.
    :type manifest: Mapping[str, object]
    :param fixture: Optional single fixture id.
    :type fixture: Optional[str]
    :param smoke_only: Whether to keep only smoke fixtures.
    :type smoke_only: bool
    :return: Selected fixture dictionaries.
    :rtype: List[Dict[str, object]]
    :raises ValueError: If the selected fixture does not exist.
    """
    fixtures = list(manifest.get("fixtures", []))
    if fixture is not None:
        selected = [item for item in fixtures if item.get("id") == fixture]
        if not selected:
            raise ValueError(f"unknown inspect repair fixture: {fixture!r}")
        return selected
    if smoke_only:
        return [item for item in fixtures if item.get("smoke") is True]
    return fixtures


def _select_values(
    value: Optional[str], allowed: Tuple[str, ...], label: str
) -> Tuple[str, ...]:
    """
    Select one value or all allowed values.

    :param value: Optional selected value.
    :type value: Optional[str]
    :param allowed: Allowed values.
    :type allowed: Tuple[str, ...]
    :param label: Human-readable value class.
    :type label: str
    :return: Selected values.
    :rtype: Tuple[str, ...]
    :raises ValueError: If ``value`` is not allowed.
    """
    if value is None:
        return allowed
    if value not in allowed:
        raise ValueError(
            f"unsupported {label} {value!r}; expected one of {', '.join(allowed)}"
        )
    return (value,)


def _artifact_dir(
    root: Path, fixture_id: str, provider: str, output_format: str
) -> Path:
    """
    Return the artifact directory for one evaluation cell.

    :param root: Artifact root.
    :type root: pathlib.Path
    :param fixture_id: Fixture id.
    :type fixture_id: str
    :param provider: Provider name.
    :type provider: str
    :param output_format: Inspect report format.
    :type output_format: str
    :return: Artifact directory.
    :rtype: pathlib.Path
    """
    return root / fixture_id / provider / output_format


def _inspect_args_for_fixture(
    fixture: Mapping[str, object], output_format: str
) -> List[str]:
    """
    Build command arguments for the inspect report.

    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param output_format: Inspect report format.
    :type output_format: str
    :return: Argument list without executable name.
    :rtype: List[str]
    """
    args = ["--format", output_format]
    if fixture.get("enable_verify"):
        args.extend(
            [
                "--enable-verify",
                "--max-complexity-tier",
                "smt_linear",
                "--smt-timeout-ms",
                "1000",
            ]
        )
    return args


def _verify_options_for_fixture(fixture: Mapping[str, object]) -> Dict[str, object]:
    """
    Return inspect verification options for one fixture.

    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :return: Keyword-style inspect options.
    :rtype: Dict[str, object]
    """
    enable_verify = bool(fixture.get("enable_verify"))
    return {
        "enable_verify": enable_verify,
        "max_complexity_tier": "smt_linear" if enable_verify else "structural",
        "smt_timeout_ms": 1000 if enable_verify else None,
    }


def _verification_command(path: Path, fixture: Mapping[str, object]) -> List[str]:
    """
    Return a reproducible command for validating one repaired source.

    :param path: Repaired source path.
    :type path: pathlib.Path
    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :return: Command arguments.
    :rtype: List[str]
    """
    args = ["pyfcstm", "inspect", "-i", _repo_display_path(path), "--format", "json"]
    if fixture.get("enable_verify"):
        args.extend(
            [
                "--enable-verify",
                "--max-complexity-tier",
                "smt_linear",
                "--smt-timeout-ms",
                "1000",
            ]
        )
    return args


def _build_inspect_report(
    fixture_path: Path, fixture: Mapping[str, object], output_format: str
) -> Tuple[str, List[str]]:
    """
    Render one LLM-oriented inspect report.

    :param fixture_path: FCSTM fixture path.
    :type fixture_path: pathlib.Path
    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param output_format: ``llm-json`` or ``llm-md``.
    :type output_format: str
    :return: Pair of rendered report text and equivalent CLI argument list.
    :rtype: Tuple[str, List[str]]
    :raises pyfcstm.entry.base.ClickErrorException: If inspect fails.
    """
    inspect_args = _inspect_args_for_fixture(fixture, output_format)
    source_path = str(fixture_path)
    display_path = _repo_display_path(fixture_path)
    options = _verify_options_for_fixture(fixture)
    report = build_inspect_output(
        source_path,
        output_format=output_format,
        enable_verify=bool(options["enable_verify"]),
        max_complexity_tier=str(options["max_complexity_tier"]),
        smt_timeout_ms=options["smt_timeout_ms"],
    )
    report = report.replace(source_path, "input.fcstm")
    return report, ["pyfcstm", "inspect", "-i", display_path, *inspect_args]


def _fill_prompt_template(
    template: str, guide: str, source: str, inspect_report: str
) -> str:
    """
    Fill the repair prompt template.

    :param template: Template text with simple placeholders.
    :type template: str
    :param guide: Official grammar guide prompt.
    :type guide: str
    :param source: FCSTM source under repair.
    :type source: str
    :param inspect_report: Rendered inspect report.
    :type inspect_report: str
    :return: Full prompt packet.
    :rtype: str
    """
    return (
        template.replace("{{ grammar_guide }}", guide)
        .replace("{{ fcstm_source }}", source)
        .replace("{{ inspect_report }}", inspect_report)
    )


def _provider_command(provider: str, output_file: Optional[Path] = None) -> List[str]:
    """
    Build a local provider command.

    :param provider: Provider name.
    :type provider: str
    :param output_file: Optional file that receives the provider's final
        response when the client supports it.
    :type output_file: Optional[pathlib.Path], optional
    :return: Command argv.
    :rtype: List[str]
    :raises ValueError: If provider is unsupported.
    """
    codex_output_args = (
        ["--output-last-message", str(output_file)] if output_file is not None else []
    )
    if provider == "codex":
        return [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--color",
            "never",
            *codex_output_args,
            "-",
        ]
    if provider == "claude":
        return ["claude", "-p"]
    if provider == "codex-deepseek":
        return [
            "codex-deepseek",
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--color",
            "never",
            *codex_output_args,
            "-",
        ]
    raise ValueError(f"unsupported provider: {provider!r}")


def _provider_version(provider: str) -> str:
    """
    Return a best-effort provider client version.

    :param provider: Provider name.
    :type provider: str
    :return: Version text, or an empty string if unavailable.
    :rtype: str
    """
    executable = _provider_command(provider)[0]
    try:
        completed = subprocess.run(
            [executable, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        # FileNotFoundError: optional provider CLI is not installed.
        # OSError: optional provider CLI exists but cannot be executed, for
        # example because of permission or platform launcher problems.
        # TimeoutExpired: provider version command hung or waited for auth.
        return ""
    return (completed.stdout or completed.stderr or "").strip()


def _run_provider(
    provider: str, prompt: str, timeout_seconds: int, cwd: Path
) -> Dict[str, object]:
    """
    Run one live provider in an isolated working directory.

    :param provider: Provider name.
    :type provider: str
    :param prompt: Full prompt packet.
    :type prompt: str
    :param timeout_seconds: Timeout in seconds.
    :type timeout_seconds: int
    :param cwd: Isolated provider working directory.
    :type cwd: pathlib.Path
    :return: Process report.
    :rtype: Dict[str, object]
    """
    response_file = cwd / "provider_response.txt"
    command = _provider_command(provider, response_file)
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            input=prompt,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except OSError as err:
        # FileNotFoundError: optional provider CLI is not installed locally.
        # OSError: optional provider CLI exists but cannot be executed, for
        # example because of permission or platform launcher problems.
        return {
            "success": False,
            "failure_category": "infra-blocked",
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(err),
        }
    except subprocess.TimeoutExpired as err:
        # TimeoutExpired: provider exceeded the configured live-eval limit.
        return {
            "success": False,
            "failure_category": "infra-blocked",
            "command": command,
            "returncode": None,
            "stdout": err.stdout or "",
            "stderr": err.stderr
            or f"provider timed out after {timeout_seconds} seconds",
        }
    return {
        "success": completed.returncode == 0,
        "failure_category": "passed" if completed.returncode == 0 else "infra-blocked",
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "response_text": _read_text(response_file) if response_file.is_file() else "",
    }


def _extract_fcstm_source(raw_output: str) -> str:
    """
    Extract FCSTM source from provider output.

    :param raw_output: Raw provider text.
    :type raw_output: str
    :return: Extracted FCSTM source.
    :rtype: str
    """
    for match in _FCSTM_FENCE_RE.finditer(raw_output):
        candidate = match.group(1).strip()
        if "state " in candidate:
            return candidate
    match = _FCSTM_START_RE.search(raw_output)
    if match:
        return raw_output[match.start() :].strip()
    return raw_output.strip()


def _stderr_summary(stderr: object) -> Dict[str, object]:
    """
    Return bounded stderr metadata for reports.

    :param stderr: Provider stderr payload.
    :type stderr: object
    :return: Bounded stderr summary.
    :rtype: Dict[str, object]
    """
    text = str(stderr or "")
    return {
        "provider_stderr_size": len(text),
        "provider_stderr_tail": text[-_STDERR_TAIL_LIMIT:],
    }


def _state_names(source: str) -> List[str]:
    """
    Extract declared state names from FCSTM text for repair-quality checks.

    :param source: FCSTM source text.
    :type source: str
    :return: State names in declaration order.
    :rtype: List[str]
    """
    return [match.group(1) for match in _STATE_DECL_RE.finditer(source)]


def _transition_count(source: str) -> int:
    """
    Count source-level transition arrows for coarse deletion detection.

    :param source: FCSTM source text.
    :type source: str
    :return: Number of transition-like arrows.
    :rtype: int
    """
    return len(_TRANSITION_RE.findall(source))


def _end_transition_count(source: str) -> int:
    """
    Count transitions to the final pseudo state.

    :param source: FCSTM source text.
    :type source: str
    :return: Number of transitions targeting ``[*]``.
    :rtype: int
    """
    return len(_END_TRANSITION_RE.findall(source))


def _bad_repair_flags(
    source: str, fixture: Mapping[str, object], original_source: str
) -> List[str]:
    """
    Detect obvious low-quality repair patterns.

    :param source: Repaired FCSTM source.
    :type source: str
    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param original_source: Original broken FCSTM source.
    :type original_source: str
    :return: Bad-repair flags present in the source.
    :rtype: List[str]
    """
    flags: List[str] = []
    requested = set(fixture.get("bad_repair_flags", []))
    if "dummy-assignment" in requested and re.search(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\1\s*;", source
    ):
        flags.append("dummy-assignment")
    if "guard-to-true" in requested and _CONST_TRUE_GUARD_RE.search(source):
        flags.append("guard-to-true")
    if "self-loop-mask" in requested and re.search(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*->\s*\1\b", source
    ):
        flags.append("self-loop-mask")
    if "delete-state" in requested:
        original_states = set(_state_names(original_source))
        repaired_states = set(_state_names(source))
        if original_states - repaired_states:
            flags.append("delete-state")
    if "delete-transition" in requested and _transition_count(
        source
    ) < _transition_count(original_source):
        flags.append("delete-transition")
    end_transition_delta = _end_transition_count(source) - _end_transition_count(
        original_source
    )
    transition_delta = _transition_count(source) - _transition_count(original_source)
    if (
        "unconditional-exit-stack" in requested
        and end_transition_delta > 0
        and transition_delta <= end_transition_delta
    ):
        flags.append("unconditional-exit-stack")
    return flags


def _verify_repair(
    source: str, fixture: Mapping[str, object], repaired_path: Path
) -> Dict[str, object]:
    """
    Verify repaired FCSTM source with parse/model/inspect.

    :param source: Repaired FCSTM source.
    :type source: str
    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param repaired_path: Path where the repaired source is stored.
    :type repaired_path: pathlib.Path
    :return: Verification result.
    :rtype: Dict[str, object]
    """
    verification_command = _verification_command(repaired_path, fixture)
    try:
        model = load_state_machine_from_file(str(repaired_path))
        options = _verify_options_for_fixture(fixture)
        report = inspect_model(
            model,
            enable_verify=bool(options["enable_verify"]),
            max_complexity_tier=str(options["max_complexity_tier"]),
            smt_timeout_ms=options["smt_timeout_ms"],
        )
    except (
        OSError,
        UnicodeDecodeError,
        GrammarParseError,
        SyntaxError,
        ValueError,
    ) as err:
        # OSError/UnicodeDecodeError: filesystem or decoding failure for the
        # repaired file. GrammarParseError: parser rejects the returned source.
        # SyntaxError/ValueError: model construction rejects the returned source
        # after parsing.
        return {
            "success": False,
            "failure_category": "model-error",
            "diagnostics": str(err),
            "verification_command": verification_command,
            "verification_result": {
                "passed": False,
                "error": str(err),
            },
        }

    remaining_diagnostics = [
        {"code": diagnostic.code, "severity": diagnostic.severity}
        for diagnostic in report.diagnostics
    ]
    remaining_codes = [item["code"] for item in remaining_diagnostics]
    expected_codes = set(fixture.get("expected_codes", []))
    still_present = [code for code in remaining_codes if code in expected_codes]
    blocking_diagnostics = [
        item
        for item in remaining_diagnostics
        if item["severity"] in {"error", "warning"}
    ]
    original_path = repaired_path.parent / "input.fcstm"
    original_source = _read_text(original_path) if original_path.is_file() else ""
    flags = _bad_repair_flags(source, fixture, original_source)
    success = not still_present and not blocking_diagnostics and not flags
    diagnostics_message = ""
    if not success:
        diagnostics_message = (
            "remaining expected diagnostics, blocking diagnostics, or bad repair flags"
        )
    return {
        "success": success,
        "failure_category": "passed" if success else "model-error",
        "diagnostics": diagnostics_message,
        "verification_command": verification_command,
        "verification_result": {
            "passed": success,
            "expected_codes_cleared": not still_present,
            "blocking_diagnostics_cleared": not blocking_diagnostics,
            "bad_repair_flags_cleared": not flags,
        },
        "remaining_diagnostic_codes": remaining_codes,
        "remaining_diagnostics": remaining_diagnostics,
        "blocking_diagnostics": blocking_diagnostics,
        "bad_repair_flags": flags,
    }


def _prepare_cell(
    fixture: Mapping[str, object],
    provider: str,
    output_format: str,
    args: argparse.Namespace,
) -> Dict[str, object]:
    """
    Generate inspect report and prompt packet for one cell.

    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param provider: Provider name.
    :type provider: str
    :param output_format: Inspect report format.
    :type output_format: str
    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Cell metadata.
    :rtype: Dict[str, object]
    """
    fixture_id = str(fixture["id"])
    fixture_path = args.fixtures_dir / str(fixture["path"])
    cell_dir = _artifact_dir(args.artifacts, fixture_id, provider, output_format)
    source = _read_text(fixture_path)
    inspect_report, inspect_command = _build_inspect_report(
        fixture_path, fixture, output_format
    )
    guide = get_grammar_guide_prompt_for_llm()
    guide_metadata = get_grammar_guide_prompt_metadata_for_llm()
    template = _read_text(args.prompt_template)
    prompt = _fill_prompt_template(template, guide, source, inspect_report)

    _write_text(cell_dir / "input.fcstm", source)
    _write_text(
        cell_dir / f"inspect_report.{'json' if output_format == 'llm-json' else 'md'}",
        inspect_report,
    )
    _write_text(cell_dir / "prompt_packet.md", prompt)

    metadata = {
        "fixture_id": fixture_id,
        "provider": provider,
        "format": output_format,
        "fixture_path": _repo_display_path(fixture_path),
        "guide_metadata": guide_metadata,
        "inspect_command": inspect_command,
        "artifact_dir": _repo_display_path(cell_dir),
        "expected_codes": list(fixture.get("expected_codes", [])),
        "bad_repair_flags_under_watch": list(fixture.get("bad_repair_flags", [])),
        "requires_max_tier": fixture.get("requires_max_tier"),
        "prepared_at": _utc_timestamp(),
    }
    _write_json(cell_dir / "metadata.json", metadata)
    return metadata


def _replay_metadata_cell(
    cell_dir: Path,
    fixture: Mapping[str, object],
    provider: str,
    output_format: str,
    args: argparse.Namespace,
) -> Dict[str, object]:
    """
    Load replay metadata without mutating prompt-generation evidence.

    Replay mode validates already captured provider output. It must not
    regenerate ``input.fcstm``, ``inspect_report.*``, ``prompt_packet.md``, or
    ``metadata.json`` because those files are the historical prompt snapshot
    that produced ``raw_output.md`` and ``repaired.fcstm``.

    :param cell_dir: Existing artifact cell directory.
    :type cell_dir: pathlib.Path
    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param provider: Provider name.
    :type provider: str
    :param output_format: Inspect report format.
    :type output_format: str
    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Metadata for the replay report.
    :rtype: Dict[str, object]
    :raises OSError: If reading an existing metadata file fails.
    :raises ValueError: If an existing metadata file is not a JSON object.

    Example::

        >>> from argparse import Namespace
        >>> from pathlib import Path
        >>> args = Namespace(fixtures_dir=Path("fixtures"), artifacts=Path("artifacts"))
        >>> meta = _replay_metadata_cell(Path("artifacts/demo/codex/llm-json"), {"id": "demo", "path": "demo.fcstm"}, "codex", "llm-json", args)
        >>> meta["fixture_id"]
        'demo'
    """
    metadata_path = cell_dir / "metadata.json"
    if metadata_path.is_file():
        metadata = json.loads(_read_text(metadata_path))
        if not isinstance(metadata, dict):
            raise ValueError(f"metadata file is not a JSON object: {metadata_path}")
        return metadata

    fixture_id = str(fixture["id"])
    fixture_path = args.fixtures_dir / str(fixture["path"])
    inspect_command = [
        "pyfcstm",
        "inspect",
        "-i",
        _repo_display_path(fixture_path),
        *_inspect_args_for_fixture(fixture, output_format),
    ]
    return {
        "fixture_id": fixture_id,
        "provider": provider,
        "format": output_format,
        "fixture_path": _repo_display_path(fixture_path),
        "guide_metadata": get_grammar_guide_prompt_metadata_for_llm(),
        "inspect_command": inspect_command,
        "artifact_dir": _repo_display_path(cell_dir),
        "expected_codes": list(fixture.get("expected_codes", [])),
        "bad_repair_flags_under_watch": list(fixture.get("bad_repair_flags", [])),
        "requires_max_tier": fixture.get("requires_max_tier"),
        "prepared_at": None,
    }


def _copy_isolated_inputs(cell_dir: Path, isolated_dir: Path) -> List[str]:
    """
    Copy prompt inputs into an isolated generation directory.

    :param cell_dir: Artifact cell directory.
    :type cell_dir: pathlib.Path
    :param isolated_dir: Temporary isolated directory.
    :type isolated_dir: pathlib.Path
    :return: Visible file names.
    :rtype: List[str]
    """
    visible = []
    for name in ("prompt_packet.md", "input.fcstm"):
        shutil.copy2(str(cell_dir / name), str(isolated_dir / name))
        visible.append(name)
    for report in sorted(cell_dir.glob("inspect_report.*")):
        shutil.copy2(str(report), str(isolated_dir / report.name))
        visible.append(report.name)
    return sorted(visible)


def _run_live_cell(
    fixture: Mapping[str, object],
    provider: str,
    output_format: str,
    args: argparse.Namespace,
) -> Dict[str, object]:
    """
    Run one live repair cell.

    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param provider: Provider name.
    :type provider: str
    :param output_format: Inspect report format.
    :type output_format: str
    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Live report.
    :rtype: Dict[str, object]
    """
    metadata = _prepare_cell(fixture, provider, output_format, args)
    cell_dir = _artifact_dir(
        args.artifacts, str(fixture["id"]), provider, output_format
    )
    prompt = _read_text(cell_dir / "prompt_packet.md")
    with tempfile.TemporaryDirectory(prefix="pyfcstm_inspect_repair_") as td:
        isolated_dir = Path(td)
        visible_files = _copy_isolated_inputs(cell_dir, isolated_dir)
        process_result = _run_provider(
            provider, prompt, args.timeout_seconds, isolated_dir
        )
        raw_output = str(process_result.get("response_text") or "")
        if not raw_output:
            raw_output = str(process_result.get("stdout") or "")
        if not raw_output:
            raw_output = str(process_result.get("stderr") or "")
        repaired_source = _extract_fcstm_source(raw_output)
        _write_text(cell_dir / "raw_output.md", raw_output)
        _write_text(cell_dir / "repaired.fcstm", repaired_source + "\n")
        report = {
            **metadata,
            "mode": "live",
            "provider_command": process_result.get("command"),
            "provider_returncode": process_result.get("returncode"),
            "provider_version": _provider_version(provider),
            "isolated_workdir": str(isolated_dir),
            "visible_files": visible_files,
        }
        report.update(_stderr_summary(process_result.get("stderr")))
        if process_result.get("success"):
            report.update(
                _verify_repair(repaired_source, fixture, cell_dir / "repaired.fcstm")
            )
        else:
            report.update(
                {
                    "success": False,
                    "failure_category": "infra-blocked",
                    "diagnostics": str(process_result.get("stderr") or "")[
                        -_STDERR_TAIL_LIMIT:
                    ],
                }
            )
    _write_json(cell_dir / "live_report.json", report)
    return report


def _run_replay_cell(
    fixture: Mapping[str, object],
    provider: str,
    output_format: str,
    args: argparse.Namespace,
) -> Dict[str, object]:
    """
    Replay one existing repaired source artifact.

    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param provider: Provider name.
    :type provider: str
    :param output_format: Inspect report format.
    :type output_format: str
    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Replay report.
    :rtype: Dict[str, object]
    """
    cell_dir = _artifact_dir(
        args.artifacts, str(fixture["id"]), provider, output_format
    )
    metadata = _replay_metadata_cell(cell_dir, fixture, provider, output_format, args)
    repaired_path = cell_dir / "repaired.fcstm"
    if not repaired_path.is_file():
        report = {
            **metadata,
            "mode": "replay",
            "success": False,
            "failure_category": "infra-blocked",
            "diagnostics": f"repaired source not found at {repaired_path}",
        }
    else:
        source = _read_text(repaired_path)
        report = {**metadata, "mode": "replay"}
        report.update(_verify_repair(source, fixture, repaired_path))
    _write_json(cell_dir / "replay_report.json", report)
    return report


def _run_prepare_cell(
    fixture: Mapping[str, object],
    provider: str,
    output_format: str,
    args: argparse.Namespace,
) -> Dict[str, object]:
    """
    Prepare one cell without contacting a provider.

    :param fixture: Fixture manifest entry.
    :type fixture: Mapping[str, object]
    :param provider: Provider name.
    :type provider: str
    :param output_format: Inspect report format.
    :type output_format: str
    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Prepare report.
    :rtype: Dict[str, object]
    """
    metadata = _prepare_cell(fixture, provider, output_format, args)
    report = {
        **metadata,
        "mode": "prepare",
        "success": None,
        "prepared": True,
        "failure_category": "prepared",
        "diagnostics": "prepared prompt packet only; provider not run",
    }
    cell_dir = _artifact_dir(
        args.artifacts, str(fixture["id"]), provider, output_format
    )
    _write_json(cell_dir / "prepare_report.json", report)
    return report


def _write_summary(
    args: argparse.Namespace, reports: Sequence[Mapping[str, object]]
) -> Path:
    """
    Write an aggregate Markdown summary.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :param reports: Per-cell reports.
    :type reports: Sequence[Mapping[str, object]]
    :return: Summary path.
    :rtype: pathlib.Path
    """
    path = (
        args.reports
        / f"{args.mode}-{args.provider or 'all-providers'}-{args.format or 'all-formats'}-{args.fixture or 'all-fixtures'}-{_utc_timestamp()}.md"
    )
    lines = ["# Inspect Repair Evaluation Summary", ""]
    passed = sum(1 for report in reports if report.get("success") is True)
    prepared = sum(
        1 for report in reports if report.get("failure_category") == "prepared"
    )
    lines.append(f"- Mode: `{args.mode}`")
    lines.append(f"- Case count: {len(reports)}")
    lines.append(f"- Passed: {passed}/{len(reports)}")
    if prepared:
        lines.append(f"- Prepared only: {prepared}/{len(reports)}")
    lines.append("")
    lines.append(
        "| Fixture | Provider | Format | Success | Failure category | Artifact |"
    )
    lines.append("|---|---|---|---:|---|---|")
    for report in reports:
        lines.append(
            "| {fixture} | {provider} | {fmt} | {success} | {failure} | `{artifact}` |".format(
                fixture=report.get("fixture_id"),
                provider=report.get("provider"),
                fmt=report.get("format"),
                success=(
                    "yes"
                    if report.get("success") is True
                    else (
                        "prepared"
                        if report.get("failure_category") == "prepared"
                        else "no"
                    )
                ),
                failure=report.get("failure_category"),
                artifact=report.get("artifact_dir"),
            )
        )
    _write_text(path, "\n".join(lines) + "\n")
    return path


def run(args: argparse.Namespace) -> List[Dict[str, object]]:
    """
    Run the selected evaluation mode.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Per-cell reports.
    :rtype: List[Dict[str, object]]
    """
    manifest = _load_manifest(args.manifest)
    fixtures = _select_fixtures(manifest, args.fixture, args.smoke_only)
    providers = _select_values(args.provider, _PROVIDERS, "provider")
    formats = _select_values(args.format, _FORMATS, "format")
    runners = {
        "prepare": _run_prepare_cell,
        "live": _run_live_cell,
        "replay": _run_replay_cell,
    }
    selected_runner = runners[args.mode]
    reports: List[Dict[str, object]] = []
    for fixture in fixtures:
        for provider in providers:
            for output_format in formats:
                reports.append(selected_runner(fixture, provider, output_format, args))
    return reports


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "live", "replay"), required=True)
    parser.add_argument("--provider", choices=_PROVIDERS)
    parser.add_argument("--format", choices=_FORMATS)
    parser.add_argument("--fixture")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--fixtures-dir", type=Path, default=root / "fixtures")
    parser.add_argument(
        "--manifest", type=Path, default=root / "fixtures" / "manifest.json"
    )
    parser.add_argument(
        "--prompt-template",
        type=Path,
        default=root / "prompts" / "repair_prompt_template.md",
    )
    parser.add_argument("--artifacts", type=Path, default=root / "artifacts")
    parser.add_argument("--reports", type=Path, default=root / "reports")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Execute the inspect repair evaluation command.

    :param argv: Optional command-line argument vector.
    :type argv: Optional[Sequence[str]], optional
    :return: Process exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    reports = run(args)
    summary = _write_summary(args, reports)
    passed = sum(1 for report in reports if report.get("success") is True)
    prepared = sum(
        1 for report in reports if report.get("failure_category") == "prepared"
    )
    print(f"Summary: {summary}")
    print(f"Passed: {passed}/{len(reports)}")
    if prepared:
        print(f"Prepared only: {prepared}/{len(reports)}")
    if args.mode == "prepare":
        return 0 if prepared == len(reports) else 1
    return 0 if passed == len(reports) else 1


if __name__ == "__main__":
    sys.exit(main())
