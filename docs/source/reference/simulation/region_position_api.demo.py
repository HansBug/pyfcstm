"""Read the position of a runtime for a model with regions and for one without."""
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeRegionQueryError

with open('../../tutorials/regions/controller.fcstm') as stream:
    controller = load_state_machine_from_text(stream.read())
plain = load_state_machine_from_text('state Root { [*] -> A; state A; state B; A -> B :: Go; }')

print('-- model with regions')
runtime = SimulationRuntime(controller, input_source={'fault': 0, 'requested': 1})
runtime.cycle()
runtime.cycle('/Start')
print('configuration  %r' % runtime.configuration)
print('current_state  %s (%s)' % (runtime.current_state, type(runtime.current_state).__name__))
print('leaves         %s' % [state.path for state in runtime.configuration.leaves])
try:
    runtime.brief_stack
except SimulationRuntimeRegionQueryError as error:
    # SimulationRuntimeRegionQueryError: a stack describes one path, a model with
    # regions has one branch per region.
    print('brief_stack    %s: %s' % (type(error).__name__, error))

result = runtime.cycle()
print('CycleResult    delta=%s input_events=%s consumed_events=%s unconsumed_events=%s' % (
    result.delta, result.input_events, result.consumed_events, result.unconsumed_events))
print('after cycle 3  %s  motor=%s' % (runtime.configuration, runtime.vars['motor']))

print('-- model without regions')
runtime = SimulationRuntime(plain)
runtime.cycle()
print('configuration  %r' % runtime.configuration)
print('current_state  %s (%s)' % (runtime.current_state.path, type(runtime.current_state).__name__))
print('brief_stack    %s' % runtime.brief_stack)
