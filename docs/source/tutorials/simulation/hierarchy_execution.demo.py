#!/usr/bin/env python3
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime

dsl_code = """
def int counter = 0;

state System {
    >> during before {
        counter = counter + 1;
    }

    [*] -> Parent;

    state Parent {
        during before {
            counter = counter + 100;
        }

        state Child {
            during {
                counter = counter + 10;
            }
        }

        [*] -> Child;
    }
}
"""

# Parse and create state machine
ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
sm = parse_dsl_node_to_state_machine(ast)

# Create runtime
runtime = SimulationRuntime(sm)

# Execute first cycle (initialization)
runtime.cycle()
print(f"After initialization:")
print(f"  State: {runtime.current_state}")
print(f"  Counter: {runtime.vars['counter']}")
print(f"  Explanation: during before (100) executed during entry")

# Execute second cycle (during phase)
runtime.cycle()
print(f"\nAfter cycle 2:")
print(f"  State: {runtime.current_state}")
print(f"  Counter: {runtime.vars['counter']}")
print(f"  Explanation: >> during before (1) + Child.during (10)")

# Execute third cycle
runtime.cycle()
print(f"\nAfter cycle 3:")
print(f"  State: {runtime.current_state}")
print(f"  Counter: {runtime.vars['counter']}")
print(f"  Explanation: >> during before (1) + Child.during (10)")
