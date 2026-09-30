"""End-to-end BMC on models whose entry macro-steps read many guard atoms.

Every model here enters nested composites whose initial transitions are all
guarded, from several entry transitions, so one macro-step reads well over the
twelve atoms a truth-table partition check can enumerate.  Each ``pyfcstm bmc``
verdict is cross-checked against an exhaustive ``SimulationRuntime`` search over
every event subset in every step, so the expected answers are computed, not
hard-coded.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyfcstm.entry.cli import pyfcstmcli
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

FIXTURES = Path(__file__).parent / "fixtures"


def earliest_step(model_text, predicate, bound):
    """
    Return the earliest BMC step at which ``predicate`` can hold, or ``None``.

    Step 1 is the initialisation cycle, matching ``check reach <= k``.  The
    search replays event sequences from scratch and explores every subset of
    the model's events in every cycle, keeping one representative sequence per
    reached configuration.
    """
    machine = load_state_machine_from_text(model_text)
    events = sorted(
        {
            t.event.path_name
            for s in machine.walk_states()
            for t in s.transitions
            if t.event
        }
    )
    subsets = [
        list(chosen)
        for size in range(len(events) + 1)
        for chosen in itertools.combinations(events, size)
    ]

    def replay(sequence):
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        for chosen in sequence:
            runtime.cycle(chosen)
        return runtime

    def signature(runtime):
        return tuple(runtime.current_state.path), tuple(sorted(runtime.vars.items()))

    first = replay(())
    if predicate(first):
        return 1
    seen = {signature(first)}
    frontier = [()]
    for step in range(2, bound + 1):
        following = []
        for sequence in frontier:
            for chosen in subsets:
                candidate = sequence + (tuple(chosen),)
                runtime = replay(candidate)
                if predicate(runtime):
                    return step
                key = signature(runtime)
                if key not in seen:
                    seen.add(key)
                    following.append(candidate)
        frontier = following
    return None


def run_bmc(model_path, query_text, tmp_path, *extra):
    query_path = tmp_path / "property.fbmcq"
    query_path.write_text(query_text + "\n", encoding="utf-8")
    result = CliRunner().invoke(
        pyfcstmcli, ["bmc", "-i", str(model_path), "-q", str(query_path), *extra]
    )
    assert "Traceback" not in result.output, result.output
    return result


def bmc_status(model_path, query_text, tmp_path):
    result = run_bmc(model_path, query_text, tmp_path, "--json")
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == result.exit_code
    if payload["result"]["status"] == "sat":
        assert payload["replay"]["ok"] is True
    return payload["result"]["status"]


def active(path):
    return lambda runtime: ".".join(runtime.current_state.path) == path


def assert_bound_is_tight(model_path, predicate, formula, tmp_path, horizon=8):
    """BMC is unsat one step before the simulated earliest step and sat at it."""
    earliest = earliest_step(model_path.read_text(encoding="utf-8"), predicate, horizon)
    assert earliest is not None and earliest > 1
    assert (
        bmc_status(
            model_path, "check reach <= %d: %s;" % (earliest - 1, formula), tmp_path
        )
        == "unsat"
    )
    assert (
        bmc_status(model_path, "check reach <= %d: %s;" % (earliest, formula), tmp_path)
        == "sat"
    )


@pytest.mark.unittest
def test_guarded_initial_selectors_are_checked_by_bmc(tmp_path):
    model = FIXTURES / "guarded_initial_selectors.fcstm"
    assert_bound_is_tight(
        model,
        active("Washer.Program.Wash.Agitate"),
        'active("Washer.Program.Wash.Agitate")',
        tmp_path,
    )


@pytest.mark.unittest
def test_guarded_initial_selectors_report_verdicts_without_internal_errors(tmp_path):
    model = FIXTURES / "guarded_initial_selectors.fcstm"
    result = run_bmc(
        model, 'check reach <= 2: active("Washer.Program.Wash.Agitate");', tmp_path
    )
    # The human report of the original failing command: a bounded verdict
    # (exit code 1 for an unrealizable reach goal), not an internal error.
    assert result.exit_code == 1
    assert "NOT SATISFIED WITHIN BOUND" in result.output
    assert "partition check" not in result.output


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("predicate", "formula"),
    [
        (
            active("Washer.Program.Wash.Agitate"),
            'active("Washer.Program.Wash.Agitate")',
        ),
        (
            lambda runtime: (
                ".".join(runtime.current_state.path) == "Washer.Program.Wash.Agitate"
                and runtime.vars["entries"] == 2
                and runtime.vars["inits"] == 1
            ),
            'active("Washer.Program.Wash.Agitate") && var("entries") == 2 && var("inits") == 1',
        ),
    ],
    ids=["reach-agitate", "resume-agitate-without-reinitialising"],
)
def test_restore_by_guarded_initials_is_checked_by_bmc(predicate, formula, tmp_path):
    assert_bound_is_tight(
        FIXTURES / "restore_by_guarded_initials.fcstm", predicate, formula, tmp_path
    )


def selector_family(entries, fanout, depth):
    """Model text: ``entries`` entry events set a selector, then ``depth`` nested guarded choices."""
    lines = ["def int m = 0;", "state R {", "    state Off;"]

    def composite(name, level, indent):
        pad = "    " * indent
        if level == depth:
            lines.append("%sstate %s;" % (pad, name))
            return
        lines.append("%sstate %s {" % (pad, name))
        children = ["%s_%d" % (name, index) for index in range(fanout)]
        for child in children:
            composite(child, level + 1, indent + 1)
        for value in range(entries):
            lines.append(
                "%s    [*] -> %s : if [m == %d];"
                % (pad, children[value % fanout], value)
            )
        lines.append("%s}" % pad)

    composite("S", 0, 1)
    lines.append("    [*] -> Off;")
    for value in range(entries):
        lines.append("    Off -> S :: go%d effect { m = %d; }" % (value, value))
    lines.append("    !S -> Off :: stop;")
    lines.append("}")
    return "\n".join(lines) + "\n"


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("entries", "fanout", "depth", "target"),
    [
        (3, 3, 2, "R.S.S_2.S_2_2"),
        (4, 2, 3, "R.S.S_1.S_1_1.S_1_1_1"),
        (4, 4, 2, "R.S.S_3.S_3_3"),
    ],
)
def test_generated_guarded_selector_family_is_checked_by_bmc(
    entries, fanout, depth, target, tmp_path
):
    model = tmp_path / "selectors.fcstm"
    model.write_text(selector_family(entries, fanout, depth), encoding="utf-8")
    assert_bound_is_tight(model, active(target), 'active("%s")' % target, tmp_path)
