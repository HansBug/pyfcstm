#!/bin/sh
cd "$(dirname "$0")"

# Print the command, run it, and drop the one line that carries wall-clock time.
run() {
    echo "\$ pyfcstm bmc $*"
    out="$(pyfcstm bmc "$@" 2>&1; echo "exit=$?")"
    printf '%s\n' "$out" | grep -v -E ' in [0-9.]+ ms'
}

run -i ../../tutorials/regions/controller.fcstm -q interlock.fbmcq --color never
echo
run -i ../../tutorials/regions/controller_swapped.fcstm -q interlock.fbmcq --color never
