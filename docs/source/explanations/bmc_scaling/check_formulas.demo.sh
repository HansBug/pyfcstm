#!/bin/bash
set -e
cd "$(dirname "$0")"
python ../../../../tools/measure_bmc_scaling.py check-formulas --data data
