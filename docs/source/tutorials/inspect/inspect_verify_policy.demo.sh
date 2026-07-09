#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".inspect_verify_policy.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

run_forbidden() {
    label="$1"
    shift
    set +e
    pyfcstm inspect -i inspect_diagnostics.fcstm --format json "$@" > "$workdir/$label.out" 2> "$workdir/$label.err"
    status=$?
    set -e
    echo "=== $label ==="
    echo "exit_code: $status"
    sed -n '1,2p' "$workdir/$label.err"
}

run_forbidden bmc_search --enable-verify --max-complexity-tier bmc_search
run_forbidden k_unrollings --enable-verify --max-call-count-scaling k_unrollings
run_forbidden k_unrollings_times_branching --enable-verify --max-call-count-scaling k_unrollings_times_branching
