"""Start the controller of the tutorial from a position, in the five accepted spellings."""
from pyfcstm.model import Configuration, load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

with open('../../tutorials/regions/controller.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())

# Every persistent variable is given, the hidden one included.
variables = {'permit': 1, 'motor': 1, '__forced_0': 0}
inputs = {'fault': 0, 'requested': 1}
motion_on = [state for state in model.walk_states()
             if state.path == ('Controller', 'Running', 'Motion', 'On')][0]


def start(label, position):
    runtime = SimulationRuntime(model, initial_state=position, initial_vars=variables,
                                input_source=inputs)
    print('%-34s %s' % (label, runtime.configuration))
    return runtime


print('-- the five spellings of initial_state')
start('configuration text', 'Controller.Running{Safety: Watching, Motion: On}')
start('Configuration object', Configuration.parse(
    model, 'Controller.Running{Safety: Watching, Motion: On}'))
start('dotted path into a region', 'Controller.Running.Motion.On')
start('tuple', ('Controller', 'Running', 'Motion', 'On'))
start('State object', motion_on)

print('-- what a position leaves out')
start('owner path alone', 'Controller.Running')
start('Safety written as [done]', 'Controller.Running{Safety: [done], Motion: On}')
start('Safety written as [init]', 'Controller.Running{Safety: [init], Motion: On}')
start('root only', 'Controller')
start('ordinary leaf', 'Controller.Idle')

print('-- the first cycle initializes the regions that were left out')
runtime = start('dotted path into a region', 'Controller.Running.Motion.On')
result = runtime.cycle()
print('%-34s %s  delta=%s' % ('after cycle 1', runtime.configuration, result.delta))
