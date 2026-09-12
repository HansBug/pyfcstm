#!/usr/bin/env python3
"""Compare source-partition resolution revisions using the existing BMC sampler."""

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import tempfile

from run_bmc_solving_benchmark import _dump, _environment, _run_sample


def revision(path):
    path = path.resolve()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=str(path), text=True
    )
    if dirty:
        raise ValueError("Benchmark checkout must be clean: %s" % path)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(path), text=True
    ).strip()
    return {"path": str(path), "commit": commit, "dirty": False}


def rebuild(output):
    manifest = json.loads((output / "manifest.json").read_text())
    rows = [
        json.loads(line) for line in (output / "raw.jsonl").read_text().splitlines()
    ]
    specs = manifest["samples"]
    if len(rows) != len(specs):
        raise ValueError("Incomplete run: %d of %d samples" % (len(rows), len(specs)))
    groups = {}
    for row, spec in zip(rows, specs):
        if any(row[key] != value for key, value in spec.items()):
            raise ValueError("Record does not match the registered sample order")
        if "error" in row:
            raise ValueError(row["error"])
        expected = manifest["expected"][row["case"] + "/" + row["query"]]
        if any(row[key] != value for key, value in expected.items()):
            raise ValueError("Sample disagrees with corpus expectations")
        if row["status"] == "sat" and row["replay_ok"] is not True:
            raise ValueError("SAT sample did not pass ordinary replay")
        if row["suffix_replay_ok"] is False:
            raise ValueError("Incomplete suffix replay failed")
        if (
            Path(row["pyfcstm_file"]).parent
            != Path(manifest["arms"][row["arm"]]["path"]) / "pyfcstm"
        ):
            raise ValueError("Sample imported the wrong revision")
        if not row["warmup"]:
            groups.setdefault((row["case"], row["query"], row["arm"]), []).append(row)
    comparisons = []
    for case, query, arm in sorted(groups):
        if arm != "baseline":
            continue
        base = groups[case, query, arm]
        candidate = groups[case, query, "candidate"]
        comparison = {"case": case, "query": query, "n": len(base)}
        for field in ("api_total_ms", "build_ms", "solve_ms", "peak_rss_bytes"):
            b = statistics.median(row[field] for row in base)
            c = statistics.median(row[field] for row in candidate)
            comparison[field] = {
                "baseline": b,
                "candidate": c,
                "change_percent": (c / b - 1) * 100,
            }
        if {row["formula_dag_nodes"] for row in base} != {
            row["formula_dag_nodes"] for row in candidate
        }:
            raise ValueError("Formula DAG sizes changed")
        comparisons.append(comparison)
    vtol = "claude_vtol_mission_supervision"
    reach = next(
        row for row in comparisons if row["case"] == vtol and row["query"] == "reach"
    )
    regression = [
        row
        for row in comparisons
        if row["case"] != vtol and row["api_total_ms"]["change_percent"] > 5
    ]
    memory = [
        row for row in comparisons if row["peak_rss_bytes"]["change_percent"] > 10
    ]
    borderline = [
        {"case": row["case"], "query": row["query"]}
        for row in comparisons
        if (row["case"] != vtol and abs(row["api_total_ms"]["change_percent"] - 5) <= 2)
        or abs(row["peak_rss_bytes"]["change_percent"] - 10) <= 2
        or (
            row["case"] == vtol
            and row["query"] == "reach"
            and abs(row["api_total_ms"]["change_percent"] + 50) <= 2
        )
    ]
    summary = {
        "comparisons": comparisons,
        "vtol_reach_pass": reach["api_total_ms"]["change_percent"] <= -50,
        "api_regressions": regression,
        "memory_regressions": memory,
        "borderline_queries": borderline,
        "sat_replays": sum(row["status"] == "sat" for row in rows if not row["warmup"]),
        "measured_samples": sum(not row["warmup"] for row in rows),
        "correctness_pass": True,
    }
    (output / "summary.json").write_text(_dump(summary), encoding="utf-8")
    lines = [
        "# Accepted-condition resolution benchmark",
        "",
        "Baseline: `%s`; candidate: `%s`."
        % (
            manifest["arms"]["baseline"]["commit"],
            manifest["arms"]["candidate"]["commit"],
        ),
        "",
        "API timing includes loading, compilation, solving and ordinary replay; imports and report serialization are excluded. Partition-local caches are released normally during compilation. RSS is the independent process high-water mark before diagnostic size traversal.",
        "",
        "Measured samples: %d; SAT replays: %d."
        % (summary["measured_samples"], summary["sat_replays"]),
        "",
        "| Query | API baseline ms | API candidate ms | API change | RSS change |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in comparisons:
        times = row["api_total_ms"]
        lines.append(
            "| %s/%s | %.3f | %.3f | %+.2f%% | %+.2f%% |"
            % (
                row["case"],
                row["query"],
                times["baseline"],
                times["candidate"],
                times["change_percent"],
                row["peak_rss_bytes"]["change_percent"],
            )
        )
    lines.extend(
        [
            "",
            "VTOL reach target: %s. Non-VTOL API failures: %d. RSS failures: %d. Borderline queries requiring the registered follow-up: %d."
            % (
                summary["vtol_reach_pass"],
                len(regression),
                len(memory),
                len(borderline),
            ),
            "",
            "The first-round judgment remains authoritative; follow-up measurements do not replace it.",
            "",
        ]
    )
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def self_check():
    with tempfile.TemporaryDirectory(prefix="bmc-resolution-check-") as directory:
        output = Path(directory)
        arms = {
            name: {"path": "/" + name, "commit": name}
            for name in ("baseline", "candidate")
        }
        expected = {}
        rows, specs = [], []
        for case in ("claude_vtol_mission_supervision", "small"):
            expected[case + "/reach"] = {
                "status": "sat",
                "outcome": "witness",
                "property_satisfied": True,
            }
            for arm in arms:
                for repetition in range(1, 6):
                    spec = {
                        "case": case,
                        "query": "reach",
                        "arm": arm,
                        "repetition": repetition,
                        "warmup": False,
                    }
                    specs.append(spec)
                    row = dict(spec, **expected[case + "/reach"])
                    row.update(
                        api_total_ms=40
                        if arm == "candidate" and case != "small"
                        else 100,
                        build_ms=30,
                        solve_ms=10,
                        peak_rss_bytes=1000,
                        formula_dag_nodes=10,
                        replay_ok=True,
                        suffix_replay_ok=None,
                        pyfcstm_file="/" + arm + "/pyfcstm/__init__.py",
                    )
                    rows.append(row)
        (output / "manifest.json").write_text(
            _dump({"arms": arms, "samples": specs, "expected": expected})
        )

        def write(values):
            (output / "raw.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in values)
            )

        write(rows)
        summary = rebuild(output)
        assert summary["vtol_reach_pass"] and not summary["api_regressions"]
        assert summary["sat_replays"] == 20
        before = (output / "summary.json").read_bytes()
        rebuild(output)
        assert (output / "summary.json").read_bytes() == before
        for field, value in (
            ("status", "unsat"),
            ("replay_ok", False),
            ("pyfcstm_file", "/wrong/pyfcstm/__init__.py"),
            ("formula_dag_nodes", 11),
        ):
            changed = [dict(row) for row in rows]
            changed[0][field] = value
            write(changed)
            try:
                rebuild(output)
            except ValueError:
                # ValueError: the deliberately corrupted sample violates the run contract.
                pass
            else:
                raise AssertionError("Accepted corrupted " + field)
        write(rows[:-1])
        try:
            rebuild(output)
        except ValueError:
            # ValueError: the final registered sample is intentionally absent.
            pass
        else:
            raise AssertionError("Accepted incomplete run")
        for row in rows:
            if row["arm"] == "candidate" and row["case"] == "small":
                row["api_total_ms"] = 106
                row["peak_rss_bytes"] = 1110
        write(rows)
        summary = rebuild(output)
        assert (
            len(summary["api_regressions"]) == len(summary["memory_regressions"]) == 1
        )
        assert summary["borderline_queries"] == [{"case": "small", "query": "reach"}]
    print(
        "Resolution benchmark rejects invalid records and preserves threshold failures."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    if args.check:
        self_check()
        return
    if args.output is None:
        parser.error("--output is required")
    if args.rebuild:
        rebuild(args.output)
        return
    if args.baseline is None or args.candidate is None:
        parser.error("Both revision checkouts are required")
    arms = {
        name: revision(path)
        for name, path in (("baseline", args.baseline), ("candidate", args.candidate))
    }
    corpus = args.baseline.resolve() / "benchmarks/bmc/solving/cases"
    specs, expected, inputs = [], {}, {}
    for case in sorted(corpus.iterdir()):
        if not case.is_dir():
            continue
        metadata = json.loads((case / "case.json").read_text())
        for path in sorted(case.iterdir()):
            if path.is_file():
                relative = path.relative_to(args.baseline.resolve())
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                other = args.candidate.resolve() / relative
                if hashlib.sha256(other.read_bytes()).hexdigest() != digest:
                    raise ValueError("Revision corpus mismatch: %s" % relative)
                inputs[str(relative)] = digest
        for query in metadata["queries"]:
            expected[case.name + "/" + query["kind"]] = query["expected"]
            for repetition in range(6):
                order = (
                    ("baseline", "candidate")
                    if repetition % 2 == 0
                    else ("candidate", "baseline")
                )
                for arm in order:
                    specs.append(
                        {
                            "case": case.name,
                            "query": query["kind"],
                            "query_file": query["file"],
                            "arm": arm,
                            "warmup": repetition == 0,
                            "repetition": repetition,
                        }
                    )
    manifest = {
        "arms": arms,
        "environment": _environment(),
        "samples": specs,
        "expected": expected,
        "inputs": inputs,
        "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sampler_sha256": hashlib.sha256(
            Path(__file__).with_name("run_bmc_solving_benchmark.py").read_bytes()
        ).hexdigest(),
        "thresholds": {
            "vtol_reach_improvement": 0.50,
            "non_vtol_api_regression": 0.05,
            "rss_regression": 0.10,
        },
        "warmups": 1,
        "repetitions": 5,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "manifest.json").write_text(_dump(manifest), encoding="utf-8")
    with (args.output / "raw.jsonl").open("x", encoding="utf-8") as stream:
        for index, spec in enumerate(specs):
            tree = Path(arms[spec["arm"]]["path"])
            case = tree / "benchmarks/bmc/solving/cases" / spec["case"]
            row = _run_sample(
                case / "model.fcstm",
                case / spec["query_file"],
                {"compile": {}, "solve": {}},
                tree,
            )
            row.update(spec)
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            if "error" in row:
                raise RuntimeError(row["error"])
            print(
                "%d/%d %s/%s %s"
                % (index + 1, len(specs), spec["case"], spec["query"], spec["arm"]),
                flush=True,
            )
    rebuild(args.output)


if __name__ == "__main__":
    main()
