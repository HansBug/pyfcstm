#!/usr/bin/env python3
"""Python visualization with different detail levels."""

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.model.plantuml import PlantUMLOptions

# Read the example state machine
with open('example.fcstm', 'r') as f:
    code = f.read()

# Parse DSL code
ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
model = parse_dsl_node_to_state_machine(ast_node)

# Generate with minimal detail level
minimal_options = PlantUMLOptions(detail_level='minimal')
minimal_output = model.to_plantuml(minimal_options)
with open('output_python_minimal.puml', 'w') as f:
    f.write(minimal_output)
print("Minimal detail level: output_python_minimal.puml")

# Generate with normal detail level
normal_options = PlantUMLOptions(detail_level='normal')
normal_output = model.to_plantuml(normal_options)
with open('output_python_normal.puml', 'w') as f:
    f.write(normal_output)
print("Normal detail level: output_python_normal.puml")

# Generate with full detail level
full_options = PlantUMLOptions(detail_level='full')
full_output = model.to_plantuml(full_options)
with open('output_python_full.puml', 'w') as f:
    f.write(full_output)
print("Full detail level: output_python_full.puml")
