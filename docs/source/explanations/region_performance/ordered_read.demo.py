import random

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

LABELS = [
    "regions_reader_after_writer",
    "regions_reader_before_writer",
    "flat_naive",
    "flat_substituted",
]


def run(label, inputs):
    with open("coupled_%s.fcstm" % label) as handle:
        model = load_state_machine_from_text(handle.read())
    runtime = SimulationRuntime(model, input_source={"x0": 0}, history_size=1)
    trace = []
    for value in inputs:
        runtime.cycle(inputs={"x0": value})
        trace.append((runtime.vars["c"], runtime.vars["d"]))
    return trace


rng = random.Random(3)
inputs = [rng.randint(0, 1) for _ in range(200)]
traces = {label: run(label, inputs) for label in LABELS}

print("x0 :", " ".join(str(v) for v in inputs[:8]))
for label in LABELS:
    print("%-30s c after cycles 1-8: %s" % (label, " ".join(str(c) for c, _ in traces[label][:8])))
print()
reference = traces["regions_reader_after_writer"]
for label in LABELS[1:]:
    differing = sum(1 for x, y in zip(reference, traces[label]) if x != y)
    print("%-30s differs from regions_reader_after_writer in %3d of 200 cycles" % (label, differing))
print()
before = traces["regions_reader_before_writer"]
differing = sum(1 for x, y in zip(before, traces["flat_naive"]) if x != y)
print("%-30s differs from regions_reader_before_writer in %3d of 200 cycles" % ("flat_naive", differing))
