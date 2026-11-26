#!/bin/bash
set -e
cd "$(dirname "$0")"

summary='
import json, sys
for d in json.load(sys.stdin)["diagnostics"]:
    if d["code"] in ("I_REGION_BACKWARD_READ", "W_DEAD_GUARD"):
        line = d["span"]["line"]
        print("  line %d  %s" % (line, d["code"]))
        refs = d["refs"]
        if d["code"] == "I_REGION_BACKWARD_READ":
            print("    target = %s (%s)" % (refs["target"], refs["target_kind"]))
        else:
            print("    guard  = %s" % refs["transition"]["guard"])'

echo '$ pyfcstm inspect -i region_written_vs_running.fcstm'
pyfcstm inspect -i region_written_vs_running.fcstm --format json | python3 -c "$summary"
echo '$ pyfcstm inspect -i region_written_vs_running.fcstm --enable-verify --max-complexity-tier smt_linear'
pyfcstm inspect -i region_written_vs_running.fcstm --enable-verify --max-complexity-tier smt_linear --format json | python3 -c "$summary"
