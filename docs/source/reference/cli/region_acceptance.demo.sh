#!/bin/sh
set -eu
here=$(pwd)
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT
cp "$here/../../tutorials/regions/controller.fcstm" "$here/../../tutorials/regions/controller_swapped.fcstm" "$workdir/"
cp "$here"/motor_reach.fbmcq "$here"/motor_needs_permit.fbmcq "$workdir/"
cp -r "$here/listed_template" "$workdir/"
cd "$workdir"

echo '$ pyfcstm simulate -i controller.fcstm -e "cycle; cycle /Start ..."'
pyfcstm simulate -i controller.fcstm --no-color -e "cycle --input fault=0 --input requested=1; cycle /Start --input fault=0 --input requested=1; cycle --input fault=0 --input requested=1; cycle --input fault=1 --input requested=1; current" | grep -E '^(>>>|Current State)' | sed 's/[[:space:]]*$//'
echo

echo '$ pyfcstm inspect -i controller.fcstm --color never   (Summary block)'
pyfcstm inspect -i controller.fcstm --color never | sed -n '3,15p' | sed 's/[[:space:]]*$//'
echo

echo '$ pyfcstm inspect -i controller.fcstm --format json   (the regions list)'
pyfcstm inspect -i controller.fcstm --format json | python3 -c "
import json, sys
for region in json.load(sys.stdin)['regions']:
    print(region['index'], region['path'], 'owner=%s' % region['owner_path'], region['substates'])
"
echo

echo '$ pyfcstm inspect -i controller_swapped.fcstm --color never   (the order diagnostic)'
pyfcstm inspect -i controller_swapped.fcstm --color never | grep -A1 '^\[INFO\] I_REGION' | sed 's/[[:space:]]*$//'
echo

echo '$ pyfcstm bmc -i controller.fcstm -q motor_reach.fbmcq   (verdict lines)'
pyfcstm bmc -i controller.fcstm -q motor_reach.fbmcq | grep -E '^(BMC|Property verdict|  Replay)'
echo
echo '$ pyfcstm bmc -i controller.fcstm -q motor_needs_permit.fbmcq   (verdict lines)'
pyfcstm bmc -i controller.fcstm -q motor_needs_permit.fbmcq | grep -E '^(BMC|Property verdict)'
echo

echo '$ pyfcstm generate -i controller.fcstm --template python -o out'
pyfcstm generate -i controller.fcstm --template python -o out
LC_ALL=C ls out
echo

echo '$ pyfcstm generate -i controller.fcstm -t listed_template -o listed_out'
pyfcstm generate -i controller.fcstm -t listed_template -o listed_out
cat listed_out/summary.txt
echo
echo

echo '$ pyfcstm plantuml -i controller.fcstm   (the Running block)'
pyfcstm plantuml -i controller.fcstm | sed -n '21,38p'
echo

echo '$ pyfcstm diagram -i controller.fcstm   (regions of Running, from the JSON)'
pyfcstm diagram -i controller.fcstm | python3 -c "
import json, sys
running = json.load(sys.stdin)['rootState']['children'][1]
for child in running['children']:
    print(child['qualifiedName'], 'region=%s' % child['region'], 'ordinal=%s' % child['ordinal'])
"
