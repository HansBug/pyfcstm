set -e
trap 'rm -rf .region_declared_out' EXIT
cat region_listing_template/config.yaml
pyfcstm generate -i region_controller.fcstm -t region_listing_template -o .region_declared_out --clear
cat .region_declared_out/regions.txt
python - <<'PY'
from pyfcstm.render import StateMachineCodeRenderer

print(sorted(StateMachineCodeRenderer("region_listing_template").features))
PY
