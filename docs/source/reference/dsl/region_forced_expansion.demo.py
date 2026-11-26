"""Show the plain FCSTM that forced transitions expand to when regions are involved."""
from pyfcstm.model import load_state_machine_from_text


def load(path):
    with open(path) as stream:
        return load_state_machine_from_text(stream.read())


def block(text, header):
    """Return the exported lines of the block that starts with ``header``."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == header)
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = next(index for index in range(start + 1, len(lines))
               if lines[index].strip() == '}' and len(lines[index]) - len(lines[index].lstrip()) == indent)
    return '\n'.join(lines[start:end + 1])


model = load('../../tutorials/regions/controller.fcstm')
print('== written: !Running -> Idle : /Stop;   (owner Running has regions Safety and Motion)')
print('forced_transitions:', [(item['from_path'], item['to_path'], item['expansion_count'])
                              for item in model.forced_transitions])
print('forced_variables:', list(model.forced_variables))
exported = str(model.to_ast_node())
print('== expanded: region Safety')
print(block(exported, 'region Safety {'))
print('== expanded: region Motion')
print(block(exported, 'region Motion {'))
print('== expanded: the owner scope (Controller) transitions and gate state')
for line in exported.splitlines():
    if line.strip().startswith(('Running ->', 'pseudo state __forced_gate_0', '__forced_gate_0 ->')):
        print(line)

print('== written: !* -> Safe : /Fault;   (owner scope Plant has Idle, Run with regions, Safe)')
wildcard = load('region_forced_wildcard.fcstm')
print('forced_transitions:', [(item['from_path'], item['to_path'], item['expansion_count'])
                              for item in wildcard.forced_transitions])
print(str(wildcard.to_ast_node()))

print('== written: !On -> Off : /Stop;   (inside region Panel; On is an ordinary composite state)')
inside = load('region_forced_in_region.fcstm')
print('forced_transitions:', [(item['from_path'], item['to_path'], item['expansion_count'])
                              for item in inside.forced_transitions])
print(block(str(inside.to_ast_node()), 'region Panel {'))

from pyfcstm.simulate import SimulationRuntime

print('== running the controller: /Stop finishes both regions and leaves Running in one cycle')
runtime = SimulationRuntime(model, input_source={'fault': 0, 'requested': 1})
for event in [None, '/Start', None, '/Stop']:
    runtime.cycle(event)
    print('cycle %d  %-7s %s  __forced_0=%s' % (
        runtime.cycle_count, event or '-', runtime.configuration, runtime.vars['__forced_0']))
