"""Cone reduction preserves observable execution and scenario feasibility."""

import pytest
import z3

from pyfcstm.bmc import (
    BmcBuildError,
    BmcCoreFormula,
    BmcEventDecodePolicy,
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
def int reported = 3;
def int other = 5;
state Root {
    enter { ticks = ticks + 1; reported = ticks * 17; other = reported + 9; }
    during { ticks = ticks + 1; reported = reported + ticks; other = other * 2; }
}
"""


def test_unread_outputs_are_removed_and_public_decoders_fill_every_frame():
    query = "check reach <= 4: ticks == 2;"
    machine, full = _compile(_OUTPUTS, query, False)
    _, sliced = _compile(_OUTPUTS, query)
    assert sliced.core.cone_slice.dropped_variables == ("reported", "other")
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
        "reported",
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
        "def int reported = 0; state Root { enter abstract Observe; }",
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


@pytest.mark.parametrize("profile", ["default", "logic", "tactic"])
def test_response_suffix_is_completed_before_exposing_result(profile):
    machine, formula = _compile(
        _OUTPUTS, "check response <= 1: trigger true -> within 2 false;"
    )
    result = solve_bmc_property(formula, solver_profile=profile)
    assert result.status == "unsat"
    assert result.incomplete_status == "sat"
    trace = decode_bmc_result_trace(result, source="incomplete_suffix")
    assert replay_bmc_witness(machine, trace).ok
    assert trace.frames[1].vars["reported"] == 19


@pytest.mark.parametrize(
    "query,source",
    [
        ("check reach <= 4: ticks == 2;", "primary"),
        (
            "check response <= 1: trigger true -> within 2 false;",
            "incomplete_suffix",
        ),
    ],
)
def test_result_decoding_reuses_validation_without_sharing_mutable_traces(
    monkeypatch, query, source
):
    import pyfcstm.bmc.witness as witness_module

    machine, formula = _compile(_OUTPUTS, query)
    calls = []
    original_replay = witness_module.replay_bmc_witness

    def record_replay(*args, **kwargs):
        calls.append(1)
        return original_replay(*args, **kwargs)

    # Observe real public solves without replacing their validation behavior.
    monkeypatch.setattr(witness_module, "replay_bmc_witness", record_replay)
    result = solve_bmc_property(formula)
    assert len(calls) == 1
    first = decode_bmc_result_trace(result, source=source)
    expected = first.to_canonical()
    first.frames[1].vars["reported"] = -999
    first.initial["vars"]["reported"] = -999
    first.solver["primary_status"] = "changed"
    second = decode_bmc_result_trace(result, source=source)
    assert second.to_canonical() == expected
    assert len(calls) == 1
    assert not replay_bmc_witness(machine, first).ok
    assert replay_bmc_witness(machine, second).ok
    # A valid dataclass variant must derive its own metadata, not reuse an old
    # result's decoded witness. This is also how callers construct variants.
    from dataclasses import replace

    variant = replace(result, elapsed_ms=result.elapsed_ms + 1)
    assert (
        decode_bmc_result_trace(variant, source=source).solver["primary_elapsed_ms"]
        == variant.elapsed_ms
    )


def test_result_reuse_preserves_explicit_event_policy_and_channel_validation():
    machine, formula = _compile(
        """
        def int reported = 0;
        state Root {
            state A { event go; during { reported = reported + 1; } }
            state B;
            [*] -> A;
            A -> B :: go;
        }
        """,
        'init state("Root.A"); assume event("Root.A.go", 0) == false; '
        'check reach <= 1: active("Root.A");',
    )
    result = solve_bmc_property(formula)
    assert decode_bmc_result_trace(result).steps[0].event_reads
    quiet = decode_bmc_result_trace(
        result, event_policy=BmcEventDecodePolicy(include_debug_reads=False)
    )
    assert quiet.steps[0].event_reads == ()
    assert replay_bmc_witness(machine, quiet).ok
    with pytest.raises(BmcBuildError, match="event_policy"):
        decode_bmc_result_trace(result, event_policy="quiet")
    with pytest.raises(BmcBuildError, match="response"):
        decode_bmc_result_trace(result, source="incomplete_suffix")


def test_failed_slice_replays_once_then_solves_full_model_with_same_budget(monkeypatch):
    import pyfcstm.bmc.witness as witness_module

    _, formula = _compile(_OUTPUTS, "check reach <= 4: ticks == 2;")
    checks, validations = [], []
    original_check = witness_module._check_with_budget

    def record_check(solver, budget):
        checks.append(budget)
        return original_check(solver, budget)

    def reject_candidate(formula, trace):
        validations.append(trace)
        raise witness_module._ConeReplayFailure("injected replay mismatch")

    # Injection instruments the public solve contract: a rejected candidate
    # must not escape, loop, or acquire a fresh complete timeout allowance.
    monkeypatch.setattr(witness_module, "_check_with_budget", record_check)
    monkeypatch.setattr(witness_module, "_fill_cone_trace", reject_candidate)
    result = solve_bmc_property(formula, timeout_ms=10000)
    assert result.status == "sat"
    assert len(validations) == 1
    assert len(checks) == 2 and checks[0] is checks[1]
    assert result.formula.core.context.options.cone_slicing is False
    assert result.to_canonical()["cone_slicing"]["fallback"] is True
    assert "slicing_fallback" in result.diagnostics
    assert decode_bmc_result_trace(result).frames[1].vars["reported"] == 19


def test_slicing_disabled_keeps_core_and_result_payload_unchanged():
    machine = load_state_machine_from_text(_OUTPUTS)
    query = "check reach <= 4: ticks == 2;"
    implicit = compile_bmc_query(machine, query)
    explicit = compile_bmc_query(machine, query, options=BmcOptions(cone_slicing=False))
    assert implicit.core.to_canonical() == explicit.core.to_canonical()
    assert "cone_slicing" not in solve_bmc_property(explicit).to_canonical()


@pytest.mark.parametrize(
    "retained,dropped,reason",
    [
        (("x",), ("x",), None),
        ((), ("x", "x"), None),
        ((), ("x",), "abstract_actions"),
        ((), (), "unknown"),
        (("x",), ("",), None),
    ],
)
def test_slice_metadata_rejects_inconsistent_partitions(retained, dropped, reason):
    from pyfcstm.bmc.slicing import ConeSlice

    with pytest.raises(BmcBuildError):
        ConeSlice(retained, dropped, reason)


def test_float_and_unknown_arithmetic_remain_in_the_model():
    source = """
    def float value = 1.0;
    def float reported = 0.0;
    def int integer_output = 0;
    state Root { enter { reported = sqrt(value); integer_output = 17; } }
    """
    machine, formula = _compile(source, 'check reach <= 1: active("Root");')
    assert formula.core.cone_slice.dropped_variables == ("integer_output",)
    result = solve_bmc_property(formula)
    assert replay_bmc_witness(machine, decode_bmc_result_trace(result)).ok


def test_temporary_float_in_integer_variable_preserves_dependent_writes():
    source = """
    def int temporary = 0;
    def int reported = 0;
    def int telemetry = 0;
    state Root {
        enter {
            temporary = 0.5;
            reported = temporary + 1;
            temporary = 0;
            reported = 0;
            telemetry = 17;
        }
    }
    """
    query = "check reach <= 1: true;"
    machine, sliced = _compile(source, query)
    _, full = _compile(source, query, False)
    assert sliced.core.cone_slice.dropped_variables == ("telemetry",)
    result = solve_bmc_property(sliced)
    baseline = solve_bmc_property(full)
    assert (result.status, result.outcome) == (baseline.status, baseline.outcome)
    trace = decode_bmc_result_trace(result)
    assert replay_bmc_witness(machine, trace).ok
    assert [frame.vars for frame in trace.frames] == [
        frame.vars for frame in decode_bmc_result_trace(baseline).frames
    ]


@pytest.mark.parametrize(
    "property_text",
    [
        "check reach <= 3: ticks == 2;",
        "check invariant <= 3: ticks >= 0;",
        "check forbid <= 3: ticks < 0;",
        "check must_reach <= 3: ticks == 2;",
        "check exists_always <= 3: ticks >= 0;",
        'check cover <= 3: case("Root::transition::__terminate__::0");',
        "check response <= 3: trigger ticks == 1 -> within 1 ticks == 2;",
    ],
)
def test_property_verdicts_match_full_model(property_text):
    _, full = _compile(_OUTPUTS, property_text, False)
    machine, sliced = _compile(_OUTPUTS, property_text)
    assert sliced.core.cone_slice.dropped_variables
    baseline, result = solve_bmc_property(full), solve_bmc_property(sliced)
    for field in ("status", "property_satisfied", "outcome", "incomplete_status"):
        assert getattr(result, field) == getattr(baseline, field)
    if result.model is not None:
        assert replay_bmc_witness(machine, decode_bmc_result_trace(result)).ok
    if result.incomplete_model is not None:
        assert replay_bmc_witness(
            machine, decode_bmc_result_trace(result, source="incomplete_suffix")
        ).ok


@pytest.mark.parametrize("profile", ["default", "logic", "tactic"])
@pytest.mark.parametrize("numeric_type", ["int", "float"])
def test_slicing_preserves_input_steps_parameters_and_complete_outputs(
    profile, numeric_type
):
    source = """
    input %s sensor;
    input int spare;
    param int gain = 2;
    param int unused_gain = 9;
    control int ticks = 0;
    output %s reading = 0;
    output int held = 11;
    state Root {
        state Ready { during { ticks = ticks + 1; reading = sensor + gain; } }
        [*] -> Ready;
    }
    """ % (numeric_type, numeric_type)
    query = (
        "init cold havoc { gain }; assume always: gain == 4; "
        "assume at 0: sensor == 3; assume at 1: sensor == 5; "
        "assume at 0: spare == 9; assume at 1: spare == 8; "
        "check reach <= 2: ticks == 2;"
    )
    machine, sliced = _compile(source, query)
    _, full = _compile(source, query, False)
    result = solve_bmc_property(sliced, solver_profile=profile)
    baseline = solve_bmc_property(full, solver_profile=profile)
    assert result.status == baseline.status == "sat"
    assert result.to_canonical()["cone_slicing"]["fallback"] is False
    cone = sliced.core.cone_slice
    assert set(cone.retained_variables) | set(cone.dropped_variables) == {
        "ticks", "reading", "held"
    }
    assert "held" in cone.dropped_variables
    expected = decode_bmc_result_trace(baseline)
    for witness in (
        decode_bmc_result_trace(result),
        decode_bmc_witness(result.formula, result.model),
    ):
        assert witness.initial["parameters"] == {"gain": 4, "unused_gain": 9}
        assert [step.inputs for step in witness.steps] == [
            {"sensor": 3, "spare": 9}, {"sensor": 5, "spare": 8}
        ]
        assert [frame.vars for frame in witness.frames] == [
            frame.vars for frame in expected.frames
        ]
        assert witness.frames[-1].vars == {"ticks": 2, "reading": 9, "held": 11}
        assert replay_bmc_witness(machine, witness).ok


@pytest.mark.parametrize("abstract", [False, True])
def test_slicing_without_persistent_variables_keeps_environment_and_call_context(abstract):
    source = "input int sensor; param int gain = 2; state Root { %s }" % (
        "enter abstract Observe;" if abstract else ""
    )
    machine, formula = _compile(
        source, 'assume at 0: sensor == 5; check reach <= 1: active("Root");'
    )
    cone = formula.core.cone_slice
    assert cone.retained_variables == cone.dropped_variables == ()
    assert cone.skipped_reason == (
        "abstract_actions" if abstract else "no_removable_variables"
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    witness = decode_bmc_result_trace(result)
    assert witness.initial["parameters"] == {"gain": 2}
    assert witness.steps[0].inputs == {"sensor": 5}
    assert all(frame.vars == {} for frame in witness.frames)
    if abstract:
        assert len(witness.steps[0].abstract_calls) == 1
        assert witness.steps[0].abstract_calls[0].snapshot == {}
    assert replay_bmc_witness(machine, witness).ok


@pytest.mark.parametrize("name", ["sensor", "gain"])
def test_core_slice_partition_rejects_input_and_parameter_names(name):
    from pyfcstm.bmc.slicing import ConeSlice

    _, formula = _compile(
        "input int sensor; param int gain = 2; control int ticks = 0; state Root;",
        'check reach <= 1: active("Root");',
    )
    core = formula.core
    with pytest.raises(BmcBuildError, match="partition the persistent variables"):
        BmcCoreFormula(
            context=core.context,
            symbols=core.symbols,
            domain_formula=core.domain_formula,
            initial_formula=core.initial_formula,
            transition_formula=core.transition_formula,
            environment_formula=core.environment_formula,
            core=core.core,
            steps=core.steps,
            cone_slice=ConeSlice(("ticks", name), ()),
        )
