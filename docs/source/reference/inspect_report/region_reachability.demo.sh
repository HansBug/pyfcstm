#!/bin/bash
set -e
cd "$(dirname "$0")"

show() {
    echo "--- $1"
    pyfcstm inspect -i "$1" --format json | python -c '
import json
import sys

report = json.load(sys.stdin)
wanted = ("W_UNREACHABLE_STATE", "W_UNREACHABLE_TRANSITION")
rows = [d for d in report["diagnostics"] if d["code"] in wanted]
if not rows:
    print("(no unreachable state or transition)")
for d in rows:
    line = "%s line %d" % (d["code"], d["span"]["line"])
    if d["code"] == "W_UNREACHABLE_TRANSITION":
        line += " reasons=" + ",".join(d["refs"]["reasons"])
    else:
        line += " " + d["refs"]["state_path"]
    print(line)
'
}

echo "=== owner of regions ==="
show region_owner_never_completes.fcstm
show region_owner_completes.fcstm
echo
echo "=== plain composite state, no regions ==="
show region_branch_plain_stuck.fcstm
show region_branch_plain_exits.fcstm
echo
echo "=== forced transition and history default ==="
show region_branch_forced.fcstm
show region_branch_history.fcstm
echo
echo "=== known over-approximation ==="
show region_over_history_initial.fcstm
