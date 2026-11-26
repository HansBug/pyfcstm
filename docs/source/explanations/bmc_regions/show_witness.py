"""Print one view of the witness in a ``pyfcstm bmc --json`` result file."""

import json
import sys

path, view = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as stream:
    result = json.load(stream)

witness = result["witness"]
if view == "frames":
    for frame in witness["frames"]:
        print("frame %d: %s" % (frame["index"], frame.get("configuration") or frame["sentinel"]))
elif view == "cases":
    for step in witness["steps"]:
        print("step %d: case_label=%s" % (step["index"], step["case_label"]))
        for case in step["local_cases"]:
            print("    scope=%s kind=%s label=%s" % (case["scope"], case["kind"], case["label"]))
elif view == "calls":
    for step in witness["steps"]:
        print("step %d: %s" % (step["index"], " ".join(call["action_name"] for call in step["abstract_calls"])))
elif view == "replay":
    print("replay ok=%s mismatches=%d" % (result["replay"]["ok"], len(result["replay"]["mismatches"])))
