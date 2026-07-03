#!/bin/bash
set -e

workdir=".inspect_invalid.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT
cat > "$workdir/bad.fcstm" <<'FCSTM'
state Broken {
    state A;
    [*] -> MissingTarget;
FCSTM

set +e
pyfcstm inspect -i "$workdir/bad.fcstm" --format json > "$workdir/stdout.txt" 2> "$workdir/stderr.txt"
status=$?
set -e

echo "exit_code: $status"
echo "stdout_bytes: $(wc -c < "$workdir/stdout.txt")"
echo "stderr_excerpt:"
sed -n '1,3p' "$workdir/stderr.txt"
