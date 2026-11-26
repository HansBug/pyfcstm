set -e
trap 'rm -rf .region_c' EXIT
rm -rf .region_c
pyfcstm generate -i region_controller.fcstm --template c -o .region_c --clear
cp region_capacity_app.c .region_c/app.c
grep -E '^#define CONTROLLER_MACHINE_(ARENA|TRAIL)_CAPACITY' .region_c/machine.h

run() {
    echo "-- cc $*"
    (
        cd .region_c
        cc -std=c99 -Wall -Wextra -pedantic -O2 "$@" machine.c app.c -lm -o app
        set +e
        ./app
        echo "exit $?"
    )
}

run
run -DCONTROLLER_MACHINE_ARENA_CAPACITY=4
run -DCONTROLLER_MACHINE_ARENA_CAPACITY=480 -DCONTROLLER_MACHINE_TRAIL_CAPACITY=96
