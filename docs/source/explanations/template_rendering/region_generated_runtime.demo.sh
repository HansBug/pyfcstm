#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_generated_runtime.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

model=../../tutorials/regions/controller.fcstm

echo '$ pyfcstm generate -i controller.fcstm --template python -o out'
pyfcstm generate -i "$model" --template python -o "$workdir/out"
ls "$workdir/out"

# The same six cycles are driven through the generated runtime and through the simulator.
cat > "$workdir/drive.py" <<'PY'
import sys

sys.path.insert(0, sys.argv[1])
from machine import ControllerMachine

machine = ControllerMachine()
steps = [
    (None, 0, 0),
    ("/Start", 0, 1),
    (None, 0, 1),
    (None, 1, 1),
    (None, 1, 1),
    ("/Stop", 0, 0),
]
for events, fault, requested in steps:
    machine.cycle(events, inputs={"fault": fault, "requested": requested})
    print(machine.configuration)
print("leaves:", machine.leaves)
print("is_active Controller.Running:", machine.is_active("Controller.Running"))
PY
echo
echo '$ python drive.py out   (generated runtime, configuration after each cycle)'
python3 "$workdir/drive.py" "$workdir/out" | tee "$workdir/generated.txt"

echo
echo '$ pyfcstm simulate -i controller.fcstm -e "cycle ..."   (configuration after each cycle)'
pyfcstm simulate -i "$model" -e "cycle --input fault=0 --input requested=0; cycle /Start --input fault=0 --input requested=1; cycle --input fault=0 --input requested=1; cycle --input fault=1 --input requested=1; cycle --input fault=1 --input requested=1; cycle /Stop --input fault=0 --input requested=0" \
    | grep "^Current State" | sed 's/^Current State: //' | tee "$workdir/simulated.txt"

echo
echo '$ diff generated simulated'
head -6 "$workdir/generated.txt" > "$workdir/generated_cycles.txt"
diff "$workdir/generated_cycles.txt" "$workdir/simulated.txt"
echo 'identical'
