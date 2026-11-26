#!/usr/bin/env python3
"""Reproduce the measurements behind the BMC scaling explanation and check its closed forms.

This is a maintenance tool for ``docs/source/explanations/bmc_scaling``.  It is
not imported by the package, not run by pytest and not part of CI.  It builds
synthetic state machines, measures the bounded model checking pipeline on them
one fresh process at a time, writes the records as JSON Lines, and compares the
closed forms that the page states with those records.  Every number on the page
can be traced to a record produced here, and the sub-command ``check-formulas``
fails when a closed form leaves its stated tolerance.

The measured quantities are the number of distinct z3 nodes of the compiled
formula, the number of z3 C-interface calls and throw-away z3 contexts used to
build it, the wall-clock build and solve times, and the z3 statistics of the
solver checks (propagations and conflicts).  Timings are single runs on a
shared machine unless a record says otherwise; counts are deterministic.

The module contains:

* model generators :func:`flat_model`, :func:`regions_model`,
  :func:`nested_regions_model`, :func:`plain_depth_model` and
  :func:`pigeonhole_model`, selected by :func:`build`
* measurement: :func:`measure_one` (one process), :func:`run_config` (process
  isolation and the median) and the plans ``plan_*`` run by :func:`command_run`
* closed forms :func:`nodes_flat`, :func:`nodes_flat_vars`, :func:`bool_vars`,
  :func:`nodes_regions`, :func:`calls_flat` and :func:`calls_regions`
* reports: :func:`command_fit`, :func:`command_check`,
  :func:`command_range_table` and :func:`command_compare_retest`
* :func:`main`, the command-line entry point with the sub-commands ``generate``,
  ``measure``, ``run``, ``import-original``, ``range-table``,
  ``compare-retest``, ``fit`` and ``check-formulas``

.. note::
   The root ``--help`` text is kept in ``_HELP_DESCRIPTION`` so that it does not
   change when this docstring does.

Example::

    $ python tools/measure_bmc_scaling.py generate flat --N 8 --k 2
    $ python tools/measure_bmc_scaling.py run formula-grid --output grid.jsonl --limit 4
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

# Root ``--help`` text, frozen so that edits of the module docstring do not alter it.
_HELP_DESCRIPTION = """Reproduce the measurements behind the BMC scaling explanation page.

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

# --------------------------------------------------------------------------
# Synthetic models
# --------------------------------------------------------------------------


def _back_edges(i, t, rng):
    """Return the guarded back edges of one state.

    The ring models give every state one forward edge on ``d == 0``; this helper
    draws the remaining ``t - 1`` edges, guard value ``j`` for ``j = 1 .. t - 1``,
    towards a random earlier state (or the state itself).  The random generator is
    passed in so that one seed fixes the whole model.

    :param i: Index of the state; targets are drawn from ``0 .. i`` inclusive.
    :type i: int
    :param t: Transitions per state; ``t - 1`` back edges are returned.
    :type t: int
    :param rng: Seeded generator shared by the whole model.
    :type rng: random.Random
    :return: ``(guard_value, target_index)`` pairs in guard order.
    :rtype: list

    Example::

        >>> _back_edges(3, 3, random.Random(1))
        [(1, 1), (2, 0)]
    """
    return [(j, rng.randint(0, i)) for j in range(1, t)]


def flat_model(n, t=2, v=0, write=True, seed=1):
    """Build a region-free ring of ``n`` leaf states with ``t`` transitions each.

    State ``Si`` moves to ``S(i+1)`` (and the last one back to ``S0``) when
    ``d == 0``; the other ``t - 1`` transitions of each state are guarded back
    edges from :func:`_back_edges`.  With ``v > 0`` every ring transition except the
    one leaving the last state increments each of ``v`` variables, so the number of
    transitions that carry an assignment is ``n - 1``.  This is the family behind
    the node-count, call-count and variable-write closed forms of the page.

    :param n: Number of leaf states.
    :type n: int
    :param t: Transitions per state, defaults to ``2``.
    :type t: int, optional
    :param v: Variables written by every writing transition, defaults to ``0``.
    :type v: int, optional
    :param write: Whether the ring transitions carry the assignments; ``False``
        declares the variables but never writes them, defaults to ``True``.
    :type write: bool, optional
    :param seed: Seed of the back-edge targets, defaults to ``1``.
    :type seed: int, optional
    :return: FCSTM source text.
    :rtype: str

    Example::

        >>> print(flat_model(3))
        input int d;
        state Root {
            [*] -> S0;
            state S0;
            state S1;
            state S2;
            S0 -> S1 : if [d == 0];
            S0 -> S0 : if [d == 1];
            S1 -> S2 : if [d == 0];
            S1 -> S0 : if [d == 1];
            S2 -> S0 : if [d == 0];
            S2 -> S1 : if [d == 1];
        }
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
    """Build one owner ``Run`` with ``r`` regions of ``s`` leaf states each.

    Inside every region the states form the same chain-with-back-edges as
    :func:`flat_model`, entered at ``P0``.  All regions read the same input ``d``, so
    they are independent of each other, which is why this family measures the cost
    of the region count without mutual constraints.  Back edges are drawn from one
    generator across all regions, so the regions differ slightly.

    :param r: Number of regions.
    :type r: int
    :param s: Leaf states per region.
    :type s: int
    :param t: Transitions per state, defaults to ``2``.
    :type t: int, optional
    :param calls: Whether every leaf declares ``during abstract W<region>_<state>``,
        which the call-count queries need, defaults to ``False``.
    :type calls: bool, optional
    :param seed: Seed of the back-edge targets, defaults to ``1``.
    :type seed: int, optional
    :return: FCSTM source text.
    :rtype: str

    Example::

        >>> print(regions_model(1, 2))
        input int d;
        state Root {
            [*] -> Run;
            state Run {
                region R0 {
                    [*] -> P0;
                    state P0;
                    state P1;
                    P0 -> P1 : if [d == 0];
                    P0 -> P0 : if [d == 1];
                    P1 -> P0 : if [d == 1];
                }
            }
        }
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
    """Build owners nested ``depth`` levels deep, with two regions per level.

    Level ``l`` has regions ``A<l>`` and ``B<l>`` of ``s`` states each; the first
    state of ``A<l>`` is itself the owner of level ``l + 1``.  The family probes the
    fixed limit on how deep groups may nest, not the cost of any one level.

    :param depth: Number of nested owners.
    :type depth: int
    :param s: Leaf states per region, defaults to ``3``.
    :type s: int, optional
    :return: FCSTM source text.
    :rtype: str

    Example::

        >>> print(nested_regions_model(1, 2))
        input int d;
        state Root {
            [*] -> Run;
            state Run {
                region A1 {
                    [*] -> N0;
                    state N0;
                    state N1;
                    N0 -> N1 : if [d == 0];
                }
                region B1 {
                    [*] -> N0;
                    state N0;
                    state N1;
                    N0 -> N1 : if [d == 0];
                }
            }
        }
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

    Every level has ``width`` sibling states; the first one is the composite that
    holds the next level.  Used to compare the nesting limit of region-free
    hierarchy with that of nested regions.

    :param depth: Number of nested composite states.
    :type depth: int
    :param width: Sibling states per level, defaults to ``2``.
    :type width: int, optional
    :return: FCSTM source text.
    :rtype: str

    Example::

        >>> print(plain_depth_model(2, 2))
        input int d;
        state Root {
            [*] -> C1_0;
            state C1_0 {
                [*] -> C2_0;
                state C2_0;
                state C2_1;
                C2_0 -> C2_1 : if [d == 0];
            }
            state C1_1;
            C1_0 -> C1_1 : if [d == 0];
        }
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
    """Join ``terms`` with ``operator`` as a balanced binary tree.

    A left-leaning chain of hundreds of ``&&`` would make the query parser recurse
    deeply; pairing neighbours level by level keeps the depth logarithmic.  An odd
    element is carried up unchanged.

    :param terms: Non-empty list of query sub-expressions.
    :type terms: list
    :param operator: Binary query operator such as ``&&`` or ``||``.
    :type operator: str
    :return: One parenthesised expression.
    :rtype: str

    Example::

        >>> _balanced(['a', 'b', 'c'], '&&')
        '((a && b) && c)'
    """
    while len(terms) > 1:
        terms = [
            "(%s %s %s)" % (terms[j], operator, terms[j + 1])
            if j + 1 < len(terms)
            else terms[j]
            for j in range(0, len(terms), 2)
        ]
    return terms[0]


def pigeonhole_model(holes, pigeons):
    """Build ``pigeons`` regions that each move into one of ``holes`` states.

    Region ``P<i>`` leaves its waiting state ``W`` into ``H<h>`` when its own input
    ``d<i>`` equals ``h``.  The query asks that every region ends in some ``H``
    state and that no two regions end in the same ``H`` index.  With more regions
    than holes this is unsatisfiable and the solver must prove it; with as many
    regions as holes it is satisfiable.  The conjunction is built with
    :func:`_balanced` to keep the query shallow.

    :param holes: Number of pick-states per region.
    :type holes: int
    :param pigeons: Number of regions.
    :type pigeons: int
    :return: FCSTM source text and the all-different query text.
    :rtype: tuple

    Example::

        >>> text, query = pigeonhole_model(1, 2)
        >>> print(text.splitlines()[0])
        input int d0;
        >>> print(query)
        check reach <= 2: ((active("Root.P0.H0") && active("Root.P1.H0")) && !(active("Root.P0.H0") && active("Root.P1.H0")));
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
    """Return the model text and the query text of one configuration.

    ``cfg["family"]`` selects the generator: ``flat``, ``regions``, ``calls``
    (regions with abstract actions and a ``call_count`` query), ``nested``,
    ``plain_depth`` or ``pigeonhole``.  ``cfg["kind"]`` chooses the target of the
    ``check reach`` query: ``unsat`` asks for something that cannot happen within
    ``k`` steps, so the solver must prove it unreachable, and ``sat`` asks for
    something reachable within ``k`` steps.  The ``flat`` unsat target is state
    ``S<k+2>``, so the ring needs ``N >= k + 3`` states for the query to bind.

    :param cfg: Configuration with ``family``, ``params``, ``k`` and ``kind``.
    :type cfg: dict
    :return: ``(model_text, query_text)``.
    :rtype: tuple
    :raises SystemExit: If ``cfg["family"]`` is not one of the families above.

    Example::

        >>> build({"family": "flat", "params": {"N": 6}, "k": 2, "kind": "unsat"})[1]
        'check reach <= 2: active("Root.S4");'
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

    Nodes are identified by z3's expression id, so a sub-expression shared in many
    places is counted once; this is the size z3 actually stores, and the quantity
    the closed forms of the page describe.  The walk is iterative, because the
    formulas are far deeper than Python's recursion limit.

    :param expr: Root expression.
    :type expr: z3.ExprRef
    :return: Number of distinct sub-expressions, the root included.
    :rtype: int

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> dag_nodes(x + x > 0)
        4
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
    """Compile and solve a two-state model so that lazy start-up costs stay outside the timers.

    The first compile in a process pays for importing and initialising parts of z3
    and pyfcstm.  Running this once, on a model with no variables, moves that cost
    out of the measured interval without touching the variable-write path that the
    page measures separately.

    :return: ``None``.
    :rtype: None
    """
    import z3  # noqa: F401
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    model = load_state_machine_from_text(flat_model(2))
    formula = compile_bmc_query(model, 'check reach <= 2: active("Root.S1");')
    solve_bmc_property(formula, timeout_ms=10000)


def measure_one(cfg):
    """Measure one configuration in this process.

    ``cfg["mode"]`` is ``time`` or ``count``.  ``time`` records wall-clock load,
    compile and solve times, the formula size (total and by part), the z3 statistics
    of every solver check made during the solve, the number of satisfiability checks
    issued while compiling, and the peak resident size.  ``count`` runs the compile
    under ``cProfile`` and records deterministic call counts: all Python calls, z3
    C-interface calls, ``Z3_mk_context`` calls (the throw-away contexts of variable
    writes) and ``Z3_substitute`` calls.  ``z3.Solver.check`` is wrapped for the
    duration of the call and restored afterwards, even on error.

    :param cfg: Configuration, see :func:`build`, plus ``mode``; optional
        ``solve_timeout_s`` (default ``250``) and ``warm_up`` (default ``True``).
    :type cfg: dict
    :return: Measurement record without environment metadata.
    :rtype: dict
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If the query does not bind, for
        example because the ring has fewer than ``k + 3`` states.

    Example::

        $ python tools/measure_bmc_scaling.py measure '{"family": "flat", "params": {"N": 20}, "k": 4, "kind": "unsat", "mode": "count"}'
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
    """Return a short machine description such as ``"<cpu model>, Linux"``.

    The CPU model comes from ``/proc/cpuinfo`` when it exists and falls back to the
    platform string otherwise, so the record is informative on Linux and still
    defined elsewhere.

    :return: CPU model and operating-system name.
    :rtype: str
    """
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
    """Return the short commit of the checkout the measured code comes from.

    :return: Eight-character commit, or ``"unknown"`` when git is missing or the
        directory is not a checkout.
    :rtype: str
    """
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
    """Return the metadata attached to every record this tool writes.

    ``BMC_SCALING_COMMIT`` overrides the commit, which is needed when the tool runs
    from a copy that is not a git checkout.

    :return: Mapping with ``commit``, ``machine``, ``python`` and ``z3``.
    :rtype: dict

    Example::

        >>> sorted(environment())
        ['commit', 'machine', 'python', 'z3']
    """
    import z3

    return {
        "commit": os.environ.get("BMC_SCALING_COMMIT") or _commit(),
        "machine": _machine(),
        "python": platform.python_version(),
        "z3": z3.get_version_string(),
    }


def _run_once(cfg, timeout_s):
    """Run one configuration in a fresh interpreter and return its record.

    The child is ``python <this file> measure <json>`` with ``PYTHONPATH`` set to
    the repository, so every point starts cold and cannot warm the next one.  A
    child that exceeds ``timeout_s`` or prints no ``RESULT`` line becomes an error
    record instead of an exception, so one bad point does not end a plan.

    :param cfg: Configuration passed to :func:`measure_one`.
    :type cfg: dict
    :param timeout_s: Wall-clock cap of the whole process in seconds.
    :type timeout_s: int
    :return: The measured record, or ``{"cfg", "error"}`` (with ``cap_s`` for a
        timeout).
    :rtype: dict
    """
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
    """Return compile plus solve seconds of a record, counting a missing phase as zero.

    :param record: Measurement record, possibly without ``t_solve``.
    :type record: dict
    :return: Total seconds.
    :rtype: float
    """
    return record.get("t_compile", 0.0) + record.get("t_solve", 0.0)


def run_config(cfg, repeats, timeout_s, repeat_below_s=8.0):
    """Measure one configuration with process isolation and keep the median run.

    The first run decides whether to repeat: a ``time`` point whose compile plus
    solve time is below ``repeat_below_s`` seconds is run ``repeats`` times in
    total, a slower point once, and ``count`` points once, because call counts are
    deterministic.  Runs that failed are dropped from the median; if the first run
    fails, its error record is returned unchanged.

    :param cfg: Configuration, see :func:`measure_one`.
    :type cfg: dict
    :param repeats: Total runs for a fast point.
    :type repeats: int
    :param timeout_s: Wall-clock cap of one process in seconds.
    :type timeout_s: int
    :param repeat_below_s: Repeat only below this total time, defaults to ``8.0``.
    :type repeat_below_s: float, optional
    :return: Record of the median run, with ``runs_total_s`` (``time`` mode),
        ``repeats`` and ``statistic`` (``median`` or ``single run``) filled in.
    :rtype: dict

    Example::

        $ python tools/measure_bmc_scaling.py run formula-grid --output grid.jsonl --limit 1
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
    """Build a configuration dict, the shape :func:`build` and :func:`measure_one` take.

    :param family: Model family name.
    :type family: str
    :param params: Family parameters such as ``{"N": 100}``.
    :type params: dict
    :param k: Step bound of the query.
    :type k: int
    :param kind: ``unsat`` or ``sat``, defaults to ``"unsat"``.
    :type kind: str, optional
    :param mode: ``time`` or ``count``, defaults to ``"time"``.
    :type mode: str, optional
    :param extra: Further keys copied into the dict, such as ``solve_timeout_s``.
    :return: Configuration dict.
    :rtype: dict

    Example::

        >>> _cfg('flat', {'N': 4}, 2)
        {'family': 'flat', 'params': {'N': 4}, 'k': 2, 'kind': 'unsat', 'mode': 'time'}
    """
    out = {"family": family, "params": params, "k": k, "kind": kind, "mode": mode}
    out.update(extra)
    return out


def plan_formula_grid():
    """Return the small grids on which the closed forms are fitted.

    Each point is listed twice, once in ``time`` mode (formula size, solver
    statistics) and once in ``count`` mode (deterministic call counts): ring sizes
    20 to 160 with 1, 2 and 4 transitions per state, rings that write 1 to 8
    variables, and 1 to 8 regions of 3 to 24 states.  Counts are deterministic, so
    the plan is run once per point.

    :return: Configurations in execution order.
    :rtype: list

    Example::

        >>> len(plan_formula_grid())
        240
    """
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
    """Return the medium points that relate solve time to solver propagations.

    Rings of 200 to 800 states at bounds 8 to 32 and 16 to 64 regions of 4 or 16
    states at bounds 3 and 6, each for an unsatisfiable and a satisfiable query.
    The main solver check of each point supplies the propagation count.

    :return: Configurations in execution order.
    :rtype: list

    Example::

        >>> len(plan_solve_law())
        42
    """
    cfgs = []
    for kind in ("unsat", "sat"):
        for n, k in itertools.product((200, 400, 800), (8, 16, 32)):
            cfgs.append(_cfg("flat", {"N": n, "T": 2}, k, kind))
        for r, s, k in itertools.product((16, 32, 64), (4, 16), (3, 6)):
            cfgs.append(_cfg("regions", {"R": r, "S": s}, k, kind))
    return cfgs


def plan_unit_cost():
    """Return the large points whose z3 call counts are recorded.

    Counts at 96 and 256 regions and at a 1600-state ring.  Their unprofiled
    times come from :func:`plan_unit_cost_time` and the timing sweeps, so a cost per
    call can be computed without profiling overhead.

    :return: Configurations in execution order.
    :rtype: list

    Example::

        >>> len(plan_unit_cost())
        3
    """
    return [
        _cfg("regions", {"R": 96, "S": 4}, 3, mode="count"),
        _cfg("regions", {"R": 256, "S": 4}, 3, mode="count"),
        _cfg("flat", {"N": 1600, "T": 2}, 5, mode="count"),
    ]


def plan_unit_cost_time():
    """Return the unprofiled timing points that pair with :func:`plan_unit_cost`.

    Times of the region machines with 96 and 256 regions, measured without
    ``cProfile``.

    :return: Configurations in execution order.
    :rtype: list

    Example::

        >>> len(plan_unit_cost_time())
        2
    """
    return [
        _cfg("regions", {"R": 96, "S": 4}, 3),
        _cfg("regions", {"R": 256, "S": 4}, 3),
    ]


def plan_variables():
    """Return the variable-write points.

    Rings of 40 to 100 states that write 0 to 64 variables at bounds 2 to 10,
    in ``time`` and ``count`` mode, plus a second variable-free point.  The count
    records carry the number of z3 contexts created while compiling.

    :return: Configurations in execution order.
    :rtype: list

    Example::

        >>> len(plan_variables())
        21
    """
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
    """Return the sweeps over states, transitions, variables, regions, bound and nesting.

    The sweeps double each dimension until a point is expected to exceed the
    process cap.  The retest ran only the first 15 of these points, so the page
    takes its practical-range table from the original campaign.

    :return: Configurations in execution order.
    :rtype: list

    Example::

        >>> len(plan_timing())
        99
    """
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
    """Return the exclusive-region family and its satisfiable control.

    Unsatisfiable: ``n + 1`` regions that pick among ``n`` states, ``n`` from 3 to
    12.  Control: ``n`` regions and ``n`` states, satisfiable.  The solve limit is
    280 seconds.

    :return: Configurations in execution order.
    :rtype: list

    Example::

        >>> len(plan_pigeonhole())
        20
    """
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
    """Execute a named plan serially and append records to the output file.

    Looks the plan up in ``_PLANS``, runs each configuration through
    :func:`run_config` one after another, and writes one JSON line per point as soon
    as it finishes, so an interrupted run keeps what it measured.  An existing
    output file is removed first unless ``--append`` is given.  ``--limit`` keeps
    only the first configurations and ``--repeats`` overrides the per-plan repeat
    count.  Progress goes to standard output.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py run formula-grid --output grid.jsonl --limit 4
    """
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
    """Measure one JSON configuration in this process and print one ``RESULT`` line.

    This is the entry point :func:`_run_once` starts in a child process.  The
    output line is ``RESULT `` followed by the JSON record of
    :func:`measure_one`.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py measure '{"family": "flat", "params": {"N": 20}, "k": 4, "kind": "unsat", "mode": "count"}'
    """
    print("RESULT " + json.dumps(measure_one(json.loads(args.config))))
    return 0


def command_generate(args):
    """Print one synthetic model and its query.

    Collects the parameters given on the command line (``--N``, ``--T``, ``--V``,
    ``--R``, ``--S``, ``--D``, ``--holes``, ``--pigeons``), builds the
    configuration with :func:`build`, prints the model, a blank line, ``// query``
    and the query.  The output of the model part is a valid ``.fcstm`` file.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py generate regions --R 2 --S 3 --k 2
    """
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
    """Read one JSON Lines data file.

    Every non-blank line is parsed and returned, including records that carry an
    ``error`` key; callers filter those themselves, because a timeout record is
    information in some tables and noise in others.

    :param directory: Data directory.
    :type directory: pathlib.Path
    :param name: File name inside the directory.
    :type name: str
    :return: Parsed records in file order.
    :rtype: list
    :raises OSError: If the file cannot be opened.
    :raises json.JSONDecodeError: If a non-blank line is not valid JSON.

    Example::

        >>> len(load_records(_DEFAULT_DATA, "pigeonhole.jsonl"))
        20
    """
    path = Path(directory) / name
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def nodes_flat(n, k):
    """Return the DAG node count of the region-free ring, two transitions per state, no variables.

    The closed form is :math:`21Nk - 18N + 33k + 6`.  It holds for ``k >= 2`` and
    for the unsatisfiable query of :func:`build`, which needs ``n >= k + 3`` states.

    :param n: Number of leaf states.
    :type n: int
    :param k: Step bound.
    :type k: int
    :return: Number of distinct nodes of ``solve_formula``.
    :rtype: int

    Example::

        >>> nodes_flat(8, 2)
        264
    """
    return 21 * n * k - 18 * n + 33 * k + 6


def nodes_flat_vars(n, k, v):
    """Return the DAG node count of the ring whose transitions write ``v`` variables.

    The closed form is :math:`23Nk - 20N + 4Vk + 35k + 9`, again for two
    transitions per state, ``k >= 2`` and ``n >= k + 3``.

    :param n: Number of leaf states.
    :type n: int
    :param k: Step bound.
    :type k: int
    :param v: Variables written by every writing transition.
    :type v: int
    :return: Number of distinct nodes of ``solve_formula``.
    :rtype: int

    Example::

        >>> nodes_flat_vars(8, 2, 1)
        295
    """
    return 23 * n * k - 20 * n + 4 * v * k + 35 * k + 9


def bool_vars(n, t, k):
    """Return the number of z3 boolean variables allocated for the first solver check.

    The closed form is :math:`1 + 8k + T(k-1) + N(4k-2) + 3NT(k-1)`.  Unlike the
    node count it is exact for any number of transitions per state.

    :param n: Number of leaf states.
    :type n: int
    :param t: Transitions per state.
    :type t: int
    :param k: Step bound.
    :type k: int
    :return: The ``mk bool var`` statistic of the first check.
    :rtype: int

    Example::

        >>> bool_vars(8, 2, 2)
        115
    """
    return 1 + 8 * k + t * (k - 1) + n * (4 * k - 2) + 3 * n * t * (k - 1)


def _lstsq(rows, getters, value, max_degrees):
    """Fit ``value`` with every monomial whose per-variable degree is bounded.

    The design matrix has one column per exponent tuple in the product of
    ``range(d + 1)`` over ``max_degrees``; the solution is the minimum-norm least
    squares fit, so a rank-deficient grid still returns coefficients (the caller
    reads the residual to judge the fit).

    :param rows: Records to fit.
    :type rows: list
    :param getters: One function per variable, returning its value for a record.
    :type getters: list
    :param value: Function returning the fitted quantity of a record.
    :type value: callable
    :param max_degrees: Highest allowed exponent of each variable.
    :type max_degrees: list
    :return: ``(exponents, coefficients, maximum absolute residual)``.
    :rtype: tuple
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
    """Format fitted monomials as a readable sum, dropping near-zero coefficients.

    Coefficients within ``1e-6`` of an integer are printed as that integer, the
    others with four significant digits; a constant term has no monomial.

    :param names: Variable names in the order of the exponent tuples.
    :type names: list
    :param exponents: Exponent tuples, as returned by :func:`_lstsq`.
    :type exponents: list
    :param coefficients: Fitted coefficients, one per exponent tuple.
    :type coefficients: list
    :return: Text such as ``2 + 3.5*N + -1*N*k``.
    :rtype: str

    Example::

        >>> _format_poly(['N', 'k'], [(0, 0), (1, 0), (1, 1)], [2.0, 3.5, -1.0])
        '2 + 3.5*N + -1*N*k'
    """
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
    """Return one configuration parameter of a record, with a default.

    :param record: Measurement record.
    :type record: dict
    :param name: Parameter name inside ``record["cfg"]["params"]``.
    :type name: str
    :param default: Value when the parameter is absent, defaults to ``None``.
    :type default: object, optional
    :return: The parameter or ``default``.
    :rtype: object

    Example::

        >>> _param({'cfg': {'params': {'N': 3}}}, 'T', 2)
        2
    """
    return record["cfg"]["params"].get(name, default)


def _select(rows, family, mode, kind="unsat", where=lambda r: True):
    """Select the records of one family, mode and kind that also satisfy ``where``.

    Records with an ``error`` key are always dropped.

    :param rows: Records to filter.
    :type rows: list
    :param family: Model family.
    :type family: str
    :param mode: ``time`` or ``count``.
    :type mode: str
    :param kind: ``unsat`` or ``sat``, defaults to ``"unsat"``.
    :type kind: str, optional
    :param where: Extra predicate on a record, defaults to accepting everything.
    :type where: callable, optional
    :return: The matching records.
    :rtype: list
    """
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
    """Print the fitted closed forms and power-law fits from the data files.

    Refits the node count, boolean-variable count and call count of the grids in
    ``formula_grid.jsonl`` by least squares and prints each polynomial with its
    maximum residual, so that a coefficient on the page can be traced to its
    derivation.  Needs numpy.  The exact forms print as integers; the fitted ones
    show their non-integer coefficients.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py fit --data docs/source/explanations/bmc_scaling/data
    """
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
    """Return the fitted node count of the region family.

    The coefficients are the rounded ones printed on the page, so the function and
    the page agree; the fit is not exact (largest grid residual 11.5 nodes, largest
    out-of-sample error 0.94%).

    :param r: Number of regions.
    :type r: int
    :param s: Leaf states per region.
    :type s: int
    :param k: Step bound.
    :type k: int
    :return: Predicted number of distinct nodes.
    :rtype: float

    Example::

        >>> nodes_regions(2, 3, 2)
        373.0
    """
    return 23 * r * s * k - 18 * r * s + 22.3 * r * k + 2.9 * r + 46.2 * k + 17.6


def calls_flat(n, k):
    """Return the fitted z3 call count of building the ring formula, two transitions per state.

    :param n: Number of leaf states.
    :type n: int
    :param k: Step bound.
    :type k: int
    :return: Predicted number of z3 C-interface calls (within 0.3% on the fit grid).
    :rtype: int

    Example::

        >>> calls_flat(8, 2)
        18101
    """
    return 1680 * n * k - 1578 * n + 1698 * k + 449


def calls_regions(r, s, k):
    """Return the fitted z3 call count of building the formula of the region family.

    The ``R * R`` term is real: it is what makes construction bend upward when there
    are many small regions.

    :param r: Number of regions.
    :type r: int
    :param s: Leaf states per region.
    :type s: int
    :param k: Step bound.
    :type k: int
    :return: Predicted number of z3 C-interface calls (within 0.3% on the fit grid).
    :rtype: int

    Example::

        >>> calls_regions(2, 3, 2)
        23709
    """
    return (
        r * s * (1754 * k - 1418)
        + r * (976 * k + 440)
        + r * r * (151 * k - 96)
        + 2561 * k
        + 439
    )


def _median(values):
    """Return the median of a non-empty list of numbers (the mean of the middle pair when even).

    :param values: Numbers to summarise.
    :type values: list
    :return: The median.
    :rtype: float

    Example::

        >>> _median([5, 1, 3])
        3
    """
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def command_check(args):
    """Check every closed form against the committed data and print a report.

    Compares the exact closed forms for equality on the grid and on every large
    record, the fitted ones against their stated tolerances, the context count
    against :math:`2W V (k-1)`, and reports the propagation fit, the
    exclusive-region conflict ratios, the cost per context and per z3 call, the
    share of build time and the node count against ``T``.  Every number the page
    quotes from the data is printed here.  Failures are listed after the report and
    make the exit status ``1``.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py check-formulas --data docs/source/explanations/bmc_scaling/data
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
    """Write the slim original measurement file from the raw ``results*.jsonl``.

    Keeps the records with status ``sat``, ``unsat`` or ``timeout`` and drops the
    rest, removes the solver time limit from the configuration, marks every record
    as ``time`` mode and adds the commit, machine and conditions of the original
    campaign.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py import-original --source path/to/results --output original_measurements.jsonl
    """
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
    """Return compile plus solve seconds of a record, counting a missing phase as zero.

    Same value as :func:`_total_seconds`; kept as a separate name for the retest
    comparison code.

    :param rec: Measurement record.
    :type rec: dict
    :return: Total seconds.
    :rtype: float
    """
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
    """Group the unsatisfiable records of one range-table row by the swept value.

    ``extra`` narrows the family: ``plain`` drops records with calls or an explicit
    ``T`` unless ``T`` is the swept dimension, ``writes`` keeps rings that write
    variables, ``filter`` and ``nofilter`` keep the call-count machines with and
    without a ``where`` clause.  Records of other sweeps (another fixed parameter,
    another bound) are skipped.

    :param records: Original measurement records.
    :type records: list
    :param family: Model family of the row.
    :type family: str
    :param dim: Swept dimension; ``k`` sweeps the bound.
    :type dim: str
    :param fixed: Parameters held fixed, name to value.
    :type fixed: dict
    :param k: Bound held fixed, or ``None`` when the bound is swept.
    :type k: int or None
    :param extra: Row-specific narrowing named above, or ``None``.
    :type extra: str or None
    :return: Records per swept value.
    :rtype: dict
    """
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
    """Compute the practical-range table, one dictionary per dimension.

    For each of 10, 60 and 300 seconds the row holds the largest swept value whose
    median total time (compile plus solve, over duplicate records) finished within
    the budget, with that time.  ``first_unfinished`` is the smallest value that
    timed out, or ``None`` when none did.  Values are "largest measured", so the
    true limit lies between a value and the next measured one.

    :param records: Original measurement records.
    :type records: list
    :return: Rows with ``label``, ``budgets`` (budget to ``(value, seconds)``) and
        ``first_unfinished``.
    :rtype: list

    Example::

        $ python tools/measure_bmc_scaling.py range-table --data docs/source/explanations/bmc_scaling/data
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
    """Return the median of a non-empty list of numbers.

    Equal to :func:`_median`; this name serves the range-table code.

    :param values: Numbers to summarise.
    :type values: list
    :return: The middle value, or the mean of the middle pair when the count is even.
    :rtype: float

    Example::

        >>> statistics_median([1, 2, 3, 4])
        2.5
    """
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def command_range_table(args):
    """Print the practical-range table from the original measurements.

    Reads ``original_measurements.jsonl`` and prints one line per dimension with
    the largest size that finished within 10, 60 and 300 seconds and the first
    size that timed out.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py range-table --data docs/source/explanations/bmc_scaling/data
    """
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
    """Return a hashable key identifying a configuration across campaigns.

    The key is ``(family, params as sorted JSON, k, kind)``; ``mode`` and the
    solver limit are deliberately left out, so a retest record matches its original.

    :param rec: Measurement record.
    :type rec: dict
    :return: The key.
    :rtype: tuple

    Example::

        >>> _config_key({'cfg': {'family': 'flat', 'params': {'N': 4}, 'k': 2, 'kind': 'unsat'}})
        ('flat', '{"N": 4}', 2, 'unsat')
    """
    cfg = rec["cfg"]
    return (
        cfg["family"],
        json.dumps(cfg["params"], sort_keys=True),
        cfg["k"],
        cfg["kind"],
    )


def command_compare_retest(args):
    """Print retest-over-original time ratios for configurations measured both times.

    Only finished unsatisfiable retest points with an original counterpart are
    listed; the original time is the median over its duplicate records.  The ratio
    is a rough check, because each point is a single run on a shared machine.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    :return: Process exit status, ``0`` on success.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py compare-retest --data docs/source/explanations/bmc_scaling/data
    """
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
    """Build the argument parser with every sub-command.

    The root description is the original module text kept in ``_HELP_DESCRIPTION``,
    so ``--help`` is unchanged by edits to the module docstring.  Every sub-command
    binds its handler as ``handler`` for :func:`main`.

    :return: The parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description=_HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    """Run the tool's command line.

    :param argv: Arguments, defaults to ``sys.argv[1:]``.
    :type argv: list, optional
    :return: Process exit status of the chosen sub-command.
    :rtype: int

    Example::

        $ python tools/measure_bmc_scaling.py --help
    """
    args = _build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
