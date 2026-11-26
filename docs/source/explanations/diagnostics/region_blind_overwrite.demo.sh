#!/bin/bash
set -e
cd "$(dirname "$0")"

echo '$ pyfcstm inspect -i region_blind_overwrite.fcstm'
pyfcstm inspect -i region_blind_overwrite.fcstm --color never | sed -n '/\[WARN\] W_REGION_BLIND_OVERWRITE/,/   = source/p'
echo '$ refs'
pyfcstm inspect -i region_blind_overwrite.fcstm --format json | python3 -c "
import json, sys
for d in json.load(sys.stdin)['diagnostics']:
    if d['code'] == 'W_REGION_BLIND_OVERWRITE':
        print(json.dumps(d['refs'], indent=2, sort_keys=True))"
echo '$ pyfcstm simulate: two cycles'
pyfcstm simulate -i region_blind_overwrite.fcstm -e "cycle --input fault=0; cycle --input fault=0" | grep -E "^(Cycle|Current State|  speed)"
