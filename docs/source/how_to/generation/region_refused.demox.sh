out=$(pyfcstm generate -i region_controller.fcstm -t plain_template -o .region_refused_out --clear 2>&1)
code="$?"
echo "$out" | sed "s#$PWD#.#g" >&2
ls .region_refused_out > /dev/null 2>&1 || echo "no output directory was written" >&2
exit "$code"
