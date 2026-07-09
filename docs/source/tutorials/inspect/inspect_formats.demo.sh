#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".inspect_formats.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o "$workdir/report.json"
pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-json -o "$workdir/report.llm.json"
pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-md -o "$workdir/report.llm.md"

echo "=== JSON summary ==="
INSPECT_JSON="$workdir/report.json" python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ["INSPECT_JSON"]).read_text())
print("root:", report["root_state_path"])
print("states:", len(report["states"]))
print("transitions:", len(report["transitions"]))
print("combo_transitions:", len(report["combo_transitions"]))
print("combo_origins:", len(report["combo_origins"]))
codes = [item["code"] for item in report["diagnostics"]]
interesting_codes = [
    "W_DURING_CONST_ASSIGN",
    "W_COMBO_DUPLICATE_EVENT",
    "W_COMBO_GUARD_PREFIX_IMPLIED",
    "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
]
print("diagnostic_count:", len(codes))
print("diagnostic_codes_sample:", ", ".join(code for code in interesting_codes if code in codes))
print("first_diagnostic_keys:", ", ".join(sorted(report["diagnostics"][0].keys())))
for item in report["diagnostics"]:
    if item["code"] == "W_DEADLOCK_LEAF":
        print("suggested_fix_key:", "suggested_fix" in item["refs"])
        break
for item in report["diagnostics"]:
    if item["code"].startswith("W_NUMERIC_"):
        print("numeric_target_templates:", ", ".join(item["refs"]["target_templates"]))
        print("numeric_runtime_note:", item["refs"]["runtime_note"])
        break
PY

echo ""
echo "=== LLM JSON shape ==="
LLM_JSON="$workdir/report.llm.json" python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ["LLM_JSON"]).read_text())
first = report["diagnostics"][0]
print("top_level_keys:", ", ".join(sorted(report.keys())))
print("first_diagnostic_keys:", ", ".join(sorted(first.keys())))
print("recommended_actions:", len(first["recommended_actions"]))
print("do_not:", len(first["do_not"]))
print("repair_guidance:", len(first["repair_guidance"]))
PY

echo ""
echo "=== LLM Markdown excerpt ==="
sed -n '1,12p' "$workdir/report.llm.md"
