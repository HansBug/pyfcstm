#!/bin/bash
set -e
cd "$(dirname "$0")"

echo '$ pyfcstm plantuml -i controller.fcstm   (the Running block)'
pyfcstm plantuml -i ../../tutorials/regions/controller.fcstm | sed -n '/^    state "Running"/,/^    }$/p'
echo
echo '$ pyfcstm plantuml -i controller_swapped.fcstm   (region lines only)'
pyfcstm plantuml -i ../../tutorials/regions/controller_swapped.fcstm | grep -E '\*\*region|^ +--$'
echo
echo '$ pyfcstm plantuml -i controller.fcstm -c max_depth=2   (the Running block)'
pyfcstm plantuml -i ../../tutorials/regions/controller.fcstm -c max_depth=2 | sed -n '/^    state "Running"/,/^    }$/p'
