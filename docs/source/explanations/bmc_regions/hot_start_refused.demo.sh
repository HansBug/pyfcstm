#!/bin/sh
cd "$(dirname "$0")"

echo "--- start_all_done.fbmcq"
cat start_all_done.fbmcq
echo "\$ pyfcstm bmc -i joint.fcstm -q start_all_done.fbmcq"
out="$(pyfcstm bmc -i joint.fcstm -q start_all_done.fbmcq 2>&1; echo "exit=$?")"
printf '%s\n' "$out"
