#!/bin/bash
# max_depth counts a region as one layer; excerpts start at the first state line.
for depth in 1 2 3; do
    echo "\$ pyfcstm plantuml -i region_pipeline.fcstm -c max_depth=$depth"
    pyfcstm plantuml -i region_pipeline.fcstm -c max_depth=$depth | sed -n '/state "Work"/,/^    }$/p'
    echo
done
