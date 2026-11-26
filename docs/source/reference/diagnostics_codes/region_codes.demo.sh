#!/bin/bash
set -e
cd "$(dirname "$0")"

# Run one inspect command. A rejected model prints the CLI error text; an
# accepted one prints a one-line summary. The exit status is always shown.
run() {
    echo "\$ pyfcstm inspect -i $1 --format json"
    set +e
    out=$(pyfcstm inspect -i "$1" --format json 2>&1)
    code=$?
    set -e
    if [ "$code" -eq 0 ]; then
        printf "%s\n" "$out" | python -c '
import json
import sys

report = json.load(sys.stdin)
print("accepted: %d states, %d regions" % (len(report["states"]), len(report.get("regions", []))))
'
    else
        printf "%s\n" "$out"
    fi
    echo "exit status: $code"
    echo
}

echo "=== E_REGION_STRUCTURE ==="
run region_diag_empty_region.fcstm.txt
run region_diag_empty_region_fixed.fcstm
run region_diag_history_boundary.fcstm.txt
run region_diag_history_outside.fcstm
echo "=== mixed_children and owner_statements: syntax errors in text ==="
run region_diag_mixed_children.fcstm.txt
run region_diag_owner_transition.fcstm.txt

echo "=== E_DUPLICATE_REGION ==="
run region_diag_duplicate.fcstm.txt
run region_diag_same_name_two_owners.fcstm

echo "=== E_ACTIVE_QUERY_TARGET ==="
run region_diag_active_not_found.fcstm.txt
run region_diag_active_invalid_path.fcstm.txt
run region_diag_active_region.fcstm.txt
run region_diag_active_pseudo.fcstm.txt
run region_diag_active_ok.fcstm
echo "=== active() in a persistent initializer is a syntax error ==="
run region_diag_active_initializer.fcstm.txt
