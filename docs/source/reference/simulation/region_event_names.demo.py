"""Resolve event names against a position with several active leaves."""
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeEventError

with open('event_names.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())


def runtime_at(position):
    return SimulationRuntime(model, initial_state=position, initial_vars={'trail': 0})


both = 'Controller.Running{Safety: Watching, Motion: Off}'
print('position: %s' % both)
config = runtime_at(both).configuration
print('-- Configuration.resolve_event')
for name in ['Trip', 'Go', 'Ping', 'Nope', '..Stop', '.Stop', '/Running.Stop', '/Reset', 'Reset']:
    try:
        print('%-15s -> %s' % (name, config.resolve_event(name).path_name))
    except (ValueError, LookupError) as error:
        # ModelValueError (a ValueError) marks an ambiguous or malformed name and
        # ModelLookupError (a LookupError) marks a name that no active leaf finds.
        print('%-15s !! %s: %s' % (name, type(error).__name__, error))

print('-- runtime.cycle(name)')
for name in ['Controller.Running.Stop', 'Controller.Running.Motion.Off.Ping', '/Running.Stop',
             '..Stop', 'Running.Stop', 'Ping', 'Trip']:
    runtime = runtime_at(both)
    try:
        result = runtime.cycle([name])
    except SimulationRuntimeEventError as error:
        # SimulationRuntimeEventError: the name is unknown, ambiguous or foreign.
        print('%-36s !! %s: %s' % (name, type(error).__name__, error))
    else:
        print('%-36s ok  %s  consumed=%s' % (name, runtime.configuration, list(result.consumed_events)))

print('-- a finished region does not take part')
done = 'Controller.Running{Safety: [done], Motion: Off}'
runtime = runtime_at(done)
result = runtime.cycle(['Ping'])
print('Ping from %s -> consumed %s' % (done, list(result.consumed_events)))

print('-- one active leaf')
for name in ['Start', 'Reset']:
    runtime = runtime_at('Controller.Idle')
    try:
        runtime.cycle([name])
        print('%-6s ok  %s' % (name, runtime.configuration))
    except SimulationRuntimeEventError as error:
        # SimulationRuntimeEventError: the name is unknown, ambiguous or foreign.
        print('%-6s !! %s: %s' % (name, type(error).__name__, error))
