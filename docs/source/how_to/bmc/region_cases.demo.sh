set -e
trap 'rm -rf .region_tmp' EXIT
. ./region_run.sh
run_region_query region_controller.fcstm region_cases.fbmcq
echo "-- human trace of the same query"
pyfcstm bmc -i region_controller.fcstm -q region_cases.fbmcq --color never |
    sed -n '/^Trace/,/^$/p'
echo "-- cover a local case"
run_region_query region_controller.fcstm region_cover.fbmcq
