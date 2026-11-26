#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

pyfcstm simulate -i controller.fcstm --no-color -e "\
cycle --input fault=0 --input requested=0; \
cycle /Start --input fault=0 --input requested=0; \
cycle --input fault=0 --input requested=1; \
cycle --input fault=1 --input requested=1; \
cycle --input fault=0 --input requested=1; \
cycle /Stop --input fault=0 --input requested=1" \
  | sed 's/[[:space:]]*$//'
