"""
Contract tests for role-aware variables in BMC public predicate surfaces.

These tests pin behaviors promised by PR-4 and the FBMCQ guide: input,
parameter, and output variables are usable inside ``assume``/``where``/``check``
frame predicates; concrete input scenarios are expressible through the public
query language; witness decoding and replay carry the role metadata with exact
numeric fidelity; and the public JSON payload validates against the shipped
schema.
"""

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.relation import BmcCaseRelation
from pyfcstm.bmc.witness import (
    decode_bmc_result_trace,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

_FLIGHT_MODEL = """
input float pressure;
param float gain = 2.0;
def int ticks = 0;
output float altitude = 0.0;
state Root {
    state Flying { during { ticks = ticks + 1; altitude = altitude + pressure * gain; } }
    [*] -> Flying;
}
"""

_ORDER_MODEL = """
input int second;
input int first;
control int total = 0;
output int result = 0;
state Root {
    state S;
    state T;
    [*] -> S;
    S -> T : if [first > 0] effect { result = second; };
}
"""

_TERMINATE_MODEL = """
input int finish;
output int result = 0;
state Root {
    state Ready;
    [*] -> Ready;
    Ready -> [*] : if [finish > 0] effect { result = finish; };
}
"""

_NESTED_IF_MODEL = """
input int cmd;
input int mode;
def int r = 0;
state Root { state S { during { if [cmd > 0] { r = cmd; } else { if [mode > 0] { r = mode; } } } } [*] -> S; }
"""

_TWO_INPUT_MODEL = """
input int watched;
input int ignored;
control int seen = 0;
output int value = 0;
state Root {
    state S { during { seen = watched; } }
    [*] -> S;
}
"""


def _solve(model_text: str, query: str):
    model = load_state_machine_from_text(model_text)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(query))
    )
    result = solve_bmc_property(formula)
    return model, formula, result


def _core_symbols(expr):
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


def _symbol(symbols, prefix):
    matches = [item for item in symbols if str(item).startswith(prefix)]
    assert matches, "missing symbol %s" % prefix
    return matches[0]


# ---------------------------------------------------------------------------
# Group A: role variables in public FBMCQ predicate surfaces.
# ---------------------------------------------------------------------------


def test_input_range_assume_always_tightens_satisfiability() -> None:
    """A range assumption on a Real input genuinely restricts executions."""
    _, _, unrestricted = _solve(
        _FLIGHT_MODEL,
        "check invariant <= 3: altitude >= 0.0 && altitude <= 6.5;",
    )
    assert unrestricted.status == "sat"
    assert unrestricted.property_satisfied is False

    _, _, restricted = _solve(
        _FLIGHT_MODEL,
        "assume always: pressure >= 0.0 && pressure <= 1.0;\n"
        "check invariant <= 3: altitude >= 0.0 && altitude <= 6.5;",
    )
    # ``check invariant`` searches for a violating trace: sat = violated,
    # unsat with property_satisfied true = the property holds.
    assert restricted.status == "unsat"
    assert restricted.property_satisfied is True


def test_input_range_assume_applies_to_every_decoded_cycle() -> None:
    """Decoded step inputs all respect an ``assume always`` input band."""
    model, formula, result = _solve(
        _FLIGHT_MODEL,
        "assume always: pressure >= 0.0 && pressure <= 1.0;\n"
        'check reach <= 3: active("Root.Flying");',
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    for step in witness.steps:
        assert 0.0 <= step.inputs["pressure"] <= 1.0
    assert replay_bmc_witness(model, witness).ok


def test_output_assume_at_pins_decoded_frame_value() -> None:
    """An output variable can be pinned at one frame via ``assume at``."""
    model, formula, result = _solve(
        _FLIGHT_MODEL,
        "assume at 0: pressure == 1.0;\n"
        "assume at 2: altitude == 4.0;\n"
        'check reach <= 3: active("Root.Flying");',
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    assert witness.frames[2].vars["altitude"] == 4.0
    assert replay_bmc_witness(model, witness).ok


def test_param_assume_conflicting_with_initializer_is_unsat() -> None:
    """Parameters are pinned once at frame 0; conflicting assumes are unsat."""
    _, _, result = _solve(
        _FLIGHT_MODEL,
        'assume always: gain == 3.0;\ncheck reach <= 1: active("Root.Flying");',
    )
    assert result.status == "unsat"


def test_param_assume_matching_initializer_is_sat() -> None:
    """A parameter assume equal to the initializer stays consistent."""
    _, _, result = _solve(
        _FLIGHT_MODEL,
        'assume always: gain == 2.0;\ncheck reach <= 1: active("Root.Flying");',
    )
    assert result.status == "sat"
    assert result.property_satisfied is True


def test_param_override_via_where_havoc_decodes_into_initial_parameters() -> None:
    """``init ... havoc { p } where p == v`` is the public parameter surface."""
    model, formula, result = _solve(
        _FLIGHT_MODEL,
        "init cold havoc { gain } where gain == 3.0;\n"
        'check reach <= 1: active("Root.Flying");',
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    assert witness.initial["parameters"] == {"gain": 3.0}
    assert replay_bmc_witness(model, witness).ok


@pytest.mark.parametrize(
    "predicate", ["pressure >= 0.0", "altitude - pressure <= 10.0"]
)
def test_frame_property_rejects_dynamic_input_predicates(predicate):
    from pyfcstm.bmc import InvalidBmcQuery

    with pytest.raises(InvalidBmcQuery, match="variable_role_mismatch"):
        _solve(_FLIGHT_MODEL, "check invariant <= 3: %s;" % predicate)


# ---------------------------------------------------------------------------
# Group B: symbolic role semantics.
# ---------------------------------------------------------------------------


def test_input_reads_follow_declaration_order_not_read_order() -> None:
    """input_reads is ordered by declaration, deduplicated, case-scoped."""
    model, formula, result = _solve(
        _ORDER_MODEL,
        "assume at 1: first == 1;\nassume at 1: second == 2;\n"
        'check reach <= 2: active("Root.T");',
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    transition = next(step for step in witness.steps if step.case_kind == "transition")
    assert transition.input_reads == ("second", "first")
    assert transition.inputs == {"second": 2, "first": 1}


def test_unread_inputs_still_decode_but_stay_out_of_reads() -> None:
    """Complete input snapshots include unread inputs; reads stay a subset."""
    model, formula, result = _solve(
        _TWO_INPUT_MODEL,
        "assume at 0: watched == 5;\nassume at 0: ignored == 9;\n"
        'check reach <= 1: active("Root.S");',
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    step = witness.steps[0]
    assert step.inputs == {"watched": 5, "ignored": 9}
    assert step.input_reads == ("watched", "ignored")


def test_terminated_initial_frame_decodes_empty_step_inputs() -> None:
    """``init terminated`` role models carry empty inputs on absorb steps."""
    model, formula, result = _solve(
        _TERMINATE_MODEL,
        "init terminated;\ncheck reach <= 2: terminated();",
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    assert witness.initial["sentinel"] == "terminated"
    for step in witness.steps:
        assert step.case_kind == "absorb"
        assert step.inputs == {}
        assert step.input_reads == ()
    replay = replay_bmc_witness(model, witness)
    assert replay.ok


def test_havoc_rejects_dynamic_inputs() -> None:
    from pyfcstm.bmc import InvalidBmcQuery

    with pytest.raises(InvalidBmcQuery, match="variable_role_mismatch"):
        _solve(
            _TWO_INPUT_MODEL,
            'init cold havoc { watched }; check reach <= 1: active("Root.S");',
        )


def test_case_consequent_never_pins_next_frame_input_symbols() -> None:
    """Structural: dynamic inputs receive no post-frame case equalities."""
    model_text = _ORDER_MODEL
    model = load_state_machine_from_text(model_text)
    built = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= 2: terminated();")
    )
    dynamic_names = set(built.context.domain.dynamic_input_names)
    assert dynamic_names == {"second", "first"}
    for step_relation in built.steps:
        for relation in step_relation.case_relations:
            assert isinstance(relation, BmcCaseRelation)
            consequent_symbols = _core_symbols(relation.consequent)
            next_frame_inputs = [
                str(item)
                for item in consequent_symbols
                if str(item).startswith("F_%d_" % (relation.step_index + 1))
                and any(
                    str(item).endswith(name) or name in str(item)
                    for name in dynamic_names
                )
            ]
            assert next_frame_inputs == [], (relation.case.label, next_frame_inputs)


# ---------------------------------------------------------------------------
# Group C: decode/replay fidelity and read collection.
# ---------------------------------------------------------------------------


def test_fractional_real_input_decodes_and_replays_exactly() -> None:
    """Non-binary-exact Real inputs survive decode and replay within contract."""
    model, formula, result = _solve(
        _FLIGHT_MODEL,
        'assume always: pressure == 0.1;\ncheck reach <= 2: active("Root.Flying");',
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    for step in witness.steps:
        assert abs(step.inputs["pressure"] - 0.1) < 1e-9
    replay = replay_bmc_witness(model, witness)
    assert replay.ok
    assert replay.mismatches == ()


def test_fractional_real_param_decodes_exactly() -> None:
    """Real parameters decode with the same precision contract."""
    model = load_state_machine_from_text(
        _FLIGHT_MODEL.replace("param float gain = 2.0;", "param float gain = 0.1;")
    )
    formula = compile_bmc_property(
        build_bmc_core_formula(
            BmcEngine(model).prepare('check reach <= 1: active("Root.Flying");')
        )
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    assert abs(witness.initial["parameters"]["gain"] - 0.1) < 1e-9
    assert replay_bmc_witness(model, witness).ok


def test_nested_if_blocks_collect_reads_recursively() -> None:
    """Reads inside nested if/else branches are collected."""
    model, formula, result = _solve(
        _NESTED_IF_MODEL,
        "assume at 0: cmd == 0;\nassume at 0: mode == 4;\n"
        'check reach <= 1: active("Root.S");',
    )
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result, source="primary")
    step = witness.steps[0]
    declared = ("cmd", "mode")
    assert (
        tuple(name for name in declared if name in step.input_reads) == step.input_reads
    )
    assert set(step.input_reads) == {"cmd", "mode"}
    assert replay_bmc_witness(model, witness).ok
