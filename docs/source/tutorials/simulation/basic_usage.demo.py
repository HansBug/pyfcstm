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
print(f"Initial: state={'.'.join(runtime.current_state.path)}, counter={runtime.vars['counter']}")

for i in range(1, 8):
    runtime.cycle()
    print(f"Cycle {i}: state={'.'.join(runtime.current_state.path)}, counter={runtime.vars['counter']}")
