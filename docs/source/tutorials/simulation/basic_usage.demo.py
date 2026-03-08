#!/usr/bin/env python3
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime

dsl_code = """
def int counter = 0;

state System {
    [*] -> Idle;

    state Idle {
        during {
            counter = counter + 1;
        }
    }

    state Active {
        during {
            counter = counter + 10;
        }
    }

    Idle -> Active : if [counter >= 5];
    Active -> Idle : if [counter >= 50];
}
"""

# Parse and create state machine
ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
sm = parse_dsl_node_to_state_machine(ast)

# Create runtime
runtime = SimulationRuntime(sm)

# Execute cycles
print("Initial state:", runtime.current_state)
print("Initial counter:", runtime.vars['counter'])

runtime.cycle()
print("\nAfter cycle 1:")
print("State:", runtime.current_state)
print("Counter:", runtime.vars['counter'])

for i in range(2, 8):
    runtime.cycle()
    print(f"\nAfter cycle {i}:")
    print("State:", runtime.current_state)
    print("Counter:", runtime.vars['counter'])
