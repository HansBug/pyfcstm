#!/bin/sh
# Commands that stop or report a negative result; each line after the command is its exit status.
here=$(pwd)
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT
cp "$here/../../tutorials/regions/controller.fcstm" "$here/../../tutorials/regions/controller_swapped.fcstm" "$workdir/"
cp "$here/motor_needs_permit.fbmcq" "$workdir/"
cp -r "$here/plain_template" "$workdir/"
cd "$workdir"

echo '$ pyfcstm generate -i controller.fcstm -t plain_template -o out'
pyfcstm generate -i controller.fcstm -t plain_template -o out 2>&1 | sed "s#'[^']*plain_template'#'plain_template'#"
echo "exit status: $(pyfcstm generate -i controller.fcstm -t plain_template -o out >/dev/null 2>&1; echo $?)"
test ! -e out && echo "out was not created"
echo

echo '$ pyfcstm bmc -i controller_swapped.fcstm -q motor_needs_permit.fbmcq   (verdict lines)'
pyfcstm bmc -i controller_swapped.fcstm -q motor_needs_permit.fbmcq | grep -E '^(BMC|Property verdict|  Replay)'
echo "exit status: $(pyfcstm bmc -i controller_swapped.fcstm -q motor_needs_permit.fbmcq >/dev/null 2>&1; echo $?)"
