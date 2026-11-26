"""Run region-aware BMC queries and print deterministic excerpts of the results."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

WORKDIR = Path(".region_bmc_results.tmp")


def bmc(model, query, *extra):
    """Run ``pyfcstm bmc`` on a query text; return (exit code, stdout, stderr, payload)."""
    WORKDIR.mkdir(exist_ok=True)
    query_file = WORKDIR / "query.fbmcq"
    query_file.write_text(query + "\n", encoding="utf-8")
    result_file = WORKDIR / "result.json"
    if result_file.exists():
        result_file.unlink()
    command = [sys.executable, "-m", "pyfcstm", "bmc", "-i", model, "-q", str(query_file)]
    command += list(extra)
    if "--json" in extra:
        command += ["-o", str(result_file)]
    done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    payload = None
    if result_file.exists():
        payload = json.loads(result_file.read_text(encoding="utf-8"))
    return done.returncode, done.stdout, done.stderr, payload


def section(title):
    print("== " + title)
    print()


def lines_of(text, drop=("Solver:", "Runtime safety check:")):
    """Return report lines without the nondeterministic timing lines."""
    return [line for line in text.splitlines() if not line.startswith(drop)]


def local_case(case):
    return "%s %s %s" % (case["scope"], case["kind"], case["label"])


try:
    section("witness of a model with regions: frames, steps, local cases")
    query = 'check reach <= 6: active("Job.Next");'
    print("query:  " + query)
    code, _, _, payload = bmc("region_job.fcstm", query, "--json")
    witness = payload["witness"]
    print("exit:   %d" % code)
    print("initial keys:  %s" % sorted(witness["initial"]))
    print("frame keys:    %s" % sorted(witness["frames"][1]))
    print("step keys:     %s" % sorted(witness["steps"][0]))
    print()
    for frame in witness["frames"]:
        print("frame %d: %s" % (frame["index"], frame.get("configuration")))
    print()
    for step in witness["steps"]:
        print("step %d: case_label=%s case_kind=%s" % (step["index"], step["case_label"], step["case_kind"]))
        for case in step["local_cases"]:
            print("    " + local_case(case))
    print()
    replay = payload["replay"]
    print("replay ok: %s, mismatches: %s" % (replay["ok"], replay["mismatches"]))
    print("runtime frame keys: %s" % sorted(replay["runtime_trace"]["frames"][1]))
    print(
        "runtime frames: %s"
        % [frame["configuration"] for frame in replay["runtime_trace"]["frames"]]
    )
    print()

    section("case_label names the case that ran outside every region")
    query = 'check cover <= 3: case("Controller.Idle::transition::Controller.Running::0");'
    print("query:  " + query)
    code, out, _, payload = bmc("region_controller.fcstm", query, "--json")
    print("exit:   %d" % code)
    print("witness.property.case_label: %s" % payload["witness"]["property"]["case_label"])
    for step in payload["witness"]["steps"]:
        print("step %d: case_label=%s" % (step["index"], step["case_label"]))
        for case in step["local_cases"]:
            print("    " + local_case(case))
    code, out, _, _ = bmc("region_controller.fcstm", query)
    lines = lines_of(out)
    print()
    for line in lines[lines.index("Trace"):]:
        if not line:
            break
        print(line)
    print()

    section("a hot start records the start configuration")
    query = 'init state("Job.Run{Work: Busy}"); check reach <= 1: true;'
    print("query:  " + query)
    code, _, _, payload = bmc("region_job.fcstm", query, "--json")
    print("exit:   %d" % code)
    print("witness.initial.configuration: %s" % payload["witness"]["initial"]["configuration"])
    print("witness.initial.state:         %s" % payload["witness"]["initial"]["state"])
    print()

    section("abstract calls carry the configuration at the moment of the call")
    query = 'check reach <= 2: called("Root.Run.B.B1.BEnter");'
    print("query:  " + query)
    code, _, _, payload = bmc("region_calls.fcstm", query, "--json")
    print("exit:   %d" % code)
    print("call keys: %s" % sorted(payload["witness"]["steps"][0]["abstract_calls"][0]))
    for call in payload["witness"]["steps"][0]["abstract_calls"]:
        print(
            "  %d %s | stage=%s role=%s | state=%s active_leaf=%s | %s"
            % (
                call["ordinal"],
                call["action_name"],
                call["stage"],
                call["role"],
                call["state"],
                call["active_leaf"],
                call["configuration"],
            )
        )
    print()

    section("the same fields are absent for a model without regions")
    query = 'check reach <= 2: active("Root.Busy");'
    print("query:  " + query)
    code, _, _, payload = bmc("region_plain.fcstm", query, "--json")
    witness = payload["witness"]
    print("exit:   %d" % code)
    print("initial keys:  %s" % sorted(witness["initial"]))
    print("frame keys:    %s" % sorted(witness["frames"][1]))
    print("step keys:     %s" % sorted(witness["steps"][0]))
    print("case_label of step 0: %s" % witness["steps"][0]["case_label"])
    print()

    section("human report: one line per local case")
    query = 'check reach <= 6: active("Job.Next");'
    print("query:  " + query)
    code, out, _, _ = bmc("region_job.fcstm", query)
    print("exit:   %d" % code)
    for line in lines_of(out):
        print(line)
    print()

    section("a nested owner: scopes in the human report")
    query = 'check reach <= 2: active("Root.Run{Work: Inner{X: x2}}");'
    print("query:  " + query)
    code, out, _, _ = bmc("region_nested.fcstm", query)
    print("exit:   %d" % code)
    lines = lines_of(out)
    for line in lines[lines.index("Trace"):]:
        if not line:
            break
        print(line)
    print()

    section("diagnostics")
    for model, query in (
        ("region_job.fcstm", 'init state("Job.Run{Prep: [done], Work: [done]}"); check reach <= 1: true;'),
        ("region_job.fcstm", 'check reach <= 1: active("Job.Run{Zed: Wait}");'),
        ("region_job.fcstm", "check reach <= 1: " + " && ".join(["true"] * 100) + ";"),
        ("region_job.fcstm", "check reach <= 1: " + " && ".join(["true"] * 101) + ";"),
    ):
        text = query if len(query) < 120 else "check reach <= 1: true && true && ... && true;  // %d terms" % query.count("true")
        print("query:  " + text)
        code, out, err, _ = bmc(model, query)
        print("exit:   %d" % code)
        print("stdout: " + (out.splitlines()[0] if out else "(empty)"))
        print("stderr: " + (err.strip() or "(empty)"))
        print()

    section("a group that re-enters itself too often (default max_group_reentries is 16)")
    query = "check reach <= 1: terminated();"
    print("query:  " + query)
    code, out, err, _ = bmc("region_reentry.fcstm", query)
    err_lines = err.strip().splitlines()
    print("exit:   %d" % code)
    print("stdout: " + (out.splitlines()[0] if out else "(empty)"))
    print("stderr, first line: " + err_lines[0])
    print("stderr, last line:  " + err_lines[-1])
    print()

    section("runtime safety covers every region, including candidates that are not chosen")
    query = 'check reach <= 2: active("Root.Run{R: A}");'
    print("query:  " + query)
    code, out, _, payload = bmc("region_safety.fcstm", query)
    print("exit:   %d" % code)
    for line in lines_of(out):
        if line.startswith(("BMC", "  Runtime error", "  Model role", "  Replay", "  1:")) or line.startswith("Trace"):
            print(line)
    code, _, _, payload = bmc("region_safety.fcstm", query, "--json")
    print("json runtime_safety.status: %s" % payload["result"]["runtime_safety"]["status"])
    print("json runtime_safety.error:  %s" % payload["result"]["runtime_safety"]["error"])
    print()

    section("the same query with --no-runtime-safety: the core relation is satisfiable, the simulator raises")
    print("query:  " + query)
    code, out, err, _ = bmc("region_safety.fcstm", query, "--no-runtime-safety")
    err_lines = err.strip().splitlines()
    print("exit:   %d" % code)
    print("stdout: " + (out.splitlines()[0] if out else "(empty)"))
    print("stderr, first line: " + err_lines[0])
    print("stderr, last line:  " + err_lines[-1])
    print()

    section("BmcOptions.max_group_reentries from the Python API")
    from pyfcstm.bmc import BmcBuildError, BmcEngine, BmcOptions, build_bmc_core_formula
    from pyfcstm.model import load_state_machine_from_text

    text = Path("region_reentry.fcstm").read_text(encoding="utf-8").replace("n < 20", "n < 3")
    model = load_state_machine_from_text(text)
    for limit in (3, 4):
        print("max_group_reentries=%d with a group that passes 3 times:" % limit)
        engine = BmcEngine(model, BmcOptions(max_group_reentries=limit))
        try:
            build_bmc_core_formula(engine.prepare("check reach <= 1: terminated();"))
        except BmcBuildError as err:
            print("  BmcBuildError: %s" % err)
        else:
            print("  built")
    for value in (0, -1, True, "16"):
        try:
            BmcOptions(max_group_reentries=value)
        except BmcBuildError as err:
            print("max_group_reentries=%r: BmcBuildError: %s" % (value, err))
finally:
    shutil.rmtree(WORKDIR, ignore_errors=True)
