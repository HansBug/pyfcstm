#!/bin/sh
set -eu
cd "$(dirname "$0")"

# Hot start in the middle of a run: the text in braces is the configuration.
pyfcstm simulate -i controller.fcstm --no-color -e "init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; cycle --input fault=1 --input requested=1"
