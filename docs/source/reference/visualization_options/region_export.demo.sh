#!/bin/bash
# PlantUML export of a model with two ordered regions; excerpts start at the first state line.
echo '$ pyfcstm plantuml -i region_pipeline.fcstm'
pyfcstm plantuml -i region_pipeline.fcstm | sed -n '/^state "/,$p'
echo
echo '$ pyfcstm plantuml -i region_pipeline.fcstm -l full   (excerpt: the region 1 note and the owner aspect)'
pyfcstm plantuml -i region_pipeline.fcstm -l full | sed -n '/region 1: Intake/,/end note/p'
pyfcstm plantuml -i region_pipeline.fcstm -l full | grep '^    line__work : '
