from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime
from region_trace import load

written = load("controller.fcstm")
exported_text = str(written.to_ast_node())
reloaded = load_state_machine_from_text(exported_text)
print("exported text: %d lines, loads again: %s" % (len(exported_text.splitlines()), type(reloaded).__name__))
print("hidden variables of the written model:", written.forced_variables)
print("variables of the reloaded model:", [item.name for item in reloaded.defines.values()])
print("hidden variables the reloaded model still marks:", reloaded.forced_variables)

steps = [
    (None, {"fault": 0, "requested": 1}),
    (["/Start"], {"fault": 0, "requested": 1}),
    (None, {"fault": 0, "requested": 1}),
    (None, {"fault": 1, "requested": 1}),
    (["/Stop"], {"fault": 0, "requested": 0}),
    (None, {"fault": 0, "requested": 0}),
]


def run(model):
    runtime = SimulationRuntime(model, input_source={"fault": 0, "requested": 0})
    rows = []
    for events, inputs in steps:
        runtime.cycle(events, inputs=inputs)
        rows.append((str(runtime.configuration), dict(runtime.vars)))
    return rows


first, second = run(written), run(reloaded)
for number, (left, right) in enumerate(zip(first, second), start=1):
    print(number, left[0], "same" if left == right else "DIFFERENT")
print("every cycle identical:", first == second)
