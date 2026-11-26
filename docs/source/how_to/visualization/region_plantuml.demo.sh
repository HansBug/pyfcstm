set -e
trap 'rm -rf .region_puml' EXIT
mkdir -p .region_puml
for depth in none 3 2 1; do
    if [ "$depth" = none ]; then
        pyfcstm plantuml -i region_controller.fcstm -o .region_puml/out.puml
    else
        pyfcstm plantuml -i region_controller.fcstm -c max_depth=$depth -o .region_puml/out.puml
    fi
    echo "== max_depth=$depth"
    grep -E 'region [0-9]+:|^ *--$|collapsed' .region_puml/out.puml
done
echo "== event paths in the legend"
pyfcstm plantuml -i region_events.fcstm -c show_events=true -c event_visualization_mode=legend |
    sed -n '/^legend right/,/^endlegend/p'
