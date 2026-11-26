# Shared helper sourced by the region_*.demo.sh scripts: run one query and print
# the deterministic parts of its JSON result.
run_region_query() {
    model="$1"
    query="$2"
    workdir=".region_tmp"
    mkdir -p "$workdir"
    set +e
    pyfcstm bmc -i "$model" -q "$query" --json -o "$workdir/result.json"
    code="$?"
    set -e
    echo "-- $query (exit $code)"
    python region_summary.py "$workdir/result.json"
}
