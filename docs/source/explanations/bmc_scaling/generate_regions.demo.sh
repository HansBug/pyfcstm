#!/bin/bash
set -e
cd "$(dirname "$0")"
python ../../../../tools/measure_bmc_scaling.py generate regions --R 2 --S 3 --k 2
