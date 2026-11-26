set -e
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
CC_FLAGS="-std=c99 -Wall -Wextra -pedantic -O1"

echo "== c: model with regions (region_controller.fcstm)"
python -m pyfcstm generate -i region_controller.fcstm --template c -o "$work/c" > /dev/null
cc $CC_FLAGS -I "$work/c" "$work/c/machine.c" region_c_runtime.c -lm -o "$work/c_demo"
"$work/c_demo"

echo "== c: hook context (region_probe.fcstm)"
python -m pyfcstm generate -i region_probe.fcstm --template c -o "$work/hooks" > /dev/null
cc $CC_FLAGS -I "$work/hooks" "$work/hooks/machine.c" region_c_hooks.c -lm -o "$work/hooks_demo"
"$work/hooks_demo"

echo "== c: model without regions (region_plain.fcstm)"
python -m pyfcstm generate -i region_plain.fcstm --template c -o "$work/plain" > /dev/null
grep -o "PlainMachine_current_state_[a-z]*" "$work/plain/machine.h" | sort -u
echo "== c: model with regions (current_state_* functions in machine.h)"
grep -o "ControllerMachine_current_state_[a-z]*" "$work/c/machine.h" | sort -u | wc -l

echo "== cpp: wrapper over the same core"
python -m pyfcstm generate -i region_controller.fcstm --template cpp -o "$work/cpp" > /dev/null
cc -std=c99 -O1 -c "$work/cpp/machine.c" -o "$work/cpp/machine_c.o"
c++ -std=c++98 -Wall -Wextra -pedantic -O1 -I "$work/cpp" "$work/cpp/machine.cpp" region_cpp_runtime.cpp "$work/cpp/machine_c.o" -lm -o "$work/cpp_demo"
"$work/cpp_demo"

echo "== c_poll: event checks are queried during the cycle"
python -m pyfcstm generate -i region_controller.fcstm --template c_poll -o "$work/c_poll" > /dev/null
cc $CC_FLAGS -I "$work/c_poll" "$work/c_poll/machine.c" region_c_poll_runtime.c -lm -o "$work/c_poll_demo"
"$work/c_poll_demo"

echo "== cpp_poll: wrapper over the polling core"
python -m pyfcstm generate -i region_controller.fcstm --template cpp_poll -o "$work/cpp_poll" > /dev/null
cc -std=c99 -O1 -c "$work/cpp_poll/machine.c" -o "$work/cpp_poll/machine_c.o"
c++ -std=c++98 -Wall -Wextra -pedantic -O1 -I "$work/cpp_poll" "$work/cpp_poll/machine.cpp" region_cpp_poll_runtime.cpp "$work/cpp_poll/machine_c.o" -lm -o "$work/cpp_poll_demo"
"$work/cpp_poll_demo"
