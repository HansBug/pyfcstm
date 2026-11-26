#!/bin/bash
# An event written inside a region belongs to that region; the legend shows its path from the root.
echo '$ pyfcstm plantuml -i region_nested.fcstm -c event_visualization_mode=legend'
pyfcstm plantuml -i region_nested.fcstm -c event_visualization_mode=legend | sed -n '/^legend right/,/^endlegend/p'
echo
echo '$ pyfcstm plantuml -i region_pipeline.fcstm -c event_visualization_mode=legend'
pyfcstm plantuml -i region_pipeline.fcstm -c event_visualization_mode=legend | sed -n '/^legend right/,/^endlegend/p'
