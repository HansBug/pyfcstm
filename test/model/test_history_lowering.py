"""History pseudo-states are lowered into plain FCSTM during model conversion."""

import pytest

from pyfcstm.dsl import INIT_STATE, parse_with_grammar_entry
from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime

WASHER = """
def int program_entries = 0;
def int fill_entries = 0;
def int agitate_entries = 0;
def int wash_initials = 0;

state Washer {
    state Paused;
    state Program {
        enter { program_entries = program_entries + 1; }
        state Idle;
        state Wash {
            state Fill {
                enter { fill_entries = fill_entries + 1; }
            }
            state Agitate {
                enter { agitate_entries = agitate_entries + 1; }
            }
            [*] -> Fill effect { wash_initials = wash_initials + 1; }
            Fill -> Agitate :: Filled;
        }
        [*] -> Idle;
        [H] -> Idle;
        [H*] -> Wash.Fill;
        Idle -> Wash :: Start;
    }
    [*] -> Paused;
    Paused -> Program :: Fresh;
    Paused -> Program.[H] :: Shallow;
    Paused -> Program.[H*] :: Deep;
    !Program -> Paused :: Pause;
}
"""

EVENTS = {
    "Fresh": "Washer.Paused.Fresh",
    "Shallow": "Washer.Paused.Shallow",
    "Deep": "Washer.Paused.Deep",
    "Start": "Washer.Program.Idle.Start",
    "Filled": "Washer.Program.Wash.Fill.Filled",
    "Pause": "Washer.Program.Pause",
}


def _collect(text):
    return parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(text, "state_machine_dsl"), collect=True
    )


def _codes(diagnostics):
    return [(item.code, item.severity) for item in diagnostics]


def _state(machine, path):
    state = machine.root_state
    for name in path.split(".")[1:]:
        state = state.substates[name]
    return state


def _active(runtime):
    return ".".join(runtime.current_state.path)


@pytest.mark.unittest
class TestLoweredStructure:
    def test_washer_lowers_to_the_minimal_plain_machine(self):
        machine = load_state_machine_from_text(WASHER)
        program = _state(machine, "Washer.Program")
        wash = _state(machine, "Washer.Program.Wash")

        assert len(program.init_transitions) == 2
        assert len(wash.init_transitions) == 3
        hidden = [name for name in machine.defines if name.startswith("__hist_")]
        assert hidden == ["__hist_goto", "__hist_Program"]
        assert all(machine.defines[name].type == "int" for name in hidden)
        assert not any(state.is_history_gate for state in machine.walk_states())

    def test_owner_metadata_describes_records_in_source_terms(self):
        machine = load_state_machine_from_text(WASHER)
        (owner,) = machine.history_owners
        assert owner.owner_path == ("Washer", "Program")
        assert owner.record_variable == "__hist_Program"
        assert owner.goto_variable == "__hist_goto"
        assert owner.defaults == {"shallow": ("Idle",), "deep": ("Wash", "Fill")}
        assert sorted(owner.leaf_paths()) == [("Idle",), ("Wash", "Agitate"), ("Wash", "Fill")]
        value = owner.record_value(("Wash", "Agitate"))
        assert value > 0
        assert owner.decode(value) == ("Wash", "Agitate")
        assert owner.decode(0) is None
        assert owner.decode(-1) is None

    def test_history_entries_carry_their_kind_and_a_target_assignment(self):
        machine = load_state_machine_from_text(WASHER)
        root = machine.root_state
        entries = {t.event.name: t for t in root.transitions if t.event is not None and t.from_state == "Paused"}
        assert entries["Fresh"].target_history is None
        assert entries["Shallow"].target_history == "shallow"
        assert entries["Deep"].target_history == "deep"
        assert [op.var_name for op in entries["Deep"].effects] == ["__hist_goto"]
        assert entries["Fresh"].effects == []

    def test_hidden_names_stay_distinct_after_identifier_conversion(self):
        text = """
        state R {
            state Off;
            state A_B { state X; [*] -> X; [H] -> X; }
            state A {
                state B { state Y; [*] -> Y; [H] -> Y; }
                [*] -> B;
                [H] -> B;
            }
            state goto { state Z; [*] -> Z; [H] -> Z; }
            [*] -> Off;
            Off -> A_B.[H] :: E1;
            Off -> A.[H] :: E2;
            Off -> goto.[H] :: E3;
            !A_B -> Off :: S1;
            !A -> Off :: S2;
            !goto -> Off :: S3;
        }
        """
        machine = load_state_machine_from_text(text)
        names = [owner.record_variable for owner in machine.history_owners]
        assert names == ["__hist_A_B", "__hist_A", "__hist_goto_2"]
        # Generated code collapses underscore runs; the names must survive it.
        collapsed = {name.replace("__", "_") for name in names + ["__hist_goto"]}
        assert len(collapsed) == 4

    def test_owner_paths_that_join_to_the_same_tag_are_numbered(self):
        # ``R.A_B`` and ``R.A.B`` both join to the tag ``A_B``.
        text = """
        state R {
            state Off;
            state A_B { state X; [*] -> X; [H] -> X; }
            state A {
                state B { state Y; [*] -> Y; [H] -> Y; }
                state C;
                [*] -> C;
                C -> B.[H] :: Back;
            }
            [*] -> Off;
            Off -> A_B.[H] :: E1;
            Off -> A :: E2;
            !A_B -> Off :: S1;
            !A -> Off :: S2;
        }
        """
        machine = load_state_machine_from_text(text)
        names = [owner.record_variable for owner in machine.history_owners]
        assert names == ["__hist_A_B", "__hist_A_B_2"]

    def test_models_without_history_are_unchanged(self):
        text = "def int x = 0; state R { state A; state B; [*] -> A; A -> B :: Go; }"
        machine = load_state_machine_from_text(text)
        assert machine.history_owners == ()
        assert list(machine.defines) == ["x"]
        assert machine.history_variables() == {}


@pytest.mark.unittest
class TestWasherExecution:
    def test_records_follow_the_owner_exits_cycle_by_cycle(self):
        machine = load_state_machine_from_text(WASHER)
        runtime = SimulationRuntime(machine)
        script = [
            (None, "Washer.Paused", None),
            ("Fresh", "Washer.Program.Idle", None),
            ("Start", "Washer.Program.Wash.Fill", None),
            ("Filled", "Washer.Program.Wash.Agitate", None),
            ("Pause", "Washer.Paused", "Wash.Agitate"),
            ("Shallow", "Washer.Program.Wash.Fill", None),
            ("Pause", "Washer.Paused", "Wash.Fill"),
            ("Deep", "Washer.Program.Wash.Fill", None),
            ("Pause", "Washer.Paused", "Wash.Fill"),
            ("Fresh", "Washer.Program.Idle", None),
            ("Pause", "Washer.Paused", "Idle"),
            ("Deep", "Washer.Program.Idle", None),
        ]
        for event, active, record in script:
            runtime.cycle([EVENTS[event]] if event else [])
            assert _active(runtime) == active, event
            if record is not None:
                assert machine.history_record(runtime.vars, "Washer.Program") == record
            assert runtime.vars["__hist_goto"] == 0

    def test_deep_restore_skips_the_initial_transitions_it_passes(self):
        machine = load_state_machine_from_text(WASHER)
        runtime = SimulationRuntime(machine)
        for event in [None, "Fresh", "Start", "Filled", "Pause", "Deep"]:
            runtime.cycle([EVENTS[event]] if event else [])
        assert _active(runtime) == "Washer.Program.Wash.Agitate"
        assert runtime.vars["agitate_entries"] == 2
        assert runtime.vars["fill_entries"] == 1
        assert runtime.vars["wash_initials"] == 1
        assert runtime.vars["program_entries"] == 2

    def test_shallow_restore_reruns_the_initial_of_the_recorded_child(self):
        machine = load_state_machine_from_text(WASHER)
        runtime = SimulationRuntime(machine)
        for event in [None, "Fresh", "Start", "Filled", "Pause", "Shallow"]:
            runtime.cycle([EVENTS[event]] if event else [])
        assert _active(runtime) == "Washer.Program.Wash.Fill"
        assert runtime.vars["wash_initials"] == 2

    def test_history_without_a_record_takes_its_default(self):
        machine = load_state_machine_from_text(WASHER)
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        runtime.cycle([EVENTS["Deep"]])
        assert _active(runtime) == "Washer.Program.Wash.Fill"
        assert runtime.vars["wash_initials"] == 0
        machine2 = load_state_machine_from_text(WASHER)
        runtime2 = SimulationRuntime(machine2)
        runtime2.cycle()
        runtime2.cycle([EVENTS["Shallow"]])
        assert _active(runtime2) == "Washer.Program.Idle"


BLOCKED = """
def int ready = 1;
def int fresh_entries = 0;
state R {
    state Off;
    state O {
        state Idle;
        state K {
            state K1;
            [*] -> K1 : if [ready == 1];
        }
        %s
        [H] -> Idle;
        [H*] -> K;
        Idle -> K :: Go;
    }
    [*] -> Off;
    Off -> O :: Fresh;
    Off -> O.[H] :: Resume;
    Off -> O.[H*] :: ResumeDeep;
    !O -> Off :: Stop;
    Off -> Off :: Block effect { ready = 0; }
}
"""

# A plain user initial is merged into the route to the same child; one with
# an effect is gated separately.  Both must refuse to stand in for a blocked
# restore.
BLOCKED_INITIALS = {
    "merged": "[*] -> Idle;",
    "gated": "[*] -> Idle effect { fresh_entries = fresh_entries + 1; }",
}


@pytest.mark.unittest
@pytest.mark.parametrize("initial", sorted(BLOCKED_INITIALS))
class TestBlockedRestore:
    def _run(self, initial, *events):
        machine = load_state_machine_from_text(BLOCKED % BLOCKED_INITIALS[initial])
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        for event in events:
            runtime.cycle([event])
        return runtime

    def test_a_blocked_shallow_restore_rejects_the_whole_transition(self, initial):
        runtime = self._run(
            initial, "R.Off.Fresh", "R.O.Idle.Go", "R.O.Stop", "R.Off.Block", "R.Off.Resume"
        )
        assert _active(runtime) == "R.Off"

    def test_a_blocked_deep_default_rejects_the_whole_transition(self, initial):
        runtime = self._run(initial, "R.Off.Block", "R.Off.ResumeDeep")
        assert _active(runtime) == "R.Off"

    def test_ordinary_entry_is_not_affected_by_the_gates(self, initial):
        runtime = self._run(initial, "R.Off.Block", "R.Off.Fresh")
        assert _active(runtime) == "R.O.Idle"
        assert runtime.vars["fresh_entries"] == (1 if initial == "gated" else 0)


@pytest.mark.unittest
class TestHistoryTargetForms:
    def test_evented_initial_is_gated_through_a_pseudo_state(self):
        text = """
        state R {
            state Off;
            state O {
                event Kick;
                state A;
                state B;
                [*] -> A :: Kick;
                [H] -> B;
                A -> B :: Next;
            }
            [*] -> Off;
            Off -> O :: Fresh;
            Off -> O.[H] :: Resume;
            !O -> Off :: Stop;
        }
        """
        machine = load_state_machine_from_text(text)
        owner = _state(machine, "R.O")
        gates = [state for state in owner.substates.values() if state.is_history_gate]
        assert len(gates) == 1 and gates[0].is_pseudo
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        runtime.cycle(["R.Off.Fresh", "R.O.Kick"])
        assert _active(runtime) == "R.O.A"
        runtime.cycle(["R.O.A.Next"])
        runtime.cycle(["R.O.Stop"])
        runtime.cycle(["R.Off.Resume"])
        assert _active(runtime) == "R.O.B"

    def test_forced_and_initial_transitions_may_target_history(self):
        text = """
        def int n = 0;
        state R {
            state Outer {
                state O {
                    state A;
                    state B;
                    [*] -> A;
                    [H*] -> A;
                    A -> B :: Next;
                }
                state Side;
                [*] -> O.[H*];
                !O -> Side :: Leave;
                Side -> O.[H*] :: Back;
            }
            state Away;
            [*] -> Outer;
            !Outer -> Away :: Out;
            !Away -> Outer :: In;
        }
        """
        machine = load_state_machine_from_text(text)
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        assert _active(runtime) == "R.Outer.O.A"
        runtime.cycle(["R.Outer.O.A.Next"])
        runtime.cycle(["R.Outer.O.Leave"])
        assert _active(runtime) == "R.Outer.Side"
        runtime.cycle(["R.Outer.Side.Back"])
        assert _active(runtime) == "R.Outer.O.B"
        # Leaving Outer and coming back uses Outer's initial, which itself
        # enters O through its history.
        runtime.cycle(["R.Outer.Out"])
        runtime.cycle(["R.Away.In"])
        assert _active(runtime) == "R.Outer.O.B"

    def test_all_forced_transition_and_combo_trigger_may_target_history(self):
        text = """
        def int online = 0;
        state R {
            state Off;
            state S {
                state A;
                state B;
                [*] -> A;
                [H*] -> A;
                A -> B :: Next;
            }
            [*] -> Off;
            Off -> S :: Fresh;
            Off -> S.[H*] :: Resume + [online > 0];
            Off -> Off :: Online effect { online = 1; }
            !* -> Off :: Halt;
        }
        """
        machine = load_state_machine_from_text(text)
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        runtime.cycle(["R.Off.Fresh"])
        runtime.cycle(["R.S.A.Next"])
        runtime.cycle(["R.Halt"])
        runtime.cycle(["R.Off.Resume"])
        assert _active(runtime) == "R.Off"
        runtime.cycle(["R.Off.Online"])
        runtime.cycle(["R.Off.Resume"])
        assert _active(runtime) == "R.S.B"

    def test_self_history_reenters_the_recorded_leaf(self):
        text = """
        def int enters = 0;
        state R {
            state O {
                enter { enters = enters + 1; }
                state A;
                state B;
                [*] -> A;
                [H*] -> A;
                A -> B :: Next;
            }
            [*] -> O;
            !O -> O.[H*] :: Reenter;
        }
        """
        machine = load_state_machine_from_text(text)
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        runtime.cycle(["R.O.A.Next"])
        runtime.cycle(["R.O.Reenter"])
        assert _active(runtime) == "R.O.B"
        assert runtime.vars["enters"] == 2

    def test_pseudo_only_activation_keeps_the_record(self):
        text = """
        def int bounce = 0;
        state R {
            state Off;
            state O {
                pseudo state Router;
                state A;
                state B;
                [*] -> Router : if [bounce == 1];
                [*] -> A;
                [H*] -> A;
                A -> B :: Next;
                Router -> [*];
            }
            [*] -> Off;
            Off -> O :: Fresh;
            Off -> O.[H*] :: Resume;
            Off -> Off :: Arm effect { bounce = 1; }
            O -> Off : if [bounce == 1] effect { bounce = 0; }
            !O -> Off :: Stop;
        }
        """
        machine = load_state_machine_from_text(text)
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        runtime.cycle(["R.Off.Fresh"])
        runtime.cycle(["R.O.A.Next"])
        runtime.cycle(["R.O.Stop"])
        assert machine.history_record(runtime.vars, "R.O") == "B"
        runtime.cycle(["R.Off.Arm"])
        # This activation only passes the pseudo Router and leaves again.
        runtime.cycle(["R.Off.Fresh"])
        assert _active(runtime) == "R.Off"
        assert runtime.vars["bounce"] == 0
        assert machine.history_record(runtime.vars, "R.O") == "B"
        runtime.cycle(["R.Off.Resume"])
        assert _active(runtime) == "R.O.B"


@pytest.mark.unittest
class TestNestedOwners:
    TEXT = """
    state R {
        state Off;
        state O {
            state S1;
            state S2 {
                state A2;
                state B2;
                [*] -> A2;
                [H*] -> A2;
                A2 -> B2 :: Next;
            }
            [*] -> S2.[H*];
            [H] -> S1;
        }
        [*] -> Off;
        Off -> O :: Fresh;
        Off -> O.[H] :: Resume;
        !O -> Off :: Stop;
    }
    """

    def _runtime(self):
        machine = load_state_machine_from_text(self.TEXT)
        runtime = SimulationRuntime(machine)
        runtime.cycle()
        return machine, runtime

    def test_an_initial_that_enters_a_nested_history_keeps_its_target(self):
        machine, runtime = self._runtime()
        for event in ["R.Off.Fresh", "R.O.S2.A2.Next", "R.O.Stop"]:
            runtime.cycle([event])
        assert machine.history_record(runtime.vars, "R.O") == "S2.B2"
        assert machine.history_record(runtime.vars, "R.O.S2") == "B2"
        # O's ordinary entry is itself a deep-history entry into S2.
        runtime.cycle(["R.Off.Fresh"])
        assert _active(runtime) == "R.O.S2.B2"

    def test_shallow_restore_of_the_outer_owner_reruns_the_inner_initial(self):
        machine, runtime = self._runtime()
        for event in ["R.Off.Fresh", "R.O.S2.A2.Next", "R.O.Stop", "R.Off.Resume"]:
            runtime.cycle([event])
        assert _active(runtime) == "R.O.S2.A2"
        assert runtime.vars["__hist_goto"] == 0


@pytest.mark.unittest
class TestHistoryHotStartHelpers:
    def test_history_variables_translate_source_records(self):
        machine = load_state_machine_from_text(WASHER)
        assert machine.history_variables() == {"__hist_goto": 0, "__hist_Program": 0}
        values = machine.history_variables({"Washer.Program": "Wash.Agitate"})
        assert values["__hist_goto"] == 0
        assert machine.history_record(values, "Washer.Program") == "Wash.Agitate"

    def test_history_variables_reject_unknown_owners_and_leaves(self):
        machine = load_state_machine_from_text(WASHER)
        with pytest.raises(ValueError, match="history owner"):
            machine.history_variables({"Washer.Nope": "Idle"})
        with pytest.raises(ValueError, match="stoppable leaf"):
            machine.history_variables({"Washer.Program": "Wash"})
        with pytest.raises(ValueError, match="history owner"):
            machine.history_record({}, "Washer.Paused")

    def test_hot_start_with_a_record_resumes_from_it(self):
        machine = load_state_machine_from_text(WASHER)
        user = {"program_entries": 0, "fill_entries": 0, "agitate_entries": 0, "wash_initials": 0}
        runtime = SimulationRuntime(
            machine,
            initial_state="Washer.Paused",
            initial_vars={**user, **machine.history_variables({"Washer.Program": "Wash.Agitate"})},
        )
        runtime.cycle()
        runtime.cycle([EVENTS["Deep"]])
        assert _active(runtime) == "Washer.Program.Wash.Agitate"
