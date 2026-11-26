"""Print the deterministic parts of one pyfcstm bmc JSON result."""
import json
import sys

payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
result = payload["result"]
print(f"{result['kind']} status={result['status']} outcome={result['outcome']} exit={payload['exit_code']}")
witness = payload["witness"]
if witness is not None and witness["frames"]:
    for frame in witness["frames"]:
        print(f"  frame {frame['index']}: {frame['configuration']}")
    for step in witness["steps"]:
        print(f"  step {step['index']}: case_label={step['case_label']}")
        for case in step["local_cases"]:
            print(f"    local {case['scope']} [{case['kind']}] {case['label']}")
