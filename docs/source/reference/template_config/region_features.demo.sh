work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp region_controller.fcstm region_plain.fcstm "$work"
cd "$work"

make_template() {
    # $1 = directory, $2 = the config.yaml text
    mkdir -p "$1"
    printf 'name: {{ model.root_state.name }}\n' > "$1/names.txt.j2"
    printf '%s\n' "$2" > "$1/config.yaml"
}

run_case() {
    # $1 = label, $2 = template directory, $3 = model
    echo "== $1"
    rm -rf out
    python -m pyfcstm generate -i "$3" -t "$2" -o out > stdout.txt 2> stderr.txt
    echo "exit=$?"
    sed "s#$work#<work>#g" stderr.txt
    cat stdout.txt
    echo "files written: $(LC_ALL=C ls out 2>/dev/null | tr '\n' ' ')"
}

make_template declared 'features: [region]'
make_template undeclared '{}'
make_template empty_list 'features: []'
make_template null_value 'features:'

run_case "region model, template declares [region]" declared region_controller.fcstm
run_case "region model, template without features" undeclared region_controller.fcstm
run_case "region model, features: []" empty_list region_controller.fcstm
run_case "region model, features: null" null_value region_controller.fcstm
run_case "model without regions, template without features" undeclared region_plain.fcstm
