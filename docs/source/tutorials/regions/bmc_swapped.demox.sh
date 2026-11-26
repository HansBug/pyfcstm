#!/bin/sh
set -u
cd "$(dirname "$0")"

out=.bmc_swapped.out
trap 'rm -f "$out"' EXIT

status=0
pyfcstm bmc -i controller_swapped.fcstm -q fault_beat_motor_off.fbmcq --color never > "$out" || status=$?
grep -v '^Solver:' "$out"
exit "$status"
