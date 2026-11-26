"""Local cases of a model with regions: public labels, scopes and execution order."""

import pytest
import z3

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
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


def core_of(text, bound):
    model = load_state_machine_from_text(text)
    return build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= %d: terminated();" % bound)
    )


def run(core, cycles):
    """Solve a pinned run; ``cycles`` is a list of dicts with events and inputs."""
    symbols = core.symbols
    pins = []
    for index, cycle in enumerate(cycles):
        events = set(cycle.get("events", ()))
        for event in core.context.domain.events:
            literal = symbols.event_input(index, event.path)
            pins.append(literal if event.path in events else z3.Not(literal))
        for name, value in cycle.get("inputs", {}).items():
            pins.append(symbols.step_inputs[index][name] == value)
    solver = z3.Solver()
    solver.add(core.core, *pins)
    assert solver.check() == z3.sat
    return solver.model()


def executed(core, model, step):
    """Return the cases a step executed, flattened in execution order."""
    found = []

    def walk(relations):
        for relation in relations:
            if z3.is_true(model.eval(relation.selector, True)):
                found.append(relation)
                walk(relation.children)

    walk(core.region_steps[step].cases)
    return sorted(found, key=lambda relation: relation.order)


def listing(core, model, step):
    return [
        (item.case.scope, item.case.kind, item.case.public_label)
        for item in executed(core, model, step)
    ]


CYCLES = [
    {"inputs": {"fault": 0, "requested": 0}},
    {"events": ["Controller.Start"], "inputs": {"fault": 0, "requested": 0}},
    {"inputs": {"fault": 0, "requested": 1}},
]


def test_the_cold_start_is_one_case_named_after_the_start_marker():
    core = core_of(interlock(), 3)
    model = run(core, CYCLES)
    assert listing(core, model, 0) == [
        (None, "initial", "__init__::initial::Controller.Idle::0")
    ]


def test_entering_a_group_lists_the_transition_and_then_every_start_in_order():
    core = core_of(interlock(), 3)
    model = run(core, CYCLES)
    assert listing(core, model, 1) == [
        (None, "transition", "Controller.Idle::transition::Controller.Running::0"),
        (
            "Controller.Running",
            "initial",
            "Controller.Running::initial::Controller.Running.Safety.Watching::0",
        ),
        (
            "Controller.Running",
            "initial",
            "Controller.Running::initial::Controller.Running.Motion.Off::0",
        ),
    ]


def test_the_regions_of_a_resting_group_are_listed_in_declaration_order():
    core = core_of(interlock(), 3)
    model = run(core, CYCLES)
    assert listing(core, model, 2) == [
        (
            "Controller.Running.Safety",
            "fallback",
            "Controller.Running.Safety.Watching::fallback::"
            "Controller.Running.Safety.Watching::0",
        ),
        (
            "Controller.Running.Motion",
            "transition",
            "Controller.Running.Motion.Off::transition::"
            "Controller.Running.Motion.On::0",
        ),
    ]


def test_swapping_the_regions_swaps_the_order_of_their_cases():
    core = core_of(interlock(safety_first=False), 3)
    model = run(core, CYCLES)
    assert [scope for scope, _, _ in listing(core, model, 2)] == [
        "Controller.Running.Motion",
        "Controller.Running.Safety",
    ]


def test_every_copy_of_a_unit_carries_the_same_public_labels():
    text = """
    def int n = 0;
    state Root {
        >> during before { n = n + 1; }
        region A { [*] -> P; state P { during { n = n + 2; } } }
        region B { [*] -> Q; state Q { during { n = n + 3; } } }
    }
    """
    core = core_of(text, 2)
    copies = {}

    def collect(relations):
        for relation in relations:
            base = relation.case.unit_id.split("|")[0]
            copies.setdefault(base, {}).setdefault(relation.case.unit_id, []).append(
                relation.case.public_label
            )
            collect(relation.children)

    for step in core.region_steps:
        collect(step.cases)
    assert any(len(variants) > 1 for variants in copies.values())
    for variants in copies.values():
        assert len({tuple(labels) for labels in variants.values()}) == 1


def test_a_case_that_runs_no_unit_of_the_model_has_no_public_label():
    text = """
    def int n = 0;
    state Root {
        >> during after { n = n + 1; }
        region A { [*] -> P; state P { during { n = n + 2; } } }
        region B { [*] -> Q; state Q { during { n = n + 3; } } }
    }
    """
    core = core_of(text, 2)
    model = run(core, [{}, {}])
    labels = [label for _, _, label in listing(core, model, 1)]
    assert labels
    assert all(label and "flush" not in label for label in labels)
