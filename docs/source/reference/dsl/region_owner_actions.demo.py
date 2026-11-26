"""Run region_owner_actions.fcstm and decode the order of its actions."""
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

NAMES = {
    '10': 'Job enter', '11': 'Job during before', '12': 'Job during after', '13': 'Job exit',
    '20': 'Job >> before', '21': 'Job >> after',
    '30': 'A >> before', '31': 'A >> after',
    '32': 'A1 enter', '33': 'A1 during', '34': 'A1 exit',
    '42': 'B1 enter', '43': 'B1 during', '44': 'B1 exit',
    '90': 'Done enter',
}

with open('region_owner_actions.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())

runtime = SimulationRuntime(model)
seen = ''
for label, events in [('cycle 1', None), ('cycle 2', None), ('cycle 3 /Fin', '/Fin')]:
    runtime.cycle(events)
    total = str(runtime.vars['seq'])
    new, seen = total[len(seen):], total
    print('%s  %s' % (label, runtime.configuration))
    for index in range(0, len(new), 2):
        print('   %s  %s' % (new[index:index + 2], NAMES[new[index:index + 2]]))
