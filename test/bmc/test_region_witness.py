"""Witnesses of models with regions: frames, local cases and calls."""

import dataclasses

import pytest

from pyfcstm.bmc import (
    compile_bmc_query,
    decode_bmc_result_trace,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

INTERLOCK = """
input int fault;
input int requested;
control int permit = 0;
output int motor = 0;
state Controller {
    event Start;
    [*] -> Idle;
    state Idle { during { motor = 0; } }
    state Running {
        region Safety {
            [*] -> Watching;
            state Watching {
                during { if [fault != 0] { permit = 0; } else { permit = 1; } }
            }
        }
        region Motion {
            [*] -> Off;
            state Off { during { motor = 0; } }
            state On { during { motor = 1; } }
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [permit == 0 || requested == 0];
        }
    }
    Idle -> Running : /Start;
}
"""

MOTOR_ON = 'check reach <= 3: active("Controller.Running.Motion.On");'


def witness_of(text, query):
    model = load_state_machine_from_text(text)
    result = solve_bmc_property(compile_bmc_query(model, query))
    assert result.witness_found
    return decode_bmc_result_trace(result)


def test_every_frame_of_a_model_with_regions_carries_its_configuration():
    witness = witness_of(INTERLOCK, MOTOR_ON)
    assert witness.frames[0].sentinel == "init"
    assert witness.frames[0].configuration is None
    assert witness.frames[1].configuration == "Controller.Idle"
    assert witness.frames[2].configuration == (
        "Controller.Running{Safety: Watching, Motion: Off}"
    )
    last = witness.frames[-1]
    assert last.configuration == "Controller.Running{Safety: Watching, Motion: On}"
    assert last.state == "Controller.Running"


def test_the_cold_start_is_one_initial_case():
    step = witness_of(INTERLOCK, MOTOR_ON).steps[0]
    assert step.case_label is None
    assert step.case_kind == "initial"
    assert step.progress == "initial"
    assert [(item.scope, item.kind, item.label) for item in step.local_cases] == [
        (None, "initial", "__init__::initial::Controller.Idle::0")
    ]


def test_entering_a_group_lists_the_transition_and_then_every_start_in_order():
    step = witness_of(INTERLOCK, MOTOR_ON).steps[1]
    assert step.case_kind == "transition"
    assert [(item.scope, item.kind) for item in step.local_cases] == [
        (None, "transition"),
        ("Controller.Running", "initial"),
        ("Controller.Running", "initial"),
    ]
    assert [item.target for item in step.local_cases] == [
        "Controller.Running",
        "Controller.Running.Safety.Watching",
        "Controller.Running.Motion.Off",
    ]


def test_a_step_lists_its_local_cases_region_by_region():
    step = witness_of(INTERLOCK, MOTOR_ON).steps[-1]
    assert step.case_label is None
    assert step.case_kind == "transition"
    assert [(item.scope, item.kind) for item in step.local_cases] == [
        ("Controller.Running.Safety", "fallback"),
        ("Controller.Running.Motion", "transition"),
    ]
    assert (step.local_cases[1].source, step.local_cases[1].target) == (
        "Controller.Running.Motion.Off",
        "Controller.Running.Motion.On",
    )


def test_a_step_of_the_witness_carries_the_inputs_and_events_it_used():
    witness = witness_of(INTERLOCK, MOTOR_ON)
    assert witness.steps[1].input_event_paths == ("Controller.Start",)
    assert witness.steps[1].consumed_events == ("Controller.Start",)
    assert witness.steps[-1].inputs["requested"] != 0
    assert witness.steps[-1].inputs["fault"] == 0


def test_a_model_without_regions_has_neither_field_in_its_canonical_form():
    witness = witness_of(
        "state Root { [*] -> Idle; state Idle; }",
        'check reach <= 1: active("Root.Idle");',
    )
    assert "configuration" not in witness.frames[1].to_canonical()
    assert "local_cases" not in witness.steps[0].to_canonical()
    assert isinstance(witness.steps[0].case_label, str)
    assert "configuration" not in witness.to_canonical()["initial"]


def test_the_calls_of_a_step_carry_the_configuration_they_saw():
    text = """
    state Root {
        [*] -> P;
        state P {
            region A { [*] -> X; state X { during abstract WorkX; } }
            region B { [*] -> Y; state Y { during abstract WorkY; } }
        }
    }
    """
    witness = witness_of(text, 'check reach <= 1: active("Root.P.B.Y");')
    assert [(call.action_name, call.configuration) for call in witness.steps[0].abstract_calls] == [
        ("Root.P.A.X.WorkX", "Root.P{A: X, B: [init]}"),
        ("Root.P.B.Y.WorkY", "Root.P{A: X, B: Y}"),
    ]


@pytest.mark.parametrize(
    "text, query",
    [
        (INTERLOCK, MOTOR_ON),
        (
            INTERLOCK,
            'init state("Controller.Running{Motion: On}") havoc * '
            "where permit == 1 && motor == 1;\n"
            'check reach <= 2: active("Controller.Running.Motion.Off");',
        ),
        (
            """
            def int w = 0;
            state Root {
                [*] -> P;
                state P {
                    region R1 { [*] -> A; state A { during abstract WorkA; } }
                    region R2 { [*] -> B; state B { during { w = w + 1; } during abstract WorkB; } }
                }
            }
            """,
            "check reach <= 2: w == 2;",
        ),
    ],
    ids=["interlock_cold", "interlock_hot_with_a_waiting_region", "abstract_calls"],
)
def test_the_simulator_reproduces_a_witness_of_a_model_with_regions(text, query):
    model = load_state_machine_from_text(text)
    result = solve_bmc_property(compile_bmc_query(model, query))
    assert result.witness_found
    witness = decode_bmc_result_trace(result)
    replay = replay_bmc_witness(model, witness)
    assert replay.ok, [item.message for item in replay.mismatches]
    assert [frame.configuration for frame in replay.runtime_trace.frames[1:]] == [
        frame.configuration for frame in witness.frames[1:]
    ]


def test_a_witness_whose_configuration_was_changed_does_not_replay():
    model = load_state_machine_from_text(INTERLOCK)
    witness = witness_of(INTERLOCK, MOTOR_ON)
    frames = list(witness.frames)
    frames[-1] = dataclasses.replace(
        frames[-1], configuration="Controller.Running{Safety: Watching, Motion: Off}"
    )
    replay = replay_bmc_witness(model, dataclasses.replace(witness, frames=tuple(frames)))
    assert not replay.ok
    assert any(item.path.endswith("configuration") for item in replay.mismatches)


COMPOSITE_IN_REGION = """
state Root {
    event Go;
    region A {
        [*] -> C;
        state C {
            [*] -> L1;
            state L1 { during abstract H1; }
            state L2 { during abstract H; }
            L1 -> L2 : /Go;
        }
    }
    region B { [*] -> X; state X { during abstract HX; } }
}
"""


@pytest.mark.parametrize(
    "query",
    [
        'check reach <= 3: active("Root.A.C.L2");',
        'check reach <= 2: called("Root.A.C.L1.H1");',
        'check reach <= 2: called("Root.B.X.HX");',
    ],
)
def test_calls_below_a_composite_state_of_a_region_decode_and_replay(query):
    from pyfcstm.bmc import compile_bmc_query, decode_bmc_result_trace, replay_bmc_witness, solve_bmc_property

    model = load_state_machine_from_text(COMPOSITE_IN_REGION)
    result = solve_bmc_property(compile_bmc_query(model, query))
    assert result.witness_found is True
    witness = decode_bmc_result_trace(result)
    assert replay_bmc_witness(model, witness).ok


def test_a_case_below_a_composite_state_of_a_region_is_scoped_to_the_region():
    from pyfcstm.bmc import compile_bmc_query, decode_bmc_result_trace, solve_bmc_property

    model = load_state_machine_from_text(COMPOSITE_IN_REGION)
    result = solve_bmc_property(
        compile_bmc_query(model, 'check reach <= 3: active("Root.A.C.L2");')
    )
    cases = [
        case
        for step in decode_bmc_result_trace(result).steps
        for case in (step.local_cases or ())
        if case.kind == "transition"
    ]
    assert [(case.scope, case.label) for case in cases] == [
        ("Root.A", "Root.A.C.L1::transition::Root.A.C.L2::0")
    ]


ASPECT_IN_A_REGION = """
state Root {
    [*] -> Run;
    state Run {
        region A { >> during before abstract Tick; [*] -> P; state P; }
        region B { [*] -> Q; state Q; }
    }
}
"""


def test_an_abstract_aspect_declared_in_a_region_replays_and_takes_a_handler():
    from pyfcstm.bmc import (
        compile_bmc_query,
        decode_bmc_result_trace,
        replay_bmc_witness,
        solve_bmc_property,
    )

    model = load_state_machine_from_text(ASPECT_IN_A_REGION)
    result = solve_bmc_property(
        compile_bmc_query(model, 'check reach <= 2: active("Root.Run.A.P");')
    )
    witness = decode_bmc_result_trace(result)
    assert replay_bmc_witness(model, witness).ok
    seen = []
    handled = replay_bmc_witness(
        model,
        witness,
        abstract_handlers={"Root.Run.A.Tick": lambda ctx: seen.append(ctx.action_name)},
    )
    assert handled.ok and seen
