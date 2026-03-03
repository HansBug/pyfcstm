#!/bin/bash
cd "$(dirname "$0")"

# Generate PlantUML from simple machine
echo "=== Generating PlantUML from simple_machine.fcstm ==="
pyfcstm plantuml -i simple_machine.fcstm -o simple_machine.puml

echo ""
echo "=== Generated PlantUML content ==="
cat simple_machine.puml
