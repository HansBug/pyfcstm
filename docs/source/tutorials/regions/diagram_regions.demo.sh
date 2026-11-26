#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

pyfcstm diagram -i controller.fcstm | python list_regions.py
