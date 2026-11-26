#!/bin/sh
set -eu
cd "$(dirname "$0")"

echo '$ pyfcstm inspect -i controller.fcstm --color never   (Summary and diagnostic codes only)'
pyfcstm inspect -i controller.fcstm --color never | sed -n '1,15p;/^\[[A-Z]*\] [A-Z]_/p' | sed 's/[[:space:]]*$//'
echo
echo '$ pyfcstm inspect -i controller_swapped.fcstm --color never   (diagnostic codes only)'
pyfcstm inspect -i controller_swapped.fcstm --color never | grep -E '^\[[A-Z]+\] [A-Z]_'
echo
echo '$ pyfcstm inspect -i controller_swapped.fcstm --color never   (the order diagnostic in full)'
pyfcstm inspect -i controller_swapped.fcstm --color never | sed -n '/^\[INFO\] I_REGION_BACKWARD_READ/,$p' | sed 's/[[:space:]]*$//'
