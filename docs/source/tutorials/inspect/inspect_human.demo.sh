#!/bin/bash
set -e
cd "$(dirname "$0")"

pyfcstm inspect -i inspect_diagnostics.fcstm --color never | sed -n '1,42p'
