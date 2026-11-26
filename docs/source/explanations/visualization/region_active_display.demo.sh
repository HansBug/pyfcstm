#!/bin/bash
set -e
cd "$(dirname "$0")"

model=../diagnostics/region_written_vs_running.fcstm

echo '$ pyfcstm plantuml -i region_written_vs_running.fcstm   (guards and legend)'
pyfcstm plantuml -i "$model" | grep -E 'active|^\| '
echo
echo '$ pyfcstm diagram -i region_written_vs_running.fcstm   (variables and guards)'
pyfcstm diagram -i "$model" | python3 -c "
import json, sys

def guards(node):
    for transition in node['transitions']:
        if transition['guardLabel']:
            print('  guard: ' + transition['guardLabel'])
    for child in node['children']:
        guards(child)

diagram = json.load(sys.stdin)
print('  variables: ' + ', '.join(v['name'] for v in diagram['variables']))
guards(diagram['rootState'])"
