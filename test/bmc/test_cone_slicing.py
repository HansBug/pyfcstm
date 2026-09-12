"""Cone reduction preserves observable execution and scenario feasibility."""

import pytest
import z3

from pyfcstm.bmc import (
    BmcBuildError,
    BmcOptions,
    compile_bmc_query,
    decode_bmc_result_trace,
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest


def _compile(source, query, enabled=True):
    machine = load_state_machine_from_text(source)
    return machine, compile_bmc_query(
        machine, query, options=BmcOptions(cone_slicing=enabled)
    )


def _dag_size(expr):
    seen, pending = set(), [expr]
    while pending:
        node = pending.pop()
        if node.get_id() not in seen:
            seen.add(node.get_id())
            pending.extend(node.children())
    return len(seen)


_OUTPUTS = """
def int ticks = 0;
def int output = 3;
def int other = 5;
state Root {
    enter { ticks = ticks + 1; output = ticks * 17; other = output + 9; }
    during { ticks = ticks + 1; output = output + ticks; other = other * 2; }
}
"""


def test_unread_outputs_are_removed_and_public_decoders_fill_every_frame():
    query = "check reach <= 4: ticks == 4;"
    machine, full = _compile(_OUTPUTS, query, False)
    _, sliced = _compile(_OUTPUTS, query)
    assert sliced.core.cone_slice.dropped_variables == ("output", "other")
    assert _dag_size(sliced.core.core) < _dag_size(full.core.core)
    assert z3.eq(sliced.core.initial_formula, full.core.initial_formula)
    full_result, result = solve_bmc_property(full), solve_bmc_property(sliced)
    full_trace = decode_bmc_result_trace(full_result)
    for trace in (
        decode_bmc_result_trace(result),
        decode_bmc_witness(result.formula, result.model),
    ):
        assert [frame.vars for frame in trace.frames] == [
            frame.vars for frame in full_trace.frames
        ]
        assert replay_bmc_witness(machine, trace).ok
    assert result.to_canonical()["cone_slicing"]["dropped_variables"] == [
        "output",
        "other",
    ]


def test_empty_first_branch_still_blocks_else_and_retains_condition_inputs():
    source = """
    def int gate = 1;
    def int kept = 0;
    def int unused = 0;
    state Root { enter { if [gate > 0] { unused = 1; } else { kept = 7; } } }
    """
    _, formula = _compile(source, "check reach <= 1: kept == 7;")
    assert formula.core.cone_slice.dropped_variables == ("unused",)
    assert solve_bmc_property(formula).status == "unsat"


@pytest.mark.parametrize(
    "property_text",
    [
        'check reach <= 3: active("Root.B");',
        "check invariant <= 3: total >= 0;",
    ],
)
def test_unread_division_preserves_infeasible_scenario_even_without_sat_witness(
    property_text,
):
    source = """
    def int total = 5;
    def int count = 0;
    def int mean = 0;
    def int telemetry = 0;
    state Root {
        [*] -> A;
        state A;
        state B { enter { mean = total / count; telemetry = 17; } }
        A -> B;
    }
    """
    _, formula = _compile(source, property_text)
    assert formula.core.cone_slice.dropped_variables == ("telemetry",)
    result = solve_bmc_property(formula)
    assert (result.status, result.property_satisfied, result.outcome) == (
        "unsat",
        None,
        "scenario_infeasible",
    )


def test_query_references_and_guard_dependencies_are_retained():
    source = """
    def int source = 1;
    def int guard_value = 0;
    def int constraint_value = 3;
    def int unused = 0;
    state Root {
        [*] -> A;
        state A { enter { guard_value = source + 1; unused = 4; } }
        state B;
        A -> B : if [guard_value > 0];
    }
    """
    _, formula = _compile(
        source,
        'init cold where constraint_value == 3; check reach <= 2: active("Root.B");',
    )
    assert formula.core.cone_slice.dropped_variables == ("unused",)


def test_abstract_actions_skip_slicing():
    machine, formula = _compile(
        "def int output = 0; state Root { enter abstract Observe; }",
        'check reach <= 1: active("Root");',
    )
    assert formula.core.cone_slice.skipped_reason == "abstract_actions"
    assert formula.core.cone_slice.dropped_variables == ()
    result = solve_bmc_property(formula)
    assert replay_bmc_witness(machine, decode_bmc_result_trace(result)).ok


@pytest.mark.parametrize("value", [None, 0, 1, "true", []])
def test_cone_option_requires_boolean(value):
    with pytest.raises(BmcBuildError, match="cone_slicing"):
        BmcOptions(cone_slicing=value)


def test_cone_option_is_off_by_default():
    assert BmcOptions().to_canonical()["cone_slicing"] is False
