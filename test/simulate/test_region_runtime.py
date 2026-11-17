"""Public-surface tests for executing models that declare regions.

The shared semantic fixtures pin the per-cycle configuration of small models.
These tests cover what a fixture cannot say: properties over every short input
sequence, the types of the public position objects, handler contexts, traces,
and the controlled rejections that remain for entry points that are not
supported yet.
"""

import itertools
from dataclasses import FrozenInstanceError

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.configuration import Configuration
from pyfcstm.model.model import State
from pyfcstm.simulate import (
    SimulationRuntime,
    SimulationRuntimeEventError,
    SimulationRuntimeTerminalStateError,
)
from pyfcstm.utils.validate import ModelValidationError

CONTROLLER = """
input int fault;
input int requested;
control int permit = 0;
output int motor = 0;

state Controller {
    event Start;
    event Stop;
    [*] -> Idle;
    state Idle { during { motor = 0; } }
    state Running {
        region Safety {
            [*] -> Watching;
            state Watching {
                during {
                    if [fault != 0] { permit = 0; } else { permit = 1; }
                }
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
    !Running -> Idle : /Stop;
}
"""

FIVE_LEVEL_HOOKS = """
input int fault;
input int requested;
state Controller {
    event Start;
    >> during before abstract Tick;
    [*] -> Idle;
    state Idle;
    state Running {
        >> during before abstract GroupPre;
        region Safety {
            >> during before abstract SafetyPre;
            [*] -> Normal;
            state Normal { during abstract Watch; }
            state Tripped;
            Normal -> Tripped : if [fault != 0];
        }
        region Motion {
            [*] -> Off;
            state Off;
            state On { during abstract Drive; }
            Off -> On : if [requested != 0];
        }
    }
    Idle -> Running : /Start;
}
"""


def _controller():
    return SimulationRuntime(
        load_state_machine_from_text(CONTROLLER),
        input_source={"fault": 0, "requested": 0},
    )


def _expected_controller_cycle(config, event, fault, requested):
    """Reference rules of the interlock example, written from its description.

    :return: ``(configuration text, permit, motor)`` after the cycle, given the
        text before it. ``permit`` and ``motor`` are ``None`` when untouched.
    """
    if config == "Controller.Idle":
        if event == "Start":
            return (
                "Controller.Running{Safety: Watching, Motion: Off}",
                0 if fault else 1,
                0,
            )
        return "Controller.Idle", None, 0
    if event == "Stop":
        return "Controller.Idle", None, 0
    permit = 0 if fault else 1
    # Off turns on under the same condition On needs to stay on.
    motion_on = permit != 0 and requested != 0
    text = "Controller.Running{Safety: Watching, Motion: %s}" % (
        "On" if motion_on else "Off"
    )
    return text, permit, 1 if motion_on else 0


@pytest.mark.unittest
def test_controller_interlock_holds_for_every_input_sequence_of_length_three():
    """Every length-3 sequence of events and inputs follows the interlock rules."""
    events = [None, "Controller.Start", "Controller.Stop"]
    frames = [(fault, requested) for fault in (0, 1) for requested in (0, 1)]
    options = [(event, fault, requested) for event in events for fault, requested in frames]
    assert len(options) ** 3 == 1728
    for sequence in itertools.product(options, repeat=3):
        runtime = _controller()
        config, permit, motor = "Controller.Idle", 0, 0
        # The first cycle only enters the initial state.
        runtime.cycle(inputs={"fault": 0, "requested": 0})
        for event, fault, requested in sequence:
            runtime.cycle(
                [] if event is None else event,
                inputs={"fault": fault, "requested": requested},
            )
            config, new_permit, motor = _expected_controller_cycle(
                config, None if event is None else event.split(".")[-1], fault, requested
            )
            if new_permit is not None:
                permit = new_permit
            assert str(runtime.configuration) == config, sequence
            assert runtime.vars["permit"] == permit, sequence
            assert runtime.vars["motor"] == motor, sequence
            if fault and "Running" in config:
                # The interlock reacts in the same cycle the fault is seen.
                assert motor == 0 and config.endswith("Motion: Off}"), sequence


@pytest.mark.unittest
def test_configuration_and_current_state_types_follow_the_model():
    """The position type depends on the model, and the object is immutable."""
    runtime = _controller()
    assert isinstance(runtime.current_state, Configuration)
    assert str(runtime.configuration) == "Controller"
    assert repr(runtime.configuration).startswith("Configuration(mode='initialization'")
    runtime.cycle(inputs={"fault": 0, "requested": 0})
    runtime.cycle("Controller.Start", inputs={"fault": 0, "requested": 0})
    config = runtime.configuration
    assert config == runtime.current_state
    assert str(config) == "Controller.Running{Safety: Watching, Motion: Off}"
    assert config.mode == "stable"
    assert config.is_active("Controller.Running.Motion.Off")
    assert Configuration.parse(runtime.state_machine, str(config)) == config
    with pytest.raises(FrozenInstanceError):
        config.mode = "transient"
    runtime.cycle("Controller.Stop", inputs={"fault": 0, "requested": 0})
    assert config.is_active("Controller.Running.Motion.Off"), "old snapshot stays"
    assert str(runtime.configuration) == "Controller.Idle"

    plain = SimulationRuntime(
        load_state_machine_from_text("state Root { state A; [*] -> A; }")
    )
    plain.cycle()
    assert isinstance(plain.current_state, State)
    assert str(plain.configuration) == "Root.A"
    assert plain.configuration.leaves == (plain.current_state,)


@pytest.mark.unittest
def test_configuration_is_unavailable_after_termination():
    """A terminated machine has no position to report."""
    runtime = SimulationRuntime(
        load_state_machine_from_text(
            "state Root { event Done; region R { [*] -> A; state A; A -> [*] : /Done; } }"
        )
    )
    runtime.cycle()
    assert str(runtime.configuration) == "Root{R: A}"
    runtime.cycle("Root.Done")
    assert runtime.is_ended
    with pytest.raises(SimulationRuntimeTerminalStateError):
        runtime.configuration
    with pytest.raises(SimulationRuntimeTerminalStateError):
        runtime.current_state


@pytest.mark.unittest
def test_cycle_count_history_and_delta_for_a_group_without_legal_entry():
    """A rejected whole cycle still advances the public counters and keeps variables."""
    model = load_state_machine_from_text(
        """
        def int g = 0;
        def int n = 0;
        state Root {
            region R1 { [*] -> X; state X { enter { n = n + 1; } } }
            region R2 { [*] -> Y : if [g != 0]; state Y; }
        }
        """
    )
    runtime = SimulationRuntime(model)
    result = runtime.cycle()
    assert result.delta is True
    assert runtime.cycle_count == 1
    assert runtime.vars == {"g": 0, "n": 0}
    assert runtime.history[-1]["delta"] is True
    assert runtime.history[-1]["state"] == "Root{R1: [init], R2: [init]}"
    assert str(runtime.configuration) == "Root{R1: [init], R2: [init]}"
    runtime.cycle()
    assert runtime.cycle_count == 2


@pytest.mark.unittest
def test_history_records_the_configuration_text_of_a_region_model():
    """The history keeps the whole position for models with regions."""
    runtime = _controller()
    runtime.cycle(inputs={"fault": 0, "requested": 0})
    runtime.cycle("Controller.Start", inputs={"fault": 0, "requested": 0})
    assert [item["state"] for item in runtime.history] == [
        "Controller.Idle",
        "Controller.Running{Safety: Watching, Motion: Off}",
    ]


def _paired_models(single_region):
    """Two models that differ only in whether the middle layer is a region."""
    if single_region:
        middle = "region Only { %s }"
    else:
        middle = "%s"
    body = """
            [*] -> A;
            state A { during { c = c + 1; } }
            state B { during { c = c + 10; } }
            A -> B : /Next;
            B -> A : /Back;
            B -> [*] : if [c >= 40];
        """
    return load_state_machine_from_text(
        """
        def int c = 0;
        state Root {
            event Next;
            event Back;
            [*] -> P;
            state P {
                enter { c = c + 100; }
                exit { c = c + 1000; }
                %s
            }
            state Done { during { c = c + 7; } }
            P -> Done;
        }
        """
        % (middle % body)
    )


@pytest.mark.unittest
def test_owner_with_one_region_runs_like_a_plain_composite_state():
    """Every short event sequence gives the same variables and leaf in both forms."""
    alphabet = [None, "Root.Next", "Root.Back"]
    for length in range(1, 6):
        for sequence in itertools.product(alphabet, repeat=length):
            plain = SimulationRuntime(_paired_models(False))
            region = SimulationRuntime(_paired_models(True))
            for event in sequence:
                events = [] if event is None else event
                plain_result = plain.cycle(events)
                region_result = region.cycle(events)
                assert plain.vars == region.vars, sequence
                assert plain_result.delta == region_result.delta, sequence
                assert plain.is_ended == region.is_ended, sequence
                if not plain.is_ended:
                    leaf = region.configuration.leaves[0]
                    assert plain.current_state.path[-1] == leaf.path[-1], sequence


@pytest.mark.unittest
def test_hot_start_stays_a_controlled_rejection_for_region_models():
    """Hot start of a model with regions is refused with a structured error."""
    model = load_state_machine_from_text(CONTROLLER)
    with pytest.raises(ModelValidationError, match="simulate hot start"):
        SimulationRuntime(
            model,
            initial_state="Controller.Idle",
            initial_vars={"permit": 0, "motor": 0},
            input_source={"fault": 0, "requested": 0},
        )


@pytest.mark.unittest
def test_position_dependent_event_names_are_refused_for_region_models():
    """Short names need a single current state; full paths keep working."""
    runtime = _controller()
    runtime.cycle(inputs={"fault": 0, "requested": 0})
    with pytest.raises(SimulationRuntimeEventError, match="full event path"):
        runtime.cycle("Start", inputs={"fault": 0, "requested": 0})
    with pytest.raises(SimulationRuntimeEventError, match="full event path"):
        runtime.cycle(".Start", inputs={"fault": 0, "requested": 0})
    runtime.cycle("Controller.Start", inputs={"fault": 0, "requested": 0})
    assert str(runtime.configuration).startswith("Controller.Running")


def _hook_runtime():
    runtime = SimulationRuntime(
        load_state_machine_from_text(FIVE_LEVEL_HOOKS),
        input_source={"fault": 0, "requested": 0},
    )
    calls = []

    def record(name):
        def handler(ctx):
            calls.append(
                (
                    name,
                    ctx.get_full_state_path(),
                    ".".join(ctx.active_leaf),
                    str(ctx.configuration),
                )
            )

        return handler

    for name, path in [
        ("Tick", "Controller.Tick"),
        ("GroupPre", "Controller.Running.GroupPre"),
        ("SafetyPre", "Controller.Running.Safety.SafetyPre"),
        ("Watch", "Controller.Running.Safety.Normal.Watch"),
        ("Drive", "Controller.Running.Motion.On.Drive"),
    ]:
        runtime.register_abstract_handler(path, record(name))
    return runtime, calls


@pytest.mark.unittest
def test_handlers_see_the_deepest_state_common_to_what_they_wrap():
    """Aspect handlers report the owner for a group and the leaf for one branch."""
    runtime, calls = _hook_runtime()
    inputs = {"fault": 0, "requested": 1}
    runtime.cycle(inputs=inputs)
    assert calls == [("Tick", "Controller.Idle", "Controller.Idle", "Controller.Idle")]
    runtime.cycle("Controller.Start", inputs=inputs)
    runtime.cycle(inputs=inputs)
    # From here on the machine rests in Running{Normal, On} and nothing moves.
    calls.clear()
    runtime.cycle(inputs=inputs)
    config = "Controller.Running{Safety: Normal, Motion: On}"
    running = "Controller.Running"
    normal = "Controller.Running.Safety.Normal"
    assert calls == [
        ("Tick", running, running, config),
        ("GroupPre", running, running, config),
        ("SafetyPre", normal, normal, config),
        ("Watch", normal, normal, config),
        ("Drive", "Controller.Running.Motion.On", "Controller.Running.Motion.On", config),
    ]


@pytest.mark.unittest
def test_handler_configuration_reflects_the_moment_of_the_call():
    """Earlier regions show their new place and later ones show ``[init]``."""
    runtime, calls = _hook_runtime()
    inputs = {"fault": 0, "requested": 1}
    runtime.cycle(inputs=inputs)
    calls.clear()
    runtime.cycle("Controller.Start", inputs=inputs)
    owner = "Controller.Running"
    normal = "Controller.Running.Safety.Normal"
    entering = "Controller.Running{Safety: Normal, Motion: [init]}"
    assert calls == [
        ("Tick", owner, owner, entering),
        ("GroupPre", owner, owner, entering),
        ("SafetyPre", normal, normal, entering),
        ("Watch", normal, normal, entering),
    ]
    calls.clear()
    runtime.cycle(inputs=inputs)
    before_move = "Controller.Running{Safety: Normal, Motion: Off}"
    after_move = "Controller.Running{Safety: Normal, Motion: On}"
    assert [(name, config) for name, _, _, config in calls] == [
        ("Tick", before_move),
        ("GroupPre", before_move),
        ("SafetyPre", before_move),
        ("Watch", before_move),
        ("Drive", after_move),
    ]


@pytest.mark.unittest
def test_trace_lists_regions_in_order_and_exits_in_reverse_order():
    """Entering follows the declaration order and a group exit runs backwards."""
    runtime = _controller()
    runtime.cycle(inputs={"fault": 0, "requested": 0})
    entered = runtime.cycle(
        "Controller.Start", inputs={"fault": 0, "requested": 0}, trace=True
    )
    assert [
        entry.state_path[-1] for entry in entered.trace if entry.kind == "state_enter"
    ] == ["Running", "Watching", "Off"]
    left = runtime.cycle(
        "Controller.Stop", inputs={"fault": 0, "requested": 0}, trace=True
    )
    assert [
        entry.state_path[-1] for entry in left.trace if entry.kind == "state_exit"
    ] == ["Off", "Watching", "Running"]


@pytest.mark.unittest
def test_nested_group_exits_inside_out_when_the_outer_group_is_preempted():
    """The deepest states leave first and every owner exits once."""
    model = load_state_machine_from_text(
        """
        def int order = 0;
        state Root {
            event Stop;
            [*] -> P;
            state P {
                exit { order = order * 10 + 5; }
                region A {
                    [*] -> Q;
                    state Q {
                        exit { order = order * 10 + 3; }
                        region A1 {
                            [*] -> L1;
                            state L1 { exit { order = order * 10 + 1; } }
                        }
                        region A2 {
                            [*] -> L2;
                            state L2 { exit { order = order * 10 + 2; } }
                        }
                    }
                }
                region B {
                    [*] -> N;
                    state N { exit { order = order * 10 + 4; } }
                }
            }
            state Idle;
            !P -> Idle : /Stop;
        }
        """
    )
    runtime = SimulationRuntime(model)
    runtime.cycle()
    assert str(runtime.configuration) == "Root.P{A: Q{A1: L1, A2: L2}, B: N}"
    runtime.cycle("Root.Stop")
    assert str(runtime.configuration) == "Root.Idle"
    # B first, then A: inside A, region A2 before A1, then Q, then P.
    assert runtime.vars["order"] == 4 * 10 ** 4 + 2 * 10 ** 3 + 1 * 10 ** 2 + 3 * 10 + 5


@pytest.mark.unittest
def test_owner_plain_during_actions_run_once_around_the_group():
    """Plain ``during before`` runs at group entry and ``during after`` when control returns."""
    model = load_state_machine_from_text(
        """
        def int trail = 0;
        state Root {
            event End1;
            event End2;
            [*] -> P;
            state P {
                during before { trail = trail * 10 + 1; }
                during after { trail = trail * 10 + 2; }
                region R1 {
                    [*] -> A;
                    state A { during { trail = trail * 10 + 3; } }
                    A -> [*] : /End1;
                }
                region R2 {
                    [*] -> B;
                    state B { during { trail = trail * 10 + 4; } }
                    B -> [*] : /End2;
                }
            }
            state Done;
            P -> Done;
        }
        """
    )
    runtime = SimulationRuntime(model)
    runtime.cycle()
    assert runtime.vars["trail"] == 1 * 100 + 3 * 10 + 4
    runtime.cycle("Root.End1")
    assert runtime.vars["trail"] == 134 * 10 + 4
    before = runtime.vars["trail"]
    runtime.cycle("Root.End2")
    assert str(runtime.configuration) == "Root.Done"
    assert runtime.vars["trail"] == before * 10 + 2


@pytest.mark.unittest
def test_regions_that_finish_while_initializing_hand_control_back_in_the_same_cycle():
    """A group whose regions all complete during entry continues past the owner."""
    model = load_state_machine_from_text(
        """
        def int n = 0;
        state Root {
            [*] -> P;
            state P {
                region R1 { [*] -> Skip1; pseudo state Skip1; Skip1 -> [*]; }
                region R2 { [*] -> Skip2; pseudo state Skip2; Skip2 -> [*]; }
            }
            state After { during { n = n + 1; } }
            P -> After;
        }
        """
    )
    runtime = SimulationRuntime(model)
    runtime.cycle()
    assert str(runtime.configuration) == "Root.After"
    assert runtime.vars["n"] == 1


@pytest.mark.unittest
def test_decision_diagnostics_work_on_a_region_model():
    """Capturing diagnostics does not break region execution."""
    runtime = _controller()
    runtime.cycle(inputs={"fault": 0, "requested": 0})
    result = runtime.cycle(
        "Controller.Start",
        inputs={"fault": 0, "requested": 0},
        diagnostics=True,
    )
    assert result.diagnostics.outcome == "cycle"
    assert result.diagnostics.state_after == ("Controller", "Running")
    assert str(runtime.configuration) == "Controller.Running{Safety: Watching, Motion: Off}"


@pytest.mark.unittest
def test_active_query_without_regions_runs_from_a_cold_start_only():
    """A model that only uses active() simulates, but hot start stays refused."""
    source = """
    def int seen = 0;
    state Root {
        [*] -> A;
        state A { during { if [active("Root.A")] { seen = seen + 1; } } }
    }
    """
    model = load_state_machine_from_text(source)
    runtime = SimulationRuntime(model)
    runtime.cycle()
    runtime.cycle()
    assert runtime.vars["seen"] == 2
    with pytest.raises(ModelValidationError, match="does not support active queries"):
        SimulationRuntime(
            model,
            initial_state="Root.A",
            initial_vars={"seen": 0, "__active_Root_A": 1},
        )
