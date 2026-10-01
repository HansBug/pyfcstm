#!/bin/sh
set -eu
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

echo "=== Inspect charger.fcstm ==="
pyfcstm inspect -i charger.fcstm --format human --color never > "$workdir/report.txt"
sed -n '/^Summary/,/^Structure/p' "$workdir/report.txt" | sed '$d'
grep '^  diagnostics:' "$workdir/report.txt"
grep -A1 '^\[WARN\] W_' "$workdir/report.txt" | grep -v '^--$'

# Deliberate mistake: keep the Session.[H*] target but drop its declaration.
sed '/\[H\*\] ->/d' charger.fcstm > "$workdir/forgot_deep.fcstm"
cd "$workdir"
echo ""
echo "=== Inspect forgot_deep.fcstm (no [H*] declaration) ==="
if pyfcstm inspect -i forgot_deep.fcstm --collect-errors \
    --format human --color never > report.txt; then
    status=0
else
    status=$?
fi
echo "exit status: $status"
grep '^  diagnostics:' report.txt
sed -n '/^\[ERROR\] E_HISTORY/,/^$/p' report.txt | sed 's/[[:space:]]*$//'
