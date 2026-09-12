"""
Measure what BMC solving costs, and whether an encoding or solver option changes it.

Every user-visible BMC option changes how the formula is built or how Z3 is
constructed, never what a property means.  So the question for any such option
is the same: does every answer stay identical, and what does it cost?  This
runner answers it with arms that are option sets applied to one revision, plus
a baseline arm that is an earlier revision, so an overhead the option
infrastructure adds on every run is visible separately from the option itself.

Every arm runs from a detached worktree of its commit, including the arm for the
current revision.  The child reports which ``pyfcstm`` it imported and the parent
refuses a sample that did not come from the worktree, so the recorded commit is
the code that ran, whatever sits untracked in the working tree.

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
import math
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Running ``python tools/<script>.py`` puts ``tools/`` first on ``sys.path``, not
# the repository root, and the package is not installed into the interpreter.
# The corpus check loads models and binds queries through the public API, so
# the root has to be importable here.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

#: Where the corpus, schema, and immutable run outputs live.
_BENCH_ROOT = Path("benchmarks/bmc/solving")

#: The revision the contrast is measured against: the last ``main`` commit before
#: any solving option existed, so every option arm can be read against it.
_BASELINE_COMMIT = "0cc43647ad85c99347fbdd8eab0259279a5f40d0"
_BASELINE_LABEL = "baseline-" + _BASELINE_COMMIT[:8]

#: The arm every other arm is compared against under the correctness gate.
_REFERENCE_ARM = "default"

#: The arms, in the order a reader should compare them.
#:
#: ``revision`` is a commit the child runs from a detached worktree; ``None``
#: means the current ``HEAD``, resolved when the run starts.  ``options`` has two
#: parts the child forwards unchanged: ``compile`` becomes ``BmcOptions(**...)``
#: and ``solve`` becomes keyword arguments of ``solve_bmc_property``.  A key the
#: production API does not know raises ``TypeError`` there, so an arm cannot
#: measure the default under a new name.
_ARMS: Tuple[Dict[str, Any], ...] = (
    {
        "label": _BASELINE_LABEL,
        "revision": _BASELINE_COMMIT,
        "options": {"compile": {}, "solve": {}},
    },
    {
        "label": _REFERENCE_ARM,
        "revision": None,
        "options": {"compile": {}, "solve": {}},
    },
    {
        "label": "logic",
        "revision": None,
        "options": {"compile": {}, "solve": {"solver_profile": "logic"}},
    },
    {
        "label": "tactic",
        "revision": None,
        "options": {"compile": {}, "solve": {"solver_profile": "tactic"}},
    },
    {
        "label": "cone_slicing",
        "revision": None,
        "options": {"compile": {"cone_slicing": True}, "solve": {}},
    },
    {
        "label": "slicing-2db08911",
        "revision": "2db089114bb5137aaf5a94d18af9949066f4bb6c",
        "options": {"compile": {"cone_slicing": True}, "solve": {}},
    },
)

#: Numeric form of the pre-registered solver thresholds, copied into each run.
_SOLVER_THRESHOLDS = {
    "logic": {
        "id": "T1",
        "minimum_median_improvement": 0.15,
        "maximum_query_regression": 0.10,
    },
    "tactic": {
        "id": "T2",
        "minimum_median_improvement": 0.15,
        "maximum_query_regression": 0.10,
    },
}

# Frozen T3 thresholds, separate from the historical solver-only manifests.
_SLICING_THRESHOLDS = {
    "id": "T3",
    "minimum_dag_reduction": 0.20,
    "maximum_solve_regression": 0.05,
    "maximum_unsliced_regression": 0.05,
    "maximum_fallbacks": 0,
}

#: Threshold ids the README must pre-register before the first run.
_THRESHOLD_IDS = ("H0", "T1", "T2", "T3")

#: Case roles, and what each one is in the corpus for.
_ROLES = ("llm_generated", "slicing_positive", "definedness_trap", "abstract_skip")

_STATUSES = ("sat", "unsat", "unknown", "timeout")

_EXPECTED_KEYS = ("status", "property_satisfied", "outcome")

#: How each published metric is obtained.
_MEASUREMENT_MAP: Tuple[Tuple[str, str, str], ...] = (
    (
        "build_ms",
        "compile_bmc_query wall time in the child",
        "prepare, core relation, and property compilation; the region an "
        "encoding option changes",
    ),
    (
        "solve_ms",
        "solve_bmc_property wall time in the child",
        "staged solving plus internal slicing verification and any full-model retry",
    ),
    (
        "replay_ms",
        "decode_bmc_result_trace + replay_bmc_witness wall time in the child",
        "primary SAT witness and response incomplete suffix, when present",
    ),
    (
        "api_total_ms",
        "wall time from loading the model/query through final witness replay",
        "fresh-process public API path; excludes interpreter startup, imports, "
        "JSON serialization and benchmark diagnostics",
    ),
    (
        "pipeline_ms",
        "build_ms + solve_ms + (replay_ms or zero), per sample",
        "includes internal verification and external replay without "
        "double-counting; excludes model/query file loading",
    ),
    (
        "total_elapsed_ms",
        "result.total_elapsed_ms",
        "production ledger; the solver's own accounting of the whole solve",
    ),
    (
        "formula_dag_nodes",
        "distinct Z3 AST ids reachable from core.core and objective_formula",
        "a size measure that does not depend on printing or on the process; "
        "what a slice shrinks.  Counted after the peak memory reading",
    ),
    (
        "status / property_satisfied / outcome / replay_ok",
        "result fields and replay.ok",
        "the correctness gate compares these between arms and against case.json",
    ),
    (
        "peak_child_rss_bytes",
        "resource.getrusage(RUSAGE_SELF).ru_maxrss in the child, read right "
        "after replay",
        "the kernel high-water mark of the production path; absent where the "
        "resource module is unavailable, never zero",
    ),
    (
        "solver_statistics",
        "result.solver_statistics immediately after the primary check",
        "actual Z3 statistics; keys vary by profile/version. rlimit count and "
        "num allocs are context-wide, not per-query work and not adoption gates",
    ),
    (
        "pyfcstm_file",
        "pyfcstm.__file__ in the child",
        "not published; the parent refuses a sample whose package did not come "
        "from the arm's worktree",
    ),
)


class BenchmarkFailure(RuntimeError):
    """Raised when the corpus, layout, thresholds, or a run is inconsistent."""


def _bench_root() -> Path:
    """Return the absolute benchmark directory in this checkout.

    :return: Benchmark directory.
    :rtype: pathlib.Path
    """
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
    :return: The parsed case, or ``None`` when it cannot be used further.
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
    if not isinstance(case, dict):
        problems.append("%s/case.json is not an object." % label)
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
    if not isinstance(model_name, str) or not model_name:
        problems.append("%s/case.json names no model file." % label)
    elif not (case_dir / model_name).exists():
        problems.append("%s/%s is missing." % (label, model_name))
    queries = case.get("queries")
    if not isinstance(queries, list) or not queries:
        problems.append("%s/case.json lists no queries." % label)
        return None
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
        for key in _EXPECTED_KEYS:
            if key not in expected:
                problems.append("%s expected.%s is missing." % (where, key))
        extra = sorted(set(expected) - set(_EXPECTED_KEYS))
        if extra:
            problems.append(
                "%s expected has keys the schema does not: %s." % (where, extra)
            )
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
    :rtype: Optional[pyfcstm.model.StateMachine]
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

    Binding stops before the relation is built, so a construct the encoder
    refuses is only found by ``--run``; compiling every query here would cost
    as much as a measurement.

    :param case_dir: Case directory.
    :type case_dir: pathlib.Path
    :param case: Parsed ``case.json``.
    :type case: Dict[str, Any]
    :param model: Loaded state machine.
    :type model: pyfcstm.model.StateMachine
    :param problems: Accumulates human-readable problems.
    :type problems: List[str]
    :return: ``None``.
    :rtype: None
    """
    from pyfcstm.bmc import prepare_bmc_query
    from pyfcstm.bmc.errors import (
        BmcBuildError,
        BmcQueryParseError,
        InvalidBmcDomain,
        InvalidBmcQuery,
    )

    for query in case["queries"]:
        file_name = query.get("file")
        if not isinstance(file_name, str) or not (case_dir / file_name).exists():
            continue
        text = (case_dir / file_name).read_text(encoding="utf-8")
        try:
            prepare_bmc_query(model, text, query_source_path=str(case_dir / file_name))
        except (
            BmcQueryParseError,
            InvalidBmcQuery,
            InvalidBmcDomain,
            BmcBuildError,
        ) as err:
            # BmcQueryParseError: malformed FBMCQ text; InvalidBmcQuery: a state,
            # variable or event the model does not have; InvalidBmcDomain: the
            # bounded domain cannot be built for this model and bound;
            # BmcBuildError: option policy or malformed input.
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
        or reference[0]["options"] != {"compile": {}, "solve": {}}
    ):
        problems.append(
            "Exactly one arm must be the reference: the current revision with no options."
        )
    for arm in _ARMS:
        if set(arm["options"]) != {"compile", "solve"}:
            problems.append(
                "Arm %s must carry compile and solve option sets." % arm["label"]
            )
    if len(_BASELINE_COMMIT) != 40:
        problems.append("The baseline commit must be recorded in full.")
    names = [name for name, _source, _note in _MEASUREMENT_MAP]
    if len(names) != len(set(names)):
        problems.append("The measurement map has a duplicate metric name.")
    return problems


def _schema(root: Path) -> Dict[str, Any]:
    """Load ``schema.json``.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :return: The parsed schema.
    :rtype: Dict[str, Any]
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


def _validate_documents(
    label: str, documents: Dict[str, Any], schema: Dict[str, Any], notes: List[str]
) -> List[str]:
    """Validate ``{"manifest": ..., "summary": ...}`` against the schema.

    :param label: Where the documents came from, for messages.
    :type label: str
    :param documents: Manifest and summary.
    :type documents: Dict[str, Any]
    :param schema: Parsed ``schema.json``.
    :type schema: Dict[str, Any]
    :param notes: Accumulates non-fatal remarks, such as a degraded check.
    :type notes: List[str]
    :return: Problems found.
    :rtype: List[str]
    """
    try:
        import jsonschema
    except ImportError:
        # Documented degradation: the structural check needs the optional
        # development dependency; without it only the schema tag is read, and
        # the caller is told so instead of being shown a clean result.
        notes.append(
            "jsonschema is not installed, so %s was checked for its schema tag only."
            % label
        )
        tag = (
            documents["manifest"].get("schema")
            if isinstance(documents["manifest"], dict)
            else None
        )
        if tag != schema["$defs"]["manifest"]["properties"]["schema"]["const"]:
            return ["%s does not carry the schema tag." % label]
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


def _validate_run(
    root: Path,
    run_dir: Path,
    schema: Dict[str, Any],
    live_inputs: Dict[str, str],
    live_readme: str,
    notes: List[str],
) -> List[str]:
    """Validate one saved run and say whether the corpus has moved since.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param run_dir: One ``outputs/runs/<run-id>`` directory.
    :type run_dir: pathlib.Path
    :param schema: Parsed ``schema.json``.
    :type schema: Dict[str, Any]
    :param live_inputs: Digests of the corpus as it is now.
    :type live_inputs: Dict[str, str]
    :param live_readme: Digest of the README as it is now.
    :type live_readme: str
    :param notes: Accumulates non-fatal remarks.
    :type notes: List[str]
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
    if not (run_dir / "raw.jsonl").exists():
        return ["%s/raw.jsonl is missing, so the run cannot be rebuilt." % label]
    problems = _validate_documents(label, documents, schema, notes)
    manifest = documents["manifest"]
    if isinstance(manifest, dict):
        moved = sorted(
            path
            for path in set(manifest.get("inputs", {})) | set(live_inputs)
            if manifest.get("inputs", {}).get(path) != live_inputs.get(path)
        )
        if moved:
            notes.append(
                "%s was measured against a corpus that differs now at: %s."
                % (label, ", ".join(moved[:6]) + (" ..." if len(moved) > 6 else ""))
            )
        if manifest.get("readme_digest") != live_readme:
            notes.append("%s was measured under an earlier README.md." % label)
    return problems


def _live_inputs(root: Path) -> Dict[str, str]:
    """Digest every corpus file, keyed by path relative to ``cases/``.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :return: Path to digest.
    :rtype: Dict[str, str]
    """
    return {
        path.relative_to(root / "cases").as_posix(): _digest(path)
        for case_dir in _case_dirs(root)
        for path in sorted(case_dir.iterdir())
        if path.is_file()
    }


def _check(root: Path) -> List[str]:
    """Confirm the corpus, arms, thresholds, schema and saved runs are consistent.

    Nothing here solves a query: the check must stay cheap enough to run before
    every measurement.  Models are loaded and inspected, queries are bound, and
    saved runs are validated against ``schema.json``.

    :param root: Benchmark directory to check.
    :type root: pathlib.Path
    :return: Non-fatal notes for the caller to print.
    :rtype: List[str]
    :raises BenchmarkFailure: Listing every inconsistency found.
    """
    problems: List[str] = []
    notes: List[str] = []
    for relative in ("cases", "outputs/runs", "README.md"):
        if not (root / relative).exists():
            problems.append("%s/%s is missing." % (_BENCH_ROOT, relative))
    schema: Optional[Dict[str, Any]] = None
    try:
        schema = _schema(root)
    except BenchmarkFailure as err:
        # Reported alongside the other problems rather than first and alone.
        problems.append(str(err))
    case_dirs = _case_dirs(root)
    if not case_dirs:
        problems.append("%s/cases holds no case directory." % _BENCH_ROOT)
    for case_dir in case_dirs:
        case = _load_case(case_dir, problems)
        if case is None or not isinstance(case.get("model"), str):
            continue
        if not (case_dir / case["model"]).exists():
            continue
        model = _load_model_for_check(case_dir, case, problems)
        if model is not None:
            _check_queries_bind(case_dir, case, model, problems)
    problems.extend(_readme_problems(root, [path.name for path in case_dirs]))
    problems.extend(_arm_problems())
    runs = root / "outputs/runs"
    if schema is not None and runs.is_dir() and (root / "README.md").exists():
        live_inputs = _live_inputs(root)
        live_readme = _digest(root / "README.md")
        for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
            problems.extend(
                _validate_run(root, run_dir, schema, live_inputs, live_readme, notes)
            )
    if problems:
        raise BenchmarkFailure("\n".join("- %s" % item for item in problems))
    return notes


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def _child_script() -> str:
    """Return the program each sample runs in its own interpreter.

    It prints one JSON object on standard output.  Keeping it here rather than in
    a separate file means the measured code and the measurement stay together.
    The child runs with the arm's worktree as its working directory, so
    ``import pyfcstm`` resolves to that revision; every path it receives is
    absolute, and it reports the package it imported so the parent can refuse a
    sample that came from anywhere else.

    :return: Python source for the child process.
    :rtype: str
    """
    return r"""
import json, sys, time
import pyfcstm
from pyfcstm.model import load_state_machine_from_file
from pyfcstm.bmc import (
    BmcOptions, compile_bmc_query, solve_bmc_property,
    decode_bmc_result_trace, replay_bmc_witness,
)

model_path, query_path, options = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
compile_options = options.get("compile") or {}
solve_options = options.get("solve") or {}
# Both sets go straight to the production API.  An unknown key raises TypeError
# there, which is the whole guard: an arm cannot measure the default under a
# new name, and an empty set calls the API exactly as an older revision expects.
bmc_options = BmcOptions(**compile_options) if compile_options else None

api_started = time.perf_counter()
model = load_state_machine_from_file(model_path)
query_text = open(query_path, encoding="utf-8").read()

started = time.perf_counter()
formula = compile_bmc_query(
    model, query_text, options=bmc_options, query_source_path=query_path
)
build_ms = (time.perf_counter() - started) * 1000.0

started = time.perf_counter()
result = solve_bmc_property(formula, **solve_options)
solve_ms = (time.perf_counter() - started) * 1000.0

replay_ms = None
replay_ok = None
if result.status == "sat":
    started = time.perf_counter()
    witness = decode_bmc_result_trace(result, source="primary")
    replay_ok = replay_bmc_witness(model, witness).ok
    replay_ms = (time.perf_counter() - started) * 1000.0

suffix_replay_ok = None
if result.incomplete_model is not None:
    started = time.perf_counter()
    suffix = decode_bmc_result_trace(result, source="incomplete_suffix")
    suffix_replay_ok = replay_bmc_witness(model, suffix).ok
    replay_ms = (replay_ms or 0.0) + (time.perf_counter() - started) * 1000.0

api_total_ms = (time.perf_counter() - api_started) * 1000.0

# Peak memory is read here, before the size walk below allocates anything, so
# it describes the production path alone.
try:
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak = peak if sys.platform == "darwin" else peak * 1024
except ImportError:
    # Windows has no resource module; the metric is reported absent, never zero.
    peak = None


def dag_nodes(*roots):
    import z3
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


metadata = {}
if hasattr(result, "solver_statistics"):
    metadata = {"solver_statistics": dict(result.solver_statistics),
                "solver_profile": result.solver_profile,
                "solver_logic": result.solver_logic}
cone = result.to_canonical().get("cone_slicing")
if cone is not None:
    metadata["cone_slicing"] = cone
print(json.dumps({
    **metadata,
    "build_solve_ms": build_ms + solve_ms,
    "pipeline_ms": build_ms + solve_ms + (replay_ms or 0.0),
    "api_total_ms": api_total_ms,
    "suffix_replay_ok": suffix_replay_ok,
    "pyfcstm_file": pyfcstm.__file__,
    "build_ms": build_ms,
    "solve_ms": solve_ms,
    "replay_ms": replay_ms,
    "total_elapsed_ms": result.total_elapsed_ms,
    "formula_dag_nodes": dag_nodes(formula.core.core, formula.objective_formula),
    "status": result.status,
    "property_satisfied": result.property_satisfied,
    "outcome": result.outcome,
    "replay_ok": replay_ok,
    "peak_rss_bytes": peak,
}))
"""


def _run_sample(
    model: Path, query: Path, options: Dict[str, Any], worktree: Path
) -> Dict[str, Any]:
    """Run one sample in a fresh interpreter and return what it measured.

    :param model: Absolute path to the ``.fcstm`` model.
    :type model: pathlib.Path
    :param query: Absolute path to the ``.fbmcq`` query.
    :type query: pathlib.Path
    :param options: The arm's ``compile`` and ``solve`` option sets.
    :type options: Dict[str, Any]
    :param worktree: Checkout the child runs from.
    :type worktree: pathlib.Path
    :return: The child's record, or a record with an ``error`` key.
    :rtype: Dict[str, Any]
    """
    command = [
        sys.executable,
        "-c",
        _child_script(),
        str(model),
        str(query),
        json.dumps(options, sort_keys=True),
    ]
    # subprocess.run kills the child if this process is interrupted while
    # waiting, so a Ctrl-C does not leave a Z3 solve running in the background.
    completed = subprocess.run(
        command,
        cwd=str(worktree),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        return {
            "error": "child exited %d" % completed.returncode,
            "stderr": completed.stderr.strip()[:2000],
        }
    try:
        record = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        # A child that crashed before printing leaves stderr as the only clue.
        return {"error": "child produced no JSON: %s" % err, "stderr": completed.stderr}
    imported = str(record.get("pyfcstm_file", ""))
    if not imported.startswith(str(worktree.resolve())):
        return {
            "error": "child imported pyfcstm from %s, not from the arm's worktree %s"
            % (imported, worktree)
        }
    return record


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
    parent = Path(tempfile.mkdtemp(prefix="pyfcstm-bmc-solving-"))
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


def _candidate_state() -> Dict[str, Any]:
    """Return the commit ``HEAD`` names and what the working tree looked like.

    The measurement itself runs from worktrees of recorded commits, so the
    working tree cannot reach it; the listing is kept so a reader can see what
    was uncommitted at the time.

    :return: ``commit``, ``dirty`` and the porcelain listing.
    :rtype: Dict[str, Any]
    """
    porcelain = _git("status", "--porcelain")
    lines = porcelain.splitlines() if porcelain else []
    return {
        "commit": _git("rev-parse", "HEAD"),
        "dirty": bool(lines),
        "porcelain": lines,
    }


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------

_TIMING_FIELDS = ("build_ms", "solve_ms", "replay_ms", "total_elapsed_ms")
_OBSERVED_FIELDS = (
    "formula_dag_nodes",
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
    if any("solver_statistics" in item for item in good):
        keys = sorted(
            {key for item in good for key in item.get("solver_statistics", {})}
        )
        summary["solver_statistics"] = {
            key: _distribution(
                [
                    item["solver_statistics"][key]
                    for item in good
                    if key in item.get("solver_statistics", {})
                ]
            )
            for key in keys
        }
        for key in ("solver_profile", "solver_logic"):
            summary[key] = sorted({item.get(key) for item in good}, key=str)
    # Optional fields keep historical summaries byte-for-byte rebuildable.
    for field in ("build_solve_ms", "pipeline_ms", "api_total_ms"):
        if any(field in item for item in good):
            summary[field] = _distribution(
                [item[field] for item in good if field in item]
            )
    for field in ("cone_slicing", "suffix_replay_ok"):
        if any(field in item for item in good):
            observed = sorted(
                {json.dumps(item.get(field), sort_keys=True) for item in good}
            )
            summary[field] = (
                json.loads(observed[0])
                if len(observed) == 1
                else [json.loads(value) for value in observed]
            )
            if len(observed) != 1:
                summary.setdefault("unstable_fields", []).append(field)
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

    A failed sample fails both parts: a verdict built on the samples that
    happened to survive is not a verdict about the arm.

    :param arm_summary: Summary of the arm under test.
    :type arm_summary: Dict[str, Any]
    :param reference: Summary of the reference arm for the same query.
    :type reference: Dict[str, Any]
    :param expected: ``case.json`` expectation for the query.
    :type expected: Dict[str, Any]
    :return: Whether the published fields match the reference, and whether
        status, property_satisfied and outcome match the expectation.
    :rtype: Dict[str, bool]
    """
    healthy = (
        arm_summary.get("samples", 0) > 0
        and arm_summary.get("failures", 0) == 0
        and reference.get("samples", 0) > 0
        and reference.get("failures", 0) == 0
        and arm_summary.get("suffix_replay_ok") in (None, True)
        and reference.get("suffix_replay_ok") in (None, True)
        and (arm_summary.get("status") != "sat" or arm_summary.get("replay_ok") is True)
        and (reference.get("status") != "sat" or reference.get("replay_ok") is True)
    )
    unstable = set(arm_summary.get("unstable_fields", ())) | set(
        reference.get("unstable_fields", ())
    )
    identical = (
        healthy
        and not (unstable & set(_H0_FIELDS))
        and all(arm_summary.get(field) == reference.get(field) for field in _H0_FIELDS)
    )
    matches = (
        arm_summary.get("samples", 0) > 0
        and arm_summary.get("failures", 0) == 0
        and not (unstable & set(_EXPECTED_KEYS))
        and all(arm_summary.get(key) == expected.get(key) for key in _EXPECTED_KEYS)
    )
    return {"identical_to_reference": identical, "matches_expected": matches}


def _aggregate(
    grouped: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]],
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    """Build ``summary.json`` content from grouped raw records and the manifest.

    :param grouped: ``case -> query -> arm -> samples``.
    :type grouped: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]]
    :param manifest: The run manifest, for expectations, roles and kinds.
    :type manifest: Dict[str, Any]
    :return: Summary dictionary.
    :rtype: Dict[str, Any]
    """
    expected = manifest.get("expected", {})
    roles = manifest.get("roles", {})
    kinds = manifest.get("kinds", {})
    reference_arm = manifest.get("reference_arm", _REFERENCE_ARM)
    summary: Dict[str, Any] = {}
    for case, queries in sorted(grouped.items()):
        summary[case] = {"role": roles.get(case, "unknown"), "queries": {}}
        for query, arms in sorted(queries.items()):
            arm_summaries = {arm: _summarize(samples) for arm, samples in arms.items()}
            reference = arm_summaries.get(reference_arm, {})
            want = expected.get(case, {}).get(query, {})
            if case not in expected or query not in expected[case]:
                raise BenchmarkFailure(
                    "raw.jsonl holds %s/%s, which the manifest has no expectation for."
                    % (case, query)
                )
            for arm_summary in arm_summaries.values():
                arm_summary["h0"] = _h0(arm_summary, reference, want)
            summary[case]["queries"][query] = {
                "kind": kinds.get(case, {}).get(query, query),
                "expected": want,
                "arms": arm_summaries,
            }
    return summary


def _solver_comparison(summary, arm, reference, threshold):
    """Apply a run's frozen solver adoption threshold to every measured query.

    :param summary: Aggregated query measurements.
    :param arm: Candidate arm label.
    :param reference: Default arm label.
    :param threshold: Numeric threshold copied into the run manifest.
    :return: Median improvement, worst regression, H0 and adoption decisions.
    :rtype: Dict[str, Any]
    """
    candidates, references, regressions = [], [], []
    h0 = True
    for case in summary.values():
        for query in case["queries"].values():
            candidate = query["arms"].get(arm, {})
            baseline = query["arms"].get(reference, {})
            a = candidate.get("solve_ms", {}).get("p50")
            b = baseline.get("solve_ms", {}).get("p50")
            h0 = h0 and candidate.get("h0", {}).get("identical_to_reference", False)
            h0 = h0 and candidate.get("h0", {}).get("matches_expected", False)
            if a is None or b is None or b <= 0:
                h0 = False
                continue
            candidates.append(a)
            references.append(b)
            regressions.append(a / b - 1.0)
    improvement = (
        1.0 - _percentile(candidates, 0.5) / _percentile(references, 0.5)
        if candidates
        else None
    )
    worst = max(regressions) if regressions else None
    accepted = bool(
        h0
        and improvement is not None
        and 1.0 - improvement <= 1.0 - threshold["minimum_median_improvement"]
        and 1.0 + worst <= 1.0 + threshold["maximum_query_regression"]
    )
    return {
        "median_improvement": improvement,
        "worst_regression": worst,
        "h0": bool(h0 and candidates),
        "accepted": accepted,
    }


def _slicing_comparison(summary, arm, reference, threshold):
    """Compare medians of query p50s within the actually sliced/unsliced sets."""
    groups = {"sliced": [], "unsliced": []}
    fallbacks = 0
    complete = True
    for case in summary.values():
        for query in case["queries"].values():
            candidate = query["arms"].get(arm, {})
            baseline = query["arms"].get(reference, {})
            cone = candidate.get("cone_slicing")
            if not isinstance(cone, dict) or cone.get("enabled") is not True:
                complete = False
                continue
            if not all(
                candidate.get("h0", {}).get(key, False)
                for key in ("identical_to_reference", "matches_expected")
            ):
                complete = False
            if "cone_slicing" in candidate.get("unstable_fields", ()):
                complete = False
            if not isinstance(cone.get("fallback"), bool):
                complete = False
            fallbacks += candidate.get("samples", 0) if cone.get("fallback") else 0
            dropped = cone.get("dropped_variables")
            if not isinstance(dropped, list):
                complete = False
                continue
            group = "sliced" if dropped else "unsliced"
            metrics = (
                ("formula_dag_nodes", "solve_ms") if dropped else ("build_solve_ms",)
            )
            row = []
            for metric in metrics:
                a, b = candidate.get(metric), baseline.get(metric)
                if metric.endswith("_ms"):
                    a = a.get("p50") if isinstance(a, dict) else None
                    b = b.get("p50") if isinstance(b, dict) else None
                if any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value <= 0
                    for value in (a, b)
                ):
                    complete = False
                    break
                row.append((a, b))
            else:
                groups[group].append(row)

    def ratio(group, index):
        rows = groups[group]
        if not rows:
            return None
        return _percentile([row[index][0] for row in rows], 0.5) / _percentile(
            [row[index][1] for row in rows], 0.5
        )

    dag = ratio("sliced", 0)
    solve = ratio("sliced", 1)
    unsliced = ratio("unsliced", 0)
    accepted = bool(
        complete
        and dag is not None
        and solve is not None
        and unsliced is not None
        and dag <= 1.0 - threshold["minimum_dag_reduction"]
        and solve <= 1.0 + threshold["maximum_solve_regression"]
        and unsliced <= 1.0 + threshold["maximum_unsliced_regression"]
        and fallbacks <= threshold["maximum_fallbacks"]
    )
    return {
        "sliced_queries": len(groups["sliced"]),
        "unsliced_queries": len(groups["unsliced"]),
        "dag_reduction": None if dag is None else 1.0 - dag,
        "solve_regression": None if solve is None else solve - 1.0,
        "unsliced_regression": None if unsliced is None else unsliced - 1.0,
        "fallback_samples": fallbacks,
        "complete": complete,
        "accepted": accepted,
    }


def _group_raw(raw: Path) -> Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]]:
    """Group ``raw.jsonl`` records by case, query and arm.

    :param raw: The raw records file.
    :type raw: pathlib.Path
    :return: ``case -> query -> arm -> samples``.
    :rtype: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]]
    """
    grouped: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
    for line in raw.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        grouped.setdefault(entry["case"], {}).setdefault(entry["query"], {}).setdefault(
            entry["arm"], []
        ).append(entry["record"])
    return grouped


# --------------------------------------------------------------------------
# Runs
# --------------------------------------------------------------------------


def _dump(value: Any) -> str:
    """Serialize a run document the one way this tool ever does.

    :param value: JSON-compatible value.
    :return: Indented, key-sorted JSON with a trailing newline.
    :rtype: str
    """
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _run(
    root: Path,
    repetitions: int,
    warmups: int,
    run_id: str,
    case_filter: Optional[Sequence[str]] = None,
    timeout_ms: Optional[int] = None,
) -> Path:
    """Measure the corpus across every arm and write an immutable run.

    The manifest is written first and every raw record is appended as it is
    produced, so an interrupted run keeps what it measured and ``--rebuild``
    can finish it.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param repetitions: Measured repetitions per sample.
    :type repetitions: int
    :param warmups: Discarded runs per arm before measuring.
    :type warmups: int
    :param run_id: Directory name for this run; must not already exist.
    :type run_id: str
    :param case_filter: Case names to measure, or ``None`` for the whole corpus.
    :type case_filter: Sequence[str], optional
    :param timeout_ms: Solver budget forwarded to every arm as
        ``solve_bmc_property(timeout_ms=...)``, or ``None`` to measure the
        unbounded cost, defaults to ``None``.
    :type timeout_ms: int, optional
    :return: The directory the run was written to.
    :rtype: pathlib.Path
    :raises BenchmarkFailure: If the run directory already exists, the corpus
        fails its check, a filtered case does not exist, or the written run
        violates the schema.
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
        if case is not None and (case_filter is None or case["name"] in case_filter):
            cases.append((case_dir, case))
    if case_filter is not None:
        missing = sorted(set(case_filter) - {case["name"] for _dir, case in cases})
        if missing:
            raise BenchmarkFailure(
                "--cases names cases the corpus does not have: %s" % missing
            )
    if not cases:
        raise BenchmarkFailure("nothing to measure.")

    candidate = _candidate_state()
    arms = [copy.deepcopy(arm) for arm in _ARMS]
    for arm in arms:
        if arm["revision"] is None:
            arm["revision"] = candidate["commit"]
        if timeout_ms is not None:
            arm["options"]["solve"]["timeout_ms"] = timeout_ms
    manifest = {
        "schema": "bmc-solving-benchmark/v1",
        "run_id": run_id,
        "baseline": {"label": _BASELINE_LABEL, "commit": _BASELINE_COMMIT},
        "arms": arms,
        "reference_arm": _REFERENCE_ARM,
        "solver_thresholds": copy.deepcopy(_SOLVER_THRESHOLDS),
        "slicing_thresholds": copy.deepcopy(_SLICING_THRESHOLDS),
        "repetitions": repetitions,
        "warmups": warmups,
        "case_filter": sorted(case_filter) if case_filter is not None else None,
        "timeout_ms": timeout_ms,
        "environment": _environment(),
        "candidate": candidate,
        "inputs": _live_inputs(root),
        "readme_digest": _digest(root / "README.md"),
        "roles": {case["name"]: case["role"] for _dir, case in cases},
        "kinds": {
            case["name"]: {Path(q["file"]).stem: q["kind"] for q in case["queries"]}
            for _dir, case in cases
        },
        "expected": {
            case["name"]: {Path(q["file"]).stem: q["expected"] for q in case["queries"]}
            for _dir, case in cases
        },
        "measurement_map": [
            {"metric": metric, "source": source, "note": note}
            for metric, source, note in _MEASUREMENT_MAP
        ],
    }
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(_dump(manifest), encoding="utf-8")
    raw_path = output / "raw.jsonl"

    worktrees: Dict[str, Path] = {}
    try:
        for revision in sorted({arm["revision"] for arm in arms}):
            worktrees[revision] = _add_worktree(revision)
        first_dir, first_case = cases[0]
        for arm in arms:
            tree = worktrees[arm["revision"]]
            for _ in range(warmups):
                # Warmups are per arm, not per sample: every sample is already a
                # fresh process, and the only state that persists between them
                # is the page cache and the worktree's compiled bytecode.
                _run_sample(
                    (first_dir / first_case["model"]).resolve(),
                    (first_dir / first_case["queries"][0]["file"]).resolve(),
                    arm["options"],
                    tree,
                )
        with raw_path.open("a", encoding="utf-8") as raw:
            for case_dir, case in cases:
                model = (case_dir / case["model"]).resolve()
                for query in case["queries"]:
                    query_path = (case_dir / query["file"]).resolve()
                    query_name = Path(query["file"]).stem
                    for arm in arms:
                        tree = worktrees[arm["revision"]]
                        for index in range(repetitions):
                            record = _run_sample(
                                model, query_path, arm["options"], tree
                            )
                            raw.write(
                                json.dumps(
                                    {
                                        "case": case["name"],
                                        "query": query_name,
                                        "arm": arm["label"],
                                        "repetition": index,
                                        "record": record,
                                    },
                                    sort_keys=True,
                                )
                                + "\n"
                            )
                            raw.flush()
    finally:
        for tree in worktrees.values():
            diagnostic = _remove_worktree(tree)
            if diagnostic:
                print("warning: %s" % diagnostic, file=sys.stderr)

    summary = _aggregate(_group_raw(raw_path), manifest)
    notes: List[str] = []
    problems = _validate_documents(
        "the run being written",
        {"manifest": manifest, "summary": summary},
        _schema(root),
        notes,
    )
    if problems:
        raise BenchmarkFailure(
            "the run this tool just measured violates its own schema; raw.jsonl and "
            "manifest.json are kept under %s for inspection:\n%s"
            % (output.relative_to(_REPO_ROOT), "\n".join(problems))
        )
    (output / "summary.json").write_text(_dump(summary), encoding="utf-8")
    (output / "report.md").write_text(_report(manifest, summary), encoding="utf-8")
    for note in notes:
        print("note: %s" % note, file=sys.stderr)
    return output


def _rebuild(root: Path, run_id: str) -> Path:
    """Rebuild one run's summary and report from its raw records.

    When the run already has ``summary.json`` and ``report.md`` they are never
    overwritten: the rebuild is compared with them byte for byte, which is what
    proves the aggregation is a function of the recorded samples rather than
    of the process that produced them.  A run interrupted before those two
    files were written gets them written now.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param run_id: Directory name of a saved run.
    :type run_id: str
    :return: The run directory.
    :rtype: pathlib.Path
    :raises BenchmarkFailure: If the run or its records are missing, or the
        rebuilt documents differ from the saved ones.
    """
    output = root / "outputs/runs" / run_id
    raw = output / "raw.jsonl"
    manifest_path = output / "manifest.json"
    if not raw.exists() or not manifest_path.exists():
        raise BenchmarkFailure(
            "%s has no raw.jsonl and manifest.json to rebuild from." % output
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary_text = _dump(_aggregate(_group_raw(raw), manifest))
    report_text = _report(manifest, json.loads(summary_text))
    differing = []
    for name, text in (("summary.json", summary_text), ("report.md", report_text)):
        path = output / name
        if not path.exists():
            path.write_text(text, encoding="utf-8")
        elif path.read_text(encoding="utf-8") != text:
            differing.append(name)
    if differing:
        raise BenchmarkFailure(
            "rebuilding %s from raw.jsonl does not reproduce the saved %s; the saved "
            "files were left untouched." % (run_id, " and ".join(differing))
        )
    return output


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _cell(value: Any) -> str:
    """Render one summary value for a Markdown table.

    :param value: A number, string, boolean, ``None`` or an unstable list.
    :type value: Any
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


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    """Render a Markdown table.

    :param header: Column titles.
    :type header: Sequence[str]
    :param rows: Cell text per row.
    :type rows: Sequence[Sequence[str]]
    :return: Table lines.
    :rtype: List[str]
    """
    lines = ["| %s |" % " | ".join(header), "|%s" % ("---|" * len(header))]
    lines += ["| %s |" % " | ".join(row) for row in rows]
    return lines


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
    case_filter = manifest.get("case_filter")
    lines = [
        "# BMC solving benchmark",
        "",
        "Run `%s`, measured from `HEAD` = `%s`%s."
        % (
            manifest["run_id"],
            manifest["candidate"]["commit"][:12],
            " (the working tree also had uncommitted changes; see manifest.json)"
            if manifest["candidate"]["dirty"]
            else "",
        ),
        "Baseline `%s` = `%s`; reference arm `%s`."
        % (manifest["baseline"]["label"], manifest["baseline"]["commit"], reference),
        "",
        "%d measured repetitions per sample after %d discarded warmups per arm, each "
        "sample in its own interpreter running from a detached worktree of its arm's "
        "commit." % (manifest["repetitions"], manifest["warmups"]),
    ]
    if manifest.get("timeout_ms") is not None:
        lines += ["", "Every arm ran with `timeout_ms=%d`." % manifest["timeout_ms"]]
    if case_filter:
        lines += [
            "",
            "**Partial run**: only the cases %s were measured."
            % ", ".join("`%s`" % name for name in case_filter),
        ]
    lines += [
        "",
        "Arms: %s."
        % "; ".join(
            "`%s` = `%s`%s"
            % (
                arm["label"],
                arm["revision"][:12],
                " with options `%s`" % json.dumps(arm["options"], sort_keys=True)
                if any(arm["options"].values())
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

    h0_rows = []
    h0_failures = []
    for case, query, entry in rows:
        for arm in arms:
            arm_summary = entry["arms"].get(arm)
            if arm_summary is None:
                continue
            verdict = arm_summary["h0"]
            passed = verdict["identical_to_reference"] and verdict["matches_expected"]
            if not passed:
                h0_failures.append("%s/%s/%s" % (case, query, arm))
            if arm == reference:
                # The reference is what the others are compared with; the only
                # question it can fail is the expectation.
                cell = "reference, expected %s" % (
                    "met" if verdict["matches_expected"] else "**missed**"
                )
            else:
                cell = "pass" if passed else "**FAIL**"
            h0_rows.append(
                [
                    "`%s`" % case,
                    "`%s`" % query,
                    "`%s`" % entry["expected"]["status"],
                    "`%s`" % arm,
                    _cell(arm_summary.get("status")),
                    _cell(arm_summary.get("property_satisfied")),
                    _cell(arm_summary.get("outcome")),
                    _cell(arm_summary.get("replay_ok")),
                    str(arm_summary.get("failures", 0)),
                    cell,
                ]
            )
    lines += ["", "## Correctness gate H0", ""]
    lines += _table(
        [
            "Case",
            "Query",
            "expected",
            "arm",
            "status",
            "satisfied",
            "outcome",
            "replay",
            "failed samples",
            "H0",
        ],
        h0_rows,
    )

    timing_tables = [
        ("Solve time by arm (p50 ms)", "solve_ms"),
        ("Build time by arm (p50 ms)", "build_ms"),
        ("Replay time by arm (p50 ms, sat only)", "replay_ms"),
    ]
    for title, field in (
        ("Complete API path by arm (p50 ms)", "api_total_ms"),
        ("Build, solve and replay by arm (p50 ms)", "pipeline_ms"),
    ):
        if any(field in arm for _, _, entry in rows for arm in entry["arms"].values()):
            timing_tables.append((title, field))
    for title, field in timing_tables:
        lines += ["", "## %s" % title, ""]
        lines += _table(
            ["Case", "Query"] + ["`%s`" % arm for arm in arms],
            [
                ["`%s`" % case, "`%s`" % query]
                + [
                    _cell(entry["arms"].get(arm, {}).get(field, {}).get("p50"))
                    for arm in arms
                ]
                for case, query, entry in rows
            ],
        )

    if any(
        "api_total_ms" in arm for _, _, entry in rows for arm in entry["arms"].values()
    ):
        lines += ["", "## Complete paths by reference SAT/UNSAT status", ""]
        grouped = []
        for status in ("sat", "unsat"):
            for field in ("api_total_ms", "pipeline_ms"):
                for arm in arms:
                    pairs = [
                        (
                            case,
                            query,
                            entry["arms"][_REFERENCE_ARM][field]["p50"],
                            entry["arms"][arm][field]["p50"],
                        )
                        for case, query, entry in rows
                        if entry["arms"][_REFERENCE_ARM].get("status") == status
                        and field in entry["arms"].get(arm, {})
                        and field in entry["arms"][_REFERENCE_ARM]
                    ]
                    if not pairs:
                        continue
                    default = _percentile([item[2] for item in pairs], 0.5)
                    candidate = _percentile([item[3] for item in pairs], 0.5)
                    worst = max(pairs, key=lambda item: item[3] / item[2])
                    grouped.append(
                        [
                            status,
                            field,
                            arm,
                            str(len(pairs)),
                            _cell(default),
                            _cell(candidate),
                            "%.2f%%" % ((candidate / default - 1) * 100),
                            "%.2f%%" % ((worst[3] / worst[2] - 1) * 100),
                            "%s/%s" % worst[:2],
                        ]
                    )
        lines += _table(
            [
                "Reference status",
                "Metric",
                "Arm",
                "Queries",
                "Default p50 ms",
                "Arm p50 ms",
                "Change",
                "Worst change",
                "Worst query",
            ],
            grouped,
        )
        lines += [
            "",
            "Groups use the default arm's status. Medians aggregate per-query "
            "p50s; worst change compares each query with its own default. Positive "
            "change means slower. These diagnostic groups do not alter H0 or T3.",
        ]

    lines += ["", "## Formula size (distinct Z3 AST nodes)", ""]
    lines += _table(
        ["Case", "Query"] + ["`%s`" % arm for arm in arms],
        [
            ["`%s`" % case, "`%s`" % query]
            + [
                _cell(entry["arms"].get(arm, {}).get("formula_dag_nodes"))
                for arm in arms
            ]
            for case, query, entry in rows
        ],
    )

    lines += ["", "## Peak child RSS (bytes)", ""]
    lines += _table(
        ["Case", "Query"] + ["`%s`" % arm for arm in arms],
        [
            ["`%s`" % case, "`%s`" % query]
            + [
                _cell(entry["arms"].get(arm, {}).get("peak_child_rss_bytes"))
                for arm in arms
            ]
            for case, query, entry in rows
        ],
    )

    failures = [
        "%s/%s/%s" % (case, query, arm)
        for case, query, entry in rows
        for arm in arms
        if entry["arms"].get(arm, {}).get("failures")
    ]
    unstable = [
        "%s/%s/%s: %s" % (case, query, arm, entry["arms"][arm]["unstable_fields"])
        for case, query, entry in rows
        for arm in arms
        if entry["arms"].get(arm, {}).get("unstable_fields")
    ]
    lines += ["", "## Failures and instability", ""]
    lines.append("Failed samples: %s." % (", ".join(failures) if failures else "none"))
    lines.append(
        "Unstable published fields: %s." % ("; ".join(unstable) if unstable else "none")
    )

    lines += ["", "## Thresholds", ""]
    lines.append(
        "H0 (correctness): %s."
        % (
            "**pass** for every arm and query"
            if not h0_failures
            else "**FAIL** at %s" % ", ".join(h0_failures)
        )
    )
    if manifest.get("solver_thresholds"):
        lines += [
            "",
            "| Gate | Arm | Median p50 improvement | Worst query regression | H0 | Adopt |",
            "|---|---|---|---|---|---|",
        ]
        for arm in manifest["arms"]:
            profile = arm["options"].get("solve", {}).get("solver_profile")
            threshold = manifest["solver_thresholds"].get(profile)
            if threshold is None:
                continue
            comparison = _solver_comparison(summary, arm["label"], reference, threshold)
            lines.append(
                "| %s | `%s` | %s | %s | %s | %s |"
                % (
                    threshold["id"],
                    arm["label"],
                    "n/a"
                    if comparison["median_improvement"] is None
                    else "%.2f%%" % (100 * comparison["median_improvement"]),
                    "n/a"
                    if comparison["worst_regression"] is None
                    else "%.2f%%" % (100 * comparison["worst_regression"]),
                    "pass" if comparison["h0"] else "FAIL",
                    "pass" if comparison["accepted"] else "NOT MET",
                )
            )
        lines += [
            "",
            "Median improvement compares medians of per-query solve p50; "
            "worst regression compares each query with its own default p50. "
            "Missing measurements or H0 failures prevent adoption.",
        ]
    if manifest.get("slicing_thresholds"):
        for arm in manifest["arms"]:
            if arm["options"].get("compile", {}).get("cone_slicing") is not True:
                continue
            comparison = _slicing_comparison(
                summary, arm["label"], reference, manifest["slicing_thresholds"]
            )
            lines += ["", "### T3: conservative cone slicing", ""]
            for key, value in comparison.items():
                if key.endswith(("reduction", "regression")) and value is not None:
                    value = "%.2f%%" % (100 * value)
                lines.append("- %s: %s" % (key, value))
            lines += [
                "",
                "T3: **%s**. Ratios compare medians of per-query "
                "measurements within each actual slice partition. The unsliced "
                "metric is the p50 of each sample's build plus solve time. "
                "Solve time includes internal replay and any fallback. Missing "
                "measurements, an empty partition, or H0 failure prevent adoption."
                % ("pass" if comparison["accepted"] else "NOT MET"),
            ]
    option_arms = [arm for arm in manifest["arms"] if any(arm["options"].values())]
    if option_arms and not manifest.get("solver_thresholds"):
        lines.append(
            "T1-T3 apply to the option arms %s and are evaluated against the "
            "pre-registered rows in README.md by the change that adds each option; "
            "the p50 and size columns above are their inputs."
            % ", ".join("`%s`" % arm["label"] for arm in option_arms)
        )
    elif not option_arms:
        lines.append(
            "T1-T3 are not evaluated: no arm sets an option, so this run only "
            "establishes the baseline and default distributions."
        )

    lines += ["", "## Measurement map", ""]
    lines += _table(
        ["Metric", "Source", "Note"],
        [
            ["`%s`" % entry["metric"], "`%s`" % entry["source"], entry["note"]]
            for entry in manifest["measurement_map"]
        ],
    )
    lines += [
        "",
        "Confirm this report is a function of the raw records with:",
        "",
        "```bash",
        "python tools/run_bmc_solving_benchmark.py --rebuild %s" % manifest["run_id"],
        "```",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Oracle: the expectations against the simulator, independently of the encoder.
# --------------------------------------------------------------------------

#: Explicit exploration stops here and reports the query inconclusive.
_ORACLE_MAX_FRAMES = 40000
_ORACLE_MAX_SECONDS = 150.0

#: Event alphabets up to this size are explored with every subset per step.
_ORACLE_FULL_SUBSETS_UP_TO = 4


def _parse_corpus_query(
    text: str,
) -> Tuple[Optional[str], Optional[str], str, int, str]:
    """Split one corpus query into the parts the oracle evaluates.

    The corpus is written in a small subset of FBMCQ on purpose: one optional
    ``init cold havoc ...`` clause and one ``check`` with a frame-local body,
    so the oracle can evaluate the body directly instead of re-implementing
    the query language.

    :param text: Query text.
    :type text: str
    :return: ``(havoc, where, kind, bound, body)``.
    :rtype: Tuple[Optional[str], Optional[str], str, int, str]
    :raises BenchmarkFailure: If the query uses a form the oracle cannot read.
    """
    import re

    havoc = where = None
    init = re.search(
        r"init\s+cold\s+havoc\s+(\*|\{[^}]*\})(?:\s+where\s+(.*?))?;", text, re.S
    )
    if init:
        havoc, where = init.group(1).strip(), (init.group(2) or "").strip() or None
    check = re.search(
        r"check\s+(reach|forbid|invariant)\s*<=\s*(\d+)\s*:\s*(.*?);\s*$", text, re.S
    )
    if check is None:
        raise BenchmarkFailure(
            "the oracle only reads reach, forbid and invariant queries: %r" % text
        )
    return havoc, where, check.group(1), int(check.group(2)), check.group(3).strip()


def _condition_holds(
    body: str, state_path: Optional[str], variables: Dict[str, Any]
) -> bool:
    """Evaluate a frame-local FBMCQ condition on one frame.

    :param body: Condition text using variables, ``active("...")``, comparison
        and boolean operators.
    :type body: str
    :param state_path: Active leaf path, or ``None`` for the init sentinel and
        the terminated frame, where nothing is active.
    :type state_path: str, optional
    :param variables: Persistent variable values at the frame.
    :type variables: Dict[str, Any]
    :return: Whether the condition holds.
    :rtype: bool
    """
    import re

    def active(path: str) -> bool:
        return state_path is not None and (
            state_path == path or state_path.startswith(path + ".")
        )

    source = re.sub(
        r"!(?!=)", " not ", body.replace("&&", " and ").replace("||", " or ")
    )
    return bool(eval(source, {"active": active, "__builtins__": {}}, dict(variables)))


def _oracle_initial_values(model, havoc: Optional[str], where: Optional[str]):
    """Enumerate the frame-0 variable assignments a query admits.

    :param model: Loaded state machine.
    :type model: pyfcstm.model.StateMachine
    :param havoc: ``*``, ``{name}`` or ``None``.
    :type havoc: str, optional
    :param where: The ``where`` condition text, or ``None``.
    :type where: str, optional
    :return: ``(assignments, note)``; ``assignments`` is ``None`` when the set
        is not enumerable, and ``note`` says how exact the enumeration is.
    :rtype: Tuple[Optional[List[Dict[str, Any]]], str]
    """
    import re

    from pyfcstm.simulate import SimulationRuntime

    base = dict(SimulationRuntime(model).vars)
    if havoc is None:
        return [base], "exact"
    if havoc == "*":
        return None, "skipped: havoc * is not enumerable"
    names = [name.strip().strip('"') for name in havoc.strip("{}").split(",")]
    if len(names) != 1:
        return None, "skipped: the oracle enumerates one relaxed variable"
    name = names[0]
    low = re.search(r"%s\s*>=\s*(-?\d+)" % name, where or "")
    high = re.search(r"%s\s*<=\s*(-?\d+)" % name, where or "")
    if low and high:
        values = range(int(low.group(1)), int(high.group(1)) + 1)
        return [dict(base, **{name: value}) for value in values], "exact"
    if low:
        start = int(low.group(1))
        return (
            [dict(base, **{name: value}) for value in range(start, start + 3)],
            "sampled: %s in %d..%d" % (name, start, start + 2),
        )
    return None, "skipped: the where clause does not bound %s" % name


def _oracle_explore(model, inits, events: Sequence[str], bound: int, body: str):
    """Explore every execution up to ``bound`` steps and evaluate ``body`` per frame.

    Frame 0 is the init sentinel, where nothing is active.  A step whose
    lifecycle actions raise -- division by zero, a non-integer quotient written
    to an integer variable -- is pruned, which is how the encoder treats an
    undefined operation.  Revisiting a ``(state, variables)`` pair is pruned as
    well: everything reachable from it later is reachable from its first visit
    earlier, so nothing within the bound is lost.

    :param model: Loaded state machine.
    :type model: pyfcstm.model.StateMachine
    :param inits: Frame-0 variable assignments.
    :type inits: Sequence[Dict[str, Any]]
    :param events: Event paths the model declares.
    :type events: Sequence[str]
    :param bound: Number of steps.
    :type bound: int
    :param body: Condition text.
    :type body: str
    :return: ``(truth values per visited frame or None when the cap was hit,
        mode note, frames visited, pruned steps)``.
    :rtype: Tuple[Optional[List[bool]], str, int, int]
    """
    import itertools
    import time

    from pyfcstm.simulate import SimulationRuntime
    from pyfcstm.simulate.runtime import SimulationRuntimeExpressionError

    if len(events) <= _ORACLE_FULL_SUBSETS_UP_TO:
        subsets: List[Tuple[str, ...]] = [
            combination
            for size in range(len(events) + 1)
            for combination in itertools.combinations(events, size)
        ]
        mode = "exhaustive"
    else:
        subsets = [()] + [(event,) for event in events]
        mode = "under-approximation: empty and single events only (%d events)" % len(
            events
        )
    seen = set()
    layer: List[Any] = []
    truth: List[bool] = []
    pruned = 0
    started = time.perf_counter()
    for init in inits:
        runtime = SimulationRuntime(model, initial_vars=init)
        truth.append(_condition_holds(body, None, runtime.vars))
        key = ("INIT", tuple(sorted(init.items())))
        if key not in seen:
            seen.add(key)
            layer.append(runtime)
    for _depth in range(1, bound + 1):
        following: List[Any] = []
        for runtime in layer:
            for subset in subsets:
                candidate = copy.deepcopy(runtime, memo={id(model): model})
                try:
                    candidate.cycle(list(subset))
                except (SimulationRuntimeExpressionError, ValueError):
                    # SimulationRuntimeExpressionError: an operation such as a
                    # division by zero failed; ValueError: the runtime refused
                    # to write a non-integer quotient into an int variable.
                    # Both are undefined steps the encoder prunes.
                    pruned += 1
                    continue
                path = (
                    None
                    if candidate.is_ended
                    else ".".join(candidate.current_state.path)
                )
                key = (path or "TERMINATED", tuple(sorted(candidate.vars.items())))
                if key in seen:
                    continue
                seen.add(key)
                truth.append(_condition_holds(body, path, candidate.vars))
                if not candidate.is_ended:
                    following.append(candidate)
                if (
                    len(seen) > _ORACLE_MAX_FRAMES
                    or time.perf_counter() - started > _ORACLE_MAX_SECONDS
                ):
                    return None, mode, len(seen), pruned
        layer = following
        if not layer:
            break
    return truth, mode, len(seen), pruned


def _oracle(root: Path) -> Tuple[List[str], List[str]]:
    """Check every recorded expectation against the simulator.

    The expectations in ``case.json`` were recorded from the encoder, so on
    their own they only detect drift.  This explores the bounded executions
    with :class:`pyfcstm.simulate.SimulationRuntime`, the same runtime that
    replays every witness, and decides each query from its semantics: a
    ``reach`` or ``forbid`` is ``sat`` when some frame satisfies the body, an
    ``invariant`` is ``sat`` when some frame violates it.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :return: ``(report lines, mismatches)``.
    :rtype: Tuple[List[str], List[str]]
    """
    from pyfcstm.bmc.domain import build_bmc_domain
    from pyfcstm.model import load_state_machine_from_file

    lines: List[str] = []
    mismatches: List[str] = []
    for case_dir in _case_dirs(root):
        case = _load_case(case_dir, [])
        if case is None:
            continue
        model = load_state_machine_from_file(str(case_dir / case["model"]))
        events = [event.path for event in build_bmc_domain(model, 1).events]
        for query in case["queries"]:
            havoc, where, kind, bound, body = _parse_corpus_query(
                (case_dir / query["file"]).read_text(encoding="utf-8")
            )
            expected = query["expected"]["status"]
            label = "%s/%s" % (case["name"], Path(query["file"]).stem)
            inits, init_note = _oracle_initial_values(model, havoc, where)
            if inits is None:
                lines.append(
                    "%-52s expected %-5s oracle -      %s"
                    % (label, expected, init_note)
                )
                continue
            truth, mode, frames, pruned = _oracle_explore(
                model, inits, events, bound, body
            )
            if truth is None:
                lines.append(
                    "%-52s expected %-5s oracle -      inconclusive after %d frames"
                    % (label, expected, frames)
                )
                continue
            found = (not all(truth)) if kind == "invariant" else any(truth)
            oracle = "sat" if found else "unsat"
            exact = mode == "exhaustive" and init_note == "exact"
            if oracle == expected:
                verdict = "match" if exact else "consistent"
            elif oracle == "sat":
                verdict = "MISMATCH: the simulator found a witness the encoder did not"
            elif exact:
                verdict = "MISMATCH: the encoder found a witness the simulator cannot"
            else:
                verdict = "consistent (an under-approximation cannot refute sat)"
            if verdict.startswith("MISMATCH"):
                mismatches.append(label)
            notes = [
                note
                for note in (
                    mode if not exact and mode != "exhaustive" else "",
                    init_note if init_note != "exact" else "",
                )
                if note
            ]
            if pruned:
                notes.append("%d undefined steps pruned" % pruned)
            lines.append(
                "%-52s expected %-5s oracle %-5s  %s [%d frames%s]"
                % (
                    label,
                    expected,
                    oracle,
                    verdict,
                    frames,
                    "; " + "; ".join(notes) if notes else "",
                )
            )
    return lines, mismatches


# --------------------------------------------------------------------------
# Self-test: every gate above must be able to fail.
# --------------------------------------------------------------------------


def _first_case(root: Path) -> Tuple[Path, Dict[str, Any]]:
    """Return the first case directory and its parsed metadata.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :return: Directory and ``case.json`` content.
    :rtype: Tuple[pathlib.Path, Dict[str, Any]]
    """
    case_dir = sorted(path for path in (root / "cases").iterdir() if path.is_dir())[0]
    return case_dir, json.loads((case_dir / "case.json").read_text(encoding="utf-8"))


def _mutations(root: Path) -> List[Tuple[str, str, Callable[[Path], None]]]:
    """Return the corpus mutations ``--check`` must reject.

    Each entry is ``(name, expected substring of the failure, mutate(root))``.
    File names come from the first case's metadata rather than being assumed.

    :param root: The pristine benchmark directory, read for its layout.
    :type root: pathlib.Path
    :return: Mutation table.
    :rtype: List[Tuple[str, str, Callable[[pathlib.Path], None]]]
    """
    _dir, case = _first_case(root)
    model_name = case["model"]
    query_name = case["queries"][0]["file"]

    def edit_case_json(root: Path, edit: Callable[[Dict[str, Any]], None]) -> None:
        case_dir, data = _first_case(root)
        edit(data)
        (case_dir / "case.json").write_text(json.dumps(data), encoding="utf-8")

    def missing_case_json(root: Path) -> None:
        (_first_case(root)[0] / "case.json").unlink()

    def missing_model(root: Path) -> None:
        (_first_case(root)[0] / model_name).unlink()

    def missing_query_file(root: Path) -> None:
        (_first_case(root)[0] / query_name).unlink()

    def expected_missing_status(root: Path) -> None:
        edit_case_json(root, lambda d: d["queries"][0]["expected"].pop("status"))

    def expected_bad_status(root: Path) -> None:
        edit_case_json(
            root, lambda d: d["queries"][0]["expected"].__setitem__("status", "maybe")
        )

    def expected_extra_key(root: Path) -> None:
        edit_case_json(
            root, lambda d: d["queries"][0]["expected"].__setitem__("note", "x")
        )

    def queries_not_a_list(root: Path) -> None:
        edit_case_json(root, lambda d: d.__setitem__("queries", query_name))

    def name_mismatch(root: Path) -> None:
        edit_case_json(root, lambda d: d.__setitem__("name", "somebody_else"))

    def bad_role(root: Path) -> None:
        edit_case_json(root, lambda d: d.__setitem__("role", "decorative"))

    def model_does_not_load(root: Path) -> None:
        (_first_case(root)[0] / model_name).write_text("state {", encoding="utf-8")

    def query_does_not_bind(root: Path) -> None:
        (_first_case(root)[0] / query_name).write_text(
            'check reach <= 1: active("No.Such.State");\n', encoding="utf-8"
        )

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
        name = _first_case(root)[0].name
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
        (bogus / "raw.jsonl").write_text("", encoding="utf-8")

    def run_without_raw(root: Path) -> None:
        _synthetic_run(root, "noraw")
        (root / "outputs/runs/noraw/raw.jsonl").unlink()
        (root / "outputs/runs/noraw/summary.json").write_text("{}", encoding="utf-8")

    return [
        ("missing_case_json", "case.json", missing_case_json),
        ("missing_model", model_name, missing_model),
        ("missing_query_file", query_name, missing_query_file),
        ("expected_missing_status", "expected.status", expected_missing_status),
        ("expected_bad_status", "expected.status", expected_bad_status),
        ("expected_extra_key", "keys the schema does not", expected_extra_key),
        ("queries_not_a_list", "no queries", queries_not_a_list),
        ("name_mismatch", "name", name_mismatch),
        ("bad_role", "role", bad_role),
        ("model_does_not_load", "load", model_does_not_load),
        ("query_does_not_bind", "does not bind", query_does_not_bind),
        ("readme_missing_threshold", "T3", readme_missing_threshold),
        ("readme_missing_case", "README", readme_missing_case),
        ("schema_invalid_json", "schema.json", schema_invalid_json),
        ("run_violates_schema", "schema", run_violates_schema),
        ("run_without_raw", "raw.jsonl", run_without_raw),
    ]


def _synthetic_run(root: Path, run_id: str) -> None:
    """Write a tiny manifest and raw.jsonl so a rebuild can be exercised.

    Case ``alpha`` agrees across arms; case ``beta`` has one arm whose samples
    all crashed, which the correctness gate must fail.

    :param root: Benchmark directory.
    :type root: pathlib.Path
    :param run_id: Run directory name to create.
    :type run_id: str
    :return: ``None``.
    :rtype: None
    """
    output = root / "outputs/runs" / run_id
    output.mkdir(parents=True)
    arms = [copy.deepcopy(arm) for arm in _ARMS]
    for arm in arms:
        if arm["revision"] is None:
            arm["revision"] = "f" * 40
    lines = []
    for case, query, expected in (
        ("alpha", "reach", "sat"),
        ("beta", "forbid", "unsat"),
    ):
        for arm in arms:
            for repetition, solve_ms in enumerate((3.0, 5.0, 4.0)):
                if case == "beta" and arm["label"] == _BASELINE_LABEL:
                    record: Dict[str, Any] = {
                        "error": "child exited 1",
                        "stderr": "boom",
                    }
                else:
                    record = {
                        "pyfcstm_file": "/tmp/tree/pyfcstm/__init__.py",
                        "build_ms": 10.0 + repetition,
                        "solve_ms": solve_ms,
                        "replay_ms": 1.0 if expected == "sat" else None,
                        "total_elapsed_ms": solve_ms + 0.5,
                        "formula_dag_nodes": 100,
                        "status": expected,
                        "property_satisfied": True,
                        "outcome": "witness_found"
                        if expected == "sat"
                        else "property_satisfied",
                        "replay_ok": True if expected == "sat" else None,
                        "peak_rss_bytes": 50_000_000,
                    }
                if not record.get("error"):
                    record["build_solve_ms"] = record["build_ms"] + record["solve_ms"]
                    record["pipeline_ms"] = record["build_solve_ms"] + (
                        record["replay_ms"] or 0.0
                    )
                    record["api_total_ms"] = record["pipeline_ms"] + 2.0
                    if arm["label"] == "cone_slicing":
                        record["cone_slicing"] = {
                            "enabled": True,
                            "retained_count": 1,
                            "dropped_variables": ["output"] if case == "alpha" else [],
                            "skipped_reason": None
                            if case == "alpha"
                            else "no_removable_variables",
                            "fallback": False,
                        }
                        if case == "alpha":
                            record["formula_dag_nodes"] = 80
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
        "arms": arms,
        "reference_arm": _REFERENCE_ARM,
        "solver_thresholds": copy.deepcopy(_SOLVER_THRESHOLDS),
        "slicing_thresholds": copy.deepcopy(_SLICING_THRESHOLDS),
        "repetitions": 3,
        "warmups": 0,
        "case_filter": None,
        "timeout_ms": None,
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
                    "outcome": "property_satisfied",
                }
            },
        },
        "measurement_map": [
            {"metric": m, "source": s, "note": n} for m, s, n in _MEASUREMENT_MAP
        ],
    }
    (output / "manifest.json").write_text(_dump(manifest), encoding="utf-8")
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

    for name, needle, mutate in _mutations(source):
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
        _rebuild(root, "synthetic")
        summary = json.loads(summary_a.decode("utf-8"))
        alpha = summary["alpha"]["queries"]["reach"]["arms"]
        if alpha[_REFERENCE_ARM]["solve_ms"]["p50"] != 4.0:
            problems.append("summary p50 of (3, 5, 4) is not 4.0")
        if alpha[_REFERENCE_ARM]["pipeline_ms"]["p50"] != 17.0:
            problems.append("pipeline p50 must aggregate per-sample phase sums")
        if alpha[_REFERENCE_ARM]["api_total_ms"]["p50"] != 19.0:
            problems.append("API p50 must include loading before the pipeline")
        if alpha[_BASELINE_LABEL]["h0"] != {
            "identical_to_reference": True,
            "matches_expected": True,
        }:
            problems.append("H0 verdict for an identical arm is not the passing one")
        broken_replay = dict(alpha[_REFERENCE_ARM], replay_ok=False)
        if _h0(
            broken_replay,
            broken_replay,
            summary["alpha"]["queries"]["reach"]["expected"],
        )["identical_to_reference"]:
            problems.append("H0 accepted two SAT arms whose witnesses both fail replay")
        for timings, passed in (
            ((3.4, 3.4), True),
            ((3.5, 3.5), False),
            ((2.0, 4.4), True),
            ((2.0, 4.41), False),
        ):
            trial = copy.deepcopy(summary)
            for case, timing in zip(sorted(trial), timings):
                for query in trial[case]["queries"].values():
                    query["arms"]["logic"]["solve_ms"]["p50"] = timing
            decision = _solver_comparison(
                trial, "logic", _REFERENCE_ARM, _SOLVER_THRESHOLDS["logic"]
            )
            if decision["accepted"] != passed:
                problems.append(
                    "solver adoption gate misclassified p50 values %r" % (timings,)
                )
        missing = copy.deepcopy(summary)
        missing["alpha"]["queries"]["reach"]["arms"].pop("logic")
        if _solver_comparison(
            missing, "logic", _REFERENCE_ARM, _SOLVER_THRESHOLDS["logic"]
        )["accepted"]:
            problems.append("solver adoption gate accepted a missing measurement")
        for metric, value, passed in (
            ("formula_dag_nodes", 80, True),
            ("formula_dag_nodes", 81, False),
            ("solve_ms", 4.2, True),
            ("solve_ms", 4.201, False),
            ("build_solve_ms", 16.8, True),
            ("build_solve_ms", 16.801, False),
            ("fallback", True, False),
            ("missing", None, False),
            ("h0", False, False),
        ):
            trial = copy.deepcopy(summary)
            case, query = (
                ("beta", "forbid") if metric == "build_solve_ms" else ("alpha", "reach")
            )
            candidate = trial[case]["queries"][query]["arms"]["cone_slicing"]
            if metric in ("solve_ms", "build_solve_ms"):
                candidate[metric]["p50"] = value
            elif metric == "formula_dag_nodes":
                candidate[metric] = value
            elif metric == "fallback":
                candidate["cone_slicing"]["fallback"] = value
            elif metric == "missing":
                candidate.pop("cone_slicing")
            else:
                candidate["h0"]["identical_to_reference"] = value
            if (
                _slicing_comparison(
                    trial, "cone_slicing", _REFERENCE_ARM, _SLICING_THRESHOLDS
                )["accepted"]
                != passed
            ):
                problems.append(
                    "slicing adoption gate misclassified %s=%r" % (metric, value)
                )
        failed_suffix = dict(alpha[_REFERENCE_ARM], suffix_replay_ok=False)
        if _h0(
            failed_suffix,
            failed_suffix,
            summary["alpha"]["queries"]["reach"]["expected"],
        )["identical_to_reference"]:
            problems.append("H0 accepted a failed incomplete suffix replay")
        beta = summary["beta"]["queries"]["forbid"]["arms"]
        if (
            beta[_BASELINE_LABEL]["h0"]["identical_to_reference"]
            or beta[_BASELINE_LABEL]["h0"]["matches_expected"]
        ):
            problems.append("H0 passed an arm whose every sample crashed")
        if "FAIL" not in (first / "report.md").read_text(encoding="utf-8"):
            problems.append("the report does not flag the crashed arm")
        (first / "summary.json").write_text("{}\n", encoding="utf-8")
        try:
            _rebuild(root, "synthetic")
        except BenchmarkFailure as err:
            if "summary.json" not in str(err):
                problems.append(
                    "a tampered summary.json was rejected for the wrong reason: %s"
                    % err
                )
            if (first / "summary.json").read_text(encoding="utf-8") != "{}\n":
                problems.append("--rebuild overwrote a saved summary.json")
        else:
            problems.append(
                "--rebuild accepted a summary.json that raw.jsonl does not reproduce"
            )
        (first / "summary.json").write_bytes(summary_a)
        _check(root)
    except BenchmarkFailure as err:
        problems.append("a synthetic run did not pass --check: %s" % err)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return problems


def _positive_int(text: str) -> int:
    """Parse a strictly positive integer for argparse.

    :param text: Command-line text.
    :type text: str
    :return: The integer.
    :rtype: int
    :raises argparse.ArgumentTypeError: If the value is not at least one.
    """
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def _non_negative_int(text: str) -> int:
    """Parse a non-negative integer for argparse.

    :param text: Command-line text.
    :type text: str
    :return: The integer.
    :rtype: int
    :raises argparse.ArgumentTypeError: If the value is negative.
    """
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return value


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the benchmark from the command line.

    :param argv: Argument list, defaults to ``None`` for ``sys.argv[1:]``
    :type argv: Sequence[str], optional
    :return: ``0`` on success, ``1`` on a controlled failure.
    :rtype: int

    Example::

        $ python tools/run_bmc_solving_benchmark.py --check
        Benchmark corpus, arms, thresholds, and layout are consistent.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--oracle", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--rebuild", metavar="RUN_ID")
    parser.add_argument("--repetitions", type=_positive_int, default=5)
    parser.add_argument("--warmups", type=_non_negative_int, default=1)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--timeout-ms",
        type=_positive_int,
        default=None,
        help="Solver budget forwarded to every arm; omitted, the unbounded cost is measured.",
    )
    parser.add_argument(
        "--cases",
        default=None,
        help="Comma-separated case names to measure; the manifest records the filter.",
    )
    args = parser.parse_args(argv)
    if not (args.check or args.self_test or args.oracle or args.run or args.rebuild):
        parser.error("Pass --check, --self-test, --oracle, --run, or --rebuild RUN_ID.")
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
            notes = _check(_bench_root())
        except BenchmarkFailure as err:
            # The corpus, thresholds, or a saved run do not match what the runner measures.
            print("Benchmark self-check failed:\n%s" % err)
            return 1
        for note in notes:
            print("note: %s" % note)
        print("Benchmark corpus, arms, thresholds, and layout are consistent.")
    if args.oracle:
        try:
            lines, mismatches = _oracle(_bench_root())
        except BenchmarkFailure as err:
            # A corpus query outside the subset the oracle can read.
            print("Benchmark oracle failed:\n%s" % err)
            return 1
        print("\n".join(lines))
        if mismatches:
            print("Oracle mismatches: %s" % ", ".join(mismatches))
            return 1
        print("Every enumerable expectation agrees with the simulator.")
    if args.run:
        run_id = args.run_id or _candidate_state()["commit"][:12]
        case_filter = (
            [name.strip() for name in args.cases.split(",") if name.strip()]
            if args.cases
            else None
        )
        try:
            output = _run(
                _bench_root(),
                args.repetitions,
                args.warmups,
                run_id,
                case_filter,
                args.timeout_ms,
            )
        except BenchmarkFailure as err:
            # A saved run is immutable; this refuses rather than overwriting.
            print("Benchmark run failed:\n%s" % err)
            return 1
        print("Wrote %s" % (output / "report.md").relative_to(_REPO_ROOT))
    if args.rebuild:
        try:
            output = _rebuild(_bench_root(), args.rebuild)
        except BenchmarkFailure as err:
            # The run is missing the records a rebuild needs, or does not reproduce.
            print("Benchmark rebuild failed:\n%s" % err)
            return 1
        print(
            "Rebuilt %s and it matches."
            % (output / "report.md").relative_to(_REPO_ROOT)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
