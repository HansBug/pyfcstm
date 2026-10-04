"""Reproduce the representative CLI comparison using the existing profiler child."""

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--tool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    arms = {}
    for name, tree in (("baseline", args.baseline), ("candidate", args.candidate)):
        assert not subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(tree)
        )
        arms[name] = {
            "path": str(tree.resolve()),
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=str(tree), text=True
            ).strip(),
        }
    specs = []
    for case in (
        "codex_vtol_mission_supervision",
        "codex_traffic_emergency_priority",
        "heater_logging",
    ):
        for query in ("reach", "invariant"):
            for repetition in range(6):
                for arm in (
                    ("baseline", "candidate")
                    if repetition % 2 == 0
                    else ("candidate", "baseline")
                ):
                    specs.append(
                        dict(
                            case=case,
                            query=query,
                            arm=arm,
                            repetition=repetition,
                            warmup=repetition == 0,
                        )
                    )
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        arms=arms,
        samples=specs,
        tool_sha256=hashlib.sha256(args.tool.read_bytes()).hexdigest(),
        driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        timing="Click CLI invocation including report serialization, excluding interpreter startup/imports. process_ms additionally includes startup/imports and profiler transport. No diagnostic patches or retained formulas.",
    )
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    rows = []
    with (args.output / "raw.jsonl").open("x") as stream:
        for index, spec in enumerate(specs):
            tree = Path(arms[spec["arm"]]["path"])
            started = time.perf_counter()
            result = subprocess.run(
                [
                    sys.executable,
                    str(args.tool.resolve()),
                    "--child",
                    spec["case"],
                    spec["query"],
                    "false",
                    "cli",
                ],
                cwd=str(tree),
                capture_output=True,
                text=True,
                check=True,
                timeout=300,
            )
            row = json.loads(result.stdout)
            row["process_ms"] = (time.perf_counter() - started) * 1000
            row.update(spec)
            assert Path(row["package"]).parent == tree / "pyfcstm"
            expected = next(
                q["expected"]
                for q in json.loads(
                    (
                        tree
                        / "benchmarks/bmc/solving/cases"
                        / spec["case"]
                        / "case.json"
                    ).read_text()
                )["queries"]
                if q["kind"] == spec["query"]
            )
            assert all(row[key] == value for key, value in expected.items())
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            rows.append(row)
            print(
                "%d/%d %s/%s %s"
                % (index + 1, len(specs), spec["case"], spec["query"], spec["arm"]),
                flush=True,
            )
    summary = []
    for case, query in sorted({(r["case"], r["query"]) for r in rows}):
        item = dict(case=case, query=query)
        for metric in ("call_ms", "process_ms"):
            medians = {
                arm: statistics.median(
                    r[metric]
                    for r in rows
                    if r["case"] == case
                    and r["query"] == query
                    and r["arm"] == arm
                    and not r["warmup"]
                )
                for arm in arms
            }
            medians["change_percent"] = (
                medians["candidate"] / medians["baseline"] - 1
            ) * 100
            item[metric] = medians
        summary.append(item)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
