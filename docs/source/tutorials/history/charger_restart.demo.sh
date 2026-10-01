#!/bin/sh
set -eu
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

# Run one batch script and show the final ``current`` report.
run() {
    pyfcstm simulate -i charger_restart.fcstm -e "$1" --no-color > "$workdir/out.txt"
    sed 's/[[:space:]]*$//' "$workdir/out.txt" | tail -n 8
}

# Plug in, authorize, finish precharge and reach ConstantVoltage.
steps="cycle; cycle Charger.Idle.PlugIn; cycle Charger.Session.Authenticating.Authorized"
steps="$steps; cycle Charger.Session.Charging.Precharge.Ready"
steps="$steps; cycle Charger.Session.Charging.ConstantCurrent.NearFull"

echo "=== Charging in ConstantVoltage ==="
run "$steps; current"

echo ""
echo "=== Overheat, then the fault clears ==="
run "$steps; cycle Charger.Session.OverTemp; cycle Charger.Fault.Cleared; current"
