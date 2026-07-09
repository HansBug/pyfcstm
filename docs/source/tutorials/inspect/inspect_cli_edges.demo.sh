#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".inspect_cli_edges.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

echo "=== Color policy ==="
pyfcstm inspect -i inspect_diagnostics.fcstm --color always > "$workdir/color.txt"
pyfcstm inspect -i inspect_diagnostics.fcstm --color never > "$workdir/no-color.txt"
pyfcstm inspect -i inspect_diagnostics.fcstm --format json --color always > "$workdir/json-color.txt"
COLOR_PATH="$workdir/color.txt" NO_COLOR_PATH="$workdir/no-color.txt" JSON_COLOR_PATH="$workdir/json-color.txt" python - <<'PY'
import os
from pathlib import Path

color_text = Path(os.environ["COLOR_PATH"]).read_text()
no_color_text = Path(os.environ["NO_COLOR_PATH"]).read_text()
json_color_text = Path(os.environ["JSON_COLOR_PATH"]).read_text()
print("color_always_has_ansi:", "\x1b[" in color_text)
print("color_never_has_ansi:", "\x1b[" in no_color_text)
print("json_color_always_has_ansi:", "\x1b[" in json_color_text)
PY

echo ""
echo "=== Output suffix warning ==="
pyfcstm inspect -i inspect_diagnostics.fcstm -o "$workdir/report.json" 2> "$workdir/suffix-human.err"
cat "$workdir/suffix-human.err"
sed -n '1,4p' "$workdir/report.json"

echo ""
echo "=== Explicit JSON can use any suffix ==="
pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o "$workdir/report.md" 2> "$workdir/suffix-json.err"
cat "$workdir/suffix-json.err"
REPORT_PATH="$workdir/report.md" python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ["REPORT_PATH"]).read_text())
print("json_loaded:", report["root_state_path"])
PY
