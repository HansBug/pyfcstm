#!/bin/sh
set -eu
here=$(pwd)
model="$here/../../tutorials/regions/controller.fcstm"
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"

# Print the batch transcript without the decorative rules and trailing blanks.
run() {
    pyfcstm simulate -i "$model" -e "$1" --no-color | grep -v '^─' | sed 's/[[:space:]]*$//'
}

echo "=== hot start from a configuration text, then events, cycle and history ==="
run "init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; events; cycle --input fault=1 --input requested=1; history"

echo ""
echo "=== hot start from a dotted path: the other region waits for initialization ==="
run "init Controller.Running.Motion.On permit=1 motor=1 __forced_0=0; cycle --input fault=0 --input requested=1"

echo ""
echo "=== export writes the position as configuration text ==="
pyfcstm simulate -i "$model" --no-color -e "cycle --input fault=0 --input requested=1; cycle /Start --input fault=0 --input requested=1; export history.json" > /dev/null
cat history.json
