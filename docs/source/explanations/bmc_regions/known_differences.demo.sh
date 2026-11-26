#!/bin/sh
cd "$(dirname "$0")"

# Keep the headline, the runtime-error lines and the exit status of a report.
check() {
    echo "\$ pyfcstm bmc -i $1 -q $2 --color never${3:+ $3}"
    out="$(pyfcstm bmc -i "$1" -q "$2" --color never $3 2>&1; echo "exit=$?")"
    printf '%s\n' "$out" | grep -E '^(BMC |  Runtime error|  Replay|Unexpected error|SimulationRuntimeExpressionError|exit=)'
}

check dead_end.fcstm dead_end.fbmcq
echo
check outranked.fcstm outranked.fbmcq
echo
check dead_end.fcstm dead_end.fbmcq --no-runtime-safety
