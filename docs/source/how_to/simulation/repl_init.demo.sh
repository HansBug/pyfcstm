pyfcstm simulate -i hot_controller.fcstm --no-color -e \
  'init Controller.Running{Safety: Watching, Motion: On} permit=1 motor=1 __forced_0=0; events; init Controller.Running permit=1 motor=0 __forced_0=0'
