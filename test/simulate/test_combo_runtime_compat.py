"""Runtime compatibility tests for expanded combo trigger pseudo chains."""

import pytest

from pyfcstm.simulate import SimulationRuntime
from test.testings.combo_runtime import (
    assert_combo_matches_manual_pseudo,
    combo_projection_signature,
    parse_machine,
)


pytestmark = pytest.mark.unittest


def test_event_guard_event_success_matches_hand_written_pseudo_chain():
    combo = """
    def int x = 1;
    state Root {
        state S;
        state T;
        [*] -> S;
        S -> T :: E1 + [x > 0] + E2;
    }
    """
    manual = """
    def int x = 1;
    state Root {
        state S;
        pseudo state P1 named "combo after E1";
        pseudo state P2 named "combo after E1 + [x > 0]";
        state T;
        [*] -> S;
        S -> P1 :: E1;
        P1 -> P2 : if [x > 0];
        P2 -> T : /S.E2;
    }
    """

    _, _, trace = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1", "Root.S.E2"]]
    )

    assert trace[-1]["state"] == "Root.T"
    assert trace[-1]["consumed_events"] == ("Root.S.E1", "Root.S.E2")


def test_missing_second_event_rolls_back_and_uses_later_fallback_transition():
    combo = """
    state Root {
        state S;
        state T;
        state F;
        [*] -> S;
        S -> T :: E1 + E2;
        S -> F :: E1;
    }
    """
    manual = """
    state Root {
        state S;
        pseudo state P named "combo after E1";
        state T;
        state F;
        [*] -> S;
        S -> P :: E1;
        P -> T : /S.E2;
        S -> F :: E1;
    }
    """

    _, _, trace = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1"]]
    )

    assert trace[-1]["state"] == "Root.F"
    assert trace[-1]["consumed_events"] == ("Root.S.E1",)


def test_middle_guard_false_rolls_back_and_uses_later_fallback_transition():
    combo = """
    def int x = 0;
    state Root {
        state S;
        state T;
        state F;
        [*] -> S;
        S -> T :: E1 + [x > 0] + E2;
        S -> F :: E1;
    }
    """
    manual = """
    def int x = 0;
    state Root {
        state S;
        pseudo state P1 named "combo after E1";
        pseudo state P2 named "combo after E1 + [x > 0]";
        state T;
        state F;
        [*] -> S;
        S -> P1 :: E1;
        P1 -> P2 : if [x > 0];
        P2 -> T : /S.E2;
        S -> F :: E1;
    }
    """

    _, _, trace = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1", "Root.S.E2"]]
    )

    assert trace[-1]["state"] == "Root.F"
    assert trace[-1]["consumed_events"] == ("Root.S.E1",)
    assert trace[-1]["unconsumed_events"] == ("Root.S.E2",)


def test_terminal_effect_commits_only_for_successful_combo_path():
    combo = """
    def int x = 0;
    state Root {
        state S;
        state T;
        state F;
        [*] -> S;
        S -> T :: E1 + E2 effect { x = 1; }
        S -> F :: E1 effect { x = 2; }
    }
    """
    manual = """
    def int x = 0;
    state Root {
        state S;
        pseudo state P named "combo after E1";
        state T;
        state F;
        [*] -> S;
        S -> P :: E1;
        P -> T : /S.E2 effect { x = 1; }
        S -> F :: E1 effect { x = 2; }
    }
    """

    _, _, success_trace = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1", "Root.S.E2"]]
    )
    _, _, fallback_trace = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1"]]
    )

    assert success_trace[-1]["state"] == "Root.T"
    assert dict(success_trace[-1]["vars"])["x"] == 1
    assert fallback_trace[-1]["state"] == "Root.F"
    assert dict(fallback_trace[-1]["vars"])["x"] == 2


def test_entry_combo_initial_transition_matches_hand_written_pseudo_chain():
    combo = """
    state Root {
        state S;
        state F;
        [*] -> S : E1 + E2;
        [*] -> F;
    }
    """
    manual = """
    state Root {
        pseudo state P named "combo after E1";
        state S;
        state F;
        [*] -> P : E1;
        P -> S : E2;
        [*] -> F;
    }
    """

    _, _, success_trace = assert_combo_matches_manual_pseudo(
        combo, manual, [["Root.E1", "Root.E2"]]
    )
    _, _, fallback_trace = assert_combo_matches_manual_pseudo(combo, manual, [None])

    assert success_trace[-1]["state"] == "Root.S"
    assert fallback_trace[-1]["state"] == "Root.F"


def test_exit_combo_parent_continuation_matches_hand_written_pseudo_chain():
    combo = """
    state Root {
        state Parent {
            state S;
            [*] -> S;
            S -> [*] :: E1 + E2;
        }
        state Done;
        [*] -> Parent;
        Parent -> Done;
    }
    """
    manual = """
    state Root {
        state Parent {
            state S;
            pseudo state P named "combo after E1";
            [*] -> S;
            S -> P :: E1;
            P -> [*] : /Parent.S.E2;
        }
        state Done;
        [*] -> Parent;
        Parent -> Done;
    }
    """

    _, _, trace = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.Parent.S.E1", "Root.Parent.S.E2"]]
    )

    assert trace[-1]["state"] == "Root.Done"
    assert trace[-1]["consumed_events"] == (
        "Root.Parent.S.E1",
        "Root.Parent.S.E2",
    )


def test_exit_combo_parent_continuation_failure_rolls_back_to_source():
    combo = """
    def int x = 0;
    state Root {
        state Parent {
            state S;
            [*] -> S;
            S -> [*] :: E1 + E2;
        }
        state Done;
        [*] -> Parent;
        Parent -> Done : if [x > 0];
    }
    """
    manual = """
    def int x = 0;
    state Root {
        state Parent {
            state S;
            pseudo state P named "combo after E1";
            [*] -> S;
            S -> P :: E1;
            P -> [*] : /Parent.S.E2;
        }
        state Done;
        [*] -> Parent;
        Parent -> Done : if [x > 0];
    }
    """

    _, _, trace = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.Parent.S.E1", "Root.Parent.S.E2"]]
    )

    assert trace[-1]["state"] == "Root.Parent.S"
    assert trace[-1]["consumed_events"] == ()
    assert trace[-1]["unconsumed_events"] == (
        "Root.Parent.S.E1",
        "Root.Parent.S.E2",
    )


def test_hot_start_to_event_gated_combo_pseudo_is_rejected():
    model = parse_machine(
        """
        state Root {
            state S;
            state T;
            [*] -> S;
            S -> T :: E1 + E2;
        }
        """
    )
    pseudo = next(
        state for state in model.root_state.substates.values() if state.is_pseudo
    )

    with pytest.raises(ValueError, match="cannot reach a stoppable state"):
        SimulationRuntime(model, initial_state=pseudo.path, initial_vars={})


def test_plain_pseudo_with_same_event_gate_has_same_hot_start_contract():
    model = parse_machine(
        """
        state Root {
            state S;
            pseudo state P named "combo after E1";
            state T;
            [*] -> S;
            S -> P :: E1;
            P -> T : /S.E2;
        }
        """
    )

    with pytest.raises(
        ValueError, match="Hot start target 'Root.P' cannot reach a stoppable state"
    ):
        SimulationRuntime(model, initial_state="Root.P", initial_vars={})


def test_prefix_reuse_matches_shared_hand_written_pseudo_chain():
    combo = """
    state Root {
        state S;
        state A;
        state B;
        [*] -> S;
        S -> A :: E1 + E2;
        S -> B :: E1 + E3;
    }
    """
    manual = """
    state Root {
        state S;
        pseudo state P named "combo after E1";
        state A;
        state B;
        [*] -> S;
        S -> P :: E1;
        P -> A : /S.E2;
        P -> B : /S.E3;
    }
    """

    combo_model, _, trace_to_a = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1", "Root.S.E2"]]
    )
    _, _, trace_to_b = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1", "Root.S.E3"]]
    )

    assert len(combo_projection_signature(combo_model)) == 3
    assert trace_to_a[-1]["state"] == "Root.A"
    assert trace_to_b[-1]["state"] == "Root.B"


def test_priority_fence_matches_split_hand_written_pseudo_chains():
    combo = """
    state Root {
        state S;
        state A;
        state B;
        state F;
        [*] -> S;
        S -> A :: E1 + E2;
        S -> F :: E1;
        S -> B :: E1 + E3;
    }
    """
    manual = """
    state Root {
        state S;
        pseudo state P1 named "combo after E1";
        pseudo state P2 named "combo after E1";
        state A;
        state B;
        state F;
        [*] -> S;
        S -> P1 :: E1;
        P1 -> A : /S.E2;
        S -> F :: E1;
        S -> P2 :: E1;
        P2 -> B : /S.E3;
    }
    """

    _, _, trace_to_a = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1", "Root.S.E2"]]
    )
    _, _, trace_to_f = assert_combo_matches_manual_pseudo(
        combo, manual, [None, ["Root.S.E1", "Root.S.E3"]]
    )

    assert trace_to_a[-1]["state"] == "Root.A"
    assert trace_to_f[-1]["state"] == "Root.F"
