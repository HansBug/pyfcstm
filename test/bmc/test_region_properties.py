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


AFTER_ASPECT_MOVES = """
state Root {
    event Go;
    region A {
        >> during after abstract ADone;
        [*] -> P;
        state P;
        state P2;
        P -> P2 : /Go;
    }
    region B { [*] -> Q; state Q { during abstract QWork; } }
}
"""


@pytest.mark.parametrize(
    "call, found",
    [
        # The handler of the after aspect is told the leaf the region rests in.
        ('called("Root.A.ADone", state="Root.A.P")', True),
        ('called("Root.A.ADone", state="Root.A.P2")', True),
        ('called("Root.A.ADone", active_leaf="Root.A.P2")', True),
        ('called("Root.A.ADone", state="Root.B.Q")', False),
        ('called("Root.A.ADone", state="Root")', False),
        # A state filter that names no action meets every call made in that state.
        ('called(state="Root.B.Q")', True),
        ('called(state="Root.A.P2")', True),
        ('called(state="Root.A.P2", stage="enter")', False),
    ],
)
def test_the_call_of_an_after_aspect_is_selected_by_the_state_its_handler_is_told(
    call, found
):
    assert solve(AFTER_ASPECT_MOVES, "check reach <= 2: %s;" % call).witness_found is found


def test_an_after_aspect_is_not_called_in_the_new_leaf_before_the_region_moves():
    # Without the event the region stays in P, so no call is ever made in P2.
    query = (
        'assume event("Root.Go", *) == false;\n'
        'check reach <= 3: called("Root.A.ADone", state="Root.A.P2");'
    )
    assert solve(AFTER_ASPECT_MOVES, query).witness_found is False


@pytest.mark.parametrize(
    "pattern, bound, found",
    [
        # A region that is left out is free.
        ("Controller.Running{Motion: On}", 2, False),
        ("Controller.Running{Motion: On}", 3, True),
        ("Controller.Running{Safety: Watching}", 2, True),
        ("Controller.Running{Safety: Watching, Motion: On}", 3, True),
        ("Controller.Running{Safety: Watching, Motion: Off}", 2, True),
        # Where a region has to be is where the text says.
        ("Controller.Running{Safety: Watching, Motion: [done]}", 4, False),
        ("Controller.Running{Safety: [init]}", 4, False),
        # A plain path is the pattern that writes no region.
        ("Controller.Running", 2, True),
        ("Controller.Idle", 1, True),
    ],
)
def test_a_configuration_pattern_matches_the_regions_it_writes_and_leaves_the_others_free(
    pattern, bound, found
):
    query = 'check reach <= %d: active("%s");' % (bound, pattern)
    assert solve(interlock(), query).witness_found is found


def test_the_configuration_a_witness_prints_is_a_pattern_the_same_run_satisfies():
    from pyfcstm.bmc import decode_bmc_result_trace

    witness = decode_bmc_result_trace(
        solve(interlock(), 'check reach <= 3: active("Controller.Running.Motion.On");')
    )
    seen = [frame.configuration for frame in witness.frames if frame.configuration]
    assert seen
    for index, text in enumerate(seen, start=1):
        found = solve(interlock(), 'check reach <= %d: active("%s");' % (index, text))
        assert found.witness_found is True, text


def test_a_region_that_waits_for_its_start_matches_init_in_the_first_frame_of_a_hot_start():
    base = (
        'init state("Controller.Running{Motion: On}") havoc * where permit == 1 && motor == 1;\n'
    )
    found = solve(
        interlock(), base + 'check reach <= 1: active("Controller.Running{Safety: [init]}");'
    )
    assert found.witness_found is True
    # After the first cycle the region has started, wherever it began.
    late = solve(
        interlock(),
        base
        + 'assume at 0: !active("Controller.Running{Safety: [init]}");\n'
        'check reach <= 1: active("Controller.Running{Safety: [init]}");',
    )
    assert late.witness_found is False


@pytest.mark.parametrize(
    "pattern",
    [
        "Controller.Running{Nowhere: On}",
        "Controller.Running{Motion: Watching}",
        "Controller.Running{Motion: On, Motion: Off}",
        "Controller.Idle{Motion: On}",
        "Controller.Running{Motion: On",
        "Controller.Running{Motion On}",
        "Controller.Nowhere{Motion: On}",
    ],
)
def test_a_configuration_pattern_that_is_not_one_of_the_model_is_a_diagnostic(pattern):
    with pytest.raises(InvalidBmcQuery) as refused:
        solve(interlock(), 'check reach <= 1: active("%s");' % pattern)
    assert refused.value.diagnostic.code == "invalid_active_pattern"


def test_region_blocks_in_a_model_without_regions_are_a_diagnostic():
    with pytest.raises(InvalidBmcQuery) as refused:
        solve(
            "state Root { [*] -> A; state A; }",
            'check reach <= 1: active("Root{A: A}");',
        )
    assert refused.value.diagnostic.code == "invalid_active_pattern"


CALL_TIME = """
state Root {
    event Go;
    region A { [*] -> P; state P; state P2; P -> P2 :: Go; }
    region B { [*] -> Q; state Q { during abstract QWork; } }
}
"""


@pytest.mark.parametrize(
    "where, found",
    [
        # Region A moved before region B runs, in the same cycle.
        ('active("Root{A: P2}")', True),
        ('active("Root{A: P}")', True),
        ('active("Root{A: P2}") && active("Root{A: P}")', False),
        ('active("Root.B.Q") && active("Root{B: Q}")', True),
        ('active("Root{A: [init]}")', False),
        ('active("Root{A: [done]}")', False),
    ],
)
def test_a_call_filter_asks_where_the_machine_is_at_the_moment_of_the_call(where, found):
    query = 'check reach <= 3: called("Root.B.Q.QWork", where %s);' % where
    assert solve(CALL_TIME, query).witness_found is found


ENTRY_CALLS = """
state Root {
    region A { [*] -> P; state P { enter abstract PEnter; } }
    region B { [*] -> Q; state Q { enter abstract QEnter; } }
}
"""


@pytest.mark.parametrize(
    "call, where, found",
    [
        # Region A starts before region B: A's entry still sees B waiting, and B's
        # entry sees A where it came to rest.
        ("Root.A.P.PEnter", 'active("Root{B: [init]}")', True),
        ("Root.A.P.PEnter", 'active("Root{A: P}")', True),
        ("Root.B.Q.QEnter", 'active("Root{A: P}")', True),
        ("Root.B.Q.QEnter", 'active("Root{A: P, B: Q}")', True),
        ("Root.B.Q.QEnter", 'active("Root{A: [init]}")', False),
        ("Root.B.Q.QEnter", 'active("Root{B: [init]}")', False),
    ],
)
def test_the_entry_of_a_region_sees_the_regions_that_have_not_started_as_init(
    call, where, found
):
    query = 'check reach <= 1: called("%s", where %s);' % (call, where)
    assert solve(ENTRY_CALLS, query).witness_found is found


def test_call_time_active_in_a_model_without_regions_is_the_state_the_action_runs_in():
    text = """
    state Root {
        [*] -> A;
        state A { during abstract Hook; }
        state B;
        A -> B;
    }
    """
    assert solve(text, 'check reach <= 2: called("Root.A.Hook", where active("Root.A"));').witness_found is True
    assert solve(text, 'check reach <= 2: called("Root.A.Hook", where active("Root"));').witness_found is True
    assert solve(text, 'check reach <= 2: called("Root.A.Hook", where active("Root.B"));').witness_found is False


@pytest.mark.parametrize(
    "text",
    [
        "Controller.Running{Motion On}",
        "S" + "{A: S" * 4000 + "}" * 4000,
        "Controller.Running{Motion: Controller.Idle}",
        "Controller.Idle{Motion: On}",
    ],
)
def test_a_pattern_read_against_the_domain_is_refused_with_a_query_error(text):
    from pyfcstm.bmc import build_bmc_domain, parse_active_pattern

    domain = build_bmc_domain(load_state_machine_from_text(interlock()), 1)
    with pytest.raises(InvalidBmcQuery):
        parse_active_pattern(domain, text)

