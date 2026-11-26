#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== human report (first 13 lines) ==="
pyfcstm inspect -i region_overwrite_basic.fcstm --format human --color never | head -13

echo
echo "=== regions array of the JSON report ==="
pyfcstm inspect -i region_overwrite_basic.fcstm --format json | python -c '
import json
import sys

report = json.load(sys.stdin)
print(json.dumps(report["regions"], indent=2, sort_keys=True))
print("state Root.First.A parent_path:", [s["parent_path"] for s in report["states"] if s["path"] == "Root.First.A"][0])
print("Root is_composite:", [s["is_composite"] for s in report["states"] if s["path"] == "Root"][0])
print("Root substates:", [s["substates"] for s in report["states"] if s["path"] == "Root"][0])
'

echo
echo "=== model without regions has no regions key ==="
pyfcstm inspect -i region_branch_plain_exits.fcstm --format json | python -c '
import json
import sys

print("regions" in json.load(sys.stdin))
'

echo
echo "=== diagnostic JSON of the blind overwrite ==="
pyfcstm inspect -i region_overwrite_basic.fcstm --format json | python -c '
import json
import sys

report = json.load(sys.stdin)
item = [d for d in report["diagnostics"] if d["code"] == "W_REGION_BLIND_OVERWRITE"][0]
print(json.dumps(item, indent=2, sort_keys=True))
'
