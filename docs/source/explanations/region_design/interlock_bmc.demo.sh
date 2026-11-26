#!/bin/sh
set -eu
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

# The same property against both orders; the exit status follows the verdict.
for model in controller controller_swapped; do
    status=0
    pyfcstm bmc -i "$model.fcstm" -q interlock.fbmcq --json -o "$workdir/$model.json" || status=$?
    MODEL="$model" RESULT="$workdir/$model.json" STATUS="$status" python - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["RESULT"]).read_text(encoding="utf-8"))
print(
    "%-20s status=%s outcome=%s exit=%s"
    % (os.environ["MODEL"], payload["result"]["status"], payload["result"]["outcome"], os.environ["STATUS"])
)
PY
done
