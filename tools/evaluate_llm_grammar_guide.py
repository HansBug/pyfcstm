"""
Evaluate LLM-generated FCSTM models against the packaged grammar guide.

This script is intentionally not part of the unit-test suite. It supports an
offline replay mode for saved provider outputs and a live mode for local LLM
provider CLIs. Both modes validate extracted FCSTM source with pyfcstm parsing
and model semantic validation.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.llm import (
    get_grammar_guide_prompt_for_llm,
    get_grammar_guide_prompt_metadata_for_llm,
)
from pyfcstm.model import load_state_machine_from_text

_PROVIDERS = ("codex", "claude", "codex-deepseek")
_SMOKE_FIXTURES = (
    "traffic_emergency_priority",
    "distributed_elevator_can",
    "platooning_join_protocol",
    "vtol_mission_supervision",
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
_STDERR_TAIL_LIMIT = 2000


def _fixture_id_from_path(path: Path) -> str:
    """
    Return the stable fixture id for a fixture file path.

    :param path: Natural-language fixture path.
    :type path: pathlib.Path
    :return: Fixture id without the ``.nl.md`` suffix.
    :rtype: str
    """
    name = path.name
    if name.endswith(".nl.md"):
        return name[: -len(".nl.md")]
    return path.stem


def _utc_timestamp() -> str:
    """
    Return a compact UTC timestamp for report filenames.

    :return: Timestamp in ``YYYYmmddTHHMMSSZ`` form.
    :rtype: str
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_text(path: Path) -> str:
    """
    Read a UTF-8 text file.

    :param path: File path.
    :type path: pathlib.Path
    :return: File content.
    :rtype: str
    :raises OSError: If the file cannot be read.
    :raises UnicodeDecodeError: If the file is not UTF-8.
    """
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    """
    Write UTF-8 text, creating parent directories first.

    :param path: Output file path.
    :type path: pathlib.Path
    :param text: Text content.
    :type text: str
    :return: ``None``.
    :rtype: None
    :raises OSError: If the file cannot be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, data: Dict[str, object]) -> None:
    """
    Write one JSON report file.

    :param path: Output JSON path.
    :type path: pathlib.Path
    :param data: JSON-serializable report data.
    :type data: Dict[str, object]
    :return: ``None``.
    :rtype: None
    :raises OSError: If the file cannot be written.
    """
    _write_text(
        path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def _iter_fixture_paths(
    fixtures_dir: Path,
    fixture: Optional[str],
    smoke_only: bool,
) -> List[Path]:
    """
    Select fixture files for an evaluation run.

    :param fixtures_dir: Directory containing ``*.nl.md`` fixture files.
    :type fixtures_dir: pathlib.Path
    :param fixture: Optional single fixture id.
    :type fixture: Optional[str]
    :param smoke_only: Whether to select only the fixed smoke fixtures.
    :type smoke_only: bool
    :return: Sorted fixture paths.
    :rtype: List[pathlib.Path]
    :raises FileNotFoundError: If the requested fixture does not exist.
    """
    if fixture:
        path = fixtures_dir / f"{fixture}.nl.md"
        if not path.is_file():
            raise FileNotFoundError(f"Fixture {fixture!r} was not found at {path}.")
        return [path]

    if smoke_only:
        paths = [fixtures_dir / f"{fixture_id}.nl.md" for fixture_id in _SMOKE_FIXTURES]
        missing = [path for path in paths if not path.is_file()]
        if missing:
            missing_text = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(
                f"Smoke fixture files were not found: {missing_text}."
            )
        return paths

    return sorted(fixtures_dir.glob("*.nl.md"))


def _select_providers(provider: Optional[str]) -> Tuple[str, ...]:
    """
    Select providers for an evaluation run.

    :param provider: Optional provider name.
    :type provider: Optional[str]
    :return: Provider names.
    :rtype: Tuple[str, ...]
    :raises ValueError: If ``provider`` is unsupported.
    """
    if provider is None:
        return _PROVIDERS
    if provider not in _PROVIDERS:
        raise ValueError(
            f"Unsupported provider {provider!r}; expected one of {', '.join(_PROVIDERS)}."
        )
    return (provider,)


def _extract_fcstm_source(raw_output: str) -> str:
    """
    Extract FCSTM source from raw provider output.

    Fenced ``fcstm`` blocks are preferred. If no fence exists, the first line
    that looks like FCSTM source starts the extracted text.

    :param raw_output: Raw provider response.
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
    Summarize provider stderr without embedding full prompt transcripts.

    Some local provider CLIs echo the entire prompt to stderr in non-interactive
    mode. Reports keep only a bounded tail so committed artifacts stay small
    while preserving enough diagnostics for infrastructure failures.

    :param stderr: Provider stderr object from the process result.
    :type stderr: object
    :return: Bounded stderr metadata.
    :rtype: Dict[str, object]
    """
    text = str(stderr or "")
    return {
        "provider_stderr_size": len(text),
        "provider_stderr_tail": text[-_STDERR_TAIL_LIMIT:],
    }


def _validate_fcstm_source(source: str, path: Path) -> Dict[str, object]:
    """
    Validate extracted FCSTM source with pyfcstm.

    :param source: FCSTM source text.
    :type source: str
    :param path: Path context for import resolution.
    :type path: pathlib.Path
    :return: Validation result.
    :rtype: Dict[str, object]
    """
    try:
        model = load_state_machine_from_text(source, path=str(path))
    except GrammarParseError as err:
        # GrammarParseError: pyfcstm parser rejects invalid DSL syntax.
        return {
            "success": False,
            "failure_category": "parse_error",
            "diagnostics": str(err),
        }
    except (SyntaxError, ValueError) as err:
        # SyntaxError: model semantic assembly rejects invalid structure.
        # ValueError: expression/model conversion rejects invalid values.
        return {
            "success": False,
            "failure_category": "semantic_error",
            "diagnostics": str(err),
        }

    return {
        "success": True,
        "failure_category": "passed",
        "diagnostics": "",
        "root_state": model.root_state.name if model.root_state is not None else None,
    }


def _output_paths(outputs_dir: Path, provider: str, fixture_id: str) -> Dict[str, Path]:
    """
    Return standard output paths for one provider/fixture pair.

    :param outputs_dir: Output root directory.
    :type outputs_dir: pathlib.Path
    :param provider: Provider name.
    :type provider: str
    :param fixture_id: Fixture id.
    :type fixture_id: str
    :return: Output paths keyed by role.
    :rtype: Dict[str, pathlib.Path]
    """
    item_dir = outputs_dir / provider / fixture_id
    return {
        "raw": item_dir / "raw_output.md",
        "model": item_dir / "model.fcstm",
        "live_report": item_dir / "live_report.json",
        "replay_report": item_dir / "replay_report.json",
    }


def _build_live_prompt(fixture_text: str) -> str:
    """
    Build the live provider prompt for one fixture.

    :param fixture_text: Natural-language fixture content.
    :type fixture_text: str
    :return: Full provider prompt.
    :rtype: str
    """
    guide = get_grammar_guide_prompt_for_llm()
    return (
        "You are generating an FCSTM model for pyfcstm.\n"
        "Use the official grammar guide exactly. Return only raw FCSTM source.\n"
        "Do not include Markdown fences, explanations, comments outside the model, "
        "or unsupported future syntax.\n\n"
        "## Official FCSTM LLM Grammar Guide\n\n"
        f"{guide}\n\n"
        "## Natural-language controller fixture\n\n"
        f"{fixture_text}\n\n"
        "Now return one complete legal .fcstm model."
    )


def _provider_command(provider: str) -> List[str]:
    """
    Build the subprocess command for a provider.

    :param provider: Provider name.
    :type provider: str
    :return: Command argument vector.
    :rtype: List[str]
    :raises ValueError: If the provider is unsupported.
    """
    if provider == "codex":
        return ["codex", "exec", "--skip-git-repo-check", "-"]
    if provider == "claude":
        return ["claude", "-p"]
    if provider == "codex-deepseek":
        return ["codex-deepseek", "exec", "--skip-git-repo-check", "-"]
    raise ValueError(f"Unsupported provider {provider!r}.")


def _run_provider(
    provider: str,
    prompt: str,
    timeout_seconds: int,
    cwd: Path,
) -> Dict[str, object]:
    """
    Run one live provider command.

    :param provider: Provider name.
    :type provider: str
    :param prompt: Prompt text.
    :type prompt: str
    :param timeout_seconds: Provider timeout in seconds.
    :type timeout_seconds: int
    :param cwd: Working directory for the provider process.
    :type cwd: pathlib.Path
    :return: Process result with stdout/stderr.
    :rtype: Dict[str, object]
    """
    command = _provider_command(provider)
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
    except FileNotFoundError as err:
        # FileNotFoundError: the requested provider CLI is not installed.
        return {
            "success": False,
            "failure_category": "infrastructure_failure",
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(err),
        }
    except subprocess.TimeoutExpired as err:
        # TimeoutExpired: the provider CLI exceeded the configured smoke limit.
        return {
            "success": False,
            "failure_category": "infrastructure_failure",
            "command": command,
            "returncode": None,
            "stdout": err.stdout or "",
            "stderr": err.stderr
            or f"provider timed out after {timeout_seconds} seconds",
        }

    return {
        "success": completed.returncode == 0,
        "failure_category": "provider_nonzero_exit"
        if completed.returncode != 0
        else "provider_completed",
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _evaluate_raw_output(
    raw_output: str,
    mode: str,
    provider: str,
    fixture_id: str,
    fixture_path: Path,
    outputs_dir: Path,
    process_result: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """
    Extract and validate one raw provider output.

    :param raw_output: Raw provider output.
    :type raw_output: str
    :param mode: Evaluation mode.
    :type mode: str
    :param provider: Provider name.
    :type provider: str
    :param fixture_id: Fixture id.
    :type fixture_id: str
    :param fixture_path: Fixture file path.
    :type fixture_path: pathlib.Path
    :param outputs_dir: Output root directory.
    :type outputs_dir: pathlib.Path
    :param process_result: Optional live process result.
    :type process_result: Optional[Dict[str, object]]
    :return: Evaluation report.
    :rtype: Dict[str, object]
    """
    paths = _output_paths(outputs_dir, provider, fixture_id)
    source = _extract_fcstm_source(raw_output)
    _write_text(paths["raw"], raw_output)
    _write_text(paths["model"], source + "\n")

    validation = _validate_fcstm_source(source, paths["model"])
    report: Dict[str, object] = {
        "mode": mode,
        "provider": provider,
        "fixture_id": fixture_id,
        "fixture_path": str(fixture_path),
        "guide_sha256": get_grammar_guide_prompt_metadata_for_llm()["sha256"],
        "raw_output_path": str(paths["raw"]),
        "model_output_path": str(paths["model"]),
        "evaluated_at": _utc_timestamp(),
        "source_line_count": len(source.splitlines()),
    }
    report.update(validation)

    if process_result is not None:
        report["provider_command"] = process_result.get("command")
        report["provider_returncode"] = process_result.get("returncode")
        report.update(_stderr_summary(process_result.get("stderr")))
        if not process_result.get("success"):
            report["success"] = False
            report["failure_category"] = process_result.get("failure_category")
            report["diagnostics"] = str(process_result.get("stderr") or "")[
                -_STDERR_TAIL_LIMIT:
            ]

    report_path = paths["live_report"] if mode == "live" else paths["replay_report"]
    _write_json(report_path, report)
    return report


def _evaluate_missing_output(
    mode: str,
    provider: str,
    fixture_id: str,
    fixture_path: Path,
    outputs_dir: Path,
) -> Dict[str, object]:
    """
    Build a replay report for a missing raw output.

    :param mode: Evaluation mode.
    :type mode: str
    :param provider: Provider name.
    :type provider: str
    :param fixture_id: Fixture id.
    :type fixture_id: str
    :param fixture_path: Fixture file path.
    :type fixture_path: pathlib.Path
    :param outputs_dir: Output root directory.
    :type outputs_dir: pathlib.Path
    :return: Missing-output report.
    :rtype: Dict[str, object]
    """
    paths = _output_paths(outputs_dir, provider, fixture_id)
    return {
        "mode": mode,
        "provider": provider,
        "fixture_id": fixture_id,
        "fixture_path": str(fixture_path),
        "guide_sha256": get_grammar_guide_prompt_metadata_for_llm()["sha256"],
        "raw_output_path": str(paths["raw"]),
        "model_output_path": str(paths["model"]),
        "evaluated_at": _utc_timestamp(),
        "success": False,
        "failure_category": "missing_output",
        "diagnostics": f"Replay output was not found at {paths['raw']}.",
    }


def run_replay(args: argparse.Namespace) -> List[Dict[str, object]]:
    """
    Run offline replay over saved provider outputs.

    :param args: Parsed CLI arguments.
    :type args: argparse.Namespace
    :return: Per-case reports.
    :rtype: List[Dict[str, object]]
    """
    fixture_paths = _iter_fixture_paths(args.fixtures, args.fixture, args.smoke_only)
    providers = _select_providers(args.provider)
    reports: List[Dict[str, object]] = []

    for fixture_path in fixture_paths:
        fixture_id = _fixture_id_from_path(fixture_path)
        for provider in providers:
            paths = _output_paths(args.outputs, provider, fixture_id)
            if paths["raw"].is_file():
                report = _evaluate_raw_output(
                    raw_output=_read_text(paths["raw"]),
                    mode="replay",
                    provider=provider,
                    fixture_id=fixture_id,
                    fixture_path=fixture_path,
                    outputs_dir=args.outputs,
                )
            else:
                report = _evaluate_missing_output(
                    mode="replay",
                    provider=provider,
                    fixture_id=fixture_id,
                    fixture_path=fixture_path,
                    outputs_dir=args.outputs,
                )
            reports.append(report)

    return reports


def run_live(args: argparse.Namespace) -> List[Dict[str, object]]:
    """
    Run live provider evaluation.

    :param args: Parsed CLI arguments.
    :type args: argparse.Namespace
    :return: Per-case reports.
    :rtype: List[Dict[str, object]]
    """
    fixture_paths = _iter_fixture_paths(args.fixtures, args.fixture, args.smoke_only)
    providers = _select_providers(args.provider)
    reports: List[Dict[str, object]] = []

    for fixture_path in fixture_paths:
        fixture_id = _fixture_id_from_path(fixture_path)
        fixture_text = _read_text(fixture_path)
        prompt = _build_live_prompt(fixture_text)
        for provider in providers:
            process_result = _run_provider(
                provider=provider,
                prompt=prompt,
                timeout_seconds=args.timeout_seconds,
                cwd=args.cwd,
            )
            raw_output = str(process_result.get("stdout") or "")
            if not raw_output:
                raw_output = str(process_result.get("stderr") or "")

            report = _evaluate_raw_output(
                raw_output=raw_output,
                mode="live",
                provider=provider,
                fixture_id=fixture_id,
                fixture_path=fixture_path,
                outputs_dir=args.outputs,
                process_result=process_result,
            )
            reports.append(report)

    return reports


def _write_aggregate_report(
    args: argparse.Namespace, reports: Sequence[Dict[str, object]]
) -> Path:
    """
    Write the aggregate evaluation report.

    :param args: Parsed CLI arguments.
    :type args: argparse.Namespace
    :param reports: Per-case reports.
    :type reports: Sequence[Dict[str, object]]
    :return: Aggregate report path.
    :rtype: pathlib.Path
    """
    provider_part = args.provider or "all-providers"
    fixture_part = args.fixture or "all-fixtures"
    report_path = (
        args.reports
        / f"{args.mode}-{provider_part}-{fixture_part}-{_utc_timestamp()}.json"
    )
    _write_json(
        report_path,
        {
            "mode": args.mode,
            "guide_metadata": get_grammar_guide_prompt_metadata_for_llm(),
            "smoke_fixtures": list(_SMOKE_FIXTURES),
            "case_count": len(reports),
            "passed_count": sum(1 for item in reports if item.get("success")),
            "reports": list(reports),
        },
    )
    return report_path


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("replay", "live"), required=True)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("llm_eval/fixtures"),
        help="Directory containing *.nl.md fixtures.",
    )
    parser.add_argument(
        "--outputs",
        type=Path,
        default=Path("llm_eval/outputs"),
        help="Directory for provider outputs.",
    )
    parser.add_argument(
        "--reports",
        type=Path,
        default=Path("llm_eval/reports"),
        help="Directory for aggregate JSON reports.",
    )
    parser.add_argument("--provider", choices=_PROVIDERS)
    parser.add_argument("--fixture", help="Single fixture id to evaluate.")
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Evaluate the fixed four-fixture smoke set.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the evaluation CLI.

    :param argv: Optional argument vector, defaults to ``sys.argv``.
    :type argv: Optional[Sequence[str]]
    :return: Process exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode == "replay":
        reports = run_replay(args)
    else:
        reports = run_live(args)

    report_path = _write_aggregate_report(args, reports)
    passed_count = sum(1 for item in reports if item.get("success"))
    print(f"Report: {report_path}")
    print(f"Passed: {passed_count}/{len(reports)}")
    return 0 if passed_count == len(reports) else 1


if __name__ == "__main__":
    sys.exit(main())
