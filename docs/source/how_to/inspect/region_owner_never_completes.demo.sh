pyfcstm inspect -i region_never_completes.fcstm --color never |
    awk '$0 ~ /^\[WARN\] W_UNREACHABLE_TRANSITION$/ {p=1} p && /^$/ {p=0} p'
echo "== region_owner_completes_fixed.fcstm"
pyfcstm inspect -i region_owner_completes_fixed.fcstm --color never |
    grep -c 'owner_never_completes' || true
