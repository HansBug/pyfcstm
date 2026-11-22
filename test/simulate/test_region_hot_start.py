"""Public-surface tests for hot-starting a model that declares regions.

A hot-start position is a tree. A leaf that is written is put in place without
its ``enter`` actions. Whatever is not written is left to the model: a plain
composite state waits for initialization, a region of an owner that is not
written waits for initialization, and an owner written as a bare path waits as a
whole. The first cycle then runs the initial transitions of everything that
waits, in writing order, while the parts that were put in place work as usual.

Every state of the model below adds one digit to ``seq`` when it is entered, so
the digits of ``seq`` after the first cycle name the ``enter`` actions that ran.
"""

import itertools

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.configuration import Configuration
from pyfcstm.simulate import SimulationRuntime
from test.testings.simulate_semantics import (
    build_state_machine_from_case,
    iter_semantic_cases,
)

pytestmark = pytest.mark.unittest

JOB = """
def int seq = 0;
def int n = 0;
state W {
    [*] -> Job;
    state Job {
        enter { seq = seq * 10 + 9; }
        region A {
            [*] -> Q;
            state Q {
                enter { seq = seq * 10 + 1; }
                region A1 {
                    [*] -> W1;
                    state W1 {
                        enter { seq = seq * 10 + 2; }
                        during { n = n + 1; }
                    }
                    W1 -> [*] :: Fin;
                }
                region A2 {
                    [*] -> W2;
                    state W2 {
                        enter { seq = seq * 10 + 3; }
                        during { n = n + 100; }
                    }
                }
            }
        }
        region B {
            [*] -> Comp;
            state Comp {
                enter { seq = seq * 10 + 4; }
                [*] -> In1;
                state In1 {
                    enter { seq = seq * 10 + 5; }
                    during { n = n + 10000; }
                }
                state In2 { enter { seq = seq * 10 + 6; } }
                In1 -> In2 :: Next;
            }
            pseudo state P;
            Comp -> P :: Jump;
            P -> Comp;
        }
    }
}
"""

RESTING = "W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}"


@pytest.fixture(scope="module")
def job():
    return load_state_machine_from_text(JOB)


def _hot(model, start, **overrides):
    values = {"seq": 0, "n": 0}
    values.update(overrides)
    return SimulationRuntime(model, initial_state=start, initial_vars=values)


def test_the_cold_start_enters_every_state_in_writing_order(job):
    runtime = SimulationRuntime(job)
    runtime.cycle()
    assert str(runtime.configuration) == RESTING
    assert runtime.vars["seq"] == 912345


DONE_A1 = "W.Job{A: Q{A1: [done], A2: W2}, B: Comp.In1}"


@pytest.mark.parametrize(
    ["start", "seq", "n", "final"],
    [
        pytest.param(RESTING, 0, 10101, RESTING, id="every-leaf-in-place"),
        pytest.param("W.Job", 12345, 10101, RESTING, id="owner-path-waits-as-a-whole"),
        pytest.param(
            "W.Job{A: [init], B: [init]}", 12345, 10101, RESTING, id="every-region-waits"
        ),
        pytest.param("W.Job{A: Q, B: Comp.In1}", 23, 10101, RESTING, id="nested-owner-waits"),
        pytest.param(
            "W.Job{A: Q{A1: [init], A2: W2}, B: Comp.In1}",
            2,
            10101,
            RESTING,
            id="one-region-waits",
        ),
        pytest.param("W.Job{B: Comp.In1}", 123, 10101, RESTING, id="a-region-left-out-waits"),
        pytest.param(
            "W.Job{A: Q{A1: W1, A2: W2}, B: Comp}", 5, 10101, RESTING, id="composite-waits"
        ),
        pytest.param(
            "W.Job{A: Q{A1: W1, A2: W2}, B: P}", 45, 10101, RESTING, id="pseudo-state-is-left"
        ),
        pytest.param(
            "W.Job{A: Q{A1: [done], A2: W2}, B: [init]}",
            45,
            10100,
            DONE_A1,
            id="done-region-stays-done",
        ),
    ],
)
def test_the_first_cycle_runs_only_what_was_not_put_in_place(job, start, seq, n, final):
    runtime = _hot(job, start)
    runtime.cycle()
    assert runtime.vars["seq"] == seq
    assert runtime.vars["n"] == n
    assert str(runtime.configuration) == final


def test_a_done_region_does_no_work_and_does_not_enter_again(job):
    runtime = _hot(job, DONE_A1)
    for _ in range(3):
        runtime.cycle()
    assert str(runtime.configuration) == DONE_A1
    assert runtime.vars["seq"] == 0
    assert runtime.vars["n"] == 3 * 10100


def test_a_partial_hot_start_reports_its_waiting_regions_before_the_first_cycle(job):
    """Until its first cycle the machine is not resting: waiting regions show as ``[init]``."""
    runtime = _hot(job, "W.Job{B: Comp.In1}")
    config = runtime.configuration
    assert str(config) == "W.Job{A: [init], B: Comp.In1}"
    assert config.mode == "transient"
    assert runtime.current_state == config
    runtime.cycle()
    assert runtime.configuration.mode == "stable"


def test_a_state_path_into_a_region_leaves_the_other_regions_waiting(job):
    by_text = _hot(job, "W.Job{B: Comp.In1}")
    by_path = _hot(job, "W.Job.B.Comp.In1")
    by_tuple = _hot(job, ("W", "Job", "B", "Comp", "In1"))
    by_state = _hot(
        job,
        job.root_state.substates["Job"].regions["B"].substates["Comp"].substates["In1"],
    )
    for runtime in (by_text, by_path, by_tuple, by_state):
        runtime.cycle()
        assert str(runtime.configuration) == RESTING
        assert runtime.vars["seq"] == 123


def test_a_configuration_object_starts_the_runtime_where_it_was_taken(job):
    cold = SimulationRuntime(job)
    cold.cycle()
    cold.cycle(["W.Job.A.Q.A1.W1.Fin"])
    assert str(cold.configuration) == "W.Job{A: Q{A1: [done], A2: W2}, B: Comp.In1}"
    hot = SimulationRuntime(
        job, initial_state=cold.configuration, initial_vars=dict(cold.vars)
    )
    assert hot.configuration == cold.configuration
    for events in ([], ["W.Job.B.Comp.In1.Next"], [], ["W.Job.B.Comp.In2.Back"]):
        try:
            cold.cycle(events)
        except Exception as err:  # noqa: BLE001 - an event the model lacks
            with pytest.raises(type(err)):
                hot.cycle(events)
            break
        hot.cycle(events)
        assert hot.configuration == cold.configuration
        assert dict(hot.vars) == dict(cold.vars)


def test_a_configuration_of_the_machine_that_is_a_transient_snapshot_is_accepted(job):
    snapshot = Configuration.parse(job, "W.Job{A: Q, B: Comp.In1}", mode="transient")
    runtime = SimulationRuntime(
        job, initial_state=snapshot, initial_vars={"seq": 0, "n": 0}
    )
    runtime.cycle()
    assert runtime.vars["seq"] == 23


@pytest.mark.parametrize(
    "start",
    [
        "W.Job{A: [done], B: [done]}",
        "W.Job{A: Q{A1: [done], A2: [done]}, B: Comp.In1}",
    ],
)
def test_a_position_where_every_region_of_an_owner_is_done_is_rejected(job, start):
    with pytest.raises(ValueError, match="All regions are Done"):
        _hot(job, start)


@pytest.mark.parametrize(
    ["start", "message"],
    [
        ("W.Job{C: Q}", "region"),
        ("W.Job{A: Nope}", "Nope"),
        ("W.Nowhere", "Nowhere"),
        ("W.Job.A.Q.Nope", "Nope"),
        ("W.Job{A: Q", "end of input"),
    ],
)
def test_a_position_that_is_not_one_of_the_model_is_rejected(job, start, message):
    with pytest.raises(ValueError, match=message):
        _hot(job, start)


def test_a_configuration_of_another_model_is_rejected(job):
    other = load_state_machine_from_text(JOB)
    foreign = Configuration.parse(other, RESTING)
    with pytest.raises(ValueError, match="does not belong"):
        _hot(job, foreign)


def test_a_state_of_another_model_is_rejected(job):
    other = load_state_machine_from_text(JOB)
    foreign = other.root_state.substates["Job"]
    with pytest.raises(ValueError, match="does not belong"):
        _hot(job, foreign)


@pytest.mark.parametrize(
    ["start", "error", "message"],
    [
        pytest.param("", ValueError, "cannot be empty", id="empty-text"),
        pytest.param(42, TypeError, "got int", id="unsupported-type"),
        pytest.param("W.Job.A", ValueError, "names a region", id="a-region-is-no-state"),
    ],
)
def test_a_reference_that_is_no_state_is_rejected(job, start, error, message):
    with pytest.raises(error, match=message):
        _hot(job, start)


WAITING_CANNOT_START = """
def int x = 0;
state Root {
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1 { during { x = x + 1; } } }
        region B { [*] -> B1 : if [x > 100]; state B1; }
    }
}
"""


def test_a_waiting_region_that_cannot_start_makes_the_first_cycle_a_delta():
    """Nothing changes in a cycle that cannot be completed, hot-started or not."""
    model = load_state_machine_from_text(WAITING_CANNOT_START)
    runtime = SimulationRuntime(
        model, initial_state="Root.Run{A: A1}", initial_vars={"x": 0}
    )
    result = runtime.cycle()
    assert result.delta
    assert str(runtime.configuration) == "Root.Run{A: A1, B: [init]}"
    assert runtime.vars["x"] == 0
    assert runtime.cycle_count == 1
    # Once the guard can hold, the same machine starts the region and goes on.
    runtime = SimulationRuntime(
        model, initial_state="Root.Run{A: A1}", initial_vars={"x": 101}
    )
    assert not runtime.cycle().delta
    assert str(runtime.configuration) == "Root.Run{A: A1, B: B1}"


def test_every_variable_has_to_be_given(job):
    with pytest.raises(ValueError, match="initial_vars must provide all variables"):
        SimulationRuntime(job, initial_state=RESTING, initial_vars={"seq": 0})
    with pytest.raises(ValueError, match="initial_vars must be provided"):
        SimulationRuntime(job, initial_state=RESTING)


QUERIED = """
def int n = 0;
state Root {
    [*] -> Run;
    state Run {
        region A {
            [*] -> A1;
            state A1;
            state A2;
            A1 -> A2 :: Go;
        }
        region B {
            [*] -> B1;
            state B1 { during { if [active("Root.Run.A.A2")] { n = n + 1; } } }
        }
    }
}
"""


def test_the_hidden_variable_of_an_active_query_is_an_ordinary_variable():
    model = load_state_machine_from_text(QUERIED)
    config = Configuration.parse(model, "Root.Run{A: A2, B: B1}")
    flags = model.active_variables(config)
    assert flags
    with pytest.raises(ValueError, match="initial_vars must provide all variables"):
        SimulationRuntime(model, initial_state=config, initial_vars={"n": 0})
    given = SimulationRuntime(
        model, initial_state=config, initial_vars={"n": 0, **flags}
    )
    given.cycle()
    assert given.vars["n"] == 1
    # Whatever the caller gives is what runs: nothing is derived or checked.
    lying = SimulationRuntime(
        model,
        initial_state=config,
        initial_vars={"n": 0, **{name: 0 for name in flags}},
    )
    lying.cycle()
    assert lying.vars["n"] == 0


def _replayable(case):
    data = case.data
    if "initial" in data or "parameters" in data or "handlers" in data:
        return False
    return all(
        set(step) <= {"cycle", "expect"} and isinstance(step.get("cycle"), list)
        for step in data.get("steps") or []
    )


def _region_cases():
    return [
        case
        for case in iter_semantic_cases()
        if "regions" in case.data["categories"] and _replayable(case)
    ]


def test_the_corpus_has_region_cases_to_replay():
    assert len(_region_cases()) > 30


@pytest.mark.parametrize("case", _region_cases(), ids=lambda case: case.id)
def test_a_hot_start_at_any_resting_point_continues_like_the_cold_run(case):
    """From each resting position the hot start behaves like the run it came from."""
    model = build_state_machine_from_case(case)
    steps = [step["cycle"] for step in case.data["steps"]]
    try:
        cold = SimulationRuntime(model)
    except Exception:  # noqa: BLE001 - a case that needs inputs cannot be replayed
        pytest.skip("the case needs an input source")
    for index, events in enumerate(steps):
        try:
            cold.cycle(events)
        except Exception:  # noqa: BLE001 - the case ends in an error on purpose
            return
        if cold.is_ended or cold.configuration.mode != "stable":
            continue
        try:
            hot = SimulationRuntime(
                model,
                initial_state=cold.configuration,
                initial_vars=dict(cold.vars),
            )
        except ValueError:
            continue
        reference = _clone_by_replay(model, steps[: index + 1])
        for later in steps[index + 1 :]:
            outcome_cold = _cycle_outcome(reference, later)
            outcome_hot = _cycle_outcome(hot, later)
            assert outcome_hot == outcome_cold, (case.id, index, later)
            if reference.is_ended:
                break


def _clone_by_replay(model, steps):
    runtime = SimulationRuntime(model)
    for events in steps:
        runtime.cycle(events)
    return runtime


def _cycle_outcome(runtime, events):
    try:
        runtime.cycle(events)
    except Exception as err:  # noqa: BLE001 - the error class is part of the outcome
        return ("error", type(err).__name__)
    configuration = None if runtime.is_ended else str(runtime.configuration)
    return (configuration, tuple(sorted(runtime.vars.items())))


def test_the_cold_start_of_every_short_input_sequence_is_unchanged(job):
    """Running ordinarily never leaves an owner at work with a region waiting."""
    events = [[], ["W.Job.A.Q.A1.W1.Fin"], ["W.Job.B.Comp.In1.Next"], ["W.Job.B.Comp.Jump"]]
    for sequence in itertools.product(range(len(events)), repeat=3):
        runtime = SimulationRuntime(job)
        for index in sequence:
            try:
                runtime.cycle(events[index])
            except Exception:  # noqa: BLE001 - an event that cannot fire here
                break
            if not runtime.is_ended:
                assert "[init]" not in str(runtime.configuration)


def test_hot_start_of_a_model_without_regions_is_unchanged():
    model = load_state_machine_from_text(
        "def int x = 0; state Root { [*] -> A; state A; state B; A -> B :: Go; }"
    )
    runtime = SimulationRuntime(model, initial_state="Root.A", initial_vars={"x": 5})
    runtime.cycle(["Root.A.Go"])
    assert runtime.current_state.path == ("Root", "B")
    assert runtime.vars["x"] == 5


def test_a_hot_start_is_no_longer_a_controlled_rejection():
    model = load_state_machine_from_text(
        "state Root { [*] -> Run; state Run { region A { [*] -> X; state X; }"
        " region B { [*] -> Y; state Y; } } }"
    )
    runtime = SimulationRuntime(model, initial_state="Root.Run", initial_vars={})
    runtime.cycle()
    assert str(runtime.configuration) == "Root.Run{A: X, B: Y}"
