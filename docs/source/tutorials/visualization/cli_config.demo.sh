#!/bin/bash
# CLI visualization with configuration options

# Show events and set max depth
pyfcstm plantuml -i example.fcstm \
  -c show_events=true \
  -c max_depth=3 \
  -o output_with_events.puml

echo "Generated with events visible: output_with_events.puml"

# Customize lifecycle actions display
pyfcstm plantuml -i example.fcstm \
  -c show_enter_actions=true \
  -c show_during_actions=true \
  -c show_exit_actions=false \
  -o output_lifecycle.puml

echo "Generated with custom lifecycle actions: output_lifecycle.puml"
