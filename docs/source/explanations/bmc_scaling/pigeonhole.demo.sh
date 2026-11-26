#!/bin/bash
set -e
cd "$(dirname "$0")"
python ../../../../tools/measure_bmc_scaling.py generate pigeonhole --holes 2 --pigeons 3
