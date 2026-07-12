#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".bmc_tasks.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

run_json() {
    name="$1"
    expected_exit="$2"
    set +e
    pyfcstm bmc -i bmc_tasks.fcstm -q "$name.fbmcq" --json \
        -o "$workdir/$name.json"
    actual_exit="$?"
    set -e
    if [ "$actual_exit" -ne "$expected_exit" ]; then
        echo "$name: expected exit $expected_exit, got $actual_exit" >&2
        exit 1
    fi
    RESULT_JSON="$workdir/$name.json" python - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["RESULT_JSON"]).read_text(encoding="utf-8"))
print(
    payload["property"]["kind"],
    payload["result"]["status"],
    payload["result"]["outcome"],
    "exit=%d" % payload["exit_code"],
)
PY
}

run_json reach 0
run_json forbid 1
run_json invariant 0
run_json must_reach 0
run_json exists_always 0
run_json response 0
run_json cover 0
run_json init_havoc_where 0
run_json assumptions 0
run_json calls 0
run_json response_incomplete 3

set +e
error_output="$(pyfcstm bmc -i bmc_tasks.fcstm -q invalid_state.fbmcq 2>&1)"
error_exit="$?"
set -e
if [ "$error_exit" -ne 1 ]; then
    echo "invalid_state: expected exit 1, got $error_exit" >&2
    exit 1
fi
case "$error_output" in
    *"Failed to compile BMC query"*"Root.Missing"*)
        echo "invalid_state controlled_error exit=1"
        ;;
    *)
        echo "$error_output" >&2
        exit 1
        ;;
esac
