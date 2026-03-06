#!/bin/bash
# CLI visualization with detail level

# Generate with minimal detail level
pyfcstm plantuml -i example.fcstm -l minimal -o output_minimal.puml
echo "Minimal detail level: output_minimal.puml"

# Generate with normal detail level (default)
pyfcstm plantuml -i example.fcstm -l normal -o output_normal.puml
echo "Normal detail level: output_normal.puml"

# Generate with full detail level
pyfcstm plantuml -i example.fcstm -l full -o output_full.puml
echo "Full detail level: output_full.puml"
