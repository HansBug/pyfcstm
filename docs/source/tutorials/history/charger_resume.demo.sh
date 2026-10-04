#!/bin/sh
set -eu
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

# Run one batch script and show the final ``current`` report.
run() {
    pyfcstm simulate -i charger.fcstm -e "$1" --no-color > "$workdir/out.txt"
    sed 's/[[:space:]]*$//' "$workdir/out.txt" | tail -n 10
}

# The same session as charger_restart.demo.sh, interrupted in ConstantVoltage.
steps="cycle; cycle Charger.Idle.PlugIn; cycle Charger.Session.Authenticating.Authorized"
steps="$steps; cycle Charger.Session.Charging.Precharge.Ready"
steps="$steps; cycle Charger.Session.Charging.ConstantCurrent.NearFull"
steps="$steps; cycle Charger.Session.OverTemp"

echo "=== The fault clears: resume through deep history ==="
run "$steps; cycle Charger.Fault.Cleared; current"

echo ""
echo "=== An operator resets: resume through shallow history ==="
run "$steps; cycle Charger.Fault.ManualReset; current"
