"""A region that waits for initialization and cannot reach a resting place makes the cycle a Delta."""
import logging

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

logging.disable(logging.CRITICAL)  # keep the Delta log lines out of the transcript

with open('pending_delta.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())

variables = {'ready': 0, 'ticks': 0}
for label, position in [('cold start', None),
                        ('Gate left out', 'Plant.Job{Count: Counting}'),
                        ('owner path alone', 'Plant.Job')]:
    if position is None:
        runtime = SimulationRuntime(model)
    else:
        runtime = SimulationRuntime(model, initial_state=position, initial_vars=dict(variables))
    result = runtime.cycle()
    print('%-18s delta=%s  %s  cycle_count=%d  ticks=%s' % (
        label, result.delta, runtime.configuration, runtime.cycle_count, runtime.vars['ticks']))

runtime = SimulationRuntime(model, initial_state='Plant.Job{Count: Counting}',
                            initial_vars={'ready': 1, 'ticks': 0})
result = runtime.cycle()
print('%-18s delta=%s  %s  cycle_count=%d  ticks=%s' % (
    'ready=1', result.delta, runtime.configuration, runtime.cycle_count, runtime.vars['ticks']))
