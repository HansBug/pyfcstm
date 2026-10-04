"""Runtime edge addresses agree with the public BMC macro-step expansion."""

import pytest

from pyfcstm.bmc import (
    build_bmc_domain,
    entry_source,
    expand_macro_step_cases,
    init_source,
    stable_leaf_source,
)
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime


pytestmark = pytest.mark.unittest


@pytest.mark.parametrize("start", [None, "Root", "Root.P", "Root.A"])
def test_trace_transition_labels_match_bmc_effect_blocks(start):
    model = load_state_machine_from_text("""
        def int x = 0;
        state Root {
            pseudo state P;
            state A;
            state Bad {
                state Dead;
                [*] -> Dead : if [false];
            }
            state Done;
            [*] -> P effect { x = x + 1; };
            P -> Bad effect { x = 100; };
            P -> A effect { x = x + 2; };
            A -> Done effect { x = x + 4; };
        }
    """)
    domain = build_bmc_domain(model, bound=1)
    if start is None:
        source = init_source(domain)
    elif start == "Root.A":
        source = stable_leaf_source(domain, start)
    else:
        source = entry_source(domain, start)
    formal = expand_macro_step_cases(source)
    target = "Root.Done" if start == "Root.A" else "Root.A"
    cases = [case for case in formal.success_cases if case.target_state_path == target]
    assert len(cases) == 1
    expected = [
        block.transition_label
        for block in cases[0].action_blocks
        if block.block_kind == "transition_effect"
    ]
    assert expected
    runtime = SimulationRuntime(model, initial_state=start, initial_vars={"x": 0})
    result = runtime.cycle(trace=True)
    assert [
        entry.transition_label for entry in result.trace if entry.kind == "transition"
    ] == expected
    assert ".".join(runtime.current_state.path) == target
