from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

HOT = [0, 1, 1, 0]
OPEN = [0, 1, 0, 0]

for name in ("panel_flat", "panel_regions"):
    runtime = SimulationRuntime(
        load_state_machine_from_file(f"{name}.fcstm"),
        input_source={"hot": SequenceInput(HOT), "open": SequenceInput(OPEN)},
    )
    print(f"== {name}.fcstm")
    for _ in HOT:
        result = runtime.cycle()
        inputs = result.inputs
        print(f"hot={inputs['hot']} open={inputs['open']} -> {runtime.configuration}")
