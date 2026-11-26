#!/bin/sh
set -eu
cd "$(dirname "$0")"

out=.bmc_interlock.out
trap 'rm -f "$out"' EXIT

pyfcstm bmc -i controller.fcstm -q fault_beat_motor_off.fbmcq --color never > "$out"
grep -v '^Solver:' "$out"
