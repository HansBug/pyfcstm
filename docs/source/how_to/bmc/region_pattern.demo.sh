set -e
trap 'rm -rf .region_tmp' EXIT
. ./region_run.sh
run_region_query region_controller.fcstm region_pattern_construct.fbmcq 0
run_region_query region_controller.fcstm region_pattern_match.fbmcq 0
run_region_query region_controller.fcstm region_pattern_construct_miss.fbmcq
