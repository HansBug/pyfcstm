#!/bin/sh
cd "$(dirname "$0")"

workdir=".expression_depth.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

# One conjunction chain per size: ``true && true && ... && true``.
chain() {
    text="true"
    i=1
    while [ "$i" -lt "$1" ]; do
        text="$text && true"
        i=$((i + 1))
    done
    echo "check reach <= 1: $text;"
}

for terms in 50 150; do
    chain "$terms" > "$workdir/chain.fbmcq"
    echo "# chain.fbmcq: $terms terms joined by &&"
    echo "\$ pyfcstm bmc -i blocked.fcstm -q chain.fbmcq --color never"
    out="$(pyfcstm bmc -i blocked.fcstm -q "$workdir/chain.fbmcq" --color never 2>&1; echo "exit=$?")"
    printf '%s\n' "$out" | grep -E '^(BMC |Failed to compile|exit=)'
done
