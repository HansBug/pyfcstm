import random

from pyfcstm.dsl import INIT_STATE
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime


def load(path):
    with open(path) as handle:
        return load_state_machine_from_text(handle.read())


def size(model):
    states = list(model.walk_states())
    leaves = [s for s in states if s.is_leaf_state]
    containers = list(states)
    for state in states:
        containers += list(getattr(state, "regions", {}).values())
    transitions = [
        t
        for owner in containers
        for t in owner.transitions
        if t.from_state is not INIT_STATE
    ]
    return len(leaves), len(transitions)


def run(model, inputs):
    runtime = SimulationRuntime(model, input_source={"x0": 0, "x1": 0}, history_size=1)
    trace = []
    for values in inputs:
        runtime.cycle(inputs=values)
        trace.append(dict(runtime.vars))
    return trace


regions = load("product_r2_s3.fcstm")
flat = load("expanded_r2_s3.fcstm")
print("regions: %d leaf states, %d transitions" % size(regions))
print("flat:    %d leaf states, %d transitions" % size(flat))

rng = random.Random(7)
inputs = [{"x0": rng.randint(0, 1), "x1": rng.randint(0, 1)} for _ in range(200)]
a, b = run(regions, inputs), run(flat, inputs)
print("same variables after every one of %d cycles: %s" % (len(inputs), a == b))
print("variables after the last cycle:", a[-1])
