#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_inspect_overapprox.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

codes='
import json, sys
found = [d["code"] + "@" + str(d["span"]["line"]) for d in json.load(sys.stdin)["diagnostics"]
         if d["code"].startswith(("W_UNREACHABLE", "W_DEAD_GUARD", "W_FORCED"))]
print("  " + (", ".join(found) if found else "no unreachable-state, dead-guard or forced finding"))'

echo '--- 1. a state that only history skips'
cat > "$workdir/history.fcstm" <<'FCSTM'
input int go;

state Plant {
    [*] -> Idle;
    state Idle;
    state Mode {
        [*] -> Cold;
        [H] -> Warm;
        state Cold;
        state Warm;
    }
    Idle -> Mode.[H] : if [go != 0];
}
FCSTM
cat "$workdir/history.fcstm"
echo '$ pyfcstm inspect'
pyfcstm inspect -i "$workdir/history.fcstm" --format json | python3 -c "$codes"
echo '$ pyfcstm simulate'
pyfcstm simulate -i "$workdir/history.fcstm" -e "cycle --input go=0; cycle --input go=1" | grep -E "^(Cycle|Current State)"

echo
echo '--- 2. a forced declaration whose guard can never hold'
cat > "$workdir/forced.fcstm" <<'FCSTM'
input int fault;

state Line {
    [*] -> Work;
    state Work {
        [*] -> Spin;
        state Spin;
    }
    state Stopped;
    !Work -> Stopped : if [fault != 0 && fault == 0];
}
FCSTM
cat "$workdir/forced.fcstm"
echo '$ pyfcstm inspect'
pyfcstm inspect -i "$workdir/forced.fcstm" --format json | python3 -c "$codes"
echo '$ pyfcstm inspect --enable-verify --max-complexity-tier smt_linear'
pyfcstm inspect -i "$workdir/forced.fcstm" --enable-verify --max-complexity-tier smt_linear --format json | python3 -c "$codes"
