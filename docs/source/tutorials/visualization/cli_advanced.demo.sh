#!/bin/bash
# Advanced CLI visualization with multiple options

# Combine detail level with custom options
pyfcstm plantuml -i example.fcstm \
  -l full \
  -c show_events=true \
  -c event_visualization_mode=color \
  -c state_name_format=name,path \
  -c max_action_lines=5 \
  -c use_stereotypes=true \
  -o output_advanced.puml

echo "Generated with advanced configuration: output_advanced.puml"
