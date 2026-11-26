set -e
trap 'rm -rf .region_tmp' EXIT
. ./region_run.sh
run_region_query region_controller.fcstm region_start.fbmcq
