"""Role lifetimes and abstract-call consistency through the public BMC API."""

import pytest
import z3

from pyfcstm.bmc import BmcEngine, BmcBuildError, InvalidBmcQuery, compile_bmc_query
from pyfcstm.bmc.relation import BmcTraceSymbols
from pyfcstm.bmc.witness import (
    solve_bmc_property,
    decode_bmc_result_trace,
    replay_bmc_witness,
)
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest


def test_symbol_lifetimes_are_disjoint():
    model = load_state_machine_from_text(
        "control int count = 0; input int command; param int gain = 2; "
        "output float result = 0.0; state Root;"
    )
    symbols = BmcTraceSymbols.allocate(
        BmcEngine(model).prepare('check reach <= 3: active("Root");').domain
    )
    assert len(symbols.frame_vars) == 4
    assert all(set(frame) == {"count", "result"} for frame in symbols.frame_vars)
    assert len(symbols.step_inputs) == 3
    assert all(set(step) == {"command"} for step in symbols.step_inputs)
    assert set(symbols.parameters) == {"gain"}
    solver = z3.Solver()
    solver.add(symbols.step_input(0, "command") != symbols.step_input(1, "command"))
    assert solver.check() == z3.sat
    assert symbols.parameter("gain").eq(symbols.parameters["gain"])
    with pytest.raises(BmcBuildError, match="Unknown frame variable"):
        symbols.frame_var(0, "command")
    with pytest.raises(BmcBuildError, match="step index out of range"):
        symbols.step_input(3, "command")


@pytest.mark.parametrize("reference", ["sensor", 'var("sensor")'])
def test_frame_property_rejects_dynamic_input(reference):
    model = load_state_machine_from_text("input int sensor; state Root;")
    with pytest.raises(InvalidBmcQuery, match="variable_role_mismatch"):
        compile_bmc_query(model, "check reach <= 1: %s == 1;" % reference)


def test_parameter_override_and_call_predicate_share_global_symbol():
    model = load_state_machine_from_text(
        "param int gain = 2; input int sensor; state Root { enter abstract Observe; }"
    )
    formula = compile_bmc_query(
        model,
        "init cold havoc { gain } where gain == 3; "
        'check reach <= 1: called("Root.Observe", where gain == 3);',
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    trace = decode_bmc_result_trace(result, source="primary")
    assert trace.initial["parameters"] == {"gain": 3}
    assert trace.steps[0].abstract_calls[0].snapshot == {}
    assert replay_bmc_witness(model, trace).ok


def test_parameter_cannot_change_between_frames():
    model = load_state_machine_from_text("param int gain = 2; state Root;")
    formula = compile_bmc_query(
        model,
        """
        init cold havoc { gain };
        assume at 0: gain == 3;
        assume at 1: gain == 4;
        check reach <= 2: active("Root");
    """,
    )
    assert solve_bmc_property(formula).status == "unsat"


@pytest.mark.parametrize("name", ["count", "result"])
def test_unwritten_persistent_variable_is_preserved(name):
    model = load_state_machine_from_text(
        "control int count = 1; output int result = 2; input int command; state Root;"
    )
    formula = compile_bmc_query(model, 'check reach <= 2: active("Root");')
    core = formula.core
    solver = z3.Solver()
    solver.add(
        core.core, core.symbols.frame_var(0, name) != core.symbols.frame_var(1, name)
    )
    assert solver.check() == z3.unsat
    solver = z3.Solver()
    solver.add(
        core.core,
        core.symbols.step_input(0, "command") != core.symbols.step_input(1, "command"),
    )
    assert solver.check() == z3.sat


@pytest.mark.parametrize("reference", ["sensor", 'var("sensor")'])
def test_input_assumption_cannot_reference_last_frame(reference):
    model = load_state_machine_from_text("input int sensor; state Root;")
    with pytest.raises(InvalidBmcQuery, match="input_step_out_of_range"):
        compile_bmc_query(
            model, 'assume at 2: %s == 1; check reach <= 2: active("Root");' % reference
        )


def test_all_roles_share_assumption_syntax_with_distinct_lifetimes():
    model = load_state_machine_from_text(
        "control int count = 1; output int result = 2; input int command; "
        "param int gain = 3; state Root;"
    )
    formula = compile_bmc_query(
        model,
        """
        assume always: command >= count && command < result * gain;
        assume at 0: command == 2;
        assume at 1: var("command") == 4;
        assume at 2: count == 1 && result == 2 && gain == 3;
        check reach <= 2: active("Root");
    """,
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    trace = decode_bmc_result_trace(result, source="primary")
    assert [step.inputs for step in trace.steps] == [{"command": 2}, {"command": 4}]
    assert all(step.input_reads == ("command",) for step in trace.steps)
    assert replay_bmc_witness(model, trace).ok


def test_fallback_records_input_read_by_rejected_transition():
    model = load_state_machine_from_text("""
        input int sensor;
        state Root { state A; state B; [*] -> A; A -> B : if [sensor > 0]; }
    """)
    formula = compile_bmc_query(
        model, 'init state("Root.A"); check exists_always <= 2: active("Root.A");'
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    trace = decode_bmc_result_trace(result, source="primary")
    assert all(step.case_kind == "fallback" for step in trace.steps)
    assert all(step.input_reads == ("sensor",) for step in trace.steps)
    assert replay_bmc_witness(model, trace).ok


@pytest.mark.parametrize("role", ["control", "output", "param"])
def test_noninput_roles_can_be_assumed_at_final_frame(role):
    model = load_state_machine_from_text("%s int value = 3; state Root;" % role)
    formula = compile_bmc_query(
        model, 'assume at 1: var("value") == 3; check reach <= 1: active("Root");'
    )
    assert solve_bmc_property(formula).status == "sat"


@pytest.mark.parametrize(
    "query",
    [
        "init cold where sensor == 1; check reach <= 1: true;",
        "init cold havoc { sensor }; check reach <= 1: true;",
        "check reach <= 1: called(where sensor == 1);",
    ],
)
def test_input_is_rejected_outside_assumptions(query):
    model = load_state_machine_from_text(
        "input int sensor; state Root { enter abstract Observe; }"
    )
    with pytest.raises(InvalidBmcQuery, match="variable_role_mismatch"):
        compile_bmc_query(model, query)


def test_havoc_all_covers_only_initializable_roles():
    model = load_state_machine_from_text(
        "control int c = 1; input int i; param int p = 2; output int o = 3; state Root;"
    )
    context = BmcEngine(model).prepare("init cold havoc *; check reach <= 1: true;")
    assert context.bound_query.initial.havoc_names(context.domain) == ("c", "p", "o")
    assert [v.time_domain for v in context.domain.variables] == [
        "frame",
        "step",
        "trace",
        "frame",
    ]


@pytest.mark.parametrize("index", [-1, 2, True, 1.5, "0"])
def test_step_input_accessor_rejects_invalid_index(index):
    model = load_state_machine_from_text("input int sensor; state Root;")
    symbols = BmcTraceSymbols.allocate(
        BmcEngine(model).prepare("check reach <= 2: true;").domain
    )
    with pytest.raises(BmcBuildError, match="step index out of range"):
        symbols.step_input(index, "sensor")


def test_symbol_bundle_validates_role_partitions():
    from dataclasses import replace

    model = load_state_machine_from_text(
        "input int sensor; param int gain = 2; state Root;"
    )
    symbols = BmcTraceSymbols.allocate(
        BmcEngine(model).prepare("check reach <= 1: true;").domain
    )
    with pytest.raises(BmcBuildError, match="step_inputs must contain bound mappings"):
        replace(symbols, step_inputs=())
    with pytest.raises(BmcBuildError, match="exactly the dynamic input names"):
        replace(symbols, step_inputs=({},))
    with pytest.raises(BmcBuildError, match="exactly the static input names"):
        replace(symbols, parameters={})
    with pytest.raises(BmcBuildError, match="Unknown dynamic input"):
        symbols.step_input(0, "gain")
    with pytest.raises(BmcBuildError, match="Unknown parameter"):
        symbols.parameter("sensor")
    canonical = symbols.to_canonical()
    assert set(canonical["parameters"]) == {"gain"}
    assert set(canonical["step_inputs"][0]) == {"sensor"}
    assert canonical["frame_vars"] == [{}, {}]


@pytest.mark.parametrize(
    "changes,path",
    [
        ({"inputs": {}}, "steps\\[0\\].inputs"),
        ({"inputs": {"other": 1}}, "steps\\[0\\].inputs"),
        ({"inputs": {"sensor": 1.5}}, "must be an int"),
    ],
)
def test_replay_rejects_incomplete_or_invalid_input_snapshot(changes, path):
    from dataclasses import replace

    model = load_state_machine_from_text("input int sensor; state Root;")
    result = solve_bmc_property(
        compile_bmc_query(model, 'check reach <= 1: active("Root");')
    )
    witness = decode_bmc_result_trace(result, source="primary")
    forged = replace(witness, steps=(replace(witness.steps[0], **changes),))
    with pytest.raises(BmcBuildError, match=path):
        replay_bmc_witness(model, forged)


@pytest.mark.parametrize(
    "parameters", [{}, {"gain": 2.5}, {"gain": True}, {"gain": float("inf")}]
)
def test_replay_rejects_incomplete_or_invalid_parameters(parameters):
    from dataclasses import replace

    model = load_state_machine_from_text("param int gain = 2; state Root;")
    result = solve_bmc_property(
        compile_bmc_query(model, 'check reach <= 1: active("Root");')
    )
    witness = decode_bmc_result_trace(result, source="primary")
    with pytest.raises(BmcBuildError, match="parameters"):
        forged = replace(witness, initial=dict(witness.initial, parameters=parameters))
        replay_bmc_witness(model, forged)


def test_replay_rejects_reordered_input_read_provenance():
    from dataclasses import replace

    model = load_state_machine_from_text("input int z; input int a; state Root;")
    result = solve_bmc_property(
        compile_bmc_query(
            model, 'assume always: z + a == 2; check reach <= 1: active("Root");'
        )
    )
    witness = decode_bmc_result_trace(result, source="primary")
    assert list(witness.steps[0].inputs) == ["z", "a"]
    assert list(witness.steps[0].to_canonical()["inputs"]) == ["z", "a"]
    forged = replace(
        witness, steps=(replace(witness.steps[0], input_reads=("a", "z")),)
    )
    with pytest.raises(BmcBuildError, match="declaration order"):
        replay_bmc_witness(model, forged)


def test_imported_modules_share_host_input_and_parameter(tmp_path):
    from pyfcstm.model import load_state_machine_from_file

    (tmp_path / "child.fcstm").write_text(
        """
        input int sensor; param int gain = 2; output int result = 0;
        state Child { enter { result = sensor * gain; } }
    """,
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        """
        input int shared; param int factor = 3;
        state Host {
            import "./child.fcstm" as A { var sensor -> shared; var gain -> factor; var result -> A_result; }
            import "./child.fcstm" as B { var sensor -> shared; var gain -> factor; var result -> B_result; }
            [*] -> A;
            A -> B;
        }
    """,
        encoding="utf-8",
    )
    model = load_state_machine_from_file(str(host))
    formula = compile_bmc_query(
        model,
        """
        assume at 0: shared == 2;
        assume at 1: shared == 5;
        check reach <= 2: active("Host.B");
    """,
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    trace = decode_bmc_result_trace(result, source="primary")
    assert trace.initial["parameters"] == {"factor": 3}
    assert [step.inputs for step in trace.steps] == [{"shared": 2}, {"shared": 5}]
    assert trace.frames[-1].vars == {"A_result": 6, "B_result": 15}
    assert replay_bmc_witness(model, trace).ok


def test_legacy_symbol_constructor_defaults_empty_input_slots():
    from dataclasses import replace

    model = load_state_machine_from_text("control int count = 0; state Root;")
    symbols = BmcTraceSymbols.allocate(
        BmcEngine(model).prepare("check reach <= 2: true;").domain
    )
    rebuilt = replace(symbols, step_inputs=())
    assert rebuilt.step_inputs == ({}, {})
    assert rebuilt.parameters == {}
