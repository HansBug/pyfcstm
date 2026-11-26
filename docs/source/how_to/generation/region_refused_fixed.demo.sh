set -e
trap 'rm -rf .region_refused_out' EXIT
pyfcstm generate -i region_controller.fcstm --template python -o .region_refused_out --clear
LC_ALL=C ls .region_refused_out
