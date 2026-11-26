rm -rf .region_undeclared
mkdir .region_undeclared
cp region_listing_template/regions.txt.j2 .region_undeclared/
printf 'expr_styles: {}\n' > .region_undeclared/config.yaml
out=$(pyfcstm generate -i region_controller.fcstm -t .region_undeclared -o .region_undeclared_out --clear 2>&1)
code="$?"
rm -rf .region_undeclared
echo "$out" | sed "s#$PWD#.#g" >&2
exit "$code"
