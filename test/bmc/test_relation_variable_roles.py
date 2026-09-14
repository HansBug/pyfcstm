"""
Unit tests for BMC role-aware variable and dynamic-input semantics.

These tests pin the symbolic contract through the public engine surface:
per-cycle dynamic-input freedom, parameter constancy, concrete input
scenario pinning, witness decoding, and replay input accounting.
"""

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.witness import (
    decode_bmc_result_trace,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

_ROLE_MODEL = """
input int command;
param int gain = 2;
control int total = 0;
output int result = 0;

state Root {
    state Ready {
        enter { total = command; }
    }
    state Done;
    [*] -> Ready;
    Ready -> Done : if [command > gain] effect { result = command * gain; };
}
"""


def _core(model_text: str, query: str):
    model = load_state_machine_from_text(model_text)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(query))
    )
    return model, formula


def _frame_symbols(formula):
    import z3

    collected = []

    def walk(expr):
        if z3.is_const(expr) and expr.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            collected.append(expr)
            return
        for index in range(expr.num_args()):
            walk(expr.arg(index))

    walk(formula.solve_formula)
    return collected


def _symbol(symbols, prefix):
    matches = [item for item in symbols if str(item).startswith(prefix)]
    assert matches, "missing symbol %s" % prefix
    return matches[0]


def _core_expr(model_text: str, query: str):
    """Build the raw BMC core expression (no property objective)."""
    model = load_state_machine_from_text(model_text)
    built = build_bmc_core_formula(BmcEngine(model).prepare(query))
    return model, built.core


def test_dynamic_inputs_may_differ_across_cycles() -> None:
    """Two cycles may see different dynamic-input values."""
    import z3

    _, core_expr = _core_expr(_ROLE_MODEL, "check reach <= 2: terminated();")
    symbols = _frame_symbols_expr(core_expr)
    solver = z3.Solver()
    solver.add(core_expr)
    solver.add(_symbol(symbols, "I_0_command") != _symbol(symbols, "I_1_command"))
    assert solver.check() == z3.sat


def test_parameters_stay_constant_across_cycles() -> None:
    """Assumptions at different frames cannot assign different parameters."""
    _, formula = _core(
        _ROLE_MODEL,
        """
        init cold havoc { gain };
        assume at 0: gain == 2;
        assume at 1: gain == 3;
        check reach <= 2: active("Root.Done");
    """,
    )
    assert solve_bmc_property(formula).status == "unsat"


def _frame_symbols_expr(expr):
    import z3

    collected = []

    def walk(node):
        if z3.is_const(node) and node.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            collected.append(node)
            return
        for index in range(node.num_args()):
            walk(node.arg(index))

    walk(expr)
    return collected


def test_concrete_inputs_constrain_the_scenario() -> None:
    """Pinning per-cycle inputs through ``assume at`` fixes the outcome."""
    import z3

    _, formula = _core(
        _ROLE_MODEL,
        "assume at 0: command == 3;\nassume at 1: command == 5;\n"
        'check reach <= 2: active("Root.Done");',
    )
    symbols = _frame_symbols(formula)
    solver = z3.Solver()
    solver.add(formula.solve_formula)
    assert solver.check() == z3.sat
    model = solver.model()
    total = _symbol(symbols, "F_1_total")
    assert model.eval(total).as_long() == 3


def test_witness_decode_and_replay_carry_role_metadata() -> None:
    """Decoded witnesses expose parameters, inputs, and read provenance."""
    model, formula = _core(
        _ROLE_MODEL,
        "assume at 0: command == 3;\nassume at 1: command == 5;\n"
        'check reach <= 2: active("Root.Done");',
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    assert witness.initial["parameters"] == {"gain": 2}
    assert "command" not in witness.frames[0].vars
    assert "gain" not in witness.frames[0].vars
    assert witness.steps[0].inputs == {"command": 3}
    assert witness.steps[1].inputs == {"command": 5}
    assert witness.steps[0].input_reads == ("command",)
    replay = replay_bmc_witness(model, witness)
    assert replay.ok
    assert replay.runtime_trace.steps[1].inputs == {"command": 5}


def test_forged_step_inputs_are_reported_by_replay() -> None:
    """Replay flags forged inputs on post-termination absorb steps."""
    import dataclasses as dc

    model, formula = _core(
        """
        input int finish;
        output int result = 0;
        state Root {
            state Ready;
            [*] -> Ready;
            Ready -> [*] : if [finish > 0] effect { result = finish; };
        }
        """,
        "assume at 0: finish == 1;\ncheck reach <= 3: terminated();",
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    absorb_index = next(
        index for index, step in enumerate(witness.steps) if step.case_kind == "absorb"
    )
    from pyfcstm.bmc import BmcBuildError

    with pytest.raises(BmcBuildError, match="absorb steps must have empty"):
        dc.replace(witness.steps[absorb_index], inputs={"finish": 7})
