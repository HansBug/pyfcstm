#!/bin/sh
set -eu
cd "$(dirname "$0")"

# Start the controller, let the motor run for one cycle, then show the last report.
pyfcstm simulate -i controller.fcstm --no-color -e "cycle --input fault=0 --input requested=1; cycle /Start --input fault=0 --input requested=1; cycle --input fault=0 --input requested=1" | tail -n 9
