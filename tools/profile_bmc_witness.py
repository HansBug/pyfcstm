#!/usr/bin/env python3
"""Measure complete BMC API/CLI calls and attribute witness processing cost.

Run against an existing checkout with its dependencies installed. Each timed
sample uses a fresh interpreter. cProfile runs separately and never supplies
the uninstrumented wall-time measurements. This is maintenance tooling, not a
public pyfcstm API or a pytest suite.
"""

import argparse
import contextlib
import cProfile
import hashlib
import io
import json
import os
from pathlib import Path
import pstats
import subprocess
import sys
import time


def _child(case, query, enabled, mode):
    # The script may live outside the measured revision. Import that revision,
    # never the working copy that happens to hold this profiling tool.
    sys.path.insert(0, os.getcwd())
    import pyfcstm
    import z3
    from pyfcstm.entry import build_bmc_output, pyfcstmcli

    root = Path("benchmarks/bmc/solving/cases") / case
    model, query_path = str(root / "model.fcstm"), str(root / (query + ".fbmcq"))
    profiler = cProfile.Profile() if mode == "profile" else None
    output = io.StringIO()
    if profiler is not None:
        profiler.enable()
    started = time.perf_counter()
    if mode == "cli":
        args = ["bmc", "-i", model, "-q", query_path, "--json"]
        if enabled:
            args.append("--cone-slicing")
        with contextlib.redirect_stdout(output):
            code = pyfcstmcli.main(args=args, standalone_mode=False)
        body = output.getvalue()
    else:
        body, code = build_bmc_output(
            model, query_path, json_output=True, cone_slicing=enabled
        )
    elapsed = (time.perf_counter() - started) * 1000
    if profiler is not None:
        profiler.disable()
    payload = json.loads(body)
    result = payload["result"]
    if payload["replay"] is not None and not payload["replay"]["ok"]:
        raise RuntimeError("Profiled witness failed ordinary runtime replay.")
    if payload["exit_code"] != code:
        raise RuntimeError("Report and public invocation exit codes disagree.")
    record = {
        "case": case,
        "query": query,
        "cone_slicing": enabled,
        "mode": mode,
        "call_ms": elapsed,
        "exit_code": code,
        "status": result["status"],
        "outcome": result["outcome"],
        "property_satisfied": result["property_satisfied"],
        "package": str(Path(pyfcstm.__file__).resolve()),
        "python": sys.version,
        "z3": z3.get_version_string(),
    }
    if profiler is not None:
        stats = pstats.Stats(profiler).stats
        phases = dict.fromkeys(
            (
                "build",
                "solve_core",
                "internal_decode",
                "external_decode",
                "external_replay",
            ),
            0.0,
        )
        functions = []
        z3_check_ms = 0.0
        for (filename, line, name), (
            _,
            calls,
            own,
            cumulative,
            callers,
        ) in stats.items():
            if name == "check" and Path(filename).name == "z3.py":
                z3_check_ms += sum(
                    values[3] * 1000
                    for (_, _, caller), values in callers.items()
                    if caller == "_check_with_budget"
                )
            if name in ("compile_bmc_query", "_solve_property"):
                phases["build" if name == "compile_bmc_query" else "solve_core"] += (
                    cumulative * 1000
                )
            if name == "decode_bmc_result_trace":
                for (_, _, caller), values in callers.items():
                    if caller in ("solve_bmc_property", "_decode_bmc_result_trace"):
                        phase = (
                            "internal_decode"
                            if caller == "solve_bmc_property"
                            else "external_decode"
                        )
                        phases[phase] += values[3] * 1000
            if name == "replay_bmc_witness":
                for (_, _, caller), values in callers.items():
                    # The CLI wrapper is outside the decoder and internal fill.
                    if caller == "_replay_bmc_witness":
                        phases["external_replay"] += values[3] * 1000
            if name in (
                "compile_bmc_query",
                "_solve_property",
                "_decode_witness_trace",
                "_fill_cone_trace",
                "replay_bmc_witness",
                "Z3_solver_check_assumptions",
                "Z3_solver_check",
                "build_bmc_output",
            ):
                functions.append(
                    {
                        "function": name,
                        "file": os.path.relpath(filename),
                        "line": line,
                        "calls": calls,
                        "self_ms": own * 1000,
                        "inclusive_ms": cumulative * 1000,
                    }
                )
        # These are disjoint call subtrees; nested Z3/replay diagnostics in
        # functions are explanatory only and must not be added to phase totals.
        phases["other"] = elapsed - sum(phases.values())
        if phases["other"] < -0.01 or phases["build"] <= 0 or phases["solve_core"] <= 0:
            raise RuntimeError(
                "Profiling call boundaries no longer partition the public API."
            )
        if result["status"] == "sat" and (
            phases["external_decode"] <= 0 or phases["external_replay"] <= 0
        ):
            raise RuntimeError(
                "A SAT profile must include external decoding and replay."
            )
        phases["solve_bookkeeping"] = phases.pop("solve_core") - z3_check_ms
        phases["z3_check"] = z3_check_ms
        if phases["solve_bookkeeping"] < -0.01 or z3_check_ms <= 0:
            raise RuntimeError("Budgeted Z3 checks must be a subset of core solving.")
        record["phases_ms"] = phases
        record["functions"] = sorted(
            functions, key=lambda item: (item["file"], item["line"])
        )
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case", action="append")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument(
        "--child", nargs=4, metavar=("CASE", "QUERY", "ENABLED", "MODE")
    )
    args = parser.parse_args()
    if args.child:
        case, query, enabled, mode = args.child
        print(json.dumps(_child(case, query, enabled == "true", mode)))
        return
    if args.output is None or args.output.exists() or args.repetitions < 1:
        parser.error("Supply a new --output path and positive --repetitions.")
    checkout = args.checkout.resolve()
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(checkout), text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=str(checkout),
        text=True,
    )
    if dirty:
        parser.error("Measure a clean checkout with no untracked files.")
    cases = args.case or [
        "conveyor_counters",
        "heater_logging",
        "telemetry_outputs",
        "codex_traffic_emergency_priority",
    ]
    records, inputs = [], {}
    for case in cases:
        root = checkout / "benchmarks/bmc/solving/cases" / case
        specification = json.loads((root / "case.json").read_text())
        expected = {
            entry["kind"]: entry["expected"] for entry in specification["queries"]
        }
        for filename in ("model.fcstm", "reach.fbmcq", "invariant.fbmcq"):
            path = root / filename
            inputs[str(path.relative_to(checkout))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        for query in ("reach", "invariant"):
            for enabled in (False, True):
                for mode in ("api", "cli", "profile"):
                    for repetition in range(
                        1 if mode == "profile" else args.repetitions
                    ):
                        started = time.perf_counter()
                        run = subprocess.run(
                            [
                                sys.executable,
                                str(Path(__file__).resolve()),
                                "--child",
                                case,
                                query,
                                str(enabled).lower(),
                                mode,
                            ],
                            cwd=str(checkout),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=300,
                            check=True,
                        )
                        process_ms = (time.perf_counter() - started) * 1000
                        record = json.loads(run.stdout)
                        if Path(record["package"]).parent != checkout / "pyfcstm":
                            raise RuntimeError("Sample imported the wrong revision.")
                        if any(
                            record[key] != value
                            for key, value in expected[query].items()
                        ):
                            raise RuntimeError(
                                "Sample disagrees with corpus expectation."
                            )
                        record.update(repetition=repetition, process_ms=process_ms)
                        records.append(record)
                print("Measured %s/%s slicing=%s" % (case, query, enabled), flush=True)
    document = {
        "commit": commit,
        "dirty": False,
        "inputs": inputs,
        "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "repetitions": args.repetitions,
        "records": records,
        "timing_contract": {
            "call_ms": "Complete public file API or Click CLI call, including JSON report serialization; imports/startup excluded.",
            "process_ms": "Fresh interpreter, imports, call, and profiling-tool transport overhead; not a bare CLI startup benchmark.",
            "profile": "Separate cProfile invocation, diagnostic only. phases_ms are disjoint; functions overlap and must not be summed.",
        },
    }
    # Exclusive creation protects an existing measurement from accidental reuse.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
