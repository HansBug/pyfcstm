#!/bin/sh
# Every command below is refused; the transcript records the message and the exit status of each.
here=$(pwd)
model="$here/../../tutorials/regions/controller.fcstm"
for script in \
    "init Controller.Running{Safety: Watching, Motion: On permit=1 motor=1 __forced_0=0" \
    "init Controller.Running permit=1 permit=0 motor=1 __forced_0=0" \
    "init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=1 __forced_0=0" \
    "init Controller.Running{Safety: Nowhere, Motion: On} permit=1 motor=1 __forced_0=0" \
    "init Controller.Running.Motion permit=1 motor=1 __forced_0=0" \
    "init Controller.Running permit=1 motor=1" \
    "init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; cycle Stop2 --input fault=0 --input requested=1"
do
    echo "\$ pyfcstm simulate -i controller.fcstm -e \"$script\""
    pyfcstm simulate -i "$model" --no-color -e "$script" 2>&1 | grep -v '^─' | sed 's/[[:space:]]*$//' | grep -v '^$'
    echo "exit status: $(pyfcstm simulate -i "$model" --no-color -e "$script" >/dev/null 2>&1; echo $?)"
    echo
done
