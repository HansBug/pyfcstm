#!/bin/sh
cd "$(dirname "$0")"

# Print the query, then the command and the headline of its report.
ask() {
    model="$1"
    query="$2"
    echo "--- $query"
    cat "$query"
    echo "\$ pyfcstm bmc -i $model -q $query --color never | head -n 1"
    pyfcstm bmc -i "$model" -q "$query" --color never | head -n 1
}

ask blocked.fcstm blocked_free.fbmcq
ask blocked.fcstm blocked_stuck.fbmcq
echo "--- blocked_zero.fbmcq"
cat blocked_zero.fbmcq
echo "\$ pyfcstm bmc -i blocked.fcstm -q blocked_zero.fbmcq --color never | sed -n '/^Trace/,/^\$/p'"
pyfcstm bmc -i blocked.fcstm -q blocked_zero.fbmcq --color never | sed -n '/^Trace/,/^$/p'
