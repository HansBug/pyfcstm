#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_generated_c_runtime.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

model=../../tutorials/regions/controller.fcstm

echo '$ pyfcstm generate -i controller.fcstm --template c -o out'
pyfcstm generate -i "$model" --template c -o "$workdir/out"
ls "$workdir/out"

echo
echo '$ capacity macros chosen for this model'
grep -E '^#define CONTROLLER_MACHINE_(ARENA|TRAIL)_CAPACITY [0-9]+' "$workdir/out/machine.h"

cat > "$workdir/app.c" <<'C'
#include <stdio.h>
#include "machine.h"

static void show(const ControllerMachine *machine)
{
    ControllerMachineConfiguration configuration;
    char text[128];
    if (ControllerMachine_get_configuration(machine, &configuration) != CONTROLLER_MACHINE_SUCCESS) {
        puts("ended");
        return;
    }
    ControllerMachine_configuration_format(&configuration, text, sizeof(text));
    puts(text);
}

int main(void)
{
    static ControllerMachine machine;
    ControllerMachineEventId start = CONTROLLER_MACHINE_EVENT_CONTROLLER_START;
    ControllerMachineEventId stop = CONTROLLER_MACHINE_EVENT_CONTROLLER_STOP;
    ControllerMachineInputs calm = {0, 1}, fault = {1, 1}, idle = {0, 0};

    ControllerMachine_init(&machine);
    ControllerMachine_cycle_with_inputs(&machine, NULL, 0, &idle);
    show(&machine);
    ControllerMachine_cycle_with_inputs(&machine, &start, 1, &calm);
    show(&machine);
    ControllerMachine_cycle_with_inputs(&machine, NULL, 0, &calm);
    show(&machine);
    ControllerMachine_cycle_with_inputs(&machine, NULL, 0, &fault);
    show(&machine);
    ControllerMachine_cycle_with_inputs(&machine, NULL, 0, &fault);
    show(&machine);
    ControllerMachine_cycle_with_inputs(&machine, &stop, 1, &idle);
    show(&machine);
    return 0;
}
C
cc -std=c99 -Wall -Wextra -pedantic -DPYFCSTM_GENERATED_NO_HEAP -I"$workdir/out" "$workdir/out/machine.c" "$workdir/app.c" -lm -o "$workdir/app"
echo
echo '$ ./app   (built with -DPYFCSTM_GENERATED_NO_HEAP; configuration text after each cycle)'
"$workdir/app" | tee "$workdir/generated.txt"

echo
echo '$ pyfcstm simulate -i controller.fcstm -e "cycle ..."'
pyfcstm simulate -i "$model" -e "cycle --input fault=0 --input requested=0; cycle /Start --input fault=0 --input requested=1; cycle --input fault=0 --input requested=1; cycle --input fault=1 --input requested=1; cycle --input fault=1 --input requested=1; cycle /Stop --input fault=0 --input requested=0" \
    | grep "^Current State" | sed 's/^Current State: //' | tee "$workdir/simulated.txt"

echo
echo '$ diff generated simulated'
diff "$workdir/generated.txt" "$workdir/simulated.txt"
echo 'identical'
