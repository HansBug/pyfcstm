set -e
trap 'rm -rf .region_tmp' EXIT
mkdir -p .region_tmp

for bound in 1 2 3; do
    printf 'init state("Controller.Idle") havoc { permit, motor };\ncheck reach <= %s: active("Controller.Running{Motion: On}");\n' \
        "$bound" > ".region_tmp/ladder_$bound.fbmcq"
    set +e
    pyfcstm bmc -i region_controller.fcstm -q ".region_tmp/ladder_$bound.fbmcq" \
        --json -o ".region_tmp/ladder_$bound.json"
    code="$?"
    set -e
    BOUND="$bound" CODE="$code" python - <<'PY'
import json
import os

payload = json.load(open(f".region_tmp/ladder_{os.environ['BOUND']}.json", encoding="utf-8"))
status = payload["result"]["status"]
decisive = {"sat": "decisive", "unsat": "decisive", "unknown": "inconclusive", "timeout": "inconclusive"}
print(f"k={os.environ['BOUND']} status={status} ({decisive[status]}) exit={os.environ['CODE']}")
PY
done

echo "-- a bound policy rejects the deeper query"
set +e
pyfcstm bmc -i region_controller.fcstm -q .region_tmp/ladder_3.fbmcq --max-bound 2 --json -o .region_tmp/policy.json 2>&1
echo "exit $?"
set -e
