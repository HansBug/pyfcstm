from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

FAULT = [0, 0, 0, 1, 1, 0]
REQUESTED = [1, 1, 1, 1, 1, 1]

for name in ("controller", "controller_swapped"):
    runtime = SimulationRuntime(
        load_state_machine_from_file(f"{name}.fcstm"),
        input_source={
            "fault": SequenceInput(FAULT),
            "requested": SequenceInput(REQUESTED),
        },
    )
    print(f"== {name}.fcstm")
    for cycle in range(len(FAULT)):
        runtime.cycle(["/Start"] if cycle == 1 else [])
        print(
            f"cycle {runtime.cycle_count} fault={runtime.last_inputs['fault']} "
            f"permit={runtime.vars['permit']} motor={runtime.vars['motor']} "
            f"{runtime.configuration}"
        )
