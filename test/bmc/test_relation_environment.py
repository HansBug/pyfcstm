"""Environment-assumption tests for BMC relation formulas."""

from __future__ import annotations

import re

import pytest
import z3

from pyfcstm.bmc import BmcEngine, UnsupportedBmcQuery, build_bmc_core_formula
from pyfcstm.model import load_state_machine_from_text


def _solver(*constraints):
    solver = z3.Solver()
    solver.add(*constraints)
    return solver


def _event_model():
    return load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A {
                event Ping;
            }
            state B {
                event Ping;
            }
            [*] -> A;
        }
        """
    )


@pytest.mark.unittest
def test_frame_assumptions_lower_always_to_all_frames_and_at_to_one_frame() -> None:
    """Frame assumptions are lowered over the intended frame set."""
    model = load_state_machine_from_text("def int x = 0; state Root;")
    context = BmcEngine(model).prepare(
        "assume always: x >= 0;\n"
        'assume at 1: var("x") <= 3;\n'
        "check reach <= 1: terminated();"
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core, core.symbols.frame_var(0, "x") < 0).check() == z3.unsat
    assert _solver(core.core, core.symbols.frame_var(1, "x") < 0).check() == z3.unsat
    assert _solver(core.core, core.symbols.frame_var(1, "x") > 3).check() == z3.unsat


@pytest.mark.unittest
def test_event_not_equal_is_binder_normalized_to_false() -> None:
    """Event ``!= true`` assumptions constrain the selected event to false."""
    context = BmcEngine(_event_model()).prepare(
        'assume event("Root.A.Ping", 0) != true;\ncheck reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)
    event_a = core.symbols.event_input(0, "Root.A.Ping")

    assert _solver(core.core, event_a).check() == z3.unsat
    assert _solver(core.core, z3.Not(event_a)).check() == z3.sat


@pytest.mark.unittest
def test_default_event_pool_allows_multiple_events_in_same_cycle() -> None:
    """No implicit at-most-one is added when the query does not request it."""
    context = BmcEngine(_event_model()).prepare(
        'assume event("Root.A.Ping", 0) == true;\n'
        'assume event("Root.B.Ping", 0) == true;\n'
        'check reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.sat


@pytest.mark.unittest
def test_user_event_cardinality_at_most_one_is_per_cycle() -> None:
    """Only user-declared cardinality introduces per-cycle event exclusion."""
    context = BmcEngine(_event_model()).prepare(
        'assume event("Root.A.Ping", 0) == true;\n'
        'assume event("Root.B.Ping", 0) == true;\n'
        "assume events cardinality at_most_one {\n"
        '    "Root.A.Ping",\n'
        '    "Root.B.Ping"\n'
        "};\n"
        'check reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.unsat


@pytest.mark.unittest
def test_same_short_name_events_remain_distinct_full_paths() -> None:
    """An assumption on ``A.Ping`` does not constrain the separate ``B.Ping`` input."""
    context = BmcEngine(_event_model()).prepare(
        'assume event("Root.A.Ping", 0) == true;\ncheck reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert (
        _solver(core.core, z3.Not(core.symbols.event_input(0, "Root.A.Ping"))).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, core.symbols.event_input(0, "Root.B.Ping")).check() == z3.sat
    )


@pytest.mark.unittest
def test_event_selector_star_and_ranges_lower_to_each_selected_cycle() -> None:
    """Event selectors are expanded by the binder and lowered pointwise."""
    context = BmcEngine(_event_model()).prepare(
        'assume event("Root.A.Ping", 0..1) == true;\n'
        'assume event("Root.B.Ping", *) == false;\n'
        'check reach <= 3: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert (
        _solver(core.core, z3.Not(core.symbols.event_input(0, "Root.A.Ping"))).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, z3.Not(core.symbols.event_input(1, "Root.A.Ping"))).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, z3.Not(core.symbols.event_input(2, "Root.A.Ping"))).check()
        == z3.sat
    )
    for step in range(3):
        assert (
            _solver(core.core, core.symbols.event_input(step, "Root.B.Ping")).check()
            == z3.unsat
        )


@pytest.mark.unittest
def test_event_cardinality_any_is_noop_even_with_multiple_true_events() -> None:
    """The explicit ``any`` cardinality policy adds no mutual exclusion."""
    context = BmcEngine(_event_model()).prepare(
        "assume events cardinality any;\n"
        'assume event("Root.A.Ping", 0) == true;\n'
        'assume event("Root.B.Ping", 0) == true;\n'
        'check reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.sat


@pytest.mark.unittest
def test_frame_assumption_expression_matrix_lowers_supported_terms() -> None:
    """Frame predicates exercise numeric, boolean, ufunc, and domain lowering."""
    model = load_state_machine_from_text(
        "def int x = 4; def int y = 2; def float f = 1.5; state Root;"
    )
    context = BmcEngine(model).prepare(
        "assume always: ((x + 2 - y * 3) <= 0) && ((x / y) == 2) "
        "&& ((x % y) == 0) && ((x ** y) >= 16);\n"
        "assume always: ((x > y) ? true : false);\n"
        "assume always: ((x > y) ? x : y) == x;\n"
        "assume always: abs(-x) == x && sign(-x) == -1;\n"
        "assume always: floor(f) <= f && ceil(f) >= f && trunc(f) == 1 "
        "&& round(f) == 2 && sqrt(x) >= 2;\n"
        "assume always: pi > 3 && E > 2 && tau > 6;\n"
        "assume always: (+x) == x && cycle >= 0 && 1.5 <= f && x < 5 && x != y;\n"
        "assume always: trunc(x) == x;\n"
        "assume always: (true && !false) && (true || false) && (true => true) "
        "&& (true xor false) && (true iff true) && (true == true) "
        "&& (true != false);\n"
        "check reach <= 1: terminated();"
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.sat
    assert "Sqrt" in str(core.environment_formula) or "**(1/2)" in str(
        core.environment_formula
    )
    assert "!=" in str(core.environment_formula)


@pytest.mark.unittest
def test_frame_assumptions_lower_active_and_terminated_atoms() -> None:
    """Frame predicates can constrain active and terminated frame states."""
    active_model = load_state_machine_from_text("state Root { state A; [*] -> A; }")
    active_context = BmcEngine(active_model).prepare(
        'init state("Root.A");\n'
        'assume at 0: active("Root.A");\n'
        'assume at 1: active("Root.A");\n'
        'check reach <= 1: active("Root.A");'
    )
    active_core = build_bmc_core_formula(active_context)

    terminated_context = BmcEngine(load_state_machine_from_text("state Root;")).prepare(
        "init terminated;\n"
        "assume at 0: terminated();\n"
        "assume at 1: terminated();\n"
        "check reach <= 1: terminated();"
    )
    terminated_core = build_bmc_core_formula(terminated_context)

    assert _solver(active_core.core).check() == z3.sat
    assert _solver(terminated_core.core).check() == z3.sat
    assert (
        _solver(
            active_core.core,
            active_core.symbols.frame_state(0) != active_core.symbols.frame_state(1),
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_frame_assumption_definedness_constraints_can_make_core_unsat() -> None:
    """Runtime-definedness constraints are part of ``ENV_N``."""
    model = load_state_machine_from_text("def int x = 4; def int y = 0; state Root;")
    context = BmcEngine(model).prepare(
        "assume always: (x / y) >= 0;\ncheck reach <= 1: terminated();"
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.unsat


@pytest.mark.unittest
def test_frame_assumption_logical_short_circuit_guards_definedness() -> None:
    """Skipped logical operands do not add runtime-definedness constraints."""
    model = load_state_machine_from_text("def int x = 0; state Root;")

    for query in (
        'assume always: true || (1 / x > 0);\ncheck reach <= 1: active("Root");',
        'assume always: !(false && (1 / x > 0));\ncheck reach <= 1: active("Root");',
        'assume always: x == 0 || (1 / x > 0);\ncheck reach <= 1: active("Root");',
        'assume always: !(x != 0 && (1 / x > 0));\ncheck reach <= 1: active("Root");',
    ):
        core = build_bmc_core_formula(BmcEngine(model).prepare(query))
        assert _solver(core.core).check() == z3.sat

    for query in (
        'assume always: false || (1 / x > 0);\ncheck reach <= 1: active("Root");',
        'assume always: true && (1 / x > 0);\ncheck reach <= 1: active("Root");',
        'assume always: x != 0 || (1 / x > 0);\ncheck reach <= 1: active("Root");',
        'assume always: !(x == 0 && (1 / x > 0));\ncheck reach <= 1: active("Root");',
    ):
        core = build_bmc_core_formula(BmcEngine(model).prepare(query))
        assert _solver(core.core).check() == z3.unsat


@pytest.mark.unittest
def test_frame_assumption_conditional_guards_branch_definedness() -> None:
    """Skipped conditional branches do not constrain runtime-definedness."""
    model = load_state_machine_from_text("def int x = 0; state Root;")

    for query in (
        "assume always: ((true) ? 1 : (1 / x)) == 1;\n"
        'check reach <= 1: active("Root");',
        "assume always: ((false) ? (1 / x) : 1) == 1;\n"
        'check reach <= 1: active("Root");',
        "assume always: (true) ? true : (1 / x > 0);\n"
        'check reach <= 1: active("Root");',
        "assume always: (false) ? (1 / x > 0) : true;\n"
        'check reach <= 1: active("Root");',
    ):
        core = build_bmc_core_formula(BmcEngine(model).prepare(query))
        assert _solver(core.core).check() == z3.sat

    for query in (
        "assume always: ((false) ? 1 : (1 / x)) == 1;\n"
        'check reach <= 1: active("Root");',
        "assume always: (false) ? true : (1 / x > 0);\n"
        'check reach <= 1: active("Root");',
    ):
        core = build_bmc_core_formula(BmcEngine(model).prepare(query))
        assert _solver(core.core).check() == z3.unsat


@pytest.mark.unittest
def test_unsupported_frame_expression_reports_structured_bmc_error() -> None:
    """Unsupported Z3 operations do not leak raw Python or Z3 exceptions."""
    model = load_state_machine_from_text("def int x = 4; def int y = 2; state Root;")
    context = BmcEngine(model).prepare(
        "assume always: (x & y) == 0;\ncheck reach <= 1: terminated();"
    )

    with pytest.raises(UnsupportedBmcQuery, match="unsupported for operator &"):
        build_bmc_core_formula(context)


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("expression", "operator"),
    [
        ("(x | y) == 0", "|"),
        ("(x ^ y) == 0", "^"),
        ("(x << y) == 0", "<<"),
        ("(x >> y) == 0", ">>"),
        ("(f % 1.0) == 0", "%"),
    ],
)
def test_unsupported_numeric_operator_matrix_reports_structured_bmc_error(
    expression,
    operator,
) -> None:
    """Unsupported numeric operators fail with structured BMC diagnostics."""
    model = load_state_machine_from_text(
        "def int x = 4; def int y = 2; def float f = 1.5; state Root;"
    )
    context = BmcEngine(model).prepare(
        "assume always: %s;\ncheck reach <= 1: terminated();" % expression
    )

    with pytest.raises(
        UnsupportedBmcQuery,
        match="unsupported for operator %s" % re.escape(operator),
    ):
        build_bmc_core_formula(context)


@pytest.mark.unittest
def test_unsupported_ufunc_reports_structured_bmc_error() -> None:
    """Supported parser ufuncs without relation lowering fail explicitly."""
    model = load_state_machine_from_text("def int x = 4; state Root;")
    context = BmcEngine(model).prepare(
        "assume always: sin(x) >= 0;\ncheck reach <= 1: terminated();"
    )

    with pytest.raises(UnsupportedBmcQuery, match="unsupported function 'sin'"):
        build_bmc_core_formula(context)
