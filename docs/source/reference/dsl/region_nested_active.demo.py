"""Run region_nested_active.fcstm and show the hidden variables it adds."""
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

with open('region_nested_active.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())

print('hidden variables in StateMachine.defines')
for name in model.defines:
    print('  ', name)
print('active queries')
for query in model.active_queries:
    print('  ', '.'.join(query.state_path), '->', query.variable_name)

runtime = SimulationRuntime(model)
runtime.cycle()
print('cycle %d  %s' % (runtime.cycle_count, runtime.configuration))
for event in ['/Go', '/Trip', '/Stop', '/Resume']:
    runtime.cycle(event)
    print('cycle %d  %-8s %s' % (runtime.cycle_count, event, runtime.configuration))
