#!/bin/sh
set -eu
cd "$(dirname "$0")"

trap 'rm -rf runtime_out' EXIT
pyfcstm generate -i controller.fcstm --template python -o runtime_out
ls runtime_out | LC_ALL=C sort
PYTHONPATH=runtime_out python run_scenario.py
