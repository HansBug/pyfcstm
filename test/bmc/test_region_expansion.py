"""Unit expansion of models that declare regions."""

import pytest

from pyfcstm.bmc import (
    InvalidBmcEncoding,
    build_bmc_domain,
    expand_cold_unit,
    expand_continue_unit,
    expand_init_unit,
    expand_leaf_unit,
)
from pyfcstm.model import load_state_machine_from_text

MODEL = """
input int fault;
def int x = 0;
state Root {
    [*] -> Run;
    state Run {
        during after { x = x + 100; }
        region Motion {
            [*] -> Off;
            state Off { enter { x = x + 1; } }
            state On { during { x = x + 2; } }
            state Gone;
            Off -> On :: Start;
            On -> Off : if [fault > 0];
            On -> Gone : if [fault > 5];
            Gone -> [*];
        }
        region Safety {
            [*] -> Watching;
            state Watching { during { x = x + 3; } }
        }
    }
    state Done;
    Run -> Done : if [x > 10];
}
"""

NESTED = """
state Root {
    [*] -> Outer;
    state Outer {
        region A {
            [*] -> Inner;
            state Inner {
                region A1 { [*] -> X; state X; }
                region A2 { [*] -> Y; state Y; }
            }
        }
        region B { [*] -> Z; state Z; }
    }
}
"""


def domain_of(text):
    return build_bmc_domain(load_state_machine_from_text(text), 2)


def shape(unit):
    return sorted(
        (case.kind, case.target_kind, case.target_state_path) for case in unit.cases
    )


@pytest.mark.unittest
class TestLeafUnits:
    def test_a_leaf_with_a_transition_and_a_during_has_both_paths(self):
        unit = expand_leaf_unit(domain_of(MODEL), "Root.Run.Motion.Off")
        assert unit.unit_id == "work:Root.Run.Motion.Off"
        assert unit.kind == "work"
        assert shape(unit) == [
            ("fallback", "leaf", "Root.Run.Motion.Off"),
            ("transition", "leaf", "Root.Run.Motion.On"),
        ]

    def test_a_guarded_leaf_gives_way_to_its_fallback_when_no_guard_holds(self):
        unit = expand_leaf_unit(domain_of(MODEL), "Root.Run.Motion.On")
        assert shape(unit) == [
            ("fallback", "leaf", "Root.Run.Motion.On"),
            ("transition", "leaf", "Root.Run.Motion.Gone"),
            ("transition", "leaf", "Root.Run.Motion.Off"),
        ]
        fallback = next(case for case in unit.cases if case.kind == "fallback")
        assert len(fallback.action_blocks) == 1

    def test_leaving_a_region_through_exit_ends_the_region_and_asks_the_owner(self):
        unit = expand_leaf_unit(domain_of(MODEL), "Root.Run.Motion.Gone")
        done = [case for case in unit.cases if case.target_kind == "done"]
        assert len(done) == 1
        assert "region:done" in done[0].condition.variables
        assert [case.kind for case in unit.cases if case.target_kind == "leaf"] == [
            "fallback"
        ]

    def test_a_leaf_outside_every_region_expands_like_a_single_path_leaf(self):
        unit = expand_leaf_unit(domain_of(MODEL), "Root.Done")
        assert shape(unit) == [("fallback", "leaf", "Root.Done")]

    def test_entering_a_state_with_regions_stops_at_the_owner(self):
        text = """
        state Root {
            [*] -> A;
            state A;
            state Group {
                region R1 { [*] -> P; state P; }
                region R2 { [*] -> Q; state Q; }
            }
            A -> Group :: Go;
        }
        """
        unit = expand_leaf_unit(domain_of(text), "Root.A")
        owner = [case for case in unit.cases if case.target_kind == "owner"]
        assert [case.target_state_path for case in owner] == ["Root.Group"]
        assert "region:enter" in owner[0].condition.variables

    def test_a_unit_starts_at_a_stoppable_leaf_of_the_domain(self):
        domain = domain_of(MODEL)
        with pytest.raises(InvalidBmcEncoding, match="stoppable leaf"):
            expand_leaf_unit(domain, "Root.Run")
        with pytest.raises(InvalidBmcEncoding):
            expand_leaf_unit(domain, "Root.Nowhere")


@pytest.mark.unittest
class TestOtherUnits:
    def test_the_cold_unit_enters_the_owner_through_the_root_initial_transition(self):
        unit = expand_cold_unit(domain_of(MODEL))
        assert unit.kind == "cold"
        assert shape(unit) == [("initial", "owner", "Root.Run")]

    def test_the_cold_unit_of_a_plain_leaf_machine_ends_on_the_leaf(self):
        text = "state Root { [*] -> A; state A; state B; A -> B; }"
        # No regions: the same expander still describes the first cycle.
        domain = build_bmc_domain(load_state_machine_from_text(text), 1)
        assert shape(expand_cold_unit(domain)) == [("initial", "leaf", "Root.A")]

    def test_an_init_unit_starts_one_region_and_runs_the_enter_of_its_first_state(self):
        domain = domain_of(MODEL)
        motion = expand_init_unit(domain, "Root.Run.Motion")
        assert shape(motion) == [("initial", "leaf", "Root.Run.Motion.Off")]
        assert len(motion.cases[0].action_blocks) == 1
        safety = expand_init_unit(domain, "Root.Run.Safety")
        # Entering a leaf runs its during chain as well.
        assert len(safety.cases[0].action_blocks) == 1

    def test_an_init_unit_can_enter_a_nested_owner(self):
        unit = expand_init_unit(domain_of(NESTED), "Root.Outer.A")
        assert shape(unit) == [("initial", "owner", "Root.Outer.A.Inner")]

    def test_a_continue_unit_runs_the_plain_during_after_before_the_transitions(self):
        unit = expand_continue_unit(domain_of(MODEL), "Root.Run")
        assert unit.kind == "cont"
        assert shape(unit) == [("transition", "leaf", "Root.Done")]
        roles = [block.runtime_role for block in unit.cases[0].action_blocks]
        assert roles == ["plain_during_after"]

    def test_the_other_units_reject_names_the_domain_does_not_have(self):
        domain = domain_of(MODEL)
        with pytest.raises(InvalidBmcEncoding, match="is not in the domain"):
            expand_init_unit(domain, "Root.Run.Nowhere")
        with pytest.raises(InvalidBmcEncoding, match="does not own regions"):
            expand_continue_unit(domain, "Root.Done")
        with pytest.raises(InvalidBmcEncoding):
            expand_continue_unit(domain, "Root.Nowhere")
        with pytest.raises(InvalidBmcEncoding, match="domain must be BmcDomain"):
            expand_init_unit(object(), "Root.Run.Motion")
        with pytest.raises(InvalidBmcEncoding, match="domain must be BmcDomain"):
            expand_continue_unit(object(), "Root.Run")

    def test_a_domain_without_a_model_cannot_be_expanded(self):
        domain = domain_of(MODEL)
        from dataclasses import replace

        bare = replace(domain, model=None)
        with pytest.raises(InvalidBmcEncoding, match="model-backed"):
            expand_cold_unit(bare)
        with pytest.raises(InvalidBmcEncoding, match="domain must be BmcDomain"):
            expand_cold_unit(object())

    def test_case_labels_are_unique_across_units_of_one_domain(self):
        domain = domain_of(MODEL)
        labels = []
        for path in (
            "Root.Run.Motion.Off",
            "Root.Run.Motion.On",
            "Root.Run.Safety.Watching",
        ):
            labels.extend(case.label for case in expand_leaf_unit(domain, path).cases)
        labels.extend(
            case.label for case in expand_init_unit(domain, "Root.Run.Motion").cases
        )
        labels.extend(
            case.label for case in expand_continue_unit(domain, "Root.Run").cases
        )
        labels.extend(case.label for case in expand_cold_unit(domain).cases)
        assert len(labels) == len(set(labels))
