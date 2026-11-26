report() {
    out=$(pyfcstm inspect -i "$1" --color never |
        awk -v code="$2" '$0 ~ "^\\[(INFO|WARN)\\] " code "$" {p=1} p && /^$/ {p=0} p')
    if [ -z "$out" ]; then
        echo "$1: $2 is not reported"
    else
        echo "$out"
    fi
}

echo "== region_read_back.fcstm"
report region_read_back.fcstm I_REGION_BACKWARD_READ
echo "== region_read_back_fixed.fcstm"
report region_read_back_fixed.fcstm I_REGION_BACKWARD_READ
echo "== region_blind_overwrite.fcstm"
report region_blind_overwrite.fcstm W_REGION_BLIND_OVERWRITE
echo "== region_blind_overwrite_fixed.fcstm"
report region_blind_overwrite_fixed.fcstm W_REGION_BLIND_OVERWRITE
