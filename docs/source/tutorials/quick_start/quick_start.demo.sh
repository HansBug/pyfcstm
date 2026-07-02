#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

echo "=== Simulate two cycles ==="
pyfcstm simulate -i traffic_light.fcstm -e "cycle; cycle; current"

echo ""
echo "=== Inspect model summary ==="
pyfcstm inspect -i traffic_light.fcstm -o "$workdir/traffic_light.inspect.json"
INSPECT_JSON="$workdir/traffic_light.inspect.json" python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ['INSPECT_JSON']).read_text())
metrics = report['metrics']
state_count = metrics['n_states_composite'] + metrics['n_states_leaf'] + metrics['n_states_pseudo']
transition_count = metrics['n_transitions_normal'] + metrics['n_transitions_forced']
print('states:', state_count)
print('transitions:', transition_count)
print('diagnostics:', len(report['diagnostics']))
PY

echo ""
echo "=== Generate Python built-in template ==="
pyfcstm generate -i traffic_light.fcstm --template python -o "$workdir/_quick_start_python" --clear
for path in "$workdir/_quick_start_python"/*; do
    echo "_quick_start_python/$(basename "$path")"
done | sort

echo ""
echo "=== Generate PlantUML source ==="
pyfcstm plantuml -i traffic_light.fcstm -o "$workdir/traffic_light.puml"
sed -n '1,12p' "$workdir/traffic_light.puml"
