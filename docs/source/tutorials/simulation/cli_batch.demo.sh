#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

pyfcstm simulate -i ../cli/simple_machine.fcstm \
  -e "cycle; events; cycle Start; current; cycle Stop; history 3" \
  --no-color \
  | sed 's/[[:space:]]*$//'
