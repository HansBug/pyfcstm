#!/usr/bin/env python3
"""Reproduce the measurements behind the BMC scaling explanation page.

This is a maintenance tool.  It is not imported by the package, not run by
pytest and not part of CI.  It builds synthetic state machines, measures the
bounded model checking pipeline on them, and checks the closed forms that the
page ``docs/source/explanations/bmc_scaling`` states against the committed data.

Sub-commands:

``generate``
    Print one synthetic model and its query, so that a measured point can be
    reproduced by hand with ``pyfcstm bmc``.

``measure``
    Measure one configuration in the current process and print one JSON line.
    ``run`` uses it; calling it directly is useful for a single point.

``run``
    Execute a named plan.  Every configuration runs in a fresh Python process,
    one process at a time, after a warm-up compile of a two-state model inside
    that process.  Small points are repeated and the median is recorded.

``import-original``
    Slim the raw records of the earlier, concurrent measurement campaign down
    to the fields the page uses and write ``original_measurements.jsonl``.

``range-table``
    Print, per dimension, the largest measured size that finished within 10, 60
    and 300 seconds, taken from the original measurements.

``compare-retest``
    Print the ratio of every retest point to the original measurement of the
    same configuration.

``fit``
    Recompute the closed forms and the power-law fits from the data files and
    print them, so that a number in the page can be traced to its derivation.

``check-formulas``
    Compare the closed forms printed on the page with a data directory and exit
    non-zero if any closed form leaves its stated tolerance.

Data files are JSON Lines.  Every record carries the repository commit, a short
machine description, the Python and z3 versions, the configuration, the number
of repeats and the statistic (the median) that the page uses.

Example::

    $ python tools/measure_bmc_scaling.py generate flat --N 4 --k 2
    $ python tools/measure_bmc_scaling.py run formula-grid --output grid.jsonl
    $ python tools/measure_bmc_scaling.py check-formulas --data docs/source/explanations/bmc_scaling/data
"""

import argparse
import cProfile
import itertools
import json
import os
import platform
import pstats
import random
import resource
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATA = _REPO_ROOT / "docs" / "source" / "explanations" / "bmc_scaling" / "data"

# --------------------------------------------------------------------------
# Synthetic models
# --------------------------------------------------------------------------


def _back_edges(i, t, rng):
    """Return the extra guarded back edges of state ``i`` for guard values 1..t-1."""
    return [(j, rng.randint(0, i)) for j in range(1, t)]


def flat_model(n, t=2, v=0, write=True, seed=1):
    """Build a region-free chain of ``n`` leaf states with ``t`` transitions each.

    State ``Si`` moves to ``S(i+1)`` when ``d == 0``; the other ``t - 1``
    transitions are guarded back edges.  With ``v > 0`` every chain transition
    except the last increments each of ``v`` variables.

    :param n: Number of leaf states.
    :type n: int
    :param t: Transitions per state.
    :type t: int
    :param v: Number of variables written by every chain transition.
    :type v: int
    :param write: Whether the variables are written, defaults to ``True``.
    :type write: bool
    :param seed: Seed for the back-edge targets.
    :type seed: int
    :return: FCSTM source text.
    :rtype: str
    """
    rng = random.Random(seed)
    out = ["input int d;"]
    out += ["def int x%d = 0;" % idx for idx in range(v)]
    out += ["state Root {", "    [*] -> S0;"]
    out += ["    state S%d;" % idx for idx in range(n)]
    effect = " ".join("x%d = x%d + 1;" % (idx, idx) for idx in range(v))
    for i in range(n):
        suffix = (" effect { %s }" % effect) if (v and write and i < n - 1) else ""
        out.append("    S%d -> S%d : if [d == 0]%s;" % (i, (i + 1) % n, suffix))
        for j, target in _back_edges(i, t, rng):
            out.append("    S%d -> S%d : if [d == %d];" % (i, target, j))
    out.append("}")
    return "\n".join(out)


def regions_model(r, s, t=2, calls=False, seed=1):
    """Build one owner with ``r`` regions of ``s`` leaf states each.

    :param r: Number of regions.
    :type r: int
    :param s: Leaf states per region.
    :type s: int
    :param t: Transitions per state.
    :type t: int
    :param calls: Whether every leaf declares an abstract ``during`` action.
    :type calls: bool
    :param seed: Seed for the back-edge targets.
    :type seed: int
    :return: FCSTM source text.
    :rtype: str
    """
    rng = random.Random(seed)
    out = ["input int d;", "state Root {", "    [*] -> Run;", "    state Run {"]
    for reg in range(r):
        out += ["        region R%d {" % reg, "            [*] -> P0;"]
        for i in range(s):
            if calls:
                out.append(
                    "            state P%d { during abstract W%d_%d; }" % (i, reg, i)
                )
            else:
                out.append("            state P%d;" % i)
        for i in range(s):
            if i < s - 1:
                out.append("            P%d -> P%d : if [d == 0];" % (i, i + 1))
            for j, target in _back_edges(i, t, rng):
                out.append("            P%d -> P%d : if [d == %d];" % (i, target, j))
        out.append("        }")
    out += ["    }", "}"]
    return "\n".join(out)


def nested_regions_model(depth, s=3):
    """Build owners nested ``depth`` levels deep, two regions per level.

    :param depth: Number of nested owners.
    :type depth: int
    :param s: Leaf states per region.
    :type s: int
    :return: FCSTM source text.
    :rtype: str
    """

    def level(index, indent):
        pad = "    " * indent
        lines = []
        for name in ("A", "B"):
            lines += [pad + "region %s%d {" % (name, index), pad + "    [*] -> N0;"]
            for i in range(s):
                if i == 0 and name == "A" and index < depth:
                    lines.append(pad + "    state N0 {")
                    lines += level(index + 1, indent + 2)
                    lines.append(pad + "    }")
                else:
                    lines.append(pad + "    state N%d;" % i)
            for i in range(s - 1):
                lines.append(pad + "    N%d -> N%d : if [d == 0];" % (i, i + 1))
            lines.append(pad + "}")
        return lines

    out = ["input int d;", "state Root {", "    [*] -> Run;", "    state Run {"]
    out += level(1, 2)
    out += ["    }", "}"]
    return "\n".join(out)


def plain_depth_model(depth, width=2):
    """Build ``depth`` nested composite states without regions.

    :param depth: Number of nested composite states.
    :type depth: int
    :param width: Leaf siblings per level.
    :type width: int
    :return: FCSTM source text.
    :rtype: str
    """

    def level(index, indent):
        pad = "    " * indent
        lines = [pad + "[*] -> C%d_0;" % index]
        for w in range(width):
            if w == 0 and index < depth:
                lines.append(pad + "state C%d_0 {" % index)
                lines += level(index + 1, indent + 1)
                lines.append(pad + "}")
            else:
                lines.append(pad + "state C%d_%d;" % (index, w))
        for w in range(width - 1):
            lines.append(
                pad + "C%d_%d -> C%d_%d : if [d == 0];" % (index, w, index, w + 1)
            )
        return lines

    return "\n".join(["input int d;", "state Root {"] + level(1, 1) + ["}"])


def _balanced(terms, operator):
    """Join ``terms`` with ``operator`` as a balanced tree, avoiding deep chains."""
    while len(terms) > 1:
        terms = [
            "(%s %s %s)" % (terms[j], operator, terms[j + 1])
            if j + 1 < len(terms)
            else terms[j]
            for j in range(0, len(terms), 2)
        ]
    return terms[0]


def pigeonhole_model(holes, pigeons):
    """Build ``pigeons`` regions that each pick one of ``holes`` states.

    :param holes: Number of pick-states per region.
    :type holes: int
    :param pigeons: Number of regions.
    :type pigeons: int
    :return: FCSTM source text and the all-different query.
    :rtype: tuple
    """
    out = ["input int d%d;" % i for i in range(pigeons)] + ["state Root {"]
    for i in range(pigeons):
        out += ["    region P%d {" % i, "        [*] -> W;", "        state W;"]
        out += ["        state H%d;" % h for h in range(holes)]
        out += ["        W -> H%d : if [d%d == %d];" % (h, i, h) for h in range(holes)]
        out.append("    }")
    out.append("}")
    terms = [
        _balanced(['active("Root.P%d.H%d")' % (i, h) for h in range(holes)], "||")
        for i in range(pigeons)
    ]
    for h in range(holes):
        for i in range(pigeons):
            for j in range(i + 1, pigeons):
                terms.append(
                    '!(active("Root.P%d.H%d") && active("Root.P%d.H%d"))' % (i, h, j, h)
                )
    return "\n".join(out), "check reach <= 2: %s;" % _balanced(terms, "&&")


def build(cfg):
    """Return the model text and the query of one configuration.

    A configuration is a dict with ``family`` (``flat``, ``regions``, ``calls``,
    ``nested``, ``plain_depth``, ``pigeonhole``), ``params``, the bound ``k`` and
    ``kind`` (``unsat`` asks for something unreachable within ``k`` steps,
    ``sat`` for something reachable).

    :param cfg: Configuration.
    :type cfg: dict
    :return: ``(model_text, query_text)``.
    :rtype: tuple
    """
    family, p, k, kind = cfg["family"], cfg["params"], cfg["k"], cfg["kind"]
    if family == "flat":
        n, v = p["N"], p.get("V", 0)
        text = flat_model(n, p.get("T", 2), v)
        if v:
            goal = max(k - 1, 1) if kind == "sat" else k + 3
            return text, "check reach <= %d: x0 >= %d;" % (k, goal)
        target = max(k - 1, 0) if kind == "sat" else k + 2
        return text, 'check reach <= %d: active("Root.S%d");' % (k, target)
    if family == "regions":
        r, s = p["R"], p["S"]
        text = regions_model(r, s, p.get("T", 2))
        index = min(max(k - 1, 0), s - 1) if kind == "sat" else min(k + 1, s - 1)
        pattern = ", ".join("R%d: P%d" % (reg, index) for reg in range(r))
        return text, 'check reach <= %d: active("Root.Run{%s}");' % (k, pattern)
    if family == "calls":
        r, s = p["R"], p["S"]
        text = regions_model(r, s, p.get("T", 2), calls=True)
        index = max(k - 2, 0) if kind == "sat" else min(k + 1, s - 1)
        where = ""
        if p.get("filter", True) and r > 1:
            where = ', where active("Root.Run{%s}")' % ", ".join(
                "R%d: P%d" % (reg, index) for reg in range(1, r)
            )
        query = 'check reach <= %d: call_count("Root.Run.R0.P%d.W0_%d"%s) >= 1;' % (
            k,
            index,
            index,
            where,
        )
        return text, query
    if family == "nested":
        depth, s = p["D"], p.get("S", 3)
        path = ["Root", "Run"]
        for level in range(1, depth):
            path += ["A%d" % level, "N0"]
        path += ["A%d" % depth, "N%d" % min(max(k - 1, 0), s - 1)]
        return nested_regions_model(depth, s), 'check reach <= %d: active("%s");' % (
            k,
            ".".join(path),
        )
    if family == "plain_depth":
        depth = p["D"]
        path = ".".join("C%d_0" % level for level in range(1, depth + 1))
        return plain_depth_model(depth, p.get("W", 2)), (
            'check reach <= %d: active("Root.%s");' % (k, path)
        )
    if family == "pigeonhole":
        return pigeonhole_model(p["holes"], p["pigeons"])
    raise SystemExit("unknown family %r" % family)


# --------------------------------------------------------------------------
# One measurement in the current process
# --------------------------------------------------------------------------


def dag_nodes(expr):
    """Count the distinct nodes of a z3 expression DAG.

    :param expr: Root expression.
    :type expr: z3.ExprRef
    :return: Number of distinct sub-expressions, counted by z3 expression id.
    :rtype: int
    """
    seen, stack = set(), [expr]
    while stack:
        node = stack.pop()
        ident = node.get_id()
        if ident in seen:
            continue
        seen.add(ident)
        stack.extend(node.children())
    return len(seen)


def _warm_up():
    """Compile and solve a two-state model so lazy start-up costs stay outside timers."""
    import z3  # noqa: F401
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    model = load_state_machine_from_text(flat_model(2))
    formula = compile_bmc_query(model, 'check reach <= 2: active("Root.S1");')
    solve_bmc_property(formula, timeout_ms=10000)


def measure_one(cfg):
    """Measure one configuration in this process.

    ``cfg["mode"]`` is ``time`` (wall-clock compile and solve, z3 statistics of
    every solver check, formula nodes) or ``count`` (``cProfile`` call counts of
    the formula construction, which are deterministic).

    :param cfg: Configuration, see :func:`build`, plus ``mode`` and optional
        ``solve_timeout_s`` (default 250) and ``warm_up`` (default ``True``).
    :type cfg: dict
    :return: Measurement record without environment metadata.
    :rtype: dict
    """
    import warnings

    warnings.filterwarnings("ignore")
    import z3
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    if cfg.get("warm_up", True):
        _warm_up()
    out = {"cfg": cfg}
    text, query = build(cfg)
    started = time.perf_counter()
    model = load_state_machine_from_text(text)
    out["t_load"] = time.perf_counter() - started
    checks = []
    original_check = z3.Solver.check

    def timed_check(self, *args, **kwargs):
        t0 = time.perf_counter()
        status = original_check(self, *args, **kwargs)
        stats = {
            key: val for key, val in self.statistics() if isinstance(val, (int, float))
        }
        checks.append(
            {"status": str(status), "t": time.perf_counter() - t0, "stats": stats}
        )
        return status

    z3.Solver.check = timed_check
    try:
        if cfg["mode"] == "count":
            profile = cProfile.Profile()
            profile.enable()
            formula = compile_bmc_query(model, query)
            profile.disable()
            totals = dict(py_calls=0, z3_calls=0, z3_contexts=0, z3_substitute=0)
            for (filename, _line, name), row in pstats.Stats(profile).stats.items():
                ncalls = row[1]
                totals["py_calls"] += ncalls
                if filename.endswith("z3core.py"):
                    totals["z3_calls"] += ncalls
                    if name.startswith("Z3_mk_context"):
                        totals["z3_contexts"] += ncalls
                    elif name.startswith("Z3_substitute"):
                        totals["z3_substitute"] += ncalls
            out.update(totals)
            out["nodes"] = dag_nodes(formula.solve_formula)
            return out
        started = time.perf_counter()
        formula = compile_bmc_query(model, query)
        out["t_compile"] = time.perf_counter() - started
        out["nodes"] = dag_nodes(formula.solve_formula)
        # Writing a variable makes the compiler issue satisfiability checks on
        # throw-away contexts; count them, and keep only the solve-phase checks.
        out["n_compile_checks"] = len(checks)
        del checks[:]
        core = formula.core
        out["nodes_part"] = {
            "domain": dag_nodes(core.domain_formula),
            "transition": dag_nodes(core.transition_formula),
            "initial": dag_nodes(core.initial_formula),
            "environment": dag_nodes(core.environment_formula),
        }
        started = time.perf_counter()
        result = solve_bmc_property(
            formula, timeout_ms=int(cfg.get("solve_timeout_s", 250)) * 1000
        )
        out["t_solve"] = time.perf_counter() - started
        out["status"] = str(result.status)
        out["checks"] = checks
        out["rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        return out
    finally:
        z3.Solver.check = original_check


# --------------------------------------------------------------------------
# Environment metadata and process-isolated runs
# --------------------------------------------------------------------------


def _machine():
    """Return a short machine description."""
    model = platform.processor() or platform.machine()
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break
    except OSError:
        # OSError: no /proc/cpuinfo on this platform; the platform fallback stays.
        pass
    return "%s, %s" % (model, platform.system())


def _commit():
    """Return the repository commit the measured code comes from."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        # OSError: git is not installed; CalledProcessError: not a git checkout.
        return "unknown"
    return completed.stdout.strip()


def environment():
    """Return the metadata attached to every record.

    :return: Commit, machine, Python and z3 versions.
    :rtype: dict
    """
    import z3

    return {
        "commit": os.environ.get("BMC_SCALING_COMMIT") or _commit(),
        "machine": _machine(),
        "python": platform.python_version(),
        "z3": z3.get_version_string(),
    }


def _run_once(cfg, timeout_s):
    """Run one configuration in a fresh interpreter and return its record."""
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "measure",
        json.dumps(cfg),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(_REPO_ROOT),
            env=dict(os.environ, PYTHONPATH=str(_REPO_ROOT)),
        )
    except subprocess.TimeoutExpired:
        # TimeoutExpired: the whole process exceeded the wall-clock cap.
        return {"cfg": cfg, "error": "timeout", "cap_s": timeout_s}
    lines = [
        line for line in completed.stdout.splitlines() if line.startswith("RESULT ")
    ]
    if not lines:
        return {"cfg": cfg, "error": (completed.stderr or "")[-400:].strip()}
    return json.loads(lines[-1][len("RESULT ") :])


def _total_seconds(record):
    return record.get("t_compile", 0.0) + record.get("t_solve", 0.0)


def run_config(cfg, repeats, timeout_s, repeat_below_s=8.0):
    """Measure one configuration with process isolation and keep the median.

    The first run decides whether to repeat: a point whose compile plus solve
    time is below ``repeat_below_s`` seconds is run ``repeats`` times in total,
    a slower point is measured once.

    :param cfg: Configuration.
    :type cfg: dict
    :param repeats: Total runs for a fast point.
    :type repeats: int
    :param timeout_s: Wall-clock cap of one process.
    :type timeout_s: int
    :param repeat_below_s: Repeat only below this total time.
    :type repeat_below_s: float
    :return: Record of the median run with ``runs`` and ``repeats`` filled in.
    :rtype: dict
    """
    first = _run_once(cfg, timeout_s)
    if "error" in first:
        return first
    runs = [first]
    if cfg["mode"] == "time" and _total_seconds(first) < repeat_below_s:
        runs += [_run_once(cfg, timeout_s) for _ in range(repeats - 1)]
    runs = [run for run in runs if "error" not in run]
    runs.sort(key=_total_seconds)
    median = dict(runs[len(runs) // 2])
    if cfg["mode"] == "time":
        median["runs_total_s"] = [round(_total_seconds(run), 6) for run in runs]
    median["repeats"] = len(runs)
    median["statistic"] = "median" if len(runs) > 1 else "single run"
    return median


# --------------------------------------------------------------------------
# Plans
# --------------------------------------------------------------------------


def _cfg(family, params, k, kind="unsat", mode="time", **extra):
    out = {"family": family, "params": params, "k": k, "kind": kind, "mode": mode}
    out.update(extra)
    return out


def plan_formula_grid():
    """Small grids on which the closed forms are fitted (deterministic counts)."""
    cfgs = []
    for mode in ("time", "count"):
        for n, t, k in itertools.product((20, 40, 80, 160), (1, 2, 4), (2, 4, 8, 16)):
            cfgs.append(_cfg("flat", {"N": n, "T": t}, k, mode=mode))
        for n, v, k in itertools.product((20, 40), (1, 2, 4, 8), (2, 4, 8)):
            cfgs.append(_cfg("flat", {"N": n, "T": 2, "V": v}, k, mode=mode))
        for r, s, k in itertools.product((1, 2, 4, 8), (3, 6, 12, 24), (2, 4, 8)):
            cfgs.append(_cfg("regions", {"R": r, "S": s}, k, mode=mode))
    return cfgs


def plan_solve_law():
    """Medium points on which solve time is compared with solver propagations."""
    cfgs = []
    for kind in ("unsat", "sat"):
        for n, k in itertools.product((200, 400, 800), (8, 16, 32)):
            cfgs.append(_cfg("flat", {"N": n, "T": 2}, k, kind))
        for r, s, k in itertools.product((16, 32, 64), (4, 16), (3, 6)):
            cfgs.append(_cfg("regions", {"R": r, "S": s}, k, kind))
    return cfgs


def plan_unit_cost():
    """Call counts on large points whose unprofiled time the sweeps record."""
    return [
        _cfg("regions", {"R": 96, "S": 4}, 3, mode="count"),
        _cfg("regions", {"R": 256, "S": 4}, 3, mode="count"),
        _cfg("flat", {"N": 1600, "T": 2}, 5, mode="count"),
    ]


def plan_unit_cost_time():
    """Unprofiled times of the points whose call counts ``unit-cost`` records."""
    return [
        _cfg("regions", {"R": 96, "S": 4}, 3),
        _cfg("regions", {"R": 256, "S": 4}, 3),
    ]


def plan_variables():
    """Variable-write cost: contexts, counts and time on flat machines."""
    cfgs = []
    for mode in ("time", "count"):
        for n, v, k in ((100, 0, 5), (100, 4, 5), (100, 16, 5), (100, 64, 5)):
            cfgs.append(_cfg("flat", {"N": n, "T": 2, "V": v}, k, mode=mode))
        for n, v, k in (
            (40, 4, 2),
            (40, 4, 5),
            (40, 4, 10),
            (80, 4, 5),
            (40, 8, 5),
            (40, 16, 5),
        ):
            cfgs.append(_cfg("flat", {"N": n, "T": 2, "V": v}, k, mode=mode))
    cfgs.append(_cfg("flat", {"N": 100, "T": 2, "V": 0}, 5, mode="time"))
    return cfgs


def plan_timing():
    """Sweeps over states, transitions, variables, regions, bound and nesting."""
    cfgs = []
    cfgs += [
        _cfg("flat", {"N": n, "T": 2}, 5)
        for n in (100, 200, 400, 800, 1600, 3200, 6400, 12800)
    ]
    cfgs += [_cfg("flat", {"N": 400, "T": 2}, k) for k in (2, 4, 8, 16, 32, 64, 128)]
    cfgs += [_cfg("flat", {"N": 1600, "T": 2}, 20)]
    cfgs += [
        _cfg("flat", {"N": 100, "T": t}, 5) for t in (1, 2, 4, 8, 16, 32, 64, 128, 256)
    ]
    cfgs += [
        _cfg("flat", {"N": 50, "T": 2, "V": v}, 5)
        for v in (1, 2, 4, 8, 16, 32, 64, 128, 256)
    ]
    cfgs += [
        _cfg("regions", {"R": r, "S": 4}, 3)
        for r in (8, 16, 32, 64, 96, 128, 256, 512, 768, 1024)
    ]
    cfgs += [
        _cfg("regions", {"R": 4, "S": s}, 3)
        for s in (4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048)
    ]
    cfgs += [_cfg("regions", {"R": 4, "S": 40}, k) for k in (2, 4, 8, 16, 32, 64)]
    cfgs += [_cfg("regions", {"R": 4, "S": 200}, k) for k in (16, 32, 48)]
    cfgs += [
        _cfg("regions", {"R": 4, "S": 8, "T": t}, 3)
        for t in (1, 2, 4, 8, 16, 32, 64, 128, 256)
    ]
    cfgs += [
        _cfg("calls", {"R": r, "S": 4, "filter": True}, 3)
        for r in (8, 16, 32, 64, 96, 128, 192)
    ]
    cfgs += [
        _cfg("calls", {"R": r, "S": 4, "filter": False}, 3)
        for r in (8, 16, 32, 64, 128, 256, 512, 1024)
    ]
    cfgs += [_cfg("nested", {"D": d}, 3) for d in (2, 4, 8, 16, 32, 48, 64, 96)]
    cfgs += [_cfg("plain_depth", {"D": d}, 3) for d in (8, 32, 62, 64)]
    return cfgs


def plan_pigeonhole():
    """Mutually exclusive regions: unsatisfiable family and satisfiable control."""
    cfgs = []
    for n in range(3, 13):
        cfgs.append(
            _cfg(
                "pigeonhole",
                {"holes": n, "pigeons": n + 1},
                2,
                "unsat",
                solve_timeout_s=280,
            )
        )
    for n in range(3, 13):
        cfgs.append(
            _cfg(
                "pigeonhole", {"holes": n, "pigeons": n}, 2, "sat", solve_timeout_s=280
            )
        )
    return cfgs


_PLANS = {
    "formula-grid": (plan_formula_grid, 1, 120),
    "solve-law": (plan_solve_law, 1, 320),
    "unit-cost": (plan_unit_cost, 1, 1800),
    "unit-cost-time": (plan_unit_cost_time, 3, 420),
    "variables": (plan_variables, 3, 600),
    "timing": (plan_timing, 3, 420),
    "pigeonhole": (plan_pigeonhole, 1, 420),
}


def command_run(args):
    """Execute a plan serially and append records to the output file."""
    builder, repeats, timeout_s = _PLANS[args.plan]
    cfgs = builder()
    if args.limit:
        cfgs = cfgs[: args.limit]
    meta = environment()
    output = Path(args.output)
    if output.exists() and not args.append:
        output.unlink()
    if args.plan == "formula-grid":
        timeout_s = max(timeout_s, 600)
    print("plan %s: %d configurations" % (args.plan, len(cfgs)), flush=True)
    for index, cfg in enumerate(cfgs, 1):
        started = time.perf_counter()
        record = run_config(cfg, args.repeats or repeats, timeout_s)
        record.update(meta)
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(
            "[%d/%d] %s %s k=%s %s -> %s %.1fs"
            % (
                index,
                len(cfgs),
                cfg["family"],
                json.dumps(cfg["params"], sort_keys=True),
                cfg["k"],
                cfg["mode"],
                record.get("status", record.get("error", "ok"))[:40],
                time.perf_counter() - started,
            ),
            flush=True,
        )
    return 0


def command_measure(args):
    """Measure one configuration in this process and print one RESULT line."""
    print("RESULT " + json.dumps(measure_one(json.loads(args.config))))
    return 0


def command_generate(args):
    """Print one synthetic model and its query."""
    params = {}
    for name in ("N", "T", "V", "R", "S", "D", "holes", "pigeons"):
        value = getattr(args, name)
        if value is not None:
            params[name] = value
    cfg = _cfg(args.family, params, args.k, args.kind)
    text, query = build(cfg)
    print(text)
    print()
    print("// query")
    print(query)
    return 0


# --------------------------------------------------------------------------
# Closed forms, fits and checks
# --------------------------------------------------------------------------


def load_records(directory, name):
    """Read one JSON Lines data file, dropping records with errors.

    :param directory: Data directory.
    :type directory: pathlib.Path
    :param name: File name.
    :type name: str
    :return: Parsed records.
    :rtype: list
    """
    path = Path(directory) / name
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def nodes_flat(n, k):
    """Closed form of the DAG node count: two transitions per state, no variables."""
    return 21 * n * k - 18 * n + 33 * k + 6


def nodes_flat_vars(n, k, v):
    """Closed form of the DAG node count: two transitions per state, ``v`` written variables."""
    return 23 * n * k - 20 * n + 4 * v * k + 35 * k + 9


def bool_vars(n, t, k):
    """Closed form of the number of boolean variables z3 allocates for the first check."""
    return 1 + 8 * k + t * (k - 1) + n * (4 * k - 2) + 3 * n * t * (k - 1)


def _lstsq(rows, getters, value, max_degrees):
    """Fit ``value`` with every monomial whose per-variable degree is bounded.

    :return: ``(exponents, coefficients, maximum absolute residual)``.
    """
    import numpy as np

    exponents = list(itertools.product(*[range(d + 1) for d in max_degrees]))
    matrix = np.array(
        [
            [np.prod([get(r) ** e for get, e in zip(getters, ex)]) for ex in exponents]
            for r in rows
        ],
        dtype=float,
    )
    target = np.array([value(r) for r in rows], dtype=float)
    coefficients, *_ = np.linalg.lstsq(matrix, target, rcond=None)
    return exponents, coefficients, float(np.abs(matrix @ coefficients - target).max())


def _format_poly(names, exponents, coefficients):
    terms = []
    for ex, co in zip(exponents, coefficients):
        if abs(co) < 1e-6:
            continue
        mono = "*".join(
            (name if e == 1 else "%s^%d" % (name, e)) for name, e in zip(names, ex) if e
        )
        number = "%d" % round(co) if abs(co - round(co)) < 1e-6 else "%.4g" % co
        terms.append(number + ("*" + mono if mono else ""))
    return " + ".join(terms)


def _param(record, name, default=None):
    return record["cfg"]["params"].get(name, default)


def _select(rows, family, mode, kind="unsat", where=lambda r: True):
    return [
        r
        for r in rows
        if "error" not in r
        and r["cfg"]["family"] == family
        and r["cfg"]["mode"] == mode
        and r["cfg"]["kind"] == kind
        and where(r)
    ]


def command_fit(args):
    """Print the fitted closed forms and power-law fits from the data files."""
    data = Path(args.data)
    grid = load_records(data, "formula_grid.jsonl")
    timing_grid = _select(grid, "flat", "time", where=lambda r: _param(r, "V") is None)
    names = ["N", "T", "k"]
    getters = [
        lambda r: _param(r, "N"),
        lambda r: _param(r, "T", 2),
        lambda r: r["cfg"]["k"],
    ]
    print("== flat, no written variables (%d grid points)" % len(timing_grid))
    for label, value, degrees in (
        ("DAG nodes", lambda r: r["nodes"], [1, 1, 1]),
        (
            "boolean variables",
            lambda r: r["checks"][0]["stats"].get("mk bool var", 0),
            [1, 1, 2],
        ),
    ):
        ex, co, res = _lstsq(timing_grid, getters, value, degrees)
        print(
            "%s: max|residual|=%.3g\n    %s" % (label, res, _format_poly(names, ex, co))
        )
    counts = _select(grid, "flat", "count", where=lambda r: _param(r, "V") is None)
    ex, co, res = _lstsq(counts, getters, lambda r: r["z3_calls"], [1, 2, 2])
    print(
        "z3 calls: max|residual|=%.3g rel=%.2g\n    %s"
        % (res, res / max(r["z3_calls"] for r in counts), _format_poly(names, ex, co))
    )
    variables = _select(
        grid, "flat", "time", where=lambda r: _param(r, "V") is not None
    )
    ex, co, res = _lstsq(
        variables,
        [lambda r: _param(r, "N"), lambda r: _param(r, "V"), lambda r: r["cfg"]["k"]],
        lambda r: r["nodes"],
        [1, 1, 1],
    )
    print("== flat with V written variables (%d points)" % len(variables))
    print(
        "DAG nodes: max|residual|=%.3g\n    %s"
        % (res, _format_poly(["N", "V", "k"], ex, co))
    )
    region_names = ["R", "S", "k"]
    region_getters = [
        lambda r: _param(r, "R"),
        lambda r: _param(r, "S"),
        lambda r: r["cfg"]["k"],
    ]
    regions = _select(grid, "regions", "time")
    print("== regions (%d points)" % len(regions))
    for label, value, degrees in (
        ("DAG nodes", lambda r: r["nodes"], [1, 1, 1]),
        (
            "boolean variables",
            lambda r: r["checks"][0]["stats"].get("mk bool var", 0),
            [1, 1, 1],
        ),
    ):
        ex, co, res = _lstsq(regions, region_getters, value, degrees)
        print(
            "%s: max|residual|=%.3g\n    %s"
            % (label, res, _format_poly(region_names, ex, co))
        )
    region_counts = _select(grid, "regions", "count")
    ex, co, res = _lstsq(
        region_counts, region_getters, lambda r: r["z3_calls"], [2, 1, 1]
    )
    print(
        "z3 calls: max|residual|=%.3g rel=%.2g\n    %s"
        % (
            res,
            res / max(r["z3_calls"] for r in region_counts),
            _format_poly(region_names, ex, co),
        )
    )
    return 0


def nodes_regions(r, s, k):
    """Fitted node count of the region family, with the coefficients printed on the page."""
    return 23 * r * s * k - 18 * r * s + 22.3 * r * k + 2.9 * r + 46.2 * k + 17.6


def calls_flat(n, k):
    """Fitted z3 call count of the formula construction, two transitions per state."""
    return 1680 * n * k - 1578 * n + 1698 * k + 449


def calls_regions(r, s, k):
    """Fitted z3 call count of the formula construction of the region family."""
    return (
        r * s * (1754 * k - 1418)
        + r * (976 * k + 440)
        + r * r * (151 * k - 96)
        + 2561 * k
        + 439
    )


def _median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def command_check(args):
    """Check the closed forms against the committed data and exit non-zero on a miss.

    A report is printed first so that every number the page quotes can be read
    from this output.
    """
    import math

    data = Path(args.data)
    failures = []
    report = []
    grid = load_records(data, "formula_grid.jsonl")
    timing = load_records(data, "timing.jsonl")
    original = load_records(data, "original_measurements.jsonl")
    large = [r for r in timing + original if "error" not in r and r.get("nodes")]

    def no_vars(r):
        return _param(r, "V") is None

    # Region-free node counts: exact on the grid and on every large point.
    exact = _select(
        grid, "flat", "time", where=lambda r: no_vars(r) and _param(r, "T", 2) == 2
    )
    for r in exact:
        got, want = r["nodes"], nodes_flat(_param(r, "N"), r["cfg"]["k"])
        if got != want:
            failures.append(
                "flat nodes %s k=%s: %d != %d"
                % (r["cfg"]["params"], r["cfg"]["k"], got, want)
            )
    report.append(
        "flat nodes, grid: %d points, all equal to the closed form" % len(exact)
    )
    far = [
        r
        for r in large
        if r["cfg"]["family"] == "flat"
        and no_vars(r)
        and _param(r, "T", 2) == 2
        and r["cfg"]["kind"] == "unsat"
        and r["cfg"]["k"] >= 2
    ]
    bad = [r for r in far if r["nodes"] != nodes_flat(_param(r, "N"), r["cfg"]["k"])]
    for r in bad:
        failures.append(
            "flat out-of-sample %s k=%s" % (r["cfg"]["params"], r["cfg"]["k"])
        )
    report.append(
        "flat nodes, out of sample: %d points up to N=%d, k=%d, %d differ"
        % (
            len(far),
            max(_param(r, "N") for r in far),
            max(r["cfg"]["k"] for r in far),
            len(bad),
        )
    )
    with_vars = _select(grid, "flat", "time", where=lambda r: not no_vars(r))
    for r in with_vars:
        got = r["nodes"]
        want = nodes_flat_vars(_param(r, "N"), r["cfg"]["k"], _param(r, "V"))
        if got != want:
            failures.append(
                "flat+V nodes %s k=%s: %d != %d"
                % (r["cfg"]["params"], r["cfg"]["k"], got, want)
            )
    report.append(
        "flat nodes with written variables, grid: %d points, all equal" % len(with_vars)
    )
    booleans = _select(grid, "flat", "time", where=no_vars)
    for r in booleans:
        got = r["checks"][0]["stats"].get("mk bool var", 0)
        want = bool_vars(_param(r, "N"), _param(r, "T", 2), r["cfg"]["k"])
        if got != want:
            failures.append(
                "bool vars %s k=%s: %d != %d"
                % (r["cfg"]["params"], r["cfg"]["k"], got, want)
            )
    report.append(
        "z3 boolean variables, grid: %d points (T in 1,2,4), all equal" % len(booleans)
    )

    # A power-law fit of the exact linear closed form reproduces a super-linear k.
    import numpy as np

    if far:
        design = np.array(
            [[1, math.log(_param(r, "N")), math.log(r["cfg"]["k"])] for r in far]
        )
        target = np.log([r["nodes"] for r in far])
        coef = np.linalg.lstsq(design, target, rcond=None)[0]
        report.append(
            "power-law fit of the %d out-of-sample flat points: nodes = %.1f * N^%.2f * k^%.2f"
            % (len(far), math.exp(coef[0]), coef[1], coef[2])
        )

    # Region family: fitted coefficients, so a tolerance rather than equality.
    regions = _select(grid, "regions", "time")
    residual = max(
        abs(r["nodes"] - nodes_regions(_param(r, "R"), _param(r, "S"), r["cfg"]["k"]))
        for r in regions
    )
    report.append(
        "region nodes, grid: %d points, max |residual| = %.1f nodes"
        % (len(regions), residual)
    )
    if residual > 12:
        failures.append("region node residual %.1f > 12" % residual)
    far = [
        r
        for r in large
        if r["cfg"]["family"] == "regions"
        and r["cfg"]["kind"] == "unsat"
        and not _param(r, "calls")
        and _param(r, "T", 2) == 2
    ]
    errors = [
        abs(nodes_regions(_param(r, "R"), _param(r, "S"), r["cfg"]["k"]) - r["nodes"])
        / r["nodes"]
        for r in far
    ]
    report.append(
        "region nodes, out of sample: %d points up to R=%d, S=%d, k=%d; median error %.2f%%, max %.2f%%"
        % (
            len(far),
            max(_param(r, "R") for r in far),
            max(_param(r, "S") for r in far),
            max(r["cfg"]["k"] for r in far),
            100 * _median(errors),
            100 * max(errors),
        )
    )
    if max(errors) > 0.015:
        failures.append(
            "region node extrapolation error %.2f%% > 1.5%%" % (100 * max(errors))
        )

    # Variable writes: contexts are exact, W = N - 1 writing transitions.
    contexts = _select(grid, "flat", "count", where=lambda r: not no_vars(r))
    contexts += _select(
        load_records(data, "variables.jsonl"),
        "flat",
        "count",
        where=lambda r: not no_vars(r),
    )
    for r in contexts:
        n, v, k = _param(r, "N"), _param(r, "V"), r["cfg"]["k"]
        want = 2 * (n - 1) * v * (k - 1)
        if r["z3_contexts"] != want:
            failures.append(
                "contexts N=%d V=%d k=%d: %d != %d" % (n, v, k, r["z3_contexts"], want)
            )
    report.append("contexts 2*W*V*(k-1), W=N-1: %d points, all equal" % len(contexts))

    # Call counts: fitted, so relative tolerance.
    flat_counts = _select(
        grid, "flat", "count", where=lambda r: no_vars(r) and _param(r, "T", 2) == 2
    )
    rel = [
        abs(calls_flat(_param(r, "N"), r["cfg"]["k"]) - r["z3_calls"]) / r["z3_calls"]
        for r in flat_counts
    ]
    report.append(
        "flat z3 calls, grid: %d points, max relative error %.2f%%"
        % (len(rel), 100 * max(rel))
    )
    if max(rel) > 0.01:
        failures.append("flat call count error %.2f%% > 1%%" % (100 * max(rel)))
    region_counts = _select(grid, "regions", "count")
    rel = [
        abs(
            calls_regions(_param(r, "R"), _param(r, "S"), r["cfg"]["k"]) - r["z3_calls"]
        )
        / r["z3_calls"]
        for r in region_counts
    ]
    report.append(
        "region z3 calls, grid: %d points, max relative error %.2f%%"
        % (len(rel), 100 * max(rel))
    )
    if max(rel) > 0.01:
        failures.append("region call count error %.2f%% > 1%%" % (100 * max(rel)))
    for r in load_records(data, "unit_cost.jsonl"):
        p = r["cfg"]["params"]
        if r["cfg"]["family"] == "flat":
            want = calls_flat(p["N"], r["cfg"]["k"])
        else:
            want = calls_regions(p["R"], p["S"], r["cfg"]["k"])
        error = (want - r["z3_calls"]) / r["z3_calls"]
        report.append(
            "z3 calls %s k=%d: measured %d, closed form %.0f (%+.1f%%)"
            % (p, r["cfg"]["k"], r["z3_calls"], want, 100 * error)
        )
        if abs(error) > 0.05:
            failures.append(
                "call count extrapolation error %.1f%% at %s" % (100 * error, p)
            )

    # Solve time against propagations.
    xs, ys = [], []
    for r in load_records(data, "solve_law.jsonl"):
        check = r["checks"][0]
        prop = check["stats"].get("propagations", 0)
        if prop > 2e4:
            xs.append(prop)
            ys.append(check["t"])
    lx, ly = np.log(xs), np.log(ys)
    slope, intercept = np.polyfit(lx, ly, 1)
    fitted = slope * lx + intercept
    r2 = 1 - ((ly - fitted) ** 2).sum() / ((ly - ly.mean()) ** 2).sum()
    ns = sorted(y / x * 1e9 for x, y in zip(xs, ys))
    report.append(
        "solve time vs propagations (>2e4): %d checks, exponent %.2f, R^2 %.2f, ns per propagation p10 %.0f median %.0f p90 %.0f"
        % (len(xs), slope, r2, ns[len(ns) // 10], _median(ns), ns[(len(ns) * 9) // 10])
    )

    # Mutually exclusive regions.
    php = [
        r
        for r in load_records(data, "pigeonhole.jsonl")
        if r["cfg"]["kind"] == "unsat" and r["status"] == "unsat"
    ]
    php.sort(key=lambda r: r["cfg"]["params"]["pigeons"])
    ratios = []
    for before, after in zip(php, php[1:]):
        ratios.append(
            (
                after["cfg"]["params"]["pigeons"],
                after["checks"][0]["stats"]["conflicts"]
                / before["checks"][0]["stats"]["conflicts"],
            )
        )
    report.append(
        "pigeonhole conflict ratio per added region: "
        + ", ".join("%d: x%.1f" % x for x in ratios)
    )
    tail = [x for n, x in ratios if n >= 7]
    report.append(
        "pigeonhole conflict ratio from 7 regions on: geometric mean x%.1f"
        % math.exp(sum(math.log(x) for x in tail) / len(tail))
    )

    # Cost of one throw-away context, from the variable-write time records.
    variables = [r for r in load_records(data, "variables.jsonl") if "error" not in r]
    counts = {
        (_param(r, "N"), _param(r, "V"), r["cfg"]["k"]): r["z3_contexts"]
        for r in variables
        if r["cfg"]["mode"] == "count"
    }
    base = {
        (_param(r, "N"), r["cfg"]["k"]): r["t_compile"]
        for r in variables
        if r["cfg"]["mode"] == "time" and _param(r, "V") == 0
    }
    for r in variables:
        if r["cfg"]["mode"] != "time" or not _param(r, "V"):
            continue
        key = (_param(r, "N"), _param(r, "V"), r["cfg"]["k"])
        if key in counts and (key[0], key[2]) in base:
            extra = r["t_compile"] - base[(key[0], key[2])]
            report.append(
                "context cost N=%d V=%d k=%d: %d contexts, build %.1f s (%.1f s without variables), %.2f ms per context"
                % (
                    key
                    + (
                        counts[key],
                        r["t_compile"],
                        base[(key[0], key[2])],
                        1000 * extra / counts[key],
                    )
                )
            )
    # Node count against T: not linear, the doubling factor rises with T.
    for family, fixed, k in (("flat", {"N": 100}, 5), ("regions", {"R": 4, "S": 8}, 3)):
        sweep = {}
        for r in original:
            cfg, params = r["cfg"], r["cfg"]["params"]
            if (
                cfg["family"] == family
                and cfg["kind"] == "unsat"
                and cfg["k"] == k
                and r["status"] == "unsat"
                and r.get("nodes")
                and not params.get("calls")
                and "V" not in params
                and all(params.get(n) == v for n, v in fixed.items())
            ):
                sweep[params.get("T", 2)] = r["nodes"]
        ts = sorted(sweep)
        report.append(
            "nodes against T, %s %s k=%d: " % (family, fixed, k)
            + ", ".join(
                "T=%d: %d%s"
                % (
                    t,
                    sweep[t],
                    "" if i == 0 else " (x%.2f)" % (sweep[t] / sweep[ts[i - 1]]),
                )
                for i, t in enumerate(ts)
            )
        )

    # Seconds per counted z3 call: counts from unit_cost.jsonl, unprofiled time
    # from unit_cost_time.jsonl (regions) and timing.jsonl (ring).
    seconds = {}
    for r in load_records(data, "unit_cost_time.jsonl") + timing:
        if "error" not in r and r.get("t_compile"):
            seconds[_config_key(r)] = r["t_compile"]
    for r in load_records(data, "unit_cost.jsonl"):
        key = _config_key(r)
        if key in seconds:
            report.append(
                "build seconds per z3 call %s k=%d: %.2f s for %d calls, %.2f microseconds per call"
                % (
                    r["cfg"]["params"],
                    r["cfg"]["k"],
                    seconds[key],
                    r["z3_calls"],
                    1e6 * seconds[key] / r["z3_calls"],
                )
            )
    for family in ("flat", "regions"):
        shares = [
            r["t_compile"] / (r["t_compile"] + r["t_solve"])
            for r in original
            if r["cfg"]["family"] == family
            and r["status"] in ("sat", "unsat")
            and r["t_compile"] + r["t_solve"] > 1.0
        ]
        report.append(
            "share of build time, original points above 1 s, %s: %d points, median %.0f%%, range %.0f%% to %.0f%%"
            % (
                family,
                len(shares),
                100 * _median(shares),
                100 * min(shares),
                100 * max(shares),
            )
        )
    for r in original:
        params = r["cfg"]["params"]
        if (
            r["cfg"]["family"] == "flat"
            and params.get("N") == 100
            and params.get("T", 2) == 2
            and r["cfg"]["k"] == 5
            and params.get("V") in (4, 16, 64)
            and params.get("eff") is not False
            and r["cfg"]["kind"] == "unsat"
            and r["status"] == "unsat"
        ):
            ctxs = 2 * 99 * params["V"] * 4
            report.append(
                "context cost, original campaign, N=100 V=%d k=5: build %.1f s, %d contexts, %.2f ms per context"
                % (params["V"], r["t_compile"], ctxs, 1000 * r["t_compile"] / ctxs)
            )
    print("\n".join(report))
    if failures:
        print("closed forms disagree with the data:")
        print("\n".join(failures))
        return 1
    print("closed forms agree with the data in %s" % data)
    return 0


# --------------------------------------------------------------------------
# Original measurement campaign: import, range table, retest comparison
# --------------------------------------------------------------------------

ORIGINAL_COMMIT = "560b7dc4"
ORIGINAL_NOTE = "56 concurrent processes, Python 3.11.15, z3 4.15.4"
ORIGINAL_MACHINE = "Intel Xeon Platinum 8581C, Linux"


def command_import_original(args):
    """Write the slim original measurement file from the raw ``results*.jsonl``."""
    out = []
    for name in ("results1.jsonl", "results2.jsonl", "results3.jsonl"):
        with open(Path(args.source) / name, encoding="utf-8") as handle:
            for line in handle:
                raw = json.loads(line)
                if raw.get("status") not in ("sat", "unsat", "timeout"):
                    continue
                cfg = dict(raw["cfg"])
                cfg.pop("solve_timeout_s", None)
                cfg["mode"] = "time"
                rec = {"cfg": cfg, "status": raw["status"], "reps": raw.get("reps")}
                for key in ("t_compile", "t_solve", "nodes", "rss_mb"):
                    if raw.get(key) is not None:
                        rec[key] = raw[key]
                rec.update(
                    commit=ORIGINAL_COMMIT,
                    machine=ORIGINAL_MACHINE,
                    conditions=ORIGINAL_NOTE,
                    source="original",
                )
                out.append(rec)
    with open(args.output, "w", encoding="utf-8") as handle:
        for rec in out:
            handle.write(json.dumps(rec, sort_keys=True) + "\n")
    print("wrote %d records to %s" % (len(out), args.output))
    return 0


def _total(rec):
    return rec.get("t_compile", 0.0) + rec.get("t_solve", 0.0)


# (label, family, dimension, fixed parameters, fixed k or None, extra filter)
_RANGE_ROWS = (
    ("flat: leaf states N (T=2, k=5)", "flat", "N", {"T": 2}, 5, None),
    ("flat: bound k (N=400, T=2)", "flat", "k", {"N": 400, "T": 2}, None, None),
    ("flat: transitions per state T (N=100, k=5)", "flat", "T", {"N": 100}, 5, None),
    ("flat: written variables V (N=50, k=5)", "flat", "V", {"N": 50}, 5, "writes"),
    ("regions: R (S=4, k=3)", "regions", "R", {"S": 4}, 3, "plain"),
    ("regions: S (R=4, k=3)", "regions", "S", {"R": 4}, 3, "plain"),
    ("regions: bound k (R=4, S=40)", "regions", "k", {"R": 4, "S": 40}, None, "plain"),
    (
        "regions: bound k (R=4, S=200)",
        "regions",
        "k",
        {"R": 4, "S": 200},
        None,
        "plain",
    ),
    ("regions: T (R=4, S=8, k=3)", "regions", "T", {"R": 4, "S": 8}, 3, "plain"),
    ("calls with where filter: R (S=4, k=3)", "regions", "R", {"S": 4}, 3, "filter"),
    ("calls without where: R (S=4, k=3)", "regions", "R", {"S": 4}, 3, "nofilter"),
)


def _row_points(records, family, dim, fixed, k, extra):
    """Group the unsatisfiable records of one range-table row by the swept value."""
    points = {}
    for rec in records:
        cfg, params = rec["cfg"], rec["cfg"]["params"]
        if cfg["family"] != family or cfg["kind"] != "unsat":
            continue
        if dim != "k" and k is not None and cfg["k"] != k:
            continue
        if any(
            params.get(name, 2 if name == "T" else None) != val
            for name, val in fixed.items()
        ):
            continue
        is_calls = bool(params.get("calls"))
        if extra == "plain" and (is_calls or dim != "T" and "T" in params):
            continue
        if extra == "writes" and (not params.get("V") or params.get("eff") is False):
            continue
        if extra == "filter" and (not is_calls or params.get("filter") == "none"):
            continue
        if extra == "nofilter" and (not is_calls or params.get("filter") != "none"):
            continue
        if family == "flat" and dim != "V" and params.get("V"):
            continue
        value = cfg["k"] if dim == "k" else params.get(dim, 2 if dim == "T" else None)
        points.setdefault(value, []).append(rec)
    return points


def range_rows(records):
    """Compute the range table: one dict per dimension.

    :param records: Original measurement records.
    :type records: list
    :return: Rows with the best finished size per budget and the first failure.
    :rtype: list
    """
    rows = []
    for label, family, dim, fixed, k, extra in _RANGE_ROWS:
        points = _row_points(records, family, dim, fixed, k, extra)
        finished, failed = {}, []
        for value, recs in points.items():
            done = [r for r in recs if r["status"] == "unsat"]
            if done:
                finished[value] = statistics_median([_total(r) for r in done])
            elif any(r["status"] == "timeout" for r in recs):
                failed.append(value)
        row = {
            "label": label,
            "budgets": {},
            "first_unfinished": min(failed) if failed else None,
        }
        for budget in (10, 60, 300):
            fits = [v for v, t in finished.items() if t <= budget]
            if fits:
                best = max(fits)
                row["budgets"][budget] = (best, finished[best])
        rows.append(row)
    return rows


def statistics_median(values):
    """Return the median of a non-empty list."""
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def command_range_table(args):
    """Print the practical-range table from the original measurements."""
    records = load_records(args.data, "original_measurements.jsonl")
    print("largest measured size that finished within the budget (total seconds)")
    print(
        "%-44s %-14s %-14s %-15s %s"
        % ("dimension", "10 s", "60 s", "300 s", "first timeout")
    )
    for row in range_rows(records):
        cells = []
        for budget in (10, 60, 300):
            hit = row["budgets"].get(budget)
            cells.append("%s (%.0f s)" % hit if hit else "-")
        stop = row["first_unfinished"]
        print(
            "%-44s %-14s %-14s %-15s %s"
            % ((row["label"],) + tuple(cells) + (stop if stop is not None else "-",))
        )
    return 0


def _config_key(rec):
    cfg = rec["cfg"]
    return (
        cfg["family"],
        json.dumps(cfg["params"], sort_keys=True),
        cfg["k"],
        cfg["kind"],
    )


def command_compare_retest(args):
    """Print retest/original time ratios for configurations measured both times."""
    original = {}
    for rec in load_records(args.data, "original_measurements.jsonl"):
        if rec["status"] == "unsat":
            original.setdefault(_config_key(rec), []).append(_total(rec))
    print("%-34s %9s %9s %6s" % ("configuration", "original", "retest", "ratio"))
    for rec in load_records(args.data, "timing.jsonl"):
        if "error" in rec or rec.get("status") != "unsat":
            continue
        key = _config_key(rec)
        if key not in original:
            continue
        before, after = statistics_median(original[key]), _total(rec)
        print(
            "%-34s %8.1fs %8.1fs %6.2f"
            % (
                "%s k=%d"
                % (json.dumps(rec["cfg"]["params"], sort_keys=True), rec["cfg"]["k"]),
                before,
                after,
                after / before,
            )
        )
    return 0


def _build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="print a synthetic model and query")
    gen.add_argument(
        "family",
        choices=("flat", "regions", "calls", "nested", "plain_depth", "pigeonhole"),
    )
    for name in ("N", "T", "V", "R", "S", "D", "holes", "pigeons"):
        gen.add_argument("--" + name, type=int)
    gen.add_argument("--k", type=int, default=3)
    gen.add_argument("--kind", choices=("sat", "unsat"), default="unsat")
    gen.set_defaults(handler=command_generate)
    one = sub.add_parser(
        "measure", help="measure one JSON configuration in this process"
    )
    one.add_argument("config")
    one.set_defaults(handler=command_measure)
    run = sub.add_parser(
        "run", help="execute a named plan, one fresh process per point"
    )
    run.add_argument("plan", choices=sorted(_PLANS))
    run.add_argument("--output", required=True)
    run.add_argument("--append", action="store_true")
    run.add_argument(
        "--repeats", type=int, default=0, help="runs of a fast point (default per plan)"
    )
    run.add_argument(
        "--limit", type=int, default=0, help="run only the first N configurations"
    )
    run.set_defaults(handler=command_run)
    imp = sub.add_parser(
        "import-original", help="slim the raw original campaign records"
    )
    imp.add_argument("--source", required=True, help="directory with results1-3.jsonl")
    imp.add_argument("--output", required=True)
    imp.set_defaults(handler=command_import_original)
    table = sub.add_parser("range-table", help="print the practical-range table")
    table.add_argument("--data", default=str(_DEFAULT_DATA))
    table.set_defaults(handler=command_range_table)
    cmp_ = sub.add_parser("compare-retest", help="print retest/original ratios")
    cmp_.add_argument("--data", default=str(_DEFAULT_DATA))
    cmp_.set_defaults(handler=command_compare_retest)
    fit = sub.add_parser("fit", help="recompute closed forms from the data files")
    fit.add_argument("--data", default=str(_DEFAULT_DATA))
    fit.set_defaults(handler=command_fit)
    check = sub.add_parser(
        "check-formulas", help="compare closed forms with the data files"
    )
    check.add_argument("--data", default=str(_DEFAULT_DATA))
    check.set_defaults(handler=command_check)
    return parser


def main(argv=None):
    """Entry point.

    :param argv: Arguments, defaults to ``sys.argv[1:]``.
    :type argv: list, optional
    :return: Process exit status.
    :rtype: int
    """
    args = _build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
