"""Hot start of a model with regions: the position the trace begins in."""

import pytest
import z3

from pyfcstm.bmc import (
    REGION_PENDING_ID,
    BmcEngine,
    InvalidBmcQuery,
    build_bmc_core_formula,
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

# A region that can fail to start, a plain composite state and a pseudo state.
WAITING = """
input int g;
def int n = 0;
state Root {
    [*] -> Run;
    state Run {
        region A {
            [*] -> C;
            state C { [*] -> L; state L { during { n = n + 1; } } }
            pseudo state P;
            state Next { during { n = n + 10; } }
            P -> Next;
        }
        region B { [*] -> Q : if [g != 0]; state Q { during { n = n + 100; } } }
    }
}
"""

ANY_VARIABLES = " havoc *"
PINNED = ' havoc * where permit == 1 && motor == 1'


def prepare(text, start, where=ANY_VARIABLES, bound=2):
    model = load_state_machine_from_text(text)
    query = 'init state("%s")%s;\ncheck reach <= %d: terminated();' % (
        start,
        where,
        bound,
    )
    return build_bmc_core_formula(BmcEngine(model).prepare(query))


def solved(core, extra=()):
    solver = z3.Solver()
    solver.add(core.core, *extra)
    assert solver.check() == z3.sat
    return solver.model()


def position(core, model, frame, path):
    return model.eval(core.symbols.region_position(frame, path), True).as_long()


def state_id(core, path):
    return core.context.domain.state_path_to_id(path)


def test_a_written_position_is_in_place_at_the_first_frame():
    core = prepare(
        INTERLOCK, "Controller.Running{Safety: Watching, Motion: On}", PINNED
    )
    model = solved(core)
    assert position(core, model, 0, "Controller.Running.Safety") == state_id(
        core, "Controller.Running.Safety.Watching"
    )
    assert position(core, model, 0, "Controller.Running.Motion") == state_id(
        core, "Controller.Running.Motion.On"
    )
    assert model.eval(core.symbols.frame_state(0), True).as_long() == state_id(
        core, "Controller.Running"
    )


@pytest.mark.parametrize(
    "start, pending",
    [
        ("Controller.Running{Motion: On}", ["Safety"]),
        ("Controller.Running.Motion.On", ["Safety"]),
        ("Controller.Running", ["Safety", "Motion"]),
        ("Controller.Running{Safety: [init], Motion: On}", ["Safety"]),
    ],
)
def test_a_region_that_was_not_written_waits_and_starts_in_the_first_cycle(
    start, pending
):
    core = prepare(INTERLOCK, start, PINNED)
    model = solved(core)
    for name in pending:
        path = "Controller.Running." + name
        assert position(core, model, 0, path) == REGION_PENDING_ID
        assert position(core, model, 1, path) >= 0


def test_a_start_that_leaves_no_region_at_work_is_refused():
    text = """
    state Root {
        [*] -> Job;
        state Job {
            region A { [*] -> P; state P; P -> [*]; }
            region B { [*] -> Q; state Q; Q -> [*]; }
        }
    }
    """
    with pytest.raises(InvalidBmcQuery) as refused:
        prepare(text, "Root.Job{A: [done], B: [done]}", "")
    assert refused.value.diagnostic.code == "invalid_start_position"
    assert "all regions are done" in refused.value.diagnostic.message


@pytest.mark.parametrize(
    "start, code",
    [
        ("Controller.Nowhere", "unknown_state"),
        ("Controller.Running.Motion", "unknown_state"),
        ("Controller.Running{Motion: Nowhere}", "invalid_start_position"),
        ("$STATE_INIT", "reserved_state_path"),
    ],
)
def test_a_start_that_is_not_a_position_of_the_model_is_refused(start, code):
    with pytest.raises(InvalidBmcQuery) as refused:
        prepare(INTERLOCK, start, PINNED)
    assert refused.value.diagnostic.code == code


def test_a_region_that_cannot_start_makes_the_cycle_a_delta_that_keeps_everything():
    # Region B starts only when g is not zero, and it waits for its start.
    core = prepare(WAITING, "Root.Run{A: C.L}", " havoc * where n == 0")
    stuck = solved(core, [core.symbols.step_inputs[0]["g"] == 0])
    assert z3.is_true(stuck.eval(core.symbols.delta_flag(0), True))
    assert position(core, stuck, 1, "Root.Run.B") == REGION_PENDING_ID
    assert position(core, stuck, 1, "Root.Run.A") == position(
        core, stuck, 0, "Root.Run.A"
    )
    assert stuck.eval(core.symbols.frame_var(1, "n"), True).as_long() == 0

    moving = solved(core, [core.symbols.step_inputs[0]["g"] == 1])
    assert not z3.is_true(moving.eval(core.symbols.delta_flag(0), True))
    assert position(core, moving, 1, "Root.Run.B") == state_id(core, "Root.Run.B.Q")


def test_a_composite_state_without_a_child_waits_for_its_initial_transition():
    core = prepare(WAITING, "Root.Run{A: C, B: Q}", " havoc * where n == 0")
    model = solved(core)
    assert position(core, model, 0, "Root.Run.A") == state_id(core, "Root.Run.A.C")
    assert position(core, model, 1, "Root.Run.A") == state_id(core, "Root.Run.A.C.L")


def test_a_pseudo_state_is_left_in_the_first_cycle():
    core = prepare(WAITING, "Root.Run{A: P, B: Q}", " havoc * where n == 0")
    model = solved(core)
    assert position(core, model, 0, "Root.Run.A") == state_id(core, "Root.Run.A.P")
    assert position(core, model, 1, "Root.Run.A") == state_id(
        core, "Root.Run.A.Next"
    )


# A start that leaves region B waiting while B cannot start (a > 0 is needed).
ROLLED_BACK = """
input int a;
state Root {
    [*] -> P;
    state P {
        region A { [*] -> X; state X { during abstract Work; } state X2; X -> X2 : if [a == 0]; }
        region B { [*] -> Y : if [a > 0]; state Y; }
    }
}
"""


def solve_rolled_back(query, text=ROLLED_BACK):
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property

    return solve_bmc_property(
        compile_bmc_query(load_state_machine_from_text(text), query)
    )


def test_a_cycle_rolled_back_by_a_region_that_cannot_start_runs_no_case():
    # With a == 0 region A would take X -> X2, but B cannot start, so the whole
    # cycle is a Delta and A keeps resting in X.
    found = solve_rolled_back(
        'init state("Root.P{A: X}");\n'
        'check cover <= 1: case("Root.P.A.X::transition::Root.P.A.X2::0");'
    )
    assert found.witness_found is False


def test_a_cycle_rolled_back_by_a_region_that_cannot_start_makes_no_call():
    text = """
    input int a;
    state Root {
        [*] -> P;
        state P {
            region A { [*] -> X; state X { during abstract Work; } }
            region B { [*] -> Y : if [a > 0]; state Y; }
        }
    }
    """
    found = solve_rolled_back(
        'init state("Root.P{A: X}");\n'
        "assume always: a == 0;\n"
        'check reach <= 1: call_count("Root.P.A.X.Work", step=0) == 0;',
        text,
    )
    assert found.witness_found is True


def test_a_rolled_back_cycle_consumes_no_event():
    from pyfcstm.bmc import decode_bmc_result_trace, replay_bmc_witness

    text = ROLLED_BACK.replace("X -> X2 : if [a == 0];", "X -> X2 :: Go;")
    result = solve_rolled_back(
        'init state("Root.P{A: X}");\n'
        "assume at 0: a == 0;\n"
        'check reach <= 2: active("Root.P.A.X2");',
        text,
    )
    assert result.witness_found is True
    witness = decode_bmc_result_trace(result)
    assert replay_bmc_witness(load_state_machine_from_text(text), witness).ok
    assert witness.steps[0].delta is True
    assert witness.steps[0].consumed_events == ()


# A plain composite state that waits for its initial transition, next to a
# state that owns regions.
PLAIN_NEXT_TO_GROUP = """
def int n = 0;
state Root {
    [*] -> Plain;
    state Plain { [*] -> Leaf; state Leaf { during { n = n + 1; } } }
    state Busy {
        region A { [*] -> P; state P; }
        region B { [*] -> Q; state Q; }
    }
    Plain -> Busy : if [n > 5];
}
"""


def test_a_plain_composite_state_that_is_not_in_a_region_waits_in_a_machine_with_regions():
    core = prepare(PLAIN_NEXT_TO_GROUP, "Root.Plain", " havoc * where n == 0")
    model = solved(core)
    assert model.eval(core.symbols.frame_state(0), True).as_long() == state_id(
        core, "Root.Plain"
    )
    assert model.eval(core.symbols.frame_state(1), True).as_long() == state_id(
        core, "Root.Plain.Leaf"
    )


def test_the_resolved_start_is_part_of_the_canonical_initial_specification():
    model = load_state_machine_from_text(INTERLOCK)
    query = (
        'init state("Controller.Running{Motion: On}") havoc *;\n'
        "check reach <= 2: terminated();"
    )
    initial = BmcEngine(model).prepare(query).bound_query.initial.to_canonical()
    assert initial["resolved_start"] == {
        "main": "Controller.Running",
        "positions": {
            "Controller.Running.Motion": "Controller.Running.Motion.On",
            "Controller.Running.Safety": "pending",
        },
    }


def test_a_cycle_that_is_a_delta_does_not_require_a_later_region_to_be_defined():
    # Region A cannot start with d == 0, so the cycle is a Delta and region B's
    # division by d is never reached: the scenario d == 0 is feasible and the
    # trace, which replays, is one Delta cycle.
    from pyfcstm.bmc import decode_bmc_result_trace, replay_bmc_witness

    text = """
    input int d;
    def int y = 0;
    state Root {
        [*] -> Run;
        state Run {
            region A { [*] -> P : if [d == 1]; state P; }
            region B { [*] -> Q; state Q { during { y = 10 / d; } } }
        }
    }
    """
    found = solve_rolled_back(
        'init state("Root.Run{A: [init], B: Q}");\n'
        "assume always: d == 0;\n"
        "check reach <= 1: cycle == 1;",
        text,
    )
    assert found.witness_found is True
    witness = decode_bmc_result_trace(found)
    assert witness.steps[0].delta is True
    assert replay_bmc_witness(load_state_machine_from_text(text), witness).ok
