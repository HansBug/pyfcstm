for name in controller controller_swapped; do
    echo "== $name.fcstm"
    pyfcstm inspect -i $name.fcstm --color never |
        awk '/^\[(INFO|WARN)\] (I|W)_REGION/{p=1} p&&/^$/{p=0} p'
done
