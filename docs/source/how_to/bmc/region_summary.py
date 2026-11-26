"""Print the deterministic parts of one pyfcstm bmc JSON result.

Usage: python region_summary.py RESULT.json [LAST_FRAME]

Frames after the first frame where the property already holds are free choices
of the solver, so pass LAST_FRAME to print only the frames that the property
itself forces.
"""
import json
import sys

payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
last_frame = int(sys.argv[2]) if len(sys.argv) > 2 else None
result = payload["result"]
print(f"{result['kind']} status={result['status']} outcome={result['outcome']} exit={payload['exit_code']}")
witness = payload["witness"]
if witness is not None and witness["frames"]:
    for frame in witness["frames"]:
        if last_frame is None or frame["index"] <= last_frame:
            print(f"  frame {frame['index']}: {frame['configuration']}")
    for step in witness["steps"]:
        if last_frame is not None and step["index"] >= last_frame:
            continue
        print(f"  step {step['index']}: case_label={step['case_label']}")
        for case in step["local_cases"]:
            print(f"    local {case['scope']} [{case['kind']}] {case['label']}")
