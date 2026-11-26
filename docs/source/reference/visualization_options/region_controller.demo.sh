#!/bin/bash
# A forced transition on the owner and the hidden variable it adds; excerpts start at the legend.
echo '$ pyfcstm plantuml -i region_controller.fcstm -l full'
pyfcstm plantuml -i region_controller.fcstm -l full | sed -n '/^legend top left/,$p'
