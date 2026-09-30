"""BMC checks machines with history through their lowered form.

Every expected verdict is computed by an exhaustive ``SimulationRuntime``
search over all event subsets, so BMC and the simulator must agree on the
lowered machine.
"""

import json

import pytest

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
def test_havoc_all_keeps_history_records_empty(tmp_path):
    model = _model(tmp_path, WASHER)
    query = (
        'init state("Washer.Paused") havoc *;\n'
        'check reach <= 3: active("Washer.Program.Wash.Agitate");'
    )
    result = run_bmc(model, query, tmp_path, "--json")
    payload = json.loads(result.stdout)
    assert payload["result"]["status"] == "sat"
    assert payload["replay"]["ok"] is True
    initial = payload["witness"]["frames"][0]["vars"]
    assert initial["__hist_goto"] == 0 and initial["__hist_Program"] == 0
    # With empty records one step from Paused reaches Idle or Fill at most; a
    # havocked record could restore Agitate directly.
    deep_first = (
        'init state("Washer.Paused") havoc *;\n'
        'check reach <= 1: active("Washer.Program.Wash.Agitate");'
    )
    assert bmc_status(model, deep_first, tmp_path) == "unsat"


@pytest.mark.unittest
@pytest.mark.parametrize("name", ["__hist_goto", "__hist_Program"])
def test_history_variables_cannot_be_havocked(name, tmp_path):
    model = _model(tmp_path, WASHER)
    result = run_bmc(
        model,
        'init state("Washer.Paused") havoc { %s };\ncheck reach <= 2: active("Washer.Paused");' % name,
        tmp_path,
    )
    assert result.exit_code != 0
    assert "history lowering" in result.output
    assert name in result.output


@pytest.mark.unittest
def test_queries_can_read_history_variables(tmp_path):
    model = _model(tmp_path, WASHER)
    status = bmc_status(
        model,
        'check invariant <= 5: var("__hist_goto") == 0;',
        tmp_path,
    )
    assert status == "unsat"
