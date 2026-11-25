"""Structural analysis of a model with regions: branches that must all be over."""

import re

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.verify.topology import (
    event_emission_to_consumer_reachable,
    strongly_connected_components,
    topological_finite,
    topological_inevitable_terminator,
    topological_reachable_set,
    unreachable_states,
)

pytestmark = pytest.mark.unittest


def machine(text):
    return load_state_machine_from_text(text)


BOTH_FINISH = """
state Root {
    event Go; event Fin;
    [*] -> Run;
    state Run {
        region A { [*] -> P; state P; P -> [*] :: Fin; }
        region B { [*] -> Q; state Q; Q -> [*] :: Fin; }
    }
    state After;
    state Never;
    Run -> After;
    After -> [*];
}
"""

ONE_STUCK = BOTH_FINISH.replace("Q -> [*] :: Fin;", "")


def test_the_owner_goes_on_when_every_region_can_finish():
    model = machine(BOTH_FINISH)
    assert unreachable_states(model) == ("Root.Never",)
    assert topological_finite(model).finite is True
    # Never is not reachable, so it does not count against ending for sure.
    assert topological_inevitable_terminator(model).inevitable is True
    assert "Root.After" in topological_reachable_set(model)["Root.Run"]


def test_the_owner_never_goes_on_when_one_region_cannot_finish():
    model = machine(ONE_STUCK)
    assert unreachable_states(model) == ("Root.After", "Root.Never")
    report = topological_finite(model)
    assert report.finite is False
    # P can finish its own region, but the group cannot be over: no way out.
    assert ("deadlock", "Root.Run.A.P") in report.counterexamples
    assert ("deadlock", "Root.Run.B.Q") in report.counterexamples
    assert "Root.After" not in topological_reachable_set(model)["Root.Run"]


def test_a_state_inside_a_region_that_nothing_enters_is_unreachable():
    model = machine(
        "state Root { region A { [*] -> P; state P; state Dead; } region B { [*] -> Q; state Q; } }"
    )
    assert unreachable_states(model) == ("Root.A.Dead",)


def test_the_topology_ends_for_sure_when_every_branch_ends_and_the_root_leaves():
    model = machine(
        """
        state Root {
            event Fin;
            region A { [*] -> P; state P; P -> [*] :: Fin; }
            region B { [*] -> Q; state Q; Q -> [*] :: Fin; }
        }
        """
    )
    assert topological_finite(model).finite is True
    assert topological_inevitable_terminator(model).inevitable is True
    assert strongly_connected_components(model) == ()


def test_a_cycle_inside_one_region_is_a_cycle_of_the_model():
    model = machine(
        "state Root { region A { [*] -> P; state P; state P2; P -> P2 :: Go; P2 -> P :: Back; }"
        " region B { [*] -> Q; state Q; } }"
    )
    assert strongly_connected_components(model) == (("Root.A.P", "Root.A.P2"),)
    assert topological_inevitable_terminator(model).inevitable is False


def test_a_nested_owner_must_be_over_before_the_region_it_sits_in_can_finish():
    text = """
    state Root {
        [*] -> Run;
        state Run {
            region Outer {
                [*] -> Inner;
                state Inner {
                    region X { [*] -> X1; state X1; X1 -> [*] :: Fin; }
                    region Y { [*] -> Y1; state Y1; %s }
                }
                Inner -> [*];
            }
            region Side { [*] -> S; state S; S -> [*] :: Fin; }
        }
        state After;
        Run -> After;
        event Fin;
    }
    """
    finishing = machine(text % "Y1 -> [*] :: Fin;")
    assert unreachable_states(finishing) == ()
    stuck = machine(text % "")
    # Y cannot finish, so Inner cannot, so Outer cannot, so Run goes nowhere.
    assert unreachable_states(stuck) == ("Root.After",)


def test_a_forced_transition_takes_the_whole_group_away_without_waiting():
    model = machine(
        """
        state Root {
            event Stop;
            [*] -> Run;
            state Run {
                region A { [*] -> P; state P; }
                region B { [*] -> Q; state Q; }
            }
            state Idle;
            !Run -> Idle :: Stop;
        }
        """
    )
    assert unreachable_states(model) == ()
    assert "Root.Idle" in topological_reachable_set(model)["Root.Run"]


def test_an_event_of_the_owner_has_a_consumer_only_when_the_group_can_finish():
    text = """
    state Root {
        event Go; event Fin;
        [*] -> Run;
        state Run {
            region A { [*] -> P; state P; P -> [*] :: Fin; }
            region B { [*] -> Q; state Q; %s }
        }
        state After;
        Run -> After :: Go;
    }
    """
    assert event_emission_to_consumer_reachable(machine(text % "Q -> [*] :: Fin;")) == ()
    # Region B cannot finish, so the owner's transition that waits for Go can
    # never be selected.
    assert event_emission_to_consumer_reachable(machine(text % "")) == ("Root.Run.Go",)


def _without_regions(paths, region_names):
    pattern = re.compile(r"\.(?:%s)(?=\.)" % "|".join(region_names))
    return tuple(sorted(pattern.sub("", path) for path in paths))


@pytest.mark.parametrize(
    "body",
    [
        "state P; state Q; P -> Q :: Go; Q -> [*] :: Fin;",
        "state P; state Q; P -> Q :: Go;",
        "state P; state Q; P -> Q :: Go; Q -> P :: Back; P -> [*] :: Fin;",
        "state P; state Dead;",
    ],
)
def test_a_plain_composite_state_is_the_case_of_one_region(body):
    # The same composite state, once plain and once as the only region of an owner,
    # is judged the same, up to the name of the region in the paths.
    template = """
    state Root {
        event Go; event Back; event Fin;
        [*] -> Run;
        state Run { %s }
        state After;
        Run -> After;
    }
    """
    plain = machine(template % ("[*] -> P; " + body))
    regional = machine(template % ("region Only { [*] -> P; " + body + " }"))
    assert _without_regions(unreachable_states(regional), ["Only"]) == tuple(
        sorted(unreachable_states(plain))
    )
    assert topological_finite(regional).finite == topological_finite(plain).finite
    assert (
        topological_inevitable_terminator(regional).inevitable
        == topological_inevitable_terminator(plain).inevitable
    )
    assert _without_regions(
        strongly_connected_components(regional) and sum(strongly_connected_components(regional), ()),
        ["Only"],
    ) == tuple(sorted(sum(strongly_connected_components(plain), ())))
    assert event_emission_to_consumer_reachable(regional) == event_emission_to_consumer_reachable(plain)
