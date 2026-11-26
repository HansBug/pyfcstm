#!/bin/sh
cd "$(dirname "$0")"

echo "--- start_motion_on.fbmcq"
cat start_motion_on.fbmcq
echo "\$ pyfcstm bmc -i ../../tutorials/regions/controller.fcstm -q start_motion_on.fbmcq --color never | sed -n '/^Trace/,/^\$/p'"
pyfcstm bmc -i ../../tutorials/regions/controller.fcstm -q start_motion_on.fbmcq --color never | sed -n '/^Trace/,/^$/p'
