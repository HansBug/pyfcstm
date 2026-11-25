"""Properties over models with regions, through the public BMC entry points."""

import pytest

from pyfcstm.bmc import InvalidBmcQuery, compile_bmc_query, solve_bmc_property
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

TEMPLATE = """
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

SAFETY = """Safety {
            [*] -> Watching;
            state Watching {
                during { if [fault != 0] { permit = 0; } else { permit = 1; } }
            }
        }"""
MOTION = """Motion {
            [*] -> Off;
            state Off { during { motor = 0; } }
            state On { during { motor = 1; } }
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [permit == 0 || requested == 0];
        }"""


def interlock(safety_first=True):
    first, second = (SAFETY, MOTION) if safety_first else (MOTION, SAFETY)
    return TEMPLATE % {"first": first, "second": second}


def solve(text, query):
    return solve_bmc_property(
        compile_bmc_query(load_state_machine_from_text(text), query)
    )


FAULT_CYCLE = 'check forbid <= 4: permit == 0 && motor == 1;'


@pytest.mark.parametrize("safety_first, holds", [(True, True), (False, False)])
def test_the_motor_stops_in_the_fault_cycle_only_when_safety_runs_first(
    safety_first, holds
):
    assert solve(interlock(safety_first), FAULT_CYCLE).property_satisfied is holds


@pytest.mark.parametrize("bound, found", [(2, False), (3, True)])
def test_reach_finds_a_state_inside_a_region_exactly_when_it_can_be_there(
    bound, found
):
    query = 'check reach <= %d: active("Controller.Running.Motion.On");' % bound
    assert solve(interlock(), query).witness_found is found


def test_two_states_of_the_same_region_are_never_active_together():
    query = (
        'check reach <= 4: active("Controller.Running.Motion.On") '
        '&& active("Controller.Running.Motion.Off");'
    )
    assert solve(interlock(), query).witness_found is False


def test_states_of_different_regions_are_active_together():
    query = (
        'check reach <= 3: active("Controller.Running.Motion.On") '
        '&& active("Controller.Running.Safety.Watching");'
    )
    assert solve(interlock(), query).witness_found is True


def test_the_owner_is_active_whenever_one_of_its_regions_rests_in_a_state():
    query = (
        'check forbid <= 3: active("Controller.Running.Motion.Off") '
        '&& !active("Controller.Running");'
    )
    assert solve(interlock(), query).property_satisfied is True


@pytest.mark.parametrize(
    "label",
    [
        "Controller.Running.Safety.Watching::fallback::"
        "Controller.Running.Safety.Watching::0",
        "Controller.Running.Motion.Off::transition::"
        "Controller.Running.Motion.On::0",
        "Controller.Running.Motion.Off::fallback::"
        "Controller.Running.Motion.Off::0",
        "Controller.Idle::transition::Controller.Running::0",
    ],
)
def test_cover_reaches_a_local_case_of_every_region(label):
    assert solve(interlock(), 'check cover <= 3: case("%s");' % label).witness_found


def test_a_local_case_that_needs_more_cycles_than_the_bound_is_not_covered():
    label = "Controller.Running.Motion.Off::transition::Controller.Running.Motion.On::0"
    assert solve(interlock(), 'check cover <= 2: case("%s");' % label).witness_found is False


def test_an_unknown_local_case_is_refused_like_one_without_regions():
    with pytest.raises(InvalidBmcQuery, match="cover case label is unknown"):
        solve(interlock(), 'check cover <= 3: case("Nope::fallback::Nope::0");')


def test_the_start_of_a_region_is_a_case_that_cover_does_not_take():
    label = "Controller.Running::initial::Controller.Running.Safety.Watching::0"
    with pytest.raises(InvalidBmcQuery, match="not coverable"):
        solve(interlock(), 'check cover <= 3: case("%s");' % label)


@pytest.mark.parametrize(
    "query, satisfied",
    [
        # The motor only ever runs inside Running.
        ('check invariant <= 4: motor == 0 || active("Controller.Running");', True),
        # Without a Start event the machine stays in Idle.
        ('check must_reach <= 3: active("Controller.Running");', False),
        # The root is active in every frame of every run.
        ('check exists_always <= 3: active("Controller");', True),
        # Start moves Idle to Running in the cycle it arrives in.
        (
            'check response <= 4: trigger event("Controller.Start", current) '
            '&& active("Controller.Idle") -> within 1 active("Controller.Running");',
            True,
        ),
        # In the cold-start cycle the event arrives before Idle is entered.
        (
            'check response <= 4: trigger event("Controller.Start", current) '
            '-> within 1 active("Controller.Running");',
            False,
        ),
    ],
)
def test_the_other_property_kinds_work_on_a_model_with_regions(query, satisfied):
    assert solve(interlock(), query).property_satisfied is satisfied


def test_calls_of_a_region_leaf_are_counted_in_the_cycles_they_are_made():
    text = """
    state Root {
        [*] -> P;
        state P {
            region A { [*] -> X; state X { during abstract WorkX; } }
            region B { [*] -> Y; state Y { during abstract WorkY; } }
        }
    }
    """
    counted = (
        'check reach <= 2: call_count("Root.P.A.X.WorkX", step=0..1) == 2 '
        '&& call_count("Root.P.B.Y.WorkY", step=0..1) == 2;'
    )
    assert solve(text, counted).witness_found is True
    too_many = 'check reach <= 2: call_count("Root.P.A.X.WorkX", step=0..1) == 3;'
    assert solve(text, too_many).witness_found is False


ASPECT_OVER_GROUP = """
state Root {
    >> during before abstract RootPre;
    region A { [*] -> P; state P; }
    region B { [*] -> X; state X; }
}
"""


@pytest.mark.parametrize(
    "filters, found",
    [
        ('state="Root"', True),
        ('active_leaf="Root"', True),
        ('state="Root.A.P"', False),
        ('active_leaf="Root.A.P"', False),
    ],
)
def test_an_aspect_over_a_group_is_called_in_the_state_the_handler_is_told(
    filters, found
):
    query = 'check reach <= 2: called("Root.RootPre", %s);' % filters
    assert solve(ASPECT_OVER_GROUP, query).witness_found is found


def test_an_aspect_below_the_group_is_called_in_the_leaf_it_wraps():
    text = """
    state Root {
        region A { >> during before abstract APre; [*] -> P; state P; }
        region B { [*] -> X; state X; }
    }
    """
    for filters, found in (('state="Root.A.P"', True), ('state="Root"', False)):
        query = 'check reach <= 2: called("Root.A.APre", %s);' % filters
        assert solve(text, query).witness_found is found


def test_the_call_of_an_after_aspect_cannot_be_selected_by_state():
    from pyfcstm.bmc import UnsupportedBmcQuery

    text = """
    state Root {
        region A { >> during after abstract ADone; [*] -> P; state P; }
        region B { [*] -> X; state X; }
    }
    """
    assert solve(text, 'check reach <= 2: called("Root.A.ADone");').witness_found is True
    with pytest.raises(UnsupportedBmcQuery, match="aspect in a model with regions"):
        solve(text, 'check reach <= 2: called("Root.A.ADone", state="Root.A.P");')


def test_a_state_filter_only_meets_the_aspect_calls_it_names_an_action_for():
    text = """
    state Root {
        >> during before abstract RootPre;
        region A { >> during after abstract ADone; [*] -> P; state P; }
        region B { [*] -> X; state X; }
    }
    """
    # The settlement of region A is never selected by this action, so the state
    # filter does not have to be decided for it.
    query = 'check reach <= 2: called("Root.RootPre", state="Root");'
    assert solve(text, query).witness_found is True
