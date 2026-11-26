#!/bin/sh
set -eu
cd "$(dirname "$0")"

pyfcstm diagram -i controller.fcstm | python list_regions.py
