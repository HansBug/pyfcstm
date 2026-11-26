#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_unsupported.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

echo "\$ cat region_plain_template/config.yaml"
cat region_plain_template/config.yaml
echo

echo "\$ pyfcstm generate -i region_two_regions.fcstm -t region_plain_template -o out_plain"
set +e
out=$(pyfcstm generate -i region_two_regions.fcstm -t region_plain_template -o "$workdir/out_plain" 2>&1)
code=$?
set -e
printf "%s\n" "$out" | sed -e "s#$PWD/##g" -e "s#$workdir/#./#g"
echo "exit status: $code"
if [ -e "$workdir/out_plain" ]; then echo "output directory exists"; else echo "output directory was not created"; fi
echo

echo "\$ pyfcstm generate -i region_two_regions.fcstm --template python -o out_python"
pyfcstm generate -i region_two_regions.fcstm --template python -o "$workdir/out_python"
echo "exit status: $?"
ls "$workdir/out_python" | LC_ALL=C sort
