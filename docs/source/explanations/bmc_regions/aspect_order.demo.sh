#!/bin/sh
cd "$(dirname "$0")"

workdir=".aspect_order.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

# Solve a query, then list the abstract actions of every step in call order.
calls() {
    echo "\$ pyfcstm bmc -i $1 -q $2 --json -o result.json"
    pyfcstm bmc -i "$1" -q "$2" --json -o "$workdir/result.json"
    echo "exit=$?"
    echo "\$ python show_witness.py result.json calls"
    python show_witness.py "$workdir/result.json" calls
}

calls aspects.fcstm aspects.fbmcq
echo
calls plain_before.fcstm plain_before.fbmcq
