set -e
trap 'rm -rf .region_out' EXIT
rm -rf .region_out
for template in python c c_poll cpp cpp_poll; do
    pyfcstm generate -i region_controller.fcstm --template $template -o .region_out/$template --clear
    echo "$template: $(cd .region_out/$template && LC_ALL=C ls | tr '\n' ' ')"
done
cp region_app.py .region_out/python/app.py
(cd .region_out/python && python app.py)
