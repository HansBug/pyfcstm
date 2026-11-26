#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_capacity.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

cat > "$workdir/plain.fcstm" <<'FCSTM'
state Root {
    [*] -> A;
    state A;
    state B;
    A -> B :: Go;
}
FCSTM

echo 'model                          ARENA  TRAIL'
for entry in "plain:$workdir/plain.fcstm" \
             "two_regions:../diagnostics/region_blind_overwrite.fcstm" \
             "controller:../../tutorials/regions/controller.fcstm" \
             "never_completes:../diagnostics/region_never_completes.fcstm"; do
    name="${entry%%:*}"
    path="${entry#*:}"
    pyfcstm generate -i "$path" --template c -o "$workdir/$name" > /dev/null
    arena=$(grep -E '^#define [A-Z_]+_ARENA_CAPACITY [0-9]+' "$workdir/$name/machine.h" | awk '{print $3}')
    trail=$(grep -E '^#define [A-Z_]+_TRAIL_CAPACITY [0-9]+' "$workdir/$name/machine.h" | awk '{print $3}')
    printf '%-30s %5s  %5s\n' "$name" "$arena" "$trail"
done
