#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/pyfcstm-first-bmc.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT

pyfcstm bmc -i first_check.fcstm -q reach_door.fbmcq
pyfcstm bmc -i first_check.fcstm -q reach_door.fbmcq --json \
    -o "$workdir/first_check.result.json"

RESULT_JSON="$workdir/first_check.result.json" python - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["RESULT_JSON"]).read_text(encoding="utf-8"))
print("schema:", payload["schema_version"])
print("outcome:", payload["result"]["outcome"])
print("replay_ok:", payload["replay"]["ok"])
print("exit_code:", payload["exit_code"])
PY
