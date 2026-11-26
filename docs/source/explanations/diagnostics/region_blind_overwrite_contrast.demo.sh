#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_blind_overwrite_contrast.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

# Writes one variant, shows the line that differs and the order diagnostics.
check() {
    name="$1"
    shift
    {
        echo 'input int fault;'
        echo 'output int speed = 0;'
        echo 'state Drive {'
        echo '    region Planner {'
        echo '        [*] -> Plan;'
        echo '        state Plan { during { speed = 5; } }'
        echo '    }'
        echo '    region Limiter {'
        echo '        [*] -> Clamp;'
        echo "        state Clamp { $* }"
        echo '    }'
        echo '}'
    } > "$workdir/$name.fcstm"
    printf '%-18s Limiter: %s\n' "$name" "$*"
    printf '%-18s reported: ' ""
    pyfcstm inspect -i "$workdir/$name.fcstm" --format json | python3 -c "
import json, sys
codes = sorted({d['code'] for d in json.load(sys.stdin)['diagnostics'] if d['code'].startswith(('W_REGION', 'I_REGION'))})
print(', '.join(codes) if codes else 'none')"
}

check blind        'during { speed = 0; }'
check uses_old     'during { speed = speed - 1; }'
check conditional  'during { if [fault != 0] { speed = 0; } }'
check reads_first  'during { if [speed > 3] { speed = 0; } else { speed = 1; } }'
