#!/bin/sh
cd "$(dirname "$0")"

workdir=".witness_regions.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

echo "\$ pyfcstm bmc -i ../../tutorials/regions/controller_swapped.fcstm -q interlock.fbmcq --json -o result.json"
pyfcstm bmc -i ../../tutorials/regions/controller_swapped.fcstm -q interlock.fbmcq --json -o "$workdir/result.json"
echo "exit=$?"
for view in frames cases replay; do
    echo "\$ python show_witness.py result.json $view"
    python show_witness.py "$workdir/result.json" "$view"
done
