pyfcstm simulate -i hot_controller.fcstm --no-color -e \
  'init Controller.Running{Safety: [done], Motion: [done]} permit=1 motor=0 __forced_0=0'
