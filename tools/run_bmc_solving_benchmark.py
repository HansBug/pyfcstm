"""
Measure what BMC solving costs, and whether an encoding or solver knob changes it.

The BMC engine's user-visible options all change how the formula is built or how
Z3 is constructed, never what the property means.  So the question for any such
knob is the same: does the answer stay identical, and what does it cost?  This
runner answers it with arms that are option combinations on one revision, plus
one baseline arm that is a checked-out earlier revision, so an overhead the
infrastructure adds on every run is visible separately from the knob.

Timing and peak memory are collected from a separate process per sample.  Z3
keeps state between checks inside one process, so a second measurement in the
same interpreter would be measuring a warmed solver rather than the sample.

The runner is deliberately outside pytest.  Distribution measurements are not
assertions, and a suite that fails because a machine was busy teaches nothing.
Unit tests under ``test/bmc/`` cover the API and the invariants instead.

Example::

    $ python tools/run_bmc_solving_benchmark.py --check
    Benchmark corpus, arms, thresholds, and layout are consistent.
    $ python tools/run_bmc_solving_benchmark.py --run --repetitions 5
    Wrote benchmarks/bmc/solving/outputs/runs/<run-id>/report.md
"""

import argparse
import copy
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Running ``python tools/<script>.py`` puts ``tools/`` first on ``sys.path``, not
# the repository root, and the package is not installed into the interpreter.
# The corpus check loads models and binds queries through the public API, so
# the root has to be importable here as well as in the child.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

#: Where the corpus, schema, and immutable run outputs live.
_BENCH_ROOT = Path("benchmarks/bmc/solving")

#: The revision the contrast is measured against: the umbrella's creation base.
_BASELINE_LABEL = "baseline-0cc43647"
_BASELINE_COMMIT = "0cc43647ad85c99347fbdd8eab0259279a5f40d0"

#: The arm every other arm is compared against under the correctness gate.
_REFERENCE_ARM = "default"

#: The arms, in the order a reader should compare them.
#:
#: ``revision`` names a commit the child runs from a detached worktree; ``None``
#: means the working tree.  ``options`` are forwarded to the child verbatim, and
#: the child refuses keys it does not know, so adding an arm here without
#: teaching the child what it means fails instead of measuring the default under
#: a new name.
_ARMS: Tuple[Dict[str, Any], ...] = (
    {"label": _BASELINE_LABEL, "revision": _BASELINE_COMMIT, "options": {}},
    {"label": _REFERENCE_ARM, "revision": None, "options": {}},
)

#: Threshold ids the README must pre-register before the first run.
_THRESHOLD_IDS = ("H0", "T1", "T2", "T3")

#: Case roles, and what each one is in the corpus for.
_ROLES = ("llm_generated", "slicing_positive", "definedness_trap", "abstract_skip")

_STATUSES = ("sat", "unsat", "unknown", "timeout")

#: How often the child's resident set size is sampled, in seconds.
_RSS_SAMPLE_SECONDS = 0.002

#: How each published metric is obtained.
_MEASUREMENT_MAP: Tuple[Tuple[str, str, str], ...] = (
    (
        "build_ms",
        "compile_bmc_query wall time in the child",
        "prepare, core relation, and property compilation; the region an "
        "encoding knob changes",
    ),
    (
        "solve_ms",
        "solve_bmc_property wall time in the child",
        "the staged primary solve including its verdict; the region a solver "
        "knob changes",
    ),
    (
        "replay_ms",
        "decode_bmc_result_trace + replay_bmc_witness wall time in the child",
        "only when the primary status is sat; absent otherwise",
    ),
    (
        "total_elapsed_ms",
        "result.total_elapsed_ms",
        "production ledger; the solver's own accounting of the whole solve",
    ),
    (
        "formula_dag_nodes",
        "distinct Z3 AST ids reachable from core.core and objective_formula",
        "a size measure that does not depend on printing; what a slice shrinks",
    ),
    (
        "rlimit_count",
        "z3 statistics 'rlimit count' of one plain side check of the same "
        "conjunction, outside the timed region",
        "Z3's own effort counter, steadier than wall time but not identical "
        "across processes: two arms running identical code differed by about "
        "one percent on one sat query",
    ),
    (
        "status / property_satisfied / outcome / replay_ok",
        "result fields and replay.ok",
        "the correctness gate compares these between arms and against case.json",
    ),
    (
        "peak_child_rss_bytes",
        "maximum of sampled psutil RSS readings of the child process",
        "a sampled maximum, not a kernel high-water mark: a spike shorter than "
        "the %g s interval can be missed.  Absent rather than zero when psutil "
        "is unavailable" % _RSS_SAMPLE_SECONDS,
    ),
)


class BenchmarkFailure(RuntimeError):
    """Raised when the corpus, layout, thresholds, or a run is inconsistent."""


def _bench_root() -> Path:
    """Return the absolute benchmark directory in this checkout."""
    return _REPO_ROOT / _BENCH_ROOT


# --------------------------------------------------------------------------
# Corpus
# --------------------------------------------------------------------------


def _digest_text(text: str) -> str:
    """Return the SHA-256 of ``text`` with line endings normalized.

    :param text: File content.
    :type text: str
    :return: Hex digest.
    :rtype: str
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _digest(path: Path) -> str:
    """Return a stable digest of one input file.

    :param path: File to digest.
    :type path: pathlib.Path
    :return: Hex SHA-256 of the normalized bytes.
    :rtype: str
    """
    return _digest_text(path.read_text(encoding="utf-8"))


def _case_dirs(root: Path) -> List[Path]:
    """Return the case directories in name order.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :return: Sorted case directories.
    :rtype: List[pathlib.Path]
    """
    cases = root / "cases"
    if not cases.is_dir():
        return []
    return sorted(path for path in cases.iterdir() if path.is_dir())


def _load_case(case_dir: Path, problems: List[str]) -> Optional[Dict[str, Any]]:
    """Read and validate one ``case.json``.

    :param case_dir: Directory holding the case.
    :type case_dir: pathlib.Path
    :param problems: Accumulates human-readable problems.
    :type problems: List[str]
    :return: The parsed case, or ``None`` when it cannot be read.
    :rtype: Dict[str, Any], optional
    """
    label = "cases/%s" % case_dir.name
    meta_path = case_dir / "case.json"
    if not meta_path.exists():
        problems.append("%s/case.json is missing." % label)
        return None
    try:
        case = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        # A hand-edited case.json is the usual way to get here.
        problems.append("%s/case.json is not valid JSON: %s." % (label, err))
        return None
    if case.get("name") != case_dir.name:
        problems.append(
            "%s/case.json name %r does not match its directory."
            % (label, case.get("name"))
        )
    if case.get("role") not in _ROLES:
        problems.append(
            "%s/case.json role %r is not one of %s." % (label, case.get("role"), _ROLES)
        )
    if not isinstance(case.get("why"), str) or not case["why"].strip():
        problems.append("%s/case.json has no why." % label)
    model_name = case.get("model")
    if not isinstance(model_name, str) or not (case_dir / model_name).exists():
        problems.append(
            "%s/%s model.fcstm is missing." % (label, model_name or "model.fcstm")
        )
    queries = case.get("queries")
    if not isinstance(queries, list) or not queries:
        problems.append("%s/case.json lists no queries." % label)
        return case
    seen = set()
    for index, query in enumerate(queries):
        where = "%s/case.json queries[%d]" % (label, index)
        if not isinstance(query, dict):
            problems.append("%s is not an object." % where)
            continue
        file_name = query.get("file")
        if not isinstance(file_name, str) or not file_name:
            problems.append("%s has no file." % where)
        elif not (case_dir / file_name).exists():
            problems.append("%s/%s is missing." % (label, file_name))
        elif file_name in seen:
            problems.append("%s/%s is listed twice." % (label, file_name))
        seen.add(file_name)
        if not isinstance(query.get("kind"), str) or not query["kind"]:
            problems.append("%s has no kind." % where)
        if not isinstance(query.get("why"), str) or not query["why"].strip():
            problems.append("%s has no why." % where)
        expected = query.get("expected")
        if not isinstance(expected, dict):
            problems.append("%s has no expected object." % where)
            continue
        for key in ("status", "property_satisfied", "outcome"):
            if key not in expected:
                problems.append("%s expected.%s is missing." % (where, key))
        if "status" in expected and expected["status"] not in _STATUSES:
            problems.append(
                "%s expected.status %r is not one of %s."
                % (where, expected["status"], _STATUSES)
            )
        if "property_satisfied" in expected and expected["property_satisfied"] not in (
            True,
            False,
            None,
        ):
            problems.append(
                "%s expected.property_satisfied must be true, false or null." % where
            )
        if "outcome" in expected and (
            not isinstance(expected["outcome"], str) or not expected["outcome"]
        ):
            problems.append("%s expected.outcome must be a non-empty string." % where)
    return case


def _load_model_for_check(case_dir: Path, case: Dict[str, Any], problems: List[str]):
    """Load the case model and confirm inspect reports no error-level diagnostic.

    :param case_dir: Case directory.
    :type case_dir: pathlib.Path
    :param case: Parsed ``case.json``.
    :type case: Dict[str, Any]
    :param problems: Accumulates human-readable problems.
    :type problems: List[str]
    :return: The loaded state machine, or ``None`` when it does not load.
    """
    from pyfcstm.diagnostics import inspect_model
    from pyfcstm.dsl.error import GrammarParseError
    from pyfcstm.model import load_state_machine_from_file
    from pyfcstm.utils.validate import ModelValidationError

    model_path = case_dir / case["model"]
    label = "cases/%s/%s" % (case_dir.name, case["model"])
    try:
        model = load_state_machine_from_file(str(model_path))
    except (GrammarParseError, ModelValidationError) as err:
        # GrammarParseError: the file is not syntactically FCSTM;
        # ModelValidationError: it parses but names a state or variable that
        # does not exist.  Both mean the corpus file does not load.
        problems.append("%s does not load: %s" % (label, str(err).splitlines()[0]))
        return None
    errors = [d.code for d in inspect_model(model).diagnostics if d.severity == "error"]
    if errors:
        problems.append("%s has error-level inspect diagnostics: %s." % (label, errors))
    return model


def _check_queries_bind(
    case_dir: Path, case: Dict[str, Any], model, problems: List[str]
) -> None:
    """Confirm every query parses and binds against its model without solving.

    :param case_dir: Case directory.
    :type case_dir: pathlib.Path
    :param case: Parsed ``case.json``.
    :type case: Dict[str, Any]
    :param model: Loaded state machine.
    :param problems: Accumulates human-readable problems.
    :type problems: List[str]
    """
    from pyfcstm.bmc import prepare_bmc_query
    from pyfcstm.bmc.errors import (
        BmcBuildError,
        BmcQueryParseError,
        InvalidBmcQuery,
        UnsupportedBmcQuery,
    )

    for query in case.get("queries", ()):
        file_name = query.get("file")
        if not isinstance(file_name, str) or not (case_dir / file_name).exists():
            continue
        text = (case_dir / file_name).read_text(encoding="utf-8")
        try:
            prepare_bmc_query(model, text, query_source_path=str(case_dir / file_name))
        except (
            BmcQueryParseError,
            InvalidBmcQuery,
            UnsupportedBmcQuery,
            BmcBuildError,
        ) as err:
            # BmcQueryParseError: malformed FBMCQ text; InvalidBmcQuery: a state,
            # variable or event the model does not have; UnsupportedBmcQuery: a
            # valid construct the encoder refuses; BmcBuildError: option policy.
            problems.append(
                "cases/%s/%s does not bind: %s"
                % (case_dir.name, file_name, str(err).splitlines()[0])
            )


def _readme_problems(root: Path, case_names: Sequence[str]) -> List[str]:
    """Check the README pre-registers every threshold and lists every case.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param case_names: Case directory names.
    :type case_names: Sequence[str]
    :return: Problems found.
    :rtype: List[str]
    """
    readme = root / "README.md"
    if not readme.exists():
        return ["%s/README.md is missing." % _BENCH_ROOT]
    text = readme.read_text(encoding="utf-8")
    problems = []
    if "## Pre-registered thresholds" not in text:
        problems.append("README.md has no '## Pre-registered thresholds' section.")
    for threshold in _THRESHOLD_IDS:
        if not any(line.startswith("| %s " % threshold) for line in text.splitlines()):
            problems.append(
                "README.md does not pre-register threshold %s as a table row."
                % threshold
            )
    for name in case_names:
        if "`%s`" % name not in text:
            problems.append("README.md does not list case `%s`." % name)
    return problems


def _arm_problems() -> List[str]:
    """Check the arm table is internally consistent.

    :return: Problems found.
    :rtype: List[str]
    """
    problems = []
    labels = [arm["label"] for arm in _ARMS]
    if len(labels) != len(set(labels)):
        problems.append("The arm table has a duplicate label.")
    reference = [arm for arm in _ARMS if arm["label"] == _REFERENCE_ARM]
    if (
        len(reference) != 1
        or reference[0]["revision"] is not None
        or reference[0]["options"]
    ):
        problems.append(
            "Exactly one arm must be the reference: the working tree with no options."
        )
    if len(_BASELINE_COMMIT) != 40:
        problems.append("The baseline commit must be recorded in full.")
    if not _BASELINE_COMMIT.startswith(_BASELINE_LABEL.split("-")[1]):
        problems.append("The baseline label and commit disagree.")
    names = [name for name, _source, _note in _MEASUREMENT_MAP]
    if len(names) != len(set(names)):
        problems.append("The measurement map has a duplicate metric name.")
    return problems


def _schema(root: Path) -> Optional[Dict[str, Any]]:
    """Load ``schema.json``.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :return: The parsed schema, or ``None`` when it is missing or malformed.
    :rtype: Dict[str, Any], optional
    :raises BenchmarkFailure: If the file is missing or is not valid JSON.
    """
    path = root / "schema.json"
    if not path.exists():
        raise BenchmarkFailure("%s/schema.json is missing." % _BENCH_ROOT)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        # The schema is hand-maintained JSON.
        raise BenchmarkFailure(
            "%s/schema.json is not valid JSON: %s." % (_BENCH_ROOT, err)
        )


def _validate_run(root: Path, run_dir: Path, schema: Dict[str, Any]) -> List[str]:
    """Validate one saved run against ``schema.json``.

    With ``jsonschema`` unavailable only the presence of the files and the
    manifest's schema tag are checked, and the report says so.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param run_dir: One ``outputs/runs/<run-id>`` directory.
    :type run_dir: pathlib.Path
    :param schema: Parsed ``schema.json``.
    :type schema: Dict[str, Any]
    :return: Problems found.
    :rtype: List[str]
    """
    label = "outputs/runs/%s" % run_dir.name
    documents = {}
    for name in ("manifest", "summary"):
        path = run_dir / ("%s.json" % name)
        if not path.exists():
            return ["%s/%s.json is missing." % (label, name)]
        try:
            documents[name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            # Saved runs are written by this tool, so this means a damaged file.
            return ["%s/%s.json is not valid JSON: %s." % (label, name, err)]
    try:
        import jsonschema
    except ImportError:
        # Documented degradation: the structural check needs the optional
        # development dependency; without it only the schema tag is read.
        tag = (
            documents["manifest"].get("schema")
            if isinstance(documents["manifest"], dict)
            else None
        )
        if tag != schema["$defs"]["manifest"]["properties"]["schema"]["const"]:
            return [
                "%s/manifest.json does not carry the schema tag; jsonschema is unavailable for a full check."
                % label
            ]
        return []
    validator = jsonschema.Draft202012Validator(schema)
    problems = []
    for error in sorted(
        validator.iter_errors(documents), key=lambda e: list(e.absolute_path)
    ):
        where = "/".join(str(part) for part in error.absolute_path) or "(root)"
        problems.append(
            "%s violates schema.json at %s: %s" % (label, where, error.message)
        )
        if len(problems) >= 5:
            problems.append("%s: further schema violations omitted." % label)
            break
    return problems


def _check(root: Path) -> None:
    """Confirm the corpus, arms, thresholds, schema and saved runs are consistent.

    Nothing here solves a query: the check must stay cheap enough to run before
    every measurement.  Models are loaded and inspected, queries are bound, and
    saved runs are validated against ``schema.json``.

    :param root: Benchmark directory to check.
    :type root: pathlib.Path
    :raises BenchmarkFailure: Listing every inconsistency found.
    """
    problems: List[str] = []
    for relative in ("cases", "outputs/runs", "README.md"):
        if not (root / relative).exists():
            problems.append("%s/%s is missing." % (_BENCH_ROOT, relative))
    try:
        schema = _schema(root)
    except BenchmarkFailure as err:
        # Reported alongside the other problems rather than first and alone.
        problems.append(str(err))
        schema = None
    case_dirs = _case_dirs(root)
    if not case_dirs:
        problems.append("%s/cases holds no case directory." % _BENCH_ROOT)
    for case_dir in case_dirs:
        case = _load_case(case_dir, problems)
        if (
            case is None
            or not isinstance(case.get("model"), str)
            or not (case_dir / case["model"]).exists()
        ):
            continue
        model = _load_model_for_check(case_dir, case, problems)
        if model is not None:
            _check_queries_bind(case_dir, case, model, problems)
    problems.extend(_readme_problems(root, [path.name for path in case_dirs]))
    problems.extend(_arm_problems())
    runs = root / "outputs/runs"
    if schema is not None and runs.is_dir():
        for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
            problems.extend(_validate_run(root, run_dir, schema))
    if problems:
        raise BenchmarkFailure("\n".join("- %s" % item for item in problems))


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def _child_script() -> str:
    """Return the program each sample runs in its own interpreter.

    It prints one JSON object on standard output.  Keeping it here rather than in
    a separate file means the measured code and the measurement stay together.
    The baseline arm runs it with the worktree as the working directory, so
    ``import pyfcstm`` there resolves to the checked-out revision; every path the
    child receives is therefore absolute.

    :return: Python source for the child process.
    :rtype: str
    """
    return r"""
import json, sys, time
import z3
from pyfcstm.model import load_state_machine_from_file
from pyfcstm.bmc import (
    compile_bmc_query, solve_bmc_property, decode_bmc_result_trace, replay_bmc_witness,
)

model_path, query_path, options = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
# The child knows which options it can forward.  A key it does not know means
# an arm was added to the table without teaching the child what it measures,
# and measuring the default under a new name is the one thing this must not do.
KNOWN_OPTIONS = ()
unknown = sorted(set(options) - set(KNOWN_OPTIONS))
if unknown:
    raise SystemExit("unknown benchmark options: %s" % unknown)

model = load_state_machine_from_file(model_path)
query_text = open(query_path, encoding="utf-8").read()

started = time.perf_counter()
formula = compile_bmc_query(model, query_text, query_source_path=query_path)
build_ms = (time.perf_counter() - started) * 1000.0

started = time.perf_counter()
result = solve_bmc_property(formula)
solve_ms = (time.perf_counter() - started) * 1000.0

replay_ms = None
replay_ok = None
if result.status == "sat":
    started = time.perf_counter()
    witness = decode_bmc_result_trace(result, source="primary")
    replay_ok = replay_bmc_witness(model, witness).ok
    replay_ms = (time.perf_counter() - started) * 1000.0


def dag_nodes(*roots):
    seen = set()
    stack = list(roots)
    while stack:
        expr = stack.pop()
        ident = expr.get_id()
        if ident in seen:
            continue
        seen.add(ident)
        if z3.is_app(expr):
            stack.extend(expr.children())
        elif z3.is_quantifier(expr):
            stack.append(expr.body())
    return len(seen)


# One plain side check of the same conjunction, outside every timed region, so
# the deterministic effort counter can be read.  solve_bmc_property owns its
# solver and does not expose statistics; this is the closest honest reading.
side = z3.Solver()
side.add(formula.core.core, formula.objective_formula)
side.check()
statistics = side.statistics()
keys = set(statistics.keys())
rlimit = statistics.get_key_value("rlimit count") if "rlimit count" in keys else None

print(json.dumps({
    "build_ms": build_ms,
    "solve_ms": solve_ms,
    "replay_ms": replay_ms,
    "total_elapsed_ms": result.total_elapsed_ms,
    "formula_dag_nodes": dag_nodes(formula.core.core, formula.objective_formula),
    "rlimit_count": rlimit,
    "status": result.status,
    "property_satisfied": result.property_satisfied,
    "outcome": result.outcome,
    "replay_ok": replay_ok,
}))
"""


def _run_sample(
    model: Path, query: Path, arm: Dict[str, Any], worktree: Optional[Path]
) -> Dict[str, Any]:
    """Run one sample in a fresh interpreter and return what it measured.

    :param model: Absolute path to the ``.fcstm`` model.
    :type model: pathlib.Path
    :param query: Absolute path to the ``.fbmcq`` query.
    :type query: pathlib.Path
    :param arm: Arm table entry.
    :type arm: Dict[str, Any]
    :param worktree: Checkout to run a revision arm from, else ``None``.
    :type worktree: pathlib.Path, optional
    :return: The child's record, with ``peak_rss_bytes`` when available and an
        ``error`` key when the child failed.
    :rtype: Dict[str, Any]
    """
    command = [
        sys.executable,
        "-c",
        _child_script(),
        str(model),
        str(query),
        json.dumps(arm["options"], sort_keys=True),
    ]
    cwd = worktree if arm["revision"] is not None else _REPO_ROOT
    if arm["revision"] is not None and worktree is None:
        return {"error": "arm %s needs a worktree and none was prepared" % arm["label"]}
    peak = _spawn_and_watch(command, cwd)
    if peak.get("error"):
        return peak
    try:
        record = json.loads(peak.pop("stdout"))
    except json.JSONDecodeError as err:
        # A child that crashed before printing leaves stderr as the only clue.
        return {
            "error": "child produced no JSON: %s" % err,
            "stderr": peak.get("stderr"),
        }
    if peak.get("peak_rss_bytes") is not None:
        record["peak_rss_bytes"] = peak["peak_rss_bytes"]
    return record


def _spawn_and_watch(command: Sequence[str], cwd: Path) -> Dict[str, Any]:
    """Run a child process and sample its resident set size while it lives.

    :param command: Argument list to run.
    :type command: Sequence[str]
    :param cwd: Working directory for the child.
    :type cwd: pathlib.Path
    :return: ``stdout``, ``stderr``, and ``peak_rss_bytes`` when measurable.
    :rtype: Dict[str, Any]
    """
    try:
        import psutil
    except ImportError:
        # Documented degradation: the metric is reported absent, never as zero.
        psutil = None

    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd),
        text=True,
    )
    peak: Optional[int] = None
    if psutil is not None:
        try:
            handle = psutil.Process(process.pid)
            while process.poll() is None:
                time.sleep(_RSS_SAMPLE_SECONDS)
                try:
                    rss = handle.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # The child exited between poll and read, or the platform
                    # refuses the query; the peak so far is what we have.
                    break
                peak = rss if peak is None else max(peak, rss)
        except psutil.NoSuchProcess:
            # The child finished before the first sample; its peak is unknown.
            peak = None
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        return {
            "error": "child exited %d" % process.returncode,
            "stderr": stderr.strip()[:2000],
        }
    return {"stdout": stdout, "stderr": stderr, "peak_rss_bytes": peak}


def _git(*args: str) -> str:
    """Run one git command in the repository and return its stdout.

    :param args: Arguments after ``git``.
    :type args: str
    :return: Stripped standard output.
    :rtype: str
    :raises BenchmarkFailure: If git exits non-zero.
    """
    completed = subprocess.run(
        ["git", *args],
        cwd=str(_REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise BenchmarkFailure(
            "git %s failed: %s" % (" ".join(args), completed.stderr.strip())
        )
    return completed.stdout.strip()


def _add_worktree(commit: str) -> Path:
    """Check ``commit`` out into a detached worktree under a fresh temporary directory.

    :param commit: Full commit to check out.
    :type commit: str
    :return: The worktree directory.
    :rtype: pathlib.Path
    :raises BenchmarkFailure: If git cannot create the worktree.
    """
    parent = Path(tempfile.mkdtemp(prefix="pyfcstm-bmc-solving-baseline-"))
    tree = parent / "tree"
    try:
        _git("worktree", "add", "--detach", str(tree), commit)
    except BenchmarkFailure:
        shutil.rmtree(parent, ignore_errors=True)
        raise
    return tree


def _remove_worktree(tree: Path) -> Optional[str]:
    """Remove a worktree created by :func:`_add_worktree`.

    :param tree: The worktree directory.
    :type tree: pathlib.Path
    :return: A diagnostic when git refused and the directory had to be deleted
        by hand, else ``None``.
    :rtype: str, optional
    """
    diagnostic = None
    try:
        _git("worktree", "remove", "--force", str(tree))
    except BenchmarkFailure as err:
        # git may already consider the tree gone; the directory is removed by
        # hand and the registration pruned so nothing is left behind.
        diagnostic = str(err)
        shutil.rmtree(tree, ignore_errors=True)
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(_REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    shutil.rmtree(tree.parent, ignore_errors=True)
    return diagnostic


def _environment() -> Dict[str, Any]:
    """Return the machine and dependency facts a run has to be read against.

    :return: Interpreter, Z3, OS and CPU facts.
    :rtype: Dict[str, Any]
    """
    try:
        import z3

        z3_version = z3.get_version_string()
    except ImportError:
        # Recorded as unavailable rather than omitted.
        z3_version = "unavailable"
    return {
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "z3": z3_version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def _dirty_state() -> Dict[str, Any]:
    """Return whether the tree was clean, and the commit it was on.

    :return: ``commit``, ``dirty`` and the porcelain listing when dirty.
    :rtype: Dict[str, Any]
    """
    porcelain = _git("status", "--porcelain")
    return {
        "commit": _git("rev-parse", "HEAD"),
        "dirty": bool(porcelain),
        "porcelain": porcelain.splitlines() if porcelain else [],
    }


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------

_TIMING_FIELDS = ("build_ms", "solve_ms", "replay_ms", "total_elapsed_ms")
_OBSERVED_FIELDS = (
    "formula_dag_nodes",
    "rlimit_count",
    "status",
    "property_satisfied",
    "outcome",
    "replay_ok",
)
_H0_FIELDS = ("status", "property_satisfied", "outcome", "replay_ok")


def _percentile(values: Sequence[float], fraction: float) -> Optional[float]:
    """Return a percentile by nearest rank, or ``None`` for no values.

    :param values: Measured samples.
    :type values: Sequence[float]
    :param fraction: Percentile as a fraction, ``0.5`` for the median.
    :type fraction: float
    :return: The chosen sample, or ``None``.
    :rtype: float, optional
    """
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _distribution(values: Sequence[float]) -> Dict[str, Optional[float]]:
    """Reduce samples to p50, p95 and max.

    :param values: Measured samples.
    :type values: Sequence[float]
    :return: Distribution dictionary.
    :rtype: Dict[str, Optional[float]]
    """
    return {
        "p50": _percentile(values, 0.5),
        "p95": _percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def _summarize(samples: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Reduce repeated samples of one query under one arm to a distribution.

    :param samples: Measured records.
    :type samples: Sequence[Dict[str, Any]]
    :return: Distributions, observed published fields, and failure facts.
    :rtype: Dict[str, Any]
    """
    good = [item for item in samples if not item.get("error")]
    summary: Dict[str, Any] = {
        "samples": len(samples),
        "failures": len(samples) - len(good),
    }
    for field in _TIMING_FIELDS:
        summary[field] = _distribution(
            [item[field] for item in good if item.get(field) is not None]
        )
    for field in _OBSERVED_FIELDS:
        observed = sorted(
            {
                json.dumps(item.get(field), sort_keys=True)
                for item in good
                if field in item
            }
        )
        if len(observed) == 1:
            summary[field] = json.loads(observed[0])
        elif not observed:
            summary[field] = None
        else:
            # Instability in a published field is a finding, not noise to hide.
            summary[field] = [json.loads(value) for value in observed]
            summary.setdefault("unstable_fields", []).append(field)
    rss = [
        item["peak_rss_bytes"]
        for item in good
        if item.get("peak_rss_bytes") is not None
    ]
    summary["peak_child_rss_bytes"] = max(rss) if rss else None
    if not rss:
        summary["peak_child_rss_note"] = "unavailable on this run; not reported as zero"
    errors = [item["error"] for item in samples if item.get("error")]
    if errors:
        summary["first_error"] = errors[0]
    elif not samples:
        summary["first_error"] = "no samples"
    return summary


def _h0(
    arm_summary: Dict[str, Any], reference: Dict[str, Any], expected: Dict[str, Any]
) -> Dict[str, bool]:
    """Evaluate the correctness gate for one arm.

    :param arm_summary: Summary of the arm under test.
    :type arm_summary: Dict[str, Any]
    :param reference: Summary of the reference arm for the same query.
    :type reference: Dict[str, Any]
    :param expected: ``case.json`` expectation for the query.
    :type expected: Dict[str, Any]
    :return: Whether the published fields match the reference, and the status
        matches the expectation.  An unstable field fails both.
    :rtype: Dict[str, bool]
    """
    unstable = set(arm_summary.get("unstable_fields", ())) | set(
        reference.get("unstable_fields", ())
    )
    identical = not (unstable & set(_H0_FIELDS)) and all(
        arm_summary.get(field) == reference.get(field) for field in _H0_FIELDS
    )
    matches = "status" not in unstable and arm_summary.get("status") == expected.get(
        "status"
    )
    return {"identical_to_reference": identical, "matches_expected_status": matches}


def _aggregate(
    grouped: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]],
    expected: Dict[str, Dict[str, Dict[str, Any]]],
    roles: Dict[str, str],
    kinds: Dict[str, Dict[str, str]],
    reference_arm: str,
) -> Dict[str, Any]:
    """Build ``summary.json`` content from grouped raw records.

    :param grouped: ``case -> query -> arm -> samples``.
    :type grouped: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]]
    :param expected: ``case -> query -> expected`` from the manifest.
    :type expected: Dict[str, Dict[str, Dict[str, Any]]]
    :param roles: ``case -> role``.
    :type roles: Dict[str, str]
    :param kinds: ``case -> query -> kind``.
    :type kinds: Dict[str, Dict[str, str]]
    :param reference_arm: Label of the reference arm.
    :type reference_arm: str
    :return: Summary dictionary.
    :rtype: Dict[str, Any]
    """
    summary: Dict[str, Any] = {}
    for case, queries in sorted(grouped.items()):
        summary[case] = {"role": roles.get(case, "unknown"), "queries": {}}
        for query, arms in sorted(queries.items()):
            arm_summaries = {arm: _summarize(samples) for arm, samples in arms.items()}
            reference = arm_summaries.get(reference_arm, {})
            want = expected.get(case, {}).get(
                query,
                {
                    "status": "unknown",
                    "property_satisfied": None,
                    "outcome": "not in the current corpus",
                },
            )
            for arm_summary in arm_summaries.values():
                arm_summary["h0"] = _h0(arm_summary, reference, want)
            summary[case]["queries"][query] = {
                "kind": kinds.get(case, {}).get(query, query),
                "expected": want,
                "arms": arm_summaries,
            }
    return summary


# --------------------------------------------------------------------------
# Runs
# --------------------------------------------------------------------------


def _run(root: Path, repetitions: int, warmups: int, run_id: str) -> Path:
    """Measure the corpus across every arm and write an immutable run.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param repetitions: Measured repetitions per sample.
    :type repetitions: int
    :param warmups: Discarded runs before measuring.
    :type warmups: int
    :param run_id: Directory name for this run; must not already exist.
    :type run_id: str
    :return: The directory the run was written to.
    :rtype: pathlib.Path
    :raises BenchmarkFailure: If the run directory already exists, the corpus
        fails its check, or the written run violates the schema.
    """
    _check(root)
    output = root / "outputs/runs" / run_id
    if output.exists():
        raise BenchmarkFailure(
            "%s already exists; a correction must create a new run rather than "
            "overwrite a saved one." % output.relative_to(_REPO_ROOT)
        )
    cases = []
    for case_dir in _case_dirs(root):
        case = _load_case(case_dir, [])
        if case is not None:
            cases.append((case_dir, case))
    candidate = _dirty_state()
    revisions = sorted(
        {arm["revision"] for arm in _ARMS if arm["revision"] is not None}
    )
    worktrees: Dict[str, Path] = {}
    raw_lines: List[str] = []
    grouped: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
    try:
        for revision in revisions:
            worktrees[revision] = _add_worktree(revision)
        for case_dir, case in cases:
            model = (case_dir / case["model"]).resolve()
            for query in case["queries"]:
                query_path = (case_dir / query["file"]).resolve()
                query_name = Path(query["file"]).stem
                for arm in _ARMS:
                    worktree = (
                        worktrees.get(arm["revision"]) if arm["revision"] else None
                    )
                    for _ in range(warmups):
                        _run_sample(model, query_path, arm, worktree)
                    samples = [
                        _run_sample(model, query_path, arm, worktree)
                        for _ in range(repetitions)
                    ]
                    grouped.setdefault(case["name"], {}).setdefault(query_name, {})[
                        arm["label"]
                    ] = samples
                    for index, sample in enumerate(samples):
                        raw_lines.append(
                            json.dumps(
                                {
                                    "case": case["name"],
                                    "query": query_name,
                                    "arm": arm["label"],
                                    "repetition": index,
                                    "record": sample,
                                },
                                sort_keys=True,
                            )
                        )
    finally:
        for tree in worktrees.values():
            diagnostic = _remove_worktree(tree)
            if diagnostic:
                print("warning: %s" % diagnostic, file=sys.stderr)

    expected = {
        case["name"]: {Path(q["file"]).stem: q["expected"] for q in case["queries"]}
        for _dir, case in cases
    }
    roles = {case["name"]: case["role"] for _dir, case in cases}
    kinds = {
        case["name"]: {Path(q["file"]).stem: q["kind"] for q in case["queries"]}
        for _dir, case in cases
    }
    manifest = {
        "schema": "bmc-solving-benchmark/v1",
        "run_id": run_id,
        "baseline": {"label": _BASELINE_LABEL, "commit": _BASELINE_COMMIT},
        "arms": [copy.deepcopy(arm) for arm in _ARMS],
        "reference_arm": _REFERENCE_ARM,
        "repetitions": repetitions,
        "warmups": warmups,
        "environment": _environment(),
        "candidate": candidate,
        "inputs": {
            str(path.relative_to(root / "cases")).replace("\\", "/"): _digest(path)
            for case_dir, _case in cases
            for path in sorted(case_dir.iterdir())
            if path.is_file()
        },
        "readme_digest": _digest(root / "README.md"),
        "expected": expected,
        "roles": roles,
        "kinds": kinds,
        "measurement_map": [
            {"metric": metric, "source": source, "note": note}
            for metric, source, note in _MEASUREMENT_MAP
        ],
    }
    summary = _aggregate(grouped, expected, roles, kinds, _REFERENCE_ARM)
    output.mkdir(parents=True)
    _write_run(output, manifest, summary, raw_lines)
    problems = _validate_run(root, output, _schema(root))
    if problems:
        raise BenchmarkFailure(
            "the run this tool just wrote violates its own schema:\n%s"
            % "\n".join(problems)
        )
    return output


def _write_run(
    output: Path,
    manifest: Dict[str, Any],
    summary: Dict[str, Any],
    raw_lines: Optional[List[str]],
) -> None:
    """Write the run files.

    :param output: Run directory.
    :type output: pathlib.Path
    :param manifest: Manifest content.
    :type manifest: Dict[str, Any]
    :param summary: Summary content.
    :type summary: Dict[str, Any]
    :param raw_lines: Raw JSON lines, or ``None`` to leave ``raw.jsonl`` alone.
    :type raw_lines: List[str], optional
    """
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if raw_lines is not None:
        (output / "raw.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(_report(manifest, summary), encoding="utf-8")


def _rebuild(root: Path, run_id: str) -> Path:
    """Rebuild one run's summary and report from its raw records.

    Proves the aggregation is a function of the recorded samples rather than of
    the process that produced them, which is what makes a saved run auditable.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param run_id: Directory name of a saved run.
    :type run_id: str
    :return: The run directory.
    :rtype: pathlib.Path
    :raises BenchmarkFailure: If the run or its records are missing.
    """
    output = root / "outputs/runs" / run_id
    raw = output / "raw.jsonl"
    manifest_path = output / "manifest.json"
    if not raw.exists() or not manifest_path.exists():
        raise BenchmarkFailure(
            "%s has no raw.jsonl and manifest.json to rebuild from." % output
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grouped: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
    for line in raw.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        grouped.setdefault(entry["case"], {}).setdefault(entry["query"], {}).setdefault(
            entry["arm"], []
        ).append(entry["record"])
    summary = _aggregate(
        grouped,
        manifest.get("expected", {}),
        manifest.get("roles", {}),
        manifest.get("kinds", {}),
        manifest.get("reference_arm", _REFERENCE_ARM),
    )
    _write_run(output, manifest, summary, None)
    return output


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _cell(value: Any) -> str:
    """Render one summary value for a Markdown table.

    :param value: A number, string, boolean, ``None`` or an unstable list.
    :return: Cell text.
    :rtype: str
    """
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return "%.1f" % value
    if isinstance(value, list):
        return "unstable: %s" % ", ".join(_cell(item) for item in value)
    return "`%s`" % value


def _report(manifest: Dict[str, Any], summary: Dict[str, Any]) -> str:
    """Render the human report for one run.

    :param manifest: The run manifest.
    :type manifest: Dict[str, Any]
    :param summary: The aggregated results.
    :type summary: Dict[str, Any]
    :return: Markdown report text.
    :rtype: str
    """
    arms = [arm["label"] for arm in manifest["arms"]]
    reference = manifest.get("reference_arm", _REFERENCE_ARM)
    lines = [
        "# BMC solving benchmark",
        "",
        "Run `%s`, candidate `%s`%s."
        % (
            manifest["run_id"],
            manifest["candidate"]["commit"][:12],
            " (dirty tree)" if manifest["candidate"]["dirty"] else "",
        ),
        "Baseline `%s` = `%s`; reference arm `%s`."
        % (manifest["baseline"]["label"], manifest["baseline"]["commit"], reference),
        "",
        "%d measured repetitions per sample after %d discarded warmups, each sample "
        "in its own interpreter." % (manifest["repetitions"], manifest["warmups"]),
        "",
        "Arms: %s."
        % "; ".join(
            "`%s` = %s%s"
            % (
                arm["label"],
                "revision `%s`" % arm["revision"][:12]
                if arm["revision"]
                else "working tree",
                " with options `%s`" % json.dumps(arm["options"], sort_keys=True)
                if arm["options"]
                else "",
            )
            for arm in manifest["arms"]
        ),
    ]

    rows: List[Tuple[str, str, Dict[str, Any]]] = [
        (case, query, entry)
        for case, case_summary in sorted(summary.items())
        for query, entry in sorted(case_summary["queries"].items())
    ]

    lines += [
        "",
        "## Correctness gate H0",
        "",
        "| Case | Query | expected | arm | status | satisfied | outcome | replay | H0 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    h0_failures = []
    for case, query, entry in rows:
        for arm in arms:
            arm_summary = entry["arms"].get(arm)
            if arm_summary is None:
                continue
            verdict = arm_summary["h0"]
            passed = (
                verdict["identical_to_reference"] and verdict["matches_expected_status"]
            )
            if not passed:
                h0_failures.append((case, query, arm))
            lines.append(
                "| `%s` | `%s` | `%s` | `%s` | %s | %s | %s | %s | %s |"
                % (
                    case,
                    query,
                    entry["expected"]["status"],
                    arm,
                    _cell(arm_summary.get("status")),
                    _cell(arm_summary.get("property_satisfied")),
                    _cell(arm_summary.get("outcome")),
                    _cell(arm_summary.get("replay_ok")),
                    "pass" if passed else "**FAIL**",
                )
            )

    for title, field in (
        ("Solve time by arm (p50 ms)", "solve_ms"),
        ("Build time by arm (p50 ms)", "build_ms"),
        ("Replay time by arm (p50 ms, sat only)", "replay_ms"),
    ):
        lines += [
            "",
            "## %s" % title,
            "",
            "| Case | Query | %s |" % " | ".join("`%s`" % arm for arm in arms),
            "|---|---|%s" % ("---|" * len(arms)),
        ]
        for case, query, entry in rows:
            cells = [
                _cell(entry["arms"].get(arm, {}).get(field, {}).get("p50"))
                for arm in arms
            ]
            lines.append("| `%s` | `%s` | %s |" % (case, query, " | ".join(cells)))

    lines += [
        "",
        "## Formula size and solver effort",
        "",
        "| Case | Query | %s |"
        % " | ".join("`%s` nodes / rlimit" % arm for arm in arms),
        "|---|---|%s" % ("---|" * len(arms)),
    ]
    for case, query, entry in rows:
        cells = [
            "%s / %s"
            % (
                _cell(entry["arms"].get(arm, {}).get("formula_dag_nodes")),
                _cell(entry["arms"].get(arm, {}).get("rlimit_count")),
            )
            for arm in arms
        ]
        lines.append("| `%s` | `%s` | %s |" % (case, query, " | ".join(cells)))

    lines += [
        "",
        "## Peak child RSS (bytes)",
        "",
        "| Case | Query | %s |" % " | ".join("`%s`" % arm for arm in arms),
        "|---|---|%s" % ("---|" * len(arms)),
    ]
    for case, query, entry in rows:
        cells = [
            _cell(entry["arms"].get(arm, {}).get("peak_child_rss_bytes"))
            for arm in arms
        ]
        lines.append("| `%s` | `%s` | %s |" % (case, query, " | ".join(cells)))

    failures = [
        (case, query, arm)
        for case, query, entry in rows
        for arm in arms
        if entry["arms"].get(arm, {}).get("failures")
    ]
    unstable = [
        (case, query, arm, entry["arms"][arm]["unstable_fields"])
        for case, query, entry in rows
        for arm in arms
        if entry["arms"].get(arm, {}).get("unstable_fields")
    ]
    lines += ["", "## Failures and instability", ""]
    lines.append(
        "Failed samples: %s."
        % (
            ", ".join("%s/%s/%s" % triple for triple in failures)
            if failures
            else "none"
        )
    )
    lines.append(
        "Unstable published fields: %s."
        % (
            "; ".join("%s/%s/%s: %s" % item for item in unstable)
            if unstable
            else "none"
        )
    )

    lines += ["", "## Thresholds", ""]
    lines.append(
        "H0 (correctness): %s."
        % (
            "**pass** for every arm and query"
            if not h0_failures
            else "**FAIL** at %s"
            % ", ".join("%s/%s/%s" % triple for triple in h0_failures)
        )
    )
    option_arms = [arm for arm in manifest["arms"] if arm["options"]]
    if option_arms:
        lines.append(
            "T1-T3 apply to the option arms %s; their verdicts are evaluated by the "
            "sub-PR that introduces each option, against the pre-registered rows in README.md."
            % ", ".join("`%s`" % arm["label"] for arm in option_arms)
        )
    else:
        lines.append(
            "T1-T3 are not evaluated: no arm sets an option, so this run only establishes the baseline and default distributions."
        )

    lines += [
        "",
        "## Measurement map",
        "",
        "| Metric | Source | Note |",
        "|---|---|---|",
    ]
    for entry in manifest["measurement_map"]:
        lines.append(
            "| `%s` | `%s` | %s |" % (entry["metric"], entry["source"], entry["note"])
        )
    lines += [
        "",
        "Reconstruct this report from the raw records with:",
        "",
        "```bash",
        "python tools/run_bmc_solving_benchmark.py --rebuild %s" % manifest["run_id"],
        "```",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Self-test: every gate above must be able to fail.
# --------------------------------------------------------------------------


def _mutations() -> List[Tuple[str, str, Any]]:
    """Return the corpus mutations ``--check`` must reject.

    Each entry is ``(name, expected substring of the failure, mutate(root))``.

    :return: Mutation table.
    :rtype: List[Tuple[str, str, Callable[[pathlib.Path], None]]]
    """

    def first_case(root: Path) -> Path:
        return sorted(p for p in (root / "cases").iterdir() if p.is_dir())[0]

    def edit_case_json(root: Path, edit) -> None:
        path = first_case(root) / "case.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        edit(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def missing_case_json(root: Path) -> None:
        (first_case(root) / "case.json").unlink()

    def missing_model(root: Path) -> None:
        (first_case(root) / "model.fcstm").unlink()

    def missing_query_file(root: Path) -> None:
        (first_case(root) / "reach.fbmcq").unlink()

    def expected_missing_status(root: Path) -> None:
        edit_case_json(root, lambda d: d["queries"][0]["expected"].pop("status"))

    def expected_bad_status(root: Path) -> None:
        edit_case_json(
            root, lambda d: d["queries"][0]["expected"].__setitem__("status", "maybe")
        )

    def name_mismatch(root: Path) -> None:
        edit_case_json(root, lambda d: d.__setitem__("name", "somebody_else"))

    def bad_role(root: Path) -> None:
        edit_case_json(root, lambda d: d.__setitem__("role", "decorative"))

    def model_does_not_load(root: Path) -> None:
        (first_case(root) / "model.fcstm").write_text("state {", encoding="utf-8")

    def readme_missing_threshold(root: Path) -> None:
        readme = root / "README.md"
        lines = [
            line
            for line in readme.read_text(encoding="utf-8").splitlines()
            if not line.startswith("| T3 ")
        ]
        readme.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def readme_missing_case(root: Path) -> None:
        readme = root / "README.md"
        name = first_case(root).name
        readme.write_text(
            readme.read_text(encoding="utf-8").replace("`%s`" % name, "`renamed`"),
            encoding="utf-8",
        )

    def schema_invalid_json(root: Path) -> None:
        (root / "schema.json").write_text("{", encoding="utf-8")

    def run_violates_schema(root: Path) -> None:
        bogus = root / "outputs/runs/bogus"
        bogus.mkdir(parents=True)
        (bogus / "manifest.json").write_text("{}", encoding="utf-8")
        (bogus / "summary.json").write_text("{}", encoding="utf-8")

    return [
        ("missing_case_json", "case.json", missing_case_json),
        ("missing_model", "model.fcstm", missing_model),
        ("missing_query_file", "reach.fbmcq", missing_query_file),
        ("expected_missing_status", "expected.status", expected_missing_status),
        ("expected_bad_status", "expected.status", expected_bad_status),
        ("name_mismatch", "name", name_mismatch),
        ("bad_role", "role", bad_role),
        ("model_does_not_load", "load", model_does_not_load),
        ("readme_missing_threshold", "T3", readme_missing_threshold),
        ("readme_missing_case", "README", readme_missing_case),
        ("schema_invalid_json", "schema.json", schema_invalid_json),
        ("run_violates_schema", "schema", run_violates_schema),
    ]


def _synthetic_run(root: Path, run_id: str) -> None:
    """Write a tiny raw.jsonl and manifest so a rebuild can be exercised.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param run_id: Run directory name to create.
    :type run_id: str
    """
    output = root / "outputs/runs" / run_id
    output.mkdir(parents=True)
    lines = []
    for case, query, expected in (
        ("alpha", "reach", "sat"),
        ("beta", "forbid", "unsat"),
    ):
        for arm in _ARMS:
            for repetition, solve_ms in enumerate((3.0, 5.0, 4.0)):
                record = {
                    "build_ms": 10.0 + repetition,
                    "solve_ms": solve_ms,
                    "replay_ms": 1.0 if expected == "sat" else None,
                    "total_elapsed_ms": solve_ms + 0.5,
                    "formula_dag_nodes": 100,
                    "rlimit_count": 2000,
                    "status": expected,
                    "property_satisfied": expected == "sat",
                    "outcome": "witness_found" if expected == "sat" else "no_witness",
                    "replay_ok": True if expected == "sat" else None,
                    "peak_rss_bytes": 50_000_000,
                }
                lines.append(
                    json.dumps(
                        {
                            "case": case,
                            "query": query,
                            "arm": arm["label"],
                            "repetition": repetition,
                            "record": record,
                        },
                        sort_keys=True,
                    )
                )
    manifest = {
        "schema": "bmc-solving-benchmark/v1",
        "run_id": run_id,
        "baseline": {"label": _BASELINE_LABEL, "commit": _BASELINE_COMMIT},
        "arms": [copy.deepcopy(arm) for arm in _ARMS],
        "reference_arm": _REFERENCE_ARM,
        "repetitions": 3,
        "warmups": 0,
        "environment": {
            "python": "0",
            "python_implementation": "x",
            "z3": "0",
            "platform": "x",
            "machine": "x",
            "processor": "x",
        },
        "candidate": {"commit": "0" * 40, "dirty": False, "porcelain": []},
        "inputs": {},
        "readme_digest": "0" * 64,
        "roles": {"alpha": "llm_generated", "beta": "slicing_positive"},
        "kinds": {"alpha": {"reach": "reach"}, "beta": {"forbid": "forbid"}},
        "expected": {
            "alpha": {
                "reach": {
                    "status": "sat",
                    "property_satisfied": True,
                    "outcome": "witness_found",
                }
            },
            "beta": {
                "forbid": {
                    "status": "unsat",
                    "property_satisfied": True,
                    "outcome": "no_witness",
                }
            },
        },
        "measurement_map": [
            {"metric": m, "source": s, "note": n} for m, s, n in _MEASUREMENT_MAP
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "raw.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _self_test() -> List[str]:
    """Prove every ``--check`` gate can fail and that a rebuild is a pure function.

    :return: Problems found; empty when the self-test passes.
    :rtype: List[str]
    """
    problems: List[str] = []
    source = _bench_root()
    try:
        _check(source)
    except BenchmarkFailure as err:
        # The pristine corpus must pass before any mutation is meaningful.
        return ["the checked-in corpus itself fails --check:\n%s" % err]

    def pristine_copy(into: Path) -> Path:
        copied = into / "bench"
        shutil.copytree(source, copied, ignore=shutil.ignore_patterns("runs"))
        (copied / "outputs/runs").mkdir(parents=True, exist_ok=True)
        return copied

    for name, needle, mutate in _mutations():
        scratch = tempfile.mkdtemp(prefix="pyfcstm-bmc-solving-selftest-")
        try:
            root = pristine_copy(Path(scratch))
            mutate(root)
            try:
                _check(root)
            except BenchmarkFailure as err:
                if needle not in str(err):
                    problems.append(
                        "mutation %s failed --check, but the message %r does not "
                        "mention %r" % (name, str(err), needle)
                    )
            else:
                problems.append(
                    "mutation %s passed --check; the gate cannot fail" % name
                )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    scratch = tempfile.mkdtemp(prefix="pyfcstm-bmc-solving-selftest-")
    try:
        root = pristine_copy(Path(scratch))
        _synthetic_run(root, "synthetic")
        first = _rebuild(root, "synthetic")
        summary_a = (first / "summary.json").read_bytes()
        report_a = (first / "report.md").read_bytes()
        second = _rebuild(root, "synthetic")
        if (second / "summary.json").read_bytes() != summary_a:
            problems.append(
                "rebuilding the same raw records twice changed summary.json"
            )
        if (second / "report.md").read_bytes() != report_a:
            problems.append("rebuilding the same raw records twice changed report.md")
        summary = json.loads(summary_a.decode("utf-8"))
        arms = summary["alpha"]["queries"]["reach"]["arms"]
        if arms["default"]["solve_ms"]["p50"] != 4.0:
            problems.append("summary p50 of (3, 5, 4) is not 4.0")
        if arms[_BASELINE_LABEL]["h0"] != {
            "identical_to_reference": True,
            "matches_expected_status": True,
        }:
            problems.append("H0 verdict for an identical arm is not the passing one")
        _check(root)
    except BenchmarkFailure as err:
        problems.append("a synthetic run did not pass --check: %s" % err)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the benchmark from the command line.

    :param argv: Argument list, defaults to ``None`` for ``sys.argv[1:]``
    :type argv: Sequence[str], optional
    :return: ``0`` on success, ``1`` on a controlled failure.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--rebuild", metavar="RUN_ID")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    if not (args.check or args.self_test or args.run or args.rebuild):
        parser.error("Pass --check, --self-test, --run, or --rebuild RUN_ID.")
    if args.self_test:
        problems = _self_test()
        if problems:
            print(
                "Benchmark self-test failed:\n%s"
                % "\n".join("- %s" % p for p in problems)
            )
            return 1
        print(
            "Every --check gate can fail, and a rebuild is a pure function of raw.jsonl."
        )
    if args.check:
        try:
            _check(_bench_root())
        except BenchmarkFailure as err:
            # The corpus, thresholds, or a saved run do not match what the runner measures.
            print("Benchmark self-check failed:\n%s" % err)
            return 1
        print("Benchmark corpus, arms, thresholds, and layout are consistent.")
    if args.run:
        run_id = args.run_id or _dirty_state()["commit"][:12]
        try:
            output = _run(_bench_root(), args.repetitions, args.warmups, run_id)
        except BenchmarkFailure as err:
            # A saved run is immutable; this refuses rather than overwriting.
            print("Benchmark run failed:\n%s" % err)
            return 1
        print("Wrote %s" % (output / "report.md").relative_to(_REPO_ROOT))
    if args.rebuild:
        try:
            output = _rebuild(_bench_root(), args.rebuild)
        except BenchmarkFailure as err:
            # The run is missing the records a rebuild needs.
            print("Benchmark rebuild failed:\n%s" % err)
            return 1
        print("Rebuilt %s" % (output / "report.md").relative_to(_REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
