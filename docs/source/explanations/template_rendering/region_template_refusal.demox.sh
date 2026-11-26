#!/bin/bash
cd "$(dirname "$0")"

workdir=".region_template_refusal.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

model=../../tutorials/regions/controller.fcstm

echo '$ cat region_plain_template/config.yaml'
cat region_plain_template/config.yaml
echo
echo '$ pyfcstm generate -i controller.fcstm -t region_plain_template -o out   (refused)'
pyfcstm generate -i "$model" -t region_plain_template -o "$workdir/out" 2> "$workdir/stderr.txt"
status=$?
echo "exit_code: $status"
echo "stderr (the page directory and the scratch directory are shortened):"
sed -e "s#$PWD#<page directory>#g" -e "s#$workdir/##g" "$workdir/stderr.txt"
if [ -e "$workdir/out" ]; then
    echo "output directory: created"
else
    echo "output directory: not created"
fi

echo
echo '$ cat region_declared_template/config.yaml'
cat region_declared_template/config.yaml
echo
echo '$ pyfcstm generate -i controller.fcstm -t region_declared_template -o out'
pyfcstm generate -i "$model" -t region_declared_template -o "$workdir/out"
echo "exit_code: $?"
cat "$workdir/out/states.txt"
exit "$status"
