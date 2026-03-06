#!/usr/bin/env python3
"""Python visualization with PlantUMLOptions."""

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.model.plantuml import PlantUMLOptions

# Read the example state machine
with open('example.fcstm', 'r') as f:
    code = f.read()

# Parse DSL code
ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
model = parse_dsl_node_to_state_machine(ast_node)

# Create PlantUMLOptions with custom settings
options = PlantUMLOptions(
    detail_level='full',
    show_events=True,
    max_depth=3,
    show_lifecycle_actions=True
)

# Generate PlantUML with custom options
plantuml_output = model.to_plantuml(options)

# Save to file
with open('output_custom.puml', 'w') as f:
    f.write(plantuml_output)

print("PlantUML diagram with custom options generated: output_custom.puml")
print(f"Detail level: {options.detail_level}")
print(f"Show events: {options.show_events}")
print(f"Max depth: {options.max_depth}")
