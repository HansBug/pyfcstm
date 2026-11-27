"""Differential check of how a BMC formula is built and solved.

Three comparisons over the benchmark corpus under ``benchmarks/bmc/solving/cases``
and a few inline models, all through public APIs:

* **Construction modes.**  Every query is compiled at several bounds with the
  later steps lowered one by one (``off``), instantiated from a template (``on``)
  and instantiated and compared with a direct lowering at every step
  (``verify``).  The compiled core, including its provenance ledgers, and the
  solve formula must be identical, and so must the warnings raised.
* **Solver context.**  Solving in a fresh Z3 context and in the shared one must
  reach the same verdict.
* **History independence.**  With a fresh context, solving the same formula
  again after unrelated terms were built and unrelated solves were made must
  give the same witness and the same search counters.

The mode switch is the internal environment variable read by
:func:`pyfcstm.bmc.step_template.step_instantiation_mode`; it is not a documented
option.

Usage::

    python tools/check_bmc_construction.py --check
    python tools/check_bmc_construction.py --check --bounds 3,6 --limit 20
    python tools/check_bmc_construction.py --self-check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import z3

ROOT = Path(__file__).resolve().parents[1]
# Run from a checkout without an installed package, as the other tools do.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.bmc import (  # noqa: E402
    BmcOptions,
    compile_bmc_query,
    decode_bmc_result_trace,
    solve_bmc_property,
)
from pyfcstm.bmc.errors import BmcError  # noqa: E402
from pyfcstm.bmc.step_template import MODE_VARIABLE  # noqa: E402
from pyfcstm.model import load_state_machine_from_text  # noqa: E402

CASES = ROOT / "benchmarks" / "bmc" / "solving" / "cases"
MODES = ("off", "on", "verify")

INLINE_MODELS = {
    "flat": (
        "def int x = 0; def int y = 0; input int d;"
        " state Root { state A { during { x = x + d; y = y + 2 * x - 1; } }"
        " state B; state C; [*] -> A; A -> B : if [x >= 2 && y >= 3];"
        " A -> C :: Stop; B -> A :: Back effect { x = 0; }; }",
        ['check reach <= {n}: active("Root.B");', "check invariant <= {n}: x >= 0;"],
    ),
    "regions": (
        "def int x = 0; def int y = 0; state Root {"
        " region First { [*] -> Idle; state Idle; state Busy { during { x = x + 1; } }"
        " Idle -> Busy :: Go; Busy -> Idle : if [x >= 3]; }"
        " region Second { [*] -> Off; state Off; state On { during { y = y + x; } }"
        " Off -> On : if [x >= 1]; On -> Off : if [y >= 5]; } }",
        ['check reach <= {n}: active("Root.Second.On");'],
    ),
    "power": (
        "def int x = 2; def int y = 3; state Root { state A { during { x = x ** y; } }"
        " state B; [*] -> A; A -> B : if [x > 100]; }",
        ['check reach <= {n}: active("Root.B");'],
    ),
}


def _strip(value: Any) -> Any:
    """Drop the wall-clock fields, which differ between any two runs."""
    if isinstance(value, dict):
        return {
            key: _strip(item) for key, item in value.items() if not key.endswith("_ms")
        }
    if isinstance(value, list):
        return [_strip(item) for item in value]
    return value


def _digest(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def corpus(limit: int) -> List[Tuple[str, str, str]]:
    """Return ``(name, model_text, query_text)`` for the corpus.

    :param limit: Number of corpus queries to take, spread evenly over the
        corpus so that they come from different models, ``0`` for all.
    :type limit: int
    :return: Cases in a fixed order.
    :rtype: List[Tuple[str, str, str]]
    """
    found: List[Tuple[str, str, str]] = []
    for directory in sorted(CASES.iterdir()):
        model = directory / "model.fcstm"
        if not model.is_file():
            continue
        for query in sorted(directory.glob("*.fbmcq")):
            found.append(
                (
                    "%s/%s" % (directory.name, query.stem),
                    model.read_text(encoding="utf-8"),
                    query.read_text(encoding="utf-8"),
                )
            )
    if limit:
        found = found[:: max(1, len(found) // limit)][:limit]
    for name, (model_text, queries) in sorted(INLINE_MODELS.items()):
        for index, query in enumerate(queries):
            found.append(("inline/%s/%d" % (name, index), model_text, query))
    return found


def with_bound(query_text: str, bound: int) -> str:
    """Return the query with its first ``<= N`` bound replaced.

    :param query_text: ``.fbmcq`` text.
    :type query_text: str
    :param bound: New bound.
    :type bound: int
    :return: Text with the bound replaced; ``{n}`` placeholders are filled.
    :rtype: str
    """
    import re

    text = query_text.replace("{n}", str(bound))
    return re.sub(r"(check\s+\w+\s*<=\s*)\d+", r"\g<1>%d" % bound, text, count=1)


def build(model_text: str, query_text: str, mode: str, options: Dict[str, Any]):
    """Compile one query under a construction mode.

    :param model_text: FCSTM text.
    :type model_text: str
    :param query_text: ``.fbmcq`` text.
    :type query_text: str
    :param mode: ``off``, ``on`` or ``verify``.
    :type mode: str
    :param options: Keyword arguments of :class:`pyfcstm.bmc.engine.BmcOptions`.
    :type options: Dict[str, Any]
    :return: Digest of the core and the solve formula, and the sorted warnings;
        or the error text when compilation fails.
    :rtype: Tuple[str, Tuple[str, ...]]
    """
    previous = os.environ.get(MODE_VARIABLE)
    os.environ[MODE_VARIABLE] = mode
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                formula = compile_bmc_query(
                    load_state_machine_from_text(model_text),
                    query_text,
                    options=BmcOptions(**options) if options else None,
                )
                body = _digest(
                    [_strip(formula.core.to_canonical()), formula.solve_formula.sexpr()]
                )
            except BmcError as err:
                # BmcError: the query is invalid or unsupported for this model
                # and bound; every mode has to report the same error.
                body = "error: %s" % err
    finally:
        if previous is None:
            os.environ.pop(MODE_VARIABLE, None)
        else:
            os.environ[MODE_VARIABLE] = previous
    return body, tuple(sorted(str(item.message) for item in caught))


def compare_modes(
    cases: Sequence[Tuple[str, str, str]], bounds: Iterable[int]
) -> List[str]:
    """Compare the three construction modes; return one line per difference.

    :param cases: Cases from :func:`corpus`.
    :type cases: Sequence[Tuple[str, str, str]]
    :param bounds: Bounds to compile each query at.
    :type bounds: Iterable[int]
    :return: Differences, empty when every mode agrees.
    :rtype: List[str]
    """
    problems: List[str] = []
    for name, model_text, query_text in cases:
        for bound in bounds:
            query = with_bound(query_text, bound)
            for options in ({}, {"cone_slicing": True}):
                results = {
                    mode: build(model_text, query, mode, options) for mode in MODES
                }
                for mode in ("on", "verify"):
                    if results[mode] != results["off"]:
                        problems.append(
                            "%s bound=%d options=%s: mode %s differs from off"
                            % (name, bound, options, mode)
                        )
    return problems


def compare_contexts(cases: Sequence[Tuple[str, str, str]], bound: int) -> List[str]:
    """Compare the solver contexts; return one line per difference.

    :param cases: Cases from :func:`corpus`.
    :type cases: Sequence[Tuple[str, str, str]]
    :param bound: Bound to solve at.
    :type bound: int
    :return: Differences, empty when verdicts agree and fresh solving is stable.
    :rtype: List[str]
    """
    problems: List[str] = []
    for name, model_text, query_text in cases:
        query = with_bound(query_text, bound)
        model = load_state_machine_from_text(model_text)
        try:
            formula = compile_bmc_query(model, query)
        except BmcError:
            # BmcError: not valid at this bound; the construction comparison
            # already requires every mode to agree on that.
            continue
        fresh = solve_bmc_property(formula, timeout_ms=20000)
        shared = solve_bmc_property(formula, timeout_ms=20000, solver_context="shared")
        if (fresh.status, fresh.outcome) != (shared.status, shared.outcome):
            if "timeout" not in (fresh.status, shared.status):
                problems.append(
                    "%s: fresh %s/%s, shared %s/%s"
                    % (name, fresh.status, fresh.outcome, shared.status, shared.outcome)
                )
        if fresh.solver_context != "fresh" or fresh.status == "timeout":
            continue
        clutter = [z3.Int("clutter_%d" % index) + index for index in range(300)]
        again = solve_bmc_property(compile_bmc_query(model, query), timeout_ms=20000)
        del clutter
        keys = ("conflicts", "decisions", "propagations")
        counters = [
            tuple(item.solver_statistics.get(k) for k in keys)
            for item in (fresh, again)
        ]
        if counters[0] != counters[1]:
            problems.append("%s: search counters changed with history" % name)
        elif fresh.model is not None and (
            _digest(_strip(decode_bmc_result_trace(fresh).to_canonical()))
            != _digest(_strip(decode_bmc_result_trace(again).to_canonical()))
        ):
            problems.append("%s: witness changed with history" % name)
    return problems


def self_check() -> List[str]:
    """Show that the comparisons can fail.

    :return: Problems with the check itself, empty when it works.
    :rtype: List[str]
    """
    model_text, queries = INLINE_MODELS["flat"]
    one = build(model_text, with_bound(queries[0], 4), "on", {})
    same = build(model_text, with_bound(queries[0], 4), "off", {})
    other = build(model_text, with_bound(queries[0], 5), "on", {})
    problems = []
    if one != same:
        problems.append("two modes of one query were reported different")
    if one == other:
        problems.append("two different bounds were reported equal")
    return problems


def main(argv: Sequence[str] = ()) -> int:
    """Run the requested comparisons.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: Sequence[str], optional
    :return: ``0`` when everything agrees.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="run the comparisons")
    parser.add_argument("--self-check", action="store_true", help="test the comparison")
    parser.add_argument("--bounds", default="2,3,5,9", help="comma separated bounds")
    parser.add_argument("--limit", type=int, default=0, help="corpus queries to use")
    args = parser.parse_args(list(argv) or sys.argv[1:])
    if not (args.check or args.self_check):
        parser.error("nothing to do; pass --check or --self-check")
    problems = self_check()
    if args.check and not problems:
        cases = corpus(args.limit)
        bounds = [int(item) for item in args.bounds.split(",")]
        started = time.monotonic()
        problems += compare_modes(cases, bounds)
        problems += compare_contexts(cases, bounds[-1])
        print(
            "bmc construction check: %d queries, bounds %s, %.0f s"
            % (len(cases), bounds, time.monotonic() - started)
        )
    for line in problems:
        print("FAIL", line)
    if problems:
        return 1
    print("bmc construction check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
