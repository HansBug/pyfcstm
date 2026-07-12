"""Evaluate raw LLM-generated FBMCQ queries against private repository fixtures.

This standalone tool is intentionally outside the unit-test suite and package.
It records live provider evidence and replays saved outputs without contacting a
provider. The fixture naming convention is private evaluation infrastructure,
not a public model-fact input format.
"""

# ruff: noqa: E402

import argparse
import hashlib
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

from pyfcstm.bmc.ast import BoolLiteral
from pyfcstm.bmc.binding import bind_bmc_query, bind_bmc_query_structure
from pyfcstm.bmc.errors import (
    BmcBuildError,
    BmcQueryParseError,
    InvalidBmcQuery,
    UnsupportedBmcQuery,
)
from pyfcstm.bmc.parse import parse_bmc_query
from pyfcstm.bmc.pipeline import compile_bmc_query
from pyfcstm.bmc.query import BmcProperty, BmcQuery
from pyfcstm.bmc.witness import (
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.llm import (
    get_fbmcq_language_guide_prompt_for_llm,
    get_fbmcq_language_guide_prompt_metadata_for_llm,
)
from pyfcstm.model import load_state_machine_from_text

_PROVIDERS = ("codex", "claude", "codex-deepseek")
_GENERALITY_SMOKE_IDS = (
    "repair_parse",
    "repair_binding",
    "audit_vacuity",
    "explain_response_incomplete",
)
_SMOKE_ARTIFACT_FIXTURES = {
    "repair_parse": "reach_complete",
    "repair_binding": "reach_complete",
}
_TASK_SUFFIX = ".task.md"
_REFERENCE_RE = re.compile(r'"([^"\n]+)"')
_CHECK_RE = re.compile(r"\bcheck\s+")
_ARTIFACT_START_RE = re.compile(r"^(?:init|assume|check)\b")
_RUN_ID_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z_.-]*$")
_STDERR_TAIL_LIMIT = 2000
_SNAPSHOT_SCHEMA_VERSION = "fbmcq-evaluator/v3"
_EVALUATOR_PATH = Path(__file__).resolve()


def _utc_timestamp() -> str:
    """Return a compact UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_text(text: str) -> str:
    """Return the SHA-256 digest of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one required UTF-8 evaluation asset."""
    return _sha256_text(_read_text(path))


def _read_text(path: Path) -> str:
    """Read UTF-8 text from a required evaluation artifact."""
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    """Write UTF-8 text after creating the destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, value: Dict[str, object]) -> None:
    """Write one deterministic JSON report."""
    _write_text(
        path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def _fixture_id(path: Path) -> str:
    """Return the fixture id encoded by one private task filename."""
    if not path.name.endswith(_TASK_SUFFIX):
        raise ValueError("Fixture path must end with %r: %s" % (_TASK_SUFFIX, path))
    return path.name[: -len(_TASK_SUFFIX)]


def _fixture_paths(fixtures: Path, fixture: Optional[str]) -> List[Path]:
    """Select task fixtures according to the requested CLI scope."""
    if fixture:
        path = fixtures / (fixture + _TASK_SUFFIX)
        if not path.is_file():
            raise FileNotFoundError("Fixture %r was not found at %s." % (fixture, path))
        return [path]
    return sorted(fixtures.glob("*" + _TASK_SUFFIX))


def _smoke_task_paths(fixtures: Path) -> List[Path]:
    """Return the four private repair, audit, and explanation smoke tasks."""
    paths = [
        fixtures / "smoke" / (item + _TASK_SUFFIX) for item in _GENERALITY_SMOKE_IDS
    ]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Generality smoke task files were not found: %s." % ", ".join(missing)
        )
    return paths


def _select_providers(provider: Optional[str]) -> Tuple[str, ...]:
    """Return either all supported providers or one explicitly selected provider."""
    if provider is None:
        return _PROVIDERS
    if provider not in _PROVIDERS:
        raise ValueError("Unsupported provider %r." % provider)
    return (provider,)


def _asset_paths(task_path: Path) -> Dict[str, Path]:
    """Return private nominal, mutation, and oracle assets for one task."""
    fixture_id = _fixture_id(task_path)
    property_name, separator, input_kind = fixture_id.rpartition("_")
    if not separator or input_kind not in {"complete", "facts"}:
        raise ValueError(
            "Fixture id must end with _complete or _facts: %s" % fixture_id
        )
    models = task_path.parent / "models"
    return {
        "nominal": models / (property_name + ".fcstm"),
        "mutated": models / (property_name + ".mutated.fcstm"),
        "expected": models / (property_name + ".expected.fbmcq"),
        "discriminator": models / (property_name + ".discriminator.fcstm"),
    }


def _smoke_id(task_path: Path) -> str:
    """Return the private smoke id encoded by one smoke task filename."""
    fixture_id = _fixture_id(task_path)
    if fixture_id not in _GENERALITY_SMOKE_IDS:
        raise ValueError("Unknown generality smoke id: %s" % fixture_id)
    return fixture_id


def _output_paths(
    outputs: Path, run_id: str, provider: str, case_id: str
) -> Dict[str, Path]:
    """Return the retained minimal per-case artifact paths."""
    item_dir = outputs / "runs" / run_id / provider / case_id
    return {
        "raw": item_dir / "raw_output.md",
        "query": item_dir / "query.fbmcq",
        "live_report": item_dir / "live_report.json",
        "replay_report": item_dir / "replay_report.json",
    }


def _run_directory(outputs: Path, run_id: str) -> Path:
    """Return the immutable directory for one evaluator run."""
    return outputs / "runs" / run_id


def _validate_run_id(run_id: str) -> str:
    """Validate a portable evaluator run identifier."""
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError(
            "Run id must contain only letters, digits, '.', '_' or '-': %r." % run_id
        )
    return run_id


def _resolve_run_id(args: argparse.Namespace) -> str:
    """Resolve a requested run id or the only replayable evidence run."""
    if args.run_id:
        return _validate_run_id(args.run_id)
    if args.mode == "live":
        return _utc_timestamp()
    runs_root = args.outputs / "runs"
    run_ids = (
        sorted(path.name for path in runs_root.iterdir() if path.is_dir())
        if runs_root.is_dir()
        else []
    )
    if len(run_ids) == 1:
        return run_ids[0]
    raise ValueError(
        "Replay requires --run-id when %d saved evidence runs exist." % len(run_ids)
    )


def _git_output(cwd: Path, arguments: Sequence[str]) -> str:
    """Run one required Git inspection command and return standard output."""
    try:
        completed = subprocess.run(
            ["git"] + list(arguments),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as err:
        # FileNotFoundError: the evaluator requires Git to bind evidence to source.
        raise RuntimeError("Git is required for FBMCQ evidence replay: %s" % err)
    if completed.returncode != 0:
        raise RuntimeError(
            "Git evidence inspection failed for %s: %s"
            % (" ".join(arguments), completed.stderr.strip())
        )
    return completed.stdout.strip()


def _git_context(cwd: Path) -> Dict[str, object]:
    """Return the source commit and tracked-file cleanliness for one evaluator run."""
    return {
        "git_commit": _git_output(cwd, ("rev-parse", "HEAD")),
        "git_dirty": bool(
            _git_output(cwd, ("status", "--porcelain", "--untracked-files=no"))
        ),
    }


def _commit_is_ancestor(source_commit: str, current_commit: str, cwd: Path) -> bool:
    """Return whether recorded source is an ancestor of the current checkout."""
    try:
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_commit, current_commit],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as err:
        # FileNotFoundError: the evaluator requires Git to bind evidence to source.
        raise RuntimeError("Git is required for FBMCQ evidence replay: %s" % err)
    if completed.returncode in {0, 1}:
        return completed.returncode == 0
    raise RuntimeError("Git ancestry inspection failed: %s" % completed.stderr.strip())


def _asset_digests(task_path: Path) -> Dict[str, str]:
    """Return digests for every task asset that affects evaluator semantics."""
    assets = _asset_paths(task_path)
    return {name: _sha256_file(path) for name, path in assets.items() if path.is_file()}


def _semantic_source_sha256(cwd: Path) -> str:
    """Hash the repository Python sources that define FBMCQ execution semantics."""
    source_root = cwd / "pyfcstm"
    if not source_root.is_dir():
        raise FileNotFoundError(
            "FBMCQ semantic source directory was not found: %s" % source_root
        )
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        relative_path = path.relative_to(cwd).as_posix().encode("utf-8")
        digest.update(relative_path)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _snapshot_metadata(
    prompt: str,
    task_path: Path,
    run_id: str,
    git_context: Dict[str, object],
    cwd: Path,
    raw_output: str,
    query_file_text: Optional[str],
    asset_sha256: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Capture immutable source and asset identity for one generated response."""
    return {
        "schema_version": _SNAPSHOT_SCHEMA_VERSION,
        "run_id": run_id,
        "prompt_sha256": _sha256_text(prompt),
        "guide_sha256": get_fbmcq_language_guide_prompt_metadata_for_llm()["sha256"],
        "task_sha256": _sha256_file(task_path),
        "asset_sha256": asset_sha256
        if asset_sha256 is not None
        else _asset_digests(task_path),
        "evaluator_sha256": _sha256_file(_EVALUATOR_PATH),
        "semantic_source_sha256": _semantic_source_sha256(cwd),
        "raw_output_sha256": _sha256_text(raw_output),
        "query_sha256": _sha256_text(query_file_text)
        if query_file_text is not None
        else None,
        "git_commit": git_context["git_commit"],
        "git_dirty": git_context["git_dirty"],
    }


def _build_prompt(task_text: str) -> str:
    """Build the provider request from the packaged Guide and one private task."""
    return (
        "Author one FBMCQ query for pyfcstm. Your response is consumed verbatim "
        "by a strict artifact gate: return only raw .fbmcq source; its first "
        "non-whitespace character must begin init, assume, or check, and its last "
        "must be the final semicolon. Do not use Markdown, inline backticks, "
        "comments, explanation, commands, reasoning, or multiple candidates.\n\n"
        "## Official FBMCQ Language Guide\n\n"
        + get_fbmcq_language_guide_prompt_for_llm()
        + "\n\n## Task\n\n"
        + task_text
        + "\n\nFinal response: output one raw .fbmcq artifact only. Start with "
        "init, assume, or check; end at its final semicolon."
    )


def _build_smoke_prompt(smoke_id: str, task_text: str) -> str:
    """Build one private generality-smoke request around the packaged Guide."""
    if smoke_id in _SMOKE_ARTIFACT_FIXTURES:
        response_contract = (
            "Return only one repaired raw .fbmcq artifact. Its first non-whitespace "
            "character must begin init, assume, or check; its final non-whitespace "
            "character must be the query's final semicolon. Do not use Markdown, "
            "comments, prose, reasoning, commands, or multiple candidates."
        )
    elif smoke_id == "audit_vacuity":
        response_contract = (
            "Return exactly these three English plain-text lines and nothing else:\n"
            "VERDICT: VACUOUS\n"
            "CAUSE: mention both `x == 0` and `x == 1` and that the assumption is "
            "contradictory.\n"
            "FIX: say to remove or relax that assumption."
        )
    elif smoke_id == "explain_response_incomplete":
        response_contract = (
            "Return exactly these three English plain-text lines and nothing else:\n"
            "VERDICT: INCOMPLETE\n"
            "MEANING: say that the response is neither satisfied nor violated yet.\n"
            "LIMIT: say that the selected finite bound is too short and proves no "
            "future behavior."
        )
    else:
        raise ValueError("Unknown generality smoke id: %s" % smoke_id)
    return (
        "Use the official FBMCQ Language Guide below to complete one private "
        "evaluation task. The outer task controls the response format.\n\n"
        "## Official FBMCQ Language Guide\n\n"
        + get_fbmcq_language_guide_prompt_for_llm()
        + "\n\n## Task\n\n"
        + task_text
        + "\n\n## Required Response Contract\n\n"
        + response_contract
    )


def _prose_smoke_failure(smoke_id: str, raw_output: str) -> Optional[str]:
    """Return a private smoke-contract failure for one audit or explanation reply."""
    lines = [line.strip() for line in raw_output.strip().splitlines() if line.strip()]
    if len(lines) != 3 or "```" in raw_output:
        return "smoke_output_contract_error"
    normalized = "\n".join(lines).lower()
    if smoke_id == "audit_vacuity":
        if lines[0] != "VERDICT: VACUOUS":
            return "smoke_verdict_error"
        required = ("cause:", "fix:", "x == 0", "x == 1", "assumption")
        if not all(item in normalized for item in required):
            return "smoke_audit_explanation_error"
        if "remove" not in normalized and "relax" not in normalized:
            return "smoke_audit_fix_error"
        return None
    if smoke_id == "explain_response_incomplete":
        if lines[0] != "VERDICT: INCOMPLETE":
            return "smoke_verdict_error"
        required = ("meaning:", "limit:", "bound")
        if not all(item in normalized for item in required):
            return "smoke_response_explanation_error"
        if "neither satisfied nor violated" not in normalized and (
            "not satisfied" not in normalized or "not violated" not in normalized
        ):
            return "smoke_response_explanation_error"
        if not any(
            item in normalized
            for item in ("no future", "does not prove", "proves no", "proves nothing")
        ):
            return "smoke_response_limit_error"
        return None
    raise ValueError("Unknown prose smoke id: %s" % smoke_id)


def _provider_command(provider: str) -> List[str]:
    """Return the local command for one supported provider."""
    if provider == "codex":
        return ["codex", "exec", "--skip-git-repo-check", "-"]
    if provider == "claude":
        return ["claude", "-p"]
    if provider == "codex-deepseek":
        return ["codex-deepseek", "exec", "--skip-git-repo-check", "-"]
    raise ValueError("Unsupported provider %r." % provider)


def _run_provider(
    provider: str, prompt: str, timeout_seconds: int, cwd: Path
) -> Dict[str, object]:
    """Run one local provider process and classify infrastructure failures."""
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
        # FileNotFoundError: the selected provider executable is not installed.
        return {
            "ok": False,
            "category": "infrastructure_failure",
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(err),
        }
    except subprocess.TimeoutExpired as err:
        # TimeoutExpired: the provider process exceeded the configured limit.
        return {
            "ok": False,
            "category": "infrastructure_failure",
            "command": command,
            "returncode": None,
            "stdout": err.stdout or "",
            "stderr": err.stderr or "provider timed out",
        }
    return {
        "ok": completed.returncode == 0,
        "category": "provider_completed"
        if completed.returncode == 0
        else "provider_nonzero_exit",
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _contains_comment_trivia(text: str) -> bool:
    """Return whether FBMCQ comment syntax occurs outside a quoted string.

    The FBMCQ lexer intentionally accepts comments in source files. The LLM
    evidence contract is stricter: a provider response requested as a raw
    artifact must not use comments to smuggle explanation, a command, or an
    alternative query past parser-based semantic gates.

    :param text: Candidate raw provider response.
    :type text: str
    :return: Whether a line or block comment opener occurs outside a string.
    :rtype: bool
    """
    quote = None
    index = 0
    while index < len(text):
        character = text[index]
        if quote is not None:
            if character == "\\":
                index += 2
                continue
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {'"', "'"}:
            quote = character
            index += 1
            continue
        if character == "#":
            return True
        if character == "/" and index + 1 < len(text):
            if text[index + 1] in {"/", "*"}:
                return True
        index += 1
    return False


def _output_contract(raw_output: str) -> Tuple[Optional[str], Optional[str]]:
    """Return normalized raw query text or a Gate 0 failure category."""
    query_text = raw_output.strip()
    if not query_text:
        return None, "missing_output"
    if (
        "```" in query_text
        or _ARTIFACT_START_RE.search(query_text) is None
        or _CHECK_RE.search(query_text) is None
    ):
        return None, "output_contract_error"
    if len(_CHECK_RE.findall(query_text)) != 1:
        return None, "multiple_query_output"
    if _contains_comment_trivia(query_text):
        return None, "commented_output"
    if not query_text.endswith(";"):
        return None, "output_contract_error"
    return query_text, None


def _stderr_tail(stderr: object) -> str:
    """Return a bounded provider diagnostic, including a terminal failure message."""
    text = str(stderr or "")
    return text[-_STDERR_TAIL_LIMIT:]


def _result_summary(result) -> Dict[str, object]:
    """Return the stable user-facing portion of one solve result."""
    return {
        "status": result.status,
        "outcome": result.outcome,
        "property_satisfied": result.property_satisfied,
        "incomplete": result.incomplete,
    }


def _solve_and_replay(
    model, formula
) -> Tuple[Optional[Dict[str, object]], Optional[str]]:
    """Solve a compiled query and require replay for every returned trace."""
    result = solve_bmc_property(formula)
    summary = _result_summary(result)
    if result.status == "timeout":
        return summary, "solver_timeout"
    if result.status == "unknown":
        return summary, "solver_unknown"
    for candidate, label in (
        (result.model, "primary"),
        (result.incomplete_model, "incomplete"),
    ):
        if candidate is None:
            continue
        try:
            trace = decode_bmc_witness(formula, candidate)
            replay = replay_bmc_witness(model, trace)
        except BmcBuildError as err:
            # BmcBuildError: witness decoding rejects an inconsistent solver payload.
            summary[label + "_replay_error"] = str(err)
            return summary, "witness_decode_error"
        if not replay.ok:
            summary[label + "_replay_error"] = replay.message
            return summary, "replay_mismatch"
        summary[label + "_replay"] = "passed"
    return summary, None


def _precondition_status(
    model, query
) -> Tuple[Optional[str], List[Dict[str, object]], Optional[Dict[str, object]]]:
    """Check initialization and successive assumptions admit an execution."""
    probes = []
    for count in range(len(query.assumptions) + 1):
        probe = BmcQuery(
            property=BmcProperty(
                "reach", query.property.bound, predicate=BoolLiteral("true")
            ),
            initial=query.initial,
            assumptions=query.assumptions[:count],
        )
        result = solve_bmc_property(compile_bmc_query(model, probe))
        probes.append({"assumption_count": count, "status": result.status})
        if result.status == "unsat":
            clause = query.initial if count == 0 else query.assumptions[count - 1]
            return (
                "unsatisfiable_initialization"
                if count == 0
                else "overconstrained_assumption",
                probes,
                {
                    "clause_kind": "init" if count == 0 else "assume",
                    "clause_ordinal": 1 if count == 0 else count,
                    "canonical_clause": str(clause),
                },
            )
        if result.status in {"timeout", "unknown"}:
            return "unattributed_vacuity", probes, None
    return None, probes, None


def _anti_vacuity(
    fixture_id: str, query, expected_query, query_text: str
) -> Optional[str]:
    """Apply task-specific authorization checks without defining a public schema."""
    if query.property.kind != expected_query.property.kind:
        return "property_kind_mismatch"
    if query.property.bound != expected_query.property.bound:
        return "bound_mismatch"
    if query.initial.to_canonical() != expected_query.initial.to_canonical():
        return "unauthorized_initialization"
    if [item.to_canonical() for item in query.assumptions] != [
        item.to_canonical() for item in expected_query.assumptions
    ]:
        return "unauthorized_assumption"
    if isinstance(query.property.predicate, BoolLiteral):
        return "constant_property"
    required_references = set(_REFERENCE_RE.findall(str(expected_query)))
    if any(reference not in query_text for reference in required_references):
        return "missing_required_reference"
    if fixture_id.endswith("_facts"):
        query_references = set(_REFERENCE_RE.findall(query_text))
        if not query_references <= required_references:
            return "unauthorized_model_fact"
    return None


def _evaluate_discriminator(
    model_path: Path, query, expected_query
) -> Tuple[Optional[Dict[str, object]], Optional[Dict[str, object]], Optional[str]]:
    """Compare a generated query and oracle against one task-specific discriminator."""
    model = _load_model(model_path)
    try:
        result, failure = _solve_and_replay(model, compile_bmc_query(model, query))
        expected_result, expected_failure = _solve_and_replay(
            model, compile_bmc_query(model, expected_query)
        )
    except (InvalidBmcQuery, UnsupportedBmcQuery, BmcBuildError) as err:
        # These classes: a discriminator must retain every query-visible reference.
        return None, None, "task_semantic_discriminator_error: %s" % err
    if failure is not None or expected_failure is not None:
        return result, expected_result, failure or expected_failure
    if result != expected_result:
        return result, expected_result, "task_semantics_mismatch"
    return result, expected_result, None


def _load_model(path: Path):
    """Load one private fixture model and fail loudly when the fixture is invalid."""
    return load_state_machine_from_text(_read_text(path), path=str(path))


def _evaluate_query(query_text: str, task_path: Path) -> Dict[str, object]:
    """Run Gates 1-11 for one generated raw query against private fixtures."""
    fixture_id = _fixture_id(task_path)
    assets = _asset_paths(task_path)
    model = _load_model(assets["nominal"])
    mutated_model = _load_model(assets["mutated"])
    expected_text = _read_text(assets["expected"])
    failures = []
    report: Dict[str, object] = {
        "fixture_id": fixture_id,
        "gates": [],
        "failures": failures,
    }
    try:
        query = parse_bmc_query(query_text)
    except BmcQueryParseError as err:
        failures.append("parse_error")
        report["diagnostics"] = str(err)
        return report
    report["gates"].append("parse")
    canonical_text = str(query)
    if parse_bmc_query(canonical_text).to_canonical() != query.to_canonical():
        failures.append("canonical_round_trip_error")
        return report
    report["gates"].append("canonical_round_trip")
    try:
        bind_bmc_query_structure(query)
    except InvalidBmcQuery as err:
        failures.append("structure_binding_error")
        report["diagnostics"] = str(err)
        return report
    report["gates"].append("structure_binding")
    try:
        bind_bmc_query(query, model=model)
    except InvalidBmcQuery as err:
        failures.append("model_binding_error")
        report["diagnostics"] = str(err)
        return report
    report["gates"].append("model_binding")
    try:
        formula = compile_bmc_query(model, query)
    except UnsupportedBmcQuery as err:
        failures.append("unsupported_query")
        report["diagnostics"] = str(err)
        return report
    except (BmcBuildError, InvalidBmcQuery) as err:
        # BmcBuildError: current compilation rejected a malformed internal build.
        # InvalidBmcQuery: valid syntax cannot compile against this model.
        failures.append("compile_error")
        report["diagnostics"] = str(err)
        return report
    report["gates"].append("compile")
    precondition_failure, probes, precondition_location = _precondition_status(
        model, query
    )
    report["precondition_probes"] = probes
    if precondition_failure is not None:
        failures.append(precondition_failure)
        report["precondition_failure"] = precondition_location
        return report
    report["gates"].append("query_precondition")
    result, solve_failure = _solve_and_replay(model, formula)
    report["nominal_result"] = result
    if solve_failure is not None:
        failures.append(solve_failure)
        return report
    report["gates"].append("solve_and_replay")
    expected_query = parse_bmc_query(expected_text)
    expected_result, expected_failure = _solve_and_replay(
        model, compile_bmc_query(model, expected_query)
    )
    if expected_failure is not None:
        raise RuntimeError("Fixture oracle is invalid: %s" % expected_failure)
    report["expected_nominal_result"] = expected_result
    anti_vacuity_failure = _anti_vacuity(fixture_id, query, expected_query, query_text)
    if anti_vacuity_failure is not None:
        failures.append(anti_vacuity_failure)
        return report
    if result != expected_result:
        failures.append("oracle_mismatch")
        return report
    report["gates"].append("semantic_oracle")
    discriminator_path = assets["discriminator"]
    if discriminator_path.is_file():
        discriminator_result, expected_discriminator, discriminator_failure = (
            _evaluate_discriminator(discriminator_path, query, expected_query)
        )
        report["discriminator_result"] = discriminator_result
        report["expected_discriminator_result"] = expected_discriminator
        if discriminator_failure is not None:
            failures.append(discriminator_failure)
            return report
        report["gates"].append("task_semantic_discriminator")
    try:
        mutated_formula = compile_bmc_query(mutated_model, query)
        mutated_result, mutation_failure = _solve_and_replay(
            mutated_model, mutated_formula
        )
        expected_mutated, expected_mutation_failure = _solve_and_replay(
            mutated_model, compile_bmc_query(mutated_model, expected_query)
        )
    except (InvalidBmcQuery, UnsupportedBmcQuery, BmcBuildError) as err:
        # These classes: fixture variants must retain every query-visible reference.
        failures.append("unexpected_mutation_result")
        report["diagnostics"] = str(err)
        return report
    if mutation_failure is not None or expected_mutation_failure is not None:
        failures.append(mutation_failure or expected_mutation_failure)
        return report
    report["mutated_result"] = mutated_result
    report["expected_mutated_result"] = expected_mutated
    if mutated_result != expected_mutated:
        failures.append("unexpected_mutation_result")
        return report
    if mutated_result == result:
        failures.append("mutation_not_detected")
        return report
    report["gates"].append("mutation_discrimination")
    return report


def _evaluate_case(
    raw_output: str,
    mode: str,
    run_id: str,
    provider: str,
    task_path: Path,
    outputs: Path,
    process: Optional[Dict[str, object]] = None,
    evidence_snapshot: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Apply the output contract and semantic gates, then persist one report."""
    fixture_id = _fixture_id(task_path)
    paths = _output_paths(outputs, run_id, provider, fixture_id)
    _write_text(paths["raw"], raw_output)
    query_text, contract_failure = _output_contract(raw_output)
    report: Dict[str, object] = {
        "mode": mode,
        "run_id": run_id,
        "provider": provider,
        "fixture_id": fixture_id,
        "task_sha256": _sha256_text(_read_text(task_path)),
        "guide_metadata": get_fbmcq_language_guide_prompt_metadata_for_llm(),
        "raw_output_path": str(paths["raw"]),
        "success": False,
        "failure_category": contract_failure,
    }
    if evidence_snapshot is not None:
        report["evidence_snapshot"] = evidence_snapshot
    if process is not None:
        report["provider_command"] = process["command"]
        report["provider_returncode"] = process["returncode"]
        if not process["ok"]:
            report["provider_stderr_tail"] = _stderr_tail(process["stderr"])
            report["failure_category"] = str(process["category"])
            _write_json(paths["live_report"], report)
            return report
    if contract_failure is not None:
        _write_json(
            paths["live_report"] if mode == "live" else paths["replay_report"], report
        )
        return report
    _write_text(paths["query"], query_text + "\n")
    details = _evaluate_query(query_text, task_path)
    report.update(details)
    failures = details["failures"]
    report["failure_category"] = failures[0] if failures else None
    report["success"] = not failures
    _write_json(
        paths["live_report"] if mode == "live" else paths["replay_report"], report
    )
    return report


def _evaluate_smoke_case(
    raw_output: str,
    mode: str,
    run_id: str,
    provider: str,
    smoke_task_path: Path,
    fixtures: Path,
    outputs: Path,
    process: Optional[Dict[str, object]] = None,
    evidence_snapshot: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Validate one private repair, audit, or explanation smoke response."""
    smoke_id = _smoke_id(smoke_task_path)
    case_id = "smoke_" + smoke_id
    paths = _output_paths(outputs, run_id, provider, case_id)
    _write_text(paths["raw"], raw_output)
    report: Dict[str, object] = {
        "mode": mode,
        "run_id": run_id,
        "provider": provider,
        "fixture_id": case_id,
        "smoke_id": smoke_id,
        "task_sha256": _sha256_file(smoke_task_path),
        "guide_metadata": get_fbmcq_language_guide_prompt_metadata_for_llm(),
        "raw_output_path": str(paths["raw"]),
        "success": False,
        "failure_category": None,
    }
    if evidence_snapshot is not None:
        report["evidence_snapshot"] = evidence_snapshot
    if process is not None:
        report["provider_command"] = process["command"]
        report["provider_returncode"] = process["returncode"]
        if not process["ok"]:
            report["failure_category"] = str(process["category"])
            report["provider_stderr_tail"] = _stderr_tail(process["stderr"])
            _write_json(
                paths["live_report"] if mode == "live" else paths["replay_report"],
                report,
            )
            return report
    if smoke_id in _SMOKE_ARTIFACT_FIXTURES:
        query_text, failure = _output_contract(raw_output)
        if failure is not None:
            report["failure_category"] = failure
            _write_json(
                paths["live_report"] if mode == "live" else paths["replay_report"],
                report,
            )
            return report
        _write_text(paths["query"], str(query_text) + "\n")
        core_task_path = fixtures / (_SMOKE_ARTIFACT_FIXTURES[smoke_id] + _TASK_SUFFIX)
        details = _evaluate_query(str(query_text), core_task_path)
        details["fixture_id"] = case_id
        report.update(details)
        failures = details["failures"]
        report["failure_category"] = failures[0] if failures else None
        report["success"] = not failures
    else:
        failure = _prose_smoke_failure(smoke_id, raw_output)
        report["gates"] = ["prose_output_contract"] if failure is None else []
        report["failure_category"] = failure
        report["success"] = failure is None
    _write_json(
        paths["live_report"] if mode == "live" else paths["replay_report"], report
    )
    return report


def _replay_snapshot_mismatches(
    snapshot: object,
    prompt: str,
    task_path: Path,
    run_id: str,
    cwd: Path,
    raw_output: str,
    query_file_text: Optional[str],
    asset_sha256: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Return every immutable evidence field that differs from one live snapshot."""
    if not isinstance(snapshot, dict):
        return ["missing_snapshot"]
    current_git = _git_context(cwd)
    current = _snapshot_metadata(
        prompt,
        task_path,
        run_id,
        current_git,
        cwd,
        raw_output,
        query_file_text,
        asset_sha256,
    )
    mismatches = [
        key
        for key in (
            "schema_version",
            "run_id",
            "prompt_sha256",
            "guide_sha256",
            "task_sha256",
            "asset_sha256",
            "evaluator_sha256",
            "semantic_source_sha256",
            "raw_output_sha256",
            "query_sha256",
        )
        if snapshot.get(key) != current[key]
    ]
    source_commit = snapshot.get("git_commit")
    if not isinstance(source_commit, str) or not _commit_is_ancestor(
        source_commit, str(current_git["git_commit"]), cwd
    ):
        mismatches.append("git_commit")
    if snapshot.get("git_dirty") is not False or current_git["git_dirty"]:
        mismatches.append("git_dirty")
    return mismatches


def _replay_case(
    run_id: str, provider: str, task_path: Path, outputs: Path, cwd: Path
) -> Dict[str, object]:
    """Replay one saved output only when embedded evidence metadata matches."""
    fixture_id = _fixture_id(task_path)
    paths = _output_paths(outputs, run_id, provider, fixture_id)
    report_path = paths["replay_report"]
    if not paths["raw"].is_file() or not paths["live_report"].is_file():
        report = {
            "mode": "replay",
            "run_id": run_id,
            "provider": provider,
            "fixture_id": fixture_id,
            "success": False,
            "failure_category": "missing_replay_artifact",
        }
        _write_json(report_path, report)
        return report
    try:
        live_report = json.loads(_read_text(paths["live_report"]))
    except json.JSONDecodeError:
        # JSONDecodeError: the retained live report was manually damaged.
        report = {
            "mode": "replay",
            "run_id": run_id,
            "provider": provider,
            "fixture_id": fixture_id,
            "success": False,
            "failure_category": "invalid_replay_evidence",
        }
        _write_json(report_path, report)
        return report
    raw_output = _read_text(paths["raw"])
    query_file_text = _read_text(paths["query"]) if paths["query"].is_file() else None
    mismatches = _replay_snapshot_mismatches(
        live_report.get("evidence_snapshot"),
        _build_prompt(_read_text(task_path)),
        task_path,
        run_id,
        cwd,
        raw_output,
        query_file_text,
    )
    if mismatches:
        report = {
            "mode": "replay",
            "run_id": run_id,
            "provider": provider,
            "fixture_id": fixture_id,
            "success": False,
            "failure_category": "replay_snapshot_mismatch",
            "snapshot_mismatches": mismatches,
        }
        _write_json(report_path, report)
        return report
    return _evaluate_case(
        raw_output,
        "replay",
        run_id,
        provider,
        task_path,
        outputs,
    )


def _replay_smoke_case(
    run_id: str,
    provider: str,
    smoke_task_path: Path,
    fixtures: Path,
    outputs: Path,
    cwd: Path,
) -> Dict[str, object]:
    """Replay one saved generality smoke without contacting a provider."""
    smoke_id = _smoke_id(smoke_task_path)
    case_id = "smoke_" + smoke_id
    paths = _output_paths(outputs, run_id, provider, case_id)
    report_path = paths["replay_report"]
    if not paths["raw"].is_file() or not paths["live_report"].is_file():
        report = {
            "mode": "replay",
            "run_id": run_id,
            "provider": provider,
            "fixture_id": case_id,
            "smoke_id": smoke_id,
            "success": False,
            "failure_category": "missing_replay_artifact",
        }
        _write_json(report_path, report)
        return report
    try:
        live_report = json.loads(_read_text(paths["live_report"]))
    except json.JSONDecodeError:
        # JSONDecodeError: the retained smoke live report was manually damaged.
        report = {
            "mode": "replay",
            "run_id": run_id,
            "provider": provider,
            "fixture_id": case_id,
            "smoke_id": smoke_id,
            "success": False,
            "failure_category": "invalid_replay_evidence",
        }
        _write_json(report_path, report)
        return report
    raw_output = _read_text(paths["raw"])
    query_file_text = _read_text(paths["query"]) if paths["query"].is_file() else None
    core_fixture_id = _SMOKE_ARTIFACT_FIXTURES.get(smoke_id)
    asset_sha256 = (
        _asset_digests(fixtures / (core_fixture_id + _TASK_SUFFIX))
        if core_fixture_id is not None
        else {}
    )
    mismatches = _replay_snapshot_mismatches(
        live_report.get("evidence_snapshot"),
        _build_smoke_prompt(smoke_id, _read_text(smoke_task_path)),
        smoke_task_path,
        run_id,
        cwd,
        raw_output,
        query_file_text,
        asset_sha256,
    )
    if mismatches:
        report = {
            "mode": "replay",
            "run_id": run_id,
            "provider": provider,
            "fixture_id": case_id,
            "smoke_id": smoke_id,
            "success": False,
            "failure_category": "replay_snapshot_mismatch",
            "snapshot_mismatches": mismatches,
        }
        _write_json(report_path, report)
        return report
    return _evaluate_smoke_case(
        raw_output,
        "replay",
        run_id,
        provider,
        smoke_task_path,
        fixtures,
        outputs,
    )


def _aggregate_report(
    args: argparse.Namespace, run_id: str, reports: Sequence[Dict[str, object]]
) -> Path:
    """Write one stable aggregate report for a single immutable evidence run."""
    scope = "smoke" if args.smoke_only else "core"
    path = args.reports / ("%s-%s-%s.json" % (run_id, scope, args.mode))
    _write_json(
        path,
        {
            "mode": args.mode,
            "run_id": run_id,
            "scope": scope,
            "guide_metadata": get_fbmcq_language_guide_prompt_metadata_for_llm(),
            "case_count": len(reports),
            "passed_count": sum(1 for report in reports if report["success"]),
            "reports": list(reports),
        },
    )
    return path


def _run_self_check() -> int:
    """Exercise evaluator-only regressions without contacting a provider.

    :return: Zero after the private evaluator contracts pass.
    :rtype: int
    """
    fixtures = Path("llm_eval/fbmcq/fixtures")
    reach_task_path = fixtures / ("reach_complete" + _TASK_SUFFIX)
    reach_expected = _read_text(_asset_paths(reach_task_path)["expected"])
    reach_expected_report = _evaluate_query(reach_expected, reach_task_path)
    if reach_expected_report["failures"]:
        raise AssertionError(
            "Expected oracle query failed for reach_complete: %s"
            % reach_expected_report["failures"]
        )
    if "task_semantic_discriminator" not in reach_expected_report["gates"]:
        raise AssertionError(
            "Expected discriminator gate was not applied for reach_complete."
        )
    narrowed_reach = reach_expected.replace(
        'active("Root.Done")', 'active("Root.Done") && x == 1'
    )
    narrowed_reach_report = _evaluate_query(narrowed_reach, reach_task_path)
    if narrowed_reach_report["failures"] != ["task_semantics_mismatch"]:
        raise AssertionError(
            "Semantically narrowed reach query was not rejected: %s"
            % narrowed_reach_report["failures"]
        )

    for fixture_id in ("exists_always_complete", "exists_always_facts"):
        task_path = fixtures / (fixture_id + _TASK_SUFFIX)
        expected = _read_text(_asset_paths(task_path)["expected"])
        expected_report = _evaluate_query(expected, task_path)
        if expected_report["failures"]:
            raise AssertionError(
                "Expected oracle query failed for %s: %s"
                % (fixture_id, expected_report["failures"])
            )
        if "task_semantic_discriminator" not in expected_report["gates"]:
            raise AssertionError(
                "Expected discriminator gate was not applied for %s." % fixture_id
            )
        weakened = expected.replace("x == 0", "x < 1")
        weak_report = _evaluate_query(weakened, task_path)
        if weak_report["failures"] != ["task_semantics_mismatch"]:
            raise AssertionError(
                "Weakened query was not rejected for %s: %s"
                % (fixture_id, weak_report["failures"])
            )
        relaxed = expected.replace(
            'init state("Root.Idle");',
            'init state("Root.Idle") havoc { x } where x == 0;',
        )
        relaxed_report = _evaluate_query(relaxed, task_path)
        if relaxed_report["failures"] != ["unauthorized_initialization"]:
            raise AssertionError(
                "Unauthorized initial relaxation was not rejected for %s: %s"
                % (fixture_id, relaxed_report["failures"])
            )

    for fixture_id in ("response_complete", "response_facts"):
        task_path = fixtures / (fixture_id + _TASK_SUFFIX)
        expected = _read_text(_asset_paths(task_path)["expected"])
        expected_report = _evaluate_query(expected, task_path)
        if expected_report["failures"]:
            raise AssertionError(
                "Expected response query failed for %s: %s"
                % (fixture_id, expected_report["failures"])
            )
        widened = expected.replace("check response <= 1", "check response <= 2")
        widened_report = _evaluate_query(widened, task_path)
        if widened_report["failures"] != ["bound_mismatch"]:
            raise AssertionError(
                "Unauthorized response bound was not rejected for %s: %s"
                % (fixture_id, widened_report["failures"])
            )

    artifact = 'check reach <= 1: active("Root.Idle");'
    accepted, failure = _output_contract(artifact)
    if accepted != artifact or failure is not None:
        raise AssertionError("Plain raw artifact was rejected: %r" % failure)
    for comment in (
        " // explanation;",
        " # explanation;",
        " /* explanation */;",
    ):
        _, failure = _output_contract(artifact + comment)
        if failure != "commented_output":
            raise AssertionError("Comment injection was accepted: %r" % comment)
    _, failure = _output_contract(artifact + " // explanation")
    if failure != "commented_output":
        raise AssertionError("Trailing comment was misclassified: %r" % failure)
    quoted_comment = 'check reach <= 1: active("Root//Idle");'
    accepted, failure = _output_contract(quoted_comment)
    if accepted != quoted_comment or failure is not None:
        raise AssertionError("Quoted comment marker was rejected: %r" % failure)
    _, failure = _output_contract("`" + artifact)
    if failure != "output_contract_error":
        raise AssertionError("Inline backtick was accepted: %r" % failure)

    smoke_tasks = _smoke_task_paths(fixtures)
    if [_smoke_id(path) for path in smoke_tasks] != list(_GENERALITY_SMOKE_IDS):
        raise AssertionError("Generality smoke task ids are incomplete.")
    for smoke_task in smoke_tasks:
        smoke_id = _smoke_id(smoke_task)
        prompt = _build_smoke_prompt(smoke_id, _read_text(smoke_task))
        if get_fbmcq_language_guide_prompt_for_llm() not in prompt:
            raise AssertionError("Guide was omitted from %s smoke prompt." % smoke_id)
    if (
        _prose_smoke_failure(
            "audit_vacuity",
            "VERDICT: VACUOUS\n"
            "CAUSE: The assumption x == 0 and x == 1 is contradictory.\n"
            "FIX: Remove that assumption.",
        )
        is not None
    ):
        raise AssertionError("Valid vacuity audit smoke response was rejected.")
    if (
        _prose_smoke_failure(
            "explain_response_incomplete",
            "VERDICT: INCOMPLETE\n"
            "MEANING: The response is not satisfied and not violated yet.\n"
            "LIMIT: The bound is too short and proves no future behavior.",
        )
        is not None
    ):
        raise AssertionError("Valid response explanation smoke reply was rejected.")
    task_path = fixtures / ("reach_complete" + _TASK_SUFFIX)
    snapshot = _snapshot_metadata(
        _build_prompt(_read_text(task_path)),
        task_path,
        "self-check",
        {"git_commit": "self-check", "git_dirty": False},
        Path.cwd(),
        artifact,
        artifact + "\n",
        _asset_digests(task_path),
    )
    changed_snapshot = _snapshot_metadata(
        _build_prompt(_read_text(task_path)),
        task_path,
        "self-check",
        {"git_commit": "self-check", "git_dirty": False},
        Path.cwd(),
        artifact + "\n",
        artifact + "\n",
        _asset_digests(task_path),
    )
    if snapshot["raw_output_sha256"] == changed_snapshot["raw_output_sha256"]:
        raise AssertionError("Raw provider-output digest did not detect a mutation.")
    if not snapshot["semantic_source_sha256"]:
        raise AssertionError("Semantic source digest was not recorded.")
    print("FBMCQ evaluator self-check passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone evaluation CLI parser.

    :return: Argument parser for live or offline replay evaluation.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("live", "replay"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run deterministic evaluator regression checks without a provider.",
    )
    parser.add_argument(
        "--fixtures", type=Path, default=Path("llm_eval/fbmcq/fixtures")
    )
    parser.add_argument("--outputs", type=Path, default=Path("llm_eval/fbmcq/outputs"))
    parser.add_argument("--reports", type=Path, default=Path("llm_eval/fbmcq/reports"))
    parser.add_argument(
        "--run-id",
        help="Immutable evidence run id; replay infers it only when exactly one exists.",
    )
    parser.add_argument("--provider", choices=_PROVIDERS)
    parser.add_argument("--fixture")
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Run the four private repair, audit, and explanation smoke tasks.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the standalone evaluator.

    :param argv: Optional command-line arguments, defaults to ``sys.argv``.
    :type argv: Optional[Sequence[str]]
    :return: Zero only when every selected case satisfies all applicable gates.
    :rtype: int
    """
    args = build_parser().parse_args(argv)
    if args.check:
        return _run_self_check()
    if args.mode is None:
        raise ValueError("--mode is required unless --check is selected.")
    if args.smoke_only and args.fixture:
        raise ValueError("--fixture cannot be combined with --smoke-only.")
    tasks = (
        _smoke_task_paths(args.fixtures)
        if args.smoke_only
        else _fixture_paths(args.fixtures, args.fixture)
    )
    run_id = _resolve_run_id(args)
    run_dir = _run_directory(args.outputs, run_id)
    if args.mode == "live":
        if run_dir.exists():
            raise FileExistsError(
                "Evidence run %r already exists at %s; live mode never overwrites "
                "saved provider output. Choose a new --run-id." % (run_id, run_dir)
            )
        git_context = _git_context(args.cwd)
        if git_context["git_dirty"]:
            raise RuntimeError(
                "Live evidence generation requires no tracked working-tree changes. "
                "Commit, stash, or revert the changes before running the evaluator."
            )
    else:
        git_context = None
    reports = []
    for task_path in tasks:
        for provider in _select_providers(args.provider):
            if args.mode == "replay":
                replay = (
                    _replay_smoke_case(
                        run_id,
                        provider,
                        task_path,
                        args.fixtures,
                        args.outputs,
                        args.cwd,
                    )
                    if args.smoke_only
                    else _replay_case(
                        run_id, provider, task_path, args.outputs, args.cwd
                    )
                )
                reports.append(replay)
                continue
            task_text = _read_text(task_path)
            smoke_id = _smoke_id(task_path) if args.smoke_only else None
            prompt = (
                _build_smoke_prompt(str(smoke_id), task_text)
                if smoke_id is not None
                else _build_prompt(task_text)
            )
            process = _run_provider(provider, prompt, args.timeout_seconds, args.cwd)
            raw_output = str(process["stdout"] or "")
            query_text, _ = _output_contract(raw_output)
            query_file_text = query_text + "\n" if query_text is not None else None
            core_fixture_id = (
                _SMOKE_ARTIFACT_FIXTURES.get(str(smoke_id))
                if smoke_id is not None
                else None
            )
            asset_sha256 = (
                _asset_digests(args.fixtures / (core_fixture_id + _TASK_SUFFIX))
                if core_fixture_id is not None
                else {}
                if smoke_id is not None
                else None
            )
            snapshot = _snapshot_metadata(
                prompt,
                task_path,
                run_id,
                git_context,
                args.cwd,
                raw_output,
                query_file_text,
                asset_sha256,
            )
            report = (
                _evaluate_smoke_case(
                    raw_output,
                    "live",
                    run_id,
                    provider,
                    task_path,
                    args.fixtures,
                    args.outputs,
                    process,
                    snapshot,
                )
                if smoke_id is not None
                else _evaluate_case(
                    raw_output,
                    "live",
                    run_id,
                    provider,
                    task_path,
                    args.outputs,
                    process,
                    snapshot,
                )
            )
            reports.append(report)
    report_path = _aggregate_report(args, run_id, reports)
    passed = sum(1 for report in reports if report["success"])
    print("Report: %s" % report_path)
    print("Passed: %d/%d" % (passed, len(reports)))
    return 0 if passed == len(reports) else 1


if __name__ == "__main__":
    sys.exit(main())
