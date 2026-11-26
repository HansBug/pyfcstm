"""List the events the model of region_events.fcstm owns and the event each
transition of a region refers to."""
from pyfcstm.model import load_state_machine_from_text

with open('region_events.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())

print('events owned by each namespace')
for state in model.walk_states():
    for event in state.events.values():
        print('  state  %-28s %s' % ('.'.join(state.path), event.path_name))
for region in model.walk_regions():
    for event in region.events.values():
        print('  region %-28s %s' % ('.'.join(region.path), event.path_name))

print('event of each transition written inside a region')
for region in model.walk_regions():
    for transition in region.transitions:
        if transition.event is not None:
            print('  %-14s %s -> %s  uses %s' % (
                '.'.join(region.path[-2:]), transition.from_state, transition.to_state,
                transition.event.path_name))

from pyfcstm.simulate import SimulationRuntime

print('cycles')
runtime = SimulationRuntime(model)
runtime.cycle()
print('  start                       ', runtime.configuration)
for event in ['/Job.Left.Go', 'Plant.Job.Right.Go', 'Plant.Job.Abort', '/Job.Abort']:
    try:
        result = runtime.cycle(event)
    except Exception as error:
        print('  %-28s %s: %s' % (event, type(error).__name__, error))
        continue
    print('  %-28s %s  consumed=%s' % (event, runtime.configuration, list(result.consumed_events)))
