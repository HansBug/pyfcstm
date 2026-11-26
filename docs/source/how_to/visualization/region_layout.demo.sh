set -e
trap 'rm -rf .region_layout' EXIT
mkdir -p .region_layout
pyfcstm plantuml -i region_controller.fcstm -o .region_layout/default.puml
echo "layout directives in the exported source: $(grep -c 'pragma layout' .region_layout/default.puml || true)"
echo "concurrent separators in the exported source: $(grep -c '^ *--$' .region_layout/default.puml)"
