"""Print the error of every position and variable set that a hot start refuses."""
from pyfcstm.model import Configuration, load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

with open('../../tutorials/regions/controller.fcstm') as stream:
    text = stream.read()
model = load_state_machine_from_text(text)
other = load_state_machine_from_text(text)
variables = {'permit': 1, 'motor': 1, '__forced_0': 0}
inputs = {'fault': 0, 'requested': 1}


def state_of(machine, path):
    return [state for state in machine.walk_states() if state.path == path][0]


CASES = [
    ('every region done', 'Controller.Running{Safety: [done], Motion: [done]}', variables),
    ('unknown state in a region', 'Controller.Running{Safety: Nowhere, Motion: On}', variables),
    ('unknown state', 'Controller.Nowhere', variables),
    ('a region as the position', 'Controller.Running.Motion', variables),
    ('empty text', '', variables),
    ('unbalanced braces', 'Controller.Running{Safety: Watching, Motion: On', variables),
    ('region written twice', 'Controller.Running{Safety: Watching, Safety: Watching}', variables),
    ('old marker [*]', 'Controller.Running{Safety: [*], Motion: On}', variables),
    ('marker with other case', 'Controller.Running{Safety: [Done], Motion: On}', variables),
    ('Configuration of another model',
     Configuration.parse(other, 'Controller.Running{Safety: Watching, Motion: On}'), variables),
    ('State of another model', state_of(other, ('Controller', 'Running', 'Motion', 'On')), variables),
    ('a number', 5, variables),
    ('a list', ['Controller', 'Running'], variables),
    ('hidden variable missing', 'Controller.Running.Motion.On', {'permit': 1, 'motor': 1}),
]
for label, position, given in CASES:
    try:
        SimulationRuntime(model, initial_state=position, initial_vars=given, input_source=inputs)
    except (ValueError, TypeError) as error:
        # ValueError: the position or the variable set is invalid; TypeError: the
        # position has a type that initial_state does not accept.
        print('%s\n    %s: %s' % (label, type(error).__name__, error))
    else:
        print('%s\n    accepted' % label)
