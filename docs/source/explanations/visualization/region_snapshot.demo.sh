#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=".region_snapshot.tmp"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

outline='
import json, sys

def walk(node, depth):
    flag = ""
    if node.get("region"):
        flag = "  region=true ordinal=%d" % node["ordinal"]
    print("%s%s%s" % ("  " * depth, node["id"], flag))
    for child in node["children"]:
        walk(child, depth + 1)

walk(json.load(sys.stdin)["rootState"], 0)'

for name in controller controller_swapped; do
    echo "\$ pyfcstm diagram -i $name.fcstm -o $name.json"
    pyfcstm diagram -i ../../tutorials/regions/$name.fcstm -o "$workdir/$name.json" > /dev/null
    python3 -c "$outline" < "$workdir/$name.json"
    echo
done
