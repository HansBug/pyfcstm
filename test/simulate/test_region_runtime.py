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
    SimulationRuntimeDfsError,
    SimulationRuntimeEventError,
    SimulationRuntimeRegionQueryError,
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
def test_position_dependent_event_names_need_a_single_active_leaf():
    """Short names resolve from one leaf; several leaves accept only root-based names."""
    runtime = _controller()
    inputs = {"fault": 0, "requested": 0}
    runtime.cycle(inputs=inputs)
    # One active leaf: the parent-relative name resolves like it does without regions.
    runtime.cycle(".Start", inputs=inputs)
    assert str(runtime.configuration).startswith("Controller.Running")
    # Two active leaves: a position-dependent name would be ambiguous.
    with pytest.raises(SimulationRuntimeEventError, match="single active leaf"):
        runtime.cycle(".Stop", inputs=inputs)
    runtime.cycle("/Stop", inputs=inputs)
    assert str(runtime.configuration) == "Controller.Idle"
    runtime.cycle("Controller.Start", inputs=inputs)
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
def test_trace_lists_regions_in_order_and_exits_in_the_same_order():
    """Entering and a forced group exit both follow the declaration order."""
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
    ] == ["Watching", "Off", "Running"]


@pytest.mark.unittest
def test_nested_group_exits_inside_out_when_the_outer_group_is_forced_away():
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
    # A first: inside A, region A1 before A2, then Q; then B, then P.
    assert runtime.vars["order"] == 1 * 10 ** 4 + 2 * 10 ** 3 + 3 * 10 ** 2 + 4 * 10 + 5


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
def test_diagnostics_report_the_common_state_and_the_full_configuration():
    """The report keeps the single-path fields and adds the position as text."""
    runtime = _controller()
    first = runtime.cycle(inputs={"fault": 0, "requested": 0}, diagnostics=True)
    assert first.diagnostics.configuration_before == "Controller"
    assert first.diagnostics.configuration_after == "Controller.Idle"
    result = runtime.cycle(
        "Controller.Start",
        inputs={"fault": 0, "requested": 0},
        diagnostics=True,
    )
    report = result.diagnostics
    assert report.outcome == "cycle"
    assert report.state_before == ("Controller", "Idle")
    # Two regions are active, so the deepest common state is the owner.
    assert report.state_after == ("Controller", "Running")
    assert report.configuration_before == "Controller.Idle"
    assert report.configuration_after == (
        "Controller.Running{Safety: Watching, Motion: Off}"
    )
    payload = report.to_dict()
    assert payload["configuration_after"] == report.configuration_after
    assert "Configuration: Controller.Idle -> Controller.Running{" in str(report)
    assert str(runtime.configuration) == report.configuration_after


@pytest.mark.unittest
def test_diagnostics_of_a_delta_keep_the_configuration_unchanged():
    """A rejected cycle reports the same position before and after."""
    model = load_state_machine_from_text(
        """
        def int g = 0;
        state Root {
            region R1 { [*] -> X; state X; }
            region R2 { [*] -> Y : if [g != 0]; state Y; }
        }
        """
    )
    report = SimulationRuntime(model).cycle(diagnostics=True).diagnostics
    assert report.outcome == "delta"
    assert report.configuration_before == "Root{R1: [init], R2: [init]}"
    assert report.configuration_after == report.configuration_before


@pytest.mark.unittest
def test_diagnostics_of_ignored_calls_keep_or_drop_the_configuration():
    """An ignored call keeps the position; after termination there is none."""
    model = load_state_machine_from_text(
        """
        state Root {
            event Stop;
            region A { [*] -> X; state X { enter abstract Boom; } X -> [*] : /Stop; }
        }
        """
    )
    failing = SimulationRuntime(model, abstract_error_mode="raise")

    def boom(ctx):
        raise RuntimeError("handler failed")

    failing.register_abstract_handler("Root.A.X.Boom", boom)
    with pytest.raises(RuntimeError, match="handler failed"):
        failing.cycle()
    ignored = failing.cycle(diagnostics=True).diagnostics
    assert ignored.outcome == "noop"
    assert ignored.configuration_before == ignored.configuration_after == "Root{A: [init]}"

    finished = SimulationRuntime(
        load_state_machine_from_text(
            "state Root { event Stop; region A { [*] -> X; state X; X -> [*] : /Stop; } }"
        )
    )
    finished.cycle()
    ended = finished.cycle("Root.Stop", diagnostics=True).diagnostics
    assert ended.outcome == "terminated" and ended.configuration_after is None
    after = finished.cycle(diagnostics=True).diagnostics
    assert after.configuration_before is None and after.configuration_after is None
    assert "Configuration: (terminated) -> (terminated)" not in str(after)


@pytest.mark.unittest
def test_models_without_regions_keep_their_diagnostics_payload():
    """No configuration fields appear for a model without regions."""
    runtime = SimulationRuntime(
        load_state_machine_from_text("state Root { state A; [*] -> A; }")
    )
    report = runtime.cycle(diagnostics=True).diagnostics
    assert report.configuration_before is None
    assert "configuration_before" not in report.to_dict()
    assert "Configuration:" not in str(report)


@pytest.mark.unittest
def test_brief_stack_refuses_models_with_regions_and_points_to_configuration():
    """A flat stack would leave branches out, so the query refuses."""
    runtime = _controller()
    runtime.cycle(inputs={"fault": 0, "requested": 0})
    with pytest.raises(SimulationRuntimeRegionQueryError, match="configuration"):
        runtime.brief_stack
    plain = SimulationRuntime(
        load_state_machine_from_text("state Root { state A; [*] -> A; }")
    )
    plain.cycle()
    assert plain.brief_stack[-1][0] == ("Root", "A")


@pytest.mark.unittest
def test_active_query_without_regions_runs_from_a_cold_start_and_a_hot_start():
    """A model that only uses active() simulates, and hot start treats its flag like any variable."""
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
    # The flag is an ordinary variable: it comes with the checkpoint, and
    # whatever is given is what the machine runs on.
    for flag, expected in ((1, 1), (0, 0)):
        hot = SimulationRuntime(
            model,
            initial_state="Root.A",
            initial_vars={"seen": 0, "__active_Root_A": flag},
        )
        hot.cycle()
        assert hot.vars["seen"] == expected
    with pytest.raises(ValueError, match="must provide all variables"):
        SimulationRuntime(model, initial_state="Root.A", initial_vars={"seen": 0})


@pytest.mark.unittest
def test_owner_aspect_handler_reports_the_owner_while_one_region_is_done():
    """An aspect wrapping the whole group reports the owner even when a region is done."""
    model = load_state_machine_from_text(
        """
        def int n = 0;
        state Root {
            event Stop;
            >> during after abstract Done;
            region R1 { [*] -> A; state A { during { n = n + 1; } } }
            region R2 { [*] -> B; state B; B -> [*] : /Stop; }
        }
        """
    )
    runtime = SimulationRuntime(model)
    reports = []
    runtime.register_abstract_handler(
        "Root.Done", lambda ctx: reports.append(ctx.get_full_state_path())
    )
    runtime.cycle()
    # R1 never finishes, so the machine stays alive and the aspect sees the owner.
    runtime.cycle("Root.Stop")
    assert reports == ["Root", "Root"]
    assert str(runtime.configuration) == "Root{R1: A, R2: [done]}"


@pytest.mark.unittest
def test_forced_transition_of_a_group_can_end_the_machine():
    """A forced transition from the owner to ``[*]`` terminates the whole machine."""
    model = load_state_machine_from_text(
        """
        state Root {
            event Stop;
            [*] -> P;
            state P {
                region R1 { [*] -> A; state A; }
                region R2 { [*] -> B; state B; }
            }
            !P -> [*] : /Stop;
        }
        """
    )
    runtime = SimulationRuntime(model)
    runtime.cycle()
    assert str(runtime.configuration) == "Root.P{R1: A, R2: B}"
    runtime.cycle("Root.Stop")
    assert runtime.is_ended


@pytest.mark.unittest
def test_preempted_group_runs_plain_after_actions_of_composites_inside_a_region():
    """A composite below a region leaves with its ``during after`` before its ``exit``."""
    model = load_state_machine_from_text(
        """
        def int trail = 0;
        state Root {
            event Stop;
            [*] -> P;
            state P {
                region R {
                    [*] -> C;
                    state C {
                        during after { trail = trail * 10 + 2; }
                        exit { trail = trail * 10 + 3; }
                        [*] -> L;
                        state L { exit { trail = trail * 10 + 1; } }
                    }
                }
            }
            state Idle;
            !P -> Idle : /Stop;
        }
        """
    )
    runtime = SimulationRuntime(model)
    runtime.cycle()
    runtime.cycle("Root.Stop")
    assert str(runtime.configuration) == "Root.Idle"
    assert runtime.vars["trail"] == 123


@pytest.mark.unittest
def test_machine_that_ends_while_starting_has_no_position():
    """A model whose initial chain leaves the root terminates on the first cycle."""
    runtime = SimulationRuntime(
        load_state_machine_from_text(
            "state Root { pseudo state P; [*] -> P; P -> [*]; }"
        )
    )
    runtime.cycle()
    assert runtime.is_ended
    with pytest.raises(SimulationRuntimeTerminalStateError):
        runtime.configuration


@pytest.mark.unittest
def test_forced_transition_of_an_ancestor_takes_a_nested_group_away():
    """An ancestor's forced transition preempts the group and the owner's plain actions see it."""
    model = load_state_machine_from_text(
        """
        state Root {
            event Stop;
            [*] -> Top;
            state Top {
                [*] -> P;
                state P {
                    during before abstract Pre;
                    during after abstract Post;
                    region R1 { [*] -> A; state A; }
                    region R2 { [*] -> B; state B; }
                }
            }
            state Idle;
            !Top -> Idle : /Stop;
        }
        """
    )
    runtime = SimulationRuntime(model)
    seen = []
    for name in ("Pre", "Post"):
        runtime.register_abstract_handler(
            "Root.Top.P." + name,
            lambda ctx, name=name: seen.append(
                (name, str(ctx.configuration), ctx.configuration.mode)
            ),
        )
    runtime.cycle()
    assert str(runtime.configuration) == "Root.Top.P{R1: A, R2: B}"
    runtime.cycle("Root.Stop")
    assert str(runtime.configuration) == "Root.Idle"
    assert seen == [
        ("Pre", "Root.Top.P{R1: [init], R2: [init]}", "transient"),
        ("Post", "Root.Top.P{R1: [done], R2: [done]}", "transient"),
    ]


@pytest.mark.unittest
def test_one_cycle_counts_once_however_many_regions_advance():
    """The public counter and the history grow by one per cycle."""
    runtime = _controller()
    inputs = {"fault": 0, "requested": 1}
    runtime.cycle(inputs=inputs)
    runtime.cycle("Controller.Start", inputs=inputs)
    for expected in range(3, 6):
        runtime.cycle(inputs=inputs)
        assert runtime.cycle_count == expected
        assert len(runtime.history) == expected


@pytest.mark.unittest
def test_region_declaration_order_is_kept_by_export_and_reload():
    """Exporting a model and loading it again keeps the execution order of regions."""
    source = """
    def int x = 0;
    state Root {
        [*] -> P;
        state P {
            region Second { [*] -> B; state B { during { x = x * 2; } } }
            region First { [*] -> A; state A { during { x = x + 1; } } }
        }
    }
    """
    model = load_state_machine_from_text(source)
    exported = str(model.to_ast_node())
    reloaded = load_state_machine_from_text(exported)
    assert list(reloaded.root_state.substates["P"].regions) == ["Second", "First"]
    first, second = SimulationRuntime(model), SimulationRuntime(reloaded)
    for _ in range(3):
        first.cycle()
        second.cycle()
        assert first.vars == second.vars
        assert str(first.configuration) == str(second.configuration)


@pytest.mark.unittest
def test_exit_handlers_during_a_group_exit_still_see_the_state_being_left():
    """A handler on an exit action runs while its state is still in the configuration."""
    model = load_state_machine_from_text(
        """
        state Root {
            event Kill;
            [*] -> Run;
            state Run {
                region A {
                    [*] -> Mid;
                    state Mid {
                        [*] -> L;
                        during after abstract MidAfter;
                        state L { exit abstract LeaveL; }
                    }
                }
                region B { [*] -> S; state S; }
            }
            state Off;
            !Run -> Off : /Kill;
        }
        """
    )
    runtime = SimulationRuntime(model)
    seen = []
    for name in ("Root.Run.A.Mid.L.LeaveL", "Root.Run.A.Mid.MidAfter"):
        runtime.register_abstract_handler(
            name, lambda ctx, name=name: seen.append(str(ctx.configuration))
        )
    runtime.cycle()
    runtime.cycle("Root.Kill")
    assert str(runtime.configuration) == "Root.Off"
    assert seen == [
        # Regions leave in declaration order, so B still rests in S when A leaves.
        "Root.Run{A: Mid.L, B: S}",
        "Root.Run{A: Mid, B: S}",
    ]


@pytest.mark.unittest
def test_owner_plain_before_waits_for_the_first_real_child_entry():
    """A region that finishes through pseudo states does not consume the owner's action."""
    source = """
    def int w = 0;
    state Root {
        [*] -> P;
        state P {
            during before { w = w + 10; }
            %s
        }
    }
    """
    finishing = "region A { [*] -> X; pseudo state X; X -> [*]; }"
    working = "region B { [*] -> S; state S { during { w = w + 5; } } }"
    for body in (finishing + working, working + finishing):
        runtime = SimulationRuntime(load_state_machine_from_text(source % body))
        runtime.cycle()
        assert runtime.vars["w"] == 15, body


@pytest.mark.unittest
def test_aspect_position_of_a_one_region_owner_matches_a_plain_composite():
    """Wrapping one branch reports its leaf, with or without the region."""
    template = """
    state Root {
        >> during before abstract Tick;
        [*] -> P;
        state P { %s }
    }
    """
    positions = []
    for body in ("[*] -> L; state L;", "region R { [*] -> L; state L; }"):
        runtime = SimulationRuntime(load_state_machine_from_text(template % body))
        runtime.register_abstract_handler(
            "Root.Tick", lambda ctx: positions.append(ctx.get_full_state_path())
        )
        runtime.cycle()
    assert positions == ["Root.P.L", "Root.P.R.L"]


@pytest.mark.unittest
def test_short_event_names_resolve_from_the_root_before_the_first_cycle():
    """With no active leaf yet, a name resolves from the root as without regions."""
    model = load_state_machine_from_text(
        """
        state Root {
            event Go;
            [*] -> P;
            state P { region R { [*] -> A; state A; state B; A -> B : /Go; } }
        }
        """
    )
    runtime = SimulationRuntime(model)
    runtime.cycle("Go")
    assert str(runtime.configuration) == "Root.P{R: A}"


@pytest.mark.unittest
def test_handler_runs_while_a_region_initial_chain_starts_with_a_pseudo_state():
    """The owner's plain action may run between two pseudo-state hops of a region."""
    model = load_state_machine_from_text(
        """
        state Root {
            [*] -> Owner;
            state Owner {
                during before abstract Pre;
                region R { [*] -> P; pseudo state P; state L; P -> L; }
            }
        }
        """
    )
    runtime = SimulationRuntime(model)
    seen = []
    runtime.register_abstract_handler(
        "Root.Owner.Pre", lambda ctx: seen.append(str(ctx.configuration))
    )
    runtime.cycle()
    assert str(runtime.configuration) == "Root.Owner{R: L}"
    assert seen == ["Root.Owner{R: [init]}"]


# The transitions of S60 and S62 and the first one of S59 are what two forced
# declarations of a random model used to expand into. A forced transition is no
# longer taken from the pseudo state S60, so they are written out here.
UNSETTLED_REGION_MODEL = """def int x = 0;
def int y = 0;
state Root {
    event E2; event E3;
    [*] -> S3;
    state S3 {
        region R27 { [*] -> S30; state S30 { during { y = y * 2 + 1; } } }
        region R53 {
            [*] -> S54;
            state S54;
            state S55 {
                enter { x = x + 1; }
                region R58 {
                    [*] -> S59;
                    state S59 {
                        [*] -> S60;
                        pseudo state S60;
                        state S62;
                        S60 -> [*] : /E2;
                        S60 -> S62 : /E2;
                        S62 -> [*] : /E2;
                        S62 -> S62 : /E2;
                    }
                    S59 -> S59 : /E2;
                    S59 -> [*] : if [x % 4 == 1];
                    S59 -> S59 : if [y % 3 == 1] effect { x = x + 1; }
                }
                region R65 { [*] -> S66; state S66; }
            }
            S54 -> S55 : if [x >= 0] effect { x = x + 1; }
        }
    }
    S3 -> S3 : /E3;
}"""


@pytest.mark.unittest
def test_cycle_without_a_stable_region_position_is_a_delta():
    """A chain that cannot settle a region makes the whole cycle a Delta."""
    runtime = SimulationRuntime(load_state_machine_from_text(UNSETTLED_REGION_MODEL))
    runtime.cycle()
    runtime.cycle(["Root.E2", "Root.E3"])
    before = (str(runtime.configuration), dict(runtime.vars))
    result = runtime.cycle(["Root.E2", "Root.E3"])
    assert result.delta is True
    assert (str(runtime.configuration), dict(runtime.vars)) == before
    assert runtime.configuration.mode == "stable"
    runtime.cycle()


@pytest.mark.unittest
def test_looping_region_entry_falls_back_to_the_next_candidate():
    """An entry whose region loops without a stable exit is rejected like any dead end."""
    source = """
    state Root {
        [*] -> S0;
        pseudo state S0;
        state S1 { BODY }
        S0 -> S1;
        S0 -> [*];
    }
    """
    looping = "[*] -> S3; pseudo state S3; S3 -> S3;"
    for body in (looping, "region R { " + looping + " }"):
        runtime = SimulationRuntime(
            load_state_machine_from_text(source.replace("BODY", body))
        )
        runtime.cycle()
        assert runtime.is_ended


@pytest.mark.unittest
def test_unbounded_reentry_of_a_group_reports_the_safety_limit():
    """A transition that keeps re-entering a group ends in the documented error."""
    source = """
    def int x = 0;
    state Root {
        [*] -> S0;
        state S0 { BODY }
        S0 -> S0 : if [x >= 0] effect { x = x + 1; }
    }
    """
    exits = "[*] -> P; pseudo state P; P -> [*];"
    for body in (exits, "region R { " + exits + " }"):
        runtime = SimulationRuntime(
            load_state_machine_from_text(source.replace("BODY", body))
        )
        with pytest.raises(SimulationRuntimeDfsError):
            runtime.cycle()


@pytest.mark.unittest
def test_looping_group_reentry_without_a_fallback_reports_a_livelock():
    """Re-entering a group at the same position with nothing else to try is an error."""
    source = """
    def int b = 0;
    state Root {
        [*] -> Idle;
        state Idle;
        state P {
            region R {
                [*] -> X;
                state X { region RR { [*] -> p; pseudo state p; p -> [*]; } }
                X -> X effect { b = 3; }
            }
        }
        Idle -> P :: Go;
    }
    """
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    runtime.cycle()
    with pytest.raises(SimulationRuntimeDfsError, match="suspected loop"):
        runtime.cycle("Root.Idle.Go")
    assert str(runtime.configuration) == "Root.Idle"
    assert runtime.vars["b"] == 0


@pytest.mark.unittest
def test_unbounded_reentry_is_reported_even_when_the_caller_stack_is_deep():
    """Calling cycle() from deep inside the caller still gives the documented error."""
    import inspect
    import sys

    source = """
    def int x = 0;
    state Root {
        [*] -> S0;
        state S0 { region R { [*] -> P; pseudo state P; P -> [*]; } }
        S0 -> S0 : if [x >= 0] effect { x = x + 1; }
    }
    """
    runtime = SimulationRuntime(load_state_machine_from_text(source))

    def call_at_depth(depth):
        return runtime.cycle() if depth == 0 else call_at_depth(depth - 1)

    # Leave too little stack for the engine to reach its own nesting limit.
    spare = 300
    depth = sys.getrecursionlimit() - len(inspect.stack()) - spare
    with pytest.raises(SimulationRuntimeDfsError):
        call_at_depth(depth)
    assert runtime.cycle_count == 0
    assert runtime.vars["x"] == 0
    assert str(runtime.configuration) == "Root"
    with pytest.raises(SimulationRuntimeDfsError, match="nested deeper"):
        runtime.cycle()


@pytest.mark.unittest
def test_model_without_regions_still_raises_the_interpreter_error_on_a_deep_stack():
    """Running out of call stack is only reworded for models that have regions."""
    import inspect
    import sys

    # A guard this long needs a few hundred nested calls to evaluate.
    guard = " + ".join(["x"] * 150)
    source = (
        "def int x = 0; state Root { [*] -> A; state A; state B; "
        "A -> B : if [%s > 0]; }" % guard
    )
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    runtime.cycle()

    def call_at_depth(depth):
        return runtime.cycle() if depth == 0 else call_at_depth(depth - 1)

    spare = 120
    depth = sys.getrecursionlimit() - len(inspect.stack()) - spare
    with pytest.raises(RecursionError):
        call_at_depth(depth)
    assert runtime.current_state.path == ("Root", "A")
    assert runtime.cycle_count == 1
    runtime.cycle()
    assert runtime.cycle_count == 2


@pytest.mark.unittest
def test_root_group_that_cannot_start_is_not_started_again_on_changed_values():
    """A failed start of a root that owns regions leaves no trace of the attempt."""
    source = """
    def int y = 0;
    state Root {
        region A {
            [*] -> A1;
            state A1 { enter { y = y + 1; } during abstract Tick; }
        }
        region B {
            [*] -> B1 : if [y == 2];
            state B1;
        }
    }
    """
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    calls = []
    runtime.register_abstract_handler("Root.A.A1.Tick", lambda ctx: calls.append(ctx.vars["y"]))
    # B can only start once A has written twice, which a single start never does.
    for _ in range(3):
        result = runtime.cycle(trace=True)
        assert result.delta
        assert result.trace == ()
        assert runtime.vars["y"] == 0
        assert str(runtime.configuration) == "Root{A: [init], B: [init]}"
    assert calls == []


def _chained_groups(count):
    states = "".join(
        "state P%d { region R { [*] -> p; pseudo state p; p -> [*]; } } " % index
        for index in range(count)
    )
    edges = "".join("P%d -> P%d; " % (index, index + 1) for index in range(count - 1))
    return "state Root { [*] -> P0; %s state Done; %s P%d -> Done; }" % (
        states,
        edges,
        count - 1,
    )


def _nested_groups(depth):
    body = "state L%d { during { t = t + 1; } }" % depth
    for index in range(depth - 1, -1, -1):
        body = "state L%d { region R%d { [*] -> L%d; %s } }" % (
            index,
            index,
            index + 1,
            body,
        )
    return "def int t = 0; state Root { [*] -> L0; %s }" % body


@pytest.mark.unittest
@pytest.mark.parametrize("build", [_chained_groups, _nested_groups])
def test_diagnostics_grow_with_the_model_and_not_with_repeated_checks(build):
    """A check that repeats within a cycle is expanded once in the report."""
    sizes = {}
    for count in (4, 8, 16):
        observed = SimulationRuntime(load_state_machine_from_text(build(count)))
        plain = SimulationRuntime(load_state_machine_from_text(build(count)))
        report = observed.cycle(diagnostics=True).diagnostics
        plain.cycle()
        assert str(observed.configuration) == str(plain.configuration)
        assert observed.vars == plain.vars
        assert report.configuration_after == str(plain.configuration)
        sizes[count] = len(report.decisions)
    # Twice the owners may cost a few times the checks, never a power of them.
    assert sizes[8] <= 4 * sizes[4]
    assert sizes[16] <= 4 * sizes[8]


@pytest.mark.unittest
@pytest.mark.parametrize("build", [_chained_groups, _nested_groups])
def test_more_groups_than_the_nesting_limit_in_one_cycle_are_reported(build):
    """Sixty-four groups entered in one cycle work; one more names the limit and its causes."""
    within = SimulationRuntime(load_state_machine_from_text(build(64)))
    within.cycle()
    assert within.cycle_count == 1

    beyond = SimulationRuntime(load_state_machine_from_text(build(65)))
    with pytest.raises(
        SimulationRuntimeDfsError,
        match=r"limit \(64\) within one cycle.*more than 64 groups inside one "
        r"another or one after another in the same cycle.*without bound",
    ):
        beyond.cycle()
    assert beyond.cycle_count == 0
    assert str(beyond.configuration) == "Root"


@pytest.mark.unittest
def test_diagnostics_describe_a_combo_transition_declared_in_a_region():
    """A combo transition owned by a region is reported with the trigger as written."""
    source = """
    def int n = 0;
    state Root {
        event Go;
        event Arm;
        [*] -> P;
        state P {
            region A {
                [*] -> A1;
                state A1;
                state A2;
                A1 -> A2 : /Go + /Arm effect { n = n + 1; };
            }
            region B { [*] -> B1; state B1; }
        }
    }
    """
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    runtime.cycle()
    report = runtime.cycle(["Root.Go", "Root.Arm"], diagnostics=True).diagnostics
    assert str(runtime.configuration) == "Root.P{A: A2, B: B1}"
    assert runtime.vars["n"] == 1
    triggers = {
        origin["trigger"]
        for decision in report.decisions
        for origin in decision.combo_origins
    }
    assert triggers == {"/Go + /Arm"}
    assert "/Go + /Arm" in report.to_text(verbose=True)


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["body", "position"],
    [
        ("region R { %s }", "Root.Q{R: Rest}"),
        ("%s", "Root.Q.Rest"),
    ],
)
def test_candidate_that_only_leads_back_to_its_own_start_gives_way(body, position):
    """Finishing would only re-enter the owner at the same point, so the region rests."""
    inner = "[*] -> j; pseudo state j; state Rest; j -> [*]; j -> Rest;"
    source = "state Root { [*] -> Q; state Q { %s } Q -> Q; }" % (body % inner)
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    for _ in range(2):
        result = runtime.cycle()
        assert not result.delta
        assert str(runtime.configuration) == position


CHOICE_IN_COMPOSITE = """
state Root {
    event Go;
    [*] -> Idle;
    state Idle { exit abstract IdleOut; }
    state Q {
        enter abstract QIn;
        exit abstract QOut;
        region R {
            [*] -> C;
            state C {
                [*] -> p;
                [*] -> Stay;
                pseudo state p;
                state Stay;
                p -> [*];
            }
            C -> [*];
        }
    }
    Idle -> Q : /Go;
    Q -> Q;
}
"""


@pytest.mark.unittest
def test_choice_in_a_composite_of_a_region_is_decided_alike_when_tried_and_taken():
    """What is decided while a cycle is tried is what the cycle then does."""
    runtime = SimulationRuntime(load_state_machine_from_text(CHOICE_IN_COMPOSITE))
    calls = []
    for path in ("Root.Idle.IdleOut", "Root.Q.QIn", "Root.Q.QOut"):
        runtime.register_abstract_handler(
            path, lambda ctx, path=path: calls.append(path.split(".")[-1])
        )
    runtime.cycle()
    result = runtime.cycle("Root.Go", diagnostics=True)
    # Leaving C through p only leads back into Q at the same point, so C
    # takes its second initial transition and nothing is entered twice.
    assert not result.delta
    assert str(runtime.configuration) == "Root.Q{R: C.Stay}"
    assert calls == ["IdleOut", "QIn"]
    top = [d for d in result.diagnostics.decisions if d.parent_id is None]
    tried = [(d.transition_label, d.outcome) for d in top if d.phase == "preflight"]
    taken = [(d.transition_label, d.outcome) for d in top if d.phase == "execution"]
    assert tried == taken


@pytest.mark.unittest
def test_aspects_run_while_trying_a_rejected_way_are_not_counted_for_the_next_way():
    """A dead first way through a pseudo state leaves the aspect to the way that works."""
    source = """
    def int x = 0;
    state Root {
        >> during before { x = 1; }
        [*] -> Q;
        state Q {
            region R {
                [*] -> j;
                pseudo state j;
                state O2 {
                    region X { [*] -> X1; state X1; }
                    region Y { [*] -> Y1 : if [x == 5]; state Y1; }
                }
                j -> O2;
                j -> [*];
            }
        }
        state O3 {
            region M { [*] -> M1; state M1; }
            region N { [*] -> N1 : if [x == 1]; state N1; }
        }
        Q -> O3;
    }
    """
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    result = runtime.cycle()
    assert not result.delta
    assert str(runtime.configuration) == "Root.O3{M: M1, N: N1}"
    assert runtime.vars["x"] == 1


_LONG_GUARD = " + ".join(["x"] * 150)


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["source", "position"],
    [
        # The long guard sits on a transition of a plain state.
        (
            "def int x = 0; state Root { [*] -> A; state A; state B; "
            "A -> B : if [%s > 0]; "
            "state Q { region R { [*] -> L; state L; } } B -> Q; }" % _LONG_GUARD,
            "Root.A",
        ),
        # The long guard sits on the initial transition of a region, so the
        # stack runs out inside one group entry that nests in no other.
        (
            "def int x = 0; state Root { [*] -> A; state A; "
            "state Q { region R { [*] -> L : if [%s >= 0]; state L; } } "
            "A -> Q; }" % _LONG_GUARD,
            "Root.A",
        ),
    ],
)
def test_stack_overflow_without_nested_group_entries_keeps_the_interpreter_error(
    source, position
):
    """Only group entries nested in each other can come from re-entering a group."""
    import inspect
    import sys

    runtime = SimulationRuntime(load_state_machine_from_text(source))
    runtime.cycle()
    assert str(runtime.configuration) == position

    def call_at_depth(depth):
        return runtime.cycle() if depth == 0 else call_at_depth(depth - 1)

    spare = 120
    depth = sys.getrecursionlimit() - len(inspect.stack()) - spare
    with pytest.raises(RecursionError):
        call_at_depth(depth)
    assert str(runtime.configuration) == position
    assert runtime.cycle_count == 1
    runtime.cycle()
    assert runtime.cycle_count == 2


@pytest.mark.unittest
def test_loop_report_names_the_owner_and_not_its_region():
    """A region is not a state, so a loop through it is reported at its owner."""
    source = (
        "state Root { [*] -> Q; state Q { region R { [*] -> j; pseudo state j; "
        "j -> [*]; } } Q -> Q; }"
    )
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    with pytest.raises(SimulationRuntimeDfsError) as info:
        runtime.cycle()
    assert "Root.Q -> Root.Q" in str(info.value)
    assert "Root.Q.R" not in str(info.value)


TWO_FORCED = """
def int seq = 0;
state Root {
    event Alpha;
    event Beta;
    [*] -> P;
    state P {
        region A { [*] -> A1; state A1 { exit { seq = seq * 10 + 1; } } }
        region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 2; } } }
    }
    state ToAlpha { enter { seq = seq * 10 + 7; } }
    state ToBeta { enter { seq = seq * 10 + 8; } }
    !P -> ToAlpha : /Alpha;
    !P -> ToBeta : /Beta;
}
"""


@pytest.mark.unittest
def test_forced_group_exit_uses_the_event_once_and_traces_the_exits_in_order():
    """The event counts once however many levels carry the declaration out."""
    runtime = SimulationRuntime(load_state_machine_from_text(TWO_FORCED))
    runtime.cycle()
    result = runtime.cycle("Root.Beta", trace=True)
    assert result.consumed_events == ("Root.Beta",)
    assert result.unconsumed_events == ()
    assert [
        (entry.kind, entry.state_path[-1])
        for entry in result.trace
        if entry.kind in ("state_exit", "state_enter")
    ] == [
        ("state_exit", "A1"),
        ("state_exit", "B1"),
        ("state_exit", "P"),
        ("state_enter", "ToBeta"),
    ]
    assert str(runtime.configuration) == "Root.ToBeta"
    assert runtime.vars["seq"] == 128


@pytest.mark.unittest
def test_two_forced_events_in_one_cycle_take_the_earlier_declaration_only():
    """A second event of another declaration stays unused, whichever order it is given in."""
    for events in (["Root.Alpha", "Root.Beta"], ["Root.Beta", "Root.Alpha"]):
        runtime = SimulationRuntime(load_state_machine_from_text(TWO_FORCED))
        runtime.cycle()
        result = runtime.cycle(events)
        assert str(runtime.configuration) == "Root.ToAlpha"
        assert result.consumed_events == ("Root.Alpha",)
        assert result.unconsumed_events == ("Root.Beta",)
        assert runtime.vars["seq"] == 127


@pytest.mark.unittest
def test_diagnostics_of_a_forced_group_exit_name_the_candidate_that_was_taken():
    """The leaf's exit-group transition is a decision like any other."""
    runtime = SimulationRuntime(load_state_machine_from_text(TWO_FORCED))
    runtime.cycle()
    report = runtime.cycle("Root.Alpha", diagnostics=True).diagnostics
    committed = [
        item
        for item in report.decisions
        if item.outcome == "selected" or item.outcome == "committed"
    ]
    assert any(item.transition_label.endswith("A1->[*]") for item in committed)
    assert "A1->[*]" in str(report)
    assert report.to_dict()["configuration_after"] == "Root.ToAlpha"
