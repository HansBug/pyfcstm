#!/bin/sh
set -eu
pyfcstm simulate -i region_single.fcstm -e "cycle" --no-color | sed 's/[[:space:]]*$//'
