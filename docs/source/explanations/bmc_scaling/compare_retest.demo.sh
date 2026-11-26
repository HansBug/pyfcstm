#!/bin/bash
set -e
cd "$(dirname "$0")"
python ../../../../tools/measure_bmc_scaling.py compare-retest --data data
