"""BMC checks machines with history through their lowered form.

Every expected verdict is computed by an exhaustive ``SimulationRuntime``
search over all event subsets, so BMC and the simulator must agree on the
lowered machine.
"""

import json

import pytest

from pyfcstm.model import load_state_machine_from_text
from test.bmc.test_guarded_initial_scaling import (
    assert_bound_is_tight,
    bmc_status,
    earliest_step,
    run_bmc,
)
from test.model import test_history_lowering as lowering
from test.model.test_history_lowering import BLOCKED, BLOCKED_INITIALS, WASHER


def _model(tmp_path, text, name="model.fcstm"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _leaf(path):
    return lambda runtime: ".".join(runtime.current_state.path) == path


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["text", "leaf"],
    [
        (WASHER, "Washer.Program.Wash.Agitate"),
        (BLOCKED % BLOCKED_INITIALS["gated"], "R.O.K.K1"),
        (lowering.TestNestedOwners.TEXT, "R.O.S2.B2"),
    ],
    ids=["washer-agitate", "blocked-k1", "nested-b2"],
)
def test_reachability_bounds_match_the_simulator(text, leaf, tmp_path):
    model = _model(tmp_path, text)
    assert_bound_is_tight(model, _leaf(leaf), 'active("%s")' % leaf, tmp_path)


@pytest.mark.unittest
def test_deep_restore_is_found_at_its_earliest_step(tmp_path):
    def restored(runtime):
        return (
            ".".join(runtime.current_state.path) == "Washer.Program.Wash.Agitate"
            and runtime.vars["agitate_entries"] == 2
            and runtime.vars["fill_entries"] == 1
        )

    formula = (
        'active("Washer.Program.Wash.Agitate") && var("agitate_entries") == 2 '
        '&& var("fill_entries") == 1'
    )
    assert_bound_is_tight(_model(tmp_path, WASHER), restored, formula, tmp_path, horizon=6)


@pytest.mark.unittest
def test_a_restore_without_a_record_never_skips_fill(tmp_path):
    # Agitate can only be restored after it was left, which needs Fill first.
    def violation(runtime):
        return (
            ".".join(runtime.current_state.path) == "Washer.Program.Wash.Agitate"
            and runtime.vars["fill_entries"] == 0
        )

    assert earliest_step(WASHER, violation, 5) is None
    status = bmc_status(
        _model(tmp_path, WASHER),
        'check invariant <= 5: !(active("Washer.Program.Wash.Agitate") && var("fill_entries") == 0);',
        tmp_path,
    )
    assert status == "unsat"


@pytest.mark.unittest
def test_havoc_all_starts_from_any_valid_history_record(tmp_path):
    # A havocked start may remember any leaf, so Deep restores Agitate in one
    # step; no restore is ever in flight at the start.
    model = _model(tmp_path, WASHER)
    query = (
        'init state("Washer.Paused") havoc *;\n'
        'check reach <= 1: active("Washer.Program.Wash.Agitate");'
    )
    result = run_bmc(model, query, tmp_path, "--json")
    payload = json.loads(result.stdout)
    assert payload["result"]["status"] == "sat"
    assert payload["replay"]["ok"] is True
    initial = payload["witness"]["frames"][0]["vars"]
    owner = load_state_machine_from_text(WASHER).history_owners[0]
    assert initial["__hist_goto"] == 0
    assert owner.decode(initial["__hist_Program"]) == ("Wash", "Agitate")


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["name", "value"],
    [("__hist_goto", 5), ("__hist_Program", 2), ("__hist_Program", 99)],
)
def test_havocked_history_variables_cannot_take_unreachable_values(name, value, tmp_path):
    model = _model(tmp_path, WASHER)
    query = (
        'init state("Washer.Paused") havoc { %s } where var("%s") == %d;\n'
        'check reach <= 2: active("Washer.Paused");' % (name, name, value)
    )
    result = run_bmc(model, query, tmp_path, "--json")
    payload = json.loads(result.stdout)
    assert payload["result"]["feasibility"]["infeasible_stage"] == "initialization"
    assert payload["result"]["feasibility"]["initialization"]["status"] == "unsat"
    for mode in ("formal", "proof"):
        explained = run_bmc(model, query, tmp_path, "--explain-infeasibility", mode)
        assert "SCENARIO INFEASIBLE" in explained.output


@pytest.mark.unittest
def test_a_havocked_start_from_a_real_record_replays(tmp_path):
    model = _model(tmp_path, WASHER)
    owner = load_state_machine_from_text(WASHER).history_owners[0]
    record = owner.record_value(("Idle",))
    query = (
        'init state("Washer.Paused") havoc { __hist_Program } where var("__hist_Program") == %d;\n'
        'check reach <= 1: active("Washer.Program.Idle");' % record
    )
    assert bmc_status(model, query, tmp_path) == "sat"


@pytest.mark.unittest
def test_queries_can_read_history_variables(tmp_path):
    model = _model(tmp_path, WASHER)
    status = bmc_status(
        model,
        'check invariant <= 5: var("__hist_goto") == 0;',
        tmp_path,
    )
    assert status == "unsat"
