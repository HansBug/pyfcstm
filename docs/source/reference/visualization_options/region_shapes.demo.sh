#!/bin/bash
# One region, two regions, and nested regions; excerpts start at the first state line.
for model in region_single region_nested; do
    echo "\$ pyfcstm plantuml -i $model.fcstm"
    pyfcstm plantuml -i $model.fcstm | sed -n '/^state "/,$p'
    echo
done
