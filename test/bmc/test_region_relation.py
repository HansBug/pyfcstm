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
from pyfcstm.bmc.region_relation import build_region_core_formula
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeExpressionError

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
class TestAspectsAndPlainBefore:
    """Values below were obtained from the simulator on the same machines."""

    def values(self, text, cycles, names):
        core = core_of(text, cycles)
        return [item[2] for item in frames(core, [{}] * cycles, names=names)[1:]]

    def test_an_after_aspect_runs_when_its_branch_ends_so_the_next_region_sees_it(self):
        text = """
        def int x = 0;
        def int seen = 0;
        def int tail = 0;
        state Root {
            [*] -> P;
            state P {
                >> during after { tail = x * 100 + seen; }
                region R1 {
                    >> during after { x = x + 1; }
                    [*] -> A;
                    state A { during { x = x + 10; } }
                }
                region R2 { [*] -> B; state B { during { seen = x; } } }
            }
        }
        """
        assert self.values(text, 2, ("x", "seen", "tail")) == [
            {"x": 11, "seen": 11, "tail": 1111},
            {"x": 22, "seen": 22, "tail": 2222},
        ]

    def test_after_aspects_of_several_scopes_run_innermost_first(self):
        text = """
        def int v = 0;
        state Root {
            [*] -> P;
            state P {
                >> during after { v = v * 5 + 1; }
                region R {
                    >> during after { v = v + 3; }
                    [*] -> C;
                    state C {
                        >> during after { v = v * 2; }
                        [*] -> L;
                        state L { during { v = 1; } }
                    }
                }
            }
        }
        """
        assert self.values(text, 2, ("v",)) == [{"v": 26}, {"v": 26}]

    def test_every_scope_runs_its_before_once_outside_in_and_its_after_inside_out(self):
        text = """
        def int seq = 0;
        state Root {
            [*] -> P;
            state P {
                >> during before { seq = seq * 10 + 1; }
                >> during after { seq = seq * 10 + 9; }
                region A {
                    >> during before { seq = seq * 10 + 2; }
                    >> during after { seq = seq * 10 + 8; }
                    [*] -> Q;
                    state Q {
                        >> during before { seq = seq * 10 + 3; }
                        >> during after { seq = seq * 10 + 7; }
                        region X { [*] -> X1; state X1 { during { seq = seq * 10 + 4; } } }
                        region Y { [*] -> Y1; state Y1 { during { seq = seq * 10 + 5; } } }
                    }
                }
                region B { [*] -> B1; state B1 { during { seq = seq * 10 + 6; } } }
            }
        }
        """
        assert self.values(text, 1, ("seq",)) == [{"seq": 123457869}]

    def test_a_leaf_without_a_during_action_still_triggers_the_aspects_above_it(self):
        text = """
        def int tick = 0;
        def int r1 = 0;
        def int r2 = 0;
        state Root {
            event End;
            >> during before { tick = tick + 1; }
            [*] -> P;
            state P {
                region R1 { >> during before { r1 = r1 + 1; } [*] -> A; state A; A -> [*] : /End; }
                region R2 { >> during before { r2 = r2 + 1; } [*] -> B; state B; }
            }
        }
        """
        # The owner and the root run once per cycle, each region once for its own
        # working leaf.
        assert self.values(text, 2, ("tick", "r1", "r2")) == [
            {"tick": 1, "r1": 1, "r2": 1},
            {"tick": 2, "r1": 2, "r2": 2},
        ]

    def test_the_plain_before_of_an_owner_runs_once_for_the_whole_group(self):
        text = """
        def int seq = 0;
        state Root {
            [*] -> P;
            state P {
                during before { seq = seq * 10 + 1; }
                region A { [*] -> A1 effect { seq = seq * 10 + 2; }; state A1 { enter { seq = seq * 10 + 3; } } }
                region B { [*] -> B1 effect { seq = seq * 10 + 4; }; state B1 { enter { seq = seq * 10 + 5; } } }
            }
        }
        """
        # After the effect of the first initial transition that enters a real
        # state, ahead of that state, and not again for the second region.
        assert self.values(text, 1, ("seq",)) == [{"seq": 21345}]

    def test_a_region_that_finishes_through_pseudo_states_leaves_the_plain_before_to_the_next(
        self,
    ):
        text = """
        def int seq = 0;
        state Root {
            [*] -> P;
            state P {
                during before { seq = seq * 10 + 1; }
                region A { [*] -> j; pseudo state j; j -> [*]; }
                region B { [*] -> B1; state B1 { enter { seq = seq * 10 + 2; } } }
            }
        }
        """
        trace = frames(core_of(text, 1), [{}], names=("seq",))
        assert trace[1][1]["Root.P.A"] == "done"
        assert trace[1][2] == {"seq": 12}


def scattered(count, aspects):
    """``count`` regions that each start in a composite of their own."""
    aspect = ">> during before { x = x + 1; }" if aspects else ""
    regions = "".join(
        """
        region R%d {
            [*] -> S;
            state S { %s [*] -> L; state L { during { x = x + 1; } } }
        }"""
        % (index, aspect)
        for index in range(count)
    )
    return "def int x = 0;\nstate Root {%s\n}" % regions


def shared(layers):
    """Two regions below ``layers`` nested composites that each declare a before action."""
    opening = "".join(
        "[*] -> W%d; state W%d { >> during before { x = x + 1; } " % (level, level)
        for level in range(layers)
    )
    return """
    def int x = 0;
    state Root {
        %s
        [*] -> Run;
        state Run {
            region A { [*] -> P; state P { during { x = x + 1; } } }
            region B { [*] -> Q; state Q { during { x = x + 1; } } }
        }
        %s
    }
    """ % (opening, "} " * layers)


def siblings(width):
    """Two regions whose first one holds ``width`` sibling composites with an after action."""
    states = "".join(
        """
            state S%d {
                >> during after { x = x + %d; }
                [*] -> L;
                state L { during { x = x + 1; } }
                L -> [*] : if [u > %d];
            }
            S%d -> S%d : if [u > %d];"""
        % (index, index + 2, index, index, (index + 1) % width, index)
        for index in range(width)
    )
    return (
        """
    input int u;
    def int x = 0;
    state Root {
        region A {
            [*] -> S0;%s
        }
        region B { [*] -> Q; state Q { during { x = x + 1; } } }
    }
    """
        % states
    )


MIXED_ASPECTS = """
input int u;
def int x = 0;
def int y = 0;
state Root {
    >> during before { x = x * 2 + 1; }
    >> during after { y = y + x; }
    [*] -> Wrap;
    state Wrap {
        >> during before { x = x * 2 + 2; }
        [*] -> Run;
        state Run {
            >> during after { y = y * 2 + 3; }
            region A {
                [*] -> P;
                state P {
                    >> during after { y = y + 5; }
                    [*] -> L;
                    state L { during { x = x + 7; } }
                    L -> [*] : if [u > 0];
                }
                state Q {
                    >> during after { y = y * 3 + 1; }
                    [*] -> L;
                    state L { during { x = x + 11; } }
                    L -> [*] : if [u > 2];
                }
                P -> Q : if [u > 0];
                Q -> [*] : if [u > 2];
            }
            region B {
                [*] -> M;
                state M {
                    >> during before { x = x + 13; }
                    [*] -> L;
                    state L { during { y = y + x; } }
                }
            }
        }
    }
}
"""


def simulated(text, inputs, names):
    """Return the variables after every cycle of a run in the simulator."""
    runtime = SimulationRuntime(
        load_state_machine_from_text(text), input_source={"u": 0}
    )
    trace = []
    for value in inputs:
        runtime.cycle(inputs={"u": value})
        values = dict(runtime.vars)
        trace.append({name: values[name] for name in names})
    return trace


# Each model has a guard that fails to evaluate when the input ``d`` is 0, in a
# place where no taken path would show it: a fallback, a candidate that loses
# to a later one, the start of a group nobody can start, a guard that is
# false, the continuation of an owner.  The runtime raises there, so the
# relation may not admit such a cycle.
GUARD_ERRORS = {
    "fallback_after_a_failing_guard": (
        "input int d; state Root { region R { [*] -> Q; state Q; state Q3; "
        "Q -> Q3 : if [1 % d == 0]; } region R2 { [*] -> P; state P; } }",
        [1, 0],
        1,
    ),
    "later_candidate_after_a_failing_guard": (
        "input int d; state Root { region R { [*] -> Q; state Q; state Q3; "
        "state Q4; Q -> Q3 : if [d == 5]; Q -> Q4 : if [1 % d == 0]; } "
        "region R2 { [*] -> P; state P; } }",
        [1, 0],
        1,
    ),
    "initial_candidates_of_a_region": (
        "input int d; def int y = 0; state Root { region R { "
        "[*] -> Q : if [y % d < 2]; [*] -> Q2; state Q; state Q2; } }",
        [0],
        0,
    ),
    "group_start_nobody_can_make": (
        "input int d; state Root { region R { [*] -> P : if [1 % d == 0]; "
        "state P; } region R2 { [*] -> Q; state Q; } }",
        [0],
        0,
    ),
    "group_entered_in_a_later_cycle": (
        "input int d; state Root { [*] -> I; state I; state O { "
        "region A { [*] -> P : if [1 % d == 0]; state P; } "
        "region B { [*] -> Q; state Q; } } I -> O; }",
        [1, 0],
        1,
    ),
    "start_through_a_pseudo_state": (
        "input int d; def int y = 0; state Root { [*] -> S1; state S1 { "
        "region R { [*] -> S4 effect { y = y + d; }; pseudo state S4; "
        "state S5; S5 -> S4 : if [y >= 4]; S4 -> S5 : if [1 % d == 0]; } } }",
        [0],
        0,
    ),
    "continuation_of_an_owner": (
        "input int d; state Root { [*] -> S1; state S1 { region R { "
        "[*] -> S4; pseudo state S4; S4 -> [*]; } } state T; "
        "S1 -> T : if [1 % d == 0]; }",
        [0],
        0,
    ),
}


@pytest.mark.unittest
class TestGuardsThatFailToEvaluate:
    @pytest.mark.parametrize("name", sorted(GUARD_ERRORS))
    def test_a_cycle_in_which_the_runtime_raises_has_no_trace(self, name):
        text, inputs, failing = GUARD_ERRORS[name]
        runtime = SimulationRuntime(
            load_state_machine_from_text(text), input_source={"d": 1}
        )
        for index, value in enumerate(inputs):
            if index == failing:
                with pytest.raises(SimulationRuntimeExpressionError):
                    runtime.cycle(inputs={"d": value})
            else:
                runtime.cycle(inputs={"d": value})
        core = core_of(text, len(inputs))
        cycles = [{"inputs": {"d": value}} for value in inputs]
        assert holds(core, cycles[:failing], z3.BoolVal(True)) == z3.sat
        assert holds(core, cycles, z3.BoolVal(True)) == z3.unsat
        # With the divisor defined, the same model has a trace.
        assert (
            holds(core, [{"inputs": {"d": 1}} for _ in inputs], z3.BoolVal(True))
            == z3.sat
        )


@pytest.mark.unittest
class TestGuardsThatAreNeverReached:
    # The runtime stops evaluating as soon as a candidate is taken, and it
    # starts the regions of a group one after another: a guard or an action
    # that is not reached may fail to evaluate without anybody noticing.

    FORCED_FIRST = """
    input int d;
    def int x = 1;
    def int y = 3;
    state Root {
        event Go;
        region R {
            [*] -> A;
            state A;
            state B;
            A -> B : /Go;
            B -> A : if [x > y % d];
            !B -> A : if [x >= 1];
        }
    }
    """

    LATER_REGION = """
    input int e;
    input int d;
    def int y = 0;
    state Root {
        region R1 { [*] -> P; pseudo state P; P -> [*] : if [e > 0]; }
        region R3 { [*] -> Q; state Q; }
    }
    """

    def runs(self, text, inputs, defaults):
        runtime = SimulationRuntime(
            load_state_machine_from_text(text), input_source=defaults
        )
        for item in inputs:
            runtime.cycle(item.get("events", []), inputs=item.get("inputs", defaults))
        return runtime

    def test_a_guard_behind_a_candidate_that_wins_is_not_evaluated(self):
        # In B the forced transition ranks first and is taken, so the guard
        # with the division is not looked at although the divisor is 0.
        cycles = [
            {"inputs": {"d": 1}},
            {"events": ["Root.Go"], "inputs": {"d": 1}},
            {"inputs": {"d": 0}},
        ]
        self.runs(self.FORCED_FIRST, cycles, {"d": 1})
        core = core_of(self.FORCED_FIRST, 3)
        assert holds(core, cycles, z3.BoolVal(True)) == z3.sat
        # The relation admits exactly the runtime's run: back in A.
        trace = frames(core, cycles, ["x", "y"])
        assert trace[-1][1] == {"Root.R": "Root.R.A"}

    def test_a_region_that_is_never_started_does_not_evaluate_its_start(self):
        text = self.LATER_REGION.replace(
            "[*] -> Q; state Q;", "[*] -> Q effect { y = y % d; }; state Q;"
        )
        core = core_of(text, 1)
        # R1 cannot settle without e > 0, so the group does not start and the
        # effect of R3 is never run, whatever the divisor.
        quiet = [{"inputs": {"e": 0, "d": 0}}]
        self.runs(text, quiet, {"e": 0, "d": 0})
        assert holds(core, quiet, z3.BoolVal(True)) == z3.sat
        # With R1 settled, the effect of R3 runs and fails on a zero divisor.
        loud = [{"inputs": {"e": 1, "d": 0}}]
        with pytest.raises(SimulationRuntimeExpressionError):
            self.runs(text, loud, {"e": 0, "d": 1})
        assert holds(core, loud, z3.BoolVal(True)) == z3.unsat


@pytest.mark.unittest
class TestStepsThatOnlyFallBack:
    # Gamma_i marks a step in which nothing but fallbacks ran: no transition
    # fired in any region.
    TEXT = """
    def int x = 0;
    state Root {
        event Go;
        region R1 {
            [*] -> A;
            state A { during { x = x + 1; } }
            state O {
                region Q1 { [*] -> P; state P { during { x = x + 10; } } }
                region Q2 { [*] -> P2; state P2; }
            }
            A -> O : /Go;
        }
        region R2 { [*] -> S; state S { during { x = x + 100; } } }
    }
    """

    def test_a_transition_into_a_nested_owner_is_not_a_step_of_fallbacks_only(self):
        core = core_of(self.TEXT, 4)
        cycles = [{}, {}, {"events": ["Root.Go"]}, {}]
        symbols = core.symbols
        # The cold start and the cycle in which Go fires take a transition; the
        # cycles in between only fall back.
        expected = [False, True, False, True]
        for index, only_falls_back in enumerate(expected):
            gamma = symbols.gamma_flag(index)
            assert holds(core, cycles, gamma) == (
                z3.sat if only_falls_back else z3.unsat
            ), index
            assert holds(core, cycles, z3.Not(gamma)) == (
                z3.unsat if only_falls_back else z3.sat
            ), index

    def test_a_leaf_in_place_of_the_nested_owner_gives_the_same_answer(self):
        leaf = self.TEXT.replace(
            """state O {
                region Q1 { [*] -> P; state P { during { x = x + 10; } } }
                region Q2 { [*] -> P2; state P2; }
            }""",
            "state O { during { x = x + 10; } }",
        )
        assert leaf != self.TEXT
        core = core_of(leaf, 4)
        cycles = [{}, {}, {"events": ["Root.Go"]}, {}]
        assert holds(core, cycles, core.symbols.gamma_flag(2)) == z3.unsat


@pytest.mark.unittest
class TestAspectScopes:
    # Each scope that declares aspects carries a flag from region to region.
    # How many times a path is lowered may only depend on the flags that path
    # can read and that are not known where it starts.

    def paths(self, text, bound=2):
        return len(core_of(text, bound).region_steps[1].cases)

    def test_a_before_action_inside_another_region_does_not_multiply_the_paths(self):
        for count in (2, 3, 4):
            assert self.paths(scattered(count, True)) == self.paths(
                scattered(count, False)
            )

    def test_every_shared_before_scope_adds_the_same_number_of_paths(self):
        counts = [self.paths(shared(layers)) for layers in range(5)]
        steps = [after - before for before, after in zip(counts, counts[1:])]
        # The first region always finds the shared flags clear; the second one
        # is lowered once more for every scope that may already have run.
        assert steps[0] > 0
        assert len(set(steps)) == 1

    def test_sibling_after_scopes_are_settled_one_at_a_time(self):
        sizes = [
            len(core_of(siblings(width), 2).region_steps[1].constraints)
            for width in (2, 3, 4, 5, 6)
        ]
        steps = [after - before for before, after in zip(sizes, sizes[1:])]
        assert steps[0] > 0
        assert len(set(steps)) == 1

    @pytest.mark.parametrize(
        "inputs",
        [[0, 0, 0, 0], [1, 1, 1, 1], [1, 3, 3, 3], [3, 3, 0, 1], [0, 1, 0, 3]],
    )
    def test_shared_inner_and_sibling_scopes_together_match_the_runtime(self, inputs):
        core = core_of(MIXED_ASPECTS, len(inputs))
        cycles = [{"inputs": {"u": value}} for value in inputs]
        trace = frames(core, cycles, ["x", "y"])
        assert [item[2] for item in trace[1:]] == simulated(
            MIXED_ASPECTS, inputs, ["x", "y"]
        )
        # With the inputs pinned there is no second trace.
        last = len(inputs)
        seen = trace[last][2]
        other = z3.Or(
            core.symbols.frame_var(last, "x") != seen["x"],
            core.symbols.frame_var(last, "y") != seen["y"],
        )
        assert holds(core, cycles, other) == z3.unsat

    @pytest.mark.parametrize("width", [2, 3])
    @pytest.mark.parametrize("inputs", [[0, 0, 0], [1, 1, 1], [1, 2, 3], [3, 0, 2]])
    def test_sibling_after_actions_match_the_runtime(self, width, inputs):
        text = siblings(width)
        core = core_of(text, len(inputs))
        cycles = [{"inputs": {"u": value}} for value in inputs]
        trace = frames(core, cycles, ["x"])
        assert [item[2] for item in trace[1:]] == simulated(text, inputs, ["x"])


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
        from pyfcstm.bmc.safety import runtime_error_formula

        with pytest.raises(
            UnsupportedBmcQuery, match="runtime-safety check of a model with regions"
        ):
            runtime_error_formula(core)

    def test_an_owner_before_action_over_empty_regions_keeps_the_formula_satisfiable(
        self,
    ):
        text = """
        def int y = 0;
        state Root {
            [*] -> Run;
            state Run {
                during before { y = y + 1; }
                region A { [*] -> P; state P; }
            }
        }
        """
        for bound in (1, 2):
            solver = z3.Solver()
            solver.add(core_of(text, bound).core)
            assert solver.check() == z3.sat


@pytest.mark.unittest
class TestStartValuesAndFlushes:
    def test_the_relation_builder_needs_a_model_with_regions(self):
        model = load_state_machine_from_text("state Root { [*] -> A; state A; }")
        context = BmcEngine(model).prepare("check reach <= 1: terminated();")
        with pytest.raises(BmcBuildError, match="needs a model with regions"):
            build_region_core_formula(context)

    def test_parameters_and_float_variables_keep_their_start_values(self):
        text = """
        param int gain = 2;
        def int x = 3;
        def float ratio = 1;
        state Root {
            region A { [*] -> P; state P { during { x = x + 1; } } }
            region B { [*] -> Q; state Q; }
        }
        """
        core = core_of(text, 1)
        symbols = core.symbols
        solver = z3.Solver()
        solver.add(core.core, z3.Not(symbols.frame_var(1, "x") == 4))
        assert solver.check() == z3.unsat
        solver = z3.Solver()
        solver.add(core.core, symbols.frame_var(1, "ratio") == 1)
        assert solver.check() == z3.sat

    def test_an_after_action_that_fails_while_the_group_is_entered_is_undefined(self):
        text = """
        input int u;
        def int x = 0;
        state Root {
            region A {
                [*] -> S;
                state S {
                    >> during after { x = x + 100 % u; }
                    [*] -> L;
                    state L { during { x = x + 1; } }
                }
            }
            region B { [*] -> Q; state Q; }
        }
        """
        core = core_of(text, 2)

        def run(first, second):
            cycles = [{"inputs": {"u": first}}, {"inputs": {"u": second}}]
            return holds(core, cycles, z3.BoolVal(True))

        # The first cycle enters the group, and the after action of S runs when
        # the branch of region A ends: a zero divisor makes that cycle
        # undefined exactly as it does in any later cycle.
        assert run(0, 3) == z3.unsat
        assert run(3, 0) == z3.unsat
        assert run(3, 3) == z3.sat
        cycles = [{"inputs": {"u": 3}}, {"inputs": {"u": 3}}]
        assert [item[2]["x"] for item in frames(core, cycles, ["x"])] == [0, 2, 4]

    def test_a_region_that_finishes_through_pseudo_states_owes_no_after_action(self):
        text = """
        def int x = 0;
        state Root {
            [*] -> Run;
            state Run {
                region A {
                    >> during after { x = x + 1; }
                    [*] -> j;
                    pseudo state j;
                    j -> [*];
                }
                region B { [*] -> Q; state Q; }
            }
        }
        """
        trace = frames(core_of(text, 1), [{}], names=("x",))
        assert trace[1][1]["Root.Run.A"] == "done"
        # No leaf worked below A, so nothing is owed when its branch ends.
        assert trace[1][2] == {"x": 0}

    def test_an_after_action_that_only_the_root_owes_runs_once_at_the_end_of_the_cycle(
        self,
    ):
        text = """
        def int x = 0;
        state Root {
            >> during after { x = x + 1; }
            [*] -> Run;
            state Run {
                region A { [*] -> P; state P { during { x = x + 10; } } }
                region B { [*] -> Q; state Q { during { x = x * 2; } } }
            }
        }
        """
        # No region owes anything when its branch ends; the root runs its action
        # once, after both regions worked. Values come from the simulator.
        trace = frames(core_of(text, 2), [{}, {}], names=("x",))
        assert [item[2] for item in trace[1:]] == [{"x": 21}, {"x": 63}]
