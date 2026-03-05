#!/usr/bin/env python3
"""Basic Python visualization example."""

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine

# Read the example state machine
with open('example.fcstm', 'r') as f:
    code = f.read()

# Parse DSL code
ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
model = parse_dsl_node_to_state_machine(ast_node)

# Generate PlantUML with default settings
plantuml_output = model.to_plantuml()

# Save to file
with open('output_basic.puml', 'w') as f:
    f.write(plantuml_output)

print("PlantUML diagram generated: output_basic.puml")
print(f"Total states: {len(list(model.walk_states()))}")
print(f"Variables: {', '.join(model.defines.keys())}")
