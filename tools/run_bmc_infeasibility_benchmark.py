"""
Measure what the optional infeasibility explanation costs.

The explanation is opt-in, so the question a user actually has is what they pay
for each depth.  Answering it needs four contrasts, not two: the revision before
the provenance infrastructure landed, the same code with the infrastructure but
no explanation requested, and then each depth in turn.  Without the first, an
overhead the infrastructure imposes on every run would be invisible; without the
second, it would be charged to the explanation.

Timing and peak memory are collected from a separate process per sample.  Z3
keeps state between checks inside one process, so a second measurement in the
same interpreter is measuring a warmed solver rather than the sample.  That also
makes peak RSS meaningful: it is the child's high-water mark, not this process's.

Warmups run first and are discarded.  They are reported separately rather than
averaged in, because the first run of a sample pays import and JIT-like costs
that no later run repeats.

The runner is deliberately outside pytest.  Distribution measurements are not
assertions, and a suite that fails because a machine was busy teaches nothing.
Unit tests under ``test/bmc/`` cover the API and the invariants instead.

Example::

    $ python tools/run_bmc_infeasibility_benchmark.py --check
    Benchmark corpus, measurement map, and layout are consistent.
    $ python tools/run_bmc_infeasibility_benchmark.py --run --repetitions 5
    Wrote benchmarks/bmc/infeasibility/outputs/runs/<run-id>/report.md
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where the corpus, schema, and immutable run outputs live.
_BENCH_ROOT = Path("benchmarks/bmc/infeasibility")

#: The revision the contrast is measured against.
#:
#: Frozen by the contract under this name.  The full commit is recorded in every
#: run manifest, because a short prefix is not enough to identify a revision
#: months later.
_BASELINE_LABEL = "baseline-901f30e9"
_BASELINE_COMMIT = "901f30e981c29eb8e304b33d61985652d2e85b2e"

#: The four arms of the contrast, in the order a reader should compare them.
_ARMS = (_BASELINE_LABEL, "none", "formal", "proof")

#: How each published metric is obtained.
#:
#: Written down because the umbrella asks for construction, verification and
#: linearization separately while the production ledger publishes one entry that
#: covers construction and derived-side rule checking together.  Choosing a
#: reading silently at report time would make the numbers incomparable between
#: runs, so the choice is frozen here and repeated in the report.
_MEASUREMENT_MAP: Tuple[Tuple[str, str, str], ...] = (
    (
        "classification",
        "refinement_checks[component_*].elapsed_ms",
        "production ledger; the staged feasibility probe that fixes the family",
    ),
    (
        "core_extraction",
        "refinement_checks[unsat_core].elapsed_ms",
        "production ledger",
    ),
    (
        "core_minimization",
        "refinement_checks[unsat_core_minimization].elapsed_ms",
        "production ledger",
    ),
    (
        "proof_input_verification",
        "refinement_checks[core_binding].elapsed_ms",
        "production ledger; the two-directional check of every input node",
    ),
    (
        "proof_construction",
        "refinement_checks[proof_construction].elapsed_ms",
        "production ledger; covers closure construction AND derived-side "
        "rule_checker verification, which are not separable here",
    ),
    (
        "proof_linearization",
        "benchmark-only: direct timing of pyfcstm.bmc.proof_text.linearize_proof",
        "not in the production ledger; timed in the child process around a "
        "documented module function, and reported as instrumentation",
    ),
    (
        "total_elapsed_ms",
        "result.total_elapsed_ms",
        "production ledger; whole solve including the mandatory verdict",
    ),
    (
        "peak_child_rss_bytes",
        "psutil high-water mark of the child process",
        "absent rather than zero when psutil is unavailable",
    ),
    (
        "solver_checks",
        "len(result.feasibility.refinement_checks)",
        "production ledger; how many extra checks the depth cost",
    ),
)

#: The corpus, and what each case is in the corpus for.
#:
#: A benchmark that only measures cases which succeed reports a cost the user
#: will not see, so the degrading and feasible cases are part of the corpus
#: rather than exceptions to it.
_CASES: Tuple[Tuple[str, str, str], ...] = (
    ("two_values", "proof", "one variable pinned to two values at one frame"),
    ("empty_interval", "proof", "bounds that no value satisfies"),
    ("two_states", "proof", "two states required of one frame"),
    ("state_domain", "proof", "every state at a frame excluded at once"),
    ("definedness", "proof", "an operation that cannot stay defined"),
    ("cross_step", "formal", "conflict visible only after accumulating a step"),
    ("event_conflict", "formal", "event assumption published without content"),
    ("feasible", "none", "feasible scenario; the explanation does no work"),
)

_MODEL = "latch.fcstm"


class BenchmarkFailure(RuntimeError):
    """Raised when the corpus, layout, or measurement map is inconsistent."""


def _cases_dir() -> Path:
    """Return the handwritten case directory.

    :return: Absolute path to the handwritten corpus.
    :rtype: pathlib.Path
    """
    return _REPO_ROOT / _BENCH_ROOT / "cases/handwritten"


def _digest(path: Path) -> str:
    """Return a stable digest of one input file.

    Line endings are normalized first, so a Windows checkout and a Unix checkout
    of the same corpus produce the same manifest.

    :param path: File to digest.
    :type path: pathlib.Path
    :return: Hex SHA-256 of the normalized bytes.
    :rtype: str
    """
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check() -> None:
    """Confirm the corpus and layout match what the runner and contract expect.

    :return: ``None``.
    :rtype: None
    :raises BenchmarkFailure: If a case, directory, or map entry is missing.
    """
    problems: List[str] = []
    cases = _cases_dir()
    if not (cases / _MODEL).exists():
        problems.append("%s is missing." % (_BENCH_ROOT / "cases/handwritten" / _MODEL))
    for name, _expected, _why in _CASES:
        query = cases / ("%s.fbmcq" % name)
        if not query.exists():
            problems.append("%s is missing." % query.relative_to(_REPO_ROOT))
    for relative in ("cases/generated", "outputs/runs", "README.md", "schema.json"):
        target = _REPO_ROOT / _BENCH_ROOT / relative
        if not target.exists():
            problems.append("%s is missing." % (_BENCH_ROOT / relative))
    expected_arms = (_BASELINE_LABEL, "none", "formal", "proof")
    if _ARMS != expected_arms:
        problems.append("The contrast arms no longer match the frozen four.")
    if len(_BASELINE_COMMIT) != 40:
        problems.append("The baseline commit must be recorded in full.")
    if not _BASELINE_COMMIT.startswith(_BASELINE_LABEL.split("-")[1]):
        problems.append("The baseline label and commit disagree.")
    names = [name for name, _source, _note in _MEASUREMENT_MAP]
    if len(names) != len(set(names)):
        problems.append("The measurement map has a duplicate metric name.")
    if problems:
        raise BenchmarkFailure("\n".join("- %s" % item for item in problems))


def _child_script() -> str:
    """Return the program each sample runs in its own interpreter.

    It prints one JSON object on standard output.  Keeping it here rather than in
    a separate file means the measured code and the measurement stay together.

    :return: Python source for the child process.
    :rtype: str
    """
    return r"""
import json, sys, time
from pyfcstm.model import load_state_machine_from_file
from pyfcstm.bmc import compile_bmc_query, solve_bmc_property

model_path, query_path, mode = sys.argv[1], sys.argv[2], sys.argv[3]
model = load_state_machine_from_file(model_path)
query_text = open(query_path, encoding="utf-8").read()
# The baseline arm predates the option, so it is called without it rather than
# with "none" -- passing an argument that revision does not accept would measure
# a TypeError, and passing "none" here would measure this revision's default
# path under the baseline's name.
kwargs = {} if mode == "baseline" else {"infeasibility_explanation": mode}
# Compilation is outside the timed region: it is the same work in every arm, and
# including it would dilute the difference the benchmark exists to show.
formula = compile_bmc_query(model, query_text, query_source_path=query_path)
started = time.perf_counter()
result = solve_bmc_property(formula, **kwargs)
wall_ms = (time.perf_counter() - started) * 1000.0

record = {"wall_ms": wall_ms, "outcome": result.outcome, "stages": {}}
feasibility = getattr(result, "feasibility", None)
checks = getattr(feasibility, "refinement_checks", ()) or ()
record["solver_checks"] = len(checks)
for check in checks:
    record["stages"][check.name] = check.elapsed_ms
record["total_elapsed_ms"] = getattr(result, "total_elapsed_ms", None)

explanation = getattr(feasibility, "explanation", None)
if explanation is not None:
    record["requested_mode"] = explanation.requested_mode
    record["achieved_mode"] = explanation.achieved_mode
    record["status"] = explanation.status
    record["classification"] = explanation.classification
    core = explanation.core
    if core is not None:
        record["core_size"] = len(core.items)
        record["reduction"] = core.reduction
        record["subset_minimality"] = core.subset_minimality
    narrative = explanation.narrative
    if narrative is not None:
        record["derivation_status"] = narrative.derivation_status
    proof = explanation.proof
    if proof is not None:
        record["proof_nodes"] = len(proof.nodes)
        # Timed here because the production ledger has no entry for it.  The
        # proof is already built, so this measures reading it and nothing else.
        from pyfcstm.bmc.proof_text import linearize_proof

        started = time.perf_counter()
        linearize_proof(proof)
        record["stages"]["proof_linearization"] = (
            time.perf_counter() - started
        ) * 1000.0

print(json.dumps(record))
"""


def _run_sample(query: Path, mode: str) -> Dict[str, Any]:
    """Run one sample in a fresh interpreter and return what it measured.

    :param query: Path to the ``.fbmcq`` file.
    :type query: pathlib.Path
    :param mode: ``baseline``, ``none``, ``formal`` or ``proof``.
    :type mode: str
    :return: The child's record, with ``peak_rss_bytes`` when available and an
        ``error`` key when the child failed.
    :rtype: Dict[str, Any]
    """
    command = [
        sys.executable,
        "-c",
        _child_script(),
        str(_cases_dir() / _MODEL),
        str(query),
        mode,
    ]
    peak = _spawn_and_watch(command)
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


def _spawn_and_watch(command: Sequence[str]) -> Dict[str, Any]:
    """Run a child process and sample its resident set size while it lives.

    :param command: Argument list to run.
    :type command: Sequence[str]
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
        cwd=str(_REPO_ROOT),
        text=True,
    )
    peak: Optional[int] = None
    if psutil is not None:
        try:
            handle = psutil.Process(process.pid)
            while process.poll() is None:
                try:
                    rss = handle.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # The child exited between poll and read, or the platform
                    # refuses the query; either way there is nothing more to
                    # sample and the peak so far is what we have.
                    break
                peak = rss if peak is None else max(peak, rss)
        except psutil.NoSuchProcess:
            # The child finished before the first sample.  Its peak is unknown,
            # which is reported rather than guessed.
            peak = None
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        return {
            "error": "child exited %d" % process.returncode,
            "stderr": stderr.strip()[:2000],
        }
    return {"stdout": stdout, "stderr": stderr, "peak_rss_bytes": peak}


def _environment() -> Dict[str, Any]:
    """Return the machine and dependency facts a run has to be read against.

    :return: Interpreter, Z3, OS and CPU facts.
    :rtype: Dict[str, Any]
    """
    try:
        import z3

        z3_version = z3.get_version_string()
    except ImportError:
        # Recorded as unavailable rather than omitted, so a run without the
        # solver is not mistaken for one whose version went unrecorded.
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

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=str(_REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ).stdout.strip()

    porcelain = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(porcelain),
        "porcelain": porcelain.splitlines() if porcelain else [],
    }


def _percentile(values: Sequence[float], fraction: float) -> Optional[float]:
    """Return a percentile by nearest rank, or ``None`` for no values.

    Nearest rank rather than interpolation, because a repetition count in the
    single digits makes an interpolated value look more precise than it is.

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


def _summarize(samples: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Reduce repeated samples of one arm to a distribution.

    :param samples: Measured records for one case and arm.
    :type samples: Sequence[Dict[str, Any]]
    :return: Distribution, failure count, and the observed explanation facts.
    :rtype: Dict[str, Any]
    """
    good = [item for item in samples if not item.get("error")]
    walls = [item["wall_ms"] for item in good if item.get("wall_ms") is not None]
    rss = [
        item["peak_rss_bytes"]
        for item in good
        if item.get("peak_rss_bytes") is not None
    ]
    stages: Dict[str, Any] = {}
    for item in good:
        for name, value in (item.get("stages") or {}).items():
            stages.setdefault(name, []).append(value)
    summary: Dict[str, Any] = {
        "samples": len(samples),
        "failures": len(samples) - len(good),
        "wall_ms": {
            "p50": _percentile(walls, 0.5),
            "p95": _percentile(walls, 0.95),
            "max": max(walls) if walls else None,
        },
        "peak_child_rss_bytes": max(rss) if rss else None,
        "stages_p50_ms": {
            name: _percentile(values, 0.5) for name, values in sorted(stages.items())
        },
    }
    if not rss:
        summary["peak_child_rss_note"] = "unavailable on this run; not reported as zero"
    for key in (
        "outcome",
        "requested_mode",
        "achieved_mode",
        "status",
        "classification",
        "core_size",
        "reduction",
        "subset_minimality",
        "derivation_status",
        "proof_nodes",
        "solver_checks",
    ):
        observed = {item.get(key) for item in good if key in item}
        if len(observed) == 1:
            summary[key] = observed.pop()
        elif len(observed) > 1:
            # Instability in a published field is a finding, not noise to hide.
            summary[key] = sorted(str(value) for value in observed)
            summary.setdefault("unstable_fields", []).append(key)
    if good and any(item.get("error") for item in samples):
        summary["first_error"] = next(
            item["error"] for item in samples if item.get("error")
        )
    elif not good:
        summary["first_error"] = samples[0].get("error") if samples else "no samples"
    return summary


def _run(repetitions: int, warmups: int, run_id: str) -> Path:
    """Measure the corpus across every arm and write an immutable run.

    :param repetitions: Measured repetitions per sample.
    :type repetitions: int
    :param warmups: Discarded runs before measuring.
    :type warmups: int
    :param run_id: Directory name for this run; must not already exist.
    :type run_id: str
    :return: The directory the run was written to.
    :rtype: pathlib.Path
    :raises BenchmarkFailure: If the run directory already exists.
    """
    output = _REPO_ROOT / _BENCH_ROOT / "outputs/runs" / run_id
    if output.exists():
        raise BenchmarkFailure(
            "%s already exists; a correction must create a new run rather than "
            "overwrite a saved one." % output.relative_to(_REPO_ROOT)
        )
    output.mkdir(parents=True)

    raw_lines: List[str] = []
    summary: Dict[str, Any] = {}
    for name, expected, why in _CASES:
        query = _cases_dir() / ("%s.fbmcq" % name)
        summary[name] = {"expected_depth": expected, "why": why, "arms": {}}
        for arm in _ARMS:
            mode = "baseline" if arm == _BASELINE_LABEL else arm
            for _ in range(warmups):
                _run_sample(query, mode)
            samples = [_run_sample(query, mode) for _ in range(repetitions)]
            for index, sample in enumerate(samples):
                raw_lines.append(
                    json.dumps(
                        {
                            "case": name,
                            "arm": arm,
                            "repetition": index,
                            "record": sample,
                        },
                        sort_keys=True,
                    )
                )
            summary[name]["arms"][arm] = _summarize(samples)

    manifest = {
        "schema": "bmc-infeasibility-benchmark/v1",
        "run_id": run_id,
        "baseline": {"label": _BASELINE_LABEL, "commit": _BASELINE_COMMIT},
        "arms": list(_ARMS),
        "repetitions": repetitions,
        "warmups": warmups,
        "environment": _environment(),
        "candidate": _dirty_state(),
        "inputs": {
            path.name: _digest(path)
            for path in sorted(_cases_dir().iterdir())
            if path.is_file()
        },
        "measurement_map": [
            {"metric": metric, "source": source, "note": note}
            for metric, source, note in _MEASUREMENT_MAP
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "raw.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(_report(manifest, summary), encoding="utf-8")
    return output


def _report(manifest: Dict[str, Any], summary: Dict[str, Any]) -> str:
    """Render the human report for one run.

    :param manifest: The run manifest.
    :type manifest: Dict[str, Any]
    :param summary: The aggregated results.
    :type summary: Dict[str, Any]
    :return: Markdown report text.
    :rtype: str
    """
    lines = [
        "# BMC infeasibility explanation benchmark",
        "",
        "Run `%s`, candidate `%s`%s."
        % (
            manifest["run_id"],
            manifest["candidate"]["commit"][:12],
            " (dirty tree)" if manifest["candidate"]["dirty"] else "",
        ),
        "Baseline `%s` = `%s`." % (_BASELINE_LABEL, _BASELINE_COMMIT),
        "",
        "%d measured repetitions per sample after %d discarded warmups, each "
        "sample in its own interpreter."
        % (manifest["repetitions"], manifest["warmups"]),
        "",
        "## Wall time by arm (p50 ms)",
        "",
        "| Case | expected | %s |" % " | ".join(_ARMS),
        "|---|---|%s" % ("---|" * len(_ARMS)),
    ]
    for name, case in sorted(summary.items()):
        cells = []
        for arm in _ARMS:
            value = case["arms"][arm]["wall_ms"]["p50"]
            cells.append("%.1f" % value if value is not None else "n/a")
        lines.append(
            "| `%s` | `%s` | %s |" % (name, case["expected_depth"], " | ".join(cells))
        )
    lines += [
        "",
        "## What each arm achieved",
        "",
        "| Case | arm | achieved | status | core | proof nodes |",
        "|---|---|---|---|---|---|",
    ]
    for name, case in sorted(summary.items()):
        for arm in _ARMS:
            arm_summary = case["arms"][arm]
            lines.append(
                "| `%s` | `%s` | `%s` | `%s` | %s | %s |"
                % (
                    name,
                    arm,
                    arm_summary.get("achieved_mode", "-"),
                    arm_summary.get("status", "-"),
                    arm_summary.get("core_size", "-"),
                    arm_summary.get("proof_nodes", "-"),
                )
            )
    failures = [
        (name, arm)
        for name, case in sorted(summary.items())
        for arm in _ARMS
        if case["arms"][arm]["failures"]
    ]
    unstable = [
        (name, arm, case["arms"][arm]["unstable_fields"])
        for name, case in sorted(summary.items())
        for arm in _ARMS
        if case["arms"][arm].get("unstable_fields")
    ]
    lines += ["", "## Failures, degradation, and instability", ""]
    lines.append(
        "Failed samples: %s."
        % (", ".join("%s/%s" % pair for pair in failures) if failures else "none")
    )
    lines.append(
        "Unstable published fields: %s."
        % (
            "; ".join("%s/%s: %s" % triple for triple in unstable)
            if unstable
            else "none"
        )
    )
    degraded = [
        name
        for name, case in sorted(summary.items())
        if case["arms"]["proof"].get("achieved_mode") == "formal"
    ]
    lines.append(
        "Degraded at `proof` depth: %s."
        % (", ".join("`%s`" % name for name in degraded) if degraded else "none")
    )
    lines += [
        "",
        "## Measurement map",
        "",
        "| Metric | Source | Note |",
        "|---|---|---|",
    ]
    for metric, source, note in _MEASUREMENT_MAP:
        lines.append("| `%s` | `%s` | %s |" % (metric, source, note))
    lines += [
        "",
        "Reconstruct this report from the raw records with:",
        "",
        "```bash",
        "python tools/run_bmc_infeasibility_benchmark.py --rebuild %s"
        % manifest["run_id"],
        "```",
        "",
    ]
    return "\n".join(lines)


def _rebuild(run_id: str) -> Path:
    """Rebuild one run's summary and report from its raw records.

    Proves the aggregation is a function of the recorded samples rather than of
    the process that produced them, which is what makes a saved run auditable.

    :param run_id: Directory name of a saved run.
    :type run_id: str
    :return: The run directory.
    :rtype: pathlib.Path
    :raises BenchmarkFailure: If the run or its records are missing.
    """
    output = _REPO_ROOT / _BENCH_ROOT / "outputs/runs" / run_id
    raw = output / "raw.jsonl"
    manifest_path = output / "manifest.json"
    if not raw.exists() or not manifest_path.exists():
        raise BenchmarkFailure(
            "%s has no raw.jsonl and manifest.json to rebuild from."
            % output.relative_to(_REPO_ROOT)
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for line in raw.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        grouped.setdefault(entry["case"], {}).setdefault(entry["arm"], []).append(
            entry["record"]
        )
    summary: Dict[str, Any] = {}
    expected = {name: (depth, why) for name, depth, why in _CASES}
    for name, arms in grouped.items():
        depth, why = expected.get(name, ("unknown", "not in the current corpus"))
        summary[name] = {"expected_depth": depth, "why": why, "arms": {}}
        for arm, samples in arms.items():
            summary[name]["arms"][arm] = _summarize(samples)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(_report(manifest, summary), encoding="utf-8")
    return output


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the benchmark from the command line.

    :param argv: Argument list, defaults to ``None`` for ``sys.argv[1:]``
    :type argv: Sequence[str], optional
    :return: ``0`` on success, ``1`` on a controlled failure.
    :rtype: int

    Example::

        $ python tools/run_bmc_infeasibility_benchmark.py --check
        Benchmark corpus, measurement map, and layout are consistent.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--rebuild", metavar="RUN_ID")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    if not (args.check or args.run or args.rebuild):
        parser.error("Pass --check, --run, or --rebuild RUN_ID.")
    if args.check:
        try:
            _check()
        except BenchmarkFailure as err:
            # The corpus or layout does not match what the runner measures.
            print("Benchmark self-check failed:\n%s" % err)
            return 1
        print("Benchmark corpus, measurement map, and layout are consistent.")
    if args.run:
        run_id = args.run_id or _dirty_state()["commit"][:12]
        try:
            output = _run(args.repetitions, args.warmups, run_id)
        except BenchmarkFailure as err:
            # A saved run is immutable; this refuses rather than overwriting.
            print("Benchmark run failed:\n%s" % err)
            return 1
        print("Wrote %s" % (output / "report.md").relative_to(_REPO_ROOT))
    if args.rebuild:
        try:
            output = _rebuild(args.rebuild)
        except BenchmarkFailure as err:
            # The run is missing the records a rebuild needs.
            print("Benchmark rebuild failed:\n%s" % err)
            return 1
        print("Rebuilt %s" % (output / "report.md").relative_to(_REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
