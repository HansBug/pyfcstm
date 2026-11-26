#!/bin/sh
cd "$(dirname "$0")"

# A position in which every region of an owner is done is refused.
pyfcstm simulate -i controller.fcstm --no-color -e "init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=1 __forced_0=0"
