set -e
trap 'rm -rf .region_accept' EXIT
mkdir -p .region_accept
MODEL=region_controller.fcstm

echo "== 1. simulate"
pyfcstm simulate -i $MODEL --no-color -e \
    "cycle --input fault=0 --input requested=1; cycle /Start --input fault=0 --input requested=1; cycle --input fault=0 --input requested=1; cycle --input fault=1 --input requested=1" |
    grep -E '^Cycle:|^Current State:'

echo "== 2. inspect"
pyfcstm inspect -i $MODEL --color never | sed -n '/^Summary/,/^Structure statistics/p' | sed '$d'

echo "== 3. bmc"
set +e
pyfcstm bmc -i $MODEL -q region_motion.fbmcq --json -o .region_accept/bmc.json
echo "exit $?"
set -e
python - <<'PY'
import json

payload = json.load(open(".region_accept/bmc.json", encoding="utf-8"))
print(payload["result"]["status"], payload["result"]["outcome"], "replay ok:", payload["replay"]["ok"])
for frame in payload["witness"]["frames"]:
    print(f"frame {frame['index']}: {frame['configuration']}")
PY

echo "== 4. generate"
pyfcstm generate -i $MODEL --template python -o .region_accept/python --clear
(cd .region_accept/python && LC_ALL=C ls)

echo "== 5. plantuml"
pyfcstm plantuml -i $MODEL -o .region_accept/machine.puml
grep -E 'region [0-9]+:|^ *--$' .region_accept/machine.puml

echo "== 6. diagram"
pyfcstm diagram -i $MODEL -o .region_accept/machine.json
python -c "import json; print(json.load(open('.region_accept/machine.json'))['summary'])"
