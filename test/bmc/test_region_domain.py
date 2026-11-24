"""Domain numbering of models that declare regions."""

import pytest

from pyfcstm.bmc import (
    REGION_DONE_ID,
    REGION_INACTIVE_ID,
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcDomain,
    BmcTraceSymbols,
    EventDomainEntry,
    InvalidBmcDomain,
    RegionDomainEntry,
    StateDomainEntry,
    BmcBuildError,
    build_bmc_domain,
)
from pyfcstm.model import load_state_machine_from_text

CONTROLLER = """
input int fault;
def int x = 0;
state Root {
    [*] -> Run;
    state Run {
        event Stop;
        region Motion {
            event Tick;
            [*] -> Off;
            state Off;
            state On { during { x = x + 1; } }
            Off -> On : Tick;
            On -> Off : if [fault > 0];
        }
        region Safety {
            [*] -> Watching;
            state Watching;
        }
    }
    state Idle;
    Run -> Idle :: Stop;
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

PLAIN = "def int x = 0; state Root { [*] -> A; state A { during { x = x + 1; } } }"


def domain_of(text, bound=2):
    return build_bmc_domain(load_state_machine_from_text(text), bound)


@pytest.mark.unittest
class TestRegionDomain:
    def test_regions_are_numbered_in_path_order_with_their_owner(self):
        domain = domain_of(CONTROLLER)
        assert [
            (item.path, item.owner_path, item.ordinal) for item in domain.regions
        ] == [
            ("Root.Run.Motion", "Root.Run", 0),
            ("Root.Run.Safety", "Root.Run", 1),
        ]
        assert [item.id for item in domain.regions] == [0, 1]
        assert all(item.enclosing_region_path is None for item in domain.regions)

    def test_states_inside_a_region_keep_the_owner_as_parent(self):
        domain = domain_of(CONTROLLER)
        off = domain.state_by_path("Root.Run.Motion.Off")
        assert off.parent_path == "Root.Run"
        assert off.region_path == "Root.Run.Motion"
        run = domain.state_by_path("Root.Run")
        assert run.owns_regions and run.region_path is None
        assert not domain.state_by_path("Root.Idle").owns_regions

    def test_position_ids_are_the_resting_states_of_the_region_namespace(self):
        domain = domain_of(CONTROLLER)
        motion = domain.regions[0]
        assert motion.position_state_ids == (
            domain.state_path_to_id("Root.Run.Motion.Off"),
            domain.state_path_to_id("Root.Run.Motion.On"),
        )

    def test_a_state_that_owns_regions_is_a_stable_resting_position(self):
        domain = domain_of(CONTROLLER)
        run_id = domain.state_path_to_id("Root.Run")
        assert run_id in domain.stable_state_ids
        assert STATE_TERMINATE_ID in domain.stable_state_ids

    def test_nested_regions_know_the_region_they_sit_in(self):
        domain = domain_of(NESTED)
        by_path = {item.path: item for item in domain.regions}
        assert by_path["Root.Outer.A.Inner.A1"].enclosing_region_path == "Root.Outer.A"
        assert by_path["Root.Outer.A"].enclosing_region_path is None
        inner_id = domain.state_path_to_id("Root.Outer.A.Inner")
        # A nested owner is a resting position of the region it sits in.
        assert inner_id in by_path["Root.Outer.A"].position_state_ids

    def test_an_event_declared_in_a_region_is_owned_by_the_region(self):
        domain = domain_of(CONTROLLER)
        tick = domain.event_by_path("Root.Run.Motion.Tick")
        assert tick.owner_region_path == "Root.Run.Motion"
        assert tick.owner_state_path == "Root.Run.Motion"
        assert tick.owner_state_id == domain.state_path_to_id("Root.Run")
        stop = domain.event_by_path("Root.Run.Stop")
        assert stop.owner_region_path is None

    def test_sentinel_position_values_are_not_state_ids(self):
        domain = domain_of(CONTROLLER)
        state_ids = {entry.id for entry in domain.states}
        assert REGION_DONE_ID not in state_ids
        assert REGION_INACTIVE_ID not in state_ids
        assert (
            len({REGION_DONE_ID, REGION_INACTIVE_ID, STATE_INIT_ID, STATE_TERMINATE_ID})
            == 4
        )

    def test_canonical_form_mentions_regions_only_for_models_that_have_them(self):
        plain = domain_of(PLAIN).to_canonical()
        assert "regions" not in plain
        assert all(
            "region_path" not in item and "owns_regions" not in item
            for item in plain["states"]
        )
        regional = domain_of(CONTROLLER).to_canonical()
        assert [item["path"] for item in regional["regions"]] == [
            "Root.Run.Motion",
            "Root.Run.Safety",
        ]
        run = next(item for item in regional["states"] if item["path"] == "Root.Run")
        assert run["owns_regions"] is True

    def test_a_model_without_regions_has_no_regions_or_region_positions(self):
        domain = domain_of(PLAIN)
        assert domain.regions == ()
        symbols = BmcTraceSymbols.allocate(domain)
        assert symbols.region_positions == ()
        assert "region_positions" not in symbols.to_canonical()
        with pytest.raises(BmcBuildError, match="frame index out of range"):
            symbols.region_position(0, "Root.A")

    def test_region_position_symbols_exist_for_every_frame_and_region(self):
        domain = domain_of(CONTROLLER, bound=3)
        symbols = BmcTraceSymbols.allocate(domain)
        for frame in range(4):
            for region in domain.regions:
                assert (
                    symbols.region_position(frame, region.path)
                    .decl()
                    .name()
                    .startswith("F_%d_region_" % frame)
                )
        assert "region_positions" in symbols.to_canonical()
        with pytest.raises(BmcBuildError, match="Unknown region path"):
            symbols.region_position(0, "Root.Run.Nowhere")
        with pytest.raises(BmcBuildError, match="frame index out of range"):
            symbols.region_position(9, "Root.Run.Motion")


@pytest.mark.unittest
class TestRegionDomainContracts:
    def test_a_state_in_a_region_must_extend_the_owner_path(self):
        with pytest.raises(
            InvalidBmcDomain, match="Region path must extend the owner path"
        ):
            StateDomainEntry(1, "Other.A.X", "X", "leaf", "Root", region_path="Other.A")

    def test_a_state_path_must_follow_its_region_path_and_name(self):
        with pytest.raises(InvalidBmcDomain, match="does not match region path"):
            StateDomainEntry(1, "Root.A.Y", "X", "leaf", "Root", region_path="Root.A")

    def test_only_a_composite_can_own_regions(self):
        with pytest.raises(
            InvalidBmcDomain, match="Only composite states can own regions"
        ):
            StateDomainEntry(1, "Root.A", "A", "leaf", "Root", owns_regions=True)

    def test_a_sentinel_cannot_sit_in_or_own_regions(self):
        with pytest.raises(InvalidBmcDomain, match="cannot own or sit in regions"):
            StateDomainEntry(
                STATE_INIT_ID,
                "$STATE_INIT",
                "STATE_INIT",
                "sentinel",
                is_sentinel=True,
                owns_regions=True,
            )

    def test_a_region_entry_checks_its_path_and_ids(self):
        assert RegionDomainEntry(
            0, "Root.A", "A", "Root", 0, 0, None, (3, 1)
        ).position_state_ids == (3, 1)
        with pytest.raises(
            InvalidBmcDomain, match="path does not match owner path and name"
        ):
            RegionDomainEntry(0, "Root.B", "A", "Root", 0, 0, None, ())
        with pytest.raises(InvalidBmcDomain, match="Region ids must be non-negative"):
            RegionDomainEntry(-1, "Root.A", "A", "Root", 0, 0, None, ())
        with pytest.raises(
            InvalidBmcDomain, match="Region ordinals must be non-negative"
        ):
            RegionDomainEntry(0, "Root.A", "A", "Root", 0, -1, None, ())

    def test_an_event_owned_by_a_region_must_match_that_region(self):
        domain = domain_of(CONTROLLER)
        wrong = EventDomainEntry(
            99,
            "Root.Run.Motion.Boom",
            "Boom",
            "Root.Run.Motion",
            domain.state_path_to_id("Root.Idle"),
            owner_region_path="Root.Run.Motion",
        )
        with pytest.raises(InvalidBmcDomain, match="owner region does not match"):
            BmcDomain(
                domain.bound,
                domain.states,
                domain.events + (wrong,),
                domain.variables,
                domain.frames,
                domain.steps,
                domain.event_inputs,
                domain.initial_state_ids,
                domain.stable_state_ids,
                regions=domain.regions,
            )

    def test_every_region_owner_needs_regions_and_every_region_an_owner(self):
        domain = domain_of(NESTED)
        with pytest.raises(
            InvalidBmcDomain, match="Every region-owning state needs regions"
        ):
            BmcDomain(
                domain.bound,
                domain.states,
                domain.events,
                domain.variables,
                domain.frames,
                domain.steps,
                domain.event_inputs,
                domain.initial_state_ids,
                domain.stable_state_ids,
                regions=domain.regions[:0],
            )
        lonely = RegionDomainEntry(
            9,
            "Root.Outer.A.Inner.Ghost",
            "Ghost",
            "Root.Outer.A.Inner",
            domain.state_path_to_id("Root.Outer.A.Inner.A1.X"),
            0,
            None,
            (),
        )
        with pytest.raises(InvalidBmcDomain, match="region-owning state as owner"):
            BmcDomain(
                domain.bound,
                domain.states,
                domain.events,
                domain.variables,
                domain.frames,
                domain.steps,
                domain.event_inputs,
                domain.initial_state_ids,
                domain.stable_state_ids,
                regions=domain.regions + (lonely,),
            )

    def test_an_event_named_by_an_initial_transition_of_a_region_is_collected(self):
        text = """
        state Root {
            region A { event Start; [*] -> P : Start; state P; }
            region B { [*] -> Q; state Q; }
        }
        """
        assert [event.path for event in domain_of(text).events] == ["Root.A.Start"]

    def test_region_entries_are_checked_against_each_other_and_the_states(self):
        domain = domain_of(NESTED)
        outer = domain.state_path_to_id("Root.Outer")

        def with_region(extra):
            return BmcDomain(
                domain.bound,
                domain.states,
                domain.events,
                domain.variables,
                domain.frames,
                domain.steps,
                domain.event_inputs,
                domain.initial_state_ids,
                domain.stable_state_ids,
                regions=domain.regions + (extra,),
            )

        same_path = RegionDomainEntry(
            9, "Root.Outer.A", "A", "Root.Outer", outer, 5, None, ()
        )
        with pytest.raises(InvalidBmcDomain, match="Duplicate region path"):
            with_region(same_path)
        same_id = RegionDomainEntry(
            0, "Root.Outer.Z", "Z", "Root.Outer", outer, 5, None, ()
        )
        with pytest.raises(InvalidBmcDomain, match="Duplicate region id"):
            with_region(same_id)
        lost = RegionDomainEntry(
            9, "Root.Outer.Y", "Y", "Root.Outer", outer, 5, "Nowhere", ()
        )
        with pytest.raises(InvalidBmcDomain, match="unknown enclosing region"):
            with_region(lost)
        unknown = RegionDomainEntry(
            9, "Root.Outer.X", "X", "Root.Outer", outer, 5, None, (999,)
        )
        with pytest.raises(InvalidBmcDomain, match="unknown position state id"):
            with_region(unknown)
