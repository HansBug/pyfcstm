"""Show what the context of an abstract handler reports for actions around regions."""
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

with open('handler_hooks.fcstm') as stream:
    model = load_state_machine_from_text(stream.read())

runtime = SimulationRuntime(model, input_source={'fault': 0, 'requested': 1})
ACTIONS = {
    'Tick': 'Controller.Tick',
    'GroupPre': 'Controller.Running.GroupPre',
    'SafetyPre': 'Controller.Running.Safety.SafetyPre',
    'Watch': 'Controller.Running.Safety.Normal.Watch',
    'Drive': 'Controller.Running.Motion.On.Drive',
}


def make_handler(name):
    def handler(ctx):
        print('%-9s state_path=%-31s active_leaf=%-31s configuration=%s' % (
            name, '.'.join(ctx.state_path), '.'.join(ctx.active_leaf), ctx.configuration))
    return handler


for name, path in ACTIONS.items():
    runtime.register_abstract_handler(path, make_handler(name))

for label, events in [('cycle 1', None), ('cycle 2 /Start', '/Start'), ('cycle 3', None)]:
    print('-- %s' % label)
    runtime.cycle(events)
