#!/bin/sh
cd "$(dirname "$0")"

# Print the query, then the command and the headline of its report.
ask() {
    echo "--- $1"
    cat "$1"
    echo "\$ pyfcstm bmc -i joint.fcstm -q $1 --color never | head -n 1"
    pyfcstm bmc -i joint.fcstm -q "$1" --color never | head -n 1
}

ask joint_a_done.fbmcq
ask joint_all_done.fbmcq
ask joint_next.fbmcq
ask joint_blocked_b_done.fbmcq
ask joint_blocked_next.fbmcq
