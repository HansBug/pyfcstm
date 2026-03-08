#!/usr/bin/env python3
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime

dsl_code = """
def int counter = 0;

state System {
    [*] -> Idle;

    state Idle;
    state Active;

    Idle -> Active :: Start;
    Active -> Idle :: Stop;
}
"""

# Parse and create state machine
ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
sm = parse_dsl_node_to_state_machine(ast)

# Create runtime
runtime = SimulationRuntime(sm)

# Initialize
runtime.cycle()
print(f"Initial: state={'.'.join(runtime.current_state.path)}")

# Trigger Start event
runtime.cycle(['Start'])
print(f"After 'Start': state={'.'.join(runtime.current_state.path)}")

# Trigger Stop event
runtime.cycle(['Stop'])
print(f"After 'Stop': state={'.'.join(runtime.current_state.path)}")

# Try Start again
runtime.cycle(['Start'])
print(f"After 'Start' again: state={'.'.join(runtime.current_state.path)}")
