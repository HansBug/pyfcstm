#!/bin/sh
set -eu
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

# Run one batch script and show the final ``current`` report.
run() {
    pyfcstm simulate -i history_washer.fcstm -e "$1" --no-color > "$workdir/out.txt"
    sed 's/[[:space:]]*$//' "$workdir/out.txt" | tail -n 12
}

steps="cycle; cycle Washer.Paused.Fresh; cycle Washer.Program.Idle.Start"
steps="$steps; cycle Washer.Program.Wash.Fill.Filled; cycle Washer.Program.Pause"

echo "=== Pause in Agitate, then resume through deep history ==="
run "$steps; cycle Washer.Paused.Deep; current"

echo ""
echo "=== Pause in Agitate, then resume through shallow history ==="
run "$steps; cycle Washer.Paused.Shallow; current"
