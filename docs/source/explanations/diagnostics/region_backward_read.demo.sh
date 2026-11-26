#!/bin/bash
set -e
cd "$(dirname "$0")"

echo '$ pyfcstm inspect controller.fcstm (Safety, then Motion): is the code reported?'
pyfcstm inspect -i ../../tutorials/regions/controller.fcstm --format json | python3 -c "
import json, sys
codes = [d['code'] for d in json.load(sys.stdin)['diagnostics']]
print('I_REGION_BACKWARD_READ' in codes)"
echo '$ pyfcstm inspect controller_swapped.fcstm (Motion, then Safety)'
pyfcstm inspect -i ../../tutorials/regions/controller_swapped.fcstm --color never | sed -n '/\[INFO\] I_REGION_BACKWARD_READ/,/   = source/p'
echo '$ refs'
pyfcstm inspect -i ../../tutorials/regions/controller_swapped.fcstm --format json | python3 -c "
import json, sys
for d in json.load(sys.stdin)['diagnostics']:
    if d['code'] == 'I_REGION_BACKWARD_READ':
        print(json.dumps(d['refs'], indent=2, sort_keys=True))"
for f in controller controller_swapped; do
echo "--- run $f: Start, one calm cycle, then two cycles with fault=1"
pyfcstm simulate -i ../../tutorials/regions/$f.fcstm -e "cycle --input fault=0 --input requested=0; cycle /Start --input fault=0 --input requested=1; cycle --input fault=0 --input requested=1; cycle --input fault=1 --input requested=1; cycle --input fault=1 --input requested=1" | grep -E "^(Cycle|Current State|  (motor|permit) )"
done
