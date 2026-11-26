"""Run region-aware FBMCQ queries and print deterministic excerpts of the results."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

WORKDIR = Path(".region_bmc_query.tmp")


def bmc(model, query, json_output=False):
    """Run ``pyfcstm bmc`` on a query text and return (exit code, stdout, stderr)."""
    WORKDIR.mkdir(exist_ok=True)
    query_file = WORKDIR / "query.fbmcq"
    query_file.write_text(query + "\n", encoding="utf-8")
    command = [sys.executable, "-m", "pyfcstm", "bmc", "-i", model, "-q", str(query_file)]
    if json_output:
        command += ["--json", "-o", str(WORKDIR / "result.json")]
    done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return done.returncode, done.stdout, done.stderr


def verdict(model, query):
    """Print the first report line and the exit code of one query."""
    print("query:  " + query)
    code, out, err = bmc(model, query)
    line = out.splitlines()[0] if out else err.strip().splitlines()[0]
    print("result: " + line)
    print("exit:   %d" % code)
    print()


def frames(model, query):
    """Print the configuration of every frame of the witness of one query."""
    print("query:  " + query)
    code, _, err = bmc(model, query, json_output=True)
    payload = json.loads((WORKDIR / "result.json").read_text(encoding="utf-8"))
    witness = payload["witness"]
    for frame in witness["frames"]:
        print("  frame %d: %s" % (frame["index"], frame.get("configuration", "(no configuration: %s)" % frame["sentinel"])))
    print("exit:   %d" % code)
    print()


def trace(model, query):
    """Print the human Trace section of one query."""
    print("query:  " + query)
    code, out, _ = bmc(model, query)
    lines = out.splitlines()
    start = lines.index("Trace")
    for line in lines[start:]:
        if not line:
            break
        print("  " + line)
    print("exit:   %d" % code)
    print()


def section(title):
    print("== " + title)
    print()


try:
    section("init state(...): three spellings of a start")
    for text in (
        "Job.Run{Prep: Ready, Work: Busy}",
        "Job.Run.Work.Busy",
        "Job.Run{Work: Busy}",
        "Job.Run",
        "Job.Run{Prep: [done], Work: Busy}",
    ):
        frames("region_job.fcstm", 'init state("%s"); check reach <= 2: true;' % text)

    section("init state(...): invalid starts")
    for text in (
        "Job.Run{Prep: [done], Work: [done]}",
        "Job.Run{Nope: Wait}",
        "Job.Run{Prep: Busy}",
        "Job.Run{Prep: Wait, Prep: Ready}",
        "Job.Run.Prep.Busy",
    ):
        verdict("region_job.fcstm", 'init state("%s"); check reach <= 2: true;' % text)

    section("active(...) as a pattern")
    for text in (
        "Root.Run{Work: Inner{X: x2}}",
        "Root.Run{Work: Inner{X: x2, Y: y1}}",
        "Root.Run{Aux: a1}",
        "Root.Run.Work.Inner.X.x2",
        "Root.Run{Work: [done]}",
        "Root.Run{Work: Inner{X: x2}, Aux: [init]}",
    ):
        verdict("region_nested.fcstm", 'check reach <= 2: active("%s");' % text)
    for text in ("Job.Run{Prep: [done]}", "Job.Run{Prep: [done], Work: Busy}", "Job.Run{Work: [done]}"):
        verdict("region_job.fcstm", 'check reach <= 6: active("%s");' % text)
    verdict("region_job.fcstm", 'init state("Job.Run"); check reach <= 1: active("Job.Run{Prep: [init]}");')
    verdict("region_controller.fcstm", 'check reach <= 3: active("Controller.Running{Motion: On}");')
    verdict("region_controller.fcstm", 'check reach <= 3: active("Controller.Running{Motion: [init]}");')

    section("active(...): invalid patterns")
    for text in (
        "Root.Run{Work: Nope}",
        "Root.Run{Zed: a1}",
        "Root.Run{Aux: a1, Aux: a1}",
        "Root.Run{Work: Inner{X: x2}",
        "Root.Run{Work: x1}",
    ):
        verdict("region_nested.fcstm", 'check reach <= 2: active("%s");' % text)
    verdict("region_plain.fcstm", 'check reach <= 2: active("Root.Idle{A: x}");')
    verdict("region_nested.fcstm", 'check reach <= 2: active("Root.Nope");')

    section("where active(...) in a call filter")
    for text in (
        'called("Root.Run.RunEnter", step=0, where active("Root.Run{A: [init], B: [init]}"))',
        'called("Root.Run.RunEnter", step=1, where active("Root.Run{A: [init], B: [init]}"))',
        'called("Root.Run.RunEnter", step=1, where active("Root.Run{A: [done]}"))',
        'called("Root.Run.RunExit", step=1, where active("Root.Run{A: [done], B: [done]}"))',
        'called("Root.Run.RunExit", where active("Root.Run{A: [init]}"))',
        'called("Root.Run.A.A1.AEnter", step=0, where active("Root.Run{A: A1, B: [init]}"))',
        'called("Root.Run.A.A1.AEnter", step=0, where active("Root.Run{B: B1}"))',
        'called("Root.Run.B.B1.BEnter", step=0, where active("Root.Run{A: A1, B: B1}"))',
        'called("Root.Run.B.B1.BEnter", step=0, where active("Root.Run{B: [init]}"))',
    ):
        verdict("region_calls.fcstm", "check reach <= 3: %s;" % text)

    section("state= and active_leaf= for the group's >> during after")
    for text in (
        'called("Root.Run.GroupTail", state="Root.Run", active_leaf="Root.Run")',
        'called("Root.Run.GroupTail", state="Root.Run.A.A1")',
        'called("Root.Run.GroupTail", active_leaf="Root.Run.B.B1")',
    ):
        verdict("region_calls.fcstm", "check reach <= 3: %s;" % text)
    for text in (
        'call_count("Root.Run.GroupTail", step=*) == 2',
        'call_count("Root.Run.GroupTail", step=*) == 3',
        'call_count(step=*, active_leaf="Root.Run") == 6',
        'call_count(step=*, state="Root.Run") == 6',
        'call_count("Root.Run.A.A1.AWork", step=*, active_leaf="Root.Run.A.A1") >= 1',
    ):
        verdict("region_calls.fcstm", "check reach <= 3: %s;" % text)

    section("case(...) names a local case")
    for label in (
        "Job.Run.Prep.Wait::transition::Job.Run.Prep.Ready::0",
        "Job.Run.Work.Busy::fallback::Job.Run.Work.Busy::0",
        "Job.Run::transition::Job.Next::0",
        "Job.Run::initial::Job.Run.Prep.Wait::0",
        "Job.Run.Prep.Wait::transition::Job.Run.Prep.Nope::0",
    ):
        verdict("region_job.fcstm", 'check cover <= 6: case("%s");' % label)
    trace("region_job.fcstm", 'check cover <= 6: case("Job.Run::transition::Job.Next::0");')
finally:
    shutil.rmtree(WORKDIR, ignore_errors=True)
