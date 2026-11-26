#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

pyfcstm bmc -i controller_swapped.fcstm -q fault_beat_motor_off.fbmcq --color never | grep -v '^Solver:'
