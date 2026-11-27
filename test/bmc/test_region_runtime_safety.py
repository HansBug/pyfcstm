"""Runtime errors of a model with regions: where the BMC locates them.

The relation of a cycle requires every operation it runs to be defined, so the
cycle in which the runtime raises has no solution there.  The runtime-safety
check lowers the cycles a second time to find those operations, and it has to
agree with the simulator on which cycle raises, including on candidates that
dead-end or lose to a higher priority, which the runtime evaluates all the same.
"""

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, check_runtime_safety
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeExpressionError

pytestmark = pytest.mark.unittest

# The candidate leads into a dead end and its effect divides by the input.
DEAD_END = """
input int d;
def int x = 0;
state Root {
    [*] -> Run;
    state Run {
        region R {
            [*] -> A;
            state A { during { x = x + 1; } }
            state C {
                [*] -> J effect { x = 10 % d; };
                pseudo state J;
            }
            A -> C : if [d == 0];
        }
    }
}
"""

# A lower-priority continuation of a finished group, evaluated although the
# higher one is taken: its effect, its enter action and its guard each fail.
CONTINUATION_EFFECT = """
input int d;
def int x = 0;
state Root {
    [*] -> Q;
    state Q { region R { [*] -> W; state W; W -> [*]; } }
    state T1;
    state T2;
    Q -> T1 : if [d == 0];
    Q -> T2 : if [d == 0] effect { x = 10 % d; };
}
"""

CONTINUATION_ENTER = """
input int d;
def int x = 0;
state Root {
    [*] -> Q;
    state Q { region R { [*] -> W; state W; W -> [*]; } }
    state T1;
    state T2 { enter { x = 10 % d; } }
    Q -> T1 : if [d == 0];
    Q -> T2 : if [d == 0];
}
"""

CONTINUATION_GUARD = """
input int d;
def int x = 0;
state Root {
    [*] -> Q;
    state Q { region R { [*] -> W; state W; W -> [*]; } }
    state T1;
    state T2;
    Q -> T1 : if [d == 0];
    Q -> T2 : if [10 % d == 0];
}
"""

# A plain action of a leaf in a region, on a path the cycle takes.
ACTION_IN_REGION = """
input int d;
def int x = 0;
state Root {
    region A { [*] -> P; state P { during { x = 10 % d; } } }
    region B { [*] -> Q; state Q; }
}
"""

# Nothing here can raise.
HARMLESS = """
input int d;
def int x = 0;
state Root {
    region A { [*] -> P; state P { during { x = x + d; } } }
    region B { [*] -> Q; state Q { during { x = x + 1; } } }
}
"""


def raising_cycle(text, inputs):
    """Return the cycle in which the simulator raises, or ``None``."""
    runtime = SimulationRuntime(load_state_machine_from_text(text), input_source={"d": 1})
    for index, value in enumerate(inputs):
        try:
            runtime.cycle(inputs={"d": value})
        except SimulationRuntimeExpressionError:
            return index
    return None


def check(text, bound):
    model = load_state_machine_from_text(text)
    core = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= %d: terminated();" % bound)
    )
    return check_runtime_safety(core)


@pytest.mark.parametrize(
    "text",
    [DEAD_END, CONTINUATION_EFFECT, CONTINUATION_ENTER, CONTINUATION_GUARD],
    ids=["dead_end", "continuation_effect", "continuation_enter", "continuation_guard"],
)
def test_an_error_the_runtime_raises_in_a_cycle_is_located_in_that_cycle(text):
    assert raising_cycle(text, [1, 0]) == 1
    result = check(text, 2)
    assert result.status == "violated"
    assert result.error.step == 1
    assert result.error.kind == "modulo_by_zero"


def test_an_action_of_a_leaf_in_a_region_is_located_in_the_first_cycle():
    assert raising_cycle(ACTION_IN_REGION, [0]) == 0
    result = check(ACTION_IN_REGION, 1)
    assert (result.status, result.error.step) == ("violated", 0)


def test_a_model_without_an_operation_that_can_raise_has_nothing_to_check():
    assert raising_cycle(HARMLESS, [0, 1, 2]) is None
    result = check(HARMLESS, 3)
    assert (result.status, result.sites, result.error) == ("not_applicable", 0, None)


def test_the_error_is_only_reachable_for_the_inputs_that_raise():
    # With d fixed to a value that never divides by zero the same model is safe.
    model = load_state_machine_from_text(DEAD_END)
    core = build_bmc_core_formula(
        BmcEngine(model).prepare(
            "assume always: d == 1;\ncheck reach <= 2: terminated();"
        )
    )
    assert check_runtime_safety(core).status == "safe"


AFTER_ASPECT_DIVIDES = """
input int d;
def int x = 0;
state Root {
    >> during after { x = 10 % d; }
    region A { [*] -> P; state P { during { x = x + 1; } } }
    region B { [*] -> Q; state Q; }
}
"""


def test_an_after_aspect_over_the_regions_is_checked_for_errors():
    assert raising_cycle(AFTER_ASPECT_DIVIDES, [0]) == 0
    assert check(AFTER_ASPECT_DIVIDES, 1).status == "violated"


# Region B divides by d, which is zero; region A starts only when n > 1.
START_FAILS_BEFORE_DIVISION = """
def int n = 0;
def int d = 0;
state Root {
    region A { [*] -> P : if [n > 1]; state P; }
    region B { [*] -> X; state X { during { n = 1 / d; } } }
}
"""


def hot_safety(initial_n):
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property

    query = (
        'init state("Root{A: [init], B: X}") havoc * where n == %d && d == 0;\n'
        "check reach <= 1: n == 5;" % initial_n
    )
    return solve_bmc_property(
        compile_bmc_query(
            load_state_machine_from_text(START_FAILS_BEFORE_DIVISION), query
        ),
        timeout_ms=20000,
    )


def test_a_start_that_fails_before_a_division_makes_the_cycle_a_delta_without_error():
    # The cycle is a Delta, so region B never runs and the division is not met.
    result = hot_safety(0)
    assert result.runtime_safety.status == "safe"
    assert result.outcome != "runtime_error"


def test_the_division_is_met_once_the_start_succeeds():
    result = hot_safety(2)
    assert result.runtime_safety.status == "violated"
    assert result.runtime_safety.error.step == 0


def test_a_non_integral_write_to_an_int_inside_a_region_is_located_in_its_cycle():
    text = (
        "def int x = 0; def int y = 0;\n"
        "state Root {\n"
        "    region A { [*] -> P; state P { during { y = x / 2; x = x + 1; } } }\n"
        "    region B { [*] -> Q; state Q; }\n"
        "}\n"
    )
    runtime = SimulationRuntime(load_state_machine_from_text(text))
    runtime.cycle()
    with pytest.raises(SimulationRuntimeExpressionError):
        runtime.cycle()
    result = check(text, 2)
    assert result.status == "violated"
    assert (result.error.kind, result.error.step) == ("writeback_non_integral", 1)


def test_a_division_behind_a_guarded_region_start_is_decided_without_timing_out():
    text = """
    input int d;
    def int y = 0;
    state Root {
        [*] -> Run;
        state Run {
            region A { [*] -> P : if [d == 1]; state P; }
            region B { [*] -> Q; state Q { during { y = 10 / d; } } }
        }
    }
    """
    model = load_state_machine_from_text(text)
    runtime = SimulationRuntime(model, input_source={"d": 1})
    runtime.cycle(inputs={"d": 1})
    with pytest.raises(SimulationRuntimeExpressionError):
        runtime.cycle(inputs={"d": 0})
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property

    result = solve_bmc_property(
        compile_bmc_query(model, "check reach <= 2: terminated();"), timeout_ms=20000
    )
    assert result.runtime_safety.status == "violated"
    assert result.runtime_safety.error.step == 1
