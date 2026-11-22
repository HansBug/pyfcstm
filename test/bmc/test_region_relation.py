"""Trace relation of models that declare regions, through the public BMC API."""

import pytest
import z3

from pyfcstm.bmc import (
    REGION_DONE_ID,
    REGION_INACTIVE_ID,
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcBuildError,
    BmcEngine,
    UnsupportedBmcQuery,
    build_bmc_core_formula,
    check_runtime_safety,
    compile_bmc_query,
    region_frame_constraints,
)
from pyfcstm.model import load_state_machine_from_text

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
        region %(first)s
        region %(second)s
    }
    Idle -> Running : /Start;
}
"""

SAFETY = """{
            [*] -> Watching;
            state Watching {
                during { if [fault != 0] { permit = 0; } else { permit = 1; } }
            }
        }"""
MOTION = """{
            [*] -> Off;
            state Off { during { motor = 0; } }
            state On { during { motor = 1; } }
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [permit == 0 || requested == 0];
        }"""


def interlock(safety_first):
    first, second = ("Safety " + SAFETY, "Motion " + MOTION)
    if not safety_first:
        first, second = second, first
    return INTERLOCK % {"first": first, "second": second}


def core_of(text, bound, query=None):
    model = load_state_machine_from_text(text)
    query = query or "check reach <= %d: terminated();" % bound
    return build_bmc_core_formula(BmcEngine(model).prepare(query))


def pinned(core, cycles):
    """Pin events and inputs of every cycle; ``cycles`` is a list of dicts."""
    symbols = core.symbols
    pins = []
    for index, cycle in enumerate(cycles):
        events = set(cycle.get("events", ()))
        for event in core.context.domain.events:
            literal = symbols.event_input(index, event.path)
            pins.append(literal if event.path in events else z3.Not(literal))
        for name, value in cycle.get("inputs", {}).items():
            pins.append(symbols.step_inputs[index][name] == value)
    return pins


def frames(core, cycles, names=()):
    """Return the unique trace of a pinned run: state, positions and variables."""
    solver = z3.Solver()
    solver.add(core.core, *pinned(core, cycles))
    assert solver.check() == z3.sat
    model = solver.model()
    domain = core.context.domain
    ids = {entry.id: entry.path for entry in domain.states}
    ids.update(
        {
            REGION_DONE_ID: "done",
            REGION_INACTIVE_ID: "-",
            STATE_INIT_ID: "init",
            STATE_TERMINATE_ID: "end",
        }
    )
    result = []
    for frame in range(len(cycles) + 1):
        regions = {
            path: ids[
                model.eval(core.symbols.region_position(frame, path), True).as_long()
            ]
            for path in core.symbols.region_positions[0]
        }
        values = {
            name: model.eval(core.symbols.frame_var(frame, name), True).as_long()
            for name in names
        }
        result.append(
            (
                ids[model.eval(core.symbols.frame_state(frame), True).as_long()],
                regions,
                values,
            )
        )
    return result


def holds(core, cycles, constraint):
    solver = z3.Solver()
    solver.add(core.core, *pinned(core, cycles), constraint)
    return solver.check()


@pytest.mark.unittest
class TestOrderedAdvance:
    # The first cycle is the cold start; Start moves Idle to Running in the
    # second, a request switches the motor on in the third and the fault comes
    # in the fourth.
    CYCLES = [
        {"inputs": {"fault": 0, "requested": 0}},
        {"events": ["Controller.Start"], "inputs": {"fault": 0, "requested": 0}},
        {"inputs": {"fault": 0, "requested": 1}},
        {"inputs": {"fault": 1, "requested": 1}},
    ]

    def motor_after_the_fault_cycle(self, safety_first):
        core = core_of(interlock(safety_first), 4)
        return core, self.CYCLES, core.symbols.frame_var(4, "motor")

    def test_the_earlier_region_decides_before_the_later_one_looks(self):
        core, cycles, motor = self.motor_after_the_fault_cycle(True)
        # Safety runs first: the fault takes the permit away and Motion, which
        # runs afterwards, stops the motor in the very same cycle.
        assert holds(core, cycles, motor == 1) == z3.unsat
        assert holds(core, cycles, motor == 0) == z3.sat

    def test_swapping_the_regions_delays_the_stop_by_one_cycle(self):
        core, cycles, motor = self.motor_after_the_fault_cycle(False)
        # Motion runs first and still sees the permit of the previous cycle.
        assert holds(core, cycles, motor == 1) == z3.sat
        assert holds(core, cycles, motor == 0) == z3.unsat

    def test_the_trace_shows_positions_and_values_cycle_by_cycle(self):
        core = core_of(interlock(True), 4)
        trace = frames(core, self.CYCLES, names=("permit", "motor"))
        assert trace[0][0] == "init"
        assert trace[1][0] == "Controller.Idle"
        assert all(position == "-" for position in trace[1][1].values())
        assert trace[2][0] == "Controller.Running"
        assert trace[2][1] == {
            "Controller.Running.Motion": "Controller.Running.Motion.Off",
            "Controller.Running.Safety": "Controller.Running.Safety.Watching",
        }
        assert trace[3][1]["Controller.Running.Motion"].endswith(".On")
        assert trace[3][2] == {"permit": 1, "motor": 1}
        assert trace[4][1]["Controller.Running.Motion"].endswith(".Off")
        assert trace[4][2] == {"permit": 0, "motor": 0}


@pytest.mark.unittest
class TestEntryAndFrames:
    def test_regions_start_in_declaration_order_on_the_values_left_behind(self):
        text = """
        def int x = 0;
        state Root {
            region A { [*] -> P; state P { enter { x = x + 1; } } }
            region B { [*] -> Q; state Q { enter { x = x * 10 + 2; } } }
        }
        """
        trace = frames(core_of(text, 1), [{}], names=("x",))
        assert trace[1][2] == {"x": 12}

    def test_the_regions_hold_their_own_positions_and_the_owner_rests(self):
        text = "state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }"
        trace = frames(core_of(text, 1), [{}])
        assert trace[1][0] == "Root"
        assert trace[1][1] == {"Root.A": "Root.A.P", "Root.B": "Root.B.Q"}

    def test_a_resting_owner_never_has_every_region_done(self):
        text = """
        state Root {
            [*] -> Run;
            state Run {
                region A { [*] -> P; state P; P -> [*]; }
                region B { [*] -> Q; state Q; Q -> [*]; }
            }
            state Done;
        }
        """
        core = core_of(text, 3)
        symbols = core.symbols
        run = core.context.domain.state_path_to_id("Root.Run")
        for frame in range(4):
            both_done = z3.And(
                symbols.frame_state(frame) == run,
                symbols.region_position(frame, "Root.Run.A") == REGION_DONE_ID,
                symbols.region_position(frame, "Root.Run.B") == REGION_DONE_ID,
            )
            assert holds(core, [{}] * 3, both_done) == z3.unsat

    def test_regions_are_inactive_exactly_while_their_owner_does_not_rest(self):
        text = """
        state Root {
            [*] -> Run;
            state Run {
                region A { [*] -> P; state P; P -> [*]; }
                region B { [*] -> Q; state Q; Q -> [*]; }
            }
            state Done;
            Run -> Done;
        }
        """
        core = core_of(text, 2)
        trace = frames(core, [{}] * 2)
        # The cold start enters Run with its regions at work; in the next cycle
        # both regions finish and the owner hands over to Done at once.
        assert trace[1][0] == "Root.Run"
        assert trace[1][1]["Root.Run.A"] == "Root.Run.A.P"
        assert trace[2][0] == "Root.Done"
        assert all(position == "-" for position in trace[2][1].values())
        symbols = core.symbols
        resting = symbols.frame_state(2) == core.context.domain.state_path_to_id(
            "Root.Done"
        )
        active = symbols.region_position(2, "Root.Run.A") != REGION_INACTIVE_ID
        assert holds(core, [{}] * 2, z3.And(resting, active)) == z3.unsat

    def test_the_frame_constraints_are_part_of_the_core_and_can_be_read_back(self):
        text = "state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }"
        core = core_of(text, 1)
        constraints = region_frame_constraints(core.symbols, 1)
        assert constraints
        solver = z3.Solver()
        solver.add(core.core, *pinned(core, [{}]), z3.Not(z3.And(*constraints)))
        assert solver.check() == z3.unsat
        with pytest.raises(BmcBuildError):
            region_frame_constraints(core.symbols, 7)

    def test_an_event_that_a_region_owns_drives_that_region_only(self):
        text = """
        state Root {
            region A { event Tick; [*] -> P; state P; state Q; P -> Q : Tick; }
            region B { event Tick; [*] -> S; state S; state T; S -> T : Tick; }
        }
        """
        core = core_of(text, 2)
        assert {event.path for event in core.context.domain.events} == {
            "Root.A.Tick",
            "Root.B.Tick",
        }
        trace = frames(core, [{}, {"events": ["Root.A.Tick"]}])
        assert trace[2][1]["Root.A"] == "Root.A.Q"
        assert trace[2][1]["Root.B"] == "Root.B.S"


@pytest.mark.unittest
class TestCompletionAndContinuation:
    TEXT = """
    input int go;
    def int x = 0;
    state Root {
        [*] -> Run;
        state Run {
            region A { [*] -> P; state P; P -> [*]; }
        }
        state Done;
        Run -> Done : if [go > 0];
    }
    """

    def test_the_last_region_may_finish_only_if_the_owner_can_continue(self):
        core = core_of(self.TEXT, 2)
        blocked = frames(core, [{"inputs": {"go": 0}}, {"inputs": {"go": 0}}])
        assert blocked[1][1]["Root.Run.A"] == "Root.Run.A.P"
        assert blocked[2][0] == "Root.Run"

    def test_once_the_owner_can_continue_the_finish_and_the_hand_over_are_one_cycle(
        self,
    ):
        core = core_of(self.TEXT, 2)
        trace = frames(core, [{"inputs": {"go": 1}}, {"inputs": {"go": 1}}])
        # The cold start enters Run; in the next cycle P finishes the region
        # and Run hands over to Done at once.
        assert trace[1][0] == "Root.Run"
        assert trace[2][0] == "Root.Done"
        assert trace[2][1]["Root.Run.A"] == "-"

    def test_a_region_that_is_not_last_finishes_whatever_follows(self):
        text = """
        input int go;
        state Root {
            [*] -> Run;
            state Run {
                region A { [*] -> P; state P; P -> [*]; }
                region B { [*] -> Q; state Q; }
            }
            state Done;
            Run -> Done : if [go > 0];
        }
        """
        trace = frames(core_of(text, 2), [{"inputs": {"go": 0}}, {"inputs": {"go": 0}}])
        assert trace[1][1]["Root.Run.A"] == "Root.Run.A.P"
        # P -> [*] is taken in the second cycle although the owner cannot
        # continue: region B is still at work.
        assert trace[2][1]["Root.Run.A"] == "done"
        assert trace[2][1]["Root.Run.B"] == "Root.Run.B.Q"

    def test_plain_during_after_of_the_owner_runs_when_the_group_hands_control_back(
        self,
    ):
        text = """
        def int x = 0;
        state Root {
            [*] -> Run;
            state Run {
                during after { x = x + 100; }
                region A { [*] -> P; state P { enter { x = x + 1; } } P -> [*]; }
            }
            state Done;
            Run -> Done;
        }
        """
        trace = frames(core_of(text, 2), [{}, {}], names=("x",))
        # Entering P does not finish the region: the cold start only starts it.
        assert trace[1][0] == "Root.Run"
        assert trace[1][2] == {"x": 1}
        # The next cycle finishes the region; the owner's plain during-after runs
        # once as the group hands control back, then Run continues to Done.
        assert trace[2][0] == "Root.Done"
        assert trace[2][2] == {"x": 101}


@pytest.mark.unittest
class TestColdStartDelta:
    def test_a_group_that_cannot_start_leaves_a_cold_start_delta(self):
        text = """
        input int n;
        state Root {
            region A { [*] -> P : if [n > 3]; state P; }
            region B { [*] -> Q; state Q; }
        }
        """
        core = core_of(text, 2)
        solver = z3.Solver()
        solver.add(core.core, core.symbols.step_inputs[0]["n"] == 0)
        assert solver.check() == z3.sat
        model = solver.model()
        assert z3.is_true(model.eval(core.symbols.delta_flag(0), True))
        assert model.eval(core.symbols.frame_state(1), True).as_long() == STATE_INIT_ID
        solver = z3.Solver()
        solver.add(core.core, core.symbols.step_inputs[0]["n"] == 9)
        assert solver.check() == z3.sat
        model = solver.model()
        assert not z3.is_true(model.eval(core.symbols.delta_flag(0), True))
        assert model.eval(core.symbols.frame_state(1), True).as_long() != STATE_INIT_ID

    def test_a_cycle_that_only_runs_during_actions_is_a_fallback_cycle(self):
        text = """
        def int x = 0;
        state Root {
            region A { [*] -> P; state P { during { x = x + 1; } } }
            region B { [*] -> Q; state Q { during { x = x + 2; } } }
        }
        """
        core = core_of(text, 2)
        solver = z3.Solver()
        solver.add(core.core)
        assert solver.check() == z3.sat
        model = solver.model()
        assert not z3.is_true(model.eval(core.symbols.gamma_flag(0), True))
        assert z3.is_true(model.eval(core.symbols.gamma_flag(1), True))
        assert not z3.is_true(model.eval(core.symbols.delta_flag(1), True))

    def test_a_terminated_start_stays_terminated(self):
        text = "state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }"
        core = core_of(text, 2, "init terminated;\ncheck reach <= 2: terminated();")
        trace = frames(core, [{}, {}])
        assert [item[0] for item in trace] == ["end", "end", "end"]
        assert all(position == "-" for item in trace for position in item[1].values())


@pytest.mark.unittest
class TestNestedAndRepeatedGroups:
    NESTED = """
    def int t = 0;
    state Root {
        [*] -> P;
        state P {
            region A {
                [*] -> Q;
                state Q {
                    region A1 { [*] -> M1; state M1 { during { t = t * 10 + 1; } } }
                    region A2 { [*] -> M2; state M2 { during { t = t * 10 + 2; } } }
                }
            }
            region B { [*] -> N; state N { during { t = t * 10 + 3; } } }
        }
    }
    """

    def test_an_inner_group_advances_completely_before_the_next_outer_region(self):
        trace = frames(core_of(self.NESTED, 2), [{}, {}], names=("t",))
        assert trace[1][2] == {"t": 123}
        assert trace[2][2] == {"t": 123123}
        assert trace[2][1]["Root.P.A"] == "Root.P.A.Q"
        assert trace[2][1]["Root.P.A.Q.A1"] == "Root.P.A.Q.A1.M1"
        assert trace[2][1]["Root.P.A.Q.A2"] == "Root.P.A.Q.A2.M2"

    def test_a_nested_group_is_inactive_once_its_owner_has_left_the_branch(self):
        text = """
        input int leave;
        state Root {
            [*] -> P;
            state P {
                region A {
                    [*] -> Q;
                    state Q {
                        region A1 { [*] -> M1; state M1; M1 -> [*] : if [leave > 0]; }
                        region A2 { [*] -> M2; state M2; M2 -> [*] : if [leave > 0]; }
                    }
                    state R;
                    Q -> R;
                }
                region B { [*] -> N; state N; }
            }
        }
        """
        core = core_of(text, 2)
        trace = frames(core, [{"inputs": {"leave": 0}}, {"inputs": {"leave": 1}}])
        assert trace[1][1]["Root.P.A"] == "Root.P.A.Q"
        assert trace[1][1]["Root.P.A.Q.A1"] == "Root.P.A.Q.A1.M1"
        # Both inner regions finish, so Q continues to R and its regions go
        # inactive.
        assert trace[2][1]["Root.P.A"] == "Root.P.A.R"
        assert trace[2][1]["Root.P.A.Q.A1"] == "-"
        assert trace[2][1]["Root.P.A.Q.A2"] == "-"

    def test_an_ordinary_transition_of_a_nested_owner_waits_for_its_regions(self):
        text = """
        input int leave;
        state Root {
            [*] -> P;
            state P {
                region A {
                    [*] -> Q;
                    state Q {
                        region A1 { [*] -> M1; state M1; }
                        region A2 { [*] -> M2; state M2; }
                    }
                    state R;
                    Q -> R : if [leave > 0];
                }
                region B { [*] -> N; state N; }
            }
        }
        """
        core = core_of(text, 2)
        trace = frames(core, [{"inputs": {"leave": 0}}, {"inputs": {"leave": 1}}])
        # The guard alone does not take a group away: only its regions finishing,
        # or a forced transition, hands control back to the owner.
        assert trace[2][1]["Root.P.A"] == "Root.P.A.Q"

    def test_a_group_that_re_enters_itself_on_changing_values_stops_where_a_value_stops_it(
        self,
    ):
        text = """
        def int n = 0;
        state Root {
            [*] -> O;
            state O { region A { [*] -> p : if [n < 3]; pseudo state p; p -> [*]; } }
            state Done;
            O -> O effect { n = n + 1; };
            O -> Done;
        }
        """
        trace = frames(core_of(text, 1), [{}], names=("n",))
        assert trace[1][0] == "Root.Done"
        assert trace[1][2] == {"n": 2}

    def test_a_group_that_leads_straight_back_to_where_it_started_gives_way(self):
        text = """
        state Root {
            [*] -> O;
            state O { region A { [*] -> p; pseudo state p; p -> [*]; } }
            state Done;
            O -> O;
            O -> Done;
        }
        """
        trace = frames(core_of(text, 1), [{}], names=())
        assert trace[1][0] == "Root.Done"

    def test_a_loop_that_no_value_can_stop_cannot_be_bounded(self):
        text = """
        input int limit;
        def int n = 0;
        state Root {
            [*] -> O;
            state O { region A { [*] -> p : if [n < limit]; pseudo state p; p -> [*]; } }
            state Done;
            O -> O effect { n = n + 1; };
            O -> Done;
        }
        """
        with pytest.raises(BmcBuildError, match="re-enters its own group more than"):
            core_of(text, 1)


@pytest.mark.unittest
class TestScopeOfTheRelation:
    TEXT = (
        "state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }"
    )

    def test_a_model_without_regions_is_lowered_as_before(self):
        core = core_of(
            "def int x = 0; state Root { [*] -> A; state A { during { x = x + 1; } } }",
            2,
        )
        assert core.region_steps == ()
        assert core.symbols.region_positions == ()
        assert core.cone_slice is not None or core.diagnostics == ()

    def test_every_step_exposes_the_lowered_paths_of_its_units(self):
        core = core_of(self.TEXT, 2)
        assert [step.step_index for step in core.region_steps] == [0, 1]
        first = {case.case.unit_id for case in core.region_steps[0].cases}
        second = {case.case.unit_id for case in core.region_steps[1].cases}
        assert first == {"__init__"}
        # A cold start that stays a Delta repeats, so the cold unit recurs; the
        # resting owner has its regions' units and the continuation of the
        # group.
        assert second == {"__init__", "cont:Root", "work:Root.A.P", "work:Root.B.Q"}
        for relation in core.region_steps[1].cases:
            assert z3.is_bool(relation.implication)
            solver = z3.Solver()
            solver.add(core.core, relation.selector, z3.Not(relation.antecedent))
            assert solver.check() == z3.unsat

    def test_aspects_are_refused_with_a_controlled_error(self):
        text = """
        state Root {
            >> during before { }
            region A { [*] -> P; state P; }
            region B { [*] -> Q; state Q; }
        }
        """
        with pytest.raises(
            UnsupportedBmcQuery, match="aspects in a model with regions"
        ):
            core_of(text, 1)

    def test_a_plain_during_before_of_an_owner_is_refused(self):
        text = """
        def int x = 0;
        state Root {
            during before { x = x + 1; }
            region A { [*] -> P; state P; }
            region B { [*] -> Q; state Q; }
        }
        """
        with pytest.raises(UnsupportedBmcQuery, match="plain 'during before'"):
            core_of(text, 1)

    def test_a_hot_start_is_refused(self):
        with pytest.raises(
            UnsupportedBmcQuery, match="hot start of a model with regions"
        ):
            core_of(
                self.TEXT, 1, 'init state("Root");\ncheck reach <= 1: terminated();'
            )

    def test_properties_and_the_runtime_safety_check_are_refused(self):
        model = load_state_machine_from_text(self.TEXT)
        with pytest.raises(
            UnsupportedBmcQuery, match="property over a model with regions"
        ):
            compile_bmc_query(model, "check reach <= 1: terminated();")
        core = core_of(self.TEXT, 1)
        with pytest.raises(
            UnsupportedBmcQuery, match="runtime-safety check of a model with regions"
        ):
            check_runtime_safety(core)
