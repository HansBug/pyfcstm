"""Tests for solving linear-arithmetic formulas in a fresh Z3 context.

The behaviour under test: with ``solver_context="fresh"`` the search path, and so
the witness, of a linear-arithmetic query depends only on the formula, the
options and the Z3 version.  Everything is driven through the public solving
API and the ``pyfcstm bmc`` command.
"""

from __future__ import annotations

import json
import sys
import threading

import pytest
import z3
from click.testing import CliRunner

import pyfcstm.solver.context as context_module
from pyfcstm.bmc import (
    BmcOptions,
    check_runtime_safety,
    compile_bmc_query,
    decode_bmc_result_trace,
    solve_bmc_property,
)
from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.entry import pyfcstmcli
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

LINEAR_MODEL = """
def int x = 0;
def int y = 0;
state Root {
    state A { during { x = x + 1; y = y + 2 * x - 1; } }
    state B;
    state C;
    [*] -> A;
    A -> B : if [x >= 2 && y >= 3];
    A -> C : if [y >= 9];
}
"""
LINEAR_QUERY = 'check reach <= 5: active("Root.B");'
UNSAT_QUERY = 'check reach <= 1: active("Root.B");'
NONLINEAR_MODEL = """
def int x = 1;
def int y = 2;
state Root {
    state A { during { x = x * y; y = y + 1; } }
    state B;
    [*] -> A;
    A -> B : if [x >= 8];
}
"""
EVENT_MODEL = """
def int x = 0;
state Root {
    state A { during { x = x + 1; } }
    state B;
    state C;
    [*] -> A;
    A -> B :: Go;
    A -> C :: Stop;
}
"""
EVENT_QUERY = (
    'assume events cardinality at_most_one {"Root.A.Go", "Root.A.Stop"};'
    ' check reach <= 3: active("Root.B");'
)
CONSTANT_FACTOR_MODEL = """
def int x = 0;
state Root {
    state A { during { x = x * (1 - 3) + 5; } }
    state B;
    [*] -> A;
    A -> B : if [x >= 5];
}
"""
SLICED_MODEL = """
def int x = 0;
def int unused = 0;
state Root {
    state A { during { x = x + 1; unused = unused + 3; } }
    state B;
    [*] -> A;
    A -> B : if [x >= 2];
}
"""


def _formula(model_text: str, query_text: str, **options):
    model = load_state_machine_from_text(model_text)
    return compile_bmc_query(
        model, query_text, options=BmcOptions(**options) if options else None
    )


def _without_timing(value):
    """Drop the wall-clock fields, which differ between any two runs."""
    if isinstance(value, dict):
        return {
            key: _without_timing(item)
            for key, item in value.items()
            if not key.endswith("_ms")
        }
    if isinstance(value, list):
        return [_without_timing(item) for item in value]
    return value


def _witness(result):
    return _without_timing(decode_bmc_result_trace(result).to_canonical())


def _search_counters(result):
    stats = result.solver_statistics
    return tuple(stats.get(key) for key in ("conflicts", "decisions", "propagations"))


def test_a_linear_query_is_solved_in_a_fresh_context_by_default() -> None:
    result = solve_bmc_property(_formula(LINEAR_MODEL, LINEAR_QUERY))

    assert result.status == "sat"
    assert result.solver_context == "fresh"
    assert result.to_canonical()["solver_context"] == "fresh"
    assert result.model is not None and result.model.ctx == z3.main_ctx()


def test_shared_context_solves_where_the_formula_was_built() -> None:
    result = solve_bmc_property(
        _formula(LINEAR_MODEL, LINEAR_QUERY), solver_context="shared"
    )

    assert result.status == "sat"
    assert result.solver_context == "shared"


def test_the_choice_does_not_change_verdicts() -> None:
    for query in (LINEAR_QUERY, UNSAT_QUERY):
        fresh = solve_bmc_property(_formula(LINEAR_MODEL, query))
        shared = solve_bmc_property(
            _formula(LINEAR_MODEL, query), solver_context="shared"
        )
        assert (fresh.status, fresh.outcome) == (shared.status, shared.outcome)


def test_a_non_linear_query_stays_where_the_formula_was_built() -> None:
    query = 'check reach <= 4: active("Root.B");'
    default = solve_bmc_property(_formula(NONLINEAR_MODEL, query))
    shared = solve_bmc_property(
        _formula(NONLINEAR_MODEL, query), solver_context="shared"
    )

    assert default.solver_context == "shared"
    assert (default.status, default.outcome) == (shared.status, shared.outcome)


@pytest.mark.parametrize(
    ("model_text", "query_text"),
    [
        pytest.param(EVENT_MODEL, EVENT_QUERY, id="event-cardinality"),
        pytest.param(
            CONSTANT_FACTOR_MODEL,
            'check reach <= 3: active("Root.B");',
            id="constant-expression-factor",
        ),
    ],
)
def test_shapes_z3_decides_are_still_linear(model_text, query_text) -> None:
    result = solve_bmc_property(_formula(model_text, query_text))

    assert result.status in ("sat", "unsat")
    assert result.solver_context == "fresh"


def test_the_witness_does_not_depend_on_how_the_formula_was_constructed() -> None:
    first = solve_bmc_property(_formula(LINEAR_MODEL, LINEAR_QUERY))
    # Unrelated terms change which numbers Z3 hands to the next terms built in
    # the main context, and so the numbering a shared solve would see.
    clutter = [z3.Int("clutter_%d" % index) + index for index in range(500)]
    second = solve_bmc_property(_formula(LINEAR_MODEL, LINEAR_QUERY))
    del clutter

    assert _witness(first) == _witness(second)
    assert _search_counters(first) == _search_counters(second)


def test_repeated_solves_of_one_formula_agree() -> None:
    formula = _formula(LINEAR_MODEL, LINEAR_QUERY)
    results = [solve_bmc_property(formula) for _ in range(3)]

    assert len({str(_witness(item)) for item in results}) == 1
    assert len({_search_counters(item) for item in results}) == 1


@pytest.mark.parametrize("profile", ["default", "logic", "tactic"])
@pytest.mark.parametrize("explanation", ["none", "formal", "proof"])
def test_every_profile_and_explanation_mode_runs_in_a_fresh_context(
    profile, explanation
) -> None:
    result = solve_bmc_property(
        _formula(LINEAR_MODEL, UNSAT_QUERY),
        solver_profile=profile,
        infeasibility_explanation=explanation,
    )
    shared = solve_bmc_property(
        _formula(LINEAR_MODEL, UNSAT_QUERY),
        solver_profile=profile,
        infeasibility_explanation=explanation,
        solver_context="shared",
    )

    assert result.solver_context == "fresh"
    assert (result.status, result.outcome) == (shared.status, shared.outcome)
    if explanation != "proof":
        assert _without_timing(result.to_canonical()["feasibility"]) == (
            _without_timing(shared.to_canonical()["feasibility"])
        )


def test_runtime_safety_check_follows_the_option_when_called_alone() -> None:
    core = _formula(LINEAR_MODEL, LINEAR_QUERY).core
    fresh = check_runtime_safety(core)
    shared = check_runtime_safety(core, solver_context="shared")

    assert fresh.status == shared.status


def test_cone_slicing_that_drops_variables_still_solves_and_reports() -> None:
    formula = _formula(
        SLICED_MODEL, 'check reach <= 4: active("Root.B");', cone_slicing=True
    )
    assert formula.core.cone_slice is not None
    assert formula.core.cone_slice.dropped_variables
    fresh = solve_bmc_property(formula)
    shared = solve_bmc_property(formula, solver_context="shared")

    assert (fresh.status, fresh.outcome) == (shared.status, shared.outcome)
    assert fresh.solver_context == "fresh"
    assert _witness(fresh) == _witness(
        solve_bmc_property(
            _formula(
                SLICED_MODEL, 'check reach <= 4: active("Root.B");', cone_slicing=True
            )
        )
    )


def test_a_runtime_error_found_through_a_division_by_an_input_is_solved_shared() -> (
    None
):
    model = """
    input int d;
    def int x = 0;
    state Root { [*] -> A; state A { during { x = 10 / d; } } }
    """
    result = solve_bmc_property(_formula(model, 'check reach <= 1: active("Root.A");'))

    # Dividing by a variable is outside linear arithmetic, so the whole call,
    # including the runtime-safety check that found the error, stays shared.
    assert result.outcome == "runtime_error"
    assert result.solver_context == "shared"


@pytest.mark.parametrize("bad", ["none", "", "Fresh", True, 1, None])
def test_an_invalid_solver_context_is_rejected(bad) -> None:
    formula = _formula(LINEAR_MODEL, LINEAR_QUERY)

    with pytest.raises(BmcBuildError, match="solver_context"):
        solve_bmc_property(formula, solver_context=bad)
    with pytest.raises(BmcBuildError, match="solver_context"):
        check_runtime_safety(formula.core, solver_context=bad)


def test_a_failed_call_leaves_later_solves_unaffected() -> None:
    formula = _formula(LINEAR_MODEL, LINEAR_QUERY)
    before = solve_bmc_property(formula)
    with pytest.raises(BmcBuildError):
        solve_bmc_property(formula, solver_context="bad")
    after = solve_bmc_property(formula)

    assert context_module.current_owner() is None
    assert _witness(before) == _witness(after)


def test_solving_in_another_thread_gives_the_same_answer() -> None:
    formula = _formula(LINEAR_MODEL, LINEAR_QUERY)
    here = solve_bmc_property(formula)
    box = []
    thread = threading.Thread(target=lambda: box.append(solve_bmc_property(formula)))
    thread.start()
    thread.join()

    assert _witness(box[0]) == _witness(here)


@pytest.fixture()
def model_and_query(tmp_path):
    model_path = tmp_path / "machine.fcstm"
    query_path = tmp_path / "property.fbmcq"
    model_path.write_text(LINEAR_MODEL, encoding="utf-8")
    query_path.write_text(LINEAR_QUERY, encoding="utf-8")
    return str(model_path), str(query_path)


@pytest.mark.parametrize(
    ("extra_args", "expected"),
    [
        ([], "fresh"),
        (["--solver-context", "fresh"], "fresh"),
        (["--solver-context", "shared"], "shared"),
    ],
)
def test_the_command_records_where_the_query_was_solved(
    model_and_query, extra_args, expected
) -> None:
    model_path, query_path = model_and_query
    outcome = CliRunner().invoke(
        pyfcstmcli,
        ["bmc", "-i", model_path, "-q", query_path, "--json", *extra_args],
    )

    assert outcome.exit_code in (0, 1)
    assert json.loads(outcome.output)["result"]["solver_context"] == expected


def test_the_command_rejects_an_unknown_solver_context(model_and_query) -> None:
    model_path, query_path = model_and_query
    outcome = CliRunner().invoke(
        pyfcstmcli,
        ["bmc", "-i", model_path, "-q", query_path, "--solver-context", "other"],
    )

    assert outcome.exit_code == 2


def test_the_human_report_does_not_mention_the_solver_context(model_and_query) -> None:
    model_path, query_path = model_and_query
    outcome = CliRunner().invoke(
        pyfcstmcli, ["bmc", "-i", model_path, "-q", query_path, "--color", "never"]
    )

    assert "solver_context" not in outcome.output


def test_build_bmc_output_validates_the_solver_context(model_and_query) -> None:
    from pyfcstm.entry.base import ClickErrorException
    from pyfcstm.entry.bmc import build_bmc_output

    model_path, query_path = model_and_query
    text, _ = build_bmc_output(
        model_path, query_path, json_output=True, solver_context="shared"
    )
    assert json.loads(text)["result"]["solver_context"] == "shared"
    with pytest.raises(ClickErrorException, match="solver_context"):
        build_bmc_output(model_path, query_path, solver_context="bad")


def _count_line_events(call) -> int:
    """Count the line events the interrupt sweep can reach during one call."""
    return _run_with_interrupt(call, 0)[0]


def _run_with_interrupt(call, target):
    """Run ``call`` raising ``KeyboardInterrupt`` at the ``target``-th line event.

    Only line events inside the solve-context bookkeeping of
    ``pyfcstm/solver/context.py`` and ``pyfcstm/bmc/solver.py`` are counted.  ``target == 0`` injects nothing.
    """
    count = [0]
    names = {
        "wrapper",
        "declare",
        "current_owner",
        "isolated_owner",
        "__init__",
        "is_linear",
        "_core_fragment",
        "_property_fragment",
        "_without_cardinality",
        "_resolving_unsliced",
        "solver_context_in_use",
    }

    def local(frame, event, arg):
        if event == "line":
            count[0] += 1
            if count[0] == target:
                raise KeyboardInterrupt("injected")
        return local

    def tracer(frame, event, arg):
        code = frame.f_code
        filename = code.co_filename.replace("\\", "/")
        if code.co_name in names and filename.endswith(
            ("pyfcstm/solver/context.py", "pyfcstm/bmc/solver.py")
        ):
            return local
        return None

    interrupted = False
    # Put back whatever tracer was active (coverage installs one) afterwards.
    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        call()
    except KeyboardInterrupt:
        interrupted = True
    finally:
        sys.settrace(previous)
    return count[0], interrupted


def test_an_interrupt_at_any_bookkeeping_line_leaves_no_state_behind() -> None:
    formula = _formula(LINEAR_MODEL, UNSAT_QUERY)
    expected = solve_bmc_property(formula, infeasibility_explanation="proof")
    events = _count_line_events(
        lambda: solve_bmc_property(formula, infeasibility_explanation="proof")
    )
    assert events > 20

    for target in range(1, events + 1):
        _, interrupted = _run_with_interrupt(
            lambda: solve_bmc_property(formula, infeasibility_explanation="proof"),
            target,
        )
        assert interrupted, "target %d was not reached" % target
        # No owner survives the interrupted solve, and the next solve is
        # exactly the one an untouched process would have made.
        assert context_module.current_owner() is None
        again = solve_bmc_property(formula, infeasibility_explanation="proof")
        assert again.solver_context == "fresh"
        assert _without_timing(again.to_canonical()["feasibility"]) == (
            _without_timing(expected.to_canonical()["feasibility"])
        )
        assert _search_counters(again) == _search_counters(expected)


MODULO_MODEL = """
def int x = 0;
def int y = 5;
state Root {
    state A { during { x = x + 7; y = y - x; } }
    state B;
    [*] -> A;
    A -> B : if [x % 3 == 1 && y < 0];
}
"""


@pytest.mark.parametrize("profile", ["default", "logic", "tactic"])
def test_modulo_by_a_constant_is_linear_for_every_profile(profile) -> None:
    query = 'check reach <= 4: active("Root.B");'
    fresh = solve_bmc_property(_formula(MODULO_MODEL, query), solver_profile=profile)
    shared = solve_bmc_property(
        _formula(MODULO_MODEL, query), solver_profile=profile, solver_context="shared"
    )

    assert fresh.solver_context == "fresh"
    assert (fresh.status, fresh.outcome) == (shared.status, shared.outcome)


def test_malformed_arguments_are_rejected_without_solving() -> None:
    with pytest.raises(BmcBuildError):
        solve_bmc_property(object())
    with pytest.raises(BmcBuildError):
        check_runtime_safety(object())
    assert context_module.current_owner() is None


def test_a_hand_built_result_rejects_an_invalid_solver_context() -> None:
    from pyfcstm.bmc import BmcSolveResult

    formula = _formula(LINEAR_MODEL, LINEAR_QUERY)

    shared = BmcSolveResult(
        formula, "unknown", reason="stopped", solver_context="shared"
    )
    assert shared.solver_context == "shared"
    with pytest.raises(BmcBuildError, match="solver_context"):
        BmcSolveResult(formula, "unknown", reason="stopped", solver_context="elsewhere")
