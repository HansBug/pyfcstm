"""Hot start a model that queries active() and compute the hidden flags from a position."""
from pyfcstm.model import Configuration, load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

with open('active_flags.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())

position = 'Root.Job{Feed: Busy, Check: Watch}'
config = Configuration.parse(model, position)
flags = model.active_variables(config)
print('active_variables(%s)' % config)
for name, value in flags.items():
    print('   %s = %s' % (name, value))

try:
    SimulationRuntime(model, initial_state=position, initial_vars={'alarm': 0, 'ticks': 0})
except ValueError as error:
    # ValueError: the hidden flag is an ordinary variable and has to be given.
    print('without the flag: %s' % error)

runtime = SimulationRuntime(model, initial_state=position, initial_vars=dict(flags, alarm=0, ticks=0))
runtime.cycle()
print('with the flag:    %s  alarm=%s' % (runtime.configuration, runtime.vars['alarm']))

wrong = dict(flags, alarm=0, ticks=0)
wrong[next(iter(flags))] = 0
runtime = SimulationRuntime(model, initial_state=position, initial_vars=wrong)
runtime.cycle()
print('flag given as 0:  %s  alarm=%s' % (runtime.configuration, runtime.vars['alarm']))
