#!/bin/sh
cd "$(dirname "$0")"

workdir=".call_snapshots.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

# Ask whether the abstract action $1 is called in step $2 while the whole
# machine matches the configuration pattern $3.
ask() {
    printf 'check reach <= 2: called("%s", step=%s, where active("%s"));\n' "$1" "$2" "$3" > "$workdir/query.fbmcq"
    cat "$workdir/query.fbmcq"
    pyfcstm bmc -i reenter.fcstm -q "$workdir/query.fbmcq" --color never | head -n 1
}

ask Root.O.B.Q.OnQ 0 'Root.O{A: P}'
ask Root.O.B.Q.OnQ 0 'Root.O{A: [init]}'
ask Root.O.A.P.OnEnter 0 'Root.O{B: [init]}'
ask Root.O.A.P.OnEnter 1 'Root.O{B: [init]}'
ask Root.O.A.P.OnEnter 1 'Root.O{B: Q}'
ask Root.O.A.P.OnExit 1 'Root.O{B: Q}'
ask Root.O.A.P.OnExit 1 'Root.O{B: [init]}'
