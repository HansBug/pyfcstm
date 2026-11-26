#!/bin/bash
# Names that differ only in letter case give the same PlantUML alias (counterexample).
echo '$ pyfcstm plantuml -i region_case_alias.fcstm'
pyfcstm plantuml -i region_case_alias.fcstm | sed -n '/^state "/,$p'
