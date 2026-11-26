#!/bin/bash
set -e
cd "$(dirname "$0")"

# For each model print only the findings this page is about.
show() {
    echo "--- $1"
    pyfcstm inspect -i "$1" --format json | python -c '
import json
import sys

report = json.load(sys.stdin)
wanted = ("I_REGION_BACKWARD_READ", "W_REGION_BLIND_OVERWRITE", "W_UNREACHABLE_STATE", "W_UNREACHABLE_TRANSITION")
rows = [d for d in report["diagnostics"] if d["code"] in wanted]
if not rows:
    print("(none of the four codes)")
for d in rows:
    line = "%s %s line %d" % (d["code"], d["severity"], d["span"]["line"])
    if d["code"] == "W_UNREACHABLE_TRANSITION":
        line += " reasons=" + ",".join(d["refs"]["reasons"])
    if d["code"] == "W_UNREACHABLE_STATE":
        line += " " + d["refs"]["state_path"]
    print(line)
    print("  " + d["message"])
'
}

echo "=== I_REGION_BACKWARD_READ: reported ==="
show region_backward_read_variable.fcstm
show region_backward_read_active.fcstm
show region_backward_read_two_writers.fcstm
echo
echo "=== I_REGION_BACKWARD_READ: not reported ==="
show region_backward_read_own_write.fcstm
show region_backward_read_forward.fcstm
show region_backward_read_no_writer.fcstm
echo
echo "=== W_REGION_BLIND_OVERWRITE: reported ==="
show region_overwrite_basic.fcstm
show region_overwrite_aspect.fcstm
show region_overwrite_skip_middle.fcstm
echo
echo "=== W_REGION_BLIND_OVERWRITE: not reported ==="
show region_overwrite_uses_old.fcstm
show region_overwrite_conditional.fcstm
show region_overwrite_some_states.fcstm
show region_overwrite_can_finish.fcstm
show region_overwrite_middle_reads.fcstm
