from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

print("== watch_regions.fcstm")
runtime = SimulationRuntime(
    load_state_machine_from_file("watch_regions.fcstm"),
    input_source={"go": SequenceInput([0, 1, 1])},
)
for _ in range(3):
    result = runtime.cycle()
    print(f"go={result.inputs['go']} -> {runtime.configuration}")

