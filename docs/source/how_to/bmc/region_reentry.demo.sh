set -e
trap 'rm -rf .region_tmp' EXIT
for model in region_reentry_six region_reentry_loop; do
    set +e
    out=$(pyfcstm bmc -i $model.fcstm -q region_reentry.fbmcq --color never 2>&1)
    code="$?"
    set -e
    echo "-- $model.fcstm (exit $code)"
    echo "$out" | grep -E "^(BMC reach|_BmcCliInternalError)"
done
