#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_never_completes.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

reasons='
import json, sys
report = json.load(sys.stdin)
for d in report["diagnostics"]:
    if d["code"] in ("W_UNREACHABLE_STATE", "W_UNREACHABLE_TRANSITION"):
        print("  %s: %s" % (d["code"], d["message"]))'

echo '$ pyfcstm inspect -i region_never_completes.fcstm'
pyfcstm inspect -i region_never_completes.fcstm --format json | python3 -c "$reasons"
echo '$ pyfcstm simulate: fault=1 for three cycles'
pyfcstm simulate -i region_never_completes.fcstm -e "cycle --input fault=0; cycle --input fault=1; cycle --input fault=1; cycle --input fault=1" | grep -E "^(Cycle|Current State)"

echo
echo '--- the same machine, Motion can also finish'
sed 's/^            state Spin {$/            Spin -> [*] : if [fault != 0];\n            state Spin {/' region_never_completes.fcstm > "$workdir/finishes.fcstm"
grep -n 'Spin -> \[\*\]' "$workdir/finishes.fcstm"
pyfcstm inspect -i "$workdir/finishes.fcstm" --format json | python3 -c "$reasons"
echo '(no output above means both are reachable)'
pyfcstm simulate -i "$workdir/finishes.fcstm" -e "cycle --input fault=0; cycle --input fault=1; cycle --input fault=1" | grep -E "^(Cycle|Current State)"

echo
echo '--- a composite state without regions, whose only child cannot leave'
cat > "$workdir/plain.fcstm" <<'FCSTM'
input int fault;

state Line {
    [*] -> Work;
    state Work {
        [*] -> Spin;
        state Spin;
    }
    state Stopped;
    Work -> Stopped : if [fault != 0];
}
FCSTM
pyfcstm inspect -i "$workdir/plain.fcstm" --format json | python3 -c "$reasons"
